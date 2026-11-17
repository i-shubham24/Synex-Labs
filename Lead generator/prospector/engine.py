"""
Maps prospector orchestration:
search businesses -> skip known ones -> audit websites -> score -> save -> alert the hottest.
"""

import csv
import json
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
from .sources import Business, SourceError, pick_source, WEBSITE_GROUPS
from .history import domain_of, profile as site_profile, summarize as summarize_history
from outreach.links import country_code_for
from .priority import old_or_unresponsive, compute as compute_priority
from .filters import is_excluded
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
        (r"^Website not updated since (\d{4})", lambda m: f"your website has not been updated since {m.group(1)}"),
        (r"^Design looks dated", lambda m: "the design looks dated next to newer sites"),
        (r"^No meta description", lambda m: "your site has no proper description for Google search results"),
        (r"^Homepage has no title", lambda m: "your homepage has no proper title for Google"),
        (r"^Uses jQuery ([\d.]+)", lambda m: "parts of the site use very old code that modern browsers struggle with"),
    ]
    for pattern, build in rules:
        m = re.search(pattern, issue)
        if m:
            return build(m)
    return issue[0].lower() + issue[1:] if issue else "a few things that cost you visitors"


STUDIO_INTRO = (
    "We are Synex Labs, a web studio from India building modern websites and IT solutions "
    "for businesses worldwide: {site}"
)


def template_opener(p: Dict[str, Any]) -> str:
    """
    Short first message (about 60 words): one sentence on what we found, who we are with our
    website, what we can do (website, Google presence, SEO) and one question. No phone number.
    Used whenever Gemini does not write the opener. Always grounded in the data.
    """
    name = p["name"]
    city = (p.get("city") or "").split(",")[0].strip()
    customers = f"more relevant customers in {city}" if city else "more relevant customers"
    issues = p.get("issues") or []
    tier = p.get("tier")
    intro = STUDIO_INTRO.format(site=settings.SITE_URL + "/")
    sign = f"Regards,\n{settings.EMAIL_SIGNATURE_NAME}"

    if tier in ("no_website", "no_website_unverified"):
        if tier == "no_website" and p.get("rating"):
            found = f"We found {name} on Google Maps ({p['rating']} stars) but could not find a website for you."
        else:
            found = f"We looked for {name} online and could not find a website for you."
        offer = f"We can build your website and set up your Google presence with SEO, so {customers} find you."

    elif tier == "social_only":
        found = (
            f"We looked into {name} online and your Google listing points to a social media page, "
            f"not a website of your own."
        )
        offer = f"We can build your own website and improve your Google presence with SEO, so {customers} find you."

    elif tier == "broken_website":
        first = issues[0].lower() if issues else ""
        if "page not found" in first or "404" in first:
            detail = "the link on your Google listing leads to a 'page not found' error"
        elif "shut down" in first:
            detail = "the link on your listing points to a Google site that no longer exists"
        else:
            detail = "it did not load when we tried to open it"
        found = f"We looked into your website and {detail}, so customers searching for you hit a dead end."
        offer = f"We can fix or rebuild your website and improve your Google presence with SEO, so {customers} find you."

    else:
        # Old, slow or weak website: the upgrade pitch, with the top one or two real findings
        findings = [
            _issue_phrase(i) for i in issues
            if not i.startswith("Online since") and not i.startswith("Looks like a new")
        ][:2]
        if findings:
            found = f"We looked into your website and noticed that {', and '.join(findings)}."
        else:
            found = "We looked into your website and found a few things that make it harder for customers to reach you."
        offer = f"We can upgrade your website and your Google presence with SEO, so {customers} find you."

    return f"Hi {name} team,\n\n{found}\n\n{intro}\n\n{offer} Would you like to proceed?\n\n{sign}"


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


