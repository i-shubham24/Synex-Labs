"""
Background automation jobs: follow-ups, morning digest, health alerts, backups.
"""

import logging
import sqlite3
import time
from datetime import datetime, date
from typing import Dict, Any, List

from config.settings import settings
from database.db import get_db_path, kv_get, kv_set
from database.prospect_repository import ProspectRepository
from database.repository import LeadRepository
from database.email_repository import EmailRepository
from brain.gemini_analyzer import GeminiAnalyzer
from prospector.sources import GooglePlacesSource
from . import emailer
from .actions import send_followup_email, ActionError, followup_for

logger = logging.getLogger("outreach.automation")


# ---------------------------------------------------------------------------- follow-ups

def run_followups() -> Dict[str, Any]:
    """
    Hourly. Emails due follow-ups automatically (when email is set up and the lead was
    contacted by email). Manual-channel follow-ups are sent as Telegram cards with the
    morning digest. Leads whose last follow-up went unanswered become 'no response'.
    """
    expired = ProspectRepository.expire_waiting()
    emailed, skipped = 0, 0
    auto_email = emailer.is_configured() and settings.EMAIL_AUTO_FOLLOWUPS
    for p in ProspectRepository.due_followups(limit=100):
        if auto_email and p.get("channel") == "email" and p.get("email") and p.get("email_status") != "bounced":
            try:
                send_followup_email(p["id"], enforce_hours=True)
                emailed += 1
            except ActionError as e:
                skipped += 1
                logger.info(f"Follow-up for #{p['id']} postponed: {e}")
                if "limit" in str(e).lower() or "hours" in str(e).lower():
                    break
    return {"emailed": emailed, "postponed": skipped, "no_response": expired}


def manual_followups_due() -> List[Dict[str, Any]]:
    return [
        p for p in ProspectRepository.due_followups(limit=100)
        if not (emailer.is_configured() and settings.EMAIL_AUTO_FOLLOWUPS and p.get("channel") == "email" and p.get("email"))
    ]


# ---------------------------------------------------------------------------- digest

def build_digest(problems: List[str]) -> str:
    stats = ProspectRepository.get_stats()
    hot = ProspectRepository.list(status="new", limit=3) + ProspectRepository.list(status="alerted", limit=3)
    waiting = sum(stats["by_status"].get(s, 0) for s in ("new", "alerted"))
    leads = [l for l in LeadRepository.get_recent_qualified(limit=100) if l["status"] in ("new", "alerted")]
    mail = EmailRepository.counts()
    due = manual_followups_due()
    lines = [f"☀️ <b>Lead engine, {datetime.now():%A %d %b}</b>", ""]
    lines.append(f"• Prospects waiting: <b>{waiting}</b>")
    if hot:
        names = ", ".join(p["name"] for p in hot[:3])
        lines.append(f"   Hottest: {names}")
    lines.append(f"• Follow-ups to send by hand today: <b>{len(due)}</b>")
    lines.append(f"• Email replies waiting: <b>{mail['replies_waiting']}</b>")
    lines.append(f"• Social and website leads waiting: <b>{len(leads)}</b>")
    contacted = sum(stats["by_status"].get(s, 0) for s in ("contacted", "replied", "call_booked", "proposal_sent", "won"))
    lines.append(f"• In pipeline: {contacted} · Won: {stats['by_status'].get('won', 0)}")
    if emailer.is_configured():
        lines.append(f"• Emails sent (7 days): {mail['sent_7d']} · Today's limit: {emailer.daily_limit()}")
    if problems:
        lines += ["", "⚠️ <b>Needs attention</b>"] + [f"• {p}" for p in problems]
    return "\n".join(lines)


def send_digest(telegram, problems: List[str]) -> Dict[str, Any]:
    if not telegram.is_configured():
        return {"sent": 0}
    if not telegram.send_text(build_digest(problems)):
        raise RuntimeError("Telegram unreachable; the digest will be retried")
    kv_set("digest_last", date.today().isoformat())
    cards = 0
    for p in manual_followups_due()[: settings.FOLLOWUP_CARDS_PER_DIGEST]:
        number, text = followup_for(p)
        if telegram.send_followup_card(p, number, text):
            cards += 1
        time.sleep(1.1)
    return {"digest": 1, "followup_cards": cards}


def digest_due() -> bool:
    now = datetime.now()
    after_time = (now.hour, now.minute) >= (settings.DIGEST_HOUR, settings.DIGEST_MINUTE)
    return after_time and kv_get("digest_last") != date.today().isoformat()


def telegram_catch_up(telegram, problems: List[str]) -> Dict[str, Any]:
    """
    Every 30 min: sends a missed digest and waiting prospect cards (within the daily cap).
    Covers Telegram outages and a PC that was off at the scheduled times.
    """
    if not telegram.is_configured():
        return {"skipped": "telegram off"}
    result: Dict[str, Any] = {}
    if digest_due():
        result.update(send_digest(telegram, problems))
    from prospector.engine import ProspectEngine
    result["prospect_cards"] = ProspectEngine().dispatch()
    return result


# ---------------------------------------------------------------------------- health

class HealthMonitor:
    """Collects problems and alerts Telegram, at most once per problem per cooldown."""

    COOLDOWN_SECONDS = 6 * 3600

    def problems(self, jobs: List[Dict[str, Any]]) -> List[str]:
        out = []
        if GeminiAnalyzer.last_error and time.time() - GeminiAnalyzer.last_error_at < 3 * 3600:
            out.append(f"Gemini is failing: {GeminiAnalyzer.last_error}")
        places = GooglePlacesSource()
        if places.is_configured():
            left = places.remaining_budget()
            if left <= settings.PLACES_MONTHLY_CALL_LIMIT * 0.2:
                out.append(f"Google Places budget low: {left} calls left this month")
        for job in jobs:
            if (job.get("consecutive_errors") or 0) >= 3:
                out.append(f"{job['name']} failed {job['consecutive_errors']} times in a row: {job.get('last_message', '')[:120]}")
        return out

    def alert(self, telegram, jobs: List[Dict[str, Any]]) -> int:
        sent = 0
        for problem in self.problems(jobs):
            key = "alert:" + problem.split(":")[0][:60]
            last = float(kv_get(key, "0") or 0)
            if time.time() - last < self.COOLDOWN_SECONDS:
                continue
            if telegram.is_configured() and telegram.send_text(f"⚠️ <b>Lead engine</b>\n{problem}"):
                kv_set(key, time.time())
                sent += 1
        return sent


# ---------------------------------------------------------------------------- backups

def backup_database() -> Dict[str, Any]:
    src_path = get_db_path()
    folder = src_path.parent / "backups"
    folder.mkdir(parents=True, exist_ok=True)
    dest = folder / f"leads-{date.today().isoformat()}.db"
    with sqlite3.connect(src_path) as src, sqlite3.connect(dest) as dst:
        src.backup(dst)
    backups = sorted(folder.glob("leads-*.db"))
    for old in backups[: max(0, len(backups) - settings.BACKUP_KEEP)]:
        old.unlink(missing_ok=True)
    return {"backup": dest.name, "kept": min(len(backups), settings.BACKUP_KEEP)}
