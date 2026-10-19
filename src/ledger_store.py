"""Durable signer-ledger store backed by SQLite.

Provides the S1-S3 semantics that the process-local ledger of the repaired
experiment could not: linearizable reservation through BEGIN IMMEDIATE
transactions plus a UNIQUE (tree_id, leaf_index) constraint, crash safety
through SQLite's journal, and rollback detection through a monotonically
increasing ledger epoch persisted in the same file.

Design notes
------------
* Every successful reservation is committed before the caller releases any
  signature bytes (durable-before-release).  The crash hooks below let tests
  exit either before or after the COMMIT to exercise both sides of that
  ordering.
* SQLite covers process-crash safety (os._exit, SIGKILL): uncommitted
  transactions roll back, committed ones survive.  Power-loss durability
  depends on the filesystem/journal settings and is not claimed here.
* This module is the storage engine used by audit/state_persistence_tests.py;
  the repaired timing experiment keeps its process-local ledger, and the
  engine is an optional component for production use.

The module is pure standard library (sqlite3), no third-party dependency.
"""

from __future__ import annotations

import os
import shutil
import sqlite3
import time
from pathlib import Path

SCHEMA = """
CREATE TABLE IF NOT EXISTS ledger (
    tree_id     INTEGER NOT NULL,
    leaf_index  INTEGER NOT NULL,
    consumed_at TEXT    NOT NULL,
    PRIMARY KEY (tree_id, leaf_index)
);
CREATE TABLE IF NOT EXISTS meta (
    key   TEXT PRIMARY KEY,
    value TEXT NOT NULL
);
"""

_EPOCH_KEY = "ledger_epoch"


class LedgerStore:
    """Durable one-time-key ledger with linearizable reservation."""

    def __init__(self, path, journal_mode: str = "WAL", busy_timeout_ms: int = 10_000):
        self.path = str(path)
        Path(self.path).parent.mkdir(parents=True, exist_ok=True)
        self._conn = sqlite3.connect(self.path, timeout=busy_timeout_ms / 1000.0)
        # busy_timeout must be set before any write-bearing PRAGMA so that
        # concurrent first-open initializations wait instead of failing.
        self._conn.execute(f"PRAGMA busy_timeout={busy_timeout_ms}")
        self._conn.execute("PRAGMA synchronous=FULL")
        # Schema creation must be unconditional.  Gating it on "the file was
        # empty" is racy: a second opener can observe the file after the first
        # has switched it to WAL (non-empty) but before the tables exist, and
        # then skip initialization ("no such table: meta").  Every statement
        # below is idempotent and busy_timeout serializes concurrent openers.
        # journal_mode needs an exclusive lock when it actually changes the
        # file; under concurrent first opens another opener may already hold
        # it, in which case the mode is already set and skipping is safe.
        try:
            self._conn.execute(
                f"PRAGMA journal_mode={journal_mode}").fetchall()
        except sqlite3.OperationalError:
            pass
        self._conn.executescript(SCHEMA)
        with self._conn:
            self._conn.execute(
                "INSERT OR IGNORE INTO meta(key, value) VALUES(?, '0')",
                (_EPOCH_KEY,))

    # -- core API ----------------------------------------------------------

    def reserve(self, tree_id: int, leaf_index: int,
                crash_before_commit: bool = False) -> bool:
        """Atomically reserve (tree_id, leaf_index); False if already used.

        crash_before_commit simulates a process crash inside the transaction:
        the INSERT is performed but never committed, so SQLite rolls it back
        and the key remains unreserved.  crash_after_commit (below) simulates
        a crash immediately after the reservation is durable and the signature
        has been released.
        """
        try:
            self._conn.execute("BEGIN IMMEDIATE")
            row = self._conn.execute(
                "SELECT 1 FROM ledger WHERE tree_id=? AND leaf_index=?",
                (tree_id, leaf_index)).fetchone()
            if row is not None:
                self._conn.rollback()
                return False
            self._conn.execute(
                "INSERT INTO ledger(tree_id, leaf_index, consumed_at) "
                "VALUES(?, ?, ?)",
                (tree_id, leaf_index,
                 time.strftime("%Y-%m-%dT%H:%M:%S")))
            self._conn.execute(
                "UPDATE meta SET value = CAST(value AS INTEGER) + 1 "
                "WHERE key=?", (_EPOCH_KEY,))
            if crash_before_commit:
                # Kill the process with the transaction still open.  Do not
                # call rollback() first: the point of this injection is that
                # SQLite itself recovers an uncommitted transaction after the
                # process dies, not that an explicit rollback works.
                os._exit(0)  # never reached
            self._conn.commit()
            return True
        except sqlite3.OperationalError:
            self._conn.rollback()
            raise

    def crash_after_commit(self, tree_id: int, leaf_index: int) -> bool:
        """Reserve and commit, then exit immediately (crash after release).

        Models: reservation is durable, signature bytes have left the device,
        and the process dies before doing anything else.  After restart the
        key must remain consumed.
        """
        ok = self.reserve(tree_id, leaf_index)   # commits inside
        os._exit(0)
        return ok  # never reached

    def is_reserved(self, tree_id: int, leaf_index: int) -> bool:
        row = self._conn.execute(
            "SELECT 1 FROM ledger WHERE tree_id=? AND leaf_index=?",
            (tree_id, leaf_index)).fetchone()
        return row is not None

    def used_count(self) -> int:
        return int(self._conn.execute(
            "SELECT COUNT(*) FROM ledger").fetchone()[0])

    def epoch(self) -> int:
        row = self._conn.execute(
            "SELECT value FROM meta WHERE key=?", (_EPOCH_KEY,)).fetchone()
        return int(row[0]) if row else 0

    # -- snapshot / rollback ----------------------------------------------

    def snapshot(self, dest) -> None:
        """Copy the database file (all data committed so far).

        Callers should close the store first, or use SQLite's online backup;
        for the small test volumes here, an offline copy after close is
        sufficient and unambiguous.  This method is provided for the tests
        and documentation of the restore path.
        """
        self.close()
        shutil.copy2(self.path, dest)

    def restore(self, src) -> None:
        """Replace the database with a backup file (simulates old-backup
        restore or snapshot rollback).  After restore the epoch is whatever
        the backup carried, so a monotonicity check against an external
        expected epoch detects rollback."""
        self.close()
        shutil.copy2(src, self.path)

    def detect_rollback(self, expected_min_epoch: int) -> bool:
        """True if the on-disk epoch is below the expected monotonic floor.

        expected_min_epoch should come from a trusted external record (e.g. a
        separate checkpoint file updated only by a successful run).  A backup
        that predates the last run then yields epoch < expected and the signer
        must disable the signing root (S3) instead of re-issuing keys.
        """
        return self.epoch() < expected_min_epoch

    # -- maintenance --------------------------------------------------------

    def close(self) -> None:
        try:
            self._conn.close()
        except sqlite3.ProgrammingError:
            pass


def checkpoint_epoch(store_path, checkpoint_path) -> None:
    """Persist the current epoch to an external, non-restored checkpoint."""
    s = LedgerStore(store_path)
    try:
        Path(checkpoint_path).write_text(str(s.epoch()), encoding="ascii")
    finally:
        s.close()


def read_checkpoint(checkpoint_path) -> int:
    try:
        return int(Path(checkpoint_path).read_text(encoding="ascii").strip())
    except (OSError, ValueError):
        return 0
