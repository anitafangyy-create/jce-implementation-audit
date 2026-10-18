"""
Comparative benchmark: Lamport-OBS-based MSS vs WOTS+-based MSS.

Builds a generic Merkle signature scheme where the OTS layer can be
swapped. Measures keygen / sign / verify latency and on-the-wire sizes
for both choices across tree heights.
"""

from __future__ import annotations

import time
import statistics
import dataclasses
import json
from pathlib import Path

import sys as _sys
_sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from hbs_signature import H, LamportKeyPair
from wots import WOTSKeyPair

OUT = Path(__file__).resolve().parents[1]
MSG = b"Lamport vs WOTS+ comparative benchmark"


# ---------------------------------------------------------------------------
# Generic Merkle signature scheme (pluggable OTS)
# ---------------------------------------------------------------------------

@dataclasses.dataclass
class GenericSignature:
    ots_sig: list
    ots_pk: object
    auth_path: list[bytes]
    leaf_index: int


def _hash_leaf(pk: object, kind: str) -> bytes:
    if kind == "lamport":
        flat = b"".join(pk[0]) + b"".join(pk[1])
    else:  # wots
        flat = b"".join(pk)
    return H(b"MSS-LEAF-" + kind.encode() + flat)


class GenericMSS:
    def __init__(self, height: int, kind: str):
        assert kind in ("lamport", "wots")
        self.kind = kind
        self.height = height
        self.n = 2 ** height
        self.ots_keys = []
        for _ in range(self.n):
            if kind == "lamport":
                self.ots_keys.append(LamportKeyPair.generate())
            else:
                self.ots_keys.append(WOTSKeyPair.generate())
        self.leaf_hashes = [_hash_leaf(kp.pk, kind) for kp in self.ots_keys]
        self.root = self._build_tree()

    def _build_tree(self) -> bytes:
        layer = self.leaf_hashes[:]
        for _ in range(self.height):
            layer = [H(b"MSS-NODE" + layer[i] + layer[i + 1])
                     for i in range(0, len(layer), 2)]
        return layer[0]

    def _auth_path(self, idx: int) -> list[bytes]:
        path, layer, cur = [], self.leaf_hashes[:], idx
        for _ in range(self.height):
            path.append(layer[cur ^ 1])
            layer = [H(b"MSS-NODE" + layer[i] + layer[i + 1])
                     for i in range(0, len(layer), 2)]
            cur //= 2
        return path

    def sign(self, msg: bytes, idx: int) -> GenericSignature:
        kp = self.ots_keys[idx]
        return GenericSignature(
            ots_sig=kp.sign(msg),
            ots_pk=kp.pk,
            auth_path=self._auth_path(idx),
            leaf_index=idx,
        )

    def verify(self, msg: bytes, sig: GenericSignature) -> bool:
        kp_cls = LamportKeyPair if self.kind == "lamport" else WOTSKeyPair
        if not kp_cls.verify(msg, sig.ots_sig, sig.ots_pk):
            return False
        cur = _hash_leaf(sig.ots_pk, self.kind)
        idx = sig.leaf_index
        for sibling in sig.auth_path:
            cur = H(b"MSS-NODE" + (cur if idx & 1 == 0 else sibling)
                    + (sibling if idx & 1 == 0 else cur))
            idx //= 2
        return cur == self.root

    # -- size helpers --
    def signature_bytes(self) -> int:
        if self.kind == "lamport":
            ots_sig = LamportKeyPair.sig_size_bytes()
            ots_pk = LamportKeyPair.pk_size_bytes()
        else:
            ots_sig = WOTSKeyPair.sig_bytes()
            ots_pk = WOTSKeyPair.pk_bytes()
        return ots_sig + ots_pk + self.height * 32


# ---------------------------------------------------------------------------
# Benchmark
# ---------------------------------------------------------------------------

def bench(kind: str, height: int, repeats: int = 3):
    kg = []
    for _ in range(repeats):
        t0 = time.perf_counter()
        mss = GenericMSS(height, kind)
        kg.append(time.perf_counter() - t0)
    sign_sig = mss.sign(MSG, 0)
    t0 = time.perf_counter()
    for _ in range(repeats):
        mss.sign(MSG, 0)
    sign_t = (time.perf_counter() - t0) / repeats
    t0 = time.perf_counter()
    for _ in range(repeats):
        assert mss.verify(MSG, sign_sig)
    verify_t = (time.perf_counter() - t0) / repeats
    return {
        "kind": kind,
        "height": height,
        "n_signatures": 2 ** height,
        "key_gen_ms": round(statistics.median(kg) * 1000, 2),
        "sign_ms": round(sign_t * 1000, 3),
        "verify_ms": round(verify_t * 1000, 3),
        "signature_bytes": mss.signature_bytes(),
        "pubkey_bytes": 32,
    }


def main():
    print(f"{'kind':<8} {'h':>2} {'N':>5} {'keygen(ms)':>11} "
          f"{'sign(ms)':>9} {'verify(ms)':>11} {'sig(B)':>8}")
    rows = []
    for kind in ("lamport", "wots"):
        for h in range(1, 8):
            r = bench(kind, h)
            rows.append(r)
            print(f"{kind:<8} {h:>2} {r['n_signatures']:>5} "
                  f"{r['key_gen_ms']:>11.2f} {r['sign_ms']:>9.3f} "
                  f"{r['verify_ms']:>11.3f} {r['signature_bytes']:>8}")

    (OUT / "experiments" / "results_v2.json").write_text(json.dumps(rows, indent=2))
    print(f"\n[written] {OUT/'experiments'/'results_v2.json'}")


if __name__ == "__main__":
    main()
