# Code and data audit (2026-10-19)

Scope: verify that every number in `paper/paper_jce.md` traces to the code
that produced it, before rewriting any table. Baseline commit `c54d85a`;
audit performed on the working tree that also contains the uncommitted
review-round changes. Tools: Python 3.11.9, Apple clang 17.0.0, arm64.

Principle: a claim is only as good as the artefact behind it. Where the
artefact did not exist or did not match the description, the table is marked
invalid rather than patched with prose.

---

## Findings

### A1 — The legacy prototype still shipped the checksum defect (fixed)

`src/wots.py` encoded the checksum as `base_w(checksum.to_bytes(32, "big"), LEN2)`.
Because the checksum occupies at most two bytes, the first 30 bytes are zero
and `base_w` returns `[0, 0, 0]` for every message.

Evidence: for a sample message the checksum is 554; the legacy encoder returns
`[0, 0, 0]`, the definition gives `[2, 2, 10]`.

Impact: signatures produced by `src/wots.py` (and by the legacy
`experiments/experiment_jce.py`) exposed the three checksum-chain secrets,
because the checksum digits were always zero.

Action: added `wots_checksum()`, which implements
`c_j = floor(C / w^(L2-1-j)) mod w`, and used it in both `sign` and `verify`.
Boundary self-tests cover `C ∈ {0, 1, 15, 16, 959, 960}` and a
checksum-chain advance. `tests/test_encoding.py` (E1–E8, w = 4/16/256)
cross-checks the production encoder against an independently written
reference encoder.

Note: the *repaired* variant in `experiments/experiment_submission.py` was
already correct; the defect was confined to the legacy prototype. Tables
derived from the legacy benchmark (`experiments/results_jce.json`) therefore
describe a construction with a broken checksum binding and must not be mixed
with repaired-variant tables.

### A2 — The C "port" was not the same construction (fixed)

`bench/native/bench_proto.c` used `MSS-LEAF-wots` / `MSS-NODE` domain tags and
`randombytes` key generation. The repaired Python variant uses `UMT-LEAF`
(with a `0x01` leaf tag), `UMT-NODE`, and deterministic derivation
`sk[i] = H("SUB-SK" || leaf_seed || i)` from
`leaf_seed = H("SUB-LEAF" || tree_seed || idx)`.

Impact: the C rows measured a different (structurally similar) construction,
so the Python/C comparison was cross-implementation even before considering
language.

Action: rewrote the C prototype as a structural mirror of
`experiment_submission.py`. Equality is now checked mechanically: for the same
tree seed, the Merkle root and leaf 0 are byte-identical at h = 1, 2, 4, 7, 8
(`bench_proto --root h` vs `experiment_submission.build_tree`).

### A3 — The C compact verifier did the chain work twice (fixed)

The compact path called `wots_rebuild_pk()` and then `wots_verify()`, each of
which performs one full pass over all 67 chains. The Python verifier performs
one pass and compares recovered endpoints directly.

Evidence: C compact verify was 0.246 ms against 0.131 ms explicit — the
recovered mode appeared *slower* than the explicit mode, which is impossible
for the same work minus an endpoint comparison. After the fix: 0.133 ms and
0.131 ms.

Impact: the earlier statement that "C recovered-mode verification is slower
than Python" was an artefact of the harness.

### A4 — The C signing loop rebuilt the tree (fixed)

`merkle_auth()` recomputed every tree level from the leaves on each call
(≈ n hashes at h = 7), while the Python `auth_path()` reads a precomputed
layer. The code comment claimed the rebuild matched "the Python harness"; it
did not.

Action: the tree is built once per key-generation iteration and all levels are
retained; signing reads the path from those layers, as Python does.

### A5 — Timing boundaries differed between Python and C (fixed)

Before: C verification operated on in-memory arrays (no parsing), Python
verification parsed serialized bytes; C signing included a tree rebuild;
key generation used a CSPRNG in C and hash derivation in Python.

