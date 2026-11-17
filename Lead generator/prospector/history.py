"""
How old a website is, when it last changed, and whether it gets real visitors.

- Internet Archive (free, no key): one CDX request per site gives one capture per
  month across the site's whole history. From that: the year it first appeared,
  the last month its homepage content changed, and how many of the last 24 months
  it was captured (busy, well-linked sites get captured far more often).
- Chrome UX Report (optional, free Google API key): if Google lists the site, it has
  enough real Chrome visitors to be measured. That is the closest free signal to
  "has traffic". Without a key this check is skipped.

Results are cached per domain for 30 days.
"""

import json
import logging
import threading
import time
import urllib.parse
from datetime import datetime, timezone
from typing import Dict, Any, Optional

import requests

from config.settings import settings
from database.db import get_connection

logger = logging.getLogger("prospector.history")

CDX = "http://web.archive.org/cdx/search/cdx"
CRUX = "https://chromeuxreport.googleapis.com/v1/records:queryRecord"
HEADERS = {"User-Agent": "SynexLabsLeadEngine/1.0 (python-requests)"}
CACHE_DAYS = 30
_pace_lock = threading.Lock()
_last_call = [0.0]


def domain_of(url: str) -> str:
    host = urllib.parse.urlparse(url if "://" in url else "https://" + url).netloc.lower()
    host = host.split("@")[-1].split(":")[0]
    return host[4:] if host.startswith("www.") else host


def _pace(seconds: float = 1.0):
    with _pace_lock:
        wait = seconds - (time.monotonic() - _last_call[0])
        if wait > 0:
            time.sleep(wait)
        _last_call[0] = time.monotonic()


def _cached(domain: str) -> Optional[Dict[str, Any]]:
    with get_connection() as conn:
        row = conn.execute("SELECT data, checked_at FROM site_history WHERE domain = ?;", (domain,)).fetchone()
    if not row:
        return None
    try:
        checked = datetime.strptime(row["checked_at"], "%Y-%m-%d %H:%M:%S").replace(tzinfo=timezone.utc)
        if (datetime.now(timezone.utc) - checked).days > CACHE_DAYS:
            return None
        return json.loads(row["data"])
    except (ValueError, TypeError, json.JSONDecodeError):
        return None


def _store(domain: str, data: Dict[str, Any]):
    with get_connection() as conn:
        conn.execute(
            "INSERT OR REPLACE INTO site_history (domain, data, checked_at) VALUES (?, ?, ?);",
            (domain, json.dumps(data), datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S")),
        )
        conn.commit()


def wayback(domain: str) -> Dict[str, Any]:
    """first_year, last_change (YYYY-MM), active_months_24 (0-24), months (captures used)."""
    _pace(1.0)
    resp = requests.get(
        CDX,
        params={
            "url": domain + "/",
            "output": "json",
            "fl": "timestamp,digest",
            "filter": "statuscode:200",
            "collapse": "timestamp:6",   # one capture per month
        },
        headers=HEADERS,
        timeout=45,
    )
    if resp.status_code != 200:
        raise RuntimeError(f"Internet Archive HTTP {resp.status_code}")
    rows = resp.json()[1:] if resp.text.strip() else []
    if not rows:
        return {"first_year": None, "last_change": None, "active_months_24": 0, "months": 0}
    first_year = int(rows[0][0][:4])
    last_change = rows[0][0][:6]
    for prev, cur in zip(rows, rows[1:]):
        if cur[1] != prev[1]:
            last_change = cur[0][:6]
    now = datetime.now(timezone.utc)
    cutoff = f"{now.year - 2}{now.month:02d}"
    active = sum(1 for r in rows if r[0][:6] >= cutoff)
    return {
        "first_year": first_year,
        "last_change": f"{last_change[:4]}-{last_change[4:6]}",
        "active_months_24": min(24, active),
        "months": len(rows),
    }


def crux(origin: str, key: str) -> Optional[Dict[str, Any]]:
    """Chrome UX Report: listed=True means enough real visitors to be measured. None = not checked."""
    try:
        resp = requests.post(f"{CRUX}?key={key}", json={"origin": origin}, timeout=20)
    except requests.RequestException:
        return None
    if resp.status_code == 404:
        return {"listed": False}
    if not resp.ok:
        return None
    metrics = resp.json().get("record", {}).get("metrics", {})
    lcp = metrics.get("largest_contentful_paint", {}).get("percentiles", {}).get("p75")
    return {"listed": True, "lcp_ms": int(lcp) if lcp else None}


def profile(url: str) -> Dict[str, Any]:
    """Age, staleness and traffic signals for one website (cached)."""
    domain = domain_of(url)
    if not domain:
        return {}
    cached = _cached(domain)
    if cached is not None:
        return cached
    data: Dict[str, Any] = {"domain": domain}
    try:
        data.update(wayback(domain))
    except Exception as e:
        logger.info(f"Internet Archive lookup failed for {domain}: {e}")
        return {}  # not cached, so it is retried next time
    key = settings.GOOGLE_PAGESPEED_API_KEY
    if key:
        scheme = urllib.parse.urlparse(url).scheme or "https"
        host = urllib.parse.urlparse(url if "://" in url else "https://" + url).netloc
        result = crux(f"{scheme}://{host}", key)
        if result is not None:
            data["crux"] = result
    _store(domain, data)
    return data


def summarize(data: Dict[str, Any], review_count: Optional[int] = None) -> Dict[str, Any]:
    """
    Turns raw signals into what the ranking uses:
      since: first year online; last_update: year the homepage last changed;
      old5: online 5+ years and not refreshed for 3+ years;
      established: real visitors per Google (CrUX), or steady archive captures, or many reviews.
    """
    year = datetime.now(timezone.utc).year
    since = data.get("first_year")
    last_update = int(data["last_change"][:4]) if data.get("last_change") else None
    old5 = bool(since and since <= year - 5 and last_update and last_update <= year - 3)
    crux_listed = (data.get("crux") or {}).get("listed")
    established = bool(
        crux_listed
        or (data.get("active_months_24") or 0) >= 6
        or (review_count or 0) >= 30
    )
    if crux_listed is True:
        note = "Gets enough real visitors to appear in Google's Chrome data"
    elif (data.get("active_months_24") or 0) >= 6:
        note = f"Captured by the Internet Archive in {data['active_months_24']} of the last 24 months"
    elif (review_count or 0) >= 30:
        note = f"{review_count} Google reviews"
    else:
        note = ""
    return {"since": since, "last_update": last_update, "old5": old5, "established": established, "traffic_note": note}
