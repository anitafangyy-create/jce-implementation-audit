#!/usr/bin/env python3
"""Summarize paired timing data using tree-level aggregation."""
import argparse
import csv
import json
import statistics
from collections import defaultdict
from pathlib import Path


def percentile(xs, p):
    ys = sorted(xs)
    if not ys:
        return None
    if len(ys) == 1:
        return ys[0]
    pos = (len(ys) - 1) * p
    lo = int(pos)
    hi = min(lo + 1, len(ys) - 1)
    frac = pos - lo
    return ys[lo] * (1 - frac) + ys[hi] * frac


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("csv_path")
    ap.add_argument("--out", default="results/endpoint_summary.json")
    args = ap.parse_args()

    # First reduce repeated timings to a median per tree/leaf/mode.
    buckets = defaultdict(list)
    sizes = {}
    with open(args.csv_path, newline="", encoding="utf-8") as f:
        for r in csv.DictReader(f):
            key = (int(r["tree_id"]), int(r["leaf_id"]), r["mode"])
            buckets[key].append(int(r["elapsed_ns"]))
            sizes[(int(r["tree_id"]), int(r["leaf_id"]), r["mode"])] = int(r["output_bytes"])

    leaf_medians = {k: statistics.median(v) for k, v in buckets.items()}
    tree_deltas = defaultdict(list)
    tree_ratios = defaultdict(list)
    tree_size_savings = defaultdict(list)
    tree_ids = sorted({k[0] for k in leaf_medians})
    for tree in tree_ids:
        leaf_ids = sorted({k[1] for k in leaf_medians if k[0] == tree})
        for leaf in leaf_ids:
            ke = (tree, leaf, "explicit")
            kr = (tree, leaf, "recovered")
            if ke not in leaf_medians or kr not in leaf_medians:
                continue
            te, tr = leaf_medians[ke], leaf_medians[kr]
            tree_deltas[tree].append(tr - te)
            if te > 0:
                tree_ratios[tree].append(tr / te)
            se, sr = sizes[ke], sizes[kr]
            if se > 0:
                tree_size_savings[tree].append((se - sr) / se * 100)

    # Trees are the top-level clusters; report distribution of tree summaries.
    per_tree = []
    for tree in tree_ids:
        if not tree_deltas[tree]:
            continue
        per_tree.append({
            "tree_id": tree,
            "median_paired_delta_ns": statistics.median(tree_deltas[tree]),
            "median_paired_ratio": statistics.median(tree_ratios[tree]) if tree_ratios[tree] else None,
            "median_size_saving_percent": statistics.median(tree_size_savings[tree]) if tree_size_savings[tree] else None,
            "paired_leaf_count": len(tree_deltas[tree]),
        })

    def summarize(field):
        vals = [x[field] for x in per_tree if x[field] is not None]
        return {
            "n_independent_trees": len(vals),
            "median": statistics.median(vals) if vals else None,
            "q1": percentile(vals, 0.25),
            "q3": percentile(vals, 0.75),
            "min": min(vals) if vals else None,
            "max": max(vals) if vals else None,
        }

    result = {
        "interpretation_warning": "Use only with genuine implementation measurements. Tree-level summaries avoid treating all leaf repetitions as independent trees.",
        "paired_delta_ns_recovered_minus_explicit": summarize("median_paired_delta_ns"),
        "paired_time_ratio_recovered_over_explicit": summarize("median_paired_ratio"),
        "encoded_size_saving_percent": summarize("median_size_saving_percent"),
        "per_tree": per_tree,
    }
    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(result, indent=2), encoding="utf-8")
    print(json.dumps({k: v for k, v in result.items() if k != "per_tree"}, indent=2))
    print(f"Saved {out}")


if __name__ == "__main__":
    main()
