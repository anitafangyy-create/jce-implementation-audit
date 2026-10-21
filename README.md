# HBS-PQ: A Hash-Based Post-Quantum Signature Research Prototype

HBS-PQ is a research prototype implementing **Lamport one-time signatures (OTS), Winternitz one-time signatures (WOTS+), and Merkle-tree-based aggregation** from scratch. It uses a fixed-prefix construction and is intended for reproducible engineering research on implementation auditing, signature-payload accounting, verification costs, and signer-state management.

**Security and standards disclaimer:** HBS-PQ does not claim security equivalence to NIST FIPS 204 (ML-DSA) or FIPS 205 (SLH-DSA). Sizes reported for standardized schemes are cited only as published reference values, not as evidence of security equivalence. The research motivation includes the post-quantum signature scripting path contemplated by **BIP-0360 (Pay-to-Merkle-Root, P2MR)**.

---

## Repository Structure

| Directory | Contents |
|---|---|
| `src/` | Core cryptographic implementations: `hbs_signature.py` (Lamport OTS and Merkle trees), `wots.py` (WOTS+), and `wots_bench.c` (C benchmark). |
| `experiments/` | Experiment scripts, including `experiment_jce.py`, `experiment_submission.py`, `make_kat.py`, `bip360_demo.py`, and `run_sphincs_benchmark.py`; experimental results and vectors, including `results*.json`, `kat_wots.json`, `bip360_demo.json`, and `kat_128s.rsp`. |
| `bench/native/` | Native C benchmarks under matched conditions: PQClean ML-DSA/SLH-DSA implementations and a C implementation of the repaired prototype. Includes `build.sh`, `run_sessions.py`, `bench_proto.c`, and `bench_std.c`. |
| `state_demo/` | Durable-state allocator using a hash-chain log, an atomic head, a high-water mark, and `flock`; includes six fault-injection tests in `test_state.py`. |
| `charts/` | Chart-generation and rendering scripts: `make_charts_jce.py`, `make_submission_figure.py`, `make_native_figure.py`, and `render_jce.py`. |
| `figures/` | Generated figures, including `fig_jce_*`, `fig_submission.*`, `figure3.*`, and `fig_native_benchmark.png`. |
| `tests/` | Independent tests for encoding boundary cases (E1–E8), hash-chain invocation counts, and serialization-length invariants. |
| `audit/` | Prototype audit (`audit_jce.py/json`), abstract state model (`state_model_jce.py/json`), and SQLite state tests (`state_persistence_tests.py/json`). |
| `reports/` | Research and review documents, including `RESEARCH_REPORT.md` and `CODE_AUDIT.md`. |
| `third_party/` | Third-party reference source code, including `bip360/` and official BIP 360 P2MR vectors vendored for validation by `tests/test_bip360_vectors.py`. |
| `LICENSE` | MIT license. |

---

## Data Flow

```text
experiments/experiment_*.py
        |
        +----> experiments/results*.json
        |
experiments/make_kat.py
        |
        v
experiments/kat_wots.json
        |
        v
audit/audit_jce.py
        |
        v
audit/audit_jce.json

charts/make_charts_jce.py
        |
        +---- reads experiments/*.json
        +---- reads audit/audit_jce.json
        |
        v
figures/fig_jce_*.png

charts/make_submission_figure.py
        |
        +---- reads experiments/results_submission.json
        |
        v
figures/figure3.*
        |
        v
charts/render_jce.py
        |
        v
paper/paper_jce.html
        (images embedded as Base64 for offline viewing)
```

---

## Quick Start

All scripts locate the repository root relative to their own file paths using `Path(__file__).resolve().parents[1]`. They can therefore be invoked from any working directory; changing to the repository root first is not required.

### Recommended: Reproduce the checks

```bash
# Main reproducibility entry points
make test          # 11 stages: tests, audits, state checks,
                   # operation counts, robustness statistics, and rendering
make audit-data    # Data-integrity audit: 14 checks, deterministic output
```

### Core self-tests

These commands use only the Python 3 standard library.

