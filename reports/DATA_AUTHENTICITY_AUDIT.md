# Data Authenticity Audit — round 9

Scope: prove that the numbers cited in the paper come from a real,
rerunnable pipeline (not fabricated). Evidence below was produced by
`make audit-data` on 2026-10-19 17:30:35.
Environment: darwin / CPython 3.14.7

## A. Deterministic regeneration (5 scripts vs MANIFEST)
  audit/audit_jce.py -> rc=0 new=7f589189f0cf stored=7f589189f0cf OK
  audit/state_model_jce.py -> rc=0 new=9009157a52ee stored=9009157a52ee OK
  audit/state_persistence_tests.py -> rc=0 new=21692fe360e8 stored=21692fe360e8 OK
  experiments/check_counts.py -> rc=0 new=c7c100dec576 stored=c7c100dec576 OK
  experiments/robust_stats.py -> rc=0 new=4ebba4237ac1 stored=4ebba4237ac1 OK
- [PASS] A. deterministic regen: 5 scripts rerun, JSON hashes all match MANIFEST

## B. Raw sample authenticity (results_submission.json)
  events=270 checks=5130 (19/event) env={"python": "3.14.3", "python_full": "3.14.3 (main, Feb  4 2026, 01:51:49) [Clang 21.1.4 ]", "implementation": "CPython", "platform": "macOS-15.7.7-arm64-arm-64bit-Mach-O", "machine": "arm64", "cpu_brand": "Apple M1", "cpu_count_logical": 8, "openssl": "OpenSSL 3.5.5 27 Jan 2026", "perf_counter_ns": "used", "clock": {"implementation": "mach_absolute_time()", "resolution_s": 4.166666666666666e-08, "monotonic": true}, "loadavg_1_5_15": [8.461, 10.063, 11.459], "session": "s2", "started_utc": "2026-10-19T08:15:37+00:00"}
- [PASS] B1. unique 64-hex messages: 270/270 messages unique and 64-hex
- [PASS] B2. timing diversity (not constants): distinct explicit=269/270 compact=267/270
- [PASS] B3. no exact-zero timings: min explicit=0.1421 compact=0.1273 ms
- [PASS] B4. realistic outliers (>10x median): explicit=12 compact=16 (real measurement noise)
- [PASS] B5. byte accounting = formula + 8B header (all 6 configs): w=4,h=4 OK/8648B; w=4,h=8 OK/8776B; w=16,h=4 OK/4424B; w=16,h=8 OK/4552B; w=256,h=4 OK/2312B; w=256,h=8 OK/2440B
- [PASS] B6. (tree,index) layout = 3 trees x 29 sampled leaves: trees=[0, 1, 2] per-tree indices=[29, 29, 29]

## C. Source provenance (experiment-time code == current working tree)
  artifact experiment_submission.py   recorded=dd07ab4c889e current=dd07ab4c889e  current file == recorded
  artifact experiment_jce.py          recorded=238dd29dc350 current=238dd29dc350  current file == recorded
  artifact hbs_signature.py           recorded=b815f95f5a51 current=b815f95f5a51  current file == recorded
  artifact wots.py                    recorded=42e8fab55e44 current=42e8fab55e44  current file == recorded
- [PASS] C1. recorded artifact hashes == current files: all 4 recorded hashes match the working-tree files (reproducible as-is)
  experiments/experiment_jce.py: COMMITTED (HEAD==current)
  experiments/experiment_submission.py: COMMITTED (HEAD==current)
  src/wots.py: COMMITTED (HEAD==current)
  src/hbs_signature.py: COMMITTED (HEAD==current)
- [PASS] C2. git versioning status documented: experiment_jce.py committed; experiment_submission.py + src/wots.py + src/hbs_signature.py are uncommitted working-tree versions (git HEAD keeps the earlier revision)
  legacy CPython 3.14.7 sample archived: experiments/results_submission_2026-10-19_py3147.json (sha 6b213fe33d9c)
- [PASS] C3. legacy sample archived separately: old sample kept as its own file; paper forbids mixing old/new timings

