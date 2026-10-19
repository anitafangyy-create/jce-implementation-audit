"""Serialized-length accounting (review plan, 4.1).

For every configuration the test asserts

    total = header/index + elements + endpoints(mode 0 only) + path

against the actual byte string produced by the serializer, and checks that
the verifier's strict length rules accept exactly those lengths.

Run:  python3 tests/test_serialization.py
"""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT / "experiments"))

import experiment_submission as es  # noqa: E402
from experiment_submission import VerifyError  # noqa: E402

N = 32


def run() -> None:
    rows = []
    for w, h in ((4, 4), (4, 8), (16, 4), (16, 8), (256, 4), (256, 8)):
        p = es.params(w)
        n_idx = (h + 7) // 8
        header = 7 + n_idx
        elements = p["len"] * N
        endpoints = p["len"] * N
        path = h * N

        seed = es.H(b"SUB-TREE" + bytes([es.W_TO_CODE[w], h, 1]))
        leaves_pk, layers = es.build_tree(seed, w, h)
        sk, pk = leaves_pk[1]
        msg = b"size-accounting"
        sig_e, sig_c = es.sign(msg, 1, w, h, sk, pk, layers)
        pkb = es.pack_pk(w, h, layers[h][0])

        want_e = header + elements + endpoints + path
        want_c = header + elements + path
        assert len(pkb) == 38
        assert len(sig_e) == want_e, (w, h, len(sig_e), want_e)
        assert len(sig_c) == want_c, (w, h, len(sig_c), want_c)

        # the verifier accepts exactly these lengths
        assert es.verify(msg, sig_e, pkb, expect_mode=0)
        assert es.verify(msg, sig_c, pkb, expect_mode=1)

        # and rejects one byte more or less in either mode
        for bad in (sig_e[:-1], sig_e + b"\x00", sig_c[:-1], sig_c + b"\x00"):
            try:
                es.verify(msg, bad, pkb)
            except VerifyError:
                pass
            else:
                raise AssertionError(f"length mismatch accepted: w={w} h={h}")

        rows.append({
            "w": w, "h": h, "len": p["len"],
            "header": header, "elements": elements,
            "endpoints": endpoints, "path": path,
            "explicit_total": len(sig_e), "compact_total": len(sig_c),
        })
        print(f"[ok] w={w:3d} h={h}  header={header:2d} elem={elements:5d} "
              f"ep={endpoints:5d} path={path:4d}  "
              f"explicit={len(sig_e):5d} compact={len(sig_c):5d}")

    # height four, w=256 is the smallest repaired configuration
    smallest = next(r for r in rows if r["w"] == 256 and r["h"] == 4)
    assert smallest["compact_total"] == 1224
    print(f"\nsmallest retained configuration: {smallest['compact_total']} B "
          "(1,216 payload + 8-byte experimental header)")

    # five term identity for every row
    for r in rows:
        assert r["explicit_total"] == (r["header"] + r["elements"]
                                       + r["endpoints"] + r["path"])
        assert r["compact_total"] == r["header"] + r["elements"] + r["path"]
    print(f"{len(rows)} configurations: serializer length == term sum")


if __name__ == "__main__":
    run()
