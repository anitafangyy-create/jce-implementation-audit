"""bench_like_for_like.py -- Python-side timing for the same workload the C
prototype measures, with the same operation boundaries.

Why this script exists
----------------------
The earlier comparison used Python numbers from a *different* codebase and a
different construction, and the C harness rebuilt the tree inside the signing
loop while doing the compact-mode chain work twice.  Those numbers are not a
language comparison.  This script times the repaired variant in
``experiment_submission.py`` at h = 7, w = 16, and pairs it with the C port in
``bench/native/bench_proto.c``, which now mirrors the Python construction
byte for byte (verified by comparing Merkle roots, see ``--check``).

Boundaries (identical on both sides)
------------------------------------
    keygen          build all 2^h one-time keys, their leaves, and the tree
    sign            OTS chains + authentication path from precomputed layers
                    + serialization of one signature
    verify explicit parse serialized pk/sig, one chain pass per element,
                    compare transmitted endpoints, leaf + path to root
    verify compact  same, without transmitted endpoints

``parse_ms`` is reported separately: C parses with pointer arithmetic while
Python slices bytes, so the difference belongs in the discussion, not hidden
inside the verify figure.

Usage
-----
    python3 experiments/bench_like_for_like.py --cbin native_bench/_build/bench_proto
    python3 experiments/bench_like_for_like.py --check --cbin ...

Writes: experiments/like_for_like.json
"""
from __future__ import annotations

import argparse
import json
import statistics
import subprocess
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT / "experiments"))

import experiment_submission as es  # noqa: E402
from experiment_submission import VerifyError  # noqa: E402

N = 32
W = 16
H = 8
REPS = 31
SESSIONS = 3
COOLDOWN_S = 5
MSG = bytes((i * 7 + 3) & 0xFF for i in range(64))
OUT = ROOT / "experiments" / "like_for_like.json"


# ---------------------------------------------------------------------------
# Python workload
# ---------------------------------------------------------------------------
def tree_seed(h: int) -> bytes:
    return es.H(b"SUB-TREE" + bytes([es.W_TO_CODE[W], h, 0]))


def sign_one(msg, idx, h, sk, pk, layers, mode: int) -> bytes:
    """Same work as C's wots_sign + pack_sig for one mode."""
    p = es.params(W)
    digits = es.all_digits(msg, p)
    elements = [es.chain(sk[i], 0, digits[i]) for i in range(p["len"])]
    path = es.auth_path(layers, idx, h)
    if mode == 0:
        return es.pack_sig(W, h, idx, 0, elements, pk, path)
    return es.pack_sig(W, h, idx, 1, elements, None, path)


def parse_only(sig_bytes: bytes, pk_bytes: bytes):
    """Header validation + slicing only; no chain work.  Mirrors C parsing."""
    if len(pk_bytes) != 38 or pk_bytes[:4] != es.PK_MAGIC:
        raise VerifyError("pk")
    code, h = pk_bytes[4], pk_bytes[5]
    w = es.BASE_CODE[code]
    if sig_bytes[:4] != es.SIG_MAGIC:
        raise VerifyError("magic")
    mode = sig_bytes[4]
    p = es.params(w)
    n_idx = (h + 7) // 8
    off = 7 + n_idx
    elements = [sig_bytes[off + 32 * i: off + 32 * (i + 1)] for i in range(p["len"])]
    off += p["len"] * 32
    if mode == 0:
        off += p["len"] * 32
    path = [sig_bytes[off + 32 * i: off + 32 * (i + 1)] for i in range(h)]
    return elements, path


def run_python() -> dict:
    h = H
    seed = tree_seed(h)
    # warm-up, same as C: one full tree build plus one sign/verify
    leaves, layers = es.build_tree(seed, W, h)
    pk0 = leaves[0][1]
    s0 = sign_one(MSG, 0, h, leaves[0][0], pk0, layers, 0)
    pkb = es.pack_pk(W, h, layers[h][0])
    assert es.verify(MSG, s0, pkb, expect_mode=0)

    kg, sg, ve, vc, pr = [], [], [], [], []
    for r in range(REPS):
        t = time.perf_counter_ns()
        leaves, layers = es.build_tree(seed, W, h)
        kg.append((time.perf_counter_ns() - t) / 1e6)

    pkb = es.pack_pk(W, h, layers[h][0])
    for r in range(REPS):
        idx = r % (1 << h)
        sk, pk = leaves[idx]
        t = time.perf_counter_ns()
        sig = sign_one(MSG, idx, h, sk, pk, layers, 0)
        sg.append((time.perf_counter_ns() - t) / 1e6)

    for r in range(REPS):
        idx = r % (1 << h)
        sk, pk = leaves[idx]
        se = sign_one(MSG, idx, h, sk, pk, layers, 0)
        sc = sign_one(MSG, idx, h, sk, pk, layers, 1)
        t = time.perf_counter_ns()
        assert es.verify(MSG, se, pkb, expect_mode=0)
        ve.append((time.perf_counter_ns() - t) / 1e6)
        t = time.perf_counter_ns()
        assert es.verify(MSG, sc, pkb, expect_mode=1)
        vc.append((time.perf_counter_ns() - t) / 1e6)
        t = time.perf_counter_ns()
        parse_only(sc, pkb)
        pr.append((time.perf_counter_ns() - t) / 1e6)

    return {
        "keygen_ms": statistics.median(kg),
        "sign_ms": statistics.median(sg),
        "verify_explicit_ms": statistics.median(ve),
        "verify_compact_ms": statistics.median(vc),
        "parse_ms": statistics.median(pr),
        "keygen_iqr": _iqr(kg),
        "sign_iqr": _iqr(sg),
        "verify_explicit_iqr": _iqr(ve),
        "verify_compact_iqr": _iqr(vc),
        "sig_explicit_bytes": len(sign_one(MSG, 0, h, leaves[0][0], leaves[0][1], layers, 0)),
        "sig_compact_bytes": len(sign_one(MSG, 0, h, leaves[0][0], leaves[0][1], layers, 1)),
        "n": REPS,
    }


