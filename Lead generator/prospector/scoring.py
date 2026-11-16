"""
Turns a business + website audit into a lead tier and a 0-100 heat score.
Higher heat = clearer need for a new website = contact first.
"""

import time
import urllib.parse
from typing import Optional, Tuple, List

from config.settings import settings
from .site_audit import SiteAudit
from .sources import Business

TIER_LABELS = {
    "no_website": "No website",
    "no_website_unverified": "No website on OpenStreetMap (verify on Google first)",
    "social_only": "Social page instead of a website",
    "broken_website": "Website is broken or down",
    "weak_website": "Weak website",
    "ok_website": "Website looks fine",
    "unchecked": "Site blocks automated checks",
    "closed": "Business closed",
}


def _established_bonus(reviews: int) -> int:
    """Businesses with many reviews are active and can usually pay."""
    if reviews >= 100:
        return 8
    if reviews >= 50:
        return 5
    if reviews >= 15:
        return 3
    return 0


def score_business(
    business: Business, audit: Optional[SiteAudit], current_year: Optional[int] = None
) -> Tuple[str, int, List[str]]:
    """Returns (tier, heat_score, issues)."""
    current_year = current_year or time.gmtime().tm_year
    reviews = business.review_count or 0
    bonus = _established_bonus(reviews)
    issues: List[str] = []

    if business.business_status in ("CLOSED_PERMANENTLY", "CLOSED_TEMPORARILY"):
        return "closed", 0, [f"Listing status: {business.business_status}"]

    # --- No website at all -------------------------------------------------
    if not business.website:
        if business.source == "google_places":
            line = "No website on its Google listing"
            if reviews:
                line += f" despite {reviews} reviews"
            issues.append(line)
            return "no_website", min(100, 85 + bonus), issues
        issues.append("No website listed on OpenStreetMap (check Google before calling)")
        reachable = business.phone or business.email or business.socials
        return "no_website_unverified", 55 if reachable else 45, issues

    if audit is None:
        return "unchecked", 0, ["Website not audited"]

    # --- Website field is not really a website -----------------------------
    if audit.kind == "social_only":
        issues.append(f"Google listing links to a {audit.platform} page instead of a website")
        return "social_only", min(100, 80 + bonus), issues

    if audit.kind == "dead_builder":
        issues.append(
            f"Website link is a {audit.platform}, which Google shut down in 2024, so visitors get redirected away"
        )
        return "broken_website", min(100, 85 + bonus), issues

    if audit.bot_protected:
        return "unchecked", 0, ["Site blocks automated checks; review it manually"]

    if not audit.reachable:
        if audit.status_code in (404, 410):
            issues.append("The website link on their listing leads to a 'page not found' error")
        else:
            issues.append(f"Website is down ({audit.error or 'no response'})")
        return "broken_website", min(100, 78 + bonus), issues

    # --- Weak website signals ----------------------------------------------
    points = 0
    host = urllib.parse.urlparse(audit.final_url or audit.url).netloc

    if audit.kind == "free_builder":
        points += 30
        issues.append(f"Runs on a free {audit.platform} address ({host}) instead of its own domain")

    if audit.ssl_error:
        points += 25
        issues.append("SSL certificate is broken, so browsers show a security warning")
    elif not audit.https:
        points += 25
        issues.append("No HTTPS, so browsers label the site 'Not secure'")

    if audit.has_viewport is False:
        points += 25
        issues.append("Not built for phones (no responsive viewport)")

    if audit.response_seconds is not None:
        if audit.response_seconds > 6:
            points += 20
            issues.append(f"Homepage took {audit.response_seconds:.1f}s to load")
        elif audit.response_seconds > 3:
            points += 10
            issues.append(f"Homepage took {audit.response_seconds:.1f}s to load")

    if audit.pagespeed_mobile is not None:
        if audit.pagespeed_mobile < 30:
            points += 25
            issues.append(f"Google mobile speed score is {audit.pagespeed_mobile}/100")
        elif audit.pagespeed_mobile < 50:
            points += 15
            issues.append(f"Google mobile speed score is {audit.pagespeed_mobile}/100")

    if audit.copyright_year and audit.copyright_year <= current_year - 2:
        points += 20 if audit.copyright_year <= current_year - 4 else 15
        issues.append(f"Footer copyright still says {audit.copyright_year}")

    if audit.wordpress_version:
        try:
            if int(audit.wordpress_version.split(".")[0]) < 6:
                points += 10
                issues.append(f"Runs WordPress {audit.wordpress_version}, several major versions behind")
        except ValueError:
            pass

    if audit.uses_flash:
        points += 20
        issues.append("Uses Flash, which no modern browser can play")

    if audit.old_jquery:
        points += 5
        issues.append(f"Uses jQuery {audit.old_jquery}, a library version from before 2017")

    if not audit.title:
        points += 5
        issues.append("Homepage has no title tag")
    if not audit.meta_description:
        points += 5
        issues.append("No meta description, so the Google search snippet is weak")

    heat = min(100, points + (bonus if points else 0))
    tier = "weak_website" if heat >= settings.PROSPECT_MIN_SCORE else "ok_website"
    # A years-old or not mobile-friendly site is always an upgrade lead (the user's 2nd priority)
    from .priority import old_or_unresponsive
    if tier == "ok_website" and old_or_unresponsive(audit.to_dict())[0]:
        tier, heat = "weak_website", max(heat, settings.PROSPECT_MIN_SCORE)
    return tier, heat, issues
