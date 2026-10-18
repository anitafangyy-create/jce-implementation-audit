"""
BIP-0360 (Pay-to-Merkle-Root) end-to-end integration prototype.

Simulates the full lifecycle:
  1. Build a WOTS+ Merkle tree (the script tree).
  2. Construct the P2MR scriptPubKey: OP_2 <32-byte Merkle root>.
  3. Spend via a WOTS+ leaf script: witness = [wots_sig elements]
     + [leaf script] + [control block].
  4. Verify as a simulated miner would: recompute the root from the
     leaf hash + auth path, then run the WOTS+ verification gate.

Honest caveat: On-chain Bitcoin Script cannot verify WOTS+ today
(~200-4000 SHA-256 iterations per verification). BIP-0360 reserves the
OP_SUCCESSx upgrade path precisely so that a future soft-fork can introduce
a native OP_WOTS_VERIFY opcode. This prototype simulates that future state.
"""
from __future__ import annotations

import os
import json
import dataclasses
from pathlib import Path

import sys as _sys
_sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from hbs_signature import H, H_message
from wots import WOTSKeyPair, LEN, N

OUT = Path(__file__).resolve().parents[1]


# ---------------------------------------------------------------------------
# BIP-0360 output structure
# ---------------------------------------------------------------------------

def p2mr_script_pubkey(root: bytes) -> bytes:
    """P2MR scriptPubKey: OP_2 (SegWit v2) + 32-byte witness program."""
    assert len(root) == 32
    return bytes([0x52, 0x20]) + root  # OP_2, OP_PUSHBYTES_32


def p2mr_address(root: bytes) -> str:
    """Bech32m mainnet address, bc1z prefix (SegWit v2)."""
    # We do not implement full bech32m here; this is a representative string.
    import hashlib
    h = hashlib.sha256(root).hexdigest()
    return f"bc1z{h[:38]}"


# ---------------------------------------------------------------------------
# Simulated leaf scripts
# ---------------------------------------------------------------------------

@dataclasses.dataclass
class Secp256k1Leaf:
    """The current BIP-0360 leaf: OP_CHECKSIG on a pubkey.
    This is what ships today; the WOTS+ leaf is the future upgrade."""
    pubkey: bytes  # 32-byte x-only pubkey (simulated)

    def script_bytes(self) -> int:
        # OP_PUSHBYTES_32 <pubkey> OP_CHECKSIG
        return 1 + 32 + 1

    def witness_size_spend(self, has_sig: bool = True) -> int:
        # count(1) + sig(65) + leaf script(34) + control block(33, depth-1)
        return 1 + (65 if has_sig else 0) + self.script_bytes() + 33


@dataclasses.dataclass
class WOTSLeaf:
    """A future P2MR leaf that verifies a WOTS+ signature.

    In a future soft-fork this would be a new opcode (e.g. OP_WOTS_VERIFY)
    parametrized by the WOTS+ public key. We model the on-chain footprint:
      - the leaf script occupies a small constant (opcode + params);
      - the witness must carry the WOTS+ signature and public key.
    """
    wots_pk: list[bytes]
    w: int

    def script_bytes(self) -> int:
        # Future OP_WOTS_VERIFY leaf: opcode + parameter byte (w) + length.
        return 1 + 1 + 1

    def witness_size_spend(self, wots_sig: list[bytes], depth: int) -> int:
        # count(1) + wots_sig(L*n) + wots_pk(L*n) + leaf script(3)
        # + control block(1 + 32*depth)
        control = 1 + 32 * depth
        return (1
                + sum(len(x) for x in wots_sig)
                + sum(len(x) for x in self.wots_pk)
                + self.script_bytes()
                + control)


# ---------------------------------------------------------------------------
# End-to-end spend simulation
# ---------------------------------------------------------------------------

def leaf_hash(pk: list[bytes]) -> bytes:
    return H(b"MSS-LEAF" + b"".join(pk))


def build_tree(leaves: list[bytes]):
    layer = leaves[:]
    while len(layer) > 1:
        layer = [H(b"MSS-NODE" + layer[i] + layer[i+1])
                 for i in range(0, len(layer), 2)]
    return layer[0]


