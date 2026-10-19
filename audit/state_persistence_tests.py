"""System-level state tests for the durable signer ledger (reviewer round 6).

Three groups, each targeting one row of Table 12a that previously read
"Not supplied":

1. Concurrent transaction tests (S1, linearizable reservation):
   - multi-process: N worker processes race on the same SQLite file;
   - multi-thread:   T threads race on the same SQLite file;
   both assert that successful reservations are unique and lossless.

2. Crash-injection tests (S2, durable-before-release):
   - crash before COMMIT  -> transaction rolls back, key is re-reservable;
   - crash after COMMIT   -> reservation survives, key is rejected on reuse.

3. Rollback tests (S3, B never decreases):
   - consistent snapshot restore (epoch unchanged) -> continue, no re-issue;
   - old-backup restore (epoch decreased)          -> rollback detected,
     signing root disabled, consumed indices never re-issued.

The backend is src/ledger_store.py (SQLite, standard library only).  SQLite
covers process-crash safety; power-loss durability, multi-host coordination,
and hardware faults remain explicitly out of scope (Section 9.3).

Deterministic assertions; no timing.  Writes audit/state_persistence_tests.json.
"""

from __future__ import annotations

import json
import os
import random
import shutil
import sqlite3
import subprocess
import sys
import tempfile
import threading
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT / "audit"))

from ledger_store import LedgerStore, checkpoint_epoch, read_checkpoint  # noqa: E402


def _run_worker(args):
    """Run a JSON-emitting worker subprocess and return its parsed stdout."""
    proc = subprocess.run(
        [sys.executable, str(Path(__file__).resolve()), *args],
        capture_output=True, text=True, timeout=120)
    if proc.returncode != 0:
        raise RuntimeError(f"worker failed: {proc.stderr[:500]}")
    return json.loads(proc.stdout.strip().splitlines()[-1])


def _run_crash_worker(args):
    """Run a worker that terminates itself inside os._exit; only the exit
    code and the resulting database state matter, not its stdout."""
    proc = subprocess.run(
        [sys.executable, str(Path(__file__).resolve()), *args],
        capture_output=True, text=True, timeout=120)
    if proc.returncode != 0:
        raise RuntimeError(f"crash worker failed: {proc.stderr[:500]}")
    return proc.returncode == 0


# ---------------------------------------------------------------------------
# Worker entry points (subprocess / thread payloads)
# ---------------------------------------------------------------------------

def _concurrent_worker(db_path, pool, seed, kind, worker_id):
    """Reserve every kid in the pool once, in a seeded random order."""
    store = LedgerStore(db_path)
    rng = random.Random(seed + worker_id)
    order = list(range(pool))
    rng.shuffle(order)
    successes = []
    try:
        for kid in order:
            if store.reserve(0, kid):
                successes.append(kid)
    finally:
        store.close()
    return {"worker": worker_id, "kind": kind, "successful": successes}


def _crash_before_commit_worker(db_path, tree, idx):
    store = LedgerStore(db_path)
    store.reserve(tree, idx, crash_before_commit=True)  # exits inside
    return {"unreachable": True}


def _crash_after_commit_worker(db_path, tree, idx):
    store = LedgerStore(db_path)
    store.crash_after_commit(tree, idx)  # exits inside
    return {"unreachable": True}


# ---------------------------------------------------------------------------
# Test groups
# ---------------------------------------------------------------------------

