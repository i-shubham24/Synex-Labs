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
