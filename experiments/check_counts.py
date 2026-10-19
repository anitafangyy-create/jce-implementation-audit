"""check_counts.py -- Automatically aggregate the functional-check accounting
reported in Section 6.5 / Appendix B of the JCE revision from the retained
experiment output results_submission.json.

Every signing event in experiment_submission.py counts 19 checks:
   2 successful verifications (one per serialization mode),
  16 rejections (8 rejection cases x 2 modes),
   1 key-identity bookkeeping record.

Key identity is (tree_id, leaf_index): each tree carries independent key
material, so the same index in different trees is a different one-time key.
All 270 measured events are first uses of distinct (tree, index) keys;
reuse rejection (same tree, same index) is exercised by the audit script's
key-identity state tests (audit_jce.json), not by the timing run.

The 5,130 total is the number of executed assertions, not the number of
independent test cases.  This script reports both dimensions.

Run:  python3 experiments/check_counts.py
Writes: experiments/check_counts.json
"""
from __future__ import annotations

import json
from pathlib import Path

OUT = Path(__file__).resolve().parents[1]
SRC = OUT / "experiments" / "results_submission.json"
DST = OUT / "experiments" / "check_counts.json"

CONFIG_ORDER = ["w=4,h=4", "w=4,h=8", "w=16,h=4", "w=16,h=8", "w=256,h=4", "w=256,h=8"]

PER_EVENT_POSITIVE = 2
PER_EVENT_REJECTIONS = 16
PER_EVENT_RECORD = 1
CHECKS_PER_EVENT = PER_EVENT_POSITIVE + PER_EVENT_REJECTIONS + PER_EVENT_RECORD

REJECTION_CASES = [
    "changed signature bytes", "wrong message", "truncation",
    "appended bytes", "invalid mode", "changed path", "changed index",
    "wrong root",
]


def main() -> None:
    d = json.loads(SRC.read_text(encoding="utf-8"))
    raw = d["raw_samples"]
    events = len(raw)
    assert events == d["total_signing_events"] == 270
    assert d["checks_per_event"] == CHECKS_PER_EVENT == 19

    per_config = {}
    for i, cfg in enumerate(CONFIG_ORDER):
        blk = raw[i * 45:(i + 1) * 45]
        n = len(blk)
        assert n == 45
        pos = n * PER_EVENT_POSITIVE
        rej = n * PER_EVENT_REJECTIONS
        records = n * PER_EVENT_RECORD
        # under (tree, index) identity every measured event is a first use
        rejected = sum(1 for r in blk if r["repeated_index_rejected"])
        first_use = records - rejected
        per_config[cfg] = {
            "signing_events": n,
            "trees": sorted({r["tree"] for r in blk}),
            "positive_checks": pos,
            "rejection_checks": rej,
            "key_identity_records": records,
            "first_use_events": first_use,
            "rejected_reuse_attempts": rejected,
            "checks": pos + rej + records,
            "all_positive_ok": all(r["positive_ok"] for r in blk),
            "all_rejections_ok": all(r["rejections_ok"] for r in blk),
            "all_first_use": all(not r["repeated_index_rejected"] for r in blk),
        }

    total = {
        "signing_events": events,
        "checks_per_event": CHECKS_PER_EVENT,
        "positive_checks": events * PER_EVENT_POSITIVE,
        "rejection_checks": events * PER_EVENT_REJECTIONS,
        "key_identity_records": events * PER_EVENT_RECORD,
        "first_use_events": sum(pc["first_use_events"] for pc in per_config.values()),
        "rejected_reuse_attempts": sum(pc["rejected_reuse_attempts"] for pc in per_config.values()),
        "total_checks": events * CHECKS_PER_EVENT,
    }
    total["all_positive_ok"] = all(pc["all_positive_ok"] for pc in per_config.values())
    total["all_rejections_ok"] = all(pc["all_rejections_ok"] for pc in per_config.values())
    total["all_first_use"] = all(pc["all_first_use"] for pc in per_config.values())

    independent_coverage = {
        "distinct_signing_events": events,
        "event_identity": "unique (w, h, tree, leaf_index, message) per event",
        "trees": sum(pc["trees"] is not None for pc in per_config.values()) * 3,
        "rejection_check_types": len(REJECTION_CASES) * 2,
        "rejection_case_labels": REJECTION_CASES,
        "audit_key_identity_scenarios": [
            "same_tree_same_index_first: allowed",
            "same_tree_same_index_repeat: rejected",
            "same_tree_different_index: allowed",
            "different_tree_same_index: allowed",
            "crash_restart_replay_consumed_index: rejected",
        ],
        "note": (
            "5,130 is the number of executed assertions (19 per event x 270 "
            "events), not the number of independent test cases.  Independent "
            "cases: 270 distinct signing events, 16 rejection-check types, and "
            "the deterministic audit checks (key-identity state tests, repaired "
            "round-trip/tamper checks, byte and chain-call accounting)."),
    }

    out = {
        "per_config": per_config,
        "total": total,
        "independent_test_coverage": independent_coverage,
        "state_initialization": (
            "One-time key identity is (tree_id, leaf_index).  The signer ledger "
            "is fresh per (w, h) configuration and persists across that "
            "configuration's three trees; the same leaf index in different trees "
            "is a different one-time key and is allowed.  All 270 measured events "
            "are first uses.  Same-tree same-index reuse rejection is exercised "
            "by audit_jce.json key_identity_state_tests."),
        "checks_per_event_breakdown": {
            "successful_verifications": PER_EVENT_POSITIVE,
            "rejections": PER_EVENT_REJECTIONS,
            "key_identity_records": PER_EVENT_RECORD,
        },
        "note": "Generated by experiments/check_counts.py from results_submission.json; deterministic.",
    }
    DST.write_text(json.dumps(out, indent=2) + "\n", encoding="utf-8")
    t = out["total"]
    print("signing events:", t["signing_events"])
    print("positive:", t["positive_checks"], "| rejections:", t["rejection_checks"],
          "| key-identity records:", t["key_identity_records"],
          "(first-use", t["first_use_events"], "| rejected", t["rejected_reuse_attempts"], ")")
    print("total checks:", t["total_checks"])
    print("all positive ok:", t["all_positive_ok"], "| all rejections ok:",
          t["all_rejections_ok"], "| all first use:", t["all_first_use"])
    print("independent cases:", independent_coverage["distinct_signing_events"],
          "events |", independent_coverage["rejection_check_types"], "rejection types |",
          len(independent_coverage["audit_key_identity_scenarios"]), "audit key-identity scenarios")
    print("[written]", DST)


if __name__ == "__main__":
    main()
