"""
Local dashboard for the lead engine.

Served from the same background process that runs the scheduler, so closing the
browser tab never stops the engine. Listens on 127.0.0.1 only. Every API call needs
a random per-session token (header), previews need the same token as a SameSite=Strict
cookie, and the Host header must be localhost, so other websites open in the browser
cannot read or change anything here.
"""

import hmac
import json
import logging
import os
import re
import secrets
import threading
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any, Dict, Optional, Callable, Tuple

from config.settings import settings, BASE_DIR
from config.redact import redact
from database.repository import LeadRepository
from database.prospect_repository import ProspectRepository
from database.email_repository import EmailRepository
from database.stages import LABELS, PROSPECT_STAGES, LEAD_STAGES
from brain.gemini_analyzer import GeminiUnavailable
from prospector.engine import ProspectEngine, template_opener
from prospector.scoring import TIER_LABELS
from prospector.sources import GooglePlacesSource
from outreach import actions, emailer, inbox
from outreach.links import whatsapp_link, mailto_link, tel_link, instagram_profile, best_channel, country_code_for
from prospector.priority import label as priority_label
from outreach.messages import opener_subject, audit_url, demo_url

logger = logging.getLogger("dashboard")

STATIC_DIR = Path(__file__).parent / "static"
ICON_PATH = BASE_DIR / "assets" / "synex-leads.ico"
LOG_PATH = BASE_DIR / "data" / "engine.log"
# One session file per port, so a second instance (tests, another port) never clobbers the first
SESSION_PATH = BASE_DIR / "data" / (
    "engine.session" if settings.DASHBOARD_PORT == 8765 else f"engine-{settings.DASHBOARD_PORT}.session"
)
PAGES_DIR = BASE_DIR / "data" / "pages"
APP_ID = "synex-lead-engine"

CONTENT_TYPES = {
    ".html": "text/html; charset=utf-8",
    ".css": "text/css; charset=utf-8",
    ".js": "application/javascript; charset=utf-8",
    ".ico": "image/x-icon",
    ".jpg": "image/jpeg",
    ".png": "image/png",
}
CSP = (
    "default-src 'none'; script-src 'self'; style-src 'self'; connect-src 'self'; "
    "img-src 'self' data:; frame-ancestors 'none'; base-uri 'none'; form-action 'none'"
)
# Generated pages use inline styles (and the proposal's print button)
PREVIEW_CSP = (
    "default-src 'none'; style-src 'unsafe-inline'; script-src 'unsafe-inline'; img-src 'self' data:; "
    "frame-ancestors 'none'; base-uri 'none'; form-action 'none'"
)
PREVIEW_FILES = {"demo.html", "audit.html", "proposal.html", "desktop.jpg", "mobile.jpg"}
_pages_lock = threading.Lock()


def tail_log(max_lines: int = 120) -> list:
    if not LOG_PATH.exists():
        return []
    with open(LOG_PATH, "rb") as f:
        f.seek(0, os.SEEK_END)
        size = f.tell()
        f.seek(max(0, size - 48_000))
        text = f.read().decode("utf-8", errors="ignore")
    lines = [redact(ln.rstrip()) for ln in text.splitlines() if ln.strip()]
    return lines[-max_lines:]


def _json_field(value):
    try:
        return json.loads(value) if value else None
    except (TypeError, json.JSONDecodeError):
        return None


