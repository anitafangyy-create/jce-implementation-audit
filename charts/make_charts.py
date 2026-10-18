"""Generate charts from results.json."""
import json
from pathlib import Path
import matplotlib.pyplot as plt
import numpy as np

OUT = Path(__file__).resolve().parents[1]
data = json.loads((OUT / "experiments" / "results.json").read_text())
rows = data["benchmark"]
ref = data["reference_schemes"]

plt.rcParams.update({"font.size": 11, "axes.grid": True, "grid.alpha": 0.3})

# ------------------------------------------------------------------
# Fig 1: Signature size comparison (log scale)
# ------------------------------------------------------------------
names = [r["name"] for r in ref]
sigs = [r["sig_bytes"] for r in ref]
colors = ["#888888", "#4C72B0", "#4C72B0", "#55A868", "#55A868", "#C44E52"]

fig, ax = plt.subplots(figsize=(10, 5.5))
bars = ax.barh(names, sigs, color=colors)
ax.set_xscale("log")
ax.set_xlabel("Signature size (bytes, log scale)")
ax.set_title("Post-quantum signature size comparison")
for bar, v in zip(bars, sigs):
    ax.text(v * 1.15, bar.get_y() + bar.get_height() / 2,
            f"{v:,} B", va="center", fontsize=10)
ax.axvline(64, color="#888", ls="--", alpha=0.5)
ax.text(70, -0.7, "secp256k1 baseline (64 B)", color="#666", fontsize=9)
plt.tight_layout()
plt.savefig(OUT / "figures" / "fig1_signature_size.png", dpi=150)
plt.close()

# ------------------------------------------------------------------
# Fig 2: Public key size comparison
# ------------------------------------------------------------------
pks = [r["pubkey_bytes"] for r in ref]
fig, ax = plt.subplots(figsize=(10, 5.5))
bars = ax.barh(names, pks, color=colors)
ax.set_xscale("log")
ax.set_xlabel("Public key size (bytes, log scale)")
ax.set_title("Public key size comparison")
for bar, v in zip(bars, pks):
    ax.text(v * 1.15, bar.get_y() + bar.get_height() / 2,
            f"{v:,} B", va="center", fontsize=10)
plt.tight_layout()
plt.savefig(OUT / "figures" / "fig2_pubkey_size.png", dpi=150)
plt.close()

# ------------------------------------------------------------------
# Fig 3: Key-generation time vs number of signatures supported
# ------------------------------------------------------------------
n = [r["n_signatures"] for r in rows]
kg = [r["key_gen_ms"] for r in rows]
fig, ax = plt.subplots(figsize=(8, 5))
ax.plot(n, kg, "o-", color="#C44E52", lw=2, markersize=8)
ax.set_xscale("log", base=2)
ax.set_xlabel("Number of one-time keys in tree (2^height)")
ax.set_ylabel("Key generation time (ms)")
ax.set_title("Merkle tree build time vs. supported signatures")
for xi, yi in zip(n, kg):
    ax.annotate(f"{yi:.1f}ms", (xi, yi), textcoords="offset points",
                xytext=(8, 5), fontsize=9)
plt.tight_layout()
plt.savefig(OUT / "figures" / "fig3_keygen_scaling.png", dpi=150)
plt.close()

# ------------------------------------------------------------------
# Fig 4: Sign / verify latency
# ------------------------------------------------------------------
sign_t = [r["sign_ms"] for r in rows]
verify_t = [r["verify_ms"] for r in rows]
fig, ax = plt.subplots(figsize=(8, 5))
ax.plot(n, sign_t, "o-", label="Sign", color="#4C72B0", lw=2)
ax.plot(n, verify_t, "s-", label="Verify", color="#55A868", lw=2)
ax.set_xscale("log", base=2)
ax.set_xlabel("Number of one-time keys in tree (2^height)")
ax.set_ylabel("Latency (ms)")
ax.set_title("Signing and verification latency (median of 3 runs)")
ax.legend()
plt.tight_layout()
plt.savefig(OUT / "figures" / "fig4_latency.png", dpi=150)
plt.close()

print("Charts written:")
for f in ["fig1_signature_size.png", "fig2_pubkey_size.png",
          "fig3_keygen_scaling.png", "fig4_latency.png"]:
    print(" -", f)