def auth_path(leaves: list[bytes], idx: int) -> list[bytes]:
    path, layer, cur = [], leaves[:], idx
    while len(layer) > 1:
        path.append(layer[cur ^ 1])
        layer = [H(b"MSS-NODE" + layer[i] + layer[i+1])
                 for i in range(0, len(layer), 2)]
        cur //= 2
    return path


def e2e_demo():
    print("=" * 64)
    print("BIP-0360 P2MR + WOTS+ end-to-end integration demo")
    print("=" * 64)

    # Build a depth-1 tree: 2 leaves (simulating a 2-leaf script tree).
    kp1 = WOTSKeyPair.generate()
    kp2 = WOTSKeyPair.generate()
    leaves = [leaf_hash(kp1.pk), leaf_hash(kp2.pk)]
    root = build_tree(leaves)

    # 1. P2MR output
    spk = p2mr_script_pubkey(root)
    addr = p2mr_address(root)
    print(f"\n[1] P2MR scriptPubKey ({len(spk)} B): {spk.hex()}")
    print(f"    P2MR address: {addr}")

    # 2. Spend leaf 0 with a WOTS+ signature
    msg = b"Spend P2MR UTXO via WOTS+ leaf, block 900000"
    sig = kp1.sign(msg)
    path = auth_path(leaves, 0)

    # 3. Simulated miner verification
    #    (a) recompute leaf from pk, walk path to root, compare
    recomputed_leaf = leaf_hash(kp1.pk)
    cur, idx = recomputed_leaf, 0
    for sib in path:
        cur = H(b"MSS-NODE" + (cur if idx & 1 == 0 else sib)
                + (sib if idx & 1 == 0 else cur))
        idx //= 2
    root_ok = (cur == root)
    #    (b) run WOTS+ verify gate
    wots_ok = WOTSKeyPair.verify(msg, sig, kp1.pk)
    print(f"\n[2] Spend via WOTS+ leaf 0")
    print(f"    Root recomputation OK: {root_ok}")
    print(f"    WOTS+ signature valid: {wots_ok}")
    assert root_ok and wots_ok

    # 4. Witness size comparison
    print(f"\n[3] Witness size comparison (depth-1 tree, i.e. 2 leaves)")
    secp = Secp256k1Leaf(pubkey=b"\x00" * 32)
    wots_leaf = WOTSLeaf(wots_pk=kp1.pk, w=16)
    secp_witness = secp.witness_size_spend()
    wots_witness = wots_leaf.witness_size_spend(sig, depth=1)
    print(f"    P2TR key-path spend (baseline):       66 B")
    print(f"    P2MR with secp256k1 leaf (today):   {secp_witness} B")
    print(f"    P2MR with WOTS+ leaf (future):      {wots_witness} B")

    # 5. What does it cost on-chain? BIP-0360 uses witness (1 weight unit per
    #    byte vs 4 weight units for scriptSig). Rough fee comparison at 1 sat/vB:
    print(f"\n[4] Approximate on-chain weight (1 WU = 1/4 vByte)")
    print(f"    secp256k1 leaf witness weight: {secp_witness * 1} WU "
          f"({secp_witness/4:.1f} vBytes)")
    print(f"    WOTS+ leaf witness weight:    {wots_witness * 1} WU "
          f"({wots_witness/4:.1f} vBytes)")

    return {
        "script_pubkey_hex": spk.hex(),
        "address": addr,
        "root_recomputed": root_ok,
        "wots_signature_valid": wots_ok,
        "secp256k1_leaf_witness_bytes": secp_witness,
        "wots_leaf_witness_bytes": wots_witness,
        "p2tr_keypath_witness_bytes": 66,
    }


if __name__ == "__main__":
    result = e2e_demo()
    (OUT / "experiments" / "bip360_demo.json").write_text(json.dumps(result, indent=2))
    print(f"\n[written] {OUT/'experiments'/'bip360_demo.json'}")
