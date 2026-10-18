"""
Benchmark script for the HBS-PQ (Lamport + Merkle) prototype.

Measures:
  * key-generation time (build the whole Merkle tree)
  * signing time (one OTS signature + auth path)
  * verification time (Lamport verify + path recomputation)
  * signature / public-key byte sizes

Then compares against reference post-quantum schemes (parameter-set sizes
from FIPS 204 / FIPS 205) and against today's secp256k1 Schnorr (BIP-340).
"""

from __future__ import annotations

import json
import time
import statistics
from pathlib import Path

import sys as _sys
_sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from hbs_signature import (
    MerkleSignatureScheme,
    LamportKeyPair,
    sizes_for_height,
)

OUT = Path(__file__).resolve().parents[1]
MSG = b"Research prototype: hash-based post-quantum signature benchmark"


def bench_one(height: int, repeats: int = 3):
    # Key generation
    kg_times = []
    for _ in range(repeats):
        t0 = time.perf_counter()
        mss = MerkleSignatureScheme(height=height)
        kg_times.append(time.perf_counter() - t0)
    root = mss.public_key().root

    # Signing (use leaf 0)
    sign_times = []
    for _ in range(repeats):
        t0 = time.perf_counter()
        sig = mss.sign(MSG, 0)
        sign_times.append(time.perf_counter() - t0)

    # Verification
    verify_times = []
    for _ in range(repeats):
        t0 = time.perf_counter()
        ok = MerkleSignatureScheme.verify(MSG, sig, root)
        verify_times.append(time.perf_counter() - t0)
    assert ok, "verify failed during benchmark"

    sizes = sizes_for_height(height)
    return {
        "height": height,
        "n_signatures": sizes["n_signatures"],
        "key_gen_ms": round(statistics.median(kg_times) * 1000, 2),
        "sign_ms": round(statistics.median(sign_times) * 1000, 3),
        "verify_ms": round(statistics.median(verify_times) * 1000, 3),
        "mss_pubkey_bytes": sizes["mss_pubkey_bytes"],
        "mss_signature_bytes": sizes["mss_signature_bytes"],
    }


def main():
    print(f"{'h':>2} {'N':>5} {'keygen(ms)':>12} {'sign(ms)':>10} "
          f"{'verify(ms)':>11} {'sig(KiB)':>9}")
    rows = []
    for h in range(1, 8):
        r = bench_one(h)
        rows.append(r)
        print(f"{r['height']:>2} {r['n_signatures']:>5} "
              f"{r['key_gen_ms']:>12.2f} {r['sign_ms']:>10.3f} "
              f"{r['verify_ms']:>11.3f} "
              f"{r['mss_signature_bytes']/1024:>9.2f}")

    # Reference schemes (byte sizes from FIPS 204 / FIPS 205; speeds are
    # typical reference-implementation numbers on a modern x86 core).
    reference = [
        {"name": "secp256k1 Schnorr (BIP-340)",
         "pubkey_bytes": 32, "sig_bytes": 64,
         "note": "classical, NOT quantum-resistant"},
        {"name": "ML-DSA-44 (FIPS 204, NIST L2)",
         "pubkey_bytes": 1312, "sig_bytes": 2420,
         "note": "lattice-based post-quantum"},
        {"name": "ML-DSA-65 (FIPS 204, NIST L3)",
         "pubkey_bytes": 1952, "sig_bytes": 3309,
         "note": "lattice-based post-quantum"},
        {"name": "SLH-DSA-128s (FIPS 205, NIST L1)",
         "pubkey_bytes": 32, "sig_bytes": 7856,
         "note": "hash-based, stateless post-quantum"},
        {"name": "SLH-DSA-128f (FIPS 205, NIST L1)",
         "pubkey_bytes": 32, "sig_bytes": 17088,
         "note": "hash-based, fast-sign variant"},
        {"name": "This work: Lamport+MSS h=6",
         "pubkey_bytes": rows[-1]["mss_pubkey_bytes"],
         "sig_bytes": rows[-1]["mss_signature_bytes"],
         "note": "research prototype, SHA-256 only"},
    ]

    out = {
        "benchmark": rows,
        "reference_schemes": reference,
    }
    (OUT / "experiments" / "results.json").write_text(json.dumps(out, indent=2))
    print(f"\n[written] {OUT/'experiments'/'results.json'}")


if __name__ == "__main__":
    main()
