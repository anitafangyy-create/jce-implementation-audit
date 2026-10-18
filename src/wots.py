"""
WOTS+ (Winternitz One-Time Signature, improved)
================================================

Implements the WOTS+ one-time signature scheme in the style of SPHINCS+
(FIPS 205). This replaces the naive Lamport OTS: instead of one secret
per message bit, WOTS+ encodes the message digest as base-w digits and
pays off hash chains. A checksum prevents existential forgery.

Parameters (matching SPHINCS+'s W=16 parameter set):
    n     = 32 bytes (SHA-256 output)
    w     = 16       (one digit per 4 bits)
    log_w = 4
    len1  = ceil(8n / log_w) = 64
    len2  = floor(log2(len1*(w-1))/log_w) + 1 = 3
    len   = len1 + len2 = 67

Reference:
    * SPHINCS+ specification (FIPS 205), Algorithm 5 (wots_Wots_PK),
      Algorithm 6 (wots_sign), Algorithm 7 (wots_pkFromSig).
    * https://github.com/sphincs/sphincsplus

Security: existential unforgeability under chosen-message attacks in the
random oracle model, assuming the hash is second-preimage resistant.
"""

from __future__ import annotations

import os
import math
import dataclasses
from hbs_signature import H, H_message, HASH_LEN


# ---------------------------------------------------------------------------
# Parameters
# ---------------------------------------------------------------------------
N = 32           # hash output bytes
W = 16           # Winternitz base
LOG_W = 4        # log2(W)
LEN1 = (8 * N + (LOG_W - 1)) // LOG_W          # = 64
LEN2 = math.floor(math.log2(LEN1 * (W - 1)) / LOG_W) + 1  # = 3
LEN = LEN1 + LEN2                              # = 67


def base_w(data: bytes, out_len: int) -> list[int]:
    """Convert a byte string to a list of base-W digits (each 0..W-1).

    Uses LOG_W bits per digit (LSB-first within each byte)."""
    digits = []
    in_pos = 0
    in_bits = 0
    total = 0
    for _ in range(out_len):
        while in_bits < LOG_W:
            total = (total << 8) | data[in_pos]
            in_pos += 1
            in_bits += 8
        in_bits -= LOG_W
        digits.append((total >> in_bits) & (W - 1))
        total &= (1 << in_bits) - 1
    return digits


def chain(x: bytes, start: int, steps: int) -> bytes:
    """Apply the hash function `steps` times, starting from offset `start`.

    In production WOTS+ this uses a keyed hash F with address input;
    here we use plain SHA-256 (prototype, no multi-target security claims)."""
    assert len(x) == N
    for _ in range(start, start + steps):
        x = H(b"WOTS-CHAIN" + x)
    return x


# ---------------------------------------------------------------------------
# WOTS+ key pair, sign, verify
# ---------------------------------------------------------------------------

@dataclasses.dataclass
class WOTSKeyPair:
    sk: list[bytes]   # LEN secrets, each N bytes
    pk: list[bytes]  # LEN public chain ends, each N bytes

    @staticmethod
    def generate() -> "WOTSKeyPair":
        sk = [os.urandom(N) for _ in range(LEN)]
        pk = [chain(sk[i], 0, W - 1) for i in range(LEN)]
        return WOTSKeyPair(sk=sk, pk=pk)

    def sign(self, msg: bytes) -> list[bytes]:
        digest = H_message(msg)
        msg_digits = base_w(digest, LEN1)
        checksum = sum(W - 1 - d for d in msg_digits)
        checksum_digits = base_w(checksum.to_bytes(N, "big"), LEN2)
        digits = msg_digits + checksum_digits
        assert len(digits) == LEN
        return [chain(self.sk[i], 0, digits[i]) for i in range(LEN)]

    @staticmethod
    def verify(msg: bytes, sig: list[bytes], pk: list[bytes]) -> bool:
        if len(sig) != LEN or len(pk) != LEN:
            return False
        digest = H_message(msg)
        msg_digits = base_w(digest, LEN1)
        checksum = sum(W - 1 - d for d in msg_digits)
        checksum_digits = base_w(checksum.to_bytes(N, "big"), LEN2)
        digits = msg_digits + checksum_digits
        for i in range(LEN):
            recomputed = chain(sig[i], digits[i], W - 1 - digits[i])
            if recomputed != pk[i]:
                return False
        return True

    @staticmethod
    def pk_bytes() -> int:
        return LEN * N   # 67 * 32 = 2144

    @staticmethod
    def sig_bytes() -> int:
        return LEN * N   # 2144


# ---------------------------------------------------------------------------
# Self-test
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    print("=== WOTS+ self-test ===")
    print(f"Parameters: N={N}, W={W}, LEN1={LEN1}, LEN2={LEN2}, LEN={LEN}")
    print(f"Key size:  sk={LEN*N} B, pk={LEN*N} B, sig={LEN*N} B")

    kp = WOTSKeyPair.generate()
    msg = b"WOTS+ post-quantum signature self-test"
    sig = kp.sign(msg)
    assert WOTSKeyPair.verify(msg, sig, kp.pk), "WOTS+ verify failed"
    print("[ok] round-trip")

    # tamper
    bad = list(sig)
    bad[0] = bytes([bad[0][0] ^ 1]) + bad[0][1:]
    assert not WOTSKeyPair.verify(msg, bad, kp.pk), "forged signature accepted"
    print("[ok] tamper detection")

    # wrong message
    assert not WOTSKeyPair.verify(b"wrong", sig, kp.pk), \
        "wrong message accepted"
    print("[ok] wrong-message rejection")

    # sanity on base_w
    digits = base_w(b"\xff\x00", 4)
    assert digits == [15, 15, 0, 0], f"base_w got {digits}"
    print("[ok] base_w sanity: \\xff\\x00 ->", digits)

    print("=== WOTS+ self-test passed ===")
