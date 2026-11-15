import logging
import time
import re
import random
import hashlib
from typing import List, Optional
from pathlib import Path

from config.settings import settings
from config.keywords import HIGH_INTENT_KEYWORDS, NEGATIVE_KEYWORDS
from database.repository import LeadRepository
from .base import BaseScraper, ScrapedPost

logger = logging.getLogger("ingestion.meta")

# Specific inquiry triggers in ad comments
COMMENT_INQUIRY_KEYWORDS = [
    "how much",
    "cost",
    "price",
    "pricing",
    "quote",
    "rates",
    "interested",
    "dm me",
    "details please",
    "send details",
    "info please",
    "can you build",
    "do you make",
    "need this for my",
    "need a website",
    "looking for",
    "rebuild",
    "redesign",
]


class MetaScraper(BaseScraper):
    """
    Module 1: Meta (Instagram / Facebook Ads Comments) Ingestion Layer (Phase 2).
    Visits configured competitor ad URLs and extracts prospective buyer comments.
    Strictly rate-limited (runs twice daily) with saved local cookies to prevent bot bans.
    """

    def __init__(self, target_ad_urls: Optional[List[str]] = None):
        super().__init__(platform="meta")
        self.target_ad_urls = target_ad_urls or settings.META_TARGET_AD_URLS
        self.auth_state_path = settings.META_AUTH_STATE_PATH

    def has_auth_state(self) -> bool:
        """Returns True if saved authentication state cookies exist."""
        return self.auth_state_path.exists()

    def fetch_new_posts(self) -> List[ScrapedPost]:
        """
        Visits target ad URLs with human-like stealth pacing and scrapes inquiry comments.
        """
        all_posts: List[ScrapedPost] = []

        try:
            from playwright.sync_api import sync_playwright
            from playwright_stealth.stealth import Stealth

            with sync_playwright() as p:
                browser = p.chromium.launch(
                    executable_path=settings.CHROME_EXECUTABLE_PATH,
                    headless=True,
                    args=[
                        "--disable-blink-features=AutomationControlled",
                        "--no-sandbox",
                    ],
                )

                # Load authenticated session if available
                context_args = {
                    "viewport": {"width": 1440, "height": 900},
                    "user_agent": random.choice(settings.USER_AGENTS),
                }
                if self.has_auth_state():
                    logger.info(f"[Meta] Loading saved auth cookies from {self.auth_state_path}")
                    context_args["storage_state"] = str(self.auth_state_path)
                else:
                    logger.info("[Meta] No auth cookies found. Running in public guest mode (run `python main.py meta-login` to authenticate).")

                context = browser.new_context(**context_args)
                page = context.new_page()
                Stealth().apply_stealth_sync(page)

                for i, ad_url in enumerate(self.target_ad_urls):
                    logger.info(f"[Meta] Visiting target ad: {ad_url[:70]}...")
                    comments = self._scrape_ad_comments(page, ad_url)
                    all_posts.extend(comments)

                    if i < len(self.target_ad_urls) - 1:
                        # Extra relaxed human delay for Meta safety
                        self.human_delay(min_sec=4.0, max_sec=9.0)

                browser.close()

        except Exception as e:
            logger.error(f"[Meta] Browser execution failed: {e}")

        logger.info(f"[Meta] Completed run: Found {len(all_posts)} candidate inquiry comments.")
        return all_posts

    def _scrape_ad_comments(self, page, ad_url: str) -> List[ScrapedPost]:
        """Navigates to ad page, scrolls to comments, and extracts inquiry leads."""
        scraped_posts: List[ScrapedPost] = []

        try:
            page.goto(ad_url, wait_until="domcontentloaded", timeout=35000)
            time.sleep(random.uniform(3.0, 5.5))

            # Dismiss common Meta dialogs/cookie banners
            self._dismiss_meta_overlays(page)

            # Scroll gently to trigger comment rendering
            for _ in range(2):
                page.mouse.wheel(0, random.randint(500, 800))
                time.sleep(random.uniform(1.8, 3.2))

            # Query potential comment containers across FB / Instagram / Ad Library
            comment_selectors = [
                'div[role="article"]',
                'ul[class*="comments"] > li',
                'div[data-ad-preview="message"]',
                'div[class*="comment"]',
            ]

            found_elements = []
            for sel in comment_selectors:
                elements = page.locator(sel).all()
                if elements:
                    found_elements = elements
                    break

            for elem in found_elements[:20]:
                try:
                    text = elem.inner_text().strip()
                    if not text or len(text) < 10:
                        continue

                    # Filter for commercial inquiry intent
                    if not self._is_comment_inquiry(text):
                        continue

                    # Generate deterministic unique ID from ad URL + comment text hash
                    raw_hash = hashlib.sha1(f"{ad_url}:{text}".encode("utf-8")).hexdigest()[:16]
                    comment_id = f"meta_{raw_hash}"

                    if LeadRepository.is_post_scraped(self.platform, comment_id):
                        continue

                    lines = [line.strip() for line in text.split("\n") if line.strip()]
                    author = lines[0] if len(lines) > 1 else "meta_user"
                    content = " ".join(lines[1:]) if len(lines) > 1 else text

                    scraped_posts.append(
                        ScrapedPost(
                            platform=self.platform,
                            post_id=comment_id,
                            title=f"Ad Comment Inquiry from {author}",
                            content=content,
                            url=ad_url,
                            source_channel="competitor_meta_ad",
                            author=author,
                            flair="Ad Comment",
                            created_utc=int(time.time()),
                        )
                    )
                except Exception:
                    continue

        except Exception as e:
            logger.warning(f"[Meta] Error scraping {ad_url}: {e}")

        return scraped_posts

    def _dismiss_meta_overlays(self, page):
        """Dismisses cookie consents and login nag modals."""
        try:
            page.keyboard.press("Escape")
            # Click common 'Allow essential cookies' or 'Decline optional' buttons
            closers = page.locator(
                'button:has-text("Decline"), button:has-text("Only essential"), button[aria-label="Close"]'
            )
            if closers.count() > 0:
                closers.first.click()
        except Exception:
            pass

    def _is_comment_inquiry(self, text: str) -> bool:
        """Determines if a comment expresses commercial interest or hiring intent."""
        lower = text.lower()
        # Must match at least one inquiry trigger
        has_trigger = any(kw in lower for kw in COMMENT_INQUIRY_KEYWORDS)
        # Filter obvious bots/spam
        is_spam = any(neg in lower for neg in NEGATIVE_KEYWORDS)
        return has_trigger and not is_spam

    @staticmethod
    def interactive_login_session():
        """
        Interactive helper CLI tool: opens a visible Chrome window to let
        the human operator log into Facebook/Instagram once and saves
        cookies to auth_state/meta_cookies.json for headless runs.
        """
        auth_dir = settings.META_AUTH_STATE_PATH.parent
        auth_dir.mkdir(parents=True, exist_ok=True)

        from playwright.sync_api import sync_playwright

        print("\n[META LOGIN] Launching visible browser window...")
        print("[META LOGIN] Please log in to Facebook / Instagram in the opened window.")
        print("[META LOGIN] Once logged in, press Enter in this terminal to save your session cookies.\n")

        with sync_playwright() as p:
            browser = p.chromium.launch(
                executable_path=settings.CHROME_EXECUTABLE_PATH,
                headless=False,
            )
            context = browser.new_context(viewport={"width": 1280, "height": 800})
            page = context.new_page()
            page.goto("https://www.facebook.com")

            input(">>> Press ENTER here once you have finished logging in: ")

            context.storage_state(path=str(settings.META_AUTH_STATE_PATH))
            print(f"[META LOGIN] Success! Saved authentication state to: {settings.META_AUTH_STATE_PATH}\n")
            browser.close()
