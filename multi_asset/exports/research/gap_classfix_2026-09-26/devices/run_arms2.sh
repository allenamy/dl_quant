#!/bin/bash
# run 2: every PATCHED arm on tree GAP3 (+ the AMENDMENT 2 M arms on both codes); current-code arms are reused from run 1 by symlink
# (current code and hook branches for those arms unchanged). usage: run_arms2.sh <run1 root> <run2 root> <tree GAP3> <receipt out>
set -uo pipefail
R1=${1:?}; ROOT=${2:?}; TREE=${3:?}; OUT=${4:?}; D=$(cd "$(dirname "$0")" && pwd -P)
mkdir -p "$ROOT"
for d in "$R1"/current_*; do ln -s "$d" "$ROOT/$(basename "$d")"; done
one() { local code=$1 arm=$2 A=$3; local sbr="$ROOT/${code}_${arm}"; mkdir -p "$sbr"
  echo "=== $(date -u +%FT%TZ) $code $arm $A"; bash "$D/gap_fix_replay.sh" "$A" - "$sbr" "$arm" "$code" "$TREE" 2>&1 | tail -4; }
for A in 1790380800 1790395200 1790409600; do one patched base $A; done
for arm in gap1 gap2 gap6 gap7 x1 x2 x3; do one patched $arm 1790409600; done
for code in current patched; do for arm in mhbase mhdrop; do [ -e "$ROOT/${code}_${arm}" ] && [ ! -L "$ROOT/${code}_${arm}" ] && continue; rm -f "$ROOT/${code}_${arm}"; one $code $arm 1790409600; done; done
echo "=== $(date -u +%FT%TZ) judge"
~/wide_shadow/venv/bin/python "$D/gap_fix_judge.py" "$ROOT" --out "$OUT"; echo "JUDGE_RC=$?"
