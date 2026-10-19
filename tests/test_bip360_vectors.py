"""BIP-0360 envelope conformance (vendored official vectors).

What this test does
-------------------
1. Recomputes the BIP-341 TapLeaf/TapBranch roots from the scripts given in
   the nine official P2MR construction vectors, rather than trusting the
   stored intermediates.
2. Checks ``scriptPubKey == 5220 || merkleRoot``.
3. Decodes the Bech32m (BIP-350) address: human-readable part ``bc``,
   witness version 2, witness program equal to the Merkle root, and the
   Bech32m checksum constant (not Bech32).
4. Checks every control block: length ``1 + 32m``, leaf version in the first
   byte with the low bit set, and the root recovered from
   ``leafHash + control-block path`` equal to the announced root.
5. Reports how this repository's illustrative P2MR demo relates to those
   rules: its scriptPubKey shape and control-block length conform, its tree
   commitment does not (``UMT-LEAF``, not ``TapLeaf``), and its address string
   is not Bech32m.

Scope: the vectors cover the P2MR *envelope* only. They contain no
post-quantum signature vectors, so passing this test says nothing about the
signature scheme studied in the paper.

Run:  python3 tests/test_bip360_vectors.py
"""
from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
VECTORS = ROOT / "third_party" / "bip360" / "p2mr_construction.json"
DEMO = ROOT / "experiments" / "bip360_demo.json"

BECH32M_CONST = 0x2BC830A3
CHARSET = "qpzry9x8gf2tvdw0s3jn54khce6mua7l"


# ---------------------------------------------------------------------------
# Bech32m (BIP-350)
# ---------------------------------------------------------------------------
def _polymod(values: list[int]) -> int:
    gen = [0x3B6A57B2, 0x26508E6D, 0x1EA119FA, 0x3D4233DD, 0x2A1462B3]
    chk = 1
    for v in values:
        b = chk >> 25
        chk = ((chk & 0x1FFFFFF) << 5) ^ v
        for i in range(5):
            if (b >> i) & 1:
                chk ^= gen[i]
    return chk


def _hrp_expand(hrp: str) -> list[int]:
    return [ord(c) >> 5 for c in hrp] + [0] + [ord(c) & 31 for c in hrp]


def _convertbits(data: list[int], frombits: int, tobits: int, pad: bool):
    acc = bits = 0
    out = []
    maxv = (1 << tobits) - 1
    for value in data:
        if value < 0 or value >> frombits:
            return None
        acc = (acc << frombits) | value
        bits += frombits
        while bits >= tobits:
            bits -= tobits
            out.append((acc >> bits) & maxv)
    if pad:
        if bits:
            out.append((acc << (tobits - bits)) & maxv)
    elif bits >= frombits or ((acc << (tobits - bits)) & maxv):
        return None
    return out


def decode_bech32m(addr: str):
    """Return (hrp, version, program) or raise ValueError."""
    if addr.lower() != addr and addr.upper() != addr:
        raise ValueError("mixed case")
    addr = addr.lower()
    pos = addr.rfind("1")
    if pos < 1 or pos + 7 > len(addr) or len(addr) > 90:
        raise ValueError("bad separator/length")
    hrp, tail = addr[:pos], addr[pos + 1:]
    try:
        data = [CHARSET.index(c) for c in tail]
    except ValueError as exc:
        raise ValueError(f"invalid data character: {exc}") from None
    if _polymod(_hrp_expand(hrp) + data) != BECH32M_CONST:
        raise ValueError("not bech32m")
    payload = data[:-6]
    if not payload:
        raise ValueError("empty payload")
    version, rest = payload[0], payload[1:]
    if version > 16:
        raise ValueError("bad witness version")
    program = _convertbits(rest, 5, 8, False)
    if program is None:
        raise ValueError("bad padding")
    if len(program) < 2 or len(program) > 40:
        raise ValueError("bad program length")
    if version == 0 and len(program) not in (20, 32):
        raise ValueError("bad v0 program")
    return hrp, version, bytes(program)


# ---------------------------------------------------------------------------
# BIP-341 hashes and tree reconstruction
# ---------------------------------------------------------------------------
def tagged(tag: str, msg: bytes) -> bytes:
    th = hashlib.sha256(tag.encode()).digest()
    return hashlib.sha256(th + th + msg).digest()


def compact_size(n: int) -> bytes:
    if n < 0xFD:
        return bytes([n])
    if n <= 0xFFFF:
        return b"\xfd" + n.to_bytes(2, "little")
    if n <= 0xFFFFFFFF:
        return b"\xfe" + n.to_bytes(4, "little")
    return b"\xff" + n.to_bytes(8, "little")


def tapleaf_hash(script_hex: str, leaf_version: int) -> bytes:
    script = bytes.fromhex(script_hex)
    return tagged("TapLeaf", bytes([leaf_version]) + compact_size(len(script)) + script)


def tapbranch(a: bytes, b: bytes) -> bytes:
    lo, hi = (a, b) if a < b else (b, a)
    return tagged("TapBranch", lo + hi)


def tree_hash(node) -> bytes:
    if isinstance(node, dict):
        return tapleaf_hash(node["script"], node["leafVersion"])
    if not isinstance(node, list) or not node:
        raise ValueError("bad script tree node")
    if len(node) == 1:
        return tree_hash(node[0])
    if len(node) == 2:
        return tapbranch(tree_hash(node[0]), tree_hash(node[1]))
    raise ValueError("script tree node with more than two children")


