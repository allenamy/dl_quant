#!/bin/bash
# run 4 (2026-09-27, arm64 host re-verification after the Intel -> arm64 migration): EVERY arm of runs 1-3 rerun FRESH on this host, both codes,
# tree GAP4 — no symlinks to x86 outputs (run 3 reused run-1 current arms). Arm list = run_arms.sh ∪ run_arms2.sh ∪ run_arms3.sh. Then the same judge.
# usage: run_arms4_arm64.sh <run4 root> <tree GAP4> <receipt out>
set -uo pipefail
ROOT=${1:?}; TREE=${2:?}; OUT=${3:?}; D=$(cd "$(dirname "$0")" && pwd -P)
[ -e "$ROOT" ] && { echo "REFUSED root exists: $ROOT"; exit 2; }
mkdir -p "$ROOT"
echo "HOST $(uname -m) $(~/wide_shadow/venv/bin/python -c 'import platform,numpy,scipy,pandas,lightgbm;print(platform.python_version(),numpy.__version__,scipy.__version__,pandas.__version__,lightgbm.__version__)')"
one() { local code=$1 arm=$2 A=$3; local sbr="$ROOT/${code}_${arm}"; mkdir -p "$sbr"
  echo "=== $(date -u +%FT%TZ) $code $arm $A"; bash "$D/gap_fix_replay.sh" "$A" - "$sbr" "$arm" "$code" "$TREE" 2>&1 | tail -4; }
for A in 1790380800 1790395200 1790409600; do one current base $A; one patched base $A; done
for arm in gap1 gap2 gap6 gap7 bridge1 bridge2 bridge6 bridge7 x1 x2 x3 xref mhbase mhdrop cold poison; do one current $arm 1790409600; done
for arm in gap1 gap2 gap6 gap7 x1 x2 x3 mhbase mhdrop cold poison; do one patched $arm 1790409600; done
echo "=== $(date -u +%FT%TZ) judge"
~/wide_shadow/venv/bin/python "$D/gap_fix_judge.py" "$ROOT" --out "$OUT"; echo "JUDGE_RC=$?"
