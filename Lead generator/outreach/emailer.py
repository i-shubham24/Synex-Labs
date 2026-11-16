"""
Outreach email sender (SMTP).

Off until SMTP_HOST and EMAIL_FROM_ADDRESS are set. Use a separate domain and
mailbox for cold email. Every cold email carries a sign-off, optional postal
address and an unsubscribe line, plus a List-Unsubscribe header. Daily volume
ramps up slowly (warm-up) and never exceeds EMAIL_DAILY_CAP.
"""

import logging
import re
import smtplib
import socket
import ssl
from datetime import datetime, timedelta, timezone, date
from email.message import EmailMessage
from email.utils import formataddr, formatdate, make_msgid
from typing import Optional, Tuple, Dict, Any

from config.settings import settings
from database.db import kv_get, kv_set
from database.email_repository import EmailRepository
from database.prospect_repository import SuppressionList
from .messages import email_footer

logger = logging.getLogger("outreach.email")

EMAIL_RE = re.compile(r"^[A-Za-z0-9._%+'-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}$")


class EmailNotConfigured(Exception):
    pass


class EmailBlocked(Exception):
    """Sending refused on purpose (cap, suppression, bad address, outside hours)."""


def is_configured() -> bool:
    return bool(settings.SMTP_HOST and settings.EMAIL_FROM_ADDRESS)


def _local_midnight_utc() -> str:
    local_now = datetime.now().astimezone()
    midnight = local_now.replace(hour=0, minute=0, second=0, microsecond=0)
    return midnight.astimezone(timezone.utc).strftime("%Y-%m-%d %H:%M:%S")


def daily_limit() -> int:
    first = kv_get("email_first_send_date")
    if not first:
        return min(settings.EMAIL_DAILY_CAP, settings.EMAIL_WARMUP_START)
    days = (date.today() - date.fromisoformat(first)).days
    return min(settings.EMAIL_DAILY_CAP, settings.EMAIL_WARMUP_START + settings.EMAIL_WARMUP_STEP * max(0, days))


def sent_today() -> int:
    return EmailRepository.sent_since(_local_midnight_utc())


def remaining_today() -> int:
    return max(0, daily_limit() - sent_today())


def within_send_hours(now: Optional[datetime] = None) -> bool:
    try:
        start, end = (int(x) for x in settings.EMAIL_SEND_HOURS.split("-"))
    except ValueError:
        return True
    hour = (now or datetime.now()).hour
    return start <= hour < end


def check_address(address: str) -> Tuple[bool, str]:
    address = (address or "").strip()
    if not EMAIL_RE.match(address):
        return False, "not a valid email address"
    if SuppressionList.contains(address):
        return False, "on the do-not-contact list"
    domain = address.split("@", 1)[1]
    try:
        socket.getaddrinfo(domain, None)
    except socket.gaierror:
        return False, f"domain {domain} does not exist"
    return True, "ok"


def _build(to: str, subject: str, body: str, in_reply_to: Optional[str], references: Optional[str]) -> EmailMessage:
    msg = EmailMessage()
    msg["From"] = formataddr((settings.EMAIL_FROM_NAME, settings.EMAIL_FROM_ADDRESS))
    msg["To"] = to
    msg["Subject"] = subject
    msg["Date"] = formatdate(localtime=True)
    domain = settings.EMAIL_FROM_ADDRESS.split("@")[-1] or "synexlabs.in"
    msg["Message-ID"] = make_msgid(domain=domain)
    msg["List-Unsubscribe"] = f"<mailto:{settings.EMAIL_FROM_ADDRESS}?subject=unsubscribe>"
    if in_reply_to:
        msg["In-Reply-To"] = in_reply_to
        msg["References"] = (references + " " if references else "") + in_reply_to
    msg.set_content(body)
    return msg


def _smtp_send(msg: EmailMessage):
    context = ssl.create_default_context()
    if settings.SMTP_SECURITY == "ssl":
        server = smtplib.SMTP_SSL(settings.SMTP_HOST, settings.SMTP_PORT, timeout=30, context=context)
    else:
        server = smtplib.SMTP(settings.SMTP_HOST, settings.SMTP_PORT, timeout=30)
    try:
        server.ehlo()
        if settings.SMTP_SECURITY == "starttls":
            server.starttls(context=context)
            server.ehlo()
        if settings.SMTP_USER and settings.SMTP_PASSWORD:
            server.login(settings.SMTP_USER, settings.SMTP_PASSWORD)
        server.send_message(msg)
    finally:
        try:
            server.quit()
        except Exception:
            pass


def send_email(
    to: str,
    subject: str,
    body: str,
    kind: str,
    prospect_id: Optional[int] = None,
    lead_id: Optional[int] = None,
    in_reply_to: Optional[str] = None,
    references: Optional[str] = None,
    enforce_hours: bool = False,
) -> Dict[str, Any]:
    """
    Sends one email and records it. kind: opener | followup1..3 | reply.
    Replies to people who wrote back are exempt from the daily cap.
    """
    if not is_configured():
        raise EmailNotConfigured("Email is not set up (SMTP_HOST / EMAIL_FROM_ADDRESS in .env)")
    ok, reason = check_address(to)
    if not ok:
        raise EmailBlocked(f"{to}: {reason}")
    cold = kind != "reply"
    if cold and remaining_today() <= 0:
        raise EmailBlocked(f"Daily email limit reached ({daily_limit()} today during warm-up)")
    if enforce_hours and not within_send_hours():
        raise EmailBlocked(f"Outside sending hours ({settings.EMAIL_SEND_HOURS})")

    full_body = body.rstrip() + email_footer(cold=cold)
    msg = _build(to, subject, full_body, in_reply_to, references)
    try:
        _smtp_send(msg)
    except Exception as e:
        EmailRepository.record(
            prospect_id=prospect_id, lead_id=lead_id, direction="out", kind=kind,
            message_id=msg["Message-ID"], in_reply_to=in_reply_to, from_addr=settings.EMAIL_FROM_ADDRESS,
            to_addr=to, subject=subject, body=full_body, status="failed", error=f"{type(e).__name__}: {e}"[:300],
        )
        raise

    if not kv_get("email_first_send_date"):
        kv_set("email_first_send_date", date.today().isoformat())
    email_id = EmailRepository.record(
        prospect_id=prospect_id, lead_id=lead_id, direction="out", kind=kind,
        message_id=msg["Message-ID"], in_reply_to=in_reply_to, from_addr=settings.EMAIL_FROM_ADDRESS,
        to_addr=to, subject=subject, body=full_body, status="sent",
    )
    logger.info(f"Sent {kind} email to {to} (#{email_id})")
    return {"id": email_id, "message_id": msg["Message-ID"]}
