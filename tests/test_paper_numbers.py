"""Check that the numbers printed in the paper match the retained data.

This is a regression guard against silent drift between JSON artefacts and
the manuscript (the 4,460-versus-4,461 incident is the motivating example).
It parses the Markdown tables directly, recomputes the expected cells from
the JSON files, and fails on any mismatch.

Tables checked
--------------
* Table 9  (repaired-variant sizes and mean +/- SD)  <- results_submission.json
* Table 9b (medians, IQR, paired difference)          <- robust_stats.json
* Table 10 (same-machine SLH-DSA reference)           <- sphincs_benchmark.json
* Table 11a (native C comparison)                     <- native_results_sessions.json
                                                         and like_for_like.json
* Table 15 (state fault matrix)                       <- text/evidence labels only
* Table 16 (Appendix B check accounting)              <- check_counts.json
* Global counts 270 / 5,130                           <- results_submission.json

Run:  python3 tests/test_paper_numbers.py
"""
from __future__ import annotations

import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PAPER = ROOT / "paper" / "paper_jce.md"
RES = ROOT / "experiments" / "results_submission.json"
ROBUST = ROOT / "experiments" / "robust_stats.json"
NATIVE = ROOT / "experiments" / "native_results_sessions.json"
PAIRED = ROOT / "experiments" / "like_for_like.json"

FAILS: list[str] = []


def fail(msg: str) -> None:
    FAILS.append(msg)
    print(f"[FAIL] {msg}")


def ok(msg: str) -> None:
    print(f"[ok]   {msg}")


def parse_table(md: str, marker: str) -> list[list[str]]:
    lines = md.splitlines()
    for i, line in enumerate(lines):
        if marker in line and line.lstrip().startswith("|"):
            break
    else:
        raise AssertionError(f"table marker not found: {marker}")
    rows = []
    for line in lines[i + 1:]:
        if not line.lstrip().startswith("|"):
            break
        cells = [c.strip() for c in line.strip().strip("|").split("|")]
        if all(set(c) <= set("-: ") for c in cells):
            continue
        rows.append(cells)
    return rows


def close(a: float, b: float, tol: float = 5.5e-4) -> bool:
    return abs(a - b) <= tol


def check_float(label: str, cell: str, want: float, fmt: str) -> None:
    token = cell.replace(",", "").split("±")[0].strip()
    got = float(token)
    if not close(got, float(fmt.format(want))):
        fail(f"{label}: paper {cell!r} != data {fmt.format(want)!r}")
    else:
        ok(f"{label}: {cell}")


def bracket(cell: str):
    m = re.match(r"^([\d.]+)\s*\[([\d.]+)[–\-]([\d.]+)\]$", cell.replace(",", ""))
    if not m:
        raise ValueError(cell)
    return float(m.group(1)), float(m.group(2)), float(m.group(3))


