import logging
import time
import re
import html
import random
from typing import List, Optional
import xml.etree.ElementTree as ET
import requests

from config.settings import settings
from config.keywords import HIGH_INTENT_KEYWORDS, NEGATIVE_KEYWORDS
from database.repository import LeadRepository
from .base import BaseScraper, ScrapedPost

logger = logging.getLogger("ingestion.twitter")


class TwitterScraper(BaseScraper):
    """
    Module 1: Twitter / X Ingestion Layer (Phase 2).
    Bypasses the $100+/mo paid X API using a dual-engine architecture:
    1. Zero-cost Nitter RSS search feeds
    2. Playwright with Stealth plugin and human pacing
    """

    def __init__(self, search_queries: Optional[List[str]] = None):
        super().__init__(platform="twitter")
        self.search_queries = search_queries or settings.TWITTER_SEARCH_QUERIES
        self.session = requests.Session()

    def fetch_new_posts(self) -> List[ScrapedPost]:
        """
        Polls configured search queries across Nitter RSS and Playwright fallback.
        """
        all_posts: List[ScrapedPost] = []
        for i, query in enumerate(self.search_queries):
            posts = self._fetch_via_nitter(query)
            if not posts:
                logger.info(f"[Twitter] Nitter empty or blocked for '{query}'. Trying stealth browser...")
                posts = self._fetch_via_playwright(query)

            all_posts.extend(posts)

            if i < len(self.search_queries) - 1:
                self.human_delay()

        return all_posts

    def _fetch_via_nitter(self, query: str, limit: int = 20) -> List[ScrapedPost]:
        """
        Queries public Nitter RSS instances to extract recent tweets without API costs.
        """
        scraped_posts: List[ScrapedPost] = []
        encoded_query = requests.utils.quote(query)

        for instance in settings.NITTER_INSTANCES:
            url = f"{instance}/search/rss?f=tweets&q={encoded_query}"
            headers = self.get_browser_headers()

            try:
                resp = self.session.get(url, headers=headers, timeout=8.0)
                if resp.status_code != 200 or not resp.text.strip():
                    continue

                root = ET.fromstring(resp.text)
                items = root.findall(".//item")
                if not items:
                    continue

                for item in items[:limit]:
                    link = item.find("link")
                    title = item.find("title")
                    desc = item.find("description")
                    creator = item.find("{http://purl.org/dc/elements/1.1/}creator")

                    tweet_url = link.text if link is not None else ""
                    raw_title = title.text if title is not None else ""
                    raw_desc = desc.text if desc is not None else ""
                    author = creator.text if creator is not None else "twitter_user"

                    # Extract Tweet ID from URL (e.g. status/1850123456789)
                    match = re.search(r"/status/(\d+)", tweet_url)
                    if not match:
                        continue
                    tweet_id = match.group(1)

                    if LeadRepository.is_post_scraped(self.platform, tweet_id):
                        continue

                    # Clean tweet text
                    clean_content = re.sub(r"<[^>]+>", " ", html.unescape(raw_desc)).strip()
                    clean_content = re.sub(r"\s+", " ", clean_content)
                    full_text = f"{raw_title} {clean_content}".strip()

                    # Pre-filter noise
                    if self._is_negative_noise(full_text):
                        continue
                    if not self._has_intent(full_text):
                        continue

                    # Direct clean X.com URL
                    canonical_url = f"https://x.com/{author}/status/{tweet_id}"

                    scraped_posts.append(
                        ScrapedPost(
                            platform=self.platform,
                            post_id=tweet_id,
                            title=raw_title[:100],
                            content=clean_content or raw_title,
                            url=canonical_url,
                            source_channel=f"x_search: {query[:30]}",
                            author=author,
                            flair="Live Tweet",
                            created_utc=int(time.time()),
                        )
                    )

                if scraped_posts:
                    logger.info(f"[Nitter] Retrieved {len(scraped_posts)} tweets from {instance} for '{query}'")
                    return scraped_posts

            except Exception as e:
                logger.debug(f"[Nitter] Instance {instance} failed for '{query}': {e}")
                continue

        return scraped_posts

    def _fetch_via_playwright(self, query: str, limit: int = 15) -> List[ScrapedPost]:
        """
        Launches stealth headless Chrome to scrape advanced search results from X.com.
        Uses randomized pauses and smooth scrolling to evade bot detection.
        """
        scraped_posts: List[ScrapedPost] = []
        encoded_query = requests.utils.quote(query)
        search_url = f"https://x.com/search?q={encoded_query}&f=live"

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
                context_args = {
                    "viewport": {"width": 1440, "height": 900},
                    "user_agent": random.choice(settings.USER_AGENTS),
                }
                if settings.TWITTER_AUTH_STATE_PATH.exists():
                    logger.info(f"[Twitter] Using saved auth state from: {settings.TWITTER_AUTH_STATE_PATH}")
                    context_args["storage_state"] = str(settings.TWITTER_AUTH_STATE_PATH)

                context = browser.new_context(**context_args)
                page = context.new_page()
                Stealth().apply_stealth_sync(page)

                logger.info(f"[Playwright-X] Navigating stealthily to: {search_url}")
                page.goto(search_url, wait_until="domcontentloaded", timeout=30000)

                # Randomized human pause
                time.sleep(random.uniform(3.5, 6.0))

                # Human-like micro-scrolls
                for _ in range(3):
                    page.mouse.wheel(0, random.randint(400, 700))
                    time.sleep(random.uniform(1.5, 2.8))

                articles = page.locator('article[data-testid="tweet"]').all()
                logger.info(f"[Playwright-X] Found {len(articles)} tweet elements on page.")

                for article in articles[:limit]:
                    try:
                        # Extract status link
                        status_link = article.locator('a[href*="/status/"]').first
                        href = status_link.get_attribute("href") or ""
                        match = re.search(r"/status/(\d+)", href)
                        if not match:
                            continue
                        tweet_id = match.group(1)

                        if LeadRepository.is_post_scraped(self.platform, tweet_id):
                            continue

                        # Extract text
                        text_elem = article.locator('div[data-testid="tweetText"]').first
                        tweet_text = text_elem.inner_text() if text_elem.count() > 0 else ""

                        # Extract author
                        author_elem = article.locator('div[data-testid="User-Name"]').first
                        author_text = author_elem.inner_text() if author_elem.count() > 0 else "user"
                        handle_match = re.search(r"@(\w+)", author_text)
                        author = handle_match.group(1) if handle_match else "x_user"

                        if self._is_negative_noise(tweet_text):
                            continue
                        if not self._has_intent(tweet_text):
                            continue

                        canonical_url = f"https://x.com/{author}/status/{tweet_id}"

                        scraped_posts.append(
                            ScrapedPost(
                                platform=self.platform,
                                post_id=tweet_id,
                                title=tweet_text[:80],
                                content=tweet_text,
                                url=canonical_url,
                                source_channel=f"x_search: {query[:30]}",
                                author=author,
                                flair="Live Tweet",
                                created_utc=int(time.time()),
                            )
                        )
                    except Exception as parse_err:
                        logger.debug(f"[Playwright-X] Tweet parsing error: {parse_err}")
                        continue

                browser.close()

        except Exception as e:
            logger.warning(f"[Playwright-X] Scraper error for query '{query}': {e}")

        logger.info(f"[Twitter] Retrieved {len(scraped_posts)} qualified candidate tweets for '{query}'")
        return scraped_posts

    def _is_negative_noise(self, text: str) -> bool:
        """Filters out freelancer pitches and spam."""
        lower = text.lower()
        for neg in NEGATIVE_KEYWORDS:
            if neg in lower:
                return True
        return False

    def _has_intent(self, text: str) -> bool:
        """Checks for buyer / hiring intent phrases."""
        lower = text.lower()
        for kw in HIGH_INTENT_KEYWORDS:
            if kw in lower:
                return True
        return False

    @staticmethod
    def interactive_login_session():
        """
        Interactive helper CLI tool: opens a visible Chrome window to let
        the human operator log into X.com once and saves cookies to
        auth_state/twitter_cookies.json for headless runs.
        """
        auth_dir = settings.TWITTER_AUTH_STATE_PATH.parent
        auth_dir.mkdir(parents=True, exist_ok=True)

        from playwright.sync_api import sync_playwright

        print("\n[TWITTER LOGIN] Launching visible browser window...")
        print("[TWITTER LOGIN] Please log in to X.com in the opened window.")
        print("[TWITTER LOGIN] Once logged in, press Enter in this terminal to save your session cookies.\n")

        with sync_playwright() as p:
            browser = p.chromium.launch(
                executable_path=settings.CHROME_EXECUTABLE_PATH,
                headless=False,
            )
            context = browser.new_context(viewport={"width": 1280, "height": 800})
            page = context.new_page()
            page.goto("https://x.com/i/flow/login")

            input(">>> Press ENTER here once you have finished logging in: ")

            context.storage_state(path=str(settings.TWITTER_AUTH_STATE_PATH))
            print(f"[TWITTER LOGIN] Success! Saved authentication state to: {settings.TWITTER_AUTH_STATE_PATH}\n")
            browser.close()