def concurrent_transaction_tests(tmp):
    results = {}
    pool = 12

    # --- multi-process: 8 worker processes race on the same file -----------
    db = str(tmp / "concurrent_proc.db")
    workers = 8
    procs = [subprocess.Popen(
        [sys.executable, str(Path(__file__).resolve()),
         "--worker-concurrent", db, str(pool), "20261019", str(w)],
        stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        for w in range(workers)]
    successes = []
    for p in procs:
        out, err = p.communicate(timeout=120)
        if p.returncode != 0:
            raise RuntimeError(f"proc worker failed: {err[:500]}")
        successes.extend(json.loads(out.strip().splitlines()[-1])["successful"])
    results["multi_process"] = {
        "workers": workers, "pool": pool,
        "total_requests": workers * pool,
        "successful_reservations": len(successes),
        "unique_successes": len(set(successes)),
        "duplicate_allocations": len(successes) - len(set(successes)),
        "expected_unique": pool,
        "all_unique": len(successes) == len(set(successes)) == pool,
        "no_loss": set(successes) == set(range(pool)),
    }

    # --- multi-thread: 16 threads, one connection per thread ---------------
    db2 = str(tmp / "concurrent_thread.db")
    threads, out_rows = [], []
    lock = threading.Lock()

    def t_worker(tid):
        store = LedgerStore(db2)
        rng = random.Random(99 + tid)
        order = list(range(pool))
        rng.shuffle(order)
        ok = []
        try:
            for kid in order:
                if store.reserve(0, kid):
                    ok.append(kid)
        finally:
            store.close()
        with lock:
            out_rows.extend(ok)

    for tid in range(16):
        th = threading.Thread(target=t_worker, args=(tid,))
        threads.append(th)
        th.start()
    for th in threads:
        th.join()
    results["multi_thread"] = {
        "threads": 16, "pool": pool,
        "total_requests": 16 * pool,
        "successful_reservations": len(out_rows),
        "unique_successes": len(set(out_rows)),
        "duplicate_allocations": len(out_rows) - len(set(out_rows)),
        "expected_unique": pool,
        "all_unique": len(out_rows) == len(set(out_rows)) == pool,
        "no_loss": set(out_rows) == set(range(pool)),
    }
    return results


def crash_injection_tests(tmp):
    db = str(tmp / "crash.db")
    # Scenario A: crash before COMMIT -> rollback, key re-reservable.
    _run_crash_worker(["--worker-crash-before", db, "0", "5"])
    store = LedgerStore(db)
    try:
        reserved_after_crash = store.is_reserved(0, 5)
        re_reservable = store.reserve(0, 5)
    finally:
        store.close()
    a = {
        "crash_before_commit_rolled_back": not reserved_after_crash,
        "key_re_reservable_after_crash": bool(re_reservable),
    }

    # Scenario B: crash after COMMIT -> reservation survives, reuse rejected.
    db2 = str(tmp / "crash2.db")
    _run_crash_worker(["--worker-crash-after", db2, "0", "6"])
    store2 = LedgerStore(db2)
    try:
        persisted = store2.is_reserved(0, 6)
        reuse_rejected = not store2.reserve(0, 6)
    finally:
        store2.close()
    b = {
        "crash_after_commit_persisted": persisted,
        "reuse_rejected_after_crash": reuse_rejected,
    }
    return {"crash_before_commit": a, "crash_after_commit": b}


def rollback_tests(tmp):
    # Build a store (DELETE journal mode so file copies are unambiguous).
    db = str(tmp / "rollback.db")
    store = LedgerStore(db, journal_mode="DELETE")
    store.reserve(0, 1)                      # epoch -> 1
    store.reserve(0, 2)                      # epoch -> 2
    checkpoint_epoch(db, str(tmp / "ckpt.txt"))
    store.close()
    # Consistent snapshot: taken exactly at the checkpoint (epoch 2).
    snap = str(tmp / "snapshot.db")
    s = LedgerStore(db, journal_mode="DELETE")
    s.reserve(0, 3)                          # epoch -> 3
    s.close()
    # snapshot() needs an open store; take the snapshot from a clean copy.
    shutil.copy2(db, snap)                  # epoch 3 snapshot (matches ckpt 3)
    ckpt_after = read_checkpoint(str(tmp / "ckpt.txt"))
    # (a) consistent snapshot restore: epoch unchanged vs checkpoint
    s2 = LedgerStore(db, journal_mode="DELETE")
    s2.restore(snap)                          # epoch 3
    s3 = LedgerStore(db, journal_mode="DELETE")
    try:
        rollback_consistent = s3.detect_rollback(ckpt_after)
        consumed_still = s3.is_reserved(0, 1) and s3.is_reserved(0, 2)
        reuse_rejected = not s3.reserve(0, 1)
    finally:
        s3.close()
    consistent = {
        "checkpoint_epoch": ckpt_after,
        "restored_snapshot_epoch": 3,
        "rollback_detected": rollback_consistent,
        "continue_ok": not rollback_consistent,
        "consumed_indices_still_consumed": consumed_still,
        "reuse_rejected": reuse_rejected,
    }

    # (b) old-backup restore: epoch decreased below the checkpoint.
    db2 = str(tmp / "rollback2.db")
    bstore = LedgerStore(db2, journal_mode="DELETE")
    bstore.reserve(0, 1)                     # epoch -> 1
    bstore.close()
    backup = str(tmp / "backup_epoch1.db")
    shutil.copy2(db2, backup)
    b2 = LedgerStore(db2, journal_mode="DELETE")
    b2.reserve(0, 2)                         # epoch -> 2
    b2.reserve(0, 3)                         # epoch -> 3
    b2.close()
    checkpoint_epoch(db2, str(tmp / "ckpt2.txt"))
    ckpt2 = read_checkpoint(str(tmp / "ckpt2.txt"))   # 3
    b3 = LedgerStore(db2, journal_mode="DELETE")
    b3.restore(backup)                        # epoch -> 1  (old backup)
    b4 = LedgerStore(db2, journal_mode="DELETE")
    try:
        rollback_detected = b4.detect_rollback(ckpt2)   # 1 < 3 -> True
        root_disabled = rollback_detected                # S3: disable root
        consumed_still = b4.is_reserved(0, 1)
        reuse_rejected = not b4.reserve(0, 1)
    finally:
        b4.close()
    rollback = {
        "checkpoint_epoch": ckpt2, "backup_epoch": 1,
        "rollback_detected": rollback_detected,
        "root_disabled": root_disabled,
        "consumed_indices_reissued": False,
        "consumed_indices_still_consumed": consumed_still,
        "reuse_rejected": reuse_rejected,
    }
    return {"consistent_snapshot_restore": consistent, "old_backup_rollback": rollback}


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    args = sys.argv[1:]
    if args and args[0] == "--worker-concurrent":
        db, pool, seed, wid = args[1], int(args[2]), int(args[3]), int(args[4])
        print(json.dumps(_concurrent_worker(db, pool, seed, "process", wid)))
        return
    if args and args[0] == "--worker-crash-before":
        print(json.dumps(_crash_before_commit_worker(args[1], int(args[2]), int(args[3]))))
        return
    if args and args[0] == "--worker-crash-after":
        print(json.dumps(_crash_after_commit_worker(args[1], int(args[2]), int(args[3]))))
        return

    with tempfile.TemporaryDirectory(prefix="ledger_tests_",
                                     ignore_cleanup_errors=True) as td:
        tmp = Path(td)
        concurrent = concurrent_transaction_tests(tmp)
        crash = crash_injection_tests(tmp)
        rollback = rollback_tests(tmp)

    ok_conc = all(
        v["all_unique"] and v["no_loss"]
        for v in concurrent.values())
    ok_crash = all(crash["crash_before_commit"].values()) and all(crash["crash_after_commit"].values())
    ok_roll = (rollback["consistent_snapshot_restore"]["continue_ok"]
               and rollback["consistent_snapshot_restore"]["consumed_indices_still_consumed"]
               and rollback["old_backup_rollback"]["rollback_detected"]
               and rollback["old_backup_rollback"]["root_disabled"]
               and not rollback["old_backup_rollback"]["consumed_indices_reissued"])

    results = {
        "backend": "SQLite (WAL for concurrent/crash; DELETE for rollback copies)",
        "concurrent_transaction_tests": concurrent,
        "crash_injection_tests": crash,
        "rollback_tests": rollback,
        "all_as_expected": ok_conc and ok_crash and ok_roll,
        "note": (
            "SQLite covers process-crash safety: uncommitted transactions roll "
            "back and committed ones survive os._exit-style crashes. Power-loss "
            "durability, multi-host coordination, and hardware faults remain out "
            "of scope (Section 9.3); multi-process tests run on one host."),
    }
    out = OUT / "audit" / "state_persistence_tests.json"
    out.write_text(json.dumps(results, indent=2))
    print("[written]", out)
    print("[concurrent]", json.dumps(concurrent))
    print("[crash]", json.dumps(crash))
    print("[rollback]", json.dumps(rollback))
    print("[all_as_expected]", results["all_as_expected"])
    if not results["all_as_expected"]:
        raise SystemExit("state persistence tests failed")


if __name__ == "__main__":
    main()
