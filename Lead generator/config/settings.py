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
    # Minimum gap between Gemini calls (free tier is rate limited per minute)
    GEMINI_MIN_INTERVAL_SECONDS: float = float(os.getenv("GEMINI_MIN_INTERVAL_SECONDS", "6.5"))
    # Backups used automatically when the main model hits its daily free quota
    GEMINI_FALLBACK_MODELS: List[str] = [
        m.strip() for m in os.getenv("GEMINI_FALLBACK_MODELS", "gemini-flash-lite-latest,gemini-3.5-flash-lite,gemini-flash-latest").split(",") if m.strip()
    ]

    # Database
    SQLITE_DB_PATH: Path = BASE_DIR / os.getenv("SQLITE_DB_PATH", "data/leads.db")

    # Reddit Target Subreddits
    _raw_subreddits = os.getenv(
        "REDDIT_SUBREDDITS",
        "indianstartups,StartUpIndia,forhire,smallbusiness,ecommerce,startups,webdev",
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
        '"website developer in Mumbai","website developer in Delhi","website developer in Bangalore",'
        '"need a website for my business","website chahiye","looking for a web developer","need a website"',
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

    # --- Bluesky Ingestion (optional, needs a free account + app password) ---
    BLUESKY_HANDLE: str = os.getenv("BLUESKY_HANDLE", "").strip()
    BLUESKY_APP_PASSWORD: str = os.getenv("BLUESKY_APP_PASSWORD", "").strip()
    _raw_bluesky_queries = os.getenv(
        "BLUESKY_SEARCH_QUERIES",
        '"need a website","website for my business","website developer India","new business website",'
        '"looking for a web developer","recommend a web designer"',
    )
    BLUESKY_SEARCH_QUERIES: List[str] = [
        q.strip() for q in _raw_bluesky_queries.split(",") if q.strip()
    ]
    BLUESKY_POLL_INTERVAL_MINUTES: int = int(os.getenv("BLUESKY_POLL_INTERVAL_MINUTES", "30"))

    # --- Maps Prospector: local businesses with no website or a weak one ---
    # Google Places API (New). Text Search with website/phone fields bills on the
    # "Enterprise" SKU, which has 1,000 free calls per month (up to 20 businesses per call).
    GOOGLE_PLACES_API_KEY: str = os.getenv("GOOGLE_PLACES_API_KEY", "").strip()
    # PageSpeed Insights needs its own quota; the same Google Cloud key works if the API is enabled.
    GOOGLE_PAGESPEED_API_KEY: str = (
        os.getenv("GOOGLE_PAGESPEED_API_KEY", "").strip() or GOOGLE_PLACES_API_KEY
    )
    # Hard stop for Places calls per calendar month, kept under the free cap.
    PLACES_MONTHLY_CALL_LIMIT: int = int(os.getenv("PLACES_MONTHLY_CALL_LIMIT", "900"))
    # Pages fetched per search (20 businesses per page, max 3 pages / 60 businesses).
    PLACES_PAGES_PER_SEARCH: int = max(1, min(3, int(os.getenv("PLACES_PAGES_PER_SEARCH", "3"))))

    # Niches are comma-separated. Cities are SEMICOLON-separated because names contain commas.
    _raw_niches = os.getenv(
        "PROSPECT_NICHES",
        # All-round Indian small businesses; the queue rotates through them
        "coaching centre,clinic,restaurant,hair salon,beauty parlour,gym,school,hotel,jewellery shop,clothing store,boutique,furniture store,interior designer,chartered accountant,lawyer,travel agency,event venue,photographer,cafe,bakery,sweet shop,guest house,physiotherapist,dentist,veterinary,optician,pharmacy,electronics store,mobile phone shop,car repair,car dealer,driving school,plumber,electrician",
    )
    PROSPECT_NICHES: List[str] = [n.strip() for n in _raw_niches.split(",") if n.strip()]
    _raw_cities = os.getenv(
        "PROSPECT_CITIES",
        "Mumbai, India;Delhi, India;Bengaluru, India;Pune, India;Hyderabad, India;Chennai, India;"
        "Ahmedabad, India;Jaipur, India;Dubai, United Arab Emirates;Zurich, Switzerland;Sydney, Australia",
    )
    # Priority market: searched first, and ranked first inside each lead group
    PRIORITY_COUNTRY_CODE: str = os.getenv("PRIORITY_COUNTRY_CODE", "91").strip()  # 91 = India
    PRIORITY_BOOST: int = int(os.getenv("PRIORITY_BOOST", "40"))
    # Signs of a brand-new business (opening soon, few reviews, newly mapped) rank a little higher
    NEW_BUSINESS_BOOST: int = int(os.getenv("NEW_BUSINESS_BOOST", "10"))
    NEW_BUSINESS_MAX_REVIEWS: int = int(os.getenv("NEW_BUSINESS_MAX_REVIEWS", "20"))
    PROSPECT_CITIES: List[str] = [c.strip() for c in _raw_cities.split(";") if c.strip()]
    # auto = Google Places when a key is set, otherwise free OpenStreetMap data
    PROSPECT_SOURCE: str = os.getenv("PROSPECT_SOURCE", "auto").strip().lower()
    PROSPECT_MAX_SEARCHES_PER_RUN: int = int(os.getenv("PROSPECT_MAX_SEARCHES_PER_RUN", "10"))
    PROSPECT_RERUN_DAYS: int = int(os.getenv("PROSPECT_RERUN_DAYS", "30"))
    PROSPECT_ALERTS_PER_RUN: int = int(os.getenv("PROSPECT_ALERTS_PER_RUN", "15"))
    # Hard cap on prospect cards per day, so retries after an outage never flood Telegram
    PROSPECT_ALERTS_PER_DAY: int = int(os.getenv("PROSPECT_ALERTS_PER_DAY", "15"))
    # Google only: skip businesses with fewer reviews (tiny or inactive listings)
    PROSPECT_MIN_REVIEWS: int = int(os.getenv("PROSPECT_MIN_REVIEWS", "5"))
    # Sites scoring at or above this are "weak" and worth pitching (0-100, higher = worse site)
    PROSPECT_MIN_SCORE: int = int(os.getenv("PROSPECT_MIN_SCORE", "40"))
    # Internet Archive lookups per search (site age, last update, traffic signal); about 1-2s each
    HISTORY_CHECKS_PER_SEARCH: int = int(os.getenv("HISTORY_CHECKS_PER_SEARCH", "60"))
    PROSPECT_DAILY_RUN_HOUR: int = int(os.getenv("PROSPECT_DAILY_RUN_HOUR", "9"))
    # --- Follow-ups, digest, backups ---
    FOLLOWUP_DAYS: List[int] = [
        int(d) for d in os.getenv("FOLLOWUP_DAYS", "3,7,14").split(",") if d.strip().isdigit()
    ]
    # After the last follow-up, wait this long for a reply before marking "no response"
    NO_RESPONSE_AFTER_DAYS: int = int(os.getenv("NO_RESPONSE_AFTER_DAYS", "7"))
    DIGEST_HOUR: int = int(os.getenv("DIGEST_HOUR", "9"))
    DIGEST_MINUTE: int = int(os.getenv("DIGEST_MINUTE", "45"))
    FOLLOWUP_CARDS_PER_DIGEST: int = int(os.getenv("FOLLOWUP_CARDS_PER_DIGEST", "10"))
    BACKUP_KEEP: int = int(os.getenv("BACKUP_KEEP", "14"))

    # --- Email outreach (off until SMTP is configured) ---
    # Use a SEPARATE domain + mailbox for cold email so your main domain keeps its reputation.
    SMTP_HOST: str = os.getenv("SMTP_HOST", "").strip()
    SMTP_PORT: int = int(os.getenv("SMTP_PORT", "587"))
    SMTP_SECURITY: str = os.getenv("SMTP_SECURITY", "starttls").strip().lower()  # starttls | ssl | none
    SMTP_USER: str = os.getenv("SMTP_USER", "").strip()
    SMTP_PASSWORD: str = os.getenv("SMTP_PASSWORD", "").strip()
    EMAIL_FROM_ADDRESS: str = os.getenv("EMAIL_FROM_ADDRESS", "").strip() or SMTP_USER
    EMAIL_FROM_NAME: str = os.getenv("EMAIL_FROM_NAME", "Synex Labs").strip()
    EMAIL_SIGNATURE_NAME: str = os.getenv("EMAIL_SIGNATURE_NAME", "Shubham").strip()
    EMAIL_POSTAL_ADDRESS: str = os.getenv("EMAIL_POSTAL_ADDRESS", "").strip()
    # Dashboard "Email" buttons: "gmail" opens Gmail compose in the browser (works without a mail app),
    # "mailto" hands the message to a desktop mail app. GMAIL_ACCOUNT picks the account when several are signed in.
    EMAIL_COMPOSE: str = os.getenv("EMAIL_COMPOSE", "gmail").strip().lower()
    GMAIL_ACCOUNT: str = os.getenv("GMAIL_ACCOUNT", "").strip()
    EMAIL_DAILY_CAP: int = int(os.getenv("EMAIL_DAILY_CAP", "20"))
    # Warm-up: day 1 sends EMAIL_WARMUP_START, then +EMAIL_WARMUP_STEP per day up to the cap
    EMAIL_WARMUP_START: int = int(os.getenv("EMAIL_WARMUP_START", "5"))
    EMAIL_WARMUP_STEP: int = int(os.getenv("EMAIL_WARMUP_STEP", "2"))
    EMAIL_AUTO_FOLLOWUPS: bool = os.getenv("EMAIL_AUTO_FOLLOWUPS", "true").strip().lower() not in ("0", "false", "no")
    EMAIL_SEND_HOURS: str = os.getenv("EMAIL_SEND_HOURS", "9-18")
    IMAP_HOST: str = os.getenv("IMAP_HOST", "").strip()
    IMAP_PORT: int = int(os.getenv("IMAP_PORT", "993"))
    IMAP_USER: str = os.getenv("IMAP_USER", "").strip() or SMTP_USER
    IMAP_PASSWORD: str = os.getenv("IMAP_PASSWORD", "").strip() or SMTP_PASSWORD
    IMAP_FOLDER: str = os.getenv("IMAP_FOLDER", "INBOX").strip()
    # Optional second inbox that receives website contact-form briefs ("New brief: ...")
    BRIEFS_IMAP_HOST: str = os.getenv("BRIEFS_IMAP_HOST", "").strip()
    BRIEFS_IMAP_PORT: int = int(os.getenv("BRIEFS_IMAP_PORT", "993"))
    BRIEFS_IMAP_USER: str = os.getenv("BRIEFS_IMAP_USER", "").strip()
    BRIEFS_IMAP_PASSWORD: str = os.getenv("BRIEFS_IMAP_PASSWORD", "").strip()
    INBOX_POLL_MINUTES: int = int(os.getenv("INBOX_POLL_MINUTES", "10"))

    # --- Showcase pages (audit page + demo homepage per prospect) ---
    # Agency website used in every message and page link (synexlabs.in is a different company)
    SITE_URL: str = os.getenv("SITE_URL", "https://synex-labs.pages.dev").rstrip("/")
    SITE_PUBLIC_DIR: Path = Path(os.getenv("SITE_PUBLIC_DIR", "").strip() or str(BASE_DIR.parent / "public"))
    PAGES_PER_RUN: int = int(os.getenv("PAGES_PER_RUN", "5"))
    # Screenshot + Gemini design check of sites that passed the code checks (finds dated-looking sites)
    VISUAL_CHECKS_PER_RUN: int = int(os.getenv("VISUAL_CHECKS_PER_RUN", "3"))
    BOOKING_URL: str = os.getenv("BOOKING_URL", "").strip()
    STUDIO_WHATSAPP: str = os.getenv("STUDIO_WHATSAPP", "").strip()   # e.g. +91XXXXXXXXXX
    STUDIO_EMAIL: str = os.getenv("STUDIO_EMAIL", "").strip()

    # --- Background engine + local dashboard ---
    DASHBOARD_PORT: int = int(os.getenv("DASHBOARD_PORT", "8765"))
    # Run one social scan right after the engine starts
    ENGINE_STARTUP_SCAN: bool = os.getenv("ENGINE_STARTUP_SCAN", "true").strip().lower() not in ("0", "false", "no")

    # OpenStreetMap services require an identifying User-Agent
    OSM_USER_AGENT: str = os.getenv("OSM_USER_AGENT", "SynexLabsLeadEngine/1.0 (python-requests)")

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
