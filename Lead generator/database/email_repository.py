"""Stores every outreach email sent and every matched reply received."""

from datetime import datetime, timezone, timedelta
from typing import Optional, Dict, Any, List

from .db import get_connection


def _now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S")


class EmailRepository:

    @staticmethod
    def record(**fields) -> int:
        allowed = {
            "prospect_id", "lead_id", "direction", "kind", "message_id", "in_reply_to", "from_addr",
            "to_addr", "subject", "body", "status", "error", "label", "summary", "draft_reply", "handled",
        }
        data = {k: v for k, v in fields.items() if k in allowed}
        data["created_at"] = _now()
        cols = ", ".join(data)
        marks = ", ".join("?" for _ in data)
        with get_connection() as conn:
            cur = conn.execute(f"INSERT INTO emails ({cols}) VALUES ({marks});", tuple(data.values()))
            conn.commit()
            return cur.lastrowid

    @staticmethod
    def get(email_id: int) -> Optional[Dict[str, Any]]:
        with get_connection() as conn:
            row = conn.execute("SELECT * FROM emails WHERE id = ?;", (email_id,)).fetchone()
            return dict(row) if row else None

    @staticmethod
    def find_by_message_ids(ids: List[str]) -> Optional[Dict[str, Any]]:
        ids = [i.strip() for i in ids if i and i.strip()]
        if not ids:
            return None
        marks = ",".join("?" for _ in ids)
        with get_connection() as conn:
            row = conn.execute(
                f"SELECT * FROM emails WHERE message_id IN ({marks}) ORDER BY id DESC LIMIT 1;", ids
            ).fetchone()
            return dict(row) if row else None

    @staticmethod
    def exists_message(message_id: str) -> bool:
        if not message_id:
            return False
        with get_connection() as conn:
            return conn.execute(
                "SELECT 1 FROM emails WHERE message_id = ? AND direction = 'in' LIMIT 1;", (message_id,)
            ).fetchone() is not None

    @staticmethod
    def last_outgoing(prospect_id: int) -> Optional[Dict[str, Any]]:
        with get_connection() as conn:
            row = conn.execute(
                """SELECT * FROM emails WHERE prospect_id = ? AND direction = 'out' AND status = 'sent'
                   ORDER BY id DESC LIMIT 1;""",
                (prospect_id,),
            ).fetchone()
            return dict(row) if row else None

    @staticmethod
    def first_outgoing(prospect_id: int) -> Optional[Dict[str, Any]]:
        with get_connection() as conn:
            row = conn.execute(
                """SELECT * FROM emails WHERE prospect_id = ? AND direction = 'out' AND status = 'sent'
                   ORDER BY id ASC LIMIT 1;""",
                (prospect_id,),
            ).fetchone()
            return dict(row) if row else None

    @staticmethod
    def sent_since(since_utc: str) -> int:
        with get_connection() as conn:
            return conn.execute(
                "SELECT COUNT(*) FROM emails WHERE direction = 'out' AND status = 'sent' AND kind != 'reply' AND created_at >= ?;",
                (since_utc,),
            ).fetchone()[0]

    @staticmethod
    def incoming(limit: int = 80, unhandled_only: bool = False) -> List[Dict[str, Any]]:
        where = "WHERE e.direction = 'in'" + (" AND e.handled = 0" if unhandled_only else "")
        with get_connection() as conn:
            rows = conn.execute(
                f"""SELECT e.*, p.name AS prospect_name, p.status AS prospect_status
                    FROM emails e LEFT JOIN prospects p ON p.id = e.prospect_id
                    {where} ORDER BY e.id DESC LIMIT ?;""",
                (limit,),
            ).fetchall()
            return [dict(r) for r in rows]

    @staticmethod
    def thread(prospect_id: int) -> List[Dict[str, Any]]:
        with get_connection() as conn:
            rows = conn.execute(
                "SELECT * FROM emails WHERE prospect_id = ? ORDER BY id ASC;", (prospect_id,)
            ).fetchall()
            return [dict(r) for r in rows]

    @staticmethod
    def mark_handled(email_id: int):
        with get_connection() as conn:
            conn.execute("UPDATE emails SET handled = 1 WHERE id = ?;", (email_id,))
            conn.commit()

    @staticmethod
    def set_draft(email_id: int, draft: str):
        with get_connection() as conn:
            conn.execute("UPDATE emails SET draft_reply = ? WHERE id = ?;", (draft, email_id))
            conn.commit()

    @staticmethod
    def counts() -> Dict[str, int]:
        week_ago = (datetime.now(timezone.utc) - timedelta(days=7)).strftime("%Y-%m-%d %H:%M:%S")
        with get_connection() as conn:
            sent_7d = conn.execute(
                "SELECT COUNT(*) FROM emails WHERE direction='out' AND status='sent' AND created_at >= ?;", (week_ago,)
            ).fetchone()[0]
            unhandled = conn.execute(
                "SELECT COUNT(*) FROM emails WHERE direction='in' AND handled = 0 AND COALESCE(label,'') NOT IN ('out_of_office','unsubscribe','bounce');"
            ).fetchone()[0]
        return {"sent_7d": sent_7d, "replies_waiting": unhandled}
