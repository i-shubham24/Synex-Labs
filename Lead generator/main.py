import os
import sys
import argparse

# Ensure UTF-8 output on Windows consoles
if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    except Exception:
        pass

# Background mode (pythonw / log file): keep rich from wrapping log lines at 80 columns
if sys.stdout is None or not sys.stdout.isatty():
    os.environ.setdefault("COLUMNS", "160")

from rich.console import Console
from rich.table import Table

from database.db import init_db
from database.repository import LeadRepository
from pipeline import IntentEnginePipeline
from scheduler.job_runner import run_scheduled_engine
from brain.gemini_analyzer import GeminiAnalyzer
from ingestion.meta_scraper import MetaScraper
from ingestion.twitter_scraper import TwitterScraper
from delivery.telegram_bot import TelegramAlerter

console = Console()


def cmd_run_once(platform: str = "all"):
    """Runs a single pass of ingestion and Gemini qualification."""
    pipeline = IntentEnginePipeline()
    platforms = None if platform == "all" else [platform]
    pipeline.run_full_cycle(platforms=platforms)


def cmd_schedule():
    """Starts the continuous multi-platform background scheduler."""
    run_scheduled_engine()


def cmd_meta_login():
    """Launches interactive browser to log in and save Facebook/Instagram cookies."""
    MetaScraper.interactive_login_session()


def cmd_twitter_login():
    """Launches interactive browser to log in and save X/Twitter cookies."""
    TwitterScraper.interactive_login_session()


def cmd_show_leads():
    """Displays qualified buyer leads in a clean terminal table."""
    init_db()
    leads = LeadRepository.get_qualified_leads(status="new", limit=30)
    if not leads:
        console.print("[yellow]No new qualified leads found yet. Run `python main.py run-once`.[/yellow]")
        return

    table = Table(title="🔥 SynexLabs Qualified Buyer Leads (Multi-Platform)")
    table.add_column("ID", style="dim", width=4)
    table.add_column("Platform", style="cyan", width=10)
    table.add_column("Channel / Source", style="dim", width=22)
    table.add_column("Category", style="magenta", width=18)
    table.add_column("Budget", style="yellow", width=14)
    table.add_column("Title / Query", style="white")
    table.add_column("Draft Icebreaker", style="italic green")

    for lead in leads:
        table.add_row(
            str(lead["id"]),
            lead["platform"].upper(),
            lead["source_channel"] or "N/A",
            lead["project_category"] or "Custom Dev",
            lead["budget_indicator"] or "N/A",
            lead["title"][:40] + ("..." if len(lead["title"]) > 40 else ""),
            lead["draft_icebreaker"][:70] + ("..." if len(lead["draft_icebreaker"] or "") > 70 else ""),
        )

    console.print(table)


def cmd_test_ai():
    """Tests the Gemini analyzer with sample commercial buyer post."""
    console.print("[bold cyan]Testing Gemini Flash Lead Analyzer...[/bold cyan]")
    analyzer = GeminiAnalyzer()

    sample_post = {
        "platform": "reddit",
        "source_channel": "r/smallbusiness",
        "title": "Need an agency to rebuild our e-commerce store with custom design & high speed",
        "author": "boutique_founder",
        "flair": "Hiring",
        "content": (
            "We run a high-volume apparel store currently on a bloated template. "
            "Our conversion rate dropped and load time is over 4 seconds. "
            "Need a modern Next.js or headless Shopify rebuild. Budget is $5,000 - $8,000. Looking for proven builders."
        ),
    }

    result = analyzer.analyze_post(**sample_post)
    console.print("\n[bold green]Gemini Qualification Output:[/bold green]")
    console.print(f"  Valid Lead: [bold]{result.is_valid_lead}[/bold]")
    console.print(f"  Category: [cyan]{result.project_category}[/cyan]")
    console.print(f"  Budget: [yellow]{result.budget_indicator}[/yellow]")
    console.print(f"  Draft Icebreaker:\n    [italic green]\"{result.draft_icebreaker}\"[/italic green]")
    console.print(f"  Reasoning: {result.reasoning}")


