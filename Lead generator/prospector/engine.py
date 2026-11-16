"""
Maps prospector orchestration:
search businesses -> skip known ones -> audit websites -> score -> save -> alert the hottest.
"""

import csv
import logging
import time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from typing import List, Optional, Dict, Any

from rich.console import Console

from config.settings import settings
from database.db import init_db
from database.prospect_repository import ProspectRepository
from brain.gemini_analyzer import GeminiAnalyzer, GeminiUnavailable
from delivery.telegram_bot import TelegramAlerter
from .sources import Business, SourceError, pick_source
from outreach.links import country_code_for
from .priority import old_or_unresponsive, compute as compute_priority
from .site_audit import audit_website, SiteAudit
from .scoring import score_business, TIER_LABELS

logger = logging.getLogger("prospector.engine")
console = Console()

AUDIT_WORKERS = 6


def _issue_phrase(issue: str) -> str:
    """Rewrites an audit finding as something you would say to the owner."""
    import re

    rules = [
        (r"^No HTTPS", lambda m: "browsers mark your site as 'Not secure' because it has no HTTPS"),
        (r"^SSL certificate is broken", lambda m: "your SSL certificate is broken, so visitors get a security warning"),
        (r"^Not built for phones", lambda m: "your site isn't set up for phones"),
        (r"^Homepage took ([\d.]+)s", lambda m: f"your homepage took {m.group(1)} seconds to load"),
        (r"^Google mobile speed score is (\d+)/100", lambda m: f"Google gives your site a mobile speed score of {m.group(1)}/100"),
        (r"^Footer copyright still says (\d{4})", lambda m: f"your footer still says {m.group(1)}"),
        (r"^Runs on a free (.+?) address", lambda m: f"your site runs on a free {m.group(1)} address instead of your own domain"),
        (r"^Runs WordPress ([\d.]+)", lambda m: f"your site runs WordPress {m.group(1)}, which is several versions behind"),
        (r"^Uses Flash", lambda m: "parts of your site use Flash, which no browser plays anymore"),
    ]
    for pattern, build in rules:
        m = re.search(pattern, issue)
        if m:
            return build(m)
    return issue[0].lower() + issue[1:] if issue else "a few things that cost you visitors"


def template_opener(p: Dict[str, Any]) -> str:
    """Plain fallback opener, used only when Gemini is unavailable. Always grounded in the data."""
    name = p["name"]
    niche = p.get("niche") or "business"
    city = (p.get("city") or "").split(",")[0]
    issues = p.get("issues") or []
    first_issue = issues[0] if issues else ""
    tier = p.get("tier")
    from outreach.messages import preview_line
    preview = preview_line(p)

    if tier == "no_website":
        reviews = p.get("review_count") or 0
        proof = f" with {reviews} reviews" if reviews else ""
        return (
            f"Hi {name} team, I came across your Google listing{proof} but couldn't find a website for you. "
            f"We build fast, simple sites for {niche} businesses in {city}. "
            + (preview if preview else "Would a free homepage preview be useful?")
        )
    if tier == "no_website_unverified":
        return (
            f"Hi {name} team, I was looking for {niche} businesses in {city} and couldn't find a website for you. "
            f"We build fast, simple sites for local businesses. "
            + (preview if preview else "Would a free homepage preview be useful?")
        )
    if tier == "social_only":
        return (
            f"Hi {name} team, I noticed your listing points to a social page rather than a website. "
            f"A simple site of your own would show up better on Google. "
            + (preview if preview else "Want me to send a free homepage preview?")
        )
    if tier == "broken_website":
        lowered = first_issue.lower()
        if "page not found" in lowered or "404" in lowered:
            detail = "the website link on your listing leads to a 'page not found' error"
        elif "shut down" in lowered:
            detail = "the website link on your listing points to a Google site that no longer exists"
        else:
            detail = "your website didn't load when I tried to visit it"
        return (
            f"Hi {name} team, quick heads-up: {detail}, so people searching for you hit a dead end. "
            + (preview if preview else "Happy to send over a short audit with the fix. Want me to?")
        )
    return (
        f"Hi {name} team, I had a look at your website and noticed {_issue_phrase(first_issue)}. "
        + (preview if preview else "I can send a free audit with the fixes. Want me to?")
    )


