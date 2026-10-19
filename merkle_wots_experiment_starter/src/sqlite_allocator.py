"""Minimal monotonic SQLite allocator for testing index uniqueness.

This is a prototype, not a complete crash-safe signer. It does not protect
against restoring an old database snapshot, cloned databases, or a signer
that bypasses this allocator.
"""
import sqlite3
from contextlib import closing
from pathlib import Path


class SQLiteAllocator:
    def __init__(self, path):
        self.path = str(path)
        with closing(self._connect()) as con:
            con.execute("""
                CREATE TABLE IF NOT EXISTS allocator (
                    singleton INTEGER PRIMARY KEY CHECK(singleton = 1),
                    next_index INTEGER NOT NULL CHECK(next_index >= 0)
                )
            """)
            con.execute(
                "INSERT OR IGNORE INTO allocator(singleton, next_index) VALUES (1, 0)"
            )

    def _connect(self):
        con = sqlite3.connect(self.path, timeout=30, isolation_level=None)
        con.execute("PRAGMA journal_mode=WAL")
        con.execute("PRAGMA synchronous=FULL")
        return con

    def reserve(self):
        """Atomically reserve and permanently advance one index."""
        with closing(self._connect()) as con:
            con.execute("BEGIN IMMEDIATE")
            row = con.execute(
                "SELECT next_index FROM allocator WHERE singleton=1"
            ).fetchone()
            idx = int(row[0])
            con.execute(
                "UPDATE allocator SET next_index=? WHERE singleton=1", (idx + 1,)
            )
            con.execute("COMMIT")
            return idx

    def next_index(self):
        with closing(self._connect()) as con:
            row = con.execute(
                "SELECT next_index FROM allocator WHERE singleton=1"
            ).fetchone()
            return int(row[0])