Now both sides perform the same operations in the same order, from the same
serialized format, with the same 64-byte message. Python's byte-slice parsing
is reported separately as `parse_ms`, since C parses with pointer arithmetic.

### A6 — The published Python/C ratio mixed two codebases (withdrawn)

The paper's "1.5–1.7×" compared Python numbers taken from
`hash-based-signature-proposal` (h = 7, a different construction) against the
C port in this repository. `results_submission.json` contains only
verification timings — it never measured Python key generation or signing —
so the comparison could not have come from one codebase.

Action: measurement redone at h = 8, a configuration the repaired experiment
supports (`_parse_pk` accepts h ∈ {4, 8}). Result: **1.73× keygen, 1.82× sign,
1.93× explicit verify, 1.81× recovered verify**. The single "1.5–1.7×"
sentence is withdrawn and replaced by per-operation ratios.

### A7 — Chain-call accounting is exact (verified, no change)

Runtime instrumentation of `chain()` matches theory for every configuration:

| w | h | T_sign | T_verify | T_sign + T_verify | L(w−1) |
|---|---:|---:|---:|---:|---:|
| 4 | 4 | 204 | 195 | 399 | 399 |
| 16 | 4 | 510 | 495 | 1,005 | 1,005 |
| 256 | 4 | 4,590 | 4,080 | 8,670 | 8,670 |
| 16 | 8 | 435 | 570 | 1,005 | 1,005 |

C reports the same 510/495 at h = 8. `tests/test_chain_counts.py` enforces it.

### A8 — Serialized-length accounting is exact (verified, no change)

`tests/test_serialization.py` checks
`total = header/index + elements + endpoints(mode 0) + path` against the
serializer for all six configurations, and checks that the verifier accepts
exactly those lengths and rejects ±1 byte. Smallest configuration: 1,224 B
(1,216 payload + 8-byte header).

### A9 — State tests: two validity defects (fixed)

1. `reserve(crash_before_commit=True)` called `rollback()` and only then
   `os._exit(0)`. That tests explicit rollback, not recovery from process
   death. Removed the explicit rollback; SQLite now recovers the open
   transaction itself, and the test still passes.
2. Concurrent first-open raced: a second opener could observe the file after
   WAL had made it non-empty but before the tables existed, skip schema
   creation, and fail with `no such table: meta`. Schema creation is now
   unconditional (all statements are idempotent, `busy_timeout` serializes
   openers). With 8 processes × 12 keys and 16 threads × 12 keys: 12 unique
   reservations, 0 duplicates, 0 losses.

---

## What the audit changes in the paper

| Item | Before | After |
|---|---|---|
| Python/C gap | "1.5–1.7×" | 1.73 / 1.82 / 1.93 / 1.81× per operation |
| Prototype height | h = 7, 128 signatures | h = 8, 256 signatures |
| Compact verify (C) | 0.246 ms | 0.133 ms |
| Prototype signature size | 4,512 / 2,368 B (payload, h = 7) | 4,552 / 2,408 B serialized (4,544 / 2,400 payload, h = 8) |
| Chain counts | modelled only | modelled and measured, exact |
| Crash injection | rollback then exit | process death with an open transaction |
| Concurrent open | racy | fixed and re-tested |

## What the audit does not fix

- No security proof, no standard conformance; the fixed-prefix construction
  still does not inherit the FIPS 205 argument. State tests remain bounded by
  SQLite's process-crash semantics; power-loss durability is not claimed.
- Timings remain single-host, unpinned, and report ordering rather than exact
  microseconds.
- The legacy benchmark files (`results_jce.json`, `sphincs_benchmark.json`)
  are retained unchanged and remain labelled as legacy inputs.

---

## A10 — BIP-0360: no shared dataset, envelope now anchored to official vectors

