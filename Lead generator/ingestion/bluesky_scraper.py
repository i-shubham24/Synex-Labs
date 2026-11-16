"""
Bluesky ingestion via the official AT Protocol API.

Bluesky's public search endpoint rejects anonymous requests, so this logs in with
an app password (Settings > Privacy and security > App passwords on bsky.app).
An app password cannot change the account password or delete the account.
"""

import logging
import time
from datetime import datetime, timedelta, timezone
from typing import List, Optional, Dict, Any

import requests

from config.settings import settings
from database.repository import LeadRepository
from .base import BaseScraper, ScrapedPost, has_buyer_intent, is_seller_noise

logger = logging.getLogger("ingestion.bluesky")

ENTRYWAY = "https://bsky.social"


class BlueskyScraper(BaseScraper):
    """Searches recent Bluesky posts for people asking for a website or developer."""

    def __init__(self, search_queries: Optional[List[str]] = None):
        super().__init__(platform="bluesky")
        self.search_queries = search_queries or settings.BLUESKY_SEARCH_QUERIES
        self.session = requests.Session()
        self.session.headers["User-Agent"] = "SynexLabsLeadEngine/1.0"
        self._access_jwt: Optional[str] = None
        self._service = ENTRYWAY

    def is_configured(self) -> bool:
        return bool(settings.BLUESKY_HANDLE and settings.BLUESKY_APP_PASSWORD)

    def _login(self) -> bool:
        try:
            resp = self.session.post(
                f"{ENTRYWAY}/xrpc/com.atproto.server.createSession",
                json={
                    "identifier": settings.BLUESKY_HANDLE,
                    "password": settings.BLUESKY_APP_PASSWORD,
                },
                timeout=15.0,
            )
            if not resp.ok:
                logger.error(f"[Bluesky] Login failed ({resp.status_code}): {resp.text[:160]}")
                return False
            data = resp.json()
            self._access_jwt = data.get("accessJwt")
            # Accounts live on a specific PDS; requests there are proxied to the AppView.
            for service in (data.get("didDoc") or {}).get("service", []):
                if service.get("id") == "#atproto_pds" and service.get("serviceEndpoint"):
                    self._service = service["serviceEndpoint"].rstrip("/")
            return bool(self._access_jwt)
        except Exception as e:
            logger.error(f"[Bluesky] Login error: {e}")
            return False

    def fetch_new_posts(self) -> List[ScrapedPost]:
        if not self.is_configured():
            logger.info("[Bluesky] BLUESKY_HANDLE / BLUESKY_APP_PASSWORD not set. Skipping.")
            return []
        if not self._access_jwt and not self._login():
            return []

        since = (datetime.now(timezone.utc) - timedelta(days=2)).strftime("%Y-%m-%dT%H:%M:%SZ")
        all_posts: List[ScrapedPost] = []
        for i, query in enumerate(self.search_queries):
            all_posts.extend(self._search(query, since))
            if i < len(self.search_queries) - 1:
                self.human_delay(1.0, 2.5)

        logger.info(f"[Bluesky] Found {len(all_posts)} candidate posts.")
        return all_posts

    def _search(self, query: str, since: str, retried: bool = False) -> List[ScrapedPost]:
        try:
            resp = self.session.get(
                f"{self._service}/xrpc/app.bsky.feed.searchPosts",
                params={"q": query, "sort": "latest", "limit": 50, "since": since},
                headers={"Authorization": f"Bearer {self._access_jwt}"},
                timeout=20.0,
            )
            if resp.status_code in (400, 401) and "xpired" in resp.text and not retried:
                # Access tokens last about two hours; log in again once.
                if self._login():
                    return self._search(query, since, retried=True)
            if resp.status_code == 429:
                logger.warning("[Bluesky] Rate limited; pausing this cycle.")
                time.sleep(10.0)
                return []
            if not resp.ok:
                logger.error(f"[Bluesky] Search failed for {query!r} ({resp.status_code}): {resp.text[:160]}")
                return []
            return self.parse_search_results(resp.json(), query)
        except Exception as e:
            logger.error(f"[Bluesky] Search error for {query!r}: {e}")
            return []

    def parse_search_results(self, data: Dict[str, Any], query: str) -> List[ScrapedPost]:
        """Turns an app.bsky.feed.searchPosts response into candidate posts."""
        posts: List[ScrapedPost] = []
        for item in data.get("posts", []):
            uri = item.get("uri", "")
            record = item.get("record") or {}
            text = (record.get("text") or "").strip()
            author = item.get("author") or {}
            handle = author.get("handle", "unknown")
            if not uri or not text:
                continue
            if LeadRepository.is_post_scraped(self.platform, uri):
                continue
            if is_seller_noise(text) or not has_buyer_intent(text):
                continue

            rkey = uri.rsplit("/", 1)[-1]
            created_utc = None
            created_at = record.get("createdAt") or item.get("indexedAt")
            if created_at:
                try:
                    created_utc = int(datetime.fromisoformat(created_at.replace("Z", "+00:00")).timestamp())
                except ValueError:
                    created_utc = None

            first_line = text.splitlines()[0]
            posts.append(
                ScrapedPost(
                    platform=self.platform,
                    post_id=uri,
                    title=first_line[:120],
                    content=text,
                    url=f"https://bsky.app/profile/{handle}/post/{rkey}",
                    source_channel=f"search: {query}",
                    author=handle,
                    created_utc=created_utc or int(time.time()),
                )
            )
        return posts