def _spread_by_niche(candidates: List[Dict[str, Any]], limit: int) -> List[Dict[str, Any]]:
    """
    Keeps priority order but lets each niche take at most a few of the slots, so a
    batch of cards covers many kinds of business instead of one.
    """
    cap = max(2, -(-limit // 5))  # ceil(limit / 5), at least 2
    picked, per_niche, overflow = [], {}, []
    for p in candidates:
        n = p.get("niche") or ""
        if per_niche.get(n, 0) < cap:
            per_niche[n] = per_niche.get(n, 0) + 1
            picked.append(p)
        else:
            overflow.append(p)
        if len(picked) >= limit:
            break
    # Few niches available: fill the rest in priority order
    picked += overflow[: max(0, limit - len(picked))]
    return picked[:limit]


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
        niches = niches or list(settings.PROSPECT_NICHES)
        if not explicit and self.source.name == "osm":
            # Old-website hunt: "businesses with a website" searches lead the rotation, then niches
            niches = [g for g in WEBSITE_GROUPS if g not in niches] + niches
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
            if is_excluded(b.name, b.niche or niche):
                continue  # government, embassy, tax office or real estate: not our clients
            # Few reviews only rules out businesses WITH a site; without one it signals a new business
            if b.source == "google_places" and b.website and (b.review_count or 0) < settings.PROSPECT_MIN_REVIEWS:
                continue
            fresh.append(b)

        # One business per website domain: many branches sharing a site are a chain, not a client
        domains, unique = set(), []
        for b in fresh:
            d = domain_of(b.website) if b.website else None
            if d and d in domains:
                continue
            if d:
                domains.add(d)
            unique.append(b)
        fresh = unique

        with_site = [b for b in fresh if b.website]
        audits: Dict[str, SiteAudit] = {}
        if with_site:
            with ThreadPoolExecutor(max_workers=AUDIT_WORKERS) as pool:
                for b, audit in zip(with_site, pool.map(lambda x: audit_website(x.website), with_site)):
                    audits[b.place_id] = audit

        # Site age, last update and traffic signals (Internet Archive, optional Chrome UX Report).
        # Most suspicious-looking sites first, capped per search to stay polite and quick.
        histories = self._histories(with_site, audits)

        country_code = country_code_for(city)
        saved = hot = 0
        year = time.gmtime().tm_year
        for b in fresh:
            audit = audits.get(b.place_id)
            tier, heat, issues = score_business(b, audit)
            new_business, why_new = _new_business_signal(b, tier)
            if new_business:
                issues = [why_new] + issues
            hist = histories.get(b.place_id) or {}
            old_site, why_old = old_or_unresponsive(audit.to_dict() if audit else None, None, hist.get("last_update"))
            if old_site and tier == "ok_website":
                tier, heat = "weak_website", max(heat, settings.PROSPECT_MIN_SCORE)
            if hist.get("last_update") and hist["last_update"] <= year - 3:
                issues.insert(0, f"Website not updated since {hist['last_update']} (Internet Archive)")
            if hist.get("since") and hist["since"] <= year - 5:
                issues.append(f"Online since {hist['since']}, so the business has been around a while")
            # Contact order: no website > old / unresponsive site > rest, India first in each group
            email = b.email or (audit.emails[0] if audit and audit.emails else "")
            contactable = bool(b.phone or email or b.socials or (audit.socials if audit else []))
            old5 = bool(hist.get("old5")) or bool(hist.get("since") and hist["since"] <= year - 5 and old_site)
            if hist:
                hist["old5"] = old5
            priority = compute_priority(tier, heat, city, old_site, new_business, contactable,
                                        old5, bool(hist.get("established")))
            socials = list(dict.fromkeys(b.socials + (audit.socials if audit else [])))
            row_id = ProspectRepository.save({
                "source": b.source,
                "place_id": b.place_id,
                "name": b.name,
                "niche": b.niche or niche,
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
                if hist:
                    ProspectRepository.update(
                        row_id,
                        site_since=hist.get("since"),
                        last_update_year=hist.get("last_update"),
                        old5=1 if hist.get("old5") else 0,
                        established=1 if hist.get("established") else 0,
                        traffic_note=hist.get("traffic_note") or None,
                    )
                if tier not in ("ok_website", "unchecked", "closed"):
                    hot += 1
        return saved, hot

    @staticmethod
    def backfill_history(limit: Optional[int] = None) -> Dict[str, int]:
        """
        Checks age / last update / traffic for saved websites that were never checked
        (Indian ones first), then re-ranks them. Runs on a schedule in small batches.
        """
        from database.db import get_connection
        from .priority import reprioritize

        limit = limit or settings.HISTORY_CHECKS_PER_SEARCH
        with get_connection() as conn:
            rows = conn.execute(
                """SELECT id, website, review_count, issues FROM prospects
                   WHERE website LIKE 'http%' AND site_since IS NULL
                     AND tier IN ('weak_website','ok_website') AND status IN ('new','alerted','ignored')
                   ORDER BY (city LIKE '%India%') DESC, priority DESC, id ASC LIMIT ?;""",
                (limit,),
            ).fetchall()
        year = time.gmtime().tm_year
        checked, old5, established, ids = 0, 0, 0, []
        for r in rows:
            data = site_profile(r["website"])
            if not data:
                continue  # archive unreachable: retried on the next run
            hist = summarize_history(data, r["review_count"])
            try:
                issues = json.loads(r["issues"] or "[]")
            except (TypeError, json.JSONDecodeError):
                issues = []
            if hist["last_update"] and hist["last_update"] <= year - 3:
                line = f"Website not updated since {hist['last_update']} (Internet Archive)"
                if line not in issues:
                    issues.insert(0, line)
            if hist["since"] and hist["since"] <= year - 5:
                line = f"Online since {hist['since']}, so the business has been around a while"
                if line not in issues:
                    issues.append(line)
            ProspectRepository.update(
                r["id"],
                site_since=hist["since"] or 0,  # 0 = checked, not in the archive
                last_update_year=hist["last_update"],
                old5=1 if hist["old5"] else 0,
                established=1 if hist["established"] else 0,
                traffic_note=hist["traffic_note"] or None,
                issues=issues,
            )
            ids.append(r["id"])
            checked += 1
            old5 += 1 if hist["old5"] else 0
            established += 1 if hist["established"] else 0
        if ids:
            reprioritize(ids)
        return {"checked": checked, "old_5_years": old5, "established": established, "left": max(0, len(rows) - checked)}

    @staticmethod
    def _histories(with_site: List[Business], audits: Dict[str, SiteAudit]) -> Dict[str, Dict[str, Any]]:
        year = time.gmtime().tm_year

        def suspicion(b: Business) -> int:
            a = audits.get(b.place_id)
            if not a or not a.reachable or a.bot_protected or a.kind == "social_only":
                return -1
            score = 0
            if old_or_unresponsive(a.to_dict())[0]:
                score += 3
            if not a.https:
                score += 2
            if a.copyright_year and a.copyright_year <= year - 3:
                score += 2
            if a.old_jquery or a.wordpress_version:
                score += 1
            return score

        ranked = sorted((b for b in with_site if suspicion(b) >= 0), key=suspicion, reverse=True)
        out: Dict[str, Dict[str, Any]] = {}
        for b in ranked[: settings.HISTORY_CHECKS_PER_SEARCH]:
            data = site_profile(b.website)
            if data:
                out[b.place_id] = summarize_history(data, b.review_count)
        return out

    # ------------------------------------------------------------------ alerts

    def dispatch(self, limit: Optional[int] = None) -> int:
        """Sends the hottest waiting prospects to Telegram, within the daily card cap."""
        left_today = settings.PROSPECT_ALERTS_PER_DAY - ProspectRepository.alerted_today()
        limit = min(limit or settings.PROSPECT_ALERTS_PER_RUN, left_today)
        if limit <= 0:
            return 0
        prospects = _spread_by_niche(ProspectRepository.get_alertable(limit * 8), limit)
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
            "site": settings.SITE_URL + "/",
            "signature": settings.EMAIL_SIGNATURE_NAME,
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
