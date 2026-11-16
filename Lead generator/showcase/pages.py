"""
Generates, publishes and live-checks the two showcase pages for a prospect:
  data/pages/<slug>/demo.html   concept homepage (every prospect)
  data/pages/<slug>/audit.html  website audit with screenshots (prospects with a site)

Publishing copies the folder to <site>/public/p/<slug>/. The links go live after
you deploy the site, and the engine notices on its own (live check).
"""

import json
import logging
import re
import secrets
import shutil
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, Any, List, Optional

import requests

from config.settings import settings, BASE_DIR
from database.prospect_repository import ProspectRepository
from brain.gemini_analyzer import GeminiAnalyzer, GeminiUnavailable
from brain.prompts import VISUAL_SYSTEM_INSTRUCTION, DEMO_COPY_SYSTEM_INSTRUCTION, DEMO_COPY_TEMPLATE
from .templates import render_demo, render_audit, fallback_copy

logger = logging.getLogger("showcase.pages")

PAGES_DIR = BASE_DIR / "data" / "pages"
SLUG_RE = re.compile(r"^[a-z0-9-]{4,80}$")


def _now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S")


def ensure_slug(p: Dict[str, Any]) -> str:
    if p.get("slug"):
        return p["slug"]
    base = re.sub(r"[^a-z0-9]+", "-", (p.get("name") or "business").lower()).strip("-")[:40] or "business"
    slug = f"{base}-{secrets.token_hex(3)}"  # unguessable enough for a private, noindex link
    ProspectRepository.update(p["id"], slug=slug)
    p["slug"] = slug
    return slug


def page_dir(slug: str) -> Path:
    if not SLUG_RE.match(slug or ""):
        raise ValueError("bad slug")
    return PAGES_DIR / slug


