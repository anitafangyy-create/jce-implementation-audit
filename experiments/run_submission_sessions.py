"""Run the repaired-variant timing experiment in independent sessions.

Why: the retained sample recorded Python 3.14.7, which is not installed on
the analysis host, so a reviewer could not reproduce it.  This driver runs
the same deterministic workload (same seed, same messages, same trees) in
N sessions under the *current* interpreter, keeps every session file, and
retains the median session as ``results_submission.json``.

Selection rule (fixed before looking at the data): rank sessions by the
median of their six per-configuration verification medians; retain the
median session; ties go to the lower session number.  The rule is
reproducible from the session files.

Outputs
-------
experiments/_sessions/sessionN.json          every session, verbatim
experiments/results_submission_sessions.json  cross-session summary + hashes
experiments/results_submission.json           retained (median) session

Usage:
    python3 experiments/run_submission_sessions.py --sessions 3 --cooldown 10
"""
from __future__ import annotations

import argparse
import hashlib
import json
import shutil
import statistics
import subprocess
import sys
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
OUT = HERE / "results_submission.json"
SUMMARY = HERE / "results_submission_sessions.json"
SESS_DIR = HERE / "_sessions"


def medians(doc: dict) -> dict:
    raw = doc["raw_samples"]
    out = {}
    for i, cfg in enumerate(doc["configs"]):
        blk = raw[i * 45:(i + 1) * 45]
        out[cfg] = {
            "explicit_median_ms": statistics.median(x["explicit_verify_ms"] for x in blk),
            "compact_median_ms": statistics.median(x["compact_verify_ms"] for x in blk),
        }
    return out


def overall(m: dict) -> float:
    return statistics.median(v["explicit_median_ms"] for v in m.values())


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--sessions", type=int, default=3)
    ap.add_argument("--cooldown", type=int, default=10)
    ap.add_argument("--python", default=sys.executable)
    ap.add_argument("--select-only", action="store_true",
                    help="reuse existing experiments/_sessions/sessionN.json")
    args = ap.parse_args()

    SESS_DIR.mkdir(parents=True, exist_ok=True)
    if OUT.exists() and not (HERE / "results_submission_2026-10-19_py3147.json").exists():
        shutil.copy2(OUT, HERE / "results_submission_2026-10-19_py3147.json")
        print("[archive] previous sample -> results_submission_2026-10-19_py3147.json")

    sessions = []
    for s in range(1, args.sessions + 1):
        if s > 1:
            print(f"[cooldown] {args.cooldown}s", flush=True)
            time.sleep(args.cooldown)
        path = SESS_DIR / f"session{s}.json"
        if args.select_only and path.exists():
            print(f"[reuse] session {s}: {path}", flush=True)
        else:
            cmd = [args.python, str(HERE / "experiment_submission.py"),
                   "--session", f"s{s}", "--out", str(path)]
            print(f"[run] session {s}: {' '.join(cmd)}", flush=True)
            subprocess.run(cmd, check=True)
        doc = json.loads(path.read_text())
        m = medians(doc)
        sessions.append({
            "session": f"s{s}",
            "file": str(path.relative_to(HERE.parent)),
            "sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
            "environment": doc["environment"],
            "environment_sha256": hashlib.sha256(
                json.dumps(doc["environment"], sort_keys=True).encode()).hexdigest(),
            "total_signing_events": doc["total_signing_events"],
            "total_counted_checks": doc["total_counted_checks"],
            "overall_explicit_median_ms": overall(m),
            "per_config": m,
        })
        print(f"[session {s}] overall explicit median "
              f"{overall(m):.4f} ms", flush=True)

    ranked = sorted(sessions, key=lambda r: (r["overall_explicit_median_ms"],
                                             int(r["session"][1:])))
    chosen = ranked[(len(ranked) - 1) // 2] if len(ranked) % 2 else \
        ranked[len(ranked) // 2 - 1]
    shutil.copy2(ROOT / chosen["file"], OUT)

    per_cfg = {}
    for cfg in sessions[0]["per_config"]:
        for key in ("explicit_median_ms", "compact_median_ms"):
            vals = [s["per_config"][cfg][key] for s in sessions]
            per_cfg.setdefault(cfg, {})[key] = {
                "median": statistics.median(vals),
                "min": min(vals),
                "max": max(vals),
                "spread_pct": round((max(vals) - min(vals)) / statistics.median(vals) * 100, 1),
            }

    summary = {
        "protocol": {
            "sessions": args.sessions,
            "cooldown_s": args.cooldown,
            "interpreter": args.python,
            "selection_rule": ("retain the session whose overall explicit median is "
                               "the median of the session medians; ties -> lower number"),
            "workload": ("seed 20260915, 6 configurations, 3 trees x 15 leaves, "
                         "fresh 32-byte message per event"),
        },
        "sessions": sessions,
        "retained_session": chosen["session"],
        "retained_file": "experiments/results_submission.json",
        "cross_session_per_config": per_cfg,
        "note": ("Every session uses the same deterministic workload, so message "
                 "bytes, (tree, index), and serialized sizes are identical across "
                 "sessions; only the timings differ."),
    }
    SUMMARY.write_text(json.dumps(summary, indent=2) + "\n")
    print(f"[retained] {chosen['session']} -> {OUT}")
    print(f"[written] {SUMMARY}")


if __name__ == "__main__":
    main()