**What was claimed vs. what existed.** Section 8 is explicitly an illustrative
accounting exercise, but before this check the repository never compared its
P2MR envelope against the vectors published with BIP-0360
(`bip-0360/ref-impl/common/tests/data/p2mr_construction.json`). The project's
Bitcoin numbers (4,325 / 4,461 / 135 bytes) were derived from stated
assumptions, not from that dataset, and the demo address was a `bc1z` prefix
followed by truncated hex.

**What the vectors contain.** Nine construction vectors (seven positive, two
negative), covering script tree → Merkle root, `scriptPubKey = 5220 || root`,
Bech32m addresses at witness version 2, and control blocks of `1 + 32m` bytes.
They contain secp256k1 `OP_CHECKSIG` leaves only; there are no post-quantum or
Winternitz vectors.

**What was added.** `third_party/bip360/` vendors the vectors with a
provenance note (BIP v0.12.1, commit `e7263a4cfe50`; vector file last changed
at `3e3e4347e277`; SHA-256 `cd02da0b…`). `tests/test_bip360_vectors.py`
recomputes the TapLeaf/TapBranch roots from the given scripts, checks each
`scriptPubKey`, decodes each Bech32m address (version 2, program = root), and
rebuilds each root from its control block. All seven positive and both
negative vectors pass. This is envelope-level evidence only; the repository's
`UMT-LEAF` roots are not expected to match any vector root, and the test says
so explicitly.

**A number that did not match.** The demo JSON was found storing
`wots_leaf_witness_bytes = 4460`, while the code recomputes 4,461 and the
paper's equation gives 4,461. The file was regenerated (4,461), and §8.3 now
distinguishes three quantities that had been conflated: 4,325 B prefix-free,
4,461 B with 134 item prefixes (stored), and 135 B for BIP-0360's own depth-1
`OP_CHECKSIG` example (reproduced by the demo's secp256k1 row).

---

## A11 — Reproducibility repair: retained sample re-measured under an installed interpreter

**Problem.** The retained timing sample recorded CPython 3.14.7. That release
exists, but it is not installed on this host, so the recorded environment
could not be re-created. Re-running the same deterministic workload under
CPython 3.14.3 gave per-configuration medians 1.12–1.19× slower across three
sessions (a single loaded run was up to 2.05× slower). The data were not
fabricated — the timings lie on the 41.667 ns `mach_absolute_time()` grid and
the deterministic workload reproduced byte for byte — but the absolute
numbers were not reproducible as recorded.

**What changed.**

1. `experiment_submission.py` now records `cpu_brand` (detected via `sysctl`,
   not asserted), `python_full`, `openssl`, `cpu_count_logical`, the
   `perf_counter` implementation/resolution, the 1/5/15-minute load average,
   a session label, and a UTC start time. It accepts `--out` and `--session`.
2. `run_submission_sessions.py` runs N independent sessions of the same
   deterministic workload, keeps every session file, and retains the session
   whose overall verification median is the median of the session medians
   (rule fixed before inspection; ties to the lower number).
3. Three sessions were run under CPython 3.14.3. Cross-session per-config
   medians varied by 5–17%; the retained session (`s2`) started at load
   average 8.5/10.1/11.5 on eight logical cores. The CPython 3.14.7 sample is
   archived as `results_submission_2026-10-19_py3147.json`.
4. `sync_paper_tables.py` renders Table 9, Table 9b, and the robust-statistics
   paragraph from the JSON, and refuses to write if the row count changed.
5. `tests/test_paper_numbers.py` parses the manuscript tables and fails on any
   mismatch with the retained data, including Table 11a.

**Effect on the paper.** Table 9 and Table 9b were regenerated from the new
sample; the robust-statistics paragraph now quotes the new ranges, maximum
paired difference, and explicit-slower shares. The conclusions are unchanged:
sizes are exact, and the paired explicit-versus-compact difference remains
small relative to the between-configuration differences. The new absolute
latencies are 10–35% higher than the archived sample, which is the
conservative direction and reflects the recorded load.

**Residual.** The host remains unpinned; a reviewer rerunning on an idle
machine should expect faster numbers, and the recorded range documents that.