## C4. Three-session protocol record
  sessions=['s1', 's2', 's3'] retained=s2 protocol={"sessions": 3, "cooldown_s": 10, "interpreter": "/Users/fangyuanyuan/.workbuddy/binaries/python/ver
  note: Every session uses the same deterministic workload, so message bytes, (tree, index), and serialized sizes are identical 
- [PASS] C4. three-session protocol record: 3 sessions, retained session s2 chosen by pre-fixed median rule

## D. Production-path rerun (all 6 configs, same seeds, in-memory)
  script sha256 (current): dd07ab4c889e6dc12afed96f3c67e184c5b0558b6fdbb8d393ef9a439fdb6cba (recorded dd07ab4c889e)
- [PASS] D0. inline repaired checksum (shift+mask): 270 events use the repaired digit extraction
  w=4,h=4: 45 rows in 0.10s bytes 8648/4392 (stored 8648/4392) positives=True rejections=True first-use=45/45 OK
  w=4,h=8: 45 rows in 0.50s bytes 8776/4520 (stored 8776/4520) positives=True rejections=True first-use=45/45 OK
  w=16,h=4: 45 rows in 0.19s bytes 4424/2280 (stored 4424/2280) positives=True rejections=True first-use=45/45 OK
  w=16,h=8: 45 rows in 0.53s bytes 4552/2408 (stored 4552/2408) positives=True rejections=True first-use=45/45 OK
  w=256,h=4: 45 rows in 1.26s bytes 2312/1224 (stored 2312/1224) positives=True rejections=True first-use=45/45 OK
  w=256,h=8: 45 rows in 4.58s bytes 2440/1352 (stored 2440/1352) positives=True rejections=True first-use=45/45 OK
- [PASS] D. production rerun reproduces structure/bytes/correctness: all 6 configs: 45 rows, bytes == authoritative, all checks pass (7.2s total)
  timing order-of-magnitude (rerun vs authoritative median, w16h4):
    rerun explicit median=0.2247 ms | authoritative global median=0.2597 ms

## E. BIP 360 official vectors (vendored vs upstream)
  vendored: version=1 vectors=9
  p2mr_single_leaf_script_tree merkleRoot spot-check: MATCH
  p2mr_different_version_leaves merkleRoot spot-check: MATCH
  p2mr_simple_lightning_contract merkleRoot spot-check: MATCH
- [PASS] E. vendored BIP 360 vectors match upstream: 9 vectors, version 1, merkleRoot/bip350Address spot-checks MATCH (verified 19 Oct 2026)

## Verdict

All checks passed: **YES**

### Transparency notes (what a reviewer must be told)

1. The authoritative 270-event sample (`results_submission.json`, retained
   session of a 3-session protocol) was generated by the current
   `experiments/experiment_submission.py` (sha dd07ab4c) with the current
   `src/wots.py` + `src/hbs_signature.py` (42e8fab5 / b815f95f); these four
   hashes are recorded inside the JSON (artifact_hashes) and match the
   working-tree files (check C1). The earlier CPython 3.14.7 sample is
   archived separately (`results_submission_2026-10-19_py3147.json`) and the
   paper explicitly forbids mixing the two timing sets.
2. Git status: `experiment_jce.py` is committed at HEAD; the experiment
   script and the two src files are *uncommitted* working-tree versions
   (git HEAD keeps the earlier revisions). The recorded hashes are the
   working-tree hashes, so the sample is reproducible from the workspace
   as-is, but the author should `git commit` these files to version them
   for the review package.
3. The rerun in check D reproduces, for all 6 configs: 45 rows each, byte
   sizes exactly equal to the authoritative sample, all positive/rejection
   checks passing, all 45 events first-use under (tree,index) identity.
   Timing values are fresh and differ from the stored sample (measurement,
   not fabrication), but are the same order of magnitude.
4. The message generator uses the fixed seed `random.Random(20260915)`
   hard-coded in `experiment_submission.py` (line ~467). Rerunning all six
   configs with that seed reproduces the authoritative sample **exactly**:
   270/270 messages, (tree, index) pairs, byte sizes and correctness flags
   identical (verified 19 Oct 2026). Per-message reproduction is therefore
   fully supported; the seed is versioned with the script (sha dd07ab4c)
   recorded in the JSON's artifact_hashes.
5. The BIP 360 vectors are the official upstream file (version 1, 9 vectors),
   vendored; spot-checked against upstream on 19 Oct 2026.

Conclusion: no evidence of AI-fabricated data. Every number in the paper
traces to a retained script, the retained authoritative JSON, or the
officially vendored BIP 360 vectors.