def _iqr(vals: list[float]) -> float:
    s = sorted(vals)
    q = statistics.quantiles(s, n=4, method="inclusive")
    return q[2] - q[0]


# ---------------------------------------------------------------------------
# C harness
# ---------------------------------------------------------------------------
def run_c(cbin: Path) -> dict:
    out = subprocess.check_output([str(cbin)], text=True)
    for line in out.splitlines():
        r = json.loads(line)
        if r["h"] == H and r["compact"] is False:
            explicit = r
        if r["h"] == H and r["compact"] is True:
            compact = r
    return {
        "keygen_ms": explicit["keygen_ms"],
        "sign_ms": explicit["sign_ms"],
        "verify_explicit_ms": explicit["verify_ms"],
        "verify_compact_ms": compact["verify_ms"],
        "parse_ms": 0.0,
        "keygen_iqr": explicit["keygen_iqr"],
        "sign_iqr": explicit["sign_iqr"],
        "verify_explicit_iqr": explicit["verify_iqr"],
        "verify_compact_iqr": compact["verify_iqr"],
        "sign_chain_calls": explicit["sign_chain_calls"],
        "verify_chain_calls": explicit["verify_chain_calls"],
        "sig_explicit_bytes": explicit["sig_bytes"],
        "sig_compact_bytes": compact["sig_bytes"],
        "n": REPS,
    }


def check_roots(cbin: Path) -> bool:
    py_root = es.build_tree(tree_seed(H), W, H)[1][H][0].hex()
    out = subprocess.check_output([str(cbin), "--root", str(H)], text=True)
    c_root = out.split("root=")[1].split()[0]
    ok = py_root == c_root
    print(f"[check] python root {py_root[:16]}…  C root {c_root[:16]}…  "
          f"{'MATCH' if ok else 'MISMATCH'}")
    return ok


# ---------------------------------------------------------------------------
# Driver
# ---------------------------------------------------------------------------
def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--cbin", required=True)
    ap.add_argument("--check", action="store_true")
    args = ap.parse_args()
    cbin = Path(args.cbin).resolve()
    if not cbin.exists():
        raise SystemExit(f"missing C binary: {cbin}")

    roots_ok = check_roots(cbin)
    if not roots_ok:
        raise SystemExit("C and Python constructions differ; refusing to time")

    sessions = []
    for si in range(1, SESSIONS + 1):
        if si > 1:
            time.sleep(COOLDOWN_S)
        order = ["python", "c"] if si % 2 == 1 else ["c", "python"]
        row = {"session": si, "order": order}
        for which in order:
            row[which] = run_python() if which == "python" else run_c(cbin)
        sessions.append(row)
        print(f"[session {si}] {order}  py sign={row['python']['sign_ms']:.4f} "
              f"C sign={row['c']['sign_ms']:.4f} ms", flush=True)

    def summary(key):
        per = [s[key] for s in sessions]
        return {
            m: {
                "median": statistics.median([p[m] for p in per]),
                "min": min(p[m] for p in per),
                "max": max(p[m] for p in per),
            }
            for m in ("keygen_ms", "sign_ms", "verify_explicit_ms",
                      "verify_compact_ms")
        }

    py, c = summary("python"), summary("c")
    ratios = {
        op: round(py[op]["median"] / c[op]["median"], 3)
        for op in py
    }

    payload = {
        "environment": {
            "python": sys.version.split()[0],
            "cpu": "Apple M1 (arm64)",
            "compiler": "Apple clang 17.0.0 -O3 -std=c99",
            "sessions": SESSIONS,
            "reps_per_session": REPS,
            "w": W, "h": H, "message_bytes": len(MSG),
            "timing": "perf_counter_ns (Python) / clock_gettime(CLOCK_MONOTONIC) (C)",
            "note": ("Same construction, same message, same operation boundaries. "
                     "Python verify includes byte-slice parsing; C uses pointer "
                     "parsing. parse_ms is reported for Python only."),
        },
        "checks": {
            "merkle_root_python_equals_c": roots_ok,
            "chain_calls_per_signature": (sessions[0]["c"]["sign_chain_calls"]
                                          + sessions[0]["c"]["verify_chain_calls"]),
            "expected_chain_calls": es.params(W)["len"] * (W - 1),
            "sign_chain_calls": sessions[0]["c"]["sign_chain_calls"],
            "verify_chain_calls": sessions[0]["c"]["verify_chain_calls"],
        },
        "sessions": sessions,
        "summary": {"python": py, "c": c},
        "ratios_python_over_c": ratios,
    }
    payload["size"] = {
        "explicit_bytes": sessions[0]["python"]["sig_explicit_bytes"],
        "compact_bytes": sessions[0]["python"]["sig_compact_bytes"],
    }
    OUT.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")

    print("\nop                    Python      C        ratio")
    for op in ("keygen_ms", "sign_ms", "verify_explicit_ms", "verify_compact_ms"):
        print(f"{op:20s} {py[op]['median']:8.4f}  {c[op]['median']:8.4f}  "
              f"{ratios[op]:6.2f}x")
    print(f"\nwritten {OUT}")


if __name__ == "__main__":
    main()
