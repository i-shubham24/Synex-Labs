"""
Lightweight website audit for prospect scoring.

Runs with plain HTTP requests (no browser, low RAM). When a Google API key is set,
it also asks PageSpeed Insights for the mobile performance score.
"""

import logging
import re
import time
import urllib.parse
from dataclasses import dataclass, field, asdict
from typing import List, Optional, Dict, Any

import requests

from config.settings import settings

logger = logging.getLogger("prospector.audit")

MAX_HTML_BYTES = 2_000_000

BROWSER_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/130.0.0.0 Safari/537.36"
    ),
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.9",
}

# Website field points at a social profile instead of a real site
SOCIAL_HOSTS = {
    "facebook.com": "Facebook",
    "fb.com": "Facebook",
    "instagram.com": "Instagram",
    "linktr.ee": "Linktree",
    "wa.me": "WhatsApp",
    "whatsapp.com": "WhatsApp",
    "tiktok.com": "TikTok",
    "twitter.com": "X",
    "x.com": "X",
    "linkedin.com": "LinkedIn",
    "youtube.com": "YouTube",
    "yelp.com": "Yelp",
    "t.me": "Telegram",
    "beacons.ai": "Beacons",
    "taplink.cc": "Taplink",
    "linkin.bio": "Linkin.bio",
}

# Free builder subdomains: a site exists but looks amateur and has no own domain
FREE_BUILDER_SUFFIXES = {
    "wixsite.com": "Wix",
    "blogspot.com": "Blogger",
    "wordpress.com": "WordPress.com",
    "weebly.com": "Weebly",
    "godaddysites.com": "GoDaddy",
    "square.site": "Square",
    "mystrikingly.com": "Strikingly",
    "jimdosite.com": "Jimdo",
    "site123.me": "SITE123",
    "carrd.co": "Carrd",
    "yolasite.com": "Yola",
    "simplesite.com": "SimpleSite",
    "webnode.page": "Webnode",
    "ueniweb.com": "UENI",
    "sites.google.com": "Google Sites",
}

# Google shut down Business Profile websites (*.business.site) in 2024
DEAD_BUILDER_SUFFIXES = {"business.site": "Google Business Profile site"}

IGNORED_EMAIL_DOMAINS = (
    "example.com", "domain.com", "email.com", "yourdomain.com", "sentry.io",
    "wixpress.com", "sentry-next.wixpress.com", "godaddy.com", "squarespace.com",
)
IGNORED_EMAIL_TLDS = ("png", "jpg", "jpeg", "gif", "webp", "svg", "js", "css", "ico")


@dataclass
class SiteAudit:
    url: str
    kind: str = "website"              # website | social_only | free_builder | dead_builder
    platform: str = ""                 # e.g. 'Facebook', 'Wix'
    final_url: str = ""
    reachable: bool = False
    status_code: Optional[int] = None
    error: str = ""
    https: bool = False
    ssl_error: bool = False
    bot_protected: bool = False
    response_seconds: Optional[float] = None
    has_viewport: Optional[bool] = None
    title: str = ""
    meta_description: str = ""
    copyright_year: Optional[int] = None
    generator: str = ""
    wordpress_version: str = ""
    old_jquery: str = ""
    uses_flash: bool = False
    emails: List[str] = field(default_factory=list)
    socials: List[str] = field(default_factory=list)
    pagespeed_mobile: Optional[int] = None
    lcp_seconds: Optional[float] = None

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


def normalize_url(url: str) -> str:
    url = (url or "").strip()
    if url and not re.match(r"^https?://", url, re.I):
        url = "https://" + url.lstrip("/")
    return url


def _host(url: str) -> str:
    host = urllib.parse.urlparse(url).netloc.lower().split("@")[-1].split(":")[0]
    return host[4:] if host.startswith("www.") else host


def _matches(host: str, suffix: str) -> bool:
    return host == suffix or host.endswith("." + suffix)


