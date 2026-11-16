"""Database access for the Maps prospector (local businesses to pitch)."""

import json
import math
from datetime import datetime, timedelta, timezone
from typing import Optional, Dict, Any, List, Tuple

from config.settings import settings
from .db import get_connection
from .stages import PROSPECT_STAGES, POSITIVE, CLOSED

# Tiers worth a Telegram card, hottest first
ALERTABLE_TIERS = (
    "no_website",
    "social_only",
    "broken_website",
    "weak_website",
    "no_website_unverified",
)

# Fields the dashboard / engine may update directly
UPDATABLE = {
    "opener", "opener_source", "channel", "email", "email_status", "notes", "slug", "visual_json",
    "pages_generated_at", "pages_published_at", "pages_live", "brief", "proposal_at", "issues",
    "heat_score", "tier",
}


def _now_dt() -> datetime:
    return datetime.now(timezone.utc)


def _fmt(dt: datetime) -> str:
    return dt.strftime("%Y-%m-%d %H:%M:%S")


def _now() -> str:
    return _fmt(_now_dt())


def _parse(value: Optional[str]) -> Optional[datetime]:
    if not value:
        return None
    try:
        return datetime.strptime(value[:19].replace("T", " "), "%Y-%m-%d %H:%M:%S").replace(tzinfo=timezone.utc)
    except ValueError:
        return None