def cmd_test_telegram():
    """Tests dispatching a sample lead alert to the configured Telegram bot."""
    console.print("[bold cyan]Testing Telegram Lead Card Dispatch...[/bold cyan]")
    alerter = TelegramAlerter()
    if not alerter.is_configured():
        console.print("[red]Telegram credentials not set. Add TELEGRAM_BOT_TOKEN and TELEGRAM_CHAT_ID in .env[/red]")
        return

    sample_lead = {
        "id": 999,
        "platform": "reddit",
        "project_category": "E-commerce Build & Speed Optimization",
        "budget_indicator": "High ($5k - $8k)",
        "author": "boutique_founder",
        "source_channel": "r/ecommerce",
        "title": "Need an agency to rebuild our e-commerce store with custom design & high speed",
        "url": "https://reddit.com/r/ecommerce",
        "draft_icebreaker": (
            "Hey! Saw you're dealing with a 4s+ load time and low conversions on your apparel store. "
            "At SynexLabs we specialize in headless high-speed e-commerce and would love to show you a couple of quick asset optimization wins you can implement today."
        ),
    }

    success = alerter.send_lead_alert(sample_lead)
    if success:
        console.print("[bold green]Success! Test alert sent to Telegram chat.[/bold green]")
    else:
        console.print("[bold red]Failed to send alert. Check token and chat ID.[/bold red]")


def _split(value, sep):
    return [v.strip() for v in value.split(sep) if v.strip()] if value else None


def cmd_prospect(args):
    """Finds local businesses with no website or a weak one and alerts the hottest."""
    from prospector.engine import ProspectEngine

    engine = ProspectEngine(source=args.source)
    engine.run(
        niches=_split(args.niche, ","),
        cities=_split(args.city, ";"),
        max_searches=args.limit,
        alert=not args.no_alert,
    )


def cmd_show_prospects(args):
    """Displays the hottest saved prospects."""
    from database.prospect_repository import ProspectRepository
    from prospector.scoring import TIER_LABELS

    init_db()
    status = None if args.status == "all" else args.status
    rows = ProspectRepository.list(status=status, limit=args.limit or 30)
    if not rows:
        console.print("[yellow]No prospects yet. Run `python main.py prospect`.[/yellow]")
        return

    table = Table(title="🗺  SynexLabs Maps Prospects (hottest first)")
    table.add_column("ID", style="dim", width=4)
    table.add_column("Heat", style="bold red", justify="right", width=4)
    table.add_column("Status", style="dim", width=9)
    table.add_column("Business", style="white")
    table.add_column("Niche / City", style="cyan")
    table.add_column("Contact", style="green")
    table.add_column("Why", style="yellow")
    for r in rows:
        contact = r.get("phone") or r.get("email") or (r.get("socials") or [""])[0] or "-"
        why = (r.get("issues") or [TIER_LABELS.get(r.get("tier"), "")])[0]
        table.add_row(
            str(r["id"]), str(r["heat_score"]), r["status"], r["name"],
            f"{r.get('niche')} · {r.get('city')}", contact, why[:60],
        )
    console.print(table)
    stats = ProspectRepository.get_stats()
    console.print(f"[dim]Total saved: {stats['total']} | by tier: {stats['by_tier']} | by status: {stats['by_status']}[/dim]")


def cmd_export_prospects(args):
    """Writes all pitchable prospects to a CSV call list."""
    from pathlib import Path
    from prospector.engine import ProspectEngine

    init_db()
    out = Path(args.out) if args.out else Path(__file__).parent / "data" / "prospects.csv"
    count = ProspectEngine.export_csv(out)
    console.print(f"[green]Exported {count} prospects to {out}[/green]")


