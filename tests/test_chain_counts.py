"""Chain-call accounting: theory vs. runtime counter (review plan, 4.2).

Theory (per signature, one leaf):

    L            = len1 + len2
    T_sign       = sum_i d_i
    T_verify     = L * (w - 1) - T_sign

The runtime counter wraps ``experiment_submission.chain`` and adds the number
of hash steps actually requested.  The test fails if theory and observation
differ for any (w, h) configuration, which is the condition the review plan
sets before any timing table may be regenerated.

Run:  python3 tests/test_chain_counts.py
"""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT / "experiments"))

import experiment_submission as es  # noqa: E402

_real_chain = es.chain
_real_leaf = es.leaf_hash
_real_node = es.node_hash

COUNT = {"steps": 0, "leaf": 0, "node": 0}


def counting_chain(x, start, steps):
    COUNT["steps"] += steps
    return _real_chain(x, start, steps)


def counting_leaf(pk):
    COUNT["leaf"] += 1
    return _real_leaf(pk)


def counting_node(left, right):
    COUNT["node"] += 1
    return _real_node(left, right)


es.chain = counting_chain
es.leaf_hash = counting_leaf
es.node_hash = counting_node


def run() -> None:
    rows = []
    for w, h in ((4, 4), (16, 4), (256, 4), (16, 8)):
        p = es.params(w)
        seed = es.H(b"SUB-TREE" + bytes([es.W_TO_CODE[w], h, 0]))
        leaves_pk, layers = es.build_tree(seed, w, h)
        sk, pk = leaves_pk[1]
        msg = b"chain-count-" + bytes([w & 0xFF, h])
        pkb = es.pack_pk(w, h, layers[h][0])

        digits = es.all_digits(msg, p)
        t_sign = sum(digits)
        t_verify = p["len"] * (w - 1) - t_sign

        COUNT.update(steps=0, leaf=0, node=0)
        sig_e, sig_c = es.sign(msg, 1, w, h, sk, pk, layers)
        sign_steps = COUNT["steps"]

        COUNT.update(steps=0, leaf=0, node=0)
        assert es.verify(msg, sig_e, pkb, expect_mode=0)
        ver_e_steps, leaf_e, node_e = COUNT["steps"], COUNT["leaf"], COUNT["node"]

        COUNT.update(steps=0, leaf=0, node=0)
        assert es.verify(msg, sig_c, pkb, expect_mode=1)
        ver_c_steps, leaf_c, node_c = COUNT["steps"], COUNT["leaf"], COUNT["node"]

        # theory vs runtime
        assert sign_steps == t_sign, (w, h, sign_steps, t_sign)
        assert ver_e_steps == t_verify, (w, h, ver_e_steps, t_verify)
        assert ver_c_steps == t_verify, (w, h, ver_c_steps, t_verify)
        assert sign_steps + ver_e_steps == p["len"] * (w - 1)

        # leaf hashed once, one node per level; no extra tree work
        assert leaf_e == leaf_c == 1, (leaf_e, leaf_c)
        assert node_e == node_c == h, (node_e, node_c, h)

        rows.append({
            "w": w, "h": h, "len": p["len"],
            "t_sign": t_sign, "t_verify": t_verify,
            "runtime_sign": sign_steps, "runtime_verify": ver_e_steps,
            "leaf_hashes": leaf_e, "node_hashes": node_e,
        })
        print(f"[ok] w={w:3d} h={h}  T_sign={t_sign:4d}  "
              f"T_verify={t_verify:4d}  leaf=1 node={node_e}")

    # The legacy encoder forced all checksum digits to zero, so its signature
    # work was sum(message digits) only.  Record the difference explicitly so
    # the old tables cannot be silently mixed with the repaired ones.
    p = es.params(16)
    md = es.msg_digits(b"legacy-delta", p)
    legacy_sign = sum(md)              # checksum contribution 0
    repaired_sign = legacy_sign + sum(es.checksum_digits(sum(15 - d for d in md), p))
    print(f"[info] w=16 sample: legacy T_sign={legacy_sign}, "
          f"repaired T_sign={repaired_sign}, delta={repaired_sign - legacy_sign}")
    assert repaired_sign > legacy_sign

    print(f"\n{len(rows)} configurations: theory == runtime, "
          "T_sign + T_verify == L(w-1)")


if __name__ == "__main__":
    run()
