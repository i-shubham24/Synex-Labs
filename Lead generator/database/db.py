import sqlite3
from pathlib import Path
from contextlib import contextmanager
from config.settings import settings

SCHEMA_PATH = Path(__file__).parent / "schema.sql"


def get_db_path() -> Path:
    """Returns database file path, ensuring parent directory exists."""
    path = settings.SQLITE_DB_PATH
    path.parent.mkdir(parents=True, exist_ok=True)
    return path


def init_db():
    """Initializes SQLite schema and configures WAL mode for safety and speed."""
    db_path = get_db_path()
    with sqlite3.connect(db_path) as conn:
        # Enable WAL mode (Write-Ahead Logging) for concurrent access without locking
        conn.execute("PRAGMA journal_mode = WAL;")
        conn.execute("PRAGMA synchronous = NORMAL;")
        conn.execute("PRAGMA foreign_keys = ON;")
        
        with open(SCHEMA_PATH, "r", encoding="utf-8") as f:
            schema_sql = f.read()
            conn.executescript(schema_sql)
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
