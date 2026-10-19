"""Figures for the audited paper; legacy timing data remain unchanged.

Figures 1 and 2 depict the *legacy* (pre-repair) prototype: the timings in
experiments/results_jce.json were recorded with the defective checksum, and the
chain-call counts come from the deterministic audit.  This script is kept
runnable so that both figures can be rebuilt from the archived artefacts.

Run:  python3 charts/make_charts_jce.py
"""
import json
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

OUT = Path(__file__).resolve().parents[1]
rows = json.loads((OUT / "experiments" / "results_jce.json").read_text())
audit = json.loads((OUT / "audit" / "audit_jce.json").read_text())

# Payload sizes live under byte_accounting; accept the older flat key as well.
byte_rows = audit["byte_accounting"]["rows"]
sizes = [r.get("explicit_key_payload_bytes", r.get("explicit_pk_payload_bytes"))
         for r in byte_rows]
if any(s is None for s in sizes):
    raise SystemExit("byte accounting is missing explicit payload sizes")

chain_rows = audit["table4_exact_chain_work"]["rows"]
sign_steps = [r.get("sign_chain_calls", r.get("sign_steps")) for r in chain_rows]
verify_steps = [r.get("verify_chain_calls", r.get("verify_steps")) for r in chain_rows]
if any(s is None for s in sign_steps + verify_steps):
    raise SystemExit("audit is missing exact chain-call counts")

plt.rcParams.update({"font.size": 11, "axes.spines.top": False,
                     "axes.spines.right": False, "savefig.facecolor": "white"})

fig, ax = plt.subplots(figsize=(9, 5))
for key, label, color, marker in [("sign", "Signing", "#17685d", "o"),
                                  ("verify", "Verification", "#b17138", "s")]:
    ax.errorbar(sizes, [r[f"{key}_ms_mean"] for r in rows],
                yerr=[r[f"{key}_ms_std"] for r in rows], fmt=marker + "-",
                color=color, label=label, capsize=5, lw=1.6)
for x, r in zip(sizes, rows):
    ax.annotate(f"w = {r['w']}", (x, r["sign_ms_mean"]), xytext=(0, 16),
                textcoords="offset points", ha="center", fontsize=10)
ax.set(xlabel="Explicit-public-key payload (bytes; index / framing excluded)",
       ylabel="Historical latency (ms)", ylim=(-.05, 3.65), xlim=(1600, 9200))
ax.grid(axis="y", alpha=.2)
ax.legend(frameon=False)
fig.text(.1, .98, "Recorded timings · legacy prototype with checksum defect",
         va="top", fontsize=12, fontweight="bold")
fig.tight_layout(rect=[0, 0, 1, .94])
fig.savefig(OUT / "figures" / "fig_jce_wtradeoff.png", dpi=300)
plt.close(fig)

fig, ax = plt.subplots(figsize=(9, 5))
xs = list(range(len(chain_rows)))
width = .34
ax.bar([x - width / 2 for x in xs], sign_steps, width,
       label="Signing", color="#17685d")
ax.bar([x + width / 2 for x in xs], verify_steps, width,
       label="Verification", color="#b17138")
for x, s, v in zip(xs, sign_steps, verify_steps):
    ax.text(x - width / 2, s * 1.12, f"{s:,}", ha="center", fontsize=10)
    ax.text(x + width / 2, v * 1.12, f"{v:,}", ha="center", fontsize=10)
ax.set(xticks=xs, xticklabels=[f"w = {r['w']}" for r in chain_rows],
       ylabel="Chain hash calls (log scale)", yscale="log", ylim=(100, 10000))
ax.grid(axis="y", alpha=.15)
ax.set_axisbelow(True)
ax.legend(frameon=False)
fig.text(.1, .98, "Exact chain work · fixed benchmark message",
         va="top", fontsize=12, fontweight="bold")
fig.tight_layout(rect=[0, 0, 1, .94])
fig.savefig(OUT / "figures" / "fig_jce_costmodel.png", dpi=300)
plt.close(fig)

print("Regenerated both JCE figures from preserved timing data and audit evidence.")
print("payload sizes:", sizes, "| sign:", sign_steps, "| verify:", verify_steps)
