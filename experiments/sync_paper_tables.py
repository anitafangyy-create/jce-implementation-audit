"""Synchronise the data-derived tables and the robust-statistics paragraph.

The manuscript must not be edited by hand where a JSON artefact already
determines the value.  This tool renders the expected Markdown from
``results_submission.json`` and ``robust_stats.json`` and either checks the
paper against it (default) or rewrites it (``--write``).

Tables handled: Table 9 and Table 9b, plus the "Robust statistics" paragraph
that quotes medians, ranges, and the paired-difference share.

Usage:
    python3 experiments/sync_paper_tables.py            # check only
    python3 experiments/sync_paper_tables.py --write    # update the paper
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
PAPER = ROOT / "paper" / "paper_jce.md"
RES = HERE / "results_submission.json"
ROBUST = HERE / "robust_stats.json"

ROW_RE = re.compile(r"^\|\s*\d+\s*\|\s*\d+\s*\|")


def table9(res: dict) -> list[str]:
    rows = []
    for cfg, v in res["configs"].items():
        w, h = cfg.replace("w=", "").split(",h=")
        e, c = v["explicit_verify_ms"], v["compact_verify_ms"]
        rows.append(
            f"| {w} | {h} | {round(v['explicit_bytes']['mean']):,} | "
            f"{round(v['compact_bytes']['mean']):,} | "
            f"{e['mean']:.3f} ± {e['sd']:.3f} | {c['mean']:.3f} ± {c['sd']:.3f} |")
    return rows


def table9b(robust: dict) -> list[str]:
    rows = []
    for cfg, v in robust["per_config"].items():
        w, h = cfg.replace("w=", "").split(",h=")
        e, c = v["explicit"], v["compact"]
        d = v["paired_diff_explicit_minus_compact"]
        rows.append(
            f"| {w} | {h} | {e['median_ms']:.4f} | {e['iqr_ms']:.4f} | "
            f"{c['median_ms']:.4f} | {c['iqr_ms']:.4f} | "
            f"{d['median_ms']:+.4f} | {d['explicit_slower_share'] * 100:.0f}% |")
    return rows


def robust_paragraph(res: dict, robust: dict) -> str:
    raw = res["raw_samples"]
    gaps = []
    sd_gt = []
    for cfg, rv in robust["per_config"].items():
        for mode, key in (("explicit", "explicit_verify_ms"),
                          ("compact", "compact_verify_ms")):
            e = res["configs"][cfg][key]
            med = rv[mode]["median_ms"]
            gaps.append((abs(e["mean"] - med), cfg, mode, e, med))
            if e["sd"] > e["mean"]:
                sd_gt.append((cfg, mode, e))
    _, gcfg, gmode, g, gmed = max(gaps)

    w, h = gcfg.replace("w=", "").split(",h=")
    text = ("**Robust statistics.** Table 9b reports medians and interquartile "
            "ranges alongside the means and sample standard deviations of "
            "Table 9, plus the per-event paired difference between the two "
            "serialization modes. All 270 raw samples are retained; no sample "
            "was removed as an outlier. In this run, medians and means are "
            f"close at most configurations; the largest gap is {gmode} "
            f"verification at w = {w}, h = {h} (median {gmed:.3f} ms "
            f"versus mean {g['mean']:.3f} ms)")
    if sd_gt:
        parts = []
        for cfg, mode, e in sd_gt:
            cw, ch = cfg.replace("w=", "").split(",h=")
            parts.append(f"w = {cw}, h = {ch} {mode} ({e['mean']:.3f} ± "
                         f"{e['sd']:.3f} ms, maximum {e['max']:.3f} ms)")
        text += ", and " + " and ".join(parts) + \
            (" has" if len(parts) == 1 else " have") + \
            " a sample standard deviation above the mean"
    text += "."
    ex = [r["explicit_verify_ms"] for r in raw]
    co = [r["compact_verify_ms"] for r in raw]
    dmax = max(v["paired_diff_explicit_minus_compact"]["median_ms"]
               for v in robust["per_config"].values())
    shares = [v["paired_diff_explicit_minus_compact"]["explicit_slower_share"] * 100
              for v in robust["per_config"].values()]
    text += (f" Sample ranges across configurations are {min(ex):.3f}–"
             f"{max(ex):.3f} ms (explicit) and {min(co):.3f}–{max(co):.3f} ms "
             f"(compact). Paired difference medians are at most {dmax:.3f} ms, "
             f"and the share of events in which the explicit mode was slower "
             f"ranges from {min(shares):.0f}% to {max(shares):.0f}%.")
    spreads = []
    for rv in robust["per_config"].values():
        vals = [t["explicit_median_ms"] for t in rv["tree_level"].values()]
        spreads.append((max(vals) - min(vals)) / (sum(vals) / len(vals)) * 100)
    text += (f" Within a configuration, the three per-tree medians spanned "
             f"{min(spreads):.1f}–{max(spreads):.1f}% (explicit mode), so tree "
             "identity does not explain the between-configuration differences; "
             "the paired difference is computed within each event.")
    text += (" Size savings are therefore the primary measured result of the two "
             "encodings, while timing differences are exploratory observations; "
             "no uniform latency advantage is claimed.")
    return text


def replace_table(lines: list[str], marker: str, rows: list[str]) -> list[str]:
    idx = next(i for i, l in enumerate(lines)
               if marker in l and l.lstrip().startswith("|"))
    start = idx + 2
    end = start
    while end < len(lines) and ROW_RE.match(lines[end]):
        end += 1
    if end - start != len(rows):
        raise SystemExit(f"{marker}: found {end - start} rows, expected {len(rows)}")
    return lines[:start] + rows + lines[end:]


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--write", action="store_true")
    args = ap.parse_args()

    res = json.loads(RES.read_text())
    robust = json.loads(ROBUST.read_text())
    original = PAPER.read_text().splitlines()

    lines = replace_table(original, "Explicit verify (ms)", table9(res))
    lines = replace_table(lines, "Explicit median (ms)", table9b(robust))

    pi = next(i for i, l in enumerate(lines) if l.startswith("**Robust statistics.**"))
    new_para = robust_paragraph(res, robust)
    if lines[pi] != new_para:
        lines[pi] = new_para

    changed = sum(1 for a, b in zip(original, lines) if a != b)
    if not args.write:
        if changed:
            print(f"{changed} line(s) differ from the retained data")
            for a, b in zip(original, lines):
                if a != b:
                    print("  paper :", a[:120])
                    print("  data  :", b[:120])
            sys.exit(1)
        print("Table 9, Table 9b, and the robust-statistics paragraph match the data")
        return

    PAPER.write_text("\n".join(lines) + "\n")
    print(f"updated {changed} line(s) in {PAPER}")


if __name__ == "__main__":
    main()
