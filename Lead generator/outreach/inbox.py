"""
Inbox watcher (IMAP).

- Opens the mailbox read-only (EXAMINE + BODY.PEEK), so nothing is marked as read.
- On first run it starts from the newest message; old mail is never processed.
- Only stores messages that belong to our outreach (a reply to an email we sent,
  or mail from a prospect's address), bounces of our emails, and website contact
  form briefs ("New brief: ..."). Everything else in the inbox is ignored.
"""

import email
import imaplib
import logging
import re
from email import policy
from email.utils import parseaddr
from typing import Optional, Dict, Any, List, Tuple

from config.settings import settings
from database.db import kv_get, kv_set
from database.email_repository import EmailRepository
from database.prospect_repository import ProspectRepository, SuppressionList
from database.repository import LeadRepository
from brain.gemini_analyzer import GeminiAnalyzer, GeminiUnavailable
from brain.prompts import (
    REPLY_SYSTEM_INSTRUCTION,
    REPLY_TEMPLATE,
    WEBSITE_BRIEF_SYSTEM_INSTRUCTION,
)

logger = logging.getLogger("outreach.inbox")

UNSUBSCRIBE_RE = re.compile(r"\b(unsubscribe|remove me|stop emailing|do not (?:contact|email)|don'?t (?:contact|email))\b", re.I)
OOO_RE = re.compile(r"\b(out of (?:the )?office|on (?:annual )?leave|away until|auto(?:matic)?[- ]?reply|vacation)\b", re.I)
BOUNCE_FROM_RE = re.compile(r"(mailer-daemon|postmaster|mail delivery)", re.I)
LABELS = {"interested", "question", "not_now", "not_interested", "unsubscribe", "out_of_office", "other"}


def accounts() -> List[Tuple[str, int, str, str, str]]:
    out = []
    if settings.IMAP_HOST and settings.IMAP_USER and settings.IMAP_PASSWORD:
        out.append((settings.IMAP_HOST, settings.IMAP_PORT, settings.IMAP_USER, settings.IMAP_PASSWORD, settings.IMAP_FOLDER))
    if settings.BRIEFS_IMAP_HOST and settings.BRIEFS_IMAP_USER and settings.BRIEFS_IMAP_PASSWORD:
        out.append((settings.BRIEFS_IMAP_HOST, settings.BRIEFS_IMAP_PORT, settings.BRIEFS_IMAP_USER,
                    settings.BRIEFS_IMAP_PASSWORD, "INBOX"))
    return out


def is_configured() -> bool:
    return bool(accounts())


def _text_body(msg) -> str:
    part = msg.get_body(preferencelist=("plain", "html"))
    if part is None:
        return ""
    try:
        text = part.get_content()
    except Exception:
        text = (part.get_payload(decode=True) or b"").decode("utf-8", errors="ignore")
    if part.get_content_type() == "text/html":
        text = re.sub(r"<(script|style)[^>]*>.*?</\1>", " ", text, flags=re.S | re.I)
        text = re.sub(r"<br\s*/?>|</p>", "\n", text, flags=re.I)
        text = re.sub(r"<[^>]+>", " ", text)
    return text


def strip_quoted(text: str) -> str:
    """Keeps only the new part of a reply."""
    lines = []
    for line in text.splitlines():
        if re.match(r"^\s*On .+wrote:\s*$", line) or re.match(r"^-{2,}\s*Original Message", line, re.I):
            break
        if re.match(r"^\s*(From|Sent|De|Von):\s", line) and lines:
            break
        if line.lstrip().startswith(">"):
            continue
        lines.append(line)
    return re.sub(r"\n{3,}", "\n\n", "\n".join(lines)).strip()


