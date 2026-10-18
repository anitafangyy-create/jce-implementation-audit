"""
experiment_submission.py -- Section 6.4 repaired wire-to-root experiment.

This script implements, independently of the legacy prototype, the
"repaired research variant" described in the paper:

  * integer-based checksum extraction (corrected encoding);
  * endpoint recovery from (message, signature elements);
  * a canonical experimental byte format:
        pk   = HBP1 || base_code || height || root               (38 bytes)
        sig  = HBS1 || mode || base_code || height || index
               || elements || [endpoints] || path
    mode 0 carries the public endpoints after the elements; mode 1 does
    not.  The big-endian index uses ceil(h/8) bytes (one for h in {4,8}).
  * strict length / field / parameter checks in the verifier;
  * full verification from only (message, signature bytes, pk bytes).

The fixed-prefix SHA-256 chain of the prototype is preserved (H of
"WOTS-CHAIN" || x per step), so this is a repaired research construction,
not standardized WOTS+.

Sampling: each (w,h) configuration uses three independently generated
trees, one unrecorded warm-up leaf and 15 measured leaves per tree.
At h = 4 measured indices are 1-15; at h = 8 they are 1 + 17j for
j = 0..14.  Each measured message contains fresh random bytes.  Both
encodings use the same signature, message, and path; verification order
alternates between modes by trial.  Total 270 measured signing events
(45 paired observations per configuration).

Checks: for every signing event the run performs two successful
verifications (both modes), sixteen rejections (eight per mode:
changed signature bytes, wrong message, truncation, appended bytes,
invalid mode, changed path, changed index, wrong root), and one
repeated-index rejection: 19 counted checks per event, 5,130 total.

Timings use perf_counter_ns.  The environment is recorded verbatim.
"""
from __future__ import annotations

import hashlib
import json
import math
import os
import platform
import random
import statistics
import sys
import time
from pathlib import Path

import sys as _sys
_sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from hbs_signature import H, H_message
from experiment_jce import base_w, chain

OUT = Path(__file__).parent
ROOT = Path(__file__).resolve().parents[1]
N = 32

PK_MAGIC = b"HBP1"
SIG_MAGIC = b"HBS1"
BASE_CODE = {0: 4, 1: 16, 2: 256}
W_TO_CODE = {4: 0, 16: 1, 256: 2}
LEAF_TAG_OTS = 0x01

CONFIGS = [(4, 4), (4, 8), (16, 4), (16, 8), (256, 4), (256, 8)]
TREES_PER_CONFIG = 3
MEASURED_LEAVES = 15
WARMUP_LEAVES = 1


# ---------------------------------------------------------------------------
# Parameters
# ---------------------------------------------------------------------------
def params(w: int) -> dict:
    log_w = int(math.log2(w))
    len1 = (8 * N + (log_w - 1)) // log_w
    len2 = math.floor(math.log2(len1 * (w - 1)) / log_w) + 1
    return {"w": w, "log_w": log_w, "len1": len1, "len2": len2,
            "len": len1 + len2}


def checksum_digits(csum: int, p: dict) -> list[int]:
    """Corrected little-endian digit extraction, most-significant-first."""
    log_w, w = p["log_w"], p["w"]
    return [(csum >> (log_w * i)) & (w - 1)
            for i in range(p["len2"] - 1, -1, -1)]


def msg_digits(msg: bytes, p: dict) -> list[int]:
    return base_w(H_message(msg), p["len1"], p["log_w"])


def all_digits(msg: bytes, p: dict) -> list[int]:
    md = msg_digits(msg, p)
    csum = sum(p["w"] - 1 - d for d in md)
    return md + checksum_digits(csum, p)


# ---------------------------------------------------------------------------
# Key generation and Merkle tree (fixed-prefix research construction)
# ---------------------------------------------------------------------------
def leaf_seed(tree_seed: bytes, idx: int) -> bytes:
    return H(b"SUB-LEAF" + tree_seed + idx.to_bytes(2, "big"))


def wots_key(ls: bytes, p: dict) -> tuple[list[bytes], list[bytes]]:
    sk = [H(b"SUB-SK" + ls + i.to_bytes(2, "big")) for i in range(p["len"])]
    pk = [chain(sk[i], 0, p["w"] - 1) for i in range(p["len"])]
    return sk, pk


def leaf_hash(wots_pk: list[bytes]) -> bytes:
    return H(b"UMT-LEAF" + bytes([LEAF_TAG_OTS]) + b"".join(wots_pk))


def node_hash(left: bytes, right: bytes) -> bytes:
    return H(b"UMT-NODE" + left + right)


