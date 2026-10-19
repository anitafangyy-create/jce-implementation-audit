#!/usr/bin/env python3
"""Figure 4: same-machine native C comparison.

Reads experiments/native_results_sessions.json (cross-session medians) and
draws signing/verification latency on a log scale plus signature size.
Every number in the figure comes from that file; rerunning
bench/native/run_sessions.py and this script regenerates it.

Run:  python3 charts/make_native_figure.py
"""
from __future__ import annotations

import json
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "experiments" / "native_results_sessions.json"
OUT = ROOT / "figures" / "fig_native_benchmark.png"

ROWS = [
    ("ML-DSA-44", "ML-DSA-44", "stateless"),
    ("ML-DSA-65", "ML-DSA-65", "stateless"),
    ("SLH-DSA-128f", "SLH-DSA-SHA2-128f (PQClean)", "stateless"),
    ("SLH-DSA-128s", "SLH-DSA-SHA2-128s (PQClean)", "stateless"),
    ("WOTS h=8 explicit", "wots|False|8", "stateful"),
    ("WOTS h=8 recovered", "wots|True|8", "stateful"),
]


def main() -> None:
    data = json.loads(DATA.read_text())
    summary = data["summary"]
    present = [(label, summary[key]) for label, key, _ in ROWS if key in summary]
    if not present:
        raise SystemExit("no rows found; run bench/native/run_sessions.py first")

    labels = [p[0] for p in present]
    sign = [p[1]["sign_ms"]["median"] for p in present]
    verify = [p[1]["verify_ms"]["median"] for p in present]
    size = [p[1]["sig_bytes"] if "sig_bytes" in p[1] else p[1].get("sig", 0)
            for p in present]

    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(11.2, 4.3),
                                   gridspec_kw={"width_ratios": [1.45, 1]})
    y = range(len(labels))

    ax1.set_xscale("log")
    ax1.scatter(sign, list(y), s=46, color="#1f4e79", label="sign", zorder=3)
    ax1.scatter(verify, list(y), s=46, color="#c0504d", marker="s",
                label="verify", zorder=3)
    for i, (s, v) in enumerate(zip(sign, verify)):
        ax1.plot([s, v], [i, i], color="#bfbfbf", lw=1.2, zorder=1)
        ax1.text(max(s, v) * 1.35, i, f"{s:.3g} / {v:.3g} ms",
                 va="center", fontsize=7.5, color="#333333")
    ax1.set_yticks(list(y))
    ax1.set_yticklabels(labels, fontsize=8.5)
    ax1.invert_yaxis()
    ax1.set_xlabel("latency (ms, log scale)", fontsize=9)
    ax1.set_title("Signing and verification latency", fontsize=10)
    ax1.set_xlim(left=min(min(sign), min(verify)) * 0.5,
                 right=max(max(sign), max(verify)) * 12)
    ax1.grid(axis="x", color="#e6e6e6", lw=0.8)
    ax1.legend(fontsize=8, loc="lower right", frameon=False)
    for spine in ("top", "right"):
        ax1.spines[spine].set_visible(False)

    ax2.barh(list(y), size, color="#6b8e23", height=0.55)
    for i, v in enumerate(size):
        ax2.text(v * 1.04, i, f"{v:,} B", va="center", fontsize=8)
    ax2.set_yticks(list(y))
    ax2.set_yticklabels([])
    ax2.invert_yaxis()
    ax2.set_xlabel("signature size (bytes)", fontsize=9)
    ax2.set_title("Signature size", fontsize=10)
    ax2.set_xlim(0, max(size) * 1.32)
    ax2.grid(axis="x", color="#e6e6e6", lw=0.8)
    for spine in ("top", "right"):
        ax2.spines[spine].set_visible(False)

    fig.suptitle("Same-machine native C comparison (Apple M1, PQClean clean C)",
                 fontsize=10.5, y=0.99)
    fig.text(0.01, 0.01,
             "Cross-session medians of three sessions. Prototype rows are "
             "stateful (256 signatures per key); standard rows are stateless.",
             fontsize=7, color="#555555")
    fig.tight_layout(rect=(0, 0.03, 1, 0.96))
    fig.savefig(OUT, dpi=300, facecolor="white")
    print(f"[written] {OUT}")


if __name__ == "__main__":
    main()
