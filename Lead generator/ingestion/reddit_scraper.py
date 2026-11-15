import logging
import time
import re
import html
from typing import List, Optional
import xml.etree.ElementTree as ET
import requests

from config.settings import settings
from config.keywords import HIGH_INTENT_KEYWORDS, NEGATIVE_KEYWORDS, RELEVANT_FLAIRS
from database.repository import LeadRepository
from .base import BaseScraper, ScrapedPost

logger = logging.getLogger("ingestion.reddit")


class RedditScraper(BaseScraper):
    """
    Module 1: Safe Reddit Ingestion Layer.
    Supports dual ingestion modes:
    1. Zero-auth RSS/Atom feed parsing (https://www.reddit.com/r/{sub}/new/.rss)
    2. PRAW (Python Reddit API Wrapper) when client credentials are provided
    3. Direct JSON feed fallback
    """

    def __init__(self, subreddits: Optional[List[str]] = None):
        super().__init__(platform="reddit")
        self.subreddits = subreddits or settings.REDDIT_SUBREDDITS
        self.session = requests.Session()
        self.praw_client = None

        if settings.REDDIT_CLIENT_ID and settings.REDDIT_CLIENT_SECRET:
            try:
                import praw
                self.praw_client = praw.Reddit(
                    client_id=settings.REDDIT_CLIENT_ID,
                    client_secret=settings.REDDIT_CLIENT_SECRET,
                    user_agent=settings.REDDIT_USER_AGENT,
                )
                logger.info("Initialized authenticated Reddit PRAW client.")
            except Exception as e:
                logger.warning(f"Could not initialize PRAW: {e}. Falling back to zero-auth RSS.")

    def fetch_subreddit_posts(self, subreddit: str, limit: int = 25) -> List[ScrapedPost]:
        """
        Polls a subreddit using PRAW if configured, otherwise using RSS/Atom feeds.
        """
        if self.praw_client:
            return self._fetch_via_praw(subreddit, limit)
        return self._fetch_via_rss(subreddit, limit)

    def _fetch_via_praw(self, subreddit: str, limit: int = 25) -> List[ScrapedPost]:
        """Fetches submissions using official Reddit PRAW client."""
        scraped_posts: List[ScrapedPost] = []
        try:
            sub = self.praw_client.subreddit(subreddit)
            for post in sub.new(limit=limit):
                post_id = post.id
                if LeadRepository.is_post_scraped(self.platform, post_id):
                    continue

                title = post.title or ""
                selftext = post.selftext or ""
                flair = (post.link_flair_text or "").strip()

                if self._is_negative_noise(title, selftext, flair):
                    continue
                if not self._has_intent(subreddit, title, selftext, flair):
                    continue

                scraped_posts.append(
                    ScrapedPost(
                        platform=self.platform,
                        post_id=post_id,
                        title=title,
                        content=selftext,
                        url=f"https://reddit.com{post.permalink}",
                        source_channel=f"r/{subreddit}",
                        author=str(post.author),
                        flair=flair,
                        created_utc=int(post.created_utc),
                    )
                )
        except Exception as e:
            logger.error(f"[PRAW] Error fetching r/{subreddit}: {e}")
            return self._fetch_via_rss(subreddit, limit)

        return scraped_posts

    def _fetch_via_rss(self, subreddit: str, limit: int = 25) -> List[ScrapedPost]:
        """
        Zero-auth ingestion using Reddit's RSS/Atom feeds.
        Bypasses JSON 403 blocks with high reliability.
        """
        url = f"https://www.reddit.com/r/{subreddit}/new/.rss"
        headers = {
            "User-Agent": (
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/130.0.0.0 Safari/537.36"
            ),
            "Accept": "application/atom+xml,application/xml,text/xml;q=0.9,*/*;q=0.8",
            "Accept-Language": "en-US,en;q=0.9",
        }

        try:
            response = self.session.get(url, headers=headers, timeout=15.0)
            if response.status_code == 429:
                logger.warning(f"Reddit 429 on r/{subreddit}. Pausing...")
                time.sleep(30.0)
                return []
            response.raise_for_status()
            return self._parse_atom_feed(response.text, subreddit, limit)
        except Exception as e:
            logger.warning(f"RSS fetch failed for r/{subreddit}: {e}. Trying JSON endpoint...")
            return self._fetch_via_json(subreddit, limit)

    def _parse_atom_feed(self, xml_text: str, subreddit: str, limit: int) -> List[ScrapedPost]:
        """Parses Atom XML feed entries into ScrapedPost items."""
        scraped_posts: List[ScrapedPost] = []
        ns = {"atom": "http://www.w3.org/2005/Atom"}

        try:
            root = ET.fromstring(xml_text)
        except Exception as e:
            logger.error(f"XML parse error for r/{subreddit}: {e}")
            return []

        entries = root.findall("atom:entry", ns)
        for entry in entries[:limit]:
            id_elem = entry.find("atom:id", ns)
            title_elem = entry.find("atom:title", ns)
            link_elem = entry.find("atom:link", ns)
            author_elem = entry.find("atom:author/atom:name", ns)
            content_elem = entry.find("atom:content", ns)
            category_elem = entry.find("atom:category", ns)

            raw_id = id_elem.text if id_elem is not None else ""
            post_id = raw_id.split("/")[-1].replace("t3_", "") if raw_id else ""
            if not post_id:
                continue

            # Fast deduplication
            if LeadRepository.is_post_scraped(self.platform, post_id):
                continue

            title = title_elem.text if title_elem is not None else ""
            url = link_elem.attrib.get("href", "") if link_elem is not None else ""
            author = author_elem.text.replace("/u/", "") if author_elem is not None else "Anonymous"
            flair = category_elem.attrib.get("term", "") if category_elem is not None else ""

            # Extract clean body text from HTML content
            raw_content = content_elem.text if content_elem is not None else ""
            clean_content = re.sub(r"<[^>]+>", " ", html.unescape(raw_content)).strip()
            # Remove repeated whitespace
            clean_content = re.sub(r"\s+", " ", clean_content)

            # Pre-filter noise
            if self._is_negative_noise(title, clean_content, flair):
                continue

            # Filter intent
            if not self._has_intent(subreddit, title, clean_content, flair):
                continue

            scraped_posts.append(
                ScrapedPost(
                    platform=self.platform,
                    post_id=post_id,
                    title=title,
                    content=clean_content,
                    url=url,
                    source_channel=f"r/{subreddit}",
                    author=author,
                    flair=flair,
                    created_utc=int(time.time()),
                )
            )

        logger.info(f"r/{subreddit}: Extracted {len(scraped_posts)} candidate posts.")
        return scraped_posts

    def _fetch_via_json(self, subreddit: str, limit: int = 25) -> List[ScrapedPost]:
        """JSON fallback with mobile browser headers."""
        url = f"https://www.reddit.com/r/{subreddit}/new.json?limit={limit}"
        headers = self.get_browser_headers()

        try:
            resp = self.session.get(url, headers=headers, timeout=12.0)
            if resp.status_code != 200:
                return []
            data = resp.json()
        except Exception:
            return []

        children = data.get("data", {}).get("children", [])
        scraped_posts: List[ScrapedPost] = []

        for item in children:
            post = item.get("data", {})
            post_id = post.get("id")
            if not post_id or LeadRepository.is_post_scraped(self.platform, post_id):
                continue

            title = post.get("title", "")
            selftext = post.get("selftext", "")
            author = post.get("author", "Anonymous")
            permalink = post.get("permalink", "")
            flair = (post.get("link_flair_text") or "").strip()

            if self._is_negative_noise(title, selftext, flair):
                continue
            if not self._has_intent(subreddit, title, selftext, flair):
                continue

            scraped_posts.append(
                ScrapedPost(
                    platform=self.platform,
                    post_id=post_id,
                    title=title,
                    content=selftext,
                    url=f"https://reddit.com{permalink}",
                    source_channel=f"r/{subreddit}",
                    author=author,
                    flair=flair,
                    created_utc=int(post.get("created_utc", 0)),
                )
            )

        return scraped_posts

    def fetch_new_posts(self) -> List[ScrapedPost]:
        """Polls all target subreddits sequentially with anti-bot human pauses."""
        all_posts: List[ScrapedPost] = []
        for i, subreddit in enumerate(self.subreddits):
            posts = self.fetch_subreddit_posts(subreddit)
            all_posts.extend(posts)

            if i < len(self.subreddits) - 1:
                self.human_delay()

        return all_posts

    def _is_negative_noise(self, title: str, content: str, flair: str) -> bool:
        """Filters out freelancers pitching their own services."""
        text = f"{title} {content}".lower()
        flair_lower = flair.lower()

        for neg_flair in RELEVANT_FLAIRS["negative"]:
            if neg_flair in flair_lower:
                return True

        for neg_kw in NEGATIVE_KEYWORDS:
            if neg_kw in text:
                return True

        return False

    def _has_intent(self, subreddit: str, title: str, content: str, flair: str) -> bool:
        """Checks for buyer intent or hiring flair."""
        flair_lower = flair.lower()
        text = f"{title} {content}".lower()

        if "forhire" in subreddit.lower():
            if "hiring" in flair_lower or "[hiring]" in text:
                return True

        for kw in HIGH_INTENT_KEYWORDS:
            if kw in text:
                return True

        return False
