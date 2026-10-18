"""
Generate deterministic known-answer test (KAT) vectors for WOTS+.

Uses a fixed RNG seed so that anyone can reproduce the exact bytes in
the paper appendix. This is a self-contained KAT: it does not require
the SPHINCS+ C reference implementation; it follows FIPS 205 Sec. 4.2
(WOTS+) algorithmically.
"""
import hashlib
import json
import os
from pathlib import Path

import sys as _sys
_sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from wots import WOTSKeyPair, LEN, N

OUT = Path(__file__).resolve().parents[1]

# Deterministic RNG: SHA-256(seed) counter mode
class DRNG:
    def __init__(self, seed: bytes):
        self.state = seed
        self.counter = 0
    def read(self, n: int) -> bytes:
        out = b""
        while len(out) < n:
            self.state = hashlib.sha256(
                self.state + self.counter.to_bytes(4, "big")).digest()
            out += self.state
            self.counter += 1
        return out[:n]


def wots_kat():
    rng = DRNG(b"HBS-PQ-WOTS-KAT-v1-2026")
    # Override os.urandom inside WOTSKeyPair.generate
    import wots as wots_mod
    orig_urandom = wots_mod.os.urandom
    wots_mod.os.urandom = rng.read
    try:
        kp = WOTSKeyPair.generate()
        msg = b"Post-quantum signature KAT vector #0"
        sig = kp.sign(msg)
        # Verify
        assert WOTSKeyPair.verify(msg, sig, kp.pk)
    finally:
        wots_mod.os.urandom = orig_urandom

    return {
        "algorithm": "WOTS+ (n=32, w=16, len=67, SHA-256)",
        "seed": "HBS-PQ-WOTS-KAT-v1-2026",
        "msg_hex": msg.hex(),
        "sk_hex": "".join(x.hex() for x in kp.sk),
        "pk_hex": "".join(x.hex() for x in kp.pk),
        "sig_hex": "".join(x.hex() for x in sig),
        "sk_bytes": LEN * N,
        "pk_bytes": LEN * N,
        "sig_bytes": LEN * N,
    }


if __name__ == "__main__":
    kat = wots_kat()
    (OUT / "experiments" / "kat_wots.json").write_text(json.dumps(kat, indent=2))
    print("=== WOTS+ KAT vector ===")
    for k, v in kat.items():
        if isinstance(v, str) and len(v) > 80:
            print(f"{k}: {v[:80]}... ({len(v)//2} bytes)")
        else:
            print(f"{k}: {v}")