def classify_url(url: str) -> tuple:
    """Returns (kind, platform) from the URL alone."""
    host = _host(url)
    path = urllib.parse.urlparse(url).path.lower()
    for suffix, name in SOCIAL_HOSTS.items():
        if _matches(host, suffix):
            return "social_only", name
    if host == "google.com" and path.startswith("/maps"):
        return "social_only", "Google Maps"
    for suffix, name in DEAD_BUILDER_SUFFIXES.items():
        if _matches(host, suffix):
            return "dead_builder", name
    for suffix, name in FREE_BUILDER_SUFFIXES.items():
        if _matches(host, suffix):
            return "free_builder", name
    return "website", ""


def _fetch(session: requests.Session, url: str):
    start = time.perf_counter()
    resp = session.get(url, headers=BROWSER_HEADERS, timeout=(8, 15), allow_redirects=True, stream=True)
    chunks, size = [], 0
    for chunk in resp.iter_content(65536):
        chunks.append(chunk)
        size += len(chunk)
        if size >= MAX_HTML_BYTES:
            break
    elapsed = time.perf_counter() - start
    resp.close()
    raw = b"".join(chunks)
    encoding = resp.encoding if resp.encoding and resp.encoding.lower() != "iso-8859-1" else "utf-8"
    return resp, raw.decode(encoding, errors="ignore"), elapsed


def _fetch_with_retry(session: requests.Session, url: str):
    """One retry on timeouts / refused connections so a network blip is not called 'broken'."""
    try:
        return _fetch(session, url)
    except requests.exceptions.SSLError:
        raise
    except (requests.exceptions.Timeout, requests.exceptions.ConnectionError) as e:
        if "NameResolution" in str(e) or "getaddrinfo" in str(e):
            raise
        time.sleep(2.0)
        return _fetch(session, url)


def _looks_bot_protected(resp: requests.Response, html: str) -> bool:
    if resp.status_code not in (403, 429, 503):
        return False
    server = resp.headers.get("server", "").lower()
    snippet = html[:5000].lower()
    markers = ("cf-chl", "just a moment", "attention required", "captcha", "access denied", "ddos-guard")
    return "cloudflare" in server or "sucuri" in server or any(m in snippet for m in markers) or resp.status_code == 403


def _first(pattern: str, html: str) -> str:
    m = re.search(pattern, html, re.I | re.S)
    return re.sub(r"\s+", " ", m.group(1)).strip() if m else ""


def _parse_html(audit: SiteAudit, html: str):
    audit.has_viewport = bool(re.search(r"<meta[^>]+name\s*=\s*[\"']?viewport", html, re.I))
    audit.title = _first(r"<title[^>]*>(.*?)</title>", html)[:200]
    audit.meta_description = (
        _first(r"<meta[^>]+name\s*=\s*[\"']description[\"'][^>]*content\s*=\s*[\"']([^\"']*)", html)
        or _first(r"<meta[^>]+content\s*=\s*[\"']([^\"']*)[\"'][^>]*name\s*=\s*[\"']description", html)
    )[:300]
    audit.generator = (
        _first(r"<meta[^>]+name\s*=\s*[\"']generator[\"'][^>]*content\s*=\s*[\"']([^\"']+)", html)
        or _first(r"<meta[^>]+content\s*=\s*[\"']([^\"']+)[\"'][^>]*name\s*=\s*[\"']generator", html)
    )[:120]
    wp = re.search(r"wordpress\s+(\d+\.\d+(?:\.\d+)?)", audit.generator, re.I)
    audit.wordpress_version = wp.group(1) if wp else ""

    current_year = time.gmtime().tm_year
    years = [
        int(y) for y in re.findall(
            r"(?:©|&copy;|&#169;|copyright)\s*(?:\d{4}\s*(?:-|–|&ndash;|to)\s*)?((?:19|20)\d{2})",
            html, re.I,
        )
    ]
    years = [y for y in years if 1995 <= y <= current_year]
    audit.copyright_year = max(years) if years else None

    jq = re.search(r"jquery[.-]?(1\.\d+(?:\.\d+)?)(?:\.min)?\.js", html, re.I)
    audit.old_jquery = jq.group(1) if jq else ""
    audit.uses_flash = bool(re.search(r"\.swf[\"'?]|shockwave-flash", html, re.I))

    emails = re.findall(r"mailto:([A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,})", html)
    emails += re.findall(r"\b([A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,})\b", html)
    clean = []
    for e in emails:
        e = urllib.parse.unquote(e).strip(".").lower()
        domain = e.split("@")[-1]
        if domain.endswith(IGNORED_EMAIL_DOMAINS) or domain.rsplit(".", 1)[-1] in IGNORED_EMAIL_TLDS:
            continue
        if e not in clean:
            clean.append(e)
    audit.emails = clean[:3]

    socials = []
    for href in re.findall(
        r"href\s*=\s*[\"'](https?://(?:www\.)?(?:facebook\.com|instagram\.com|linkedin\.com|tiktok\.com|x\.com|twitter\.com)/[^\"'#?\s]+)",
        html, re.I,
    ):
        if any(bad in href.lower() for bad in ("sharer", "/share", "intent/", "/plugins/", "/tr?", "/dialog/")):
            continue
        href = href.rstrip("/")
        if href not in socials:
            socials.append(href)
    audit.socials = socials[:4]