```bash
python3 src/wots.py
python3 src/hbs_signature.py
```

### Known-answer tests, audits, and state models

These commands also use only the Python 3 standard library.

```bash
# Generate WOTS+ known-answer test vectors
python3 experiments/make_kat.py

# Reproduce the implementation audit
python3 audit/audit_jce.py

# Check the abstract state model (73 states, 355 transitions)
python3 audit/state_model_jce.py

# Run six durable-state fault-injection tests
python3 state_demo/test_state.py

# Run SQLite transaction, concurrency, and rollback tests
python3 audit/state_persistence_tests.py
```

### Benchmarks

Benchmark scripts overwrite their corresponding `results*.json` files. Timing results may vary between runs.

```bash
# Submission-version paired experiment (may take longer)
python3 experiments/experiment_submission.py

# Build and run the native C benchmark.
# This requires network access to clone PQClean.
python3 bench/native/build.sh
```

### Figures and manuscript rendering

Figure generation requires `matplotlib` and `numpy`.

```bash
python3 charts/make_submission_figure.py
```

Manuscript rendering requires `mistune`.

```bash
# Render paper/paper_jce.md to paper/paper_jce.html
python3 charts/render_jce.py
```

---

## Dependencies

| Scripts or components | Dependencies |
|---|---|
| `src/*`, `experiments/*`, `audit/*` | Python 3 standard library only, except where otherwise noted above. |
| `experiments/run_sphincs_benchmark.py` | A C99 compiler (`cc` or `gcc`); automatically compiles `third_party/sphincsplus-ref`. |
| `charts/make_charts_jce.py`, `charts/make_submission_figure.py` | `matplotlib`, `numpy`. |
| `charts/render_jce.py` | `mistune`. |
| `bench/native/build.sh` | A C compiler and network access to clone PQClean. |

Install the optional plotting and rendering dependencies with:

```bash
python3 -m pip install matplotlib numpy mistune
```

---

## Notes and Known Issues

1. **Two naming conventions for manuscript Figure 3.** Existing generated files include `figures/fig_submission.png`, `.pdf`, and `.eps`. The current `charts/make_submission_figure.py` script instead writes `figures/figure3.png`, `figures/figure3.svg`, and `figures/path_traversal.json`. These outputs refer to the same manuscript figure.

2. **Benchmark outputs may change between runs.** Experiment scripts overwrite their corresponding `results*.json` files, and timing measurements vary with runtime conditions and randomness. By contrast, KAT generation, audits, and state-model checks use fixed seeds and produce deterministic outputs. The retained reference samples and three-session records are stored in `experiments/results_submission.json` and `experiments/results_submission_sessions.json`.

3. **Excluded local directories.** `archive/` contains historical backups. `merkle_wots_experiment_starter/` contains synthetic example code from an external review template and is explicitly not a real algorithm implementation. Neither directory is included in the public repository or used by its validation workflows.

4. **Artifact manifest.** `ARTIFACT_MANIFEST.txt` is a SHA-256 manifest covering 88 artifacts, including code, data, tests, and reports cited by the manuscript. `make test` checks the manifest against the working tree.

5. **Unavailable SPHINCS+ response file.** `experiments/kat_128s.rsp` contains a residual `404: Not Found` response from a failed download. This issue is disclosed in Section 4.2 of the manuscript. The file is not used by any validation workflow. The actual local regression vectors are in `experiments/kat_wots.json`.

6. **Research prototype only.** The prototype is intended for research and educational use. It does not implement domain separation or constant-time hardening and **must not be used directly in production**. No cryptographic security level is assigned to the construction. See Sections 2.2, 7.1, and 10 of `paper/paper_jce.md`, and `reports/RESEARCH_REPORT.md`, for further details.

---

## Citation and License

Please cite this artifact using `CITATION.cff`. The author names and affiliations in that file must be completed before submission.

The code and documentation are distributed under the **MIT License**; see `LICENSE`. Third-party standards, specifications, and reference implementations cited by the manuscript—including RFCs, NIST publications, BIPs, and PQClean—remain subject to their respective owners' terms and licenses.
