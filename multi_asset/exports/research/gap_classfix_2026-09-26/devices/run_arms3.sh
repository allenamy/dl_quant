#!/bin/bash
# run 3 (AMENDMENT 3): every PATCHED arm on tree GAP4 + the new cold / poison arms on both codes; unchanged current-code arms are reused
# from run 1 (and the current M arms from run 2) by symlink. usage: run_arms3.sh <run1 root> <run2 root> <run3 root> <tree GAP4> <receipt out>
set -uo pipefail
R1=${1:?}; R2=${2:?}; ROOT=${3:?}; TREE=${4:?}; OUT=${5:?}; D=$(cd "$(dirname "$0")" && pwd -P)
mkdir -p "$ROOT"
for d in "$R1"/current_*; do ln -s "$d" "$ROOT/$(basename "$d")"; done
for d in "$R2"/current_mh*; do ln -s "$(readlink -f "$d")" "$ROOT/$(basename "$d")"; done
one() { local code=$1 arm=$2 A=$3; local sbr="$ROOT/${code}_${arm}"; mkdir -p "$sbr"
  echo "=== $(date -u +%FT%TZ) $code $arm $A"; bash "$D/gap_fix_replay.sh" "$A" - "$sbr" "$arm" "$code" "$TREE" 2>&1 | tail -4; }
for A in 1790380800 1790395200 1790409600; do one patched base $A; done
for arm in gap1 gap2 gap6 gap7 x1 x2 x3 mhbase mhdrop cold poison; do one patched $arm 1790409600; done
for arm in cold poison; do one current $arm 1790409600; done
echo "=== $(date -u +%FT%TZ) judge"
~/wide_shadow/venv/bin/python "$D/gap_fix_judge.py" "$ROOT" --out "$OUT"; echo "JUDGE_RC=$?"