class ProspectRepository:

    # ---------------------------------------------------------------- prospects

    @staticmethod
    def exists(source: str, place_id: str) -> bool:
        with get_connection() as conn:
            row = conn.execute(
                "SELECT 1 FROM prospects WHERE source = ? AND place_id = ? LIMIT 1;",
                (source, place_id),
            ).fetchone()
            return row is not None

    @staticmethod
    def save(p: Dict[str, Any]) -> Optional[int]:
        """Inserts a prospect. Returns the new row id, or None if it already existed."""
        query = """
        INSERT INTO prospects (
            source, place_id, name, niche, city, address, phone, email, website, socials,
            maps_url, rating, review_count, tier, heat_score, issues, audit_json, audited_at, status,
            country_code, new_business, old_site, priority
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ON CONFLICT(source, place_id) DO NOTHING;
        """
        with get_connection() as conn:
            cur = conn.execute(
                query,
                (
                    p["source"], p["place_id"], p["name"], p.get("niche"), p.get("city"),
                    p.get("address"), p.get("phone"), p.get("email"), p.get("website"),
                    json.dumps(p.get("socials") or []), p.get("maps_url"), p.get("rating"),
                    p.get("review_count"), p.get("tier"), int(p.get("heat_score") or 0),
                    json.dumps(p.get("issues") or []), json.dumps(p.get("audit") or {}),
                    _now(), p.get("status", "new"), p.get("country_code"), int(p.get("new_business") or 0),
                    int(p.get("old_site") or 0), int(p.get("priority") or 0),
                ),
            )
            conn.commit()
            return cur.lastrowid if cur.rowcount > 0 else None

    @staticmethod
    def get_alertable(limit: int) -> List[Dict[str, Any]]:
        placeholders = ",".join("?" for _ in ALERTABLE_TIERS)
        query = f"""
        SELECT * FROM prospects
        WHERE status = 'new' AND tier IN ({placeholders})
        ORDER BY priority DESC, heat_score DESC, COALESCE(review_count, 0) DESC, id ASC
        LIMIT ?;
        """
        with get_connection() as conn:
            rows = conn.execute(query, (*ALERTABLE_TIERS, limit)).fetchall()
            return [ProspectRepository._decode(r) for r in rows]

    @staticmethod
    def list(status: Optional[str] = None, limit: int = 50, alertable_only: bool = True) -> List[Dict[str, Any]]:
        clauses, params = [], []
        if status:
            clauses.append("status = ?")
            params.append(status)
        if alertable_only:
            clauses.append(f"tier IN ({','.join('?' for _ in ALERTABLE_TIERS)})")
            params.extend(ALERTABLE_TIERS)
        where = f"WHERE {' AND '.join(clauses)}" if clauses else ""
        query = f"SELECT * FROM prospects {where} ORDER BY priority DESC, heat_score DESC, id DESC LIMIT ?;"
        with get_connection() as conn:
            rows = conn.execute(query, (*params, limit)).fetchall()
            return [ProspectRepository._decode(r) for r in rows]

    @staticmethod
    def get(prospect_id: int) -> Optional[Dict[str, Any]]:
        with get_connection() as conn:
            row = conn.execute("SELECT * FROM prospects WHERE id = ?;", (prospect_id,)).fetchone()
            return ProspectRepository._decode(row) if row else None

    @staticmethod
    def find_by_email(address: str) -> Optional[Dict[str, Any]]:
        with get_connection() as conn:
            row = conn.execute(
                "SELECT * FROM prospects WHERE lower(email) = lower(?) ORDER BY id DESC LIMIT 1;",
                (address.strip(),),
            ).fetchone()
            return ProspectRepository._decode(row) if row else None

    @staticmethod
    def find_by_slug(slug: str) -> Optional[Dict[str, Any]]:
        with get_connection() as conn:
            row = conn.execute("SELECT * FROM prospects WHERE slug = ? LIMIT 1;", (slug,)).fetchone()
            return ProspectRepository._decode(row) if row else None

    @staticmethod
    def set_opener(prospect_id: int, opener: str, opener_source: str):
        ProspectRepository.update(prospect_id, opener=opener, opener_source=opener_source)

    @staticmethod
    def update(prospect_id: int, **fields):
        fields = {k: v for k, v in fields.items() if k in UPDATABLE}
        if not fields:
            return
        for key in ("issues", "visual_json"):
            if key in fields and not isinstance(fields[key], str) and fields[key] is not None:
                fields[key] = json.dumps(fields[key])
        sets = ", ".join(f"{k} = ?" for k in fields)
        with get_connection() as conn:
            conn.execute(f"UPDATE prospects SET {sets} WHERE id = ?;", (*fields.values(), prospect_id))
            conn.commit()

    @staticmethod
    def set_status(prospect_id: int, status: str, channel: Optional[str] = None):
        """
        Moves a prospect through the pipeline. Contacting starts the follow-up
        schedule; replies and closed outcomes stop it.
        """
        if status not in PROSPECT_STAGES:
            raise ValueError(f"Unknown prospect status: {status}")
        now = _now_dt()
        with get_connection() as conn:
            if status == "contacted":
                days = settings.FOLLOWUP_DAYS
                next_at = _fmt(now + timedelta(days=days[0])) if days else None
                conn.execute(
                    """UPDATE prospects SET status = 'contacted',
                           contacted_at = COALESCE(contacted_at, ?), last_touch_at = ?,
                           followup_step = 0, next_followup_at = ?, channel = COALESCE(?, channel)
                       WHERE id = ?;""",
                    (_fmt(now), _fmt(now), next_at, channel, prospect_id),
                )
            elif status == "alerted":
                conn.execute(
                    "UPDATE prospects SET status = 'alerted', alerted_at = ? WHERE id = ?;",
                    (_fmt(now), prospect_id),
                )
            elif status == "new":
                conn.execute(
                    """UPDATE prospects SET status = 'new', next_followup_at = NULL, followup_step = 0,
                           contacted_at = NULL, outcome_at = NULL WHERE id = ?;""",
                    (prospect_id,),
                )
            elif status in CLOSED:
                conn.execute(
                    "UPDATE prospects SET status = ?, next_followup_at = NULL, outcome_at = ? WHERE id = ?;",
                    (status, _fmt(now), prospect_id),
                )
            else:  # replied, call_booked, proposal_sent
                conn.execute(
                    "UPDATE prospects SET status = ?, next_followup_at = NULL, last_touch_at = ? WHERE id = ?;",
                    (status, _fmt(now), prospect_id),
                )
            conn.commit()

    @staticmethod
    def dashboard_rows() -> List[Dict[str, Any]]:
        """Top of each priority group plus recent in-progress / closed rows, so every filter has data."""
        queries = [
            ("status IN ('new','alerted') AND tier IN ('no_website','social_only','no_website_unverified')", 300),
            ("status IN ('new','alerted') AND tier = 'weak_website' AND COALESCE(old_site,0) = 1", 200),
            ("status IN ('new','alerted') AND (tier = 'broken_website' OR (tier = 'weak_website' AND COALESCE(old_site,0) = 0))", 150),
        ]
        rows, seen = [], set()
        with get_connection() as conn:
            for where, limit in queries:
                for r in conn.execute(
                    f"SELECT * FROM prospects WHERE {where} ORDER BY priority DESC, heat_score DESC, id DESC LIMIT ?;",
                    (limit,),
                ).fetchall():
                    if r["id"] not in seen:
                        seen.add(r["id"])
                        rows.append(ProspectRepository._decode(r))
            placeholders = ",".join("?" for _ in ALERTABLE_TIERS)
            for r in conn.execute(
                f"""SELECT * FROM prospects WHERE status NOT IN ('new','alerted','ignored') AND tier IN ({placeholders})
                    ORDER BY COALESCE(last_touch_at, contacted_at, created_at) DESC LIMIT 300;""",
                ALERTABLE_TIERS,
            ).fetchall():
                if r["id"] not in seen:
                    seen.add(r["id"])
                    rows.append(ProspectRepository._decode(r))
        return rows

    @staticmethod
    def open_group_counts() -> Dict[str, int]:
        """Counts of prospects waiting to be contacted, per priority group (whole table, not a page)."""
        from outreach.links import country_code_for
        from prospector.priority import label

        out = {"open": 0, "first": 0, "first_india": 0, "upgrade": 0}
        placeholders = ",".join("?" for _ in ALERTABLE_TIERS)
        with get_connection() as conn:
            rows = conn.execute(
                f"SELECT tier, old_site, city FROM prospects WHERE status IN ('new','alerted') AND tier IN ({placeholders});",
                ALERTABLE_TIERS,
            ).fetchall()
        india_cache: Dict[str, bool] = {}
        for r in rows:
            out["open"] += 1
            group = label(r["tier"], bool(r["old_site"]))[1]
            if group == "first":
                out["first"] += 1
                city = r["city"] or ""
                if city not in india_cache:
                    india_cache[city] = country_code_for(city) == settings.PRIORITY_COUNTRY_CODE
                out["first_india"] += 1 if india_cache[city] else 0
            elif group == "upgrade":
                out["upgrade"] += 1
        return out

    @staticmethod
    def alerted_today() -> int:
        """Prospect cards sent to Telegram since local midnight."""
        local_midnight = datetime.now().astimezone().replace(hour=0, minute=0, second=0, microsecond=0)
        since = _fmt(local_midnight.astimezone(timezone.utc))
        with get_connection() as conn:
            return conn.execute(
                "SELECT COUNT(*) FROM prospects WHERE alerted_at IS NOT NULL AND alerted_at >= ?;", (since,)
            ).fetchone()[0]

    # ---------------------------------------------------------------- follow-ups

    @staticmethod
    def due_followups(limit: int = 50) -> List[Dict[str, Any]]:
        with get_connection() as conn:
            rows = conn.execute(
                """SELECT * FROM prospects
                   WHERE status = 'contacted' AND next_followup_at IS NOT NULL AND next_followup_at <= ?
                   ORDER BY next_followup_at ASC LIMIT ?;""",
                (_now(), limit),
            ).fetchall()
            return [ProspectRepository._decode(r) for r in rows]

    @staticmethod
    def advance_followup(prospect_id: int) -> str:
        """
        Records that the due follow-up was sent. Returns 'scheduled' (another follow-up
        is planned), 'waiting' (last one sent, waiting for a reply) or 'no_response'.
        """
        p = ProspectRepository.get(prospect_id)
        if not p or p["status"] != "contacted":
            return "ignored"
        days = settings.FOLLOWUP_DAYS
        step = int(p.get("followup_step") or 0)
        now = _now_dt()
        contacted = _parse(p.get("contacted_at")) or now

        if step >= len(days):
            ProspectRepository.set_status(prospect_id, "no_response")
            return "no_response"

        step += 1
        if step < len(days):
            next_at = contacted + timedelta(days=days[step])
            if next_at <= now:
                next_at = now + timedelta(days=2)
            result = "scheduled"
        else:
            next_at = now + timedelta(days=settings.NO_RESPONSE_AFTER_DAYS)
            result = "waiting"
        with get_connection() as conn:
            conn.execute(
                "UPDATE prospects SET followup_step = ?, next_followup_at = ?, last_touch_at = ? WHERE id = ?;",
                (step, _fmt(next_at), _fmt(now), prospect_id),
            )
            conn.commit()
        return result

    @staticmethod
    def postpone_followup(prospect_id: int, days: int):
        with get_connection() as conn:
            conn.execute(
                "UPDATE prospects SET next_followup_at = ? WHERE id = ? AND status = 'contacted';",
                (_fmt(_now_dt() + timedelta(days=days)), prospect_id),
            )
            conn.commit()

    @staticmethod
    def expire_waiting() -> int:
        """Marks prospects whose last follow-up went unanswered as 'no_response'."""
        days = settings.FOLLOWUP_DAYS
        with get_connection() as conn:
            cur = conn.execute(
                """UPDATE prospects SET status = 'no_response', next_followup_at = NULL, outcome_at = ?
                   WHERE status = 'contacted' AND followup_step >= ? AND next_followup_at <= ?;""",
                (_now(), len(days), _now()),
            )
            conn.commit()
            return cur.rowcount

    # ---------------------------------------------------------------- pipeline + stats

    @staticmethod
    def pipeline(limit: int = 300) -> List[Dict[str, Any]]:
        with get_connection() as conn:
            rows = conn.execute(
                """SELECT * FROM prospects
                   WHERE status IN ('contacted','replied','call_booked','proposal_sent','won','lost','no_response','not_interested')
                   ORDER BY COALESCE(last_touch_at, contacted_at, created_at) DESC LIMIT ?;""",
                (limit,),
            ).fetchall()
            return [ProspectRepository._decode(r) for r in rows]

    @staticmethod
    def get_stats() -> Dict[str, Any]:
        with get_connection() as conn:
            by_tier = {
                r["tier"]: r["n"]
                for r in conn.execute("SELECT tier, COUNT(*) AS n FROM prospects GROUP BY tier;").fetchall()
            }
            by_status = {
                r["status"]: r["n"]
                for r in conn.execute("SELECT status, COUNT(*) AS n FROM prospects GROUP BY status;").fetchall()
            }
            total = conn.execute("SELECT COUNT(*) FROM prospects;").fetchone()[0]
            due = conn.execute(
                "SELECT COUNT(*) FROM prospects WHERE status = 'contacted' AND next_followup_at <= ?;",
                (_now(),),
            ).fetchone()[0]
        return {"total": total, "by_tier": by_tier, "by_status": by_status, "followups_due": due}

    @staticmethod
    def performance() -> List[Dict[str, Any]]:
        """Reply rate per niche + city, used to rank future searches and shown on the dashboard."""
        positive = ",".join(f"'{s}'" for s in POSITIVE)
        with get_connection() as conn:
            rows = conn.execute(
                f"""SELECT niche, city,
                       COUNT(*) AS found,
                       SUM(CASE WHEN contacted_at IS NOT NULL THEN 1 ELSE 0 END) AS contacted,
                       SUM(CASE WHEN status IN ({positive}) THEN 1 ELSE 0 END) AS positive,
                       SUM(CASE WHEN status = 'won' THEN 1 ELSE 0 END) AS won
                    FROM prospects GROUP BY niche, city;"""
            ).fetchall()
        out = []
        for r in rows:
            d = dict(r)
            d["reply_rate"] = round(d["positive"] / d["contacted"], 3) if d["contacted"] else None
            out.append(d)
        out.sort(key=lambda d: (d["reply_rate"] or 0, d["contacted"]), reverse=True)
        return out

    @staticmethod
    def _decode(row) -> Dict[str, Any]:
        d = dict(row)
        for key in ("issues", "socials"):
            try:
                d[key] = json.loads(d.get(key) or "[]")
            except (TypeError, json.JSONDecodeError):
                d[key] = []
        try:
            d["visual"] = json.loads(d.get("visual_json") or "null")
        except (TypeError, json.JSONDecodeError):
            d["visual"] = None
        return d

    # ---------------------------------------------------------------- searches

    @staticmethod
    def get_due_searches(
        source: str, niches: List[str], cities: List[str], rerun_days: int, limit: int
    ) -> List[Tuple[str, str]]:
        """
        Niche + city pairs that are due (never run, or older than `rerun_days`).
        Never-run pairs come first (exploration). Among the rest, pairs whose
        niche and city have earned replies come first (self-tuning), then oldest.
        """
        cutoff = _fmt(_now_dt() - timedelta(days=rerun_days))
        with get_connection() as conn:
            last_runs = {
                (r["niche"], r["city"]): r["last_run_at"]
                for r in conn.execute(
                    "SELECT niche, city, last_run_at FROM prospect_searches WHERE source = ?;",
                    (source,),
                ).fetchall()
            }
        from outreach.links import country_code_for

        scores = ProspectRepository._search_scores([(n, c) for c in cities for n in niches])
        due = []
        for city in cities:
            priority = 0 if country_code_for(city) == settings.PRIORITY_COUNTRY_CODE else 1
            for niche in niches:
                last = last_runs.get((niche, city))
                if last is None or last < cutoff:
                    never = last is None
                    score = scores.get((niche, city), 0.0)
                    # Priority market first, then untried pairs, then best reply rate, then oldest
                    due.append((priority, 0 if never else 1, -score, last or "", niche, city))
        due.sort()
        return [(niche, city) for *_, niche, city in due[:limit]]

    @staticmethod
    def _search_scores(pairs: List[Tuple[str, str]]) -> Dict[Tuple[str, str], float]:
        """
        Expected reply rate per niche + city with a Beta(1, 4) prior, blended with
        the niche's and the city's overall rates so new pairs borrow from both.
        """
        perf = {(d["niche"], d["city"]): d for d in ProspectRepository.performance()}

        def rate(pos, n):
            return (pos + 1) / (n + 5)

        niche_tot, city_tot = {}, {}
        for d in perf.values():
            for key, tot in ((d["niche"], niche_tot), (d["city"], city_tot)):
                p, n = tot.get(key, (0, 0))
                tot[key] = (p + d["positive"], n + d["contacted"])
        scores = {}
        for niche, city in pairs:
            d = perf.get((niche, city), {"positive": 0, "contacted": 0})
            pair = rate(d["positive"], d["contacted"])
            blended = (rate(*niche_tot.get(niche, (0, 0))) + rate(*city_tot.get(city, (0, 0)))) / 2
            weight = 1 - math.exp(-d["contacted"] / 10)  # trust the pair more as data grows
            scores[(niche, city)] = weight * pair + (1 - weight) * blended
        return scores

    @staticmethod
    def record_search(source: str, niche: str, city: str, results_count: int, new_count: int):
        query = """
        INSERT INTO prospect_searches (source, niche, city, results_count, new_count, last_run_at)
        VALUES (?, ?, ?, ?, ?, ?)
        ON CONFLICT(source, niche, city) DO UPDATE SET
            results_count = excluded.results_count,
            new_count = excluded.new_count,
            last_run_at = excluded.last_run_at;
        """
        with get_connection() as conn:
            conn.execute(query, (source, niche, city, results_count, new_count, _now()))
            conn.commit()

    # ---------------------------------------------------------------- api budget

    @staticmethod
    def _month() -> str:
        return _now_dt().strftime("%Y-%m")

    @staticmethod
    def get_month_calls(api: str) -> int:
        with get_connection() as conn:
            row = conn.execute(
                "SELECT calls FROM api_usage WHERE api = ? AND month = ?;",
                (api, ProspectRepository._month()),
            ).fetchone()
            return int(row["calls"]) if row else 0

    @staticmethod
    def add_calls(api: str, n: int = 1):
        query = """
        INSERT INTO api_usage (api, month, calls) VALUES (?, ?, ?)
        ON CONFLICT(api, month) DO UPDATE SET calls = calls + excluded.calls;
        """
        with get_connection() as conn:
            conn.execute(query, (api, ProspectRepository._month(), n))
            conn.commit()

    # ---------------------------------------------------------------- geocoding

    @staticmethod
    def get_cached_area(query: str) -> Optional[Dict[str, Any]]:
        with get_connection() as conn:
            row = conn.execute(
                "SELECT osm_area_id, display_name, lat, lon FROM geocode_cache WHERE query = ?;",
                (query.lower(),),
            ).fetchone()
            return dict(row) if row else None

    @staticmethod
    def cache_area(query: str, osm_area_id: Optional[int], display_name: str,
                   lat: Optional[float] = None, lon: Optional[float] = None):
        with get_connection() as conn:
            conn.execute(
                "INSERT OR REPLACE INTO geocode_cache (query, osm_area_id, display_name, lat, lon) VALUES (?, ?, ?, ?, ?);",
                (query.lower(), osm_area_id, display_name, lat, lon),
            )
            conn.commit()


class SuppressionList:
    """People who asked not to be contacted (email address or phone digits)."""

    @staticmethod
    def _norm(value: str) -> str:
        value = (value or "").strip().lower()
        if "@" not in value:
            value = "".join(ch for ch in value if ch.isdigit())
        return value

    @staticmethod
    def add(value: str, reason: str):
        v = SuppressionList._norm(value)
        if not v:
            return
        with get_connection() as conn:
            conn.execute(
                "INSERT OR IGNORE INTO suppression (value, reason) VALUES (?, ?);", (v, reason)
            )
            conn.commit()

    @staticmethod
    def contains(value: str) -> bool:
        v = SuppressionList._norm(value)
        if not v:
            return False
        with get_connection() as conn:
            return conn.execute("SELECT 1 FROM suppression WHERE value = ?;", (v,)).fetchone() is not None
