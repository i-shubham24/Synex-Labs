import os
from pathlib import Path
from typing import List
from dotenv import load_dotenv

# Base directory for the lead generator
BASE_DIR = Path(__file__).resolve().parent.parent

# Load .env from lead generator folder first, then fallback to root
env_path = BASE_DIR / ".env"
if env_path.exists():
    load_dotenv(dotenv_path=env_path)
else:
    root_env = BASE_DIR.parent / ".env"
    if root_env.exists():
        load_dotenv(dotenv_path=root_env)


class Settings:
    """Application configuration with zero-cost sensible defaults."""

    # Gemini API
    GEMINI_API_KEY: str = os.getenv("GEMINI_API_KEY", "")
    GEMINI_MODEL: str = os.getenv("GEMINI_MODEL", "gemini-2.5-flash")

    # Database
    SQLITE_DB_PATH: Path = BASE_DIR / os.getenv("SQLITE_DB_PATH", "data/leads.db")

    # Reddit Target Subreddits
    _raw_subreddits = os.getenv(
        "REDDIT_SUBREDDITS",
        "forhire,smallbusiness,ecommerce,startups,freelance_forhire,webdev",
    )
    REDDIT_SUBREDDITS: List[str] = [
        s.strip() for s in _raw_subreddits.split(",") if s.strip()
    ]
    REDDIT_POLL_INTERVAL_MINUTES: int = int(
        os.getenv("REDDIT_POLL_INTERVAL_MINUTES", "15")
    )
    # Optional official Reddit OAuth credentials (PRAW)
    REDDIT_CLIENT_ID: str = os.getenv("REDDIT_CLIENT_ID", "")
    REDDIT_CLIENT_SECRET: str = os.getenv("REDDIT_CLIENT_SECRET", "")
    REDDIT_USER_AGENT: str = os.getenv(
        "REDDIT_USER_AGENT", "SynexLabsIntentBot/1.0 by SynexLabs"
    )

    # --- Twitter / X Ingestion (Phase 2) ---
    _raw_twitter_queries = os.getenv(
        "TWITTER_SEARCH_QUERIES",
        '"looking for a web developer","need a website","recommend a web agency","need an mvp developer"',
    )
    TWITTER_SEARCH_QUERIES: List[str] = [
        q.strip() for q in _raw_twitter_queries.split(",") if q.strip()
    ]
    TWITTER_AUTH_STATE_PATH: Path = BASE_DIR / "auth_state" / "twitter_cookies.json"
    NITTER_INSTANCES: List[str] = [
        "https://xcancel.com",
        "https://nitter.net",
        "https://nitter.cz",
        "https://nitter.privacydev.net",
    ]

    # --- Meta (Instagram / FB Ads Comments) Ingestion (Phase 2) ---
    _raw_meta_urls = os.getenv(
        "META_TARGET_AD_URLS",
        "https://www.facebook.com/ads/library/?active_status=all&ad_type=all&country=US&q=website%20redesign",
    )
    META_TARGET_AD_URLS: List[str] = [
        u.strip() for u in _raw_meta_urls.split(",") if u.strip()
    ]
    META_AUTH_STATE_PATH: Path = BASE_DIR / "auth_state" / "meta_cookies.json"

    # Browser Path (uses system Chrome for maximum stealth)
    CHROME_EXECUTABLE_PATH: str = os.getenv(
        "CHROME_PATH", "C:/Program Files/Google/Chrome/Application/chrome.exe"
    )

    # Anti-bot pacing (seconds)
    SCRAPE_DELAY_MIN: float = float(os.getenv("SCRAPE_DELAY_MIN", "2.5"))
    SCRAPE_DELAY_MAX: float = float(os.getenv("SCRAPE_DELAY_MAX", "6.0"))

    # Telegram (Module 3)
    TELEGRAM_BOT_TOKEN: str = os.getenv("TELEGRAM_BOT_TOKEN", "")
    TELEGRAM_CHAT_ID: str = os.getenv("TELEGRAM_CHAT_ID", "")
    TELEGRAM_POLL_INTERVAL: float = float(os.getenv("TELEGRAM_POLL_INTERVAL", "5.0"))

    # Rotating desktop User-Agents for anti-detection
    USER_AGENTS: List[str] = [
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/130.0.0.0 Safari/537.36",
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/129.0.0.0 Safari/537.36",
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:132.0) Gecko/20100101 Firefox/132.0",
        "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/130.0.0.0 Safari/537.36",
    ]


settings = Settings()
