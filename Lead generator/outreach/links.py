"""One-tap contact links with the message already typed."""

import re
import urllib.parse
from typing import Optional


# City / country words -> calling code, for numbers stored without one (common in OpenStreetMap)
COUNTRY_CODES = [
    (("india", "mumbai", "delhi", "bengaluru", "bangalore", "pune", "hyderabad", "chennai", "kolkata", "ahmedabad", "jaipur", "chandigarh"), "91"),
    (("united arab emirates", "uae", "dubai", "abu dhabi", "sharjah", "ajman"), "971"),
    (("switzerland", "zurich", "zürich", "geneva", "genève", "basel", "bern", "lausanne", "lucerne", "luzern"), "41"),
    (("australia", "sydney", "melbourne", "brisbane", "perth", "adelaide", "canberra"), "61"),
    (("united kingdom", "england", "london", "manchester", "birmingham", "scotland"), "44"),
    (("canada", "toronto", "vancouver", "montreal"), "1"),
    (("united states", "usa"), "1"),
]
US_STATE_RE = re.compile(r",\s*(A[LKZR]|C[AOT]|D[EC]|FL|GA|HI|I[DLNA]|K[SY]|LA|M[EDAINSOT]|N[EVHJMYCD]|O[HKR]|PA|RI|S[CD]|T[NX]|UT|V[TA]|W[AVIY])\b")


def country_code_for(city: str) -> Optional[str]:
    low = (city or "").lower()
    for words, code in COUNTRY_CODES:
        if any(w in low for w in words):
            return code
    if US_STATE_RE.search(city or ""):
        return "1"
    return None


def phone_digits_international(phone: str, city: Optional[str] = None) -> Optional[str]:
    """Digits with country code, or None when the country cannot be known."""
    raw = (phone or "").strip()
    digits = re.sub(r"\D", "", raw)
    if raw.startswith("+") and len(digits) >= 8:
        return digits
    if raw.startswith("00") and len(digits) >= 10:
        return digits[2:]
    code = country_code_for(city or "")
    if code and len(digits) >= 7:
        if digits.startswith(code) and len(digits) > len(code) + 7:
            return digits  # already includes the code, just without "+"
        return code + digits.lstrip("0")  # drop the national trunk prefix
    return None


def whatsapp_link(phone: str, text: str = "", city: Optional[str] = None) -> Optional[str]:
    digits = phone_digits_international(phone, city)
    if not digits:
        return None
    url = f"https://wa.me/{digits}"
    if text:
        url += "?text=" + urllib.parse.quote(text, safe="")
    return url


def mailto_link(email: str, subject: str = "", body: str = "") -> Optional[str]:
    if not email or "@" not in email:
        return None
    params = {}
    if subject:
        params["subject"] = subject
    if body:
        params["body"] = body
    query = urllib.parse.urlencode(params, quote_via=urllib.parse.quote)
    return f"mailto:{email}" + (f"?{query}" if query else "")


def compose_link(email: str, subject: str = "", body: str = "") -> Optional[str]:
    """
    Opens a new email with the address, subject and message filled in. Gmail compose in the
    browser by default, because a plain mailto: link does nothing when no mail app is set up.
    EMAIL_COMPOSE=mailto switches back to the desktop mail app.
    """
    if not email or "@" not in email:
        return None
    from config.settings import settings
    if settings.EMAIL_COMPOSE == "mailto":
        return mailto_link(email, subject, body)
    params = {"view": "cm", "fs": "1", "to": email}
    if settings.GMAIL_ACCOUNT:
        params["authuser"] = settings.GMAIL_ACCOUNT
    if subject:
        params["su"] = subject
    if body:
        params["body"] = body
    return "https://mail.google.com/mail/?" + urllib.parse.urlencode(params, quote_via=urllib.parse.quote)


def tel_link(phone: str) -> Optional[str]:
    cleaned = re.sub(r"[^\d+]", "", phone or "")
    return f"tel:{cleaned}" if len(cleaned) >= 6 else None


def instagram_profile(socials) -> Optional[str]:
    for url in socials or []:
        if "instagram.com/" in url.lower():
            return url
    return None


def best_channel(p: dict) -> str:
    """Suggested first channel for a prospect."""
    if phone_digits_international(p.get("phone") or "", p.get("city")):
        return "whatsapp"
    if p.get("email"):
        return "email"
    if instagram_profile(p.get("socials")):
        return "instagram"
    if p.get("phone"):
        return "phone"
    return "none"
