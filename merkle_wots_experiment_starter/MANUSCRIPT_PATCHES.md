# Suggested manuscript edits (adapt section numbers to the current HTML/LaTeX source)

## Abstract: replace cross-scheme performance claim

> We evaluate endpoint encoding and verification costs in a prototype implementation and report separate tests of file-backed and SQLite-backed state-allocation prototypes. Same-host measurements of selected standardized signature implementations are included only as descriptive implementation references. Because the constructions, security assumptions, key lifetimes, and benchmark boundaries differ, these measurements are not security-equivalent performance comparisons.

Do not insert numerical claims until the raw data and scripts regenerate them.

## Implementation boundary

> The primary endpoint-mode benchmark uses a process-local index ledger. File-backed and SQLite-backed allocators are evaluated in separate state-management experiments; they are not integrated into the primary signing benchmark. Accordingly, the performance results do not measure end-to-end signing with durable state reservation.

## State safety and Proposition 1

> The no-reuse argument is conditional on unique index reservation, durable reservation before signature release, monotonic recovery, and the absence of bypassing or cloned signer instances. The abstract state model checks the stated transition rules; it is not a proof of implementation-level linearizability or resistance to restoration of an old storage snapshot. Under the tested configurations and fault scenarios, we observed no duplicate allocation.

Only retain the last sentence if the published tests actually pass and logs are supplied.

## Benchmark limitations

> Timing observations are clustered by Merkle tree and experimental session. We therefore report per-tree summaries and do not treat repeated timings from leaves of the same tree as independent experimental units. The reported measurements are descriptive for the tested host and software configuration.

## Bitcoin section

> The Bitcoin-related material is an illustrative serialization and size analysis. It does not establish acceptance by Bitcoin consensus rules unless a protocol-compatible transaction, witness/script, and validation path is executed against a specified implementation and test network or regtest node.

## KAT file issue

If `kat_128s.rsp` contains an HTTP `404: Not Found` response, remove it from the valid known-answer-test corpus. If relevant, document the retrieval failure separately; it is not a test vector.

## Persistent-state claims

Use separate rows for:
- abstract model exploration;
- file-backed allocator tests;
- SQLite concurrency tests;
- process crash/restart tests;
- external monotonic checkpoint tests;
- old-snapshot rollback tests.

For each row state exact test count, software version, fault model, observed result, and uncovered cases. Do not combine these into a single blanket “crash-safe” or “rollback-safe” claim.
