import logging
import threading
import time
from datetime import datetime, date
from typing import Callable, Dict, Any, List, Optional

from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.interval import IntervalTrigger
from apscheduler.triggers.cron import CronTrigger
from apscheduler.triggers.date import DateTrigger

from config.settings import settings
from database.db import kv_get
from pipeline import IntentEnginePipeline
from delivery.telegram_bot import TelegramAlerter
from delivery.telegram_listener import TelegramCallbackListener
from prospector.engine import ProspectEngine
from outreach import automation, inbox

logger = logging.getLogger("scheduler")

JOB_NAMES = {
    "reddit_ingestion_job": "Reddit scan",
    "twitter_ingestion_job": "X / Twitter scan",
    "bluesky_ingestion_job": "Bluesky scan",
    "meta_ingestion_job": "Meta ad comments",
    "maps_prospector_job": "Maps prospector",
    "showcase_job": "Audit + demo pages",
    "social_scan": "Social scan (all platforms)",
    "followups_job": "Follow-ups",
    "inbox_job": "Inbox check",
    "digest_job": "Morning digest",
    "health_job": "Health check",
    "backup_job": "Database backup",
    "live_check_job": "Published pages check",
    "telegram_catchup_job": "Telegram catch-up",
    "history_job": "Website age check",
}

# kind -> (state key, lock group)
MANUAL = {
    "social": ("social_scan", "social"),
    "prospect": ("maps_prospector_job", "prospect"),
    "pages": ("showcase_job", "prospect"),
    "history": ("history_job", "prospect"),
    "followups": ("followups_job", "outreach"),
    "inbox": ("inbox_job", "outreach"),
    "digest": ("digest_job", "outreach"),
}


