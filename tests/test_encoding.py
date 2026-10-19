"""Encoding tests for the repaired checksum (review plan, Section 2.2).

Two implementations are compared deliberately:

* ``production`` -- ``experiment_submission.checksum_digits``, the encoder the
  repaired experiment actually uses;
* ``reference``  -- an independent integer-to-digit conversion written here
  from the paper's definition.  It shares no code with the production
  encoder, so a shared coding mistake cannot make both agree.

Cases E1-E8 follow the review plan.  Run:  python3 tests/test_encoding.py
"""
from __future__ import annotations

import math
import random
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT / "experiments"))

from experiment_submission import checksum_digits as production  # noqa: E402
from experiment_submission import params, all_digits, msg_digits  # noqa: E402

W_VALUES = (4, 16, 256)
N = 32


# ---------------------------------------------------------------------------
# Independent reference encoder (definition, not implementation, is shared)
# ---------------------------------------------------------------------------
def reference(c: int, w: int, len2: int) -> list[int]:
    """c_j = floor(C / w^(len2-1-j)) mod w, most significant digit first."""
    return [(c // (w ** (len2 - 1 - j))) % w for j in range(len2)]


def decode(digits: list[int], w: int) -> int:
    total = 0
    for d in digits:
        total = total * w + d
    return total


def checksum_of(digits: list[int], w: int) -> int:
    return sum(w - 1 - d for d in digits)


def run() -> None:
    rng = random.Random(20261019)
    passed = 0

    for w in W_VALUES:
        p = params(w)
        len1, len2 = p["len1"], p["len2"]
        c_max = len1 * (w - 1)
        assert c_max < w ** len2, f"len2 too small for w={w}"

        # E1: all-zero message digits -> C = len1 (w-1)
        c = checksum_of([0] * len1, w)
        assert c == len1 * (w - 1)
        assert decode(production(c, p), w) == c
        passed += 1

        # E2: all-max message digits -> C = 0
        c = checksum_of([w - 1] * len1, w)
        assert c == 0
        assert production(c, p) == [0] * len2
        passed += 1

        # E3: changing one message digit changes C by exactly the delta
        base = msg_digits(b"delta-test", p)
        c0 = checksum_of(base, w)
        for j in (0, len1 // 2, len1 - 1):
            if base[j] == 0:
                continue
            shifted = list(base)
            shifted[j] -= 1
            assert checksum_of(shifted, w) == c0 + 1
            assert production(c0 + 1, p) != production(c0, p) or w == 2
        passed += 1

        # E4: C = 0 keeps every leading zero
        out = production(0, p)
        assert len(out) == len2 and out == [0] * len2
        passed += 1

        # E5: maximum reachable C -> exact digit count, no truncation
        out = production(c_max, p)
        assert len(out) == len2 and decode(out, w) == c_max
        passed += 1

        # E6: round-trip over every legal boundary value
        boundaries = {0, 1, w - 1, w, c_max - 1, c_max,
                      w ** (len2 - 1) - 1, w ** (len2 - 1)}
        for c in sorted(x for x in boundaries if 0 <= x <= c_max):
            got = production(c, p)
            assert got == reference(c, w, len2), f"w={w} c={c}: {got}"
            assert decode(got, w) == c
        passed += 1

        # E7: random checksums, production vs independent reference
        for _ in range(2000):
            c = rng.randint(0, c_max)
            assert production(c, p) == reference(c, w, len2), f"w={w} c={c}"
        passed += 1

        # E8: digit order is most-significant-first, not least-significant
        if len2 >= 2:
            assert production(w, p)[-1] == 0 and production(w, p)[-2] == 1
            assert production(1, p)[-1] == 1 and production(1, p)[0] == 0
        passed += 1

        print(f"[ok] w={w:3d}  len1={len1:3d} len2={len2}  C_max={c_max}")

    # E9 (extra): all_digits length and checksum-position sanity
    for w in W_VALUES:
        p = params(w)
        d = all_digits(b"position-check", p)
        assert len(d) == p["len"] and all(0 <= x < w for x in d)
        assert checksum_of(d[:p["len1"]], w) == decode(d[p["len1"]:], w)
    print("[ok] all_digits: checksum occupies the final len2 positions")

    # E10 (extra): legacy defect is reproducible and distinguishable
    from wots import base_w, wots_checksum
    for c in (0, 1, 15, 16, 554, 960):
        legacy = base_w(c.to_bytes(32, "big"), 3)
        assert legacy == [0, 0, 0], legacy
        assert wots_checksum(c) == reference(c, 16, 3)
    print("[ok] legacy encoder -> [0,0,0]; src/wots.py encoder -> definition")

    print(f"\n{passed} cases x 3 bases passed (E1-E8), plus 2 cross-checks")


if __name__ == "__main__":
    run()