def _new_business_signal(b: Business, tier: str) -> tuple:
    """(True, reason) when a business looks new and has no website yet: a first-website lead."""
    if tier not in ("no_website", "no_website_unverified", "social_only"):
        return False, ""
    if b.business_status == "FUTURE_OPENING":
        return True, "Opening soon on Google Maps, no website yet"
    if b.source == "google_places" and (b.review_count or 0) < settings.NEW_BUSINESS_MAX_REVIEWS:
        reviews = b.review_count or 0
        return True, f"Looks like a new business ({reviews} Google review{'s' if reviews != 1 else ''}), no website yet"
    if b.map_added_recently:
        return True, "Added to the map in the last year, likely a new business"
    return False, ""


def _preview_link(p: Dict[str, Any]) -> Optional[str]:
    from outreach.messages import demo_url, audit_url
    if p.get("tier") in ("no_website", "no_website_unverified", "social_only"):
        return demo_url(p)
    return audit_url(p)


class ProspectEngine:

    def __init__(self, source: Optional[str] = None):
        init_db()
        self.source = pick_source(source)
        self.gemini = GeminiAnalyzer()
        self.telegram = TelegramAlerter()

    # ------------------------------------------------------------------ run

    def run(
        self,
        niches: Optional[List[str]] = None,
        cities: Optional[List[str]] = None,
        max_searches: Optional[int] = None,
        alert: bool = True,
    ) -> Dict[str, Any]:
        explicit = bool(niches or cities)
        niches = niches or settings.PROSPECT_NICHES
        cities = cities or settings.PROSPECT_CITIES
        limit = max_searches or settings.PROSPECT_MAX_SEARCHES_PER_RUN

        if explicit:
            searches = [(n, c) for c in cities for n in niches][:limit]
        else:
            searches = ProspectRepository.get_due_searches(
                self.source.name, niches, cities, settings.PROSPECT_RERUN_DAYS, limit
            )

        label = "Google Places" if self.source.name == "google_places" else "OpenStreetMap (free, verify leads)"
        console.print(f"[bold cyan]🗺  Maps Prospector[/bold cyan] [dim]source: {label}[/dim]")
        if self.source.name == "google_places":
            console.print(f"[dim]Places calls left this month: {self.source.remaining_budget()}[/dim]")
        if not searches:
            console.print(
                f"[yellow]Nothing due. Every niche + city was searched in the last "
                f"{settings.PROSPECT_RERUN_DAYS} days. Add niches/cities or pass --niche/--city.[/yellow]"
            )

        totals = {"searches": 0, "found": 0, "new": 0, "hot": 0, "failed": 0}
        for niche, city in searches:
            try:
                businesses = self.source.search(niche, city)
            except SourceError as e:
                console.print(f"[red]  ✗ {niche} in {city}: {e}[/red]")
                totals["failed"] += 1
                if "limit" in str(e).lower():
                    break
                continue
            except Exception as e:
                console.print(f"[red]  ✗ {niche} in {city}: {type(e).__name__}: {e}[/red]")
                totals["failed"] += 1
                continue

            saved, hot = self._process(businesses, niche, city)
            ProspectRepository.record_search(self.source.name, niche, city, len(businesses), saved)
            totals["searches"] += 1
            totals["found"] += len(businesses)
            totals["new"] += saved
            totals["hot"] += hot
            console.print(
                f"  [green]✓[/green] {niche} in {city}: {len(businesses)} found, "
                f"{saved} new, [bold]{hot} worth pitching[/bold]"
            )
            time.sleep(1.0)

        console.print(
            f"\n[bold]Prospecting done:[/bold] {totals['searches']} searches, {totals['found']} businesses, "
            f"{totals['new']} new, [bold green]{totals['hot']} hot leads[/bold green]."
        )
        if alert:
            totals["alerted"] = self.dispatch()
        return totals

    def _process(self, businesses: List[Business], niche: str, city: str) -> tuple:
        fresh: List[Business] = []
        seen = set()
        for b in businesses:
            if not b.place_id or b.place_id in seen:
                continue
            seen.add(b.place_id)
            if ProspectRepository.exists(b.source, b.place_id):
                continue
            # Few reviews only rules out businesses WITH a site; without one it signals a new business
            if b.source == "google_places" and b.website and (b.review_count or 0) < settings.PROSPECT_MIN_REVIEWS:
                continue
            fresh.append(b)

        with_site = [b for b in fresh if b.website]
        audits: Dict[str, SiteAudit] = {}
        if with_site:
            with ThreadPoolExecutor(max_workers=AUDIT_WORKERS) as pool:
                for b, audit in zip(with_site, pool.map(lambda x: audit_website(x.website), with_site)):
                    audits[b.place_id] = audit

        country_code = country_code_for(city)
        saved = hot = 0
        for b in fresh:
            audit = audits.get(b.place_id)
            tier, heat, issues = score_business(b, audit)
            new_business, why_new = _new_business_signal(b, tier)
            if new_business:
                issues = [why_new] + issues
            old_site = old_or_unresponsive(audit.to_dict() if audit else None)[0]
            # Contact order: no website > old / unresponsive site > rest, India first in each group
            priority = compute_priority(tier, heat, city, old_site, new_business)
            email = b.email or (audit.emails[0] if audit and audit.emails else "")
            socials = list(dict.fromkeys(b.socials + (audit.socials if audit else [])))
            row_id = ProspectRepository.save({
                "source": b.source,
                "place_id": b.place_id,
                "name": b.name,
                "niche": niche,
                "city": city,
                "address": b.address,
                "phone": b.phone,
                "email": email,
                "website": b.website,
                "socials": socials,
                "maps_url": b.maps_url,
                "rating": b.rating,
                "review_count": b.review_count,
                "tier": tier,
                "heat_score": heat,
                "issues": issues,
                "audit": audit.to_dict() if audit else {},
                "status": "new" if tier not in ("ok_website", "unchecked", "closed") else "ignored",
                "country_code": country_code,
                "new_business": 1 if new_business else 0,
                "old_site": 1 if old_site else 0,
                "priority": priority,
            })
            if row_id:
                saved += 1
                if tier not in ("ok_website", "unchecked", "closed"):
                    hot += 1
        return saved, hot

    # ------------------------------------------------------------------ alerts

    def dispatch(self, limit: Optional[int] = None) -> int:
        """Sends the hottest waiting prospects to Telegram, within the daily card cap."""
        left_today = settings.PROSPECT_ALERTS_PER_DAY - ProspectRepository.alerted_today()
        limit = min(limit or settings.PROSPECT_ALERTS_PER_RUN, left_today)
        if limit <= 0:
            return 0
        prospects = ProspectRepository.get_alertable(limit)
        if not prospects:
            return 0
        if not self.telegram.is_configured():
            console.print("[yellow]Telegram not configured; leads saved. View them with `python main.py show-prospects`.[/yellow]")
            return 0

        gemini_ok = self.gemini.is_configured()
        sent = 0
        for p in prospects:
            if not p.get("opener"):
                opener, opener_source = None, "template"
                if gemini_ok:
                    try:
                        opener = self.gemini.write_prospect_opener(self._opener_context(p))
                        opener_source = "gemini"
                    except GeminiUnavailable as e:
                        console.print(f"[yellow]Gemini unavailable ({e}); using template openers for the rest of this run.[/yellow]")
                        gemini_ok = False
                    except ValueError as e:
                        logger.warning(f"Opener for prospect #{p['id']} failed: {e}")
                opener = opener or template_opener(p)
                ProspectRepository.set_opener(p["id"], opener, opener_source)
                p["opener"], p["opener_source"] = opener, opener_source

            if self.telegram.send_prospect_alert(p):
                ProspectRepository.set_status(p["id"], "alerted")
                sent += 1
            else:
                console.print("[yellow]Telegram did not accept the card; the rest wait for the next retry.[/yellow]")
                break
            time.sleep(1.1)  # Telegram allows ~20 messages per minute in groups

        if sent:
            console.print(f"📲 Sent [bold green]{sent} prospect cards[/bold green] to Telegram.")
        return sent

    @staticmethod
    def _opener_context(p: Dict[str, Any]) -> Dict[str, Any]:
        rating = "not available"
        if p.get("rating"):
            rating = f"{p['rating']} stars from {p.get('review_count') or 0} reviews"
        return {
            "name": p["name"],
            "niche": p.get("niche") or "local business",
            "city": p.get("city") or "",
            "rating": rating,
            "tier_label": TIER_LABELS.get(p.get("tier"), p.get("tier")),
            "findings": "\n".join(f"- {i}" for i in (p.get("issues") or [])) or "- none",
            "preview_link": _preview_link(p) or "none",
        }

    # ------------------------------------------------------------------ export

    @staticmethod
    def export_csv(path: Path) -> int:
        rows = ProspectRepository.list(limit=100000)
        path.parent.mkdir(parents=True, exist_ok=True)
        columns = [
            "id", "heat_score", "tier", "status", "name", "niche", "city", "phone", "email",
            "website", "maps_url", "rating", "review_count", "address", "issues", "socials", "opener",
        ]
        with open(path, "w", newline="", encoding="utf-8-sig") as f:
            writer = csv.writer(f)
            writer.writerow(columns)
            for r in rows:
                writer.writerow([
                    "; ".join(r.get(c) or []) if c in ("issues", "socials") else r.get(c, "")
                    for c in columns
                ])
        return len(rows)
