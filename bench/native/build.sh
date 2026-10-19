#!/usr/bin/env bash
# build.sh — reproduce the native cross-implementation benchmark.
#
# Requirements: clang, git, network access (to clone PQClean), python3.
# Layout: this script lives in bench/native/; it clones PQClean into _build/
# and writes ../../experiments/native_results.json (merged).
#
# Each standard scheme is built as a SEPARATE executable so that each links
# its own copy of PQClean/common (avoids duplicate-symbol conflicts).
set -euo pipefail

HERE="$(cd "$(dirname "$0")" && pwd)"
WORK="${1:-$HERE/_build}"
mkdir -p "$WORK"
PQ="$WORK/PQClean"

if [ ! -d "$PQ" ]; then
  echo "[fetch] PQClean -> $PQ"
  git clone --depth 1 https://github.com/PQClean/PQClean.git "$PQ"
fi
echo "[pqclean] commit $(git -C "$PQ" rev-parse --short HEAD)"

CC="${CC:-clang}"
CFLAGS="-O3 -std=c99 -I $PQ/common"
COMMON="$PQ/common/fips202.c $PQ/common/sha2.c $PQ/common/randombytes.c"

build_std () {
  local name="$1" dir="$2" wrap="$3"
  echo "[build] $name"
  # shellcheck disable=SC2086
  $CC $CFLAGS -I "$PQ/crypto_sign/$dir/clean" \
      "$HERE/bench_std.c" "$HERE/$wrap" "$PQ/crypto_sign/$dir/clean"/*.c $COMMON \
      -o "$WORK/bench_$name"
}

build_std mldsa44     ml-dsa-44                 wrap_mldsa44.c
build_std mldsa65     ml-dsa-65                 wrap_mldsa65.c
build_std sphincs128s sphincs-sha2-128s-simple  wrap_sphincs128s.c
build_std sphincs128f sphincs-sha2-128f-simple  wrap_sphincs128f.c

echo "[build] prototype"
# shellcheck disable=SC2086
$CC $CFLAGS "$HERE/bench_proto.c" $COMMON -o "$WORK/bench_proto"

echo "[run]"
"$WORK/bench_mldsa44"     > "$WORK/r_mldsa44.jsonl"
"$WORK/bench_mldsa65"     > "$WORK/r_mldsa65.jsonl"
"$WORK/bench_sphincs128f" > "$WORK/r_sphincs128f.jsonl"
"$WORK/bench_sphincs128s" > "$WORK/r_sphincs128s.jsonl"
"$WORK/bench_proto"       > "$WORK/r_proto.jsonl"

python3 - "$WORK" "$HERE/../../experiments/native_results.json" "$(git -C "$PQ" rev-parse --short HEAD)" <<'PY'
import json, os, sys
work, out_path, commit = sys.argv[1], sys.argv[2], sys.argv[3]
std=[]
for f in ["r_mldsa44.jsonl","r_mldsa65.jsonl","r_sphincs128s.jsonl","r_sphincs128f.jsonl"]:
    for line in open(os.path.join(work,f)):
        line=line.strip()
        if line: std.append(json.loads(line))
proto=[json.loads(l) for l in open(os.path.join(work,"r_proto.jsonl")) if l.strip()]
out={
  "environment": {
    "cpu":"Apple M1 (arm64)",
    "compiler":"Apple clang 17.0.0",
    "pqclean_commit":commit,
    "reps":31,
    "message_bytes":64,
    "timing":"clock_gettime(CLOCK_MONOTONIC)",
    "note":"Each scheme built as a separate executable linking its own PQClean/common copy; no CPU pinning; PQClean clean (portable C) implementations, not AVX2."
  },
  "standards": std,
  "prototype": proto
}
open(out_path,"w").write(json.dumps(out,indent=2))
print("[written]", out_path)
PY