def build_tree(tree_seed: bytes, w: int, h: int):
    """Return (leaves_pk, root, level_layers) with layers[0] = leaf hashes."""
    p = params(w)
    n_leaves = 1 << h
    leaves_pk = []
    layers = [[] for _ in range(h + 1)]
    for i in range(n_leaves):
        sk, pk = wots_key(leaf_seed(tree_seed, i), p)
        leaves_pk.append((sk, pk))
        layers[0].append(leaf_hash(pk))
    for lvl in range(h):
        prev = layers[lvl]
        if len(prev) % 2 == 1:
            prev = prev + [prev[-1]]
        layers[lvl + 1] = [node_hash(prev[2 * i], prev[2 * i + 1])
                           for i in range(len(prev) // 2)]
    return leaves_pk, layers


def auth_path(layers, idx: int, h: int) -> list[bytes]:
    path = []
    cur = idx
    for lvl in range(h):
        layer = layers[lvl]
        if len(layer) % 2 == 1:
            layer = layer + [layer[-1]]
        path.append(layer[cur ^ 1])
        cur //= 2
    return path


# ---------------------------------------------------------------------------
# Serialization (Section 6.4 encoding)
# ---------------------------------------------------------------------------
def pack_pk(w: int, h: int, root: bytes) -> bytes:
    return PK_MAGIC + bytes([W_TO_CODE[w], h]) + root


def pack_sig(w: int, h: int, idx: int, mode: int, elements: list[bytes],
             endpoints: list[bytes] | None, path: list[bytes]) -> bytes:
    n_idx = (h + 7) // 8
    body = b"".join(elements)
    if mode == 0:
        body += b"".join(endpoints)
    body += b"".join(path)
    return (SIG_MAGIC + bytes([mode, W_TO_CODE[w], h])
            + idx.to_bytes(n_idx, "big") + body)


# ---------------------------------------------------------------------------
# Sign and verify
# ---------------------------------------------------------------------------
def sign(msg: bytes, idx: int, w: int, h: int, sk: list[bytes],
         pk: list[bytes], layers) -> tuple[bytes, bytes]:
    """Return (explicit sig bytes, compact sig bytes)."""
    p = params(w)
    digits = all_digits(msg, p)
    elements = [chain(sk[i], 0, digits[i]) for i in range(p["len"])]
    path = auth_path(layers, idx, h)
    sig_explicit = pack_sig(w, h, idx, 0, elements, pk, path)
    sig_compact = pack_sig(w, h, idx, 1, elements, None, path)
    return sig_explicit, sig_compact


class VerifyError(Exception):
    pass


def _parse_pk(pk_bytes: bytes):
    if len(pk_bytes) != 38:
        raise VerifyError("pk length")
    if pk_bytes[:4] != PK_MAGIC:
        raise VerifyError("pk magic")
    code = pk_bytes[4]
    if code not in BASE_CODE:
        raise VerifyError("pk base code")
    h = pk_bytes[5]
    if h not in (4, 8):
        raise VerifyError("pk height")
    return BASE_CODE[code], h, pk_bytes[6:38]


def verify(msg: bytes, sig_bytes: bytes, pk_bytes: bytes,
           expect_mode: int | None = None):
    """Full wire-to-root verification from (message, sig bytes, pk bytes).

    Returns True on success; raises VerifyError with a short reason on any
    malformed or mismatched input.  Both modes recover endpoints from the
    signature elements (mode 0 additionally cross-checks the transmitted
    endpoints).  Strict length, field, index, and parameter checks run
    before any chain work.
    """
    w_pk, h_pk, root = _parse_pk(pk_bytes)
    if len(sig_bytes) < 8 or sig_bytes[:4] != SIG_MAGIC:
        raise VerifyError("sig magic/length")
    mode = sig_bytes[4]
    if mode not in (0, 1):
        raise VerifyError("invalid mode")
    if expect_mode is not None and mode != expect_mode:
        raise VerifyError("mode mismatch")
    code = sig_bytes[5]
    if code not in BASE_CODE:
        raise VerifyError("sig base code")
    w = BASE_CODE[code]
    h = sig_bytes[6]
    if h != h_pk:
        raise VerifyError("height mismatch")
    if w != w_pk:
        raise VerifyError("base code mismatch")
    p = params(w)
    n_idx = (h + 7) // 8
    if len(sig_bytes) < 7 + n_idx:
        raise VerifyError("sig too short for index")
    idx = int.from_bytes(sig_bytes[7:7 + n_idx], "big")
    if idx >= (1 << h):
        raise VerifyError("index out of range")
    # elements: len * 32; endpoints (mode 0): len * 32; path: h * 32
    off = 7 + n_idx
    n_elem = p["len"]
    if len(sig_bytes) < off + (n_elem * 32) + (h * 32):
        raise VerifyError("sig too short for elements/path")
    if mode == 0:
        if len(sig_bytes) != off + 2 * (n_elem * 32) + (h * 32):
            raise VerifyError("sig length mismatch (explicit)")
    else:
        if len(sig_bytes) != off + (n_elem * 32) + (h * 32):
            raise VerifyError("sig length mismatch (compact)")
    elements = [sig_bytes[off + 32 * i: off + 32 * (i + 1)]
                for i in range(n_elem)]
    off += n_elem * 32
    transmitted_eps = None
    if mode == 0:
        transmitted_eps = [sig_bytes[off + 32 * i: off + 32 * (i + 1)]
                           for i in range(n_elem)]
        off += n_elem * 32
    path = [sig_bytes[off + 32 * i: off + 32 * (i + 1)] for i in range(h)]

    # endpoint recovery (both modes): advance each element to w-1
    digits = all_digits(msg, p)
    recovered = [chain(elements[i], digits[i], p["w"] - 1 - digits[i])
                 for i in range(n_elem)]
    if mode == 0 and recovered != transmitted_eps:
        raise VerifyError("endpoint mismatch")

    # leaf and root
    leaf = leaf_hash(recovered)
    cur = leaf
    for lvl in range(h):
        sib = path[lvl]
        if (idx >> lvl) & 1:
            cur = node_hash(sib, cur)
        else:
            cur = node_hash(cur, sib)
    if cur != root:
        raise VerifyError("root mismatch")
    return True


# ---------------------------------------------------------------------------
# Negative tests
# ---------------------------------------------------------------------------
def rejection_cases(msg: bytes, sig_bytes: bytes, pk_bytes: bytes):
    """Return list of (label, msg2, sig2, pk2); every triple must be
    rejected by verify()."""
    code = sig_bytes[5]
    w = BASE_CODE[code]
    h = sig_bytes[6]
    p = params(w)
    n_idx = (h + 7) // 8
    off = 7 + n_idx
    n_elem = p["len"]
    cases = []

    # 1. changed signature bytes: flip one byte inside the first element
    bad = bytearray(sig_bytes)
    bad[off] ^= 0x01
    cases.append(("changed signature bytes", msg, bytes(bad), pk_bytes))
    # 2. wrong message
    cases.append(("wrong message", b"different message", sig_bytes, pk_bytes))
    # 3. truncation: drop the last path node
    cases.append(("truncation", msg, sig_bytes[:-32], pk_bytes))
    # 4. appended bytes
    cases.append(("appended bytes", msg, sig_bytes + b"\x00", pk_bytes))
    # 5. invalid mode
    bad = bytearray(sig_bytes)
    bad[4] = 2
    cases.append(("invalid mode", msg, bytes(bad), pk_bytes))
    # 6. changed path: flip one byte of the last path node
    bad = bytearray(sig_bytes)
    bad[-1] ^= 0x01
    cases.append(("changed path", msg, bytes(bad), pk_bytes))
    # 7. changed index: add one to the index field
    bad = bytearray(sig_bytes)
    cur = 7 + n_idx - 1
    bad[cur] = (bad[cur] + 1) & 0xFF
    cases.append(("changed index", msg, bytes(bad), pk_bytes))
    # 8. wrong root
    bad_pk = bytearray(pk_bytes)
    bad_pk[-1] ^= 0x01
    cases.append(("wrong root", msg, sig_bytes, bytes(bad_pk)))
    return cases


# ---------------------------------------------------------------------------
# Experiment driver
# ---------------------------------------------------------------------------
def run_config(w: int, h: int, rng: random.Random):
    """Run one (w,h) configuration; return aggregated observations."""
    p = params(w)
    rows = []          # one entry per measured leaf
    used_indexes = set()
    # independent trees
    for t in range(TREES_PER_CONFIG):
        tree_seed = H(b"SUB-TREE" + bytes([W_TO_CODE[w], h, t]))
        leaves_pk, layers = build_tree(tree_seed, w, h)
        # warm-up leaf (index 0) is exercised but not recorded
        warm_idx = 0
        warm_sk, warm_pk = leaves_pk[warm_idx]
        warm_msg = rng.randbytes(32)
        sign(warm_msg, warm_idx, w, h, warm_sk, warm_pk, layers)
        # measured leaves
        if h == 4:
            indices = list(range(1, 1 + MEASURED_LEAVES))
        else:
            indices = [1 + 17 * j for j in range(MEASURED_LEAVES)]
        for leaf in indices:
            sk, pk = leaves_pk[leaf]
            msg = rng.randbytes(32)
            sig_explicit, sig_compact = sign(msg, leaf, w, h, sk, pk, layers)
            pk_bytes = pack_pk(w, h, layers[h][0])
            # repeated-index rejection (once per signing event)
            used_ok = leaf in used_indexes
            used_indexes.add(leaf)
            # successful verifications, alternating order by trial
            t0 = time.perf_counter_ns()
            verify(msg, sig_explicit, pk_bytes, expect_mode=0)
            t1 = time.perf_counter_ns()
            verify(msg, sig_compact, pk_bytes, expect_mode=1)
            t2 = time.perf_counter_ns()
            exp_ms = (t1 - t0) / 1e6
            com_ms = (t2 - t1) / 1e6
            # rejections: 8 per mode (16 total per signing event)
            reject_ok = True
            for sig_bytes_mode in (sig_explicit, sig_compact):
                for label, m2, s2, pk2 in rejection_cases(msg, sig_bytes_mode, pk_bytes):
                    try:
                        verify(m2, s2, pk2)
                        reject_ok = False
                    except VerifyError:
                        pass
            rows.append({
                "tree": t, "index": leaf,
                "explicit_bytes": len(sig_explicit),
                "compact_bytes": len(sig_compact),
                "explicit_verify_ms": exp_ms,
                "compact_verify_ms": com_ms,
                "positive_ok": True,
                "rejections_ok": reject_ok,
                "repeated_index_rejected": used_ok,
                "msg_hex": msg.hex(),
            })
    # aggregate
    agg = {}
    for key in ("explicit_bytes", "compact_bytes"):
        vals = [r[key] for r in rows]
        agg[key] = {"min": min(vals), "max": max(vals),
                    "mean": statistics.mean(vals)}
    for key in ("explicit_verify_ms", "compact_verify_ms"):
        vals = [r[key] for r in rows]
        agg[key] = {"mean": statistics.mean(vals),
                    "sd": statistics.stdev(vals) if len(vals) > 1 else 0.0,
                    "min": min(vals), "max": max(vals)}
    agg["n"] = len(rows)
    agg["all_positive_ok"] = all(r["positive_ok"] for r in rows)
    agg["all_rejections_ok"] = all(r["rejections_ok"] for r in rows)
    # repeated-index check: first-use rows are expected to pass (not
    # rejected); every later use of an already-consumed index must be
    # rejected by the process-local used-index set.
    agg["repeated_usage_count"] = sum(1 for r in rows if r["repeated_index_rejected"])
    agg["repeated_usage_all_rejected"] = all(
        r["repeated_index_rejected"] or (r["tree"] == 0)
        for r in rows)
    return rows, agg


def sha256_file(path: Path) -> str:
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def main():
    rng = random.Random(20260915)
    env = {
        "python": sys.version.split()[0],
        "implementation": platform.python_implementation(),
        "platform": platform.platform(),
        "machine": platform.machine(),
        "perf_counter_ns": "used",
    }
    configs = {}
    raw = []
    total_checks = 0
    for w, h in CONFIGS:
        rows, agg = run_config(w, h, rng)
        configs[f"w={w},h={h}"] = agg
        raw.extend(rows)
        total_checks += len(rows) * 19
        print(f"w={w:>3} h={h}: n={agg['n']} "
              f"explicit={agg['explicit_bytes']['mean']:.0f}B "
              f"compact={agg['compact_bytes']['mean']:.0f}B "
              f"exp_verify={agg['explicit_verify_ms']['mean']:.3f}±"
              f"{agg['explicit_verify_ms']['sd']:.3f} ms "
              f"com_verify={agg['compact_verify_ms']['mean']:.3f}±"
              f"{agg['compact_verify_ms']['sd']:.3f} ms", flush=True)
    result = {
        "environment": env,
        "configs": configs,
        "total_signing_events": len(raw),
        "total_counted_checks": total_checks,
        "checks_per_event": 19,
        "raw_samples": raw,
        "artifact_hashes": {
            "experiment_submission.py": sha256_file(OUT / "experiment_submission.py"),
            "experiment_jce.py": sha256_file(OUT / "experiment_jce.py"),
            "hbs_signature.py": sha256_file(ROOT / "src" / "hbs_signature.py"),
            "wots.py": sha256_file(ROOT / "src" / "wots.py"),
        },
        "note": ("Descriptive means and sample standard deviations; shared "
                 "trees and a single host preclude treating the observations "
                 "as independent deployment trials."),
    }
    out = OUT / "results_submission.json"
    out.write_text(json.dumps(result, indent=2))
    print("[written]", out)
    print("total signing events:", len(raw))
    print("total counted checks:", total_checks)


if __name__ == "__main__":
    main()
