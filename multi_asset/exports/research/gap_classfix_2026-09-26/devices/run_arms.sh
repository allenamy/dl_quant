#!/bin/bash
# Run every replay arm of ACCEPTANCE_gap_classfix_2026-09-26 §2 sequentially (sandboxed, production read-only), then the judge.
# usage: run_arms.sh <replay root> <patched tree> <receipt out>
set -uo pipefail
ROOT=${1:?root}; TREE=${2:?tree}; OUT=${3:?receipt}; D=$(cd "$(dirname "$0")" && pwd -P)
mkdir -p "$ROOT"
one() { local code=$1 arm=$2 A=$3; local sbr="$ROOT/${code}_${arm}"; mkdir -p "$sbr"
  echo "=== $(date -u +%FT%TZ) $code $arm $A"; bash "$D/gap_fix_replay.sh" "$A" - "$sbr" "$arm" "$code" "$TREE" 2>&1 | tail -4; }
for A in 1790380800 1790395200 1790409600; do one current base $A; one patched base $A; done
for arm in gap1 gap2 gap6 gap7 bridge1 bridge2 bridge6 bridge7 x1 x2 x3 xref; do one current $arm 1790409600; done
for arm in gap1 gap2 gap6 gap7 x1 x2 x3; do one patched $arm 1790409600; done
echo "=== $(date -u +%FT%TZ) judge"
~/wide_shadow/venv/bin/python "$D/gap_fix_judge.py" "$ROOT" --out "$OUT"; echo "JUDGE_RC=$?"
