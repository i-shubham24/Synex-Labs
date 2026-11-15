import logging
import threading
from apscheduler.schedulers.blocking import BlockingScheduler
from apscheduler.triggers.interval import IntervalTrigger
from apscheduler.triggers.cron import CronTrigger

from config.settings import settings
from pipeline import IntentEnginePipeline
from delivery.telegram_listener import TelegramCallbackListener

logger = logging.getLogger("scheduler")


def run_scheduled_engine():
    """
    Starts the multi-platform APScheduler with staggered anti-ban intervals:
    - Reddit: every 15 minutes
    - Twitter / X: every 45 minutes
    - Meta Ad Comments: twice daily (10:00 AM & 4:00 PM)
    - Telegram Callback Listener: background daemon
    """
    pipeline = IntentEnginePipeline()
    scheduler = BlockingScheduler()

    # 1. Reddit Ingestion Job (Every 15m with 45s jitter)
    scheduler.add_job(
        func=lambda: pipeline.run_full_cycle(platforms=["reddit"]),
        trigger=IntervalTrigger(minutes=settings.REDDIT_POLL_INTERVAL_MINUTES, jitter=45),
        id="reddit_ingestion_job",
        name="Reddit Ingestion (15m)",
        replace_existing=True,
    )

    # 2. Twitter / X Ingestion Job (Every 45m with 60s jitter)
    scheduler.add_job(
        func=lambda: pipeline.run_full_cycle(platforms=["twitter"]),
        trigger=IntervalTrigger(minutes=45, jitter=60),
        id="twitter_ingestion_job",
        name="Twitter/X Ingestion (45m)",
        replace_existing=True,
    )

    # 3. Meta Ad Comments Job (Twice Daily: 10:00 AM & 4:00 PM)
    scheduler.add_job(
        func=lambda: pipeline.run_full_cycle(platforms=["meta"]),
        trigger=CronTrigger(hour="10,16", minute="0"),
        id="meta_ingestion_job",
        name="Meta Ad Comments (Twice Daily)",
        replace_existing=True,
    )

    # 4. Telegram Interactive Callback Listener (Background Daemon)
    listener = TelegramCallbackListener()
    if listener.is_configured():
        listener_thread = threading.Thread(target=listener.start_polling, daemon=True)
        listener_thread.start()
        print("[SCHEDULER] Telegram interactive button listener started in background.")

    print(
        f"[SCHEDULER] SynexLabs Multi-Platform Ingestion Engine is RUNNING.\n"
        f"  - Reddit: every {settings.REDDIT_POLL_INTERVAL_MINUTES} min\n"
        f"  - Twitter/X: every 45 min\n"
        f"  - Meta Ads: 10:00 AM & 4:00 PM\n"
        f"Press Ctrl+C to stop."
    )

    # Run initial cycle on startup for active platforms
    try:
        pipeline.run_full_cycle(platforms=["reddit", "twitter"])
        scheduler.start()
    except (KeyboardInterrupt, SystemExit):
        listener.stop()
        print("\n[SCHEDULER] Gracefully stopped scheduler.")
