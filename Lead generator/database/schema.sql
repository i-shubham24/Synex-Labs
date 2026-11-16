-- ====================================================================
-- SynexLabs Intent Ingestion Engine - Database Schema (SQLite)
-- Designed for zero-cost, persistent deduplication & audit trail.
-- ====================================================================

-- 1. Main table for scraped items and their AI-qualified status
CREATE TABLE IF NOT EXISTS leads (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    
    -- Ingestion Metadata
    platform TEXT NOT NULL,                     -- 'reddit', 'twitter', 'meta'
    post_id TEXT NOT NULL,                      -- Platform-specific unique ID (e.g. Reddit fullname 't3_abc123')
    author TEXT,                                -- Username / profile name
    title TEXT,                                 -- Post title or headline
    content TEXT,                               -- Full body text or comment
    url TEXT NOT NULL,                          -- Direct URL to the post/comment
    source_channel TEXT,                        -- Subreddit (r/forhire), Search query, or Ad URL
    flair TEXT,                                 -- Post tag/flair if available
    created_utc INTEGER,                        -- Original publication timestamp (Unix)
    scraped_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    -- AI Processing & Filtering (Gemini Output)
    is_processed INTEGER DEFAULT 0,             -- 0 = pending, 1 = processed by Gemini
    is_valid_lead INTEGER DEFAULT 0,            -- 0 = no, 1 = qualified buyer
    project_category TEXT,                      -- e.g. 'Website Redesign', 'Custom Web App', 'AI Agent'
    budget_indicator TEXT,                      -- e.g. 'High', 'Medium', 'Not mentioned'
    draft_icebreaker TEXT,                      -- 2-sentence conversational outreach message
    ai_reasoning TEXT,                          -- Brief rationale behind classification
    confidence_score REAL DEFAULT 0.0,          -- 0.0 to 1.0 confidence rating
    processed_at TIMESTAMP,

    -- Delivery & Pipeline Status (Human-in-the-Loop)
    status TEXT DEFAULT 'new',                  -- 'new', 'alerted', 'contacted', 'ignored', 'disqualified'
    alerted_at TIMESTAMP,
    contacted_at TIMESTAMP
);

-- Fast O(1) deduplication index across all platforms
CREATE UNIQUE INDEX IF NOT EXISTS idx_leads_platform_post_id ON leads(platform, post_id);

-- Query performance indexes
CREATE INDEX IF NOT EXISTS idx_leads_status ON leads(status);
CREATE INDEX IF NOT EXISTS idx_leads_is_valid ON leads(is_valid_lead);
CREATE INDEX IF NOT EXISTS idx_leads_scraped_at ON leads(scraped_at);


-- 2. Ingestion Run Metrics (Audit log for monitoring rate limits & scrapers)
CREATE TABLE IF NOT EXISTS ingestion_runs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    platform TEXT NOT NULL,
    source_channel TEXT NOT NULL,
    items_scraped INTEGER DEFAULT 0,
    duplicates_skipped INTEGER DEFAULT 0,
    valid_leads_found INTEGER DEFAULT 0,
    status TEXT NOT NULL,                       -- 'success', 'rate_limited', 'error'
    error_message TEXT,
    started_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    completed_at TIMESTAMP
);


-- ====================================================================
-- Maps Prospector: local businesses with no website or a weak one
-- ====================================================================

-- 3. One row per business found on Google Places or OpenStreetMap
CREATE TABLE IF NOT EXISTS prospects (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    source TEXT NOT NULL,                       -- 'google_places' | 'osm'
    place_id TEXT NOT NULL,                     -- Google place id or OSM 'node/123'
    name TEXT NOT NULL,
    niche TEXT,                                 -- Search niche, e.g. 'dentist'
    city TEXT,                                  -- Search city, e.g. 'Austin, TX'
    address TEXT,
    phone TEXT,
    email TEXT,                                 -- Found on their website, if any
    website TEXT,
    socials TEXT,                               -- JSON list of social profile URLs
    maps_url TEXT,
    rating REAL,
    review_count INTEGER,

    -- Website audit
    tier TEXT,                                  -- no_website | no_website_unverified | social_only | broken_website | weak_website | ok_website
    heat_score INTEGER DEFAULT 0,               -- 0-100, higher = hotter lead
    issues TEXT,                                -- JSON list of human-readable findings
    audit_json TEXT,                            -- Raw audit measurements
    audited_at TIMESTAMP,

    -- Outreach
    opener TEXT,                                -- Drafted first message (Gemini or template)
    opener_source TEXT,                         -- 'gemini' | 'template'
    status TEXT DEFAULT 'new',                  -- new | alerted | contacted | skipped | ignored
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    alerted_at TIMESTAMP,
    contacted_at TIMESTAMP
);

CREATE UNIQUE INDEX IF NOT EXISTS idx_prospects_source_place ON prospects(source, place_id);
CREATE INDEX IF NOT EXISTS idx_prospects_status ON prospects(status);
CREATE INDEX IF NOT EXISTS idx_prospects_heat ON prospects(heat_score);

-- 4. Which niche + city searches ran, so paid API calls are not repeated too often
CREATE TABLE IF NOT EXISTS prospect_searches (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    source TEXT NOT NULL,
    niche TEXT NOT NULL,
    city TEXT NOT NULL,
    results_count INTEGER DEFAULT 0,
    new_count INTEGER DEFAULT 0,
    last_run_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE UNIQUE INDEX IF NOT EXISTS idx_prospect_searches_key ON prospect_searches(source, niche, city);

-- 5. Monthly paid-API call counter (budget guard for Google Places)
CREATE TABLE IF NOT EXISTS api_usage (
    api TEXT NOT NULL,
    month TEXT NOT NULL,                        -- 'YYYY-MM' (UTC)
    calls INTEGER DEFAULT 0,
    PRIMARY KEY (api, month)
);

-- 6. City name -> OpenStreetMap area id (geocoded once via Nominatim)
CREATE TABLE IF NOT EXISTS geocode_cache (
    query TEXT PRIMARY KEY,
    osm_area_id INTEGER,
    display_name TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);


-- ====================================================================
-- Outreach automation
-- ====================================================================

-- 7. Every email sent or received about a prospect or lead
CREATE TABLE IF NOT EXISTS emails (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    prospect_id INTEGER,
    lead_id INTEGER,
    direction TEXT NOT NULL,                    -- 'out' | 'in'
    kind TEXT,                                  -- opener | followup1..3 | reply | inbound
    message_id TEXT,
    in_reply_to TEXT,
    from_addr TEXT,
    to_addr TEXT,
    subject TEXT,
    body TEXT,
    status TEXT,                                -- sent | failed | received | bounced
    error TEXT,
    label TEXT,                                 -- Gemini reply label (interested, question, ...)
    summary TEXT,
    draft_reply TEXT,
    handled INTEGER DEFAULT 0,                  -- 1 once a human dealt with an incoming email
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_emails_prospect ON emails(prospect_id);
CREATE INDEX IF NOT EXISTS idx_emails_message_id ON emails(message_id);
CREATE INDEX IF NOT EXISTS idx_emails_direction ON emails(direction, created_at);

-- 8. Never contact these again (email address or phone digits)
CREATE TABLE IF NOT EXISTS suppression (
    value TEXT PRIMARY KEY,
    reason TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 9. Small engine state (digest dates, IMAP position, alert cooldowns)
CREATE TABLE IF NOT EXISTS kv (
    key TEXT PRIMARY KEY,
    value TEXT
);
