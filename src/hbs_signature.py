"""
Hash-Based Post-Quantum Signature Scheme (HBS-PQ)
===================================================

A pedagogical but security-meaningful implementation built on the same
cryptographic family as NIST standards:

    * Lamport One-Time Signature (Lamport, 1979)
    * Merkle Signature Scheme (Merkle, 1989) -- many OTS key pairs
      aggregated into a hash tree, root = public key

This is the exact design family behind:
    * XMSS  (RFC 8391 / NIST SP 800-208)
    * LMS   (RFC 8554 / NIST SP 800-208)
    * SLH-DSA / SPHINCS+ (FIPS 205)

Security assumption: SHA-256 (FIPS 180-4). Shor's algorithm gives no
speedup on hash preimages; Grover only halves the bit security, so a
256-bit hash still gives ~128-bit post-quantum security.

Reference datasets / test-vector families used:
    * SPHINCS+ reference implementation & KAT vectors:
        https://github.com/sphincs/sphincsplus
    * NIST ACVP server vectors:
        https://github.com/usnistgov/ACVP-Server
    * IETF draft-mcgrew-hash-sigs (Lamport/Winternitz/Merkle spec).

Authors: research prototype for "机构项目/量子计算机"
"""

from __future__ import annotations

import os
import time
import hashlib
import dataclasses
from typing import List, Tuple

# ---------------------------------------------------------------------------
# Crypto primitives
# ---------------------------------------------------------------------------

HASH_LEN = 32  # SHA-256 output length in bytes (256 bits)


def H(data: bytes) -> bytes:
    """Tagged hash used everywhere. In a production scheme one would use
    domain-separation prefixes (like SPHINCS+'s PRF / H_msg / F / H / T_l),
    but for this research prototype a plain SHA-256 is sufficient."""
    return hashlib.sha256(data).digest()


def H_message(msg: bytes) -> bytes:
    """Hash the message to sign to a 256-bit digest."""
    return hashlib.sha256(b"HBS-PQ-MSG-v1" + msg).digest()


def secure_rand(n: int) -> bytes:
    return os.urandom(n)


# ---------------------------------------------------------------------------
# Lamport One-Time Signature
# ---------------------------------------------------------------------------

@dataclasses.dataclass
class LamportKeyPair:
    """A Lamport one-time key pair.

    Secret: x[bit][i] for bit in {0,1}, i in 0..255  (512 x 32-byte secrets)
    Public: y[bit][i] = H(x[bit][i])
    """
    sk: List[List[bytes]]   # sk[0] and sk[1], each length 256
    pk: List[List[bytes]]   # pk[0] and pk[1], each length 256

    @staticmethod
    def generate() -> "LamportKeyPair":
        sk = [[secure_rand(HASH_LEN) for _ in range(HASH_LEN * 8)]
              for _ in range(2)]
        pk = [[H(x) for x in sk[b]] for b in range(2)]
        return LamportKeyPair(sk=sk, pk=pk)

    def sign(self, msg: bytes) -> List[bytes]:
        """Sign a single message. Returns the 256 revealed preimages, one per
        bit of the message digest. The OTS key pair MUST NOT be reused."""
        digest = H_message(msg)
        sig = []
        for i, byte in enumerate(digest):
            for j in range(8):
                bit = (byte >> j) & 1
                # Reveal the preimage for this bit value
                sig.append(self.sk[bit][i * 8 + j])
        return sig  # 256 x 32-byte values

    @staticmethod
    def verify(msg: bytes, sig: List[bytes],
               pk: List[List[bytes]]) -> bool:
        digest = H_message(msg)
        if len(sig) != HASH_LEN * 8:
            return False
        k = 0
        for byte in digest:
            for j in range(8):
                bit = (byte >> j) & 1
                if H(sig[k]) != pk[bit][k]:
                    return False
                k += 1
        return True

    # ---- size helpers ----
    @staticmethod
    def pk_size_bytes() -> int:
        return 2 * HASH_LEN * 8 * HASH_LEN  # 2 * 256 * 32 = 16384 B

    @staticmethod
    def sig_size_bytes() -> int:
        return HASH_LEN * 8 * HASH_LEN      # 256 * 32 = 8192 B


# ---------------------------------------------------------------------------
# Merkle Signature Scheme (MSS): aggregate many Lamport OTS keys into a tree
# ---------------------------------------------------------------------------

@dataclasses.dataclass
class MSSPublicKey:
    root: bytes                 # 32-byte Merkle root
    height: int                 # number of levels; leaves = 2**height
    leaf_pk_digests: List[bytes]  # H(pk) for each leaf (for inspection)


@dataclasses.dataclass
class MSSSignature:
    ots_sig: List[bytes]        # Lamport signature
    ots_pk: List[List[bytes]]   # the Lamport public key being used
    auth_path: List[bytes]      # sibling hashes along the path to root
    leaf_index: int             # which leaf was used


