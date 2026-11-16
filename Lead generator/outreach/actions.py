"""
One place for every outreach action, shared by the dashboard and Telegram buttons.
Each function returns a small dict that both UIs can show.
"""

import logging
from typing import Optional, Dict, Any, Tuple

from database.prospect_repository import ProspectRepository, SuppressionList
from database.repository import LeadRepository
from database.email_repository import EmailRepository
from . import emailer
from .messages import opener_subject, followup_text, followup_subject

logger = logging.getLogger("outreach.actions")


class ActionError(Exception):
    pass


def _prospect(pid: int) -> Dict[str, Any]:
    p = ProspectRepository.get(pid)
    if not p:
        raise ActionError(f"Prospect #{pid} not found")
    return p


def opener_for(p: Dict[str, Any]) -> str:
    if p.get("opener"):
        return p["opener"]
    from prospector.engine import template_opener
    return template_opener(p)


def followup_for(p: Dict[str, Any]) -> Tuple[int, str]:
    number = int(p.get("followup_step") or 0) + 1
    return number, followup_text(p, min(number, 3))


# ------------------------------------------------------------------ prospects

def mark_contacted(pid: int, channel: Optional[str] = None) -> Dict[str, Any]:
    p = _prospect(pid)
    if p.get("phone") and SuppressionList.contains(p["phone"]):
        raise ActionError("This business asked not to be contacted")
    ProspectRepository.set_status(pid, "contacted", channel=channel)
    return {"ok": True, "message": f"{p['name']} marked as contacted"}


def set_prospect_stage(pid: int, stage: str) -> Dict[str, Any]:
    p = _prospect(pid)
    if stage == "contacted":
        return mark_contacted(pid)
    ProspectRepository.set_status(pid, stage)
    result = {"ok": True, "message": f"{p['name']}: {stage.replace('_', ' ')}"}
    if stage == "call_booked":
        try:
            from sales.briefs import build_brief
            result["brief"] = build_brief(pid)
        except Exception as e:
            logger.warning(f"Brief for #{pid} failed: {e}")
    return result


def send_opener_email(pid: int, subject: Optional[str] = None, body: Optional[str] = None) -> Dict[str, Any]:
    p = _prospect(pid)
    if not p.get("email"):
        raise ActionError("No email address for this business")
    if p.get("email_status") == "bounced":
        raise ActionError("This address bounced before")
    if EmailRepository.first_outgoing(pid):
        raise ActionError("The opener was already emailed; follow-ups are scheduled")
    try:
        emailer.send_email(
            p["email"], subject or opener_subject(p), body or opener_for(p), kind="opener", prospect_id=pid
        )
    except (emailer.EmailNotConfigured, emailer.EmailBlocked) as e:
        raise ActionError(str(e))
    ProspectRepository.set_status(pid, "contacted", channel="email")
    return {"ok": True, "message": f"Email sent to {p['email']}"}


def followup_done(pid: int) -> Dict[str, Any]:
    """The due follow-up was sent by hand (WhatsApp, phone, DM)."""
    p = _prospect(pid)
    result = ProspectRepository.advance_followup(pid)
    text = {
        "scheduled": "Follow-up logged, next one scheduled",
        "waiting": "Last follow-up logged, waiting for a reply",
        "no_response": "Marked as no response",
    }.get(result, "Nothing to update")
    return {"ok": True, "message": f"{p['name']}: {text}"}


def send_followup_email(pid: int, enforce_hours: bool = False) -> Dict[str, Any]:
    p = _prospect(pid)
    if not p.get("email") or p.get("email_status") == "bounced":
        raise ActionError("No working email address for this business")
    number, text = followup_for(p)
    if number > 3:
        return followup_done(pid)
    first = EmailRepository.first_outgoing(pid)
    last = EmailRepository.last_outgoing(pid)
    try:
        emailer.send_email(
            p["email"], followup_subject(p, first["subject"] if first else None), text,
            kind=f"followup{number}", prospect_id=pid,
            in_reply_to=last["message_id"] if last else None,
            references=first["message_id"] if first and last and first["id"] != last["id"] else None,
            enforce_hours=enforce_hours,
        )
    except (emailer.EmailNotConfigured, emailer.EmailBlocked) as e:
        raise ActionError(str(e))
    ProspectRepository.advance_followup(pid)
    return {"ok": True, "message": f"Follow-up {number} emailed to {p['email']}"}


def stop_sequence(pid: int) -> Dict[str, Any]:
    p = _prospect(pid)
    ProspectRepository.set_status(pid, "no_response")
    return {"ok": True, "message": f"{p['name']}: follow-ups stopped"}


# ------------------------------------------------------------------ replies

def send_reply(email_id: int, body: Optional[str] = None) -> Dict[str, Any]:
    incoming = EmailRepository.get(email_id)
    if not incoming or incoming["direction"] != "in":
        raise ActionError("Reply not found")
    text = (body or incoming.get("draft_reply") or "").strip()
    if not text:
        raise ActionError("No reply text")
    subject = incoming.get("subject") or "Re:"
    if not subject.lower().startswith("re:"):
        subject = f"Re: {subject}"
    try:
        emailer.send_email(
            incoming["from_addr"], subject, text, kind="reply", prospect_id=incoming.get("prospect_id"),
            in_reply_to=incoming.get("message_id"),
        )
    except (emailer.EmailNotConfigured, emailer.EmailBlocked) as e:
        raise ActionError(str(e))
    EmailRepository.mark_handled(email_id)
    return {"ok": True, "message": f"Reply sent to {incoming['from_addr']}"}


def mark_reply_handled(email_id: int) -> Dict[str, Any]:
    EmailRepository.mark_handled(email_id)
    return {"ok": True, "message": "Marked as handled"}


# ------------------------------------------------------------------ social / website leads

def set_lead_stage(lead_id: int, stage: str) -> Dict[str, Any]:
    lead = LeadRepository.get(lead_id)
    if not lead:
        raise ActionError(f"Lead #{lead_id} not found")
    LeadRepository.set_status(lead_id, stage)
    return {"ok": True, "message": f"Lead #{lead_id}: {stage.replace('_', ' ')}"}
