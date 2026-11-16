import sqlite3
from pathlib import Path
from contextlib import contextmanager
from config.settings import settings

SCHEMA_PATH = Path(__file__).parent / "schema.sql"

# Columns added after the first release. init_db() adds any that are missing,
# so existing leads.db files upgrade in place without losing data.
MIGRATIONS = {
    "leads": [
        ("notes", "TEXT"),
        ("outcome_at", "TIMESTAMP"),
        ("reply_email", "TEXT"),          # website briefs: who to answer
        ("country", "TEXT"),              # Gemini's best guess of the buyer's country
        ("first_website", "INTEGER DEFAULT 0"),  # no website yet (first website)
        ("old_website", "INTEGER DEFAULT 0"),    # wants to upgrade an old / unresponsive site
        ("priority", "INTEGER DEFAULT 0"),       # higher = shown and sent first
    ],
    "prospects": [
        ("followup_step", "INTEGER DEFAULT 0"),
        ("next_followup_at", "TIMESTAMP"),
        ("last_touch_at", "TIMESTAMP"),
        ("channel", "TEXT"),              # whatsapp | email | phone | instagram
        ("email_status", "TEXT"),         # unknown | valid | invalid | bounced
        ("notes", "TEXT"),
        ("outcome_at", "TIMESTAMP"),
        ("slug", "TEXT"),                 # private page folder name
        ("visual_json", "TEXT"),          # Gemini screenshot verdict
        ("pages_generated_at", "TIMESTAMP"),
        ("pages_published_at", "TIMESTAMP"),
        ("pages_live", "INTEGER DEFAULT 0"),
        ("brief", "TEXT"),                # pre-call brief
        ("proposal_at", "TIMESTAMP"),
        ("country_code", "TEXT"),         # calling code of the search city (91 = India)
        ("new_business", "INTEGER DEFAULT 0"),
        ("old_site", "INTEGER DEFAULT 0"),  # years-old or not mobile-friendly website
        ("priority", "INTEGER DEFAULT 0"),  # contact order: no website > old site > rest; India first
    ],
    "geocode_cache": [
        ("lat", "REAL"),                  # city centre, for cities without a boundary
        ("lon", "REAL"),
    ],
}


def get_db_path() -> Path:
    """Returns database file path, ensuring parent directory exists."""
    path = settings.SQLITE_DB_PATH
    path.parent.mkdir(parents=True, exist_ok=True)
    return path


def _migrate(conn: sqlite3.Connection):
    for table, columns in MIGRATIONS.items():
        existing = {row[1] for row in conn.execute(f"PRAGMA table_info({table});")}
        for name, decl in columns:
            if name not in existing:
                conn.execute(f"ALTER TABLE {table} ADD COLUMN {name} {decl};")


def init_db():
    """Initializes SQLite schema, applies column migrations, and enables WAL mode."""
    db_path = get_db_path()
    with sqlite3.connect(db_path) as conn:
        # Enable WAL mode (Write-Ahead Logging) for concurrent access without locking
        conn.execute("PRAGMA journal_mode = WAL;")
        conn.execute("PRAGMA synchronous = NORMAL;")
        conn.execute("PRAGMA foreign_keys = ON;")

        with open(SCHEMA_PATH, "r", encoding="utf-8") as f:
            conn.executescript(f.read())
        _migrate(conn)
        conn.execute("CREATE INDEX IF NOT EXISTS idx_prospects_followup ON prospects(next_followup_at);")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_prospects_priority ON prospects(priority);")
        conn.commit()


@contextmanager
def get_connection():
    """Context manager for SQLite connections with row factory enabled."""
    db_path = get_db_path()
    conn = sqlite3.connect(db_path, timeout=30.0)
    conn.row_factory = sqlite3.Row
    try:
        yield conn
    finally:
        conn.close()


def kv_get(key: str, default=None):
    with get_connection() as conn:
        row = conn.execute("SELECT value FROM kv WHERE key = ?;", (key,)).fetchone()
        return row["value"] if row else default


def kv_set(key: str, value) -> None:
    with get_connection() as conn:
        conn.execute(
            "INSERT INTO kv (key, value) VALUES (?, ?) ON CONFLICT(key) DO UPDATE SET value = excluded.value;",
            (key, None if value is None else str(value)),
        )
        conn.commit()