def cmd_audit_site(args):
    """Audits one website and prints the findings (handy before a sales call)."""
    from prospector.site_audit import audit_website
    from prospector.scoring import score_business, TIER_LABELS
    from prospector.sources import Business

    if not args.url:
        console.print("[red]Pass a site: python main.py audit-site --url https://example.com[/red]")
        return
    console.print(f"[cyan]Auditing {args.url} ...[/cyan]")
    audit = audit_website(args.url)
    tier, heat, issues = score_business(Business(source="manual", place_id="-", name="-", website=args.url), audit)
    console.print(f"[bold]{TIER_LABELS.get(tier, tier)}[/bold]  heat {heat}/100")
    for issue in issues or ["No problems found by the automated checks"]:
        console.print(f"  • {issue}")
    details = {
        "final_url": audit.final_url, "status": audit.status_code, "load_s": audit.response_seconds,
        "https": audit.https, "mobile_viewport": audit.has_viewport, "copyright_year": audit.copyright_year,
        "generator": audit.generator, "pagespeed_mobile": audit.pagespeed_mobile, "emails": audit.emails,
        "socials": audit.socials,
    }
    console.print(f"[dim]{details}[/dim]")


def _engine_running(port: int) -> bool:
    import requests
    try:
        r = requests.get(f"http://127.0.0.1:{port}/api/health", timeout=1.5)
        return r.ok and r.json().get("app") == "synex-lead-engine"
    except Exception:
        return False


def _message_box(text: str, error: bool = False):
    """Visible feedback when started from the desktop shortcut (no console window)."""
    if sys.platform == "win32":
        try:
            import ctypes
            ctypes.windll.user32.MessageBoxW(0, text, "Synex Lead Engine", 0x10 if error else 0x40)
        except Exception:
            pass


def _redirect_output_to_log():
    import logging
    from config.settings import BASE_DIR

    log_path = BASE_DIR / "data" / "engine.log"
    log_path.parent.mkdir(parents=True, exist_ok=True)
    if log_path.exists() and log_path.stat().st_size > 2_000_000:
        log_path.replace(log_path.with_suffix(".log.1"))
    from config.redact import RedactingStream
    stream = RedactingStream(open(log_path, "a", encoding="utf-8", buffering=1))
    sys.stdout = stream
    sys.stderr = stream
    logging.basicConfig(
        level=logging.INFO,
        stream=stream,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
        force=True,
    )
    for noisy in ("httpx", "httpx2", "httpcore", "urllib3", "google_genai", "apscheduler"):
        logging.getLogger(noisy).setLevel(logging.WARNING)


def cmd_start(args):
    """
    Desktop-shortcut entry point: runs the engine in the background and opens the dashboard.
    If the engine is already running, it just opens the dashboard again.
    Closing the browser never stops the engine; use the dashboard's Stop button or `main.py stop`.
    """
    import threading
    import webbrowser
    from config.settings import settings

    port = settings.DASHBOARD_PORT
    url = f"http://127.0.0.1:{port}/"
    if _engine_running(port):
        if not args.no_browser:
            webbrowser.open(url)
        print(f"Engine already running. Dashboard: {url}")
        return

    print(f"Starting the lead engine in the background. Dashboard: {url}  Log: data/engine.log")
    _redirect_output_to_log()

    from scheduler.job_runner import EngineService
    from dashboard.server import DashboardServer, SESSION_PATH

    try:
        service = EngineService()
        dash = DashboardServer(service, port=port)
    except OSError:
        _message_box(
            f"Could not start: port {port} is used by another program.\n"
            f"Set DASHBOARD_PORT in .env to a free port and try again.",
            error=True,
        )
        return
    except Exception as e:
        import logging
        logging.exception("Engine startup failed")
        _message_box(f"Could not start the lead engine:\n{e}\n\nDetails are in data/engine.log", error=True)
        return

    dash.on_stop = dash.shutdown
    service.start(startup_scan=settings.ENGINE_STARTUP_SCAN)
    print(f"[ENGINE] Dashboard at {url}", flush=True)
    if not args.no_browser:
        threading.Timer(0.4, webbrowser.open, args=(url,)).start()

    try:
        dash.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        service.stop()
        try:
            SESSION_PATH.unlink()
        except OSError:
            pass
        print("[ENGINE] Stopped.", flush=True)
        sys.stdout.flush()
        # Background job threads may be mid-request; SQLite commits per statement, so exit now.
        os._exit(0)