class EngineService:
    """
    Runs every background job:
    - Social: Reddit every 15 min, X every 45 min, Bluesky every 30 min (if set up), Meta 10:00 & 16:00
    - Maps prospector daily, then audit + demo pages for the hottest prospects
    - Follow-ups hourly (auto-email when set up), inbox every few minutes (if set up)
    - Morning digest + follow-up cards, hourly health alerts, daily backup
    Jobs in the same group share a lock so they never overlap.
    """

    def __init__(self):
        self.pipeline = IntentEnginePipeline()
        self.telegram = TelegramAlerter()
        self.listener = TelegramCallbackListener()
        self.health = automation.HealthMonitor()
        self.scheduler = BackgroundScheduler(
            job_defaults={"coalesce": True, "max_instances": 1, "misfire_grace_time": 900}
        )
        self.started_at = time.time()
        self.bluesky_enabled = self.pipeline.bluesky_scraper.is_configured()
        self.inbox_enabled = inbox.is_configured()
        self._locks = {g: threading.Lock() for g in ("social", "prospect", "outreach", "maintenance")}
        self._state: Dict[str, Dict[str, Any]] = {}
        self._state_lock = threading.Lock()

    # ------------------------------------------------------------------ jobs

    def _wrap(self, key: str, group: str, fn: Callable[[], Any]) -> Callable[[], None]:
        def runner():
            lock = self._locks[group]
            if not lock.acquire(blocking=False):
                logger.info(f"[{key}] skipped: another {group} job is running")
                self._update(key, last_status="skipped", last_message=f"Another {group} job was running")
                return
            self._update(key, running=True, last_start=datetime.now().isoformat(timespec="seconds"))
            try:
                print(f"\n[{datetime.now():%Y-%m-%d %H:%M:%S}] ▶ {JOB_NAMES.get(key, key)} started", flush=True)
                result = fn()
                message = ""
                status = "ok"
                if isinstance(result, dict):
                    message = ", ".join(f"{k} {v}" for k, v in result.items())
                    if result.get("failed") and not result.get("searches"):
                        status = "error"
                        message = "all searches failed: " + message
                self._update(key, last_status=status, last_message=message)
                self._count(key, status == "error")
            except Exception as e:
                logger.exception(f"[{key}] failed")
                self._update(key, last_status="error", last_message=f"{type(e).__name__}: {e}"[:300])
                self._count(key, True)
            finally:
                self._update(key, running=False, last_end=datetime.now().isoformat(timespec="seconds"))
                lock.release()

        return runner

    def _update(self, key: str, **fields):
        with self._state_lock:
            self._state.setdefault(key, {}).update(fields)

    def _count(self, key: str, failed: bool):
        with self._state_lock:
            st = self._state.setdefault(key, {})
            st["consecutive_errors"] = (st.get("consecutive_errors") or 0) + 1 if failed else 0

    # job bodies
    def _social(self, platforms: Optional[List[str]] = None):
        return lambda: self.pipeline.run_full_cycle(platforms=platforms)

    @staticmethod
    def _prospect():
        totals = ProspectEngine().run()
        try:
            from showcase.pages import build_for_top
            totals.update(build_for_top())
        except Exception as e:
            logger.error(f"Showcase pages failed: {e}")
        return totals

    @staticmethod
    def _pages():
        from showcase.pages import build_for_top
        return build_for_top()

    def _inbox(self):
        return inbox.InboxWatcher(notifier=self.telegram).poll()

    def _digest(self):
        return automation.send_digest(self.telegram, self.health.problems(self.jobs_snapshot()))

    def _telegram_catch_up(self):
        return automation.telegram_catch_up(self.telegram, self.health.problems(self.jobs_snapshot()))

    def _health(self):
        return {"alerts": self.health.alert(self.telegram, self.jobs_snapshot())}

    @staticmethod
    def _live_check():
        from showcase.pages import check_live
        return check_live()

    def _job(self, key: str, group: str, fn, trigger):
        self.scheduler.add_job(self._wrap(key, group, fn), trigger, id=key, name=JOB_NAMES[key], replace_existing=True)

    def add_jobs(self):
        self._job("reddit_ingestion_job", "social", self._social(["reddit"]),
                  IntervalTrigger(minutes=settings.REDDIT_POLL_INTERVAL_MINUTES, jitter=45))
        self._job("twitter_ingestion_job", "social", self._social(["twitter"]), IntervalTrigger(minutes=45, jitter=60))
        self._job("meta_ingestion_job", "social", self._social(["meta"]), CronTrigger(hour="10,16", minute="0"))
        if self.bluesky_enabled:
            self._job("bluesky_ingestion_job", "social", self._social(["bluesky"]),
                      IntervalTrigger(minutes=settings.BLUESKY_POLL_INTERVAL_MINUTES, jitter=60))
        self._job("maps_prospector_job", "prospect", self._prospect,
                  CronTrigger(hour=settings.PROSPECT_DAILY_RUN_HOUR, minute=30, jitter=300))
        self._job("followups_job", "outreach", automation.run_followups, IntervalTrigger(minutes=60, jitter=120))
        if self.inbox_enabled:
            self._job("inbox_job", "outreach", self._inbox, IntervalTrigger(minutes=settings.INBOX_POLL_MINUTES, jitter=30))
        self._job("digest_job", "outreach", self._digest,
                  CronTrigger(hour=settings.DIGEST_HOUR, minute=settings.DIGEST_MINUTE))
        self._job("health_job", "maintenance", self._health, IntervalTrigger(minutes=60, jitter=120))
        self._job("backup_job", "maintenance", automation.backup_database, CronTrigger(hour=13, minute=15))
        self._job("live_check_job", "maintenance", self._live_check, IntervalTrigger(minutes=60, jitter=300))
        self._job("telegram_catchup_job", "outreach", self._telegram_catch_up, IntervalTrigger(minutes=30, jitter=60))
        # Age / last update / traffic for saved websites, a batch every 2 hours
        self._job("history_job", "prospect", ProspectEngine.backfill_history, IntervalTrigger(minutes=120, jitter=300))

    def run_now(self, kind: str) -> bool:
        """Queues an immediate run. Returns False if that kind is already running."""
        if kind == "social":
            key, group = MANUAL[kind]
            fn = self._social(None)
        elif kind in MANUAL:
            key, group = MANUAL[kind]
            fn = {"prospect": self._prospect, "pages": self._pages, "history": ProspectEngine.backfill_history, "followups": automation.run_followups,
                  "inbox": self._inbox, "digest": self._digest}[kind]
        else:
            raise ValueError(f"Unknown job kind: {kind}")
        if self._locks[group].locked():
            return False
        self.scheduler.add_job(
            self._wrap(key, group, fn), DateTrigger(run_date=datetime.now()),
            id=f"manual_{kind}_{int(time.time() * 1000)}", name=f"Manual {JOB_NAMES.get(key, key)}",
        )
        return True

    # ------------------------------------------------------------------ lifecycle

    def start(self, startup_scan: bool = True):
        # Apply the current priority rules to everything already saved
        try:
            from prospector.priority import reprioritize
            print(f"[ENGINE] Prospect priorities refreshed: {reprioritize()}", flush=True)
        except Exception as e:
            logger.error(f"Reprioritize failed: {e}")
        self.add_jobs()
        self.scheduler.start()
        if self.listener.is_configured():
            threading.Thread(target=self.listener.start_polling, daemon=True, name="telegram-listener").start()
            print("[ENGINE] Telegram button listener started.", flush=True)
        if startup_scan:
            self.run_now("social")
        # Missed digest (PC off, Telegram down) is handled by the 30-minute Telegram catch-up job
        self.scheduler.add_job(self._wrap("backup_job", "maintenance", automation.backup_database),
                               DateTrigger(run_date=datetime.now()), id="startup_backup")
        print(
            f"[ENGINE] SynexLabs Lead Engine is RUNNING.\n"
            f"  - Social: Reddit {settings.REDDIT_POLL_INTERVAL_MINUTES} min, X 45 min, "
            f"Bluesky {'on' if self.bluesky_enabled else 'off'}, Meta 10:00 & 16:00\n"
            f"  - Maps prospector + pages: daily at {settings.PROSPECT_DAILY_RUN_HOUR:02d}:30\n"
            f"  - Follow-ups hourly · Inbox {'every ' + str(settings.INBOX_POLL_MINUTES) + ' min' if self.inbox_enabled else 'off'}"
            f" · Digest {settings.DIGEST_HOUR:02d}:{settings.DIGEST_MINUTE:02d}",
            flush=True,
        )

    def stop(self):
        self.listener.stop()
        try:
            self.scheduler.shutdown(wait=False)
        except Exception:
            pass

    def jobs_snapshot(self) -> List[Dict[str, Any]]:
        rows, seen = [], set()
        with self._state_lock:
            state = {k: dict(v) for k, v in self._state.items()}
        for job in self.scheduler.get_jobs():
            if job.id.startswith(("manual_", "catchup_", "startup_")):
                continue
            seen.add(job.id)
            rows.append({
                "id": job.id,
                "name": JOB_NAMES.get(job.id, job.name),
                "next_run": job.next_run_time.isoformat(timespec="seconds") if job.next_run_time else None,
                **state.get(job.id, {}),
            })
        for key, st in state.items():
            if key not in seen:
                rows.append({"id": key, "name": JOB_NAMES.get(key, key), "next_run": None, **st})
        return rows


def run_scheduled_engine():
    """CLI mode (`python main.py schedule`): runs in the foreground until Ctrl+C."""
    service = EngineService()
    service.start(startup_scan=True)
    print("Press Ctrl+C to stop.", flush=True)
    try:
        while True:
            time.sleep(1)
    except (KeyboardInterrupt, SystemExit):
        service.stop()
        print("\n[SCHEDULER] Gracefully stopped scheduler.")
