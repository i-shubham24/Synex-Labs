"""Subject lines, follow-ups and sign-offs. Plain, short, no hype, no em dashes."""

from typing import Dict, Any, Optional

from config.settings import settings


def audit_url(p: Dict[str, Any]) -> Optional[str]:
    if p.get("slug") and p.get("pages_live"):
        return f"{settings.SITE_URL}/p/{p['slug']}/audit.html"
    return None


def demo_url(p: Dict[str, Any]) -> Optional[str]:
    if p.get("slug") and p.get("pages_live"):
        return f"{settings.SITE_URL}/p/{p['slug']}/demo.html"
    return None


def preview_line(p: Dict[str, Any]) -> str:
    """A sentence pointing to the live audit / demo page, when one exists."""
    demo, audit = demo_url(p), audit_url(p)
    if p.get("tier") in ("no_website", "no_website_unverified", "social_only") and demo:
        return f"I put together a quick preview of what your site could look like: {demo}"
    if audit:
        return f"I wrote up a short audit of your current site here: {audit}"
    return ""


def offer(p: Dict[str, Any]) -> str:
    if p.get("tier") in ("no_website", "no_website_unverified", "social_only"):
        return "a free homepage preview"
    return "a free audit with the fixes"


def opener_subject(p: Dict[str, Any]) -> str:
    name = p.get("name", "your business")
    tier = p.get("tier")
    if tier in ("no_website", "no_website_unverified"):
        return f"A website for {name}?"
    if tier == "social_only":
        return f"{name}: a site of your own"
    if tier == "broken_website":
        return f"Heads-up: {name}'s website link"
    return f"Quick note about {name}'s website"


def followup_text(p: Dict[str, Any], number: int) -> str:
    """number: 1, 2 or 3 (the Nth follow-up)."""
    name = p.get("name", "there")
    preview = preview_line(p)
    if number == 1:
        lines = [f"Hi {name} team, just bumping my note in case it got buried."]
        lines.append(preview or f"Happy to send {offer(p)} if it would help.")
        return " ".join(lines)
    if number == 2:
        issues = p.get("issues") or []
        hook = ""
        if p.get("tier") in ("weak_website", "broken_website") and issues:
            from prospector.engine import _issue_phrase
            hook = f"The main thing I noticed is that {_issue_phrase(issues[0])}, which is usually a quick fix. "
        elif p.get("tier") in ("no_website", "no_website_unverified", "social_only"):
            hook = "A simple site of your own helps people find you on Google and trust you before they call. "
        booking = f" If it's easier, you can grab 15 minutes here: {settings.BOOKING_URL}" if settings.BOOKING_URL else ""
        ask = preview or f"Would {offer(p)} be useful?"
        return f"Hi again from Synex Labs. {hook}{ask}{booking}"
    return (
        f"Last note from me, I don't want to clutter your inbox. If a better website is on your list "
        f"this year, just reply and I'll send some ideas. All the best with {name}."
    )


def followup_subject(p: Dict[str, Any], original_subject: Optional[str]) -> str:
    subject = original_subject or opener_subject(p)
    return subject if subject.lower().startswith("re:") else f"Re: {subject}"


def studio_whatsapp_display() -> str:
    """The studio WhatsApp number written for people, e.g. '+91 79733 73923' (empty if not set)."""
    digits = "".join(ch for ch in settings.STUDIO_WHATSAPP if ch.isdigit())
    if digits.startswith("91") and len(digits) == 12:
        return f"+91 {digits[2:7]} {digits[7:]}"
    return f"+{digits}" if digits else ""


def email_footer(cold: bool = True, body: str = "") -> str:
    """
    Signature added under an email. Skips the name and website when the body already has them,
    and leaves the WhatsApp number out of cold emails (openers and follow-ups).
    """
    text = body.rstrip()
    site = settings.SITE_URL.replace("https://", "")
    sig = []
    if not text.endswith(settings.EMAIL_SIGNATURE_NAME):
        sig.append(settings.EMAIL_SIGNATURE_NAME)
    if site not in text:
        sig.append(f"Synex Labs | {site}")
    if not cold and studio_whatsapp_display():
        sig.append(f"WhatsApp: {studio_whatsapp_display()}")
    if cold and settings.EMAIL_POSTAL_ADDRESS:
        sig.append(settings.EMAIL_POSTAL_ADDRESS)
    blocks = ["\n".join(sig)] if sig else []
    if cold:
        blocks.append('Not interested? Reply "unsubscribe" and I won\'t email again.')
    return "".join("\n\n" + b for b in blocks)