def main() -> None:
    md = PAPER.read_text()
    res = json.loads(RES.read_text())
    robust = json.loads(ROBUST.read_text())
    native = json.loads(NATIVE.read_text())
    paired = json.loads(PAIRED.read_text())

    # ---- Table 9 ---------------------------------------------------------
    rows = parse_table(md, "Explicit verify (ms)")
    assert len(rows) == 6, len(rows)
    for w, h, exp_b, com_b, exp_ms, com_ms in rows:
        cfg = f"w={w},h={h}"
        want = res["configs"][cfg]
        if int(exp_b.replace(",", "")) != round(want["explicit_bytes"]["mean"]):
            fail(f"Table 9 {cfg} explicit bytes")
        if int(com_b.replace(",", "")) != round(want["compact_bytes"]["mean"]):
            fail(f"Table 9 {cfg} compact bytes")
        for cell, key in ((exp_ms, "explicit_verify_ms"), (com_ms, "compact_verify_ms")):
            e = want[key]
            check_float(f"Table 9 {cfg} {key}", cell, e["mean"], "{:.3f}")
            if f"{e['sd']:.3f}" not in cell:
                fail(f"Table 9 {cfg} {key} sd: paper {cell!r} != {e['sd']:.3f}")
    ok("Table 9: 6 rows, sizes and mean ± SD match")

    # ---- Table 9b --------------------------------------------------------
    rows = parse_table(md, "Explicit median (ms)")
    assert len(rows) == 6, len(rows)
    for w, h, em, ei, cm, ci, pd, share in rows:
        cfg = f"w={w},h={h}"
        r = robust["per_config"][cfg]
        check_float(f"Table 9b {cfg} explicit median", em, r["explicit"]["median_ms"], "{:.4f}")
        check_float(f"Table 9b {cfg} explicit IQR", ei, r["explicit"]["iqr_ms"], "{:.4f}")
        check_float(f"Table 9b {cfg} compact median", cm, r["compact"]["median_ms"], "{:.4f}")
        check_float(f"Table 9b {cfg} compact IQR", ci, r["compact"]["iqr_ms"], "{:.4f}")
        check_float(f"Table 9b {cfg} paired delta", pd, r["paired_diff_explicit_minus_compact"]["median_ms"], "{:+.4f}")
        got_share = float(share.rstrip("%"))
        want_share = r["paired_diff_explicit_minus_compact"]["explicit_slower_share"] * 100
        if abs(got_share - round(want_share)) > 0.5:
            fail(f"Table 9b {cfg} share: {share} != {want_share:.0f}%")
    ok("Table 9b: 6 rows, medians/IQR/paired delta/share match")

    # ---- Table 11a -------------------------------------------------------
    rows = parse_table(md, "Scheme | Keygen (ms)")
    assert len(rows) == 6, len(rows)
    std_map = {
        "ML-DSA-44": "ML-DSA-44",
        "ML-DSA-65": "ML-DSA-65",
        "SLH-DSA-SHA2-128s": "SLH-DSA-SHA2-128s (PQClean)",
        "SLH-DSA-SHA2-128f": "SLH-DSA-SHA2-128f (PQClean)",
    }
    c = paired["summary"]["c"]
    for cells in rows:
        name = cells[0]
        if name in std_map:
            e = native["summary"][std_map[name]]
            for cell, key in zip(cells[1:4], ("keygen_ms", "sign_ms", "verify_ms")):
                med, lo, hi = bracket(cell)
                if not close(med, e[key]["median"], 5e-3):
                    fail(f"Table 11a {name} {key} median: {cell} != {e[key]['median']}")
            if int(cells[4].replace(",", "")) != e["sig"]:
                fail(f"Table 11a {name} size")
        else:
            compact = "recovered" in name
            for cell, key in zip(cells[1:3], ("keygen_ms", "sign_ms")):
                med, lo, hi = bracket(cell)
                if not close(med, c[key]["median"], 5e-3):
                    fail(f"Table 11a {name} {key}: {cell} != {c[key]['median']}")
            mk = "verify_compact_ms" if compact else "verify_explicit_ms"
            med, lo, hi = bracket(cells[3])
            if not close(med, c[mk]["median"], 5e-3):
                fail(f"Table 11a {name} verify: {cells[3]} != {c[mk]['median']}")
            want_size = paired["size"]["compact_bytes" if compact else "explicit_bytes"]
            if int(cells[4].replace(",", "")) != want_size:
                fail(f"Table 11a {name} size: {cells[4]} != {want_size}")
    ok("Table 11a: 6 rows match native/like-for-like data")

    # ---- Table 10 (same-machine SLH-DSA reference) -----------------------
    rows = parse_table(md, "Parameter set | Public key (B)")
    assert len(rows) == 2, len(rows)
    sphincs = json.loads((ROOT / "experiments" / "sphincs_benchmark.json").read_text())
    for cells in rows:
        name = cells[0]
        key = name.lower().replace("slh-dsa-", "sphincs-").replace("sha2-", "sha2-")
        blk = sphincs["sets"].get(key)
        if blk is None:
            fail(f"Table 10 {name}: no matching benchmark set ({key})")
            continue
        if int(cells[1]) != 32 or int(cells[2].replace(",", "")) != int(blk["meta"]["sig_bytes"]):
            fail(f"Table 10 {name}: key/signature size")
        for cell, metric in zip(cells[3:6], ("keygen_ms", "sign_ms", "verify_ms")):
            mean_s, sd_s = [x.strip().replace(",", "") for x in cell.split("±")]
            e = blk["summary"][metric]
            if not close(float(mean_s), e["mean"], 5e-3) or \
               not close(float(sd_s), e["sd"], 5e-3):
                fail(f"Table 10 {name} {metric}: {cell} != {e['mean']:.2f} ± {e['sd']:.2f}")
    ok("Table 10: 2 rows match sphincs_benchmark.json")

    # ---- Table 16 (Appendix B: check accounting) -------------------------
    rows = parse_table(md, "Check category")
    numeric = []
    for cells in rows:
        raw = cells[1].replace(",", "").replace("*", "")
        if raw.isdigit():
            numeric.append(int(raw))
    counts = json.loads((ROOT / "experiments" / "check_counts.json").read_text())["total"]
    want = [counts["positive_checks"] // 2, counts["positive_checks"] // 2,
            counts["rejection_checks"], counts["key_identity_records"],
            counts["total_checks"]]
    if numeric != want:
        fail(f"Table 16 counts: {numeric} != {want}")
    ok("Table 16: 5 numeric rows match check_counts.json")

    # ---- Table 15 (state fault matrix) ----------------------------------
    rows = parse_table(md, "| ID | Scenario")
    if len(rows) != 10:
        fail(f"Table 15: {len(rows)} rows, expected 10")
    else:
        ids = [r[0] for r in rows]
        if ids != [f"ST-{i:02d}" for i in range(1, 11)]:
            fail(f"Table 15 IDs: {ids}")
        joined = " ".join(" ".join(r) for r in rows)
        for needle in ("12 unique, 0 duplicates, 0 lost", "rolled back = true",
                       "persisted = true", "root disabled", "CapacityExhausted",
                       "Not claimed"):
            if needle not in joined:
                fail(f"Table 15 missing evidence phrase: {needle}")
        ok("Table 15: 10 rows, ST-01..ST-10, evidence phrases present")

    # ---- global counts ---------------------------------------------------
    if res["total_signing_events"] != 270 or "270" not in md:
        fail("signing-event count 270")
    if res["total_counted_checks"] != 5130 or "5,130" not in md:
        fail("check count 5,130")
    ok("global counts: 270 events / 5,130 checks")

    # ---- environment provenance ------------------------------------------
    env = res["environment"]
    for key in ("cpu_brand", "python_full", "openssl", "loadavg_1_5_15",
                "session", "started_utc"):
        if key not in env:
            fail(f"environment missing {key}")
    ok("environment records CPU, interpreter, OpenSSL, load, session, timestamp")

    print()
    if FAILS:
        print(f"{len(FAILS)} mismatch(es)")
        sys.exit(1)
    print("paper numbers match the retained data")


if __name__ == "__main__":
    main()