def cmd_stop(args):
    """Stops a background engine started with `main.py start`."""
    import json
    import re
    import requests
    from config.settings import settings
    from dashboard.server import SESSION_PATH

    port, token = settings.DASHBOARD_PORT, None
    if SESSION_PATH.exists():
        session = json.loads(SESSION_PATH.read_text(encoding="utf-8"))
        port, token = session["port"], session["token"]
    elif _engine_running(port):
        # Session file missing (older version, or deleted): read the token from the local dashboard page
        try:
            page = requests.get(f"http://127.0.0.1:{port}/", timeout=5).text
            m = re.search(r'name="engine-token" content="([^"]+)"', page)
            token = m.group(1) if m else None
        except requests.RequestException:
            token = None
    if not token:
        console.print("[yellow]No running engine found.[/yellow]")
        return
    try:
        requests.post(f"http://127.0.0.1:{port}/api/stop", headers={"X-Engine-Token": token}, timeout=5)
        console.print("[green]Stop signal sent. The engine is shutting down.[/green]")
    except requests.RequestException:
        console.print("[yellow]Engine did not answer; it is probably already stopped.[/yellow]")


def cmd_clean_excluded(args):
    """Deletes saved leads we never pitch: government, embassies, tax offices, real estate."""
    import shutil
    from database.db import get_connection
    from prospector.filters import is_excluded, EXCLUDED_NICHES
    from showcase.pages import PAGES_DIR

    init_db()
    with get_connection() as conn:
        rows = conn.execute("SELECT id, name, niche, slug FROM prospects;").fetchall()
        doomed = [r for r in rows if is_excluded(r["name"], r["niche"])]
        ids = [r["id"] for r in doomed]
        if args.dry_run or not ids:
            console.print(f"[yellow]{len(ids)} leads match the exclusion rules{' (dry run, nothing deleted)' if args.dry_run else ''}.[/yellow]")
            for r in doomed[:30]:
                console.print(f"  {r['name']} [dim]({r['niche']})[/dim]")
            return
        marks = ",".join("?" for _ in ids)
        conn.execute(f"DELETE FROM emails WHERE prospect_id IN ({marks});", ids)
        conn.execute(f"DELETE FROM prospects WHERE id IN ({marks});", ids)
        niche_marks = ",".join("?" for _ in EXCLUDED_NICHES)
        conn.execute(f"DELETE FROM prospect_searches WHERE lower(niche) IN ({niche_marks});", tuple(EXCLUDED_NICHES))
        conn.commit()
    removed_pages = 0
    for r in doomed:
        if r["slug"] and (PAGES_DIR / r["slug"]).is_dir():
            shutil.rmtree(PAGES_DIR / r["slug"], ignore_errors=True)
            removed_pages += 1
    console.print(f"[green]Deleted {len(ids)} excluded leads[/green] (and {removed_pages} page folders). "
                  f"A copy of the database from before is in data/backups.")