class InboxWatcher:

    def __init__(self, notifier=None):
        self.gemini = GeminiAnalyzer()
        self.notifier = notifier  # TelegramAlerter or None

    # ------------------------------------------------------------------ IMAP

    def poll(self) -> Dict[str, int]:
        totals = {"checked": 0, "matched": 0}
        for host, port, user, password, folder in accounts():
            try:
                checked, matched = self._poll_account(host, port, user, password, folder)
                totals["checked"] += checked
                totals["matched"] += matched
            except Exception as e:
                logger.error(f"[Inbox] {user}@{host}: {type(e).__name__}: {e}")
                raise
        return totals

    def _poll_account(self, host, port, user, password, folder) -> Tuple[int, int]:
        imap = imaplib.IMAP4_SSL(host, port, timeout=30)
        try:
            imap.login(user, password)
            status, data = imap.select(f'"{folder}"', readonly=True)
            if status != "OK":
                raise RuntimeError(f"cannot open folder {folder}")
            uidvalidity = (imap.untagged_responses.get("UIDVALIDITY") or [b"0"])[0].decode()
            key = f"imap:{user}:{folder}:{uidvalidity}"
            status, data = imap.uid("search", None, "ALL")
            uids = [int(x) for x in (data[0] or b"").split()]
            if not uids:
                return 0, 0
            last = kv_get(key)
            if last is None:
                kv_set(key, max(uids))  # first run: start from now, never process old mail
                return 0, 0
            new = [u for u in uids if u > int(last)][:50]
            matched = 0
            for uid in new:
                status, fetched = imap.uid("fetch", str(uid), "(BODY.PEEK[])")
                raw = next((part[1] for part in fetched if isinstance(part, tuple)), None)
                if raw and self.process_message(raw):
                    matched += 1
                kv_set(key, uid)
            return len(new), matched
        finally:
            try:
                imap.logout()
            except Exception:
                pass

    # ------------------------------------------------------------------ processing

    def process_message(self, raw: bytes) -> Optional[Dict[str, Any]]:
        msg = email.message_from_bytes(raw, policy=policy.default)
        message_id = (msg.get("Message-ID") or "").strip()
        if message_id and EmailRepository.exists_message(message_id):
            return None
        subject = str(msg.get("Subject") or "").strip()
        from_addr = parseaddr(str(msg.get("From") or ""))[1].lower()

        if subject.lower().startswith("new brief:"):
            return self._website_brief(msg, subject, message_id)

        if BOUNCE_FROM_RE.search(str(msg.get("From") or "")) or msg.get_content_type() == "multipart/report":
            return self._bounce(msg, message_id, subject)

        refs = [msg.get("In-Reply-To") or ""] + str(msg.get("References") or "").split()
        original = EmailRepository.find_by_message_ids(refs)
        prospect = ProspectRepository.get(original["prospect_id"]) if original and original.get("prospect_id") else None
        if not prospect and from_addr:
            prospect = ProspectRepository.find_by_email(from_addr)
        if not prospect:
            return None  # not part of our outreach: leave the user's mail alone

        body = strip_quoted(_text_body(msg))[:4000]
        label, summary, draft = self._classify(msg, prospect, original, body)
        email_id = EmailRepository.record(
            prospect_id=prospect["id"], direction="in", kind="reply", message_id=message_id,
            in_reply_to=msg.get("In-Reply-To"), from_addr=from_addr, to_addr=settings.EMAIL_FROM_ADDRESS,
            subject=subject, body=body, status="received", label=label, summary=summary, draft_reply=draft,
            handled=1 if label in ("out_of_office", "unsubscribe") else 0,
        )
        self._apply(prospect, label, from_addr)
        result = {"email_id": email_id, "prospect_id": prospect["id"], "label": label}
        if self.notifier and label not in ("out_of_office", "unsubscribe"):
            self.notifier.send_reply_alert(EmailRepository.get(email_id), prospect)
        return result

    def _classify(self, msg, prospect, original, body) -> Tuple[str, str, str]:
        auto = (msg.get("Auto-Submitted") or "").lower()
        if (auto and auto != "no") or OOO_RE.search(str(msg.get("Subject") or "")) or (OOO_RE.search(body[:400]) and len(body) < 800):
            return "out_of_office", "Automatic away message", ""
        if UNSUBSCRIBE_RE.search(body[:500]) and len(body) < 400:
            return "unsubscribe", "Asked not to be contacted again", ""
        if self.gemini.is_configured():
            try:
                data = self.gemini.generate_json(
                    REPLY_TEMPLATE.format(
                        business=prospect["name"],
                        our_email=(original or {}).get("body", "")[:1500],
                        reply=body[:2500],
                        booking_hint=f"Booking link you may offer: {settings.BOOKING_URL}" if settings.BOOKING_URL else "",
                    ),
                    REPLY_SYSTEM_INSTRUCTION,
                )
                label = str(data.get("label", "other")).strip().lower()
                return (label if label in LABELS else "other"), str(data.get("summary", ""))[:300], str(data.get("draft_reply", ""))
            except (GeminiUnavailable, ValueError) as e:
                logger.warning(f"[Inbox] Reply classification fell back to manual: {e}")
        return "other", "New reply (not classified, Gemini unavailable)", ""

    @staticmethod
    def _apply(prospect, label, from_addr):
        pid = prospect["id"]
        if label == "out_of_office":
            ProspectRepository.postpone_followup(pid, 5)
        elif label in ("unsubscribe", "not_interested"):
            SuppressionList.add(from_addr, label)
            if prospect.get("phone"):
                SuppressionList.add(prospect["phone"], label)
            ProspectRepository.set_status(pid, "not_interested")
        elif prospect["status"] in ("new", "alerted", "contacted"):
            ProspectRepository.set_status(pid, "replied")

    def _bounce(self, msg, message_id, subject) -> Optional[Dict[str, Any]]:
        text = ""
        for part in msg.walk():
            if part.get_content_maintype() == "text" or part.get_content_type() == "message/delivery-status":
                try:
                    payload = part.get_payload(decode=True)
                    text += (payload or b"").decode("utf-8", errors="ignore") if payload else str(part.get_payload())
                except Exception:
                    continue
        failed = msg.get("X-Failed-Recipients") or ""
        m = re.search(r"Final-Recipient:\s*rfc822;\s*<?([^\s>]+@[^\s>]+)", text, re.I)
        address = (failed or (m.group(1) if m else "")).strip().lower()
        prospect = ProspectRepository.find_by_email(address) if address else None
        if not prospect:
            return None
        ProspectRepository.update(prospect["id"], email_status="bounced")
        EmailRepository.record(
            prospect_id=prospect["id"], direction="in", kind="bounce", message_id=message_id,
            from_addr="mailer-daemon", subject=subject, body=text[:1500], status="bounced",
            label="bounce", summary=f"Email to {address} bounced", handled=1,
        )
        return {"prospect_id": prospect["id"], "label": "bounce"}

    def _website_brief(self, msg, subject, message_id) -> Optional[Dict[str, Any]]:
        m = re.match(r"new brief:\s*(.+?)\s+from\s+(.+)$", subject, re.I)
        need, name = (m.group(1), m.group(2)) if m else ("Website", "Website visitor")
        reply_to = parseaddr(str(msg.get("Reply-To") or msg.get("From") or ""))[1]
        body = _text_body(msg).strip()[:4000]
        draft, category, country, first_site, old_site = "", need, "Unknown", False, False
        if self.gemini.is_configured():
            try:
                data = self.gemini.generate_json(
                    f"Name: {name}\nNeed: {need}\nTheir message and details:\n\"\"\"{body[:2500]}\"\"\"",
                    WEBSITE_BRIEF_SYSTEM_INSTRUCTION,
                )
                draft = str(data.get("draft_reply", ""))
                category = str(data.get("project_category") or need)
                country = str(data.get("country") or "Unknown")
                first_site = bool(data.get("first_website", False))
                old_site = bool(data.get("old_website", False))
            except (GeminiUnavailable, ValueError) as e:
                logger.warning(f"[Inbox] Brief reply draft failed: {e}")
        if not draft:
            first = name.split()[0] if name else "there"
            draft = (
                f"Hi {first}, thanks for reaching out about your {need.lower()} project. "
                f"Could you share your timeline and a rough budget? Happy to jump on a short call this week."
            )
        lead_id = LeadRepository.save_website_brief(
            message_id or f"brief-{hash(body)}", name, category, body, reply_to, draft,
            country=country, first_website=first_site, old_website=old_site,
        )
        if lead_id and self.notifier:
            lead = LeadRepository.get(lead_id)
            if self.notifier.send_lead_alert(lead):
                pass
        return {"lead_id": lead_id, "label": "website_brief"} if lead_id else None
