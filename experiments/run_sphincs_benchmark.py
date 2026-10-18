"""
run_sphincs_benchmark.py -- standardized baseline for Table 7.

Compiles the official SPHINCS+ reference implementation (FIPS 205
parameter sets SLH-DSA-SHA2-128s / SLH-DSA-SHA2-128f) on this machine
and times key generation, signing, and verification with
CLOCK_MONOTONIC.  Writes sphincs_benchmark.json with the environment,
sizes, and per-round timings.

These timings are used only as a same-machine size/perf context row in
Table 7; they are not compared as "our scheme is faster" claims, because
the prototype and the standardized scheme do not offer equivalent
security guarantees.
"""
from __future__ import annotations

import json
import platform
import statistics
import subprocess
import sys
from pathlib import Path

REF = Path(__file__).parent / "sphincsplus-master" / "ref"
OUT = Path(__file__).parent

PARAM_SETS = ["sphincs-sha2-128s", "sphincs-sha2-128f"]
ROUNDS = 100


def compile_ref(params: str):
    srcs = ["address.c", "randombytes.c", "merkle.c", "wots.c", "wotsx1.c",
            "utils.c", "utilsx1.c", "fors.c", "sign.c",
            "sha2.c", "hash_sha2.c", "thash_sha2_robust.c"]
    inc = " -I. "
    cmd = (["cc", "-O3", "-std=c99", "-Wall",
            f"-DPARAMS={params}", f"-DROUNDS={ROUNDS}",
            "-o", "/tmp/spx_timing"] + inc.split()
           + [str(REF / s) for s in srcs]
           + [str(REF / "benchmark_timing.c")])
    subprocess.run(cmd, check=True, cwd=REF)
    return "/tmp/spx_timing"


def run(params: str):
    exe = compile_ref(params)
    proc = subprocess.run([exe], capture_output=True, text=True, check=True)
    meta = {}
    rounds = []
    for line in proc.stdout.splitlines():
        if "=" in line and "_ms=" not in line:
            k, v = line.split("=", 1)
            meta[k] = v
        elif "_ms=" in line:
            d = dict(item.split("=", 1) for item in line.split())
            rounds.append({k: float(v) for k, v in d.items()})
    return meta, rounds


def summarize(rounds: list[dict]) -> dict:
    out = {}
    for key in ("keygen_ms", "sign_ms", "verify_ms"):
        vals = [r[key] for r in rounds]
        out[key] = {"mean": statistics.mean(vals),
                    "median": statistics.median(vals),
                    "sd": statistics.stdev(vals) if len(vals) > 1 else 0.0,
                    "min": min(vals), "max": max(vals)}
    out["n"] = len(rounds)
    return out


def main():
    env = {
        "python": sys.version.split()[0],
        "platform": platform.platform(),
        "machine": platform.machine(),
        "compiler": "cc (clang) -O3",
        "clock": "CLOCK_MONOTONIC",
    }
    result = {"environment": env, "sets": {}}
    for params in PARAM_SETS:
        meta, rounds = run(params)
        result["sets"][params] = {
            "meta": meta,
            "summary": summarize(rounds),
            "rounds": rounds,
        }
        s = result["sets"][params]["summary"]
        print(f"{params}: pk={meta['pk_bytes']} sig={meta['sig_bytes']} "
              f"keygen={s['keygen_ms']['median']:.3f}ms "
              f"sign={s['sign_ms']['median']:.3f}ms "
              f"verify={s['verify_ms']['median']:.3f}ms", flush=True)
    out = OUT / "sphincs_benchmark.json"
    out.write_text(json.dumps(result, indent=2))
    print("[written]", out)


if __name__ == "__main__":
    main()