class DashboardServer:
    def __init__(self, service, port: Optional[int] = None, on_stop: Optional[Callable[[], None]] = None):
        self.service = service
        self.port = port or settings.DASHBOARD_PORT
        self.token = secrets.token_urlsafe(32)
        self.on_stop = on_stop
        self.httpd = ThreadingHTTPServer(("127.0.0.1", self.port), self._handler_class())
        self.httpd.daemon_threads = True
        SESSION_PATH.parent.mkdir(parents=True, exist_ok=True)
        SESSION_PATH.write_text(json.dumps({"port": self.port, "token": self.token, "pid": os.getpid()}), encoding="utf-8")

    @property
    def url(self) -> str:
        return f"http://127.0.0.1:{self.port}/"

    def serve_forever(self):
        self.httpd.serve_forever(poll_interval=0.5)

    def shutdown(self):
        threading.Thread(target=self.httpd.shutdown, daemon=True).start()

    # ------------------------------------------------------------------ data

    @staticmethod
    def _prospect_view(p: Dict[str, Any], email_ready: bool) -> Dict[str, Any]:
        p["tier_label"] = TIER_LABELS.get(p.get("tier"), p.get("tier"))
        p["priority_label"], p["priority_group"] = priority_label(p.get("tier"), bool(p.get("old_site")))
        p["india"] = country_code_for(p.get("city") or "") == settings.PRIORITY_COUNTRY_CODE
        p["stage_label"] = LABELS.get(p.get("status"), p.get("status"))
        if not p.get("opener"):
            p["opener"] = template_opener(p)
            p["opener_source"] = "template"
        subject = opener_subject(p)
        p["links"] = {
            "whatsapp": whatsapp_link(p.get("phone") or "", p["opener"], p.get("city")),
            "mailto": mailto_link(p.get("email") or "", subject, p["opener"]),
            "tel": tel_link(p.get("phone") or ""),
            "instagram": instagram_profile(p.get("socials")),
        }
        p["subject"] = subject
        p["best_channel"] = best_channel(p)
        p["can_email"] = bool(email_ready and p.get("email") and p.get("email_status") != "bounced")
        slug = p.get("slug")
        files = set(os.listdir(PAGES_DIR / slug)) if slug and (PAGES_DIR / slug).is_dir() else set()
        p["pages"] = {
            "generated": bool(p.get("pages_generated_at")),
            "published": bool(p.get("pages_published_at")),
            "live": bool(p.get("pages_live")),
            "demo": f"/preview/{slug}/demo.html" if "demo.html" in files else None,
            "audit": f"/preview/{slug}/audit.html" if "audit.html" in files else None,
            "proposal": f"/preview/{slug}/proposal.html" if "proposal.html" in files else None,
            "public_demo": demo_url(p),
            "public_audit": audit_url(p),
        }
        p["brief"] = _json_field(p.get("brief")) if isinstance(p.get("brief"), str) else p.get("brief")
        for drop in ("audit_json", "place_id", "source", "visual_json"):
            p.pop(drop, None)
        return p

    def state(self) -> Dict[str, Any]:
        svc = self.service
        places = GooglePlacesSource()
        email_ready = emailer.is_configured()
        lead_stats = LeadRepository.get_stats()
        lead_stats.pop("top_sources", None)
        leads = LeadRepository.get_recent_qualified(limit=80)
        for l in leads:
            l["stage_label"] = LABELS.get(l["status"], l["status"])
            if l.get("platform") == "website" and l.get("reply_email"):
                l["reply_link"] = mailto_link(l["reply_email"], f"Re: {l.get('title') or 'your enquiry'}", l.get("draft_icebreaker") or "")
        prospects = [self._prospect_view(p, email_ready) for p in ProspectRepository.dashboard_rows()]
        pipeline_ids = {p["id"] for p in prospects}
        pipeline = [p for p in prospects if p["status"] in ("contacted", "replied", "call_booked", "proposal_sent", "won", "lost", "no_response", "not_interested")]
        pipeline += [self._prospect_view(p, email_ready) for p in ProspectRepository.pipeline() if p["id"] not in pipeline_ids]

        followups = []
        for p in ProspectRepository.due_followups(limit=60):
            p = self._prospect_view(p, email_ready)
            number, text = actions.followup_for(p)
            p["followup_number"] = number
            p["followup_text"] = text
            p["followup_links"] = {
                "whatsapp": whatsapp_link(p.get("phone") or "", text, p.get("city")),
                "mailto": mailto_link(p.get("email") or "", f"Re: {p['subject']}", text),
            }
            p["auto_email"] = bool(email_ready and settings.EMAIL_AUTO_FOLLOWUPS and p.get("channel") == "email" and p.get("email"))
            followups.append(p)

        mail_counts = EmailRepository.counts()
        groups = ProspectRepository.open_group_counts()
        stats_p = ProspectRepository.get_stats()
        due_searches = ProspectRepository.get_due_searches(
            svc_source_name(), settings.PROSPECT_NICHES, settings.PROSPECT_CITIES, settings.PROSPECT_RERUN_DAYS, 8
        )
        return {
            "engine": {
                "pid": os.getpid(),
                "port": self.port,
                "uptime_s": int(time.time() - svc.started_at),
                "started_at": time.strftime("%Y-%m-%d %H:%M", time.localtime(svc.started_at)),
            },
            "health": {
                "gemini": svc.pipeline.gemini_analyzer.is_configured(),
                "telegram": svc.pipeline.telegram_alerter.is_configured(),
                "places": places.is_configured(),
                "places_calls_left": places.remaining_budget() if places.is_configured() else None,
                "bluesky": svc.bluesky_enabled,
                "reddit_oauth": bool(settings.REDDIT_CLIENT_ID and settings.REDDIT_CLIENT_SECRET),
                "x_login": settings.TWITTER_AUTH_STATE_PATH.exists(),
                "email": email_ready,
                "email_left_today": emailer.remaining_today() if email_ready else None,
                "email_limit_today": emailer.daily_limit() if email_ready else None,
                "inbox": inbox.is_configured(),
                "site_folder": settings.SITE_PUBLIC_DIR.exists(),
                "niches": settings.PROSPECT_NICHES,
                "cities": settings.PROSPECT_CITIES,
            },
            "stages": {"prospect": list(PROSPECT_STAGES), "lead": list(LEAD_STAGES), "labels": LABELS},
            "jobs": svc.jobs_snapshot(),
            "stats": {
                "leads": lead_stats,
                "leads_to_contact": sum(1 for l in leads if l["status"] in ("new", "alerted")),
                "prospects": stats_p,
                "prospects_to_contact": groups["open"],
                "prospects_no_website": groups["first"],
                "prospects_no_website_india": groups["first_india"],
                "prospects_old_site": groups["upgrade"],
                "followups_due": len(followups),
                "replies_waiting": mail_counts["replies_waiting"],
                "won": stats_p["by_status"].get("won", 0) + sum(1 for l in leads if l["status"] == "won"),
                "emails_7d": mail_counts["sent_7d"],
            },
            "prospects": prospects,
            "followups": followups,
            "inbox": EmailRepository.incoming(limit=60),
            "leads": leads,
            "pipeline": pipeline,
            "insights": {
                "performance": ProspectRepository.performance()[:40],
                "next_searches": [{"niche": n, "city": c} for n, c in due_searches],
            },
            "log": tail_log(),
        }

    # ------------------------------------------------------------------ actions

    def write_opener(self, prospect_id: int) -> Tuple[int, Dict[str, Any]]:
        p = ProspectRepository.get(prospect_id)
        if not p:
            return 404, {"error": "prospect not found"}
        gemini = self.service.pipeline.gemini_analyzer
        if not gemini.is_configured():
            return 400, {"error": "Gemini is not configured (GEMINI_API_KEY)"}
        try:
            opener = gemini.write_prospect_opener(ProspectEngine._opener_context(p))
        except GeminiUnavailable as e:
            return 503, {"error": str(e)}
        except ValueError as e:
            return 502, {"error": str(e)}
        ProspectRepository.set_opener(prospect_id, opener, "gemini")
        return 200, {"opener": opener}

    def draft_answer(self, body: Dict[str, Any]) -> Tuple[int, Dict[str, Any]]:
        """Drafts a helpful Quora / Reddit answer for the founder to post by hand."""
        from brain.prompts import ANSWER_SYSTEM_INSTRUCTION, ANSWER_TEMPLATE

        question = str(body.get("question") or "").strip()[:3000]
        if len(question) < 10:
            return 400, {"error": "Paste the question first"}
        gemini = self.service.pipeline.gemini_analyzer
        if not gemini.is_configured():
            return 400, {"error": "Gemini is not configured (GEMINI_API_KEY)"}
        base = settings.SITE_URL
        pages = ["clinics", "dentists", "salons", "restaurants", "gyms", "real-estate", "coaching"]
        links = "\n".join([f"- {base}/websites-for/{slug}" for slug in pages] + [f"- {base}/#pricing (prices)"])
        try:
            data = gemini.generate_json(
                ANSWER_TEMPLATE.format(platform=str(body.get("platform") or "Quora")[:20], question=question, links=links),
                ANSWER_SYSTEM_INSTRUCTION,
            )
        except GeminiUnavailable as e:
            return 503, {"error": str(e)}
        except ValueError as e:
            return 502, {"error": str(e)}
        return 200, {
            "answer": str(data.get("answer") or ""),
            "link_used": str(data.get("link_used") or ""),
            "note": str(data.get("note") or ""),
        }

    @staticmethod
    def build_pages(prospect_id: int) -> Tuple[int, Dict[str, Any]]:
        from showcase.pages import PageBuilder
        p = ProspectRepository.get(prospect_id)
        if not p:
            return 404, {"error": "prospect not found"}
        if not _pages_lock.acquire(timeout=1):
            return 409, {"error": "Pages are already being built, try again in a minute"}
        try:
            result = PageBuilder().build_many([p])
        finally:
            _pages_lock.release()
        if not result:
            return 500, {"error": "Page build failed, see the activity log"}
        return 200, {"ok": True, "message": "Pages ready", **result[0]}

    # ------------------------------------------------------------------ http

    def _handler_class(self):
        server = self
        allowed_hosts = {f"127.0.0.1:{self.port}", f"localhost:{self.port}"}

        class Handler(BaseHTTPRequestHandler):
            server_version = "SynexLeadEngine"
            sys_version = ""

            def log_message(self, fmt, *args):  # keep the engine log readable
                return

            # ---------------- helpers
            def _send(self, code: int, body: bytes, ctype: str, extra: Optional[Dict[str, str]] = None, csp: str = CSP):
                self.send_response(code)
                self.send_header("Content-Type", ctype)
                self.send_header("Content-Length", str(len(body)))
                self.send_header("Cache-Control", "no-store")
                self.send_header("X-Content-Type-Options", "nosniff")
                self.send_header("Referrer-Policy", "no-referrer")
                self.send_header("Content-Security-Policy", csp)
                for k, v in (extra or {}).items():
                    self.send_header(k, v)
                self.end_headers()
                if self.command != "HEAD":
                    self.wfile.write(body)

            def _json(self, code: int, data: Any):
                self._send(code, json.dumps(data, default=str).encode("utf-8"), "application/json; charset=utf-8")

            def _host_ok(self) -> bool:
                return self.headers.get("Host", "") in allowed_hosts

            def _token_ok(self) -> bool:
                return hmac.compare_digest(self.headers.get("X-Engine-Token", ""), server.token)

            def _cookie_ok(self) -> bool:
                m = re.search(r"(?:^|;\s*)engine_token=([^;]+)", self.headers.get("Cookie", ""))
                return bool(m) and hmac.compare_digest(m.group(1), server.token)

            def _body(self) -> Dict[str, Any]:
                length = min(int(self.headers.get("Content-Length") or 0), 64_000)
                if not length:
                    return {}
                try:
                    data = json.loads(self.rfile.read(length).decode("utf-8"))
                    return data if isinstance(data, dict) else {}
                except (ValueError, UnicodeDecodeError):
                    return {}

            # ---------------- routes
            def do_GET(self):
                if not self._host_ok():
                    return self._send(403, b"Forbidden", "text/plain")
                path = self.path.split("?", 1)[0]
                if path == "/api/health":
                    return self._json(200, {"ok": True, "app": APP_ID})
                if path == "/api/state":
                    if not self._token_ok():
                        return self._json(401, {"error": "bad token"})
                    try:
                        return self._json(200, server.state())
                    except Exception as e:
                        logger.exception("state failed")
                        return self._json(500, {"error": str(e)})
                if path in ("/", "/index.html"):
                    html = (STATIC_DIR / "index.html").read_text(encoding="utf-8").replace("__ENGINE_TOKEN__", server.token)
                    cookie = f"engine_token={server.token}; Path=/; HttpOnly; SameSite=Strict"
                    return self._send(200, html.encode("utf-8"), CONTENT_TYPES[".html"], {"Set-Cookie": cookie})
                if path == "/favicon.ico" and ICON_PATH.exists():
                    return self._send(200, ICON_PATH.read_bytes(), CONTENT_TYPES[".ico"])
                if re.fullmatch(r"/(app\.js|style\.css)", path):
                    f = STATIC_DIR / path.lstrip("/")
                    return self._send(200, f.read_bytes(), CONTENT_TYPES[f.suffix])
                m = re.fullmatch(r"/preview/([a-z0-9-]{4,80})/([a-z]+\.(?:html|jpg))", path)
                if m:
                    if not self._cookie_ok():
                        return self._send(403, b"Open previews from the dashboard", "text/plain")
                    slug, name = m.groups()
                    f = PAGES_DIR / slug / name
                    if name not in PREVIEW_FILES or not f.is_file():
                        return self._send(404, b"Not found", "text/plain")
                    return self._send(200, f.read_bytes(), CONTENT_TYPES[f.suffix], csp=PREVIEW_CSP)
                return self._send(404, b"Not found", "text/plain")

            def do_POST(self):
                if not self._host_ok() or not self._token_ok():
                    return self._json(403, {"error": "forbidden"})
                path = self.path.split("?", 1)[0]
                body = self._body()
                try:
                    return self._route_post(path, body)
                except actions.ActionError as e:
                    return self._json(400, {"error": str(e)})
                except Exception as e:
                    logger.exception("POST failed")
                    return self._json(500, {"error": f"{type(e).__name__}: {e}"})

            def _route_post(self, path: str, body: Dict[str, Any]):
                m = re.fullmatch(r"/api/run/([a-z]+)", path)
                if m:
                    try:
                        return self._json(200, {"started": server.service.run_now(m.group(1))})
                    except ValueError as e:
                        return self._json(400, {"error": str(e)})

                m = re.fullmatch(r"/api/prospect/(\d+)/([a-z_-]+)(?:/([a-z_]+))?", path)
                if m:
                    pid, action, arg = int(m.group(1)), m.group(2), m.group(3)
                    if action == "opener":
                        return self._json(*server.write_opener(pid))
                    if action == "contacted":
                        return self._json(200, actions.mark_contacted(pid, channel=body.get("channel")))
                    if action == "stage" and arg:
                        return self._json(200, actions.set_prospect_stage(pid, arg))
                    if action == "email-opener":
                        return self._json(200, actions.send_opener_email(pid, body.get("subject"), body.get("body")))
                    if action == "followup" and arg == "done":
                        return self._json(200, actions.followup_done(pid))
                    if action == "followup" and arg == "email":
                        return self._json(200, actions.send_followup_email(pid))
                    if action == "followup" and arg == "stop":
                        return self._json(200, actions.stop_sequence(pid))
                    if action == "pages":
                        return self._json(*server.build_pages(pid))
                    if action == "publish":
                        from showcase.pages import publish
                        try:
                            return self._json(200, publish(pid))
                        except ValueError as e:
                            return self._json(400, {"error": str(e)})
                    if action == "brief":
                        from sales.briefs import build_brief
                        return self._json(200, {"ok": True, "brief": build_brief(pid)})
                    if action == "proposal":
                        from sales.proposals import build_proposal
                        return self._json(200, build_proposal(pid))
                    if action == "notes":
                        ProspectRepository.update(pid, notes=str(body.get("notes") or "")[:2000])
                        return self._json(200, {"ok": True})
                    # legacy simple status routes
                    if action in PROSPECT_STAGES:
                        return self._json(200, actions.set_prospect_stage(pid, action))

                if path == "/api/answer":
                    return self._json(*server.draft_answer(body))

                m = re.fullmatch(r"/api/email/(\d+)/(send|handled)", path)
                if m:
                    eid = int(m.group(1))
                    if m.group(2) == "send":
                        return self._json(200, actions.send_reply(eid, body.get("body")))
                    return self._json(200, actions.mark_reply_handled(eid))

                m = re.fullmatch(r"/api/lead/(\d+)/(?:stage/)?([a-z_]+)", path)
                if m:
                    return self._json(200, actions.set_lead_stage(int(m.group(1)), m.group(2)))

                if path == "/api/stop":
                    self._json(200, {"stopping": True})
                    if server.on_stop:
                        threading.Thread(target=server.on_stop, daemon=True).start()
                    return
                return self._json(404, {"error": "not found"})

        return Handler


def svc_source_name() -> str:
    from prospector.sources import pick_source
    return pick_source().name
