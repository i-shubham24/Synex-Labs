import random
import time
import logging
from abc import ABC, abstractmethod
from typing import List, Dict, Any, Optional
from dataclasses import dataclass
from config.settings import settings

logger = logging.getLogger("ingestion.base")


@dataclass
class ScrapedPost:
    """Standardized post payload across all platforms."""
    platform: str
    post_id: str
    title: str
    content: str
    url: str
    source_channel: str
    author: Optional[str] = None
    flair: Optional[str] = None
    created_utc: Optional[int] = None


class BaseScraper(ABC):
    """Abstract base scraper with anti-bot safety, human pacing, and rotating headers."""

    def __init__(self, platform: str):
        self.platform = platform

    def human_delay(self, min_sec: Optional[float] = None, max_sec: Optional[float] = None):
        """Randomized human pacing delay to evade platform bot detection."""
        low = min_sec or settings.SCRAPE_DELAY_MIN
        high = max_sec or settings.SCRAPE_DELAY_MAX
        sleep_time = random.uniform(low, high)
        logger.debug(f"[{self.platform}] Anti-bot pause for {sleep_time:.2f}s")
        time.sleep(sleep_time)

    def get_browser_headers(self) -> Dict[str, str]:
        """Returns realistic browser headers with rotating User-Agent."""
        ua = random.choice(settings.USER_AGENTS)
        return {
            "User-Agent": ua,
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8",
            "Accept-Language": "en-US,en;q=0.9",
            "DNT": "1",
            "Connection": "keep-alive",
            "Upgrade-Insecure-Requests": "1",
            "Sec-Fetch-Dest": "document",
            "Sec-Fetch-Mode": "navigate",
            "Sec-Fetch-Site": "none",
            "Sec-Fetch-User": "?1",
        }

    @abstractmethod
    def fetch_new_posts(self) -> List[ScrapedPost]:
        """Fetch newest raw posts from target channels."""
        pass