def cmd_automation(command: str):
    """One-off runs of the automation jobs (the background engine runs them on a schedule)."""
    init_db()
    if command == "build-pages":
        from showcase.pages import build_for_top
        console.print(build_for_top())
    elif command == "run-followups":
        from outreach.automation import run_followups
        console.print(run_followups())
    elif command == "check-inbox":
        from outreach.inbox import InboxWatcher, is_configured
        if not is_configured():
            console.print("[yellow]Inbox is not configured (IMAP_HOST / IMAP_USER / IMAP_PASSWORD).[/yellow]")
            return
        console.print(InboxWatcher(notifier=TelegramAlerter()).poll())
    elif command == "send-digest":
        from outreach.automation import send_digest, build_digest, HealthMonitor
        alerter = TelegramAlerter()
        if alerter.is_configured():
            console.print(send_digest(alerter, HealthMonitor().problems([])))
        else:
            console.print(build_digest([]))
    elif command == "backup":
        from outreach.automation import backup_database
        console.print(backup_database())


def main():
    parser = argparse.ArgumentParser(
        description="SynexLabs Lead Engine: social intent listening (Reddit, X, Bluesky, Meta) + Maps prospector"
    )
    parser.add_argument(
        "command",
        nargs="?",
        default="run-once",
        choices=[
            "run-once",
            "ingest-reddit",
            "ingest-twitter",
            "ingest-meta",
            "start",
            "stop",
            "build-pages",
            "clean-excluded",
            "run-followups",
            "check-inbox",
            "send-digest",
            "backup",
            "ingest-bluesky",
            "prospect",
            "show-prospects",
            "export-prospects",
            "audit-site",
            "meta-login",
            "twitter-login",
            "schedule",
            "show-leads",
            "test-ai",
            "test-telegram",
        ],
        help="Command to execute",
    )
    prospect_opts = parser.add_argument_group("prospector options")
    prospect_opts.add_argument("--niche", help='Comma-separated niches, e.g. "dentist,gym"')
    prospect_opts.add_argument("--city", help='Semicolon-separated cities, e.g. "Austin, TX;Pune, India"')
    prospect_opts.add_argument("--source", choices=["auto", "google", "osm"], help="Business data source")
    prospect_opts.add_argument("--limit", type=int, help="Max searches (prospect) or rows (show-prospects)")
    prospect_opts.add_argument("--no-alert", action="store_true", help="Save prospects without Telegram cards")
    prospect_opts.add_argument("--status", default="new", help="show-prospects filter: new, alerted, contacted, skipped, all")
    prospect_opts.add_argument("--out", help="export-prospects CSV path")
    prospect_opts.add_argument("--url", help="audit-site target URL")
    parser.add_argument("--dry-run", action="store_true", help="clean-excluded: only list what would be deleted")
    parser.add_argument("--no-browser", action="store_true", help="start: run in background without opening the dashboard")

    args = parser.parse_args()

    if args.command == "run-once":
        cmd_run_once(platform="all")
    elif args.command == "ingest-reddit":
        cmd_run_once(platform="reddit")
    elif args.command == "ingest-twitter":
        cmd_run_once(platform="twitter")
    elif args.command == "ingest-meta":
        cmd_run_once(platform="meta")
    elif args.command == "clean-excluded":
        cmd_clean_excluded(args)
    elif args.command in ("build-pages", "run-followups", "check-inbox", "send-digest", "backup"):
        cmd_automation(args.command)
    elif args.command == "start":
        cmd_start(args)
    elif args.command == "stop":
        cmd_stop(args)
    elif args.command == "ingest-bluesky":
        cmd_run_once(platform="bluesky")
    elif args.command == "prospect":
        cmd_prospect(args)
    elif args.command == "show-prospects":
        cmd_show_prospects(args)
    elif args.command == "export-prospects":
        cmd_export_prospects(args)
    elif args.command == "audit-site":
        cmd_audit_site(args)
    elif args.command == "meta-login":
        cmd_meta_login()
    elif args.command == "twitter-login":
        cmd_twitter_login()
    elif args.command == "schedule":
        cmd_schedule()
    elif args.command == "show-leads":
        cmd_show_leads()
    elif args.command == "test-ai":
        cmd_test_ai()
    elif args.command == "test-telegram":
        cmd_test_telegram()


if __name__ == "__main__":
    main()
