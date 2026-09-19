#!/bin/bash
# run_T3.sh — stream T arm T3 (king monthly, CPU LightGBM): device check (yearly 2025 fold vs SLOW_v4) then the 20 monthly folds. PGID -> $W/T3.pgid.
W=/workspace/retrain_reeval_2026-09-19; S=$W/device; PY=/workspace/venv/bin/python; R=/workspace/fp2_2026-09; echo $(ps -o pgid= $$ | tr -d ' ') > $W/T3.pgid
bash $S/memguard.sh T3 30 || { echo "T3 memguard rc=$? — not launched" >> $W/logs/commands.txt; exit 9; }
ENVW="KING_FEA=$R/data/wide_fea_v4.npy KING_META=$R/data/wide_fea_v4_meta.npz SLOW_BASE=$R/king_v4/SLOW_v4.npy LIVE_PINS=$R/live_pins.json OUT_DIR=$W/king"
for MODE in check months; do
  CMD="env $ENVW MODE=$MODE $PY $S/king_monthly_T3.py"; echo "CMD[T3 $MODE] $(date -u +%FT%TZ) pgid=$(cat $W/T3.pgid) cg_mem=$(cat /sys/fs/cgroup/memory.current) : $CMD" >> $W/logs/commands.txt
  T0=$(date +%s); $CMD > $W/logs/T3_$MODE.log 2>&1; rc=$?; echo "END[T3 $MODE] rc=$rc wall $(( $(date +%s) - T0 )) s $(date -u +%FT%TZ)" >> $W/logs/commands.txt
  [ $rc -eq 0 ] || exit $rc
done
echo "T3_ALL_DONE $(date -u +%FT%TZ)" >> $W/logs/commands.txt
