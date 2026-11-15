import sqlite3
from typing import Optional, Dict, Any, List
from datetime import datetime
from .db import get_connection


class LeadRepository:
    """Handles all database operations for lead deduplication, storage, and status tracking."""

    @staticmethod
    def is_post_scraped(platform: str, post_id: str) -> bool:
        """
        Fast deduplication check.
        Returns True if the post has already been recorded in SQLite.
        """
        query = "SELECT 1 FROM leads WHERE platform = ? AND post_id = ? LIMIT 1;"
        with get_connection() as conn:
            cursor = conn.execute(query, (platform, post_id))
            return cursor.fetchone() is not None

    @staticmethod
    def save_raw_post(
        platform: str,
        post_id: str,
        title: str,
        content: str,
        url: str,
        source_channel: str,
        author: Optional[str] = None,
        flair: Optional[str] = None,
        created_utc: Optional[int] = None,
    ) -> Optional[int]:
        """
        Inserts a newly scraped post. Returns the row ID if inserted,
        or None if it violates the unique constraint (already scraped).
        """
        query = """
        INSERT INTO leads (
            platform, post_id, author, title, content,
            url, source_channel, flair, created_utc
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        ON CONFLICT(platform, post_id) DO NOTHING;
        """
        with get_connection() as conn:
            cursor = conn.execute(
                query,
                (
                    platform,
                    post_id,
                    author,
                    title,
                    content,
                    url,
                    source_channel,
                    flair,
                    created_utc,
                ),
            )
            conn.commit()
            return cursor.lastrowid if cursor.rowcount > 0 else None

    @staticmethod
    def get_unprocessed_posts(limit: int = 25) -> List[Dict[str, Any]]:
        """Retrieves raw posts awaiting Gemini AI classification."""
        query = """
        SELECT id, platform, post_id, author, title, content, url, source_channel, flair, created_utc
        FROM leads
        WHERE is_processed = 0
        ORDER BY created_utc DESC
        LIMIT ?;
        """
        with get_connection() as conn:
            cursor = conn.execute(query, (limit,))
            return [dict(row) for row in cursor.fetchall()]

    @staticmethod
    def update_lead_analysis(
        lead_id: int,
        is_valid_lead: bool,
        project_category: str,
        budget_indicator: str,
        draft_icebreaker: str,
        ai_reasoning: str = "",
        confidence_score: float = 0.0,
    ):
        """Updates a post with Gemini AI parsing results."""
        query = """
        UPDATE leads
        SET
            is_processed = 1,
            is_valid_lead = ?,
            project_category = ?,
            budget_indicator = ?,
            draft_icebreaker = ?,
            ai_reasoning = ?,
            confidence_score = ?,
            processed_at = ?,
            status = CASE WHEN ? = 1 THEN 'new' ELSE 'disqualified' END
        WHERE id = ?;
        """
        now = datetime.utcnow().isoformat()
        is_valid_int = 1 if is_valid_lead else 0
        with get_connection() as conn:
            conn.execute(
                query,
                (
                    is_valid_int,
                    project_category,
                    budget_indicator,
                    draft_icebreaker,
                    ai_reasoning,
                    confidence_score,
                    now,
                    is_valid_int,
                    lead_id,
                ),
            )
            conn.commit()

    @staticmethod
    def get_qualified_leads(status: str = "new", limit: int = 50) -> List[Dict[str, Any]]:
        """Retrieves verified valid leads by status."""
        query = """
        SELECT *
        FROM leads
        WHERE is_valid_lead = 1 AND status = ?
        ORDER BY id DESC
        LIMIT ?;
        """
        with get_connection() as conn:
            cursor = conn.execute(query, (status, limit))
            return [dict(row) for row in cursor.fetchall()]

    @staticmethod
    def mark_as_alerted(lead_id: int):
        """Marks a lead as dispatched to Telegram."""
        now = datetime.utcnow().isoformat()
        query = "UPDATE leads SET status = 'alerted', alerted_at = ? WHERE id = ?;"
        with get_connection() as conn:
            conn.execute(query, (now, lead_id))
            conn.commit()

    @staticmethod
    def mark_as_contacted(lead_id: int):
        """Marks a lead as contacted by SynexLabs human operator."""
        now = datetime.utcnow().isoformat()
        query = "UPDATE leads SET status = 'contacted', contacted_at = ? WHERE id = ?;"
        with get_connection() as conn:
            conn.execute(query, (now, lead_id))
            conn.commit()

    @staticmethod
    def record_ingestion_run(
        platform: str,
        source_channel: str,
        items_scraped: int,
        duplicates_skipped: int,
        valid_leads_found: int,
        status: str,
        error_message: Optional[str] = None,
        started_at: Optional[str] = None,
    ):
        """Logs an ingestion job run for monitoring rate limits & uptime."""
        query = """
        INSERT INTO ingestion_runs (
            platform, source_channel, items_scraped, duplicates_skipped,
            valid_leads_found, status, error_message, started_at, completed_at
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?);
        """
        now = datetime.utcnow().isoformat()
        started = started_at or now
        with get_connection() as conn:
            conn.execute(
                query,
                (
                    platform,
                    source_channel,
                    items_scraped,
                    duplicates_skipped,
                    valid_leads_found,
                    status,
                    error_message,
                    started,
                    now,
                ),
            )
            conn.commit()

    @staticmethod
    def get_stats() -> Dict[str, Any]:
        """Returns pipeline performance statistics."""
        with get_connection() as conn:
            total_scraped = conn.execute("SELECT COUNT(*) FROM leads").fetchone()[0]
            valid_leads = conn.execute("SELECT COUNT(*) FROM leads WHERE is_valid_lead = 1").fetchone()[0]
            pending_ai = conn.execute("SELECT COUNT(*) FROM leads WHERE is_processed = 0").fetchone()[0]
            contacted = conn.execute("SELECT COUNT(*) FROM leads WHERE status = 'contacted'").fetchone()[0]
            
            # Subreddit breakdown
            cursor = conn.execute(
                """
                SELECT source_channel, COUNT(*) as count 
                FROM leads 
                WHERE is_valid_lead = 1 
                GROUP BY source_channel 
                ORDER BY count DESC 
                LIMIT 5;
                """
            )
            top_sources = [dict(row) for row in cursor.fetchall()]

            return {
                "total_scraped": total_scraped,
                "valid_leads": valid_leads,
                "pending_ai": pending_ai,
                "contacted": contacted,
                "top_sources": top_sources,
            }
