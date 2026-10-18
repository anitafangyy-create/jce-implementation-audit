"""
Extended benchmark for JCE submission.

Studies:
  1. Winternitz parameter w sweep (w = 4, 16, 256) -> size vs speed trade-off.
  2. Statistical rigor: 10 repetitions, mean +/- std.
  3. Memory footprint (sk, pk, sig sizes in KB).
  4. Verification cost breakdown (chain iterations).
"""
from __future__ import annotations

import os
import time
import math
import statistics
import dataclasses
import json
from pathlib import Path

from hbs_signature import H, H_message, HASH_LEN

OUT = Path(__file__).parent
N = 32  # hash output bytes


def base_w(data: bytes, out_len: int, log_w: int) -> list[int]:
    w = 1 << log_w
    digits, in_pos, in_bits, total = [], 0, 0, 0
    for _ in range(out_len):
        while in_bits < log_w:
            total = (total << 8) | data[in_pos]
            in_pos += 1
            in_bits += 8
        in_bits -= log_w
        digits.append((total >> in_bits) & (w - 1))
        total &= (1 << in_bits) - 1
    return digits


def chain(x: bytes, start: int, steps: int) -> bytes:
    for _ in range(start, start + steps):
        x = H(b"WOTS-CHAIN" + x)
    return x


@dataclasses.dataclass
class WOTSParams:
    w: int
    log_w: int
    len1: int
    len2: int
    len: int

    @staticmethod
    def for_w(w: int) -> "WOTSParams":
        log_w = int(math.log2(w))
        len1 = (8 * N + (log_w - 1)) // log_w
        len2 = math.floor(math.log2(len1 * (w - 1)) / log_w) + 1
        return WOTSParams(w, log_w, len1, len2, len1 + len2)


def wots_keygen(p: WOTSParams):
    sk = [os.urandom(N) for _ in range(p.len)]
    pk = [chain(sk[i], 0, p.w - 1) for i in range(p.len)]
    return sk, pk


def wots_sign(sk: list[bytes], msg: bytes, p: WOTSParams) -> list[bytes]:
    digest = H_message(msg)
    md = base_w(digest, p.len1, p.log_w)
    checksum = sum(p.w - 1 - d for d in md)
    cd = base_w(checksum.to_bytes(N, "big"), p.len2, p.log_w)
    digits = md + cd
    return [chain(sk[i], 0, digits[i]) for i in range(p.len)]


def wots_verify(msg: bytes, sig: list[bytes], pk: list[bytes], p: WOTSParams) -> bool:
    digest = H_message(msg)
    md = base_w(digest, p.len1, p.log_w)
    checksum = sum(p.w - 1 - d for d in md)
    cd = base_w(checksum.to_bytes(N, "big"), p.len2, p.log_w)
    digits = md + cd
    for i in range(p.len):
        if chain(sig[i], digits[i], p.w - 1 - digits[i]) != pk[i]:
            return False
    return True


# ---- Merkle tree wrapper (generic) ----
def build_tree(leaf_hashes: list[bytes]) -> bytes:
    layer = leaf_hashes[:]
    while len(layer) > 1:
        layer = [H(b"MSS-NODE" + layer[i] + layer[i+1])
                 for i in range(0, len(layer), 2)]
    return layer[0]


def auth_path(leaf_hashes: list[bytes], idx: int) -> list[bytes]:
    path, layer, cur = [], leaf_hashes[:], idx
    while len(layer) > 1:
        path.append(layer[cur ^ 1])
        layer = [H(b"MSS-NODE" + layer[i] + layer[i+1])
                 for i in range(0, len(layer), 2)]
        cur //= 2
    return path


def leaf_hash(pk: list[bytes]) -> bytes:
    return H(b"MSS-LEAF" + b"".join(pk))


def benchmark(p: WOTSParams, height: int = 4, reps: int = 10):
    msg = b"JCE extended benchmark message"
    n = 2 ** height

    # Keygen
    kg_times = []
    for _ in range(reps):
        t0 = time.perf_counter()
        keys = [wots_keygen(p) for _ in range(n)]
        kgs = [k[0] for k in keys]
        pks = [k[1] for k in keys]
        leaves = [leaf_hash(pk) for pk in pks]
        root = build_tree(leaves)
        kg_times.append((time.perf_counter() - t0) * 1000)

    # Sign (use leaf 0)
    sign_times = []
    sig = None
    for _ in range(reps):
        t0 = time.perf_counter()
        sig = wots_sign(kgs[0], msg, p)
        path = auth_path(leaves, 0)
        sign_times.append((time.perf_counter() - t0) * 1000)

    # Verify
    verify_times = []
    for _ in range(reps):
        t0 = time.perf_counter()
        ok = wots_verify(msg, sig, pks[0], p)
        # walk path
        cur = leaves[0]
        idx = 0
        for sib in path:
            cur = H(b"MSS-NODE" + (cur if idx & 1 == 0 else sib)
                    + (sib if idx & 1 == 0 else cur))
            idx //= 2
        assert ok and cur == root
        verify_times.append((time.perf_counter() - t0) * 1000)

    return {
        "w": p.w,
        "log_w": p.log_w,
        "len1": p.len1,
        "len2": p.len2,
        "len": p.len,
        "n_signatures": n,
        "sig_bytes": p.len * N + height * N,  # WOTS sig + auth path
        "pk_bytes": 32,  # merkle root
        "sk_memory_kb": p.len * N * n / 1024,  # total secret memory
        "keygen_ms_mean": round(statistics.mean(kg_times), 2),
        "keygen_ms_std": round(statistics.stdev(kg_times), 2),
        "sign_ms_mean": round(statistics.mean(sign_times), 3),
        "sign_ms_std": round(statistics.stdev(sign_times), 3),
        "verify_ms_mean": round(statistics.mean(verify_times), 3),
        "verify_ms_std": round(statistics.stdev(verify_times), 3),
        "avg_chain_iters": p.len * (p.w - 1) / 2,  # expected hash ops per sign
    }


def main():
    print(f"{'w':>5} {'len':>4} {'sig(B)':>8} {'keygen(ms)':>14} "
          f"{'sign(ms)':>14} {'verify(ms)':>14} {'chain_ops':>10}")
    rows = []
    for w in (4, 16, 256):
        p = WOTSParams.for_w(w)
        r = benchmark(p)
        rows.append(r)
        print(f"{r['w']:>5} {r['len']:>4} {r['sig_bytes']:>8} "
              f"{r['keygen_ms_mean']:>7.2f}±{r['keygen_ms_std']:<5.2f} "
              f"{r['sign_ms_mean']:>6.3f}±{r['sign_ms_std']:<5.3f} "
              f"{r['verify_ms_mean']:>6.3f}±{r['verify_ms_std']:<5.3f} "
              f"{r['avg_chain_iters']:>10.0f}")

    (OUT / "results_jce.json").write_text(json.dumps(rows, indent=2))
    print(f"\n[written] {OUT/'results_jce.json'}")


if __name__ == "__main__":
    main()
