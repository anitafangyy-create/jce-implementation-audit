#!/usr/bin/env python3
import argparse
import threading
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from src.sqlite_allocator import SQLiteAllocator


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--workers", type=int, default=8)
    p.add_argument("--per-worker", type=int, default=100)
    p.add_argument("--db", default="results/state_stress.sqlite")
    a = p.parse_args()
    if a.workers < 1 or a.per_worker < 1:
        p.error("workers and per-worker must be >= 1")

    db = Path(a.db)
    db.parent.mkdir(parents=True, exist_ok=True)
    if db.exists():
        db.unlink()
    allocator = SQLiteAllocator(db)
    barrier = threading.Barrier(a.workers)
    all_indices, errors = [], []
    lock = threading.Lock()

    def worker():
        try:
            local_allocator = SQLiteAllocator(db)
            barrier.wait()
            vals = [local_allocator.reserve() for _ in range(a.per_worker)]
            with lock:
                all_indices.extend(vals)
        except Exception as e:
            with lock:
                errors.append(repr(e))

    threads = [threading.Thread(target=worker) for _ in range(a.workers)]
    for t in threads: t.start()
    for t in threads: t.join()

    expected = a.workers * a.per_worker
    unique = len(set(all_indices))
    print({
        "workers": a.workers, "per_worker": a.per_worker,
        "expected_reservations": expected, "observed_reservations": len(all_indices),
        "unique_indices": unique, "next_index": allocator.next_index(),
        "errors": errors, "pass": not errors and len(all_indices) == expected
                 and unique == expected and allocator.next_index() == expected
    })
    if errors or len(all_indices) != expected or unique != expected or allocator.next_index() != expected:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
