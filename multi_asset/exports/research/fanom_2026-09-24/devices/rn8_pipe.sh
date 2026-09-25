#!/bin/bash
# rn8: combo with the funding clamp disabled (all-NaN rn8) -> variant target receipt -> adapter/guard/engine/extract.
# PREREG docs/PREREG_step1_rn8_clamp_2026-09-25.md (1624526af). NC's book artifacts live in the NEWS2 root, READ-ONLY.
set -e
W=/dev/shm/fresh_2026-09-23; FA=/dev/shm/fanom_2026-09-24
NC=/dev/shm/news2_2026-09-23
SEED=$1
BASE="NEWS2_s${SEED}"; VAR="RN8NC"; TAG="${VAR}_s${SEED}"
VDIR=$FA/bvar/${VAR}_$(basename $NC)_s${SEED}
PRED=500
A=$(df -BM /dev/shm|tail -1|awk '{print $4}'|tr -d M)
echo "[$TAG] shm_gate avail=${A}MiB need=$((PRED+1024))MiB"
[ "$A" -ge $((PRED+1024)) ] || { echo "[$TAG] WAIT"; exit 9; }
mkdir -p $VDIR $FA/logs
# 1. combo with the clamp disabled (asserts the clamp had a non-empty eligible population)
env -i PATH=/usr/bin:/bin HOME=/root nice -n 12 /workspace/venv/bin/python -B $W/devices/fa_rn8combo.py PATH,HOME,LC_CTYPE \
  --legs-root $NC --f10-root $NC --seed $SEED --out $VDIR --no-rn8-clamp > $FA/logs/combo_$TAG.log 2>&1
tail -1 $FA/logs/combo_$TAG.log
# 2. variant target receipt + combo-level behavioural difference (reused from B8, unchanged)
env -i PATH=/usr/bin:/bin HOME=/root /workspace/venv/bin/python -B $W/devices/fa_b8trcpt.py PATH,HOME,LC_CTYPE \
  $NC/work/combo_s${SEED} $VDIR 2>&1 | tail -1
echo "[$TAG] STOPPING HERE: engine stage is deliberately not wired until the prereg is approved."