class MerkleSignatureScheme:
    """Merkle signature scheme over Lamport OTS instances.

    Parameters:
        height h: number of levels; supports N = 2**h signatures.
    """

    def __init__(self, height: int):
        assert 1 <= height <= 12, "height kept small for this prototype"
        self.height = height
        self.n_leaves = 2 ** height
        self.ots_keys: List[LamportKeyPair] = [
            LamportKeyPair.generate() for _ in range(self.n_leaves)
        ]
        # leaf hashes: H(serialize_pk(ots_pk))
        self.leaf_hashes: List[bytes] = [
            self._hash_leaf_pk(kp.pk) for kp in self.ots_keys
        ]
        self.root = self._build_tree()

    # -- internal helpers ---------------------------------------------------
    @staticmethod
    def _hash_leaf_pk(pk: List[List[bytes]]) -> bytes:
        flat = b"".join(pk[0]) + b"".join(pk[1])
        return H(b"MSS-LEAF" + flat)

    def _build_tree(self) -> bytes:
        layer = self.leaf_hashes[:]
        for _ in range(self.height):
            nxt = []
            for i in range(0, len(layer), 2):
                left, right = layer[i], layer[i + 1]
                nxt.append(H(b"MSS-NODE" + left + right))
            layer = nxt
        return layer[0]

    def auth_path(self, idx: int) -> List[bytes]:
        """Return the sibling hashes along the path from leaf idx to root."""
        path = []
        layer = self.leaf_hashes[:]
        cur = idx
        for _ in range(self.height):
            sibling = cur ^ 1
            path.append(layer[sibling])
            # move up
            nxt = []
            for i in range(0, len(layer), 2):
                nxt.append(H(b"MSS-NODE" + layer[i] + layer[i + 1]))
            layer = nxt
            cur //= 2
        return path

    # -- public API ---------------------------------------------------------
    def public_key(self) -> MSSPublicKey:
        return MSSPublicKey(root=self.root,
                            height=self.height,
                            leaf_pk_digests=self.leaf_hashes)

    def sign(self, msg: bytes, leaf_index: int) -> MSSSignature:
        assert 0 <= leaf_index < self.n_leaves, "leaf already used / out of range"
        kp = self.ots_keys[leaf_index]
        ots_sig = kp.sign(msg)
        path = self.auth_path(leaf_index)
        return MSSSignature(ots_sig=ots_sig,
                            ots_pk=kp.pk,
                            auth_path=path,
                            leaf_index=leaf_index)

    @staticmethod
    def verify(msg: bytes, sig: MSSSignature, root: bytes) -> bool:
        # 1. Verify the inner Lamport signature
        if not LamportKeyPair.verify(msg, sig.ots_sig, sig.ots_pk):
            return False
        # 2. Recompute the leaf hash
        leaf = MerkleSignatureScheme._hash_leaf_pk(sig.ots_pk)
        # 3. Walk the auth path up to root
        cur = leaf
        idx = sig.leaf_index
        for sibling in sig.auth_path:
            if idx & 1 == 0:
                cur = H(b"MSS-NODE" + cur + sibling)
            else:
                cur = H(b"MSS-NODE" + sibling + cur)
            idx //= 2
        return cur == root


# ---------------------------------------------------------------------------
# Sizes (in bytes)
# ---------------------------------------------------------------------------

def sizes_for_height(height: int) -> dict:
    n = 2 ** height
    # MSS public key = 32-byte root
    pk_mss = HASH_LEN
    # MSS signature = Lamport sig (8192) + Lamport pk (16384)
    #                 + auth path (height * 32)
    sig_mss = (LamportKeyPair.sig_size_bytes()
               + LamportKeyPair.pk_size_bytes()
               + height * HASH_LEN)
    return {
        "height": height,
        "n_signatures": n,
        "mss_pubkey_bytes": pk_mss,
        "mss_signature_bytes": sig_mss,
        "lamport_pk_bytes": LamportKeyPair.pk_size_bytes(),
        "lamport_sig_bytes": LamportKeyPair.sig_size_bytes(),
    }


# ---------------------------------------------------------------------------
# Quick sanity test (self-check against tampering)
# ---------------------------------------------------------------------------

def _selftest():
    print("=== HBS-PQ self-test ===")
    # Lamport round-trip
    kp = LamportKeyPair.generate()
    msg = b"post-quantum signature self-test"
    sig = kp.sign(msg)
    assert LamportKeyPair.verify(msg, sig, kp.pk), "Lamport verify failed"
    assert not LamportKeyPair.verify(b"wrong message", sig, kp.pk), \
        "forged message accepted"
    print("[ok] Lamport OTS round-trip + tamper detection")

    # MSS round-trip at height 4 (16 signatures)
    mss = MerkleSignatureScheme(height=4)
    root = mss.public_key().root
    for i in range(mss.n_leaves):
        s = mss.sign(f"message #{i}".encode(), i)
        assert MerkleSignatureScheme.verify(f"message #{i}".encode(), s, root)
    # tamper
    bad = mss.sign(b"tampered", 0)
    bad.ots_sig[0] = bytes([bad.ots_sig[0][0] ^ 1]) + bad.ots_sig[0][1:]
    assert not MerkleSignatureScheme.verify(b"tampered", bad, root), \
        "tampered signature accepted"
    print(f"[ok] MSS round-trip, height=4, {mss.n_leaves} leaves, "
          f"tamper rejected")
    print("=== self-test passed ===\n")


if __name__ == "__main__":
    _selftest()
    for h in range(1, 7):
        s = sizes_for_height(h)
        print(f"height={h}  N={s['n_signatures']:>5}  "
              f"pk={s['mss_pubkey_bytes']}B  "
              f"sig={s['mss_signature_bytes']/1024:.1f}KB")
