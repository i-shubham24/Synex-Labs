"""
Who to contact first. The user's order:
  1. Businesses with NO website at all (a Facebook/Instagram page counts as none). India first.
  2. Businesses with years-old, unresponsive (not mobile-friendly) websites to upgrade.
  3. Everything else (broken links, slow but modern sites).
Heat stays the strength of the evidence; priority decides the order.
"""

import json
import time
from typing import Dict, Any, Optional, Tuple, List

from config.settings import settings
from outreach.links import country_code_for
from .filters import is_excluded

CATEGORY = {
    # key: (base priority, short label, group)
    "no_website": (400, "No website", "first"),
    "social_only": (400, "No website (social page only)", "first"),
    "no_website_unverified": (300, "No website (verify on Google)", "first"),
    "old_site": (200, "Old website to upgrade", "upgrade"),
    "broken_website": (120, "Broken website", "other"),
    "weak_website": (100, "Weak website", "other"),
}


def old_or_unresponsive(audit: Optional[Dict[str, Any]], visual: Optional[Dict[str, Any]] = None,
                        last_update: Optional[int] = None) -> Tuple[bool, str]:
    """True when a working website is clearly years old or not built for phones."""
    if not audit or not audit.get("reachable") or audit.get("bot_protected"):
        return False, ""
    if last_update and last_update <= time.gmtime().tm_year - 4:
        return True, f"Website not updated since {last_update} (Internet Archive)"
    if audit.get("has_viewport") is False:
        return True, "Not built for phones (no responsive layout)"
    year = audit.get("copyright_year")
    if year and year <= time.gmtime().tm_year - 4:
        return True, f"Footer copyright still says {year}"
    if audit.get("uses_flash"):
        return True, "Uses Flash, which no modern browser can play"
    wp = audit.get("wordpress_version") or ""
    if wp[:1].isdigit() and int(wp.split(".")[0]) < 5:
        return True, f"Runs WordPress {wp}, several major versions behind"
    if visual and int(visual.get("dated_score") or 0) >= 8:  # design score alone varies between runs
        return True, "Design looks dated next to modern sites (visual check)"
    return False, ""


def category_key(tier: str, old_site: bool) -> Optional[str]:
    if tier in ("no_website", "social_only", "no_website_unverified", "broken_website"):
        return tier
    if tier == "weak_website":
        return "old_site" if old_site else "weak_website"
    return None


def compute(tier: str, heat: int, city: str, old_site: bool, new_business: bool, contactable: bool = False,
            old5: bool = False, established: bool = False) -> int:
    key = category_key(tier, old_site)
    if not key:
        return 0
    base = CATEGORY[key][0]
    india = country_code_for(city or "") == settings.PRIORITY_COUNTRY_CODE
    # Reachable leads (phone, email or social page) first: you can only pitch who you can contact
    bonus = ((settings.PRIORITY_BOOST if india else 0) + (15 if contactable else 0)
             + (settings.NEW_BUSINESS_BOOST if new_business else 0) + int(heat or 0) // 10)
    if key == "old_site":
        # 5+ year old sites that still get visitors are the best upgrade clients
        bonus += (15 if old5 else 0) + (20 if established else 0)
    return base + min(bonus, 99)  # never jump into a higher group


def label(tier: str, old_site: bool) -> Tuple[str, str]:
    """(label, group) for display: group is first | upgrade | other | none."""
    key = category_key(tier, old_site)
    if not key:
        return "", "none"
    _, text, group = CATEGORY[key]
    return text, group


def reprioritize(prospect_ids: Optional[List[int]] = None) -> Dict[str, int]:
    """
    Recomputes old_site + priority (and promotes 'fine' sites that are really old or
    not mobile-friendly to upgrade leads). Runs at startup for existing rows and after visual checks.
    """
    from database.db import get_connection

    where, params = "", ()
    if prospect_ids:
        where = f"WHERE id IN ({','.join('?' for _ in prospect_ids)})"
        params = tuple(prospect_ids)
    promoted = updated = set_aside = 0
    with get_connection() as conn:
        rows = conn.execute(
            f"""SELECT id, name, niche, phone, email, socials, tier, heat_score, city, audit_json, visual_json, new_business, status, issues,
                       last_update_year, old5, established, site_since
                FROM prospects {where};""",
            params,
        ).fetchall()
        for r in rows:
            try:
                audit = json.loads(r["audit_json"] or "{}")
                visual = json.loads(r["visual_json"] or "null")
                issues = json.loads(r["issues"] or "[]")
            except (TypeError, json.JSONDecodeError):
                audit, visual, issues = {}, None, []
            tier, heat, status = r["tier"], int(r["heat_score"] or 0), r["status"]
            old, reason = old_or_unresponsive(audit, visual, r["last_update_year"])
            if old and tier == "ok_website":
                tier, heat = "weak_website", max(heat, settings.PROSPECT_MIN_SCORE)
                if reason and reason not in issues:
                    issues.insert(0, reason)
                if status == "ignored":
                    status = "new"
                promoted += 1
            contactable = bool(r["phone"] or r["email"] or (r["socials"] or "[]") != "[]")
            # 5+ years old = online 5+ years per the archive AND outdated (old design or untouched)
            old5 = bool(r["old5"]) or bool(r["site_since"] and r["site_since"] <= time.gmtime().tm_year - 5 and old)
            priority = compute(tier, heat, r["city"], old, bool(r["new_business"]), contactable,
                               old5, bool(r["established"]))
            if is_excluded(r["name"], r["niche"]):
                priority = 0  # government, embassy, tax office or real estate: not our clients
                if status in ("new", "alerted"):
                    status = "ignored"
                    set_aside += 1
            conn.execute(
                """UPDATE prospects SET tier = ?, heat_score = ?, status = ?, issues = ?, old_site = ?, priority = ?,
                          old5 = ? WHERE id = ?;""",
                (tier, heat, status, json.dumps(issues), 1 if old else 0, priority, 1 if old5 else 0, r["id"]),
            )
            updated += 1
        conn.commit()
    return {"updated": updated, "promoted": promoted, "public_set_aside": set_aside}
