#!/usr/bin/env python3
"""Synthetic endpoint-mode microbenchmark harness.

IMPORTANT: This is not the paper's cryptographic implementation. Replace the
two mode functions with actual implementation calls before citing measurements.
"""
import argparse
import csv
import hashlib
import os
import platform
import random
import statistics
import time
from pathlib import Path


def explicit_mode(endpoint: bytes) -> bytes:
    """Synthetic explicit wire encoding: tag + length + endpoint bytes."""
    return b"\x01" + len(endpoint).to_bytes(2, "big") + endpoint


def recovered_mode(endpoint: bytes) -> bytes:
    """Synthetic compact encoding: deterministic digest as a stand-in only."""
    # This does NOT recover an endpoint and is not cryptographically equivalent.
    # It exists only to demonstrate how to instrument two code paths.
    return hashlib.sha256(b"synthetic-recovered-mode" + endpoint).digest()


def timed_call(fn, arg, repeats):
    samples = []
    for _ in range(repeats):
        t0 = time.perf_counter_ns()
        fn(arg)
        samples.append(time.perf_counter_ns() - t0)
    return samples


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--trees", type=int, default=20)
    ap.add_argument("--leaves", type=int, default=15)
    ap.add_argument("--repeats", type=int, default=30)
    ap.add_argument("--warmups", type=int, default=100)
    ap.add_argument("--endpoint-bytes", type=int, default=32)
    ap.add_argument("--seed", type=int, default=20261019)
    ap.add_argument("--out", default="results/endpoint_raw.csv")
    args = ap.parse_args()
    if min(args.trees, args.leaves, args.repeats) < 1 or args.warmups < 0:
        ap.error("trees, leaves and repeats must be >=1; warmups must be >=0")

    rng = random.Random(args.seed)
    rows = []
    for tree_id in range(args.trees):
        endpoints = [
            rng.randbytes(args.endpoint_bytes) if hasattr(rng, "randbytes")
            else bytes(rng.randrange(256) for _ in range(args.endpoint_bytes))
            for _ in range(args.leaves)
        ]
        # Warm up both paths.
        for endpoint in endpoints[:min(len(endpoints), max(1, args.warmups))]:
            explicit_mode(endpoint)
            recovered_mode(endpoint)

        # Interleave order per leaf to reduce systematic order bias.
        for leaf_id, endpoint in enumerate(endpoints):
            modes = [("explicit", explicit_mode), ("recovered", recovered_mode)]
            rng.shuffle(modes)
            for mode, fn in modes:
                samples = timed_call(fn, endpoint, args.repeats)
                for repetition, elapsed_ns in enumerate(samples):
                    rows.append({
                        "tree_id": tree_id,
                        "leaf_id": leaf_id,
                        "mode": mode,
                        "repetition": repetition,
                        "elapsed_ns": elapsed_ns,
                        "output_bytes": len(fn(endpoint)),
                        "endpoint_bytes": len(endpoint),
                        "seed": args.seed,
                        "python": platform.python_version(),
                        "platform": platform.platform(),
                    })

    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    with out.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)
    print(f"Wrote {len(rows)} raw timing rows to {out}")
    print("WARNING: synthetic modes only; do not report these numbers as paper results.")


if __name__ == "__main__":
    main()
