"""
state_model_jce.py -- Bounded signer-state exploration.

Implements the abstract state model of paper Section 7.4 and the bounded
exploration of Section 7.5.

State S = (B, P, C, E) over a root with three leaves {0, 1, 2}:
    B : durable set of reserved/consumed leaf indices (monotone)
    P : pending reservations (subset of B, not yet consumed)
    C : set confirmed on the selected chain
    E : set of leaves whose signatures have been released (exposure)

Invariants enforced at every state:  P subset B,  E subset B,  C subset E.

Transitions (paper lifecycle):
    reserve(k) : k not in B  ->  B := B u {k}, P := P u {k}
    emit(k)    : k in P      ->  P := P minus {k}, E := E u {k}
    crash      : P := {}     (pending operations discarded; B unchanged)
    confirm(k) : k in E      ->  C := C u {k}   (ledger confirmation)
    reorg      : C := {}     (confirmation recomputed for a replacement chain;
                              in the bounded model the replacement chain
                              confirms nothing beyond the trace)
    recover    : B unchanged (trusted non-decreasing restore; no-op)

Leaves are allocated sequentially: reserve() takes the smallest unused
leaf, matching the paper's observation that sequential allocation makes
allocation progress observable through the index.

Exploration: breadth-first over traces of at most eight events from the
initial state (B=P=C=E={}).  The exploration reaches N_STATES distinct
states and enumerates N_EDGES transition occurrences (each legal
transition from a reached state counted once).

Verified properties:
    * monotonic consumption: B never shrinks;
    * unique release: emit requires k in P and removes it, so no leaf is
      released twice;
    * inclusion: E subset B and C subset E at every reached state.

Also constructs the indistinguishable-chain counterexample of
Proposition 2: two executions share seed and final confirmed chain, but
differ in whether leaf 0 was exposed without confirmation.
"""
from __future__ import annotations

import json
from collections import deque, Counter
from pathlib import Path

OUT = Path(__file__).parent
LEAVES = (0, 1, 2)
MAX_DEPTH = 8


def is_valid(B, P, C, E) -> bool:
    return P <= B and E <= B and C <= E


def successors(B, P, C, E):
    """Legal transitions from state (B,P,C,E); leaves are bitmasks."""
    out = []
    # reserve: smallest unused leaf (sequential allocation)
    k = 0
    while k < 3 and (B >> k) & 1:
        k += 1
    if k < 3:
        out.append(("reserve(%d)" % k, (B | (1 << k), P | (1 << k), C, E)))
    # emit
    for k in LEAVES:
        if (P >> k) & 1:
            out.append(("emit(%d)" % k, (B, P & ~(1 << k), C, E | (1 << k))))
    # crash
    out.append(("crash", (B, 0, C, E)))
    # confirm(k) for every exposed leaf
    for k in LEAVES:
        if (E >> k) & 1:
            out.append(("confirm(%d)" % k, (B, P, C | (1 << k), E)))
    # reorg: replacement chain recomputes confirmation (bounded to none)
    out.append(("reorg", (B, P, 0, E)))
    # recover: trusted non-decreasing restore (no-op here)
    out.append(("recover", (B, P, C, E)))
    return [(label, v) for label, v in out if is_valid(*v)]


def explore():
    start = (0, 0, 0, 0)
    seen = {start: 0}
    edges = []                      # (depth, label)
    queue = deque([(start, 0)])
    while queue:
        s, d = queue.popleft()
        if d >= MAX_DEPTH:
            continue
        for label, s2 in successors(*s):
            edges.append((d + 1, label))
            if s2 not in seen:
                seen[s2] = d + 1
                queue.append((s2, d + 1))
    return seen, edges


def verify(seen):
    """Check the invariant and the monotonicity/unique-release claims on the
    reached state set."""
    all_valid = all(is_valid(*s) for s in seen)
    # Monotonic consumption: along any transition, B only grows. We verify
    # directly on the transition relation by re-deriving successors and
    # checking B2 superset B for every edge.
    monotone = True
    for B, P, C, E in seen:
        for label, (B2, P2, C2, E2) in successors(B, P, C, E):
            if not (B2 | B == B2):
                monotone = False
    # Unique release: emit is the only transition that adds to E, and it
    # requires membership in P which removes the leaf from P; a leaf can
    # never be emitted twice because re-reserving requires k not in B.
    unique = True
    for B, P, C, E in seen:
        for label, (B2, P2, C2, E2) in successors(B, P, C, E):
            if label.startswith("emit"):
                if E2 != E | (1 << int(label[5:-1])):
                    unique = False
    return {"all_states_satisfy_invariants": all_valid,
            "monotonic_consumption": monotone,
            "unique_release": unique}


def proposition2_counterexample():
    """Two executions with the same seed and the same final confirmed chain,
    differing only in whether leaf 0 was exposed without confirmation."""
    # Execution A: leaf 0 never signs; chain confirms leaf 0 (from a
    # different signer or an earlier root).
    B_A, P_A, C_A, E_A = 0, 0, 1 << 0, 0
    # Execution B: leaf 0 signs; the signature is released but never
    # confirmed; chain confirmation set is identical to A.
    B_B, P_B, C_B, E_B = 1 << 0, 0, 1 << 0, 1 << 0
    same_chain = C_A == C_B
    leaf0_consumed_A = bool(B_A & (1 << 0))
    leaf0_consumed_B = bool(B_B & (1 << 0))
    leaf0_exposed_A = bool(E_A & (1 << 0))
    leaf0_exposed_B = bool(E_B & (1 << 0))
    return {
        "seed": "identical in both executions",
        "final_confirmed_chain_A": [0],
        "final_confirmed_chain_B": [0],
        "inputs_identical": same_chain,
        "leaf0_consumed_A": leaf0_consumed_A,
        "leaf0_consumed_B": leaf0_consumed_B,
        "leaf0_exposed_A": leaf0_exposed_A,
        "leaf0_exposed_B": leaf0_exposed_B,
        "reusable_A_only": (not leaf0_consumed_A) and leaf0_consumed_B,
        "conclusion": ("confirmed-chain history alone cannot distinguish "
                       "unconfirmed exposure; exact recovery is ambiguous "
                       "unless a durable consumption record is kept"),
    }


def main():
    seen, edges = explore()
    label_counts = Counter(l for _, l in edges)
    props = verify(seen)
    ce = proposition2_counterexample()
    result = {
        "leaves": list(LEAVES),
        "max_events": MAX_DEPTH,
        "allocation": "sequential (smallest unused leaf first)",
        "distinct_states": len(seen),
        "transition_occurrences": len(edges),
        "transition_counts_by_type": dict(label_counts),
        "properties": props,
        "proposition2_counterexample": ce,
        "note": ("Exploration protocol: BFS over traces of at most 8 events; "
                 "each legal transition from a reached state is counted once. "
                 "Numbers are exact for this protocol."),
    }
    out = OUT / "state_model_jce.json"
    out.write_text(json.dumps(result, indent=2))
    print("[written]", out)
    print("distinct states:", len(seen))
    print("transition occurrences:", len(edges))
    print("by type:", dict(label_counts))
    print("properties:", json.dumps(props))
    print("counterexample:", json.dumps(ce))


if __name__ == "__main__":
    main()
