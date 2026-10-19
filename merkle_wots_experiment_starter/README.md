# Merkle-Aggregated Winternitz Signatures: reproducibility starter

This package is a **starter harness**, not a reimplementation of the paper's cryptographic construction.
It provides:
1. a microbenchmark harness for comparing two endpoint-encoding paths;
2. paired, tree-clustered summary statistics;
3. a minimal SQLite monotonic index allocator with concurrency tests;
4. manuscript wording and a reproducibility checklist.

Before publishing, replace the synthetic endpoint functions with calls to the *actual implementation* and record the exact commit, dependencies, host, and raw output. Do not describe these tests as a proof of cryptographic security or production crash safety.

## Requirements

- Python 3.10+
- Standard library only

## Run

```bash
python -m unittest discover -s tests -v
python experiments/benchmark_endpoint_modes.py --trees 20 --leaves 15 --repeats 30 --warmups 100 --out results/endpoint_raw.csv
python experiments/analyze_paired.py results/endpoint_raw.csv --out results/endpoint_summary.json
python experiments/state_allocator_stress.py --workers 8 --per-worker 100 --db results/state_test.sqlite
```

The benchmark's `explicit` and `recovered` functions are deliberately synthetic. They illustrate the measurement protocol only. Replace them with real scheme functions before using results in a manuscript.

## Suggested repository layout for the actual submission

```text
paper/
src/
tests/
  unit/
  state/
  crash/
  integration/
experiments/
  config/
  scripts/
  raw/
  processed/
  figures/
environment/
logs/
README.md
Makefile
```

## Reproducibility rules

- Keep raw measurements; never publish only plotted averages.
- Record the git commit, Python version, OS, CPU, compiler and flags if native code is used.
- Randomize or interleave benchmark mode order.
- Treat independent trees/sessions—not every leaf timing—as the statistical unit where observations are clustered.
- Separate custom implementation benchmarks from ML-DSA/SLH-DSA reference measurements.
- If testing an old database snapshot, use an external monotonic checkpoint or explicitly exclude rollback from the threat model.
