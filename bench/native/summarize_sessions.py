"""summarize_sessions.py — turn native_results_sessions.json into markdown.

Prints cross-session median with the [min-max] range across per-session
medians, plus the spread as a percentage of the median.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
path = Path(sys.argv[1]) if len(sys.argv) > 1 else HERE.parent / "native_results_sessions.json"
d = json.loads(path.read_text())
summary = d["summary"]


def fmt(entry, metric):
    if metric not in entry:
        return "-"
    e = entry[metric]
    return f'{e["median"]:.3f} [{e["min"]:.3f}-{e["max"]:.3f}] ({e["spread_pct"]:.0f}%)'


print("## Standards\n")
print("| Scheme | keygen ms | sign ms | verify ms | sig B |")
print("|---|---:|---:|---:|---:|")
for k, e in summary.items():
    if "scheme" in e:
        print(f'| {e["scheme"]} | {fmt(e,"keygen_ms")} | {fmt(e,"sign_ms")} | '
              f'{fmt(e,"verify_ms")} | {e.get("sig","-")} |')

print("\n## Prototype (h=7)\n")
print("| Kind | compact | keygen ms | sign ms | verify ms | sig B |")
print("|---|---|---:|---:|---:|---:|")
for k, e in summary.items():
    if "kind" in e and e.get("h") == 7:
        print(f'| {e["kind"]} | {e["compact"]} | {fmt(e,"keygen_ms")} | '
              f'{fmt(e,"sign_ms")} | {fmt(e,"verify_ms")} | {e.get("sig_bytes","-")} |')
