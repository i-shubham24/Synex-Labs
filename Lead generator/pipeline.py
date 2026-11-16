import logging
import sys
from typing import Dict, Any, List, Optional

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
from ingestion.reddit_scraper import RedditScraper
from ingestion.twitter_scraper import TwitterScraper
from ingestion.meta_scraper import MetaScraper
from ingestion.bluesky_scraper import BlueskyScraper
from ingestion.base import ScrapedPost
from brain.gemini_analyzer import GeminiAnalyzer, GeminiUnavailable, LeadAnalysisResult
from delivery.telegram_bot import TelegramAlerter

logger = logging.getLogger("pipeline")
console = Console()


class IntentEnginePipeline:
    """
    Unified Multi-Platform Ingestion & Qualification Pipeline.
    Coordinates:
    - Module 1: Reddit, Twitter/X, Bluesky, and Meta Ads Scrapers
    - Module 2: Gemini Flash AI Brain
    - Module 3: Telegram Alerting Layer
    """

    def __init__(self):
        init_db()
        self.reddit_scraper = RedditScraper()
        self.twitter_scraper = TwitterScraper()
        self.meta_scraper = MetaScraper()
        self.bluesky_scraper = BlueskyScraper()
        self.gemini_analyzer = GeminiAnalyzer()
        self.telegram_alerter = TelegramAlerter()

    def run_full_cycle(self, platforms: Optional[List[str]] = None) -> Dict[str, Any]:
        """
        Executes a complete ingestion, analysis, and dispatch cycle across specified platforms.
        Default platforms: Reddit, Twitter/X, plus Bluesky when configured
        (Meta runs twice daily via scheduler).
        """
        target_platforms = platforms or self.default_platforms()
        console.print("[bold cyan]🚀 Starting Multi-Platform Intent Ingestion Pipeline[/bold cyan]")
        console.print(f"[dim]Active platforms: {', '.join(target_platforms)}[/dim]\n")

        all_scraped: List[ScrapedPost] = []

        if "reddit" in target_platforms:
            console.print("[bold blue]Scanning Reddit Subreddits...[/bold blue]")
            reddit_posts = self.reddit_scraper.fetch_new_posts()
            console.print(f"  📥 Reddit: Found [green]{len(reddit_posts)}[/green] candidates.")
            all_scraped.extend(reddit_posts)

        if "twitter" in target_platforms:
            console.print("[bold blue]Scanning X (Twitter) Search...[/bold blue]")
            twitter_posts = self.twitter_scraper.fetch_new_posts()
            console.print(f"  📥 Twitter: Found [green]{len(twitter_posts)}[/green] candidates.")
            all_scraped.extend(twitter_posts)

        if "bluesky" in target_platforms:
            if self.bluesky_scraper.is_configured():
                console.print("[bold blue]Scanning Bluesky Search...[/bold blue]")
                bluesky_posts = self.bluesky_scraper.fetch_new_posts()
                console.print(f"  📥 Bluesky: Found [green]{len(bluesky_posts)}[/green] candidates.")
                all_scraped.extend(bluesky_posts)
            else:
                console.print("[dim]Bluesky skipped: add BLUESKY_HANDLE and BLUESKY_APP_PASSWORD to .env.[/dim]")

        if "meta" in target_platforms:
            console.print("[bold blue]Scanning Meta Ad Comments...[/bold blue]")
            meta_posts = self.meta_scraper.fetch_new_posts()
            console.print(f"  📥 Meta: Found [green]{len(meta_posts)}[/green] candidates.")
            all_scraped.extend(meta_posts)

        # --- Deduplicate and Store in SQLite ---
        new_saved_count = 0
        duplicates_count = 0

        for post in all_scraped:
            row_id = LeadRepository.save_raw_post(
                platform=post.platform,
                post_id=post.post_id,
                title=post.title,
                content=post.content,
                url=post.url,
                source_channel=post.source_channel,
                author=post.author,
                flair=post.flair,
                created_utc=post.created_utc,
            )
            if row_id:
                new_saved_count += 1
            else:
                duplicates_count += 1

        console.print(
            f"\n💾 Database Sync: [bold green]{new_saved_count} new posts saved[/bold green], "
            f"[yellow]{duplicates_count} duplicates skipped[/yellow]."
        )

        # --- AI Qualification with Gemini ---
        valid_leads_count = self.process_pending_posts()

        # --- Telegram Dispatch ---
        alerted_count = self.dispatch_telegram_alerts()

        # Print summary
        self.print_summary_table()

        return {
            "scraped": len(all_scraped),
            "new_saved": new_saved_count,
            "duplicates": duplicates_count,
            "valid_leads": valid_leads_count,
            "telegram_alerted": alerted_count,
        }

    def default_platforms(self) -> List[str]:
        platforms = ["reddit", "twitter"]
        if self.bluesky_scraper.is_configured():
            platforms.append("bluesky")
        return platforms

    def process_pending_posts(self, limit: int = 30) -> int:
        """
        Processes posts in SQLite awaiting Gemini AI evaluation.
        If Gemini is unavailable the posts stay pending and are retried next cycle;
        no lead decision is ever made without the model.
        """
        pending_posts = LeadRepository.get_unprocessed_posts(limit=limit)
        if not pending_posts:
            console.print("[dim]No pending posts requiring AI processing.[/dim]")
            return 0

        if not self.gemini_analyzer.is_configured():
            console.print(
                f"[bold red]⚠ Gemini is not configured (GEMINI_API_KEY missing). "
                f"{len(pending_posts)} posts stay pending.[/bold red]"
            )
            return 0

        console.print(f"\n🧠 Evaluating [bold cyan]{len(pending_posts)}[/bold cyan] posts with Gemini Flash Analyzer...")
        valid_leads_count = 0

        for index, post in enumerate(pending_posts):
            post_id = post["id"]
            title = post["title"]
            source = post["source_channel"]
            platform = post["platform"]

            console.print(f"[dim]Analyzing {platform} #{post_id} from {source}: {(title or '')[:45]}...[/dim]")

            try:
                analysis: LeadAnalysisResult = self.gemini_analyzer.analyze_post(
                    platform=platform,
                    title=title,
                    content=post["content"],
                    source_channel=source,
                    author=post["author"],
                    flair=post.get("flair") or "",
                )
            except GeminiUnavailable as e:
                remaining = len(pending_posts) - index
                logger.error(f"Gemini unavailable: {e}")
                console.print(
                    f"[bold red]⚠ Gemini unavailable: {e}[/bold red]\n"
                    f"[yellow]{remaining} posts left pending, will retry next cycle.[/yellow]"
                )
                break
            except ValueError as e:
                logger.warning(f"Skipping post #{post_id} this cycle: {e}")
                console.print(f"  [yellow]Skipped (bad model output), will retry: {e}[/yellow]")
                continue

            LeadRepository.update_lead_analysis(
                lead_id=post_id,
                is_valid_lead=analysis.is_valid_lead,
                project_category=analysis.project_category,
                budget_indicator=analysis.budget_indicator,
                draft_icebreaker=analysis.draft_icebreaker,
                ai_reasoning=analysis.reasoning,
                confidence_score=analysis.confidence_score,
                country=analysis.country,
                first_website=analysis.first_website,
                old_website=analysis.old_website,
            )

            if analysis.is_valid_lead:
                valid_leads_count += 1
                console.print(
                    f"  ✨ [bold green]QUALIFIED BUYER LEAD![/bold green] "
                    f"Category: [cyan]{analysis.project_category}[/cyan] | Budget: [yellow]{analysis.budget_indicator}[/yellow]"
                )
                console.print(f"  💬 Icebreaker: [italic]{analysis.draft_icebreaker}[/italic]\n")
            else:
                console.print(f"  ❌ Disqualified: {analysis.reasoning}\n")

        return valid_leads_count

    def dispatch_telegram_alerts(self) -> int:
        """Dispatches any unalerted qualified buyer leads to Telegram channel."""
        unalerted = LeadRepository.get_qualified_leads(status="new", limit=20)
        if not unalerted:
            return 0

        alerted = 0
        for lead in unalerted:
            success = self.telegram_alerter.send_lead_alert(lead)
            if success:
                alerted += 1

        if alerted > 0:
            console.print(f"📲 Dispatched [bold green]{alerted} lead alert cards[/bold green] to Telegram channel.")
        return alerted

    def print_summary_table(self):
        """Displays rich table with multi-platform stats."""
        stats = LeadRepository.get_stats()
        table = Table(title="SynexLabs Intent Engine - Multi-Platform Database")
        table.add_column("Metric", style="cyan")
        table.add_column("Count", style="green", justify="right")

        table.add_row("Total Scraped Posts", str(stats["total_scraped"]))
        table.add_row("Qualified Buyer Leads", str(stats["valid_leads"]))
        table.add_row("Pending AI Evaluation", str(stats["pending_ai"]))
        table.add_row("Leads Contacted", str(stats["contacted"]))

        console.print(table)
