"""SQLite storage for deduplication and content tracking."""

import sqlite3
from datetime import datetime, timezone
from pathlib import Path


class Storage:
    """Lightweight SQLite-based storage for deduplication.

    Tracks which content items have been seen so they are only
    reported once.  Also persists the latest AI digest HTML for
    Telegram preview and GitHub Pages deployment.
    """

    def __init__(self, db_path: str) -> None:
        self.db_path = db_path
        Path(db_path).parent.mkdir(parents=True, exist_ok=True)
        self._conn = sqlite3.connect(db_path)
        self._init_db()

    def _init_db(self) -> None:
        self._conn.executescript("""
            CREATE TABLE IF NOT EXISTS seen_items (
                item_id TEXT PRIMARY KEY,
                source TEXT NOT NULL,
                source_name TEXT NOT NULL,
                title TEXT NOT NULL,
                url TEXT NOT NULL,
                first_seen TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS daily_report (
                date TEXT PRIMARY KEY,
                html_path TEXT,
                created_at TEXT NOT NULL
            );
        """)
        self._conn.commit()

    def is_new(self, item_id: str) -> bool:
        """Check if an item has been seen before."""
        cur = self._conn.execute(
            "SELECT 1 FROM seen_items WHERE item_id = ?", (item_id,)
        )
        return cur.fetchone() is None

    def mark_seen(self, item_id: str, source: str, source_name: str,
                  title: str, url: str) -> None:
        """Record an item as seen."""
        now = datetime.now(timezone.utc).isoformat()
        self._conn.execute(
            "INSERT OR IGNORE INTO seen_items VALUES (?, ?, ?, ?, ?, ?)",
            (item_id, source, source_name, title, url, now),
        )
        self._conn.commit()

    def delete_source(self, source: str, item_id: str) -> None:
        """Delete an item by its ID (used for snapshot source refresh)."""
        self._conn.execute(
            "DELETE FROM seen_items WHERE item_id = ?", (item_id,)
        )
        self._conn.commit()

    def save_report(self, date_str: str, html_path: str) -> None:
        """Record that a daily report was generated."""
        now = datetime.now(timezone.utc).isoformat()
        self._conn.execute(
            "INSERT OR REPLACE INTO daily_report VALUES (?, ?, ?)",
            (date_str, html_path, now),
        )
        self._conn.commit()

    def get_latest_report(self) -> str | None:
        """Get the HTML path of the latest report, if any."""
        cur = self._conn.execute(
            "SELECT html_path FROM daily_report ORDER BY date DESC LIMIT 1"
        )
        row = cur.fetchone()
        return row[0] if row else None

    def close(self) -> None:
        self._conn.close()