def _pagespeed(audit: SiteAudit, api_key: str):
    try:
        resp = requests.get(
            "https://www.googleapis.com/pagespeedonline/v5/runPagespeed",
            params={"url": audit.final_url, "strategy": "mobile", "category": "performance", "key": api_key},
            timeout=90.0,
        )
        if not resp.ok:
            logger.info(f"PageSpeed {resp.status_code} for {audit.final_url}")
            return
        lh = resp.json().get("lighthouseResult", {})
        score = lh.get("categories", {}).get("performance", {}).get("score")
        if score is not None:
            audit.pagespeed_mobile = int(round(score * 100))
        lcp = lh.get("audits", {}).get("largest-contentful-paint", {}).get("numericValue")
        if lcp:
            audit.lcp_seconds = round(lcp / 1000.0, 1)
    except Exception as e:
        logger.info(f"PageSpeed failed for {audit.final_url}: {e}")


def audit_website(url: str, pagespeed_key: Optional[str] = None) -> SiteAudit:
    """Audits one website. Never raises; problems are recorded on the result."""
    url = normalize_url(url)
    audit = SiteAudit(url=url)
    audit.kind, audit.platform = classify_url(url)
    if audit.kind == "social_only":
        return audit

    session = requests.Session()
    try:
        try:
            resp, html, elapsed = _fetch_with_retry(session, url)
        except requests.exceptions.SSLError:
            audit.ssl_error = True
            resp, html, elapsed = _fetch_with_retry(session, "http://" + url.split("://", 1)[1])

        audit.status_code = resp.status_code
        audit.final_url = resp.url
        audit.https = resp.url.lower().startswith("https://") and not audit.ssl_error
        audit.response_seconds = round(elapsed, 2)

        # A redirect can land on a social profile or a dead builder
        final_kind, final_platform = classify_url(resp.url)
        if final_kind in ("social_only", "dead_builder"):
            audit.kind, audit.platform = final_kind, final_platform
            audit.reachable = True
            return audit

        if _looks_bot_protected(resp, html):
            audit.bot_protected = True
            audit.reachable = True
            return audit

        audit.reachable = resp.status_code < 400
        if not audit.reachable:
            audit.error = f"HTTP {resp.status_code}"
            return audit

        _parse_html(audit, html)
    except requests.exceptions.Timeout:
        audit.error = "no response after two tries"
    except requests.exceptions.SSLError:
        audit.error = "SSL error and no plain HTTP fallback"
    except requests.exceptions.ConnectionError as e:
        text = str(e)
        audit.error = "domain does not resolve" if ("NameResolution" in text or "getaddrinfo" in text) else "server refused the connection"
    except Exception as e:
        audit.error = f"{type(e).__name__}"
    finally:
        session.close()

    key = pagespeed_key if pagespeed_key is not None else settings.GOOGLE_PAGESPEED_API_KEY
    if key and audit.reachable and audit.kind in ("website", "free_builder"):
        _pagespeed(audit, key)
    return audit
