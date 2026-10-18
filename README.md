# Implementation Auditing of Hash-Based Signatures — Reproducible Artifacts

Companion artifact package for the manuscript

> **Implementation Auditing of Hash-Based Signatures: Encoding Correctness, Payload Accounting, and State Recovery Risks**
> (revised 18 October 2026)

This repository contains the executable audit scripts, experiment harnesses,
raw JSON results, figures, and the final manuscript HTML that support the
paper's claims. The study is an **implementation audit and reproducibility
study of a fixed-prefix Winternitz-style research prototype**. The prototype is
a research construction, not a standards-conformant implementation; nothing in
this repository establishes cryptographic security, a security level, or
conformance to WOTS+, XMSS, or LMS.

## Repository layout

```
audit/        Checksum-audit and bounded state-model scripts and outputs
charts/       Figure/render pipeline (make_submission_figure.py, render_jce.py, ...)
experiments/  Submission experiment harness, SPHINCS+ benchmark, raw JSON results
figures/      figure3.png/svg (paper Figure 3) and path-traversal data
paper/        paper_jce.html (final manuscript), paper_jce.md (source text)
src/          Core prototype implementation (wots.py, hbs_signature.py, ...)
third_party/  SPHINCS+ reference implementation used for same-machine baselines
ARTIFACT_MANIFEST.txt   SHA-256 digest of every tracked artifact
```

## Requirements

- Python ≥ 3.10 (tested with CPython 3.14.7, macOS 15.7.7, arm64)
- `matplotlib` (only for `make_submission_figure.py`)
- `mistune` (only for `render_jce.py` markdown → HTML)
- `cc`/`gcc` with a C99 compiler (only for the SPHINCS+ reference baseline)

## Reproduce

Run from the repository root:

```bash
# 1. Checksum-encoding audit and chain-call counts (paper Tables 2, 4, 5)
python3 audit/audit_jce.py            # -> audit/audit_jce.json

# 2. Bounded signing-state model (paper Section 7.5; 73 states / 355 transitions)
python3 audit/state_model_jce.py      # -> audit/state_model_jce.json

# 3. Submission experiment: 270 paired samples, 5,130 functional checks
#    (paper Tables 8, 9; serialized sizes 2,312-8,648 B explicit, 1,224-4,392 B compact)
python3 experiments/experiment_submission.py   # -> experiments/results_submission.json

# 4. Figure 3 (paper Figure 3)
python3 charts/make_submission_figure.py       # -> figures/figure3.png/svg, figures/path_traversal.json

# 5. SPHINCS+ same-machine reference timings (paper Table 7)
#    (requires building third_party/sphincsplus-ref first)
cd third_party/sphincsplus-ref && make clean && make
cd ../..
python3 experiments/run_sphincs_benchmark.py  # -> experiments/sphincs_benchmark.json

# 6. Manuscript rendering (optional; the committed paper_jce.html is authoritative)
python3 charts/render_jce.py --from-markdown paper/paper_jce.md   # -> paper/paper_jce.html
```

## Result files

| File | Contents |
| --- | --- |
| `experiments/results_submission.json` | 270 raw samples (3 trees × 15 leaves × 6 configs), environment record, per-config aggregates, SHA-256 of the four core scripts |
| `experiments/results_jce.json` | Legacy (pre-fix) timing aggregates, used only as historical context in Table 6 |
| `experiments/sphincs_benchmark.json` | SPHINCS+-128s / -128f reference timings (100 rounds, CLOCK_MONOTONIC) |
| `audit/audit_jce.json` | Checksum-distribution tables, chain-call counts, KAT reproduction |
| `audit/state_model_jce.json` | Bounded state model: 73 states, 355 transitions, invariant checks, Proposition 2 counterexample |
| `figures/path_traversal.json` | Authentication-path traversal timing data (paper Table 9) |
| `experiments/kat_wots.json` | Local regression vector for the defective algorithm (not a standards KAT) |

## SPHINCS+ reference implementation

`third_party/sphincsplus-ref/` is the reference implementation distributed by
the SPHINCS+ project (upstream repository: `sphincsplus/sphincsplus`), kept
under its original license (`LICENSE` in that directory). One modification is
present: `benchmark_timing.c` no longer prints the `PARAMS` macro via a
`%s`-format printf (the macro cannot be stringified portably). The timing
harness uses `CLOCK_MONOTONIC` and 100 rounds.

## Integrity

`ARTIFACT_MANIFEST.txt` lists the SHA-256 digest and byte size of every tracked
artifact. The committed `paper/paper_jce.html` was generated from the same
numbers that these scripts reproduce.

## License

The code and materials in this repository (excluding `third_party/`) are
released under the MIT License, see `LICENSE`. The SPHINCS+ reference code
under `third_party/` remains under its own license terms.

## Disclaimer

This is a research prototype. The checksum defect, payload numbers, and state
recovery results describe this construction and its repaired variant under
explicitly defined experimental wire formats. They do not imply security,
performance, or size superiority over any standardized signature scheme.