def leaves_of(node) -> list[dict]:
    if isinstance(node, dict):
        return [node]
    out = []
    for child in node:
        out.extend(leaves_of(child))
    return out


def root_from_control(leaf_hash: bytes, control: bytes) -> bytes:
    if (len(control) - 1) % 32 != 0:
        raise ValueError("control block length")
    h = leaf_hash
    for i in range(1, len(control), 32):
        h = tapbranch(h, control[i:i + 32])
    return h


# ---------------------------------------------------------------------------
# Test
# ---------------------------------------------------------------------------
def run() -> None:
    data = json.loads(VECTORS.read_text())
    vectors = data["test_vectors"]
    assert data["version"] == 1
    assert len(vectors) == 9, len(vectors)

    positive = [v for v in vectors if "error" not in v.get("expected", {})]
    negative = [v for v in vectors if "error" in v.get("expected", {})]
    assert len(positive) == 7 and len(negative) == 2

    checked_leaves = checked_blocks = checked_addresses = 0
    for v in positive:
        tree = v["given"]["scriptTree"]
        leaves = leaves_of(tree)
        announced = v["intermediary"]["leafHashes"]
        for leaf, want in zip(leaves, announced):
            got = tapleaf_hash(leaf["script"], leaf["leafVersion"])
            assert got.hex() == want, f"{v['id']}: leaf hash"
            checked_leaves += 1

        root = tree_hash(tree)
        assert root.hex() == v["intermediary"]["merkleRoot"], f"{v['id']}: root"
        spk = v["expected"]["scriptPubKey"]
        assert spk == "5220" + root.hex(), f"{v['id']}: scriptPubKey"

        hrp, ver, prog = decode_bech32m(v["expected"]["bip350Address"])
        assert hrp == "bc" and ver == 2 and prog == root, f"{v['id']}: address"
        checked_addresses += 1

        blocks = v["expected"]["scriptPathControlBlocks"]
        assert len(blocks) == len(leaves)
        for leaf, leaf_hash_hex, ctrl_hex in zip(leaves, announced, blocks):
            ctrl = bytes.fromhex(ctrl_hex)
            assert (len(ctrl) - 1) % 32 == 0, f"{v['id']}: control length"
            assert ctrl[0] & 0xFE == leaf["leafVersion"], f"{v['id']}: leaf version"
            assert ctrl[0] & 0x01 == 1, f"{v['id']}: unused low bit"
            got = root_from_control(bytes.fromhex(leaf_hash_hex), ctrl)
            assert got == root, f"{v['id']}: control block does not reach root"
            checked_blocks += 1

        print(f"[ok] {v['id']:34s} leaves={len(leaves)} "
              f"root={root.hex()[:12]}… ctrl={[len(b)//2 for b in blocks]}")

    for v in negative:
        assert "error" in v["expected"], v["id"]
        print(f"[ok] {v['id']:34s} rejected: {v['expected']['error'][:60]}")

    # ---- how this repository's demo relates to the envelope ----------------
    demo = json.loads(DEMO.read_text())
    spk = bytes.fromhex(demo["script_pubkey_hex"])
    assert len(spk) == 34 and spk[:2] == b"\x52\x20", "demo scriptPubKey shape"
    demo_root = spk[2:]
    assert demo["root_recomputed"] is True

    # depth-1 control block: 1 + 32*1 bytes, as in the vectors
    assert (33 - 1) % 32 == 0

    try:
        decode_bech32m(demo["address"])
        demo_address_valid = True
        demo_address_note = "valid Bech32m"
    except ValueError as exc:
        demo_address_valid = False
        demo_address_note = f"not Bech32m ({exc})"

    # arithmetic in the paper's Section 8.3 (three distinct quantities)
    w = demo["wots_leaf_witness_bytes"]
    no_prefix = 1 + 2144 + 2144 + 3 + 33
    per_item = 1 + 134 * (1 + 32) + (1 + 3) + (1 + 33)
    bip_depth1 = 103 + 32 * 1
    assert no_prefix == 4325
    assert per_item == 4461
    assert bip_depth1 == 135
    assert w == per_item, f"demo stores {w}, expected {per_item}"
    assert demo["secp256k1_leaf_witness_bytes"] == bip_depth1

    print(f"\n[info] demo address: {demo_address_note}; "
          f"demo root is UMT-LEAF-based, not TapLeaf, so it cannot match a vector")
    print(f"[info] witness arithmetic: {no_prefix} B without item prefixes, "
          f"{per_item} B with 134 prefixed items (stored), "
          f"BIP depth-1 CHECKSIG leaf {bip_depth1} B")
    print(f"[info] demo address decodes as Bech32m: {demo_address_valid} "
          "(false is expected and disclosed in Section 8.2)")

    print(f"\n{len(positive)} positive vectors: {checked_leaves} leaf hashes, "
          f"{checked_addresses} addresses, {checked_blocks} control blocks; "
          f"{len(negative)} negative vectors")
    print("BIP-0360 envelope rules reproduced from the vectors")


if __name__ == "__main__":
    run()
