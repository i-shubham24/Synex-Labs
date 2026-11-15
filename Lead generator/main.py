import sys
import argparse

# Ensure UTF-8 output on Windows consoles
if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    except Exception:
        pass

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
    if platform == "all":
        platforms = ["reddit", "twitter"]
    else:
        platforms = [platform]
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


def main():
    parser = argparse.ArgumentParser(
        description="SynexLabs Intent Ingestion Engine (Multi-Platform: Reddit, Twitter/X, Meta)"
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
            "meta-login",
            "twitter-login",
            "schedule",
            "show-leads",
            "test-ai",
            "test-telegram",
        ],
        help="Command to execute",
    )

    args = parser.parse_args()

    if args.command == "run-once":
        cmd_run_once(platform="all")
    elif args.command == "ingest-reddit":
        cmd_run_once(platform="reddit")
    elif args.command == "ingest-twitter":
        cmd_run_once(platform="twitter")
    elif args.command == "ingest-meta":
        cmd_run_once(platform="meta")
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