class PageBuilder:

    def __init__(self):
        self.gemini = GeminiAnalyzer()
        self._gemini_ok = self.gemini.is_configured()

    # ------------------------------------------------------------------ copy + visual

    def demo_copy(self, p: Dict[str, Any]) -> Dict[str, Any]:
        if self._gemini_ok:
            try:
                rating = f"{p['rating']} from {p.get('review_count') or 0} reviews" if p.get("rating") else "not available"
                data = self.gemini.generate_json(
                    DEMO_COPY_TEMPLATE.format(
                        name=p["name"], niche=p.get("niche") or "", city=p.get("city") or "",
                        rating=rating, address=p.get("address") or "not given",
                    ),
                    DEMO_COPY_SYSTEM_INSTRUCTION,
                )
                services = [s for s in data.get("services", []) if isinstance(s, dict) and s.get("title")]
                if data.get("headline") and len(services) >= 3:
                    data["services"] = services[:6]
                    return data
            except GeminiUnavailable as e:
                logger.info(f"Demo copy via template ({e})")
                self._gemini_ok = False
            except ValueError as e:
                logger.info(f"Demo copy via template ({e})")
        return fallback_copy(p)

    def visual_verdict(self, images: List[bytes]) -> Optional[Dict[str, Any]]:
        if not (self._gemini_ok and images):
            return None
        try:
            data = self.gemini.generate_json(
                "Desktop screenshot first, then mobile. Judge the design.", VISUAL_SYSTEM_INSTRUCTION, images=images
            )
            score = int(data.get("dated_score", 0))
            return {
                "dated_score": max(0, min(10, score)),
                "problems": [str(x) for x in (data.get("problems") or [])][:3],
                "positive": str(data.get("positive") or "")[:200],
            }
        except GeminiUnavailable as e:
            logger.info(f"Visual check skipped ({e})")
            self._gemini_ok = False
        except (ValueError, TypeError) as e:
            logger.info(f"Visual check skipped ({e})")
        return None

    # ------------------------------------------------------------------ build

    def build(self, p: Dict[str, Any], shots_session=None) -> Dict[str, Any]:
        """Builds the pages for one prospect. Returns what was produced."""
        slug = ensure_slug(p)
        out = page_dir(slug)
        out.mkdir(parents=True, exist_ok=True)
        made = {"slug": slug, "demo": False, "audit": False, "visual": None}

        try:
            audit = json.loads(p.get("audit_json") or _raw_audit(p["id"]) or "{}")
        except (TypeError, json.JSONDecodeError):
            audit = {}

        has_site = bool(p.get("website")) and p.get("tier") not in ("social_only", "no_website", "no_website_unverified")
        desktop = mobile = None
        if has_site and shots_session is not None:
            target = audit.get("final_url") or p["website"]
            desktop, mobile = shots_session.capture(target, out)

        visual = None
        if desktop or mobile:
            images = [f.read_bytes() for f in (desktop, mobile) if f]
            visual = self.visual_verdict(images)
            if visual:
                made["visual"] = visual
                self._apply_visual(p, visual)

        (out / "demo.html").write_text(render_demo(p, self.demo_copy(p)), encoding="utf-8")
        made["demo"] = True
        if has_site:
            (out / "audit.html").write_text(
                render_audit(p, audit, p.get("issues") or [], visual, bool(desktop), bool(mobile)), encoding="utf-8"
            )
            made["audit"] = True
        ProspectRepository.update(p["id"], pages_generated_at=_now(), visual_json=visual)
        from prospector.priority import reprioritize
        reprioritize([p["id"]])
        return made

    @staticmethod
    def _apply_visual(p: Dict[str, Any], visual: Dict[str, Any]):
        """A dated-looking site is a stronger lead, even when the technical checks pass."""
        if visual["dated_score"] < 7:
            return
        issues = list(p.get("issues") or [])
        line = "Design looks dated next to modern sites (visual check)"
        if line not in issues:
            issues.append(line)
        heat = min(100, int(p.get("heat_score") or 0) + 15 + (visual["dated_score"] - 7) * 5)
        fields = {"issues": issues, "heat_score": heat}
        if p.get("tier") == "ok_website" and heat >= settings.PROSPECT_MIN_SCORE:
            fields["tier"] = "weak_website"
            ProspectRepository.update(p["id"], **fields)
            if p.get("status") == "ignored":
                ProspectRepository.set_status(p["id"], "new")
        else:
            ProspectRepository.update(p["id"], **fields)
        p.update(fields)

    # ------------------------------------------------------------------ batch

    def build_many(self, prospects: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        results = []
        needs_shots = any(
            p.get("website") and p.get("tier") not in ("social_only", "no_website", "no_website_unverified")
            for p in prospects
        )
        session = None
        if needs_shots:
            try:
                from .screenshots import ScreenshotSession
                session = ScreenshotSession().__enter__()
            except Exception as e:
                logger.warning(f"Screenshots disabled: {type(e).__name__}: {e}")
                session = None
        try:
            for p in prospects:
                try:
                    results.append(self.build(p, session))
                except Exception as e:
                    logger.error(f"Pages for #{p['id']} failed: {type(e).__name__}: {e}")
        finally:
            if session is not None:
                session.__exit__(None, None, None)
        return results


def _raw_audit(prospect_id: int) -> Optional[str]:
    from database.db import get_connection
    with get_connection() as conn:
        row = conn.execute("SELECT audit_json FROM prospects WHERE id = ?;", (prospect_id,)).fetchone()
        return row["audit_json"] if row else None


def build_for_top() -> Dict[str, Any]:
    """
    Daily: pages for the hottest prospects that have none yet, plus a design check of a
    few sites that passed the code checks (a dated look turns them into leads).
    """
    from database.db import get_connection
    from database.prospect_repository import ALERTABLE_TIERS

    marks = ",".join("?" for _ in ALERTABLE_TIERS)
    with get_connection() as conn:
        top = [r["id"] for r in conn.execute(
            f"""SELECT id FROM prospects WHERE pages_generated_at IS NULL AND tier IN ({marks})
                AND status IN ('new','alerted','contacted') ORDER BY heat_score DESC, id ASC LIMIT ?;""",
            (*ALERTABLE_TIERS, settings.PAGES_PER_RUN),
        ).fetchall()]
        sweep = [r["id"] for r in conn.execute(
            """SELECT id FROM prospects WHERE tier = 'ok_website' AND visual_json IS NULL AND pages_generated_at IS NULL
               AND website LIKE 'http%' ORDER BY COALESCE(review_count, 0) DESC, id ASC LIMIT ?;""",
            (settings.VISUAL_CHECKS_PER_RUN,),
        ).fetchall()]
    prospects = [ProspectRepository.get(i) for i in top + sweep]
    results = PageBuilder().build_many([p for p in prospects if p])
    promoted = sum(1 for r in results if r.get("visual") and r["visual"]["dated_score"] >= 7)
    return {"pages": len(results), "design_checks": len(sweep), "promoted": promoted}


# ---------------------------------------------------------------------------- publish + live

def publish(prospect_id: int) -> Dict[str, Any]:
    p = ProspectRepository.get(prospect_id)
    if not p or not p.get("slug") or not p.get("pages_generated_at"):
        raise ValueError("Generate the pages first")
    src = page_dir(p["slug"])
    public = settings.SITE_PUBLIC_DIR
    if not public.exists():
        raise ValueError(f"Site public folder not found: {public}")
    dest = public / "p" / p["slug"]
    dest.mkdir(parents=True, exist_ok=True)
    # Only the prospect-facing pages; proposals and anything else stay local
    for f in src.iterdir():
        if f.name in ("demo.html", "audit.html", "desktop.jpg", "mobile.jpg"):
            shutil.copy2(f, dest / f.name)
    ProspectRepository.update(prospect_id, pages_published_at=_now())
    return {"ok": True, "folder": str(dest), "url": f"{settings.SITE_URL}/p/{p['slug']}/"}


def check_live() -> Dict[str, int]:
    """Marks published pages as live once the deployed site serves them."""
    from database.db import get_connection
    with get_connection() as conn:
        rows = conn.execute(
            "SELECT id, slug FROM prospects WHERE pages_published_at IS NOT NULL AND COALESCE(pages_live, 0) = 0 LIMIT 50;"
        ).fetchall()
    live = 0
    for row in rows:
        url = f"{settings.SITE_URL}/p/{row['slug']}/demo.html"
        try:
            r = requests.get(url, timeout=15, headers={"User-Agent": "SynexLabsLeadEngine/1.0"})
            if r.ok and "Concept preview" in r.text:
                ProspectRepository.update(row["id"], pages_live=1)
                live += 1
        except requests.RequestException:
            continue
    return {"checked": len(rows), "live": live}
