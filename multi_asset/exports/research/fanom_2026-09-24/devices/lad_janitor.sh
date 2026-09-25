#!/bin/bash
# Receipt-gated janitor for the ladder queue. Frees an arm's combo/targets npz ONLY when both of these exist:
#   - the arm's saved per-path series  receipts/SER_LAD_<label>_s<seed>.npz
#   - the arm's behavioural receipt    ladder/<label>_s<seed>/FA_B8TRCPT_RECEIPT.json
# It never touches a directory whose series is missing, never touches anyone else's root, and never signals a process.
# It exists because the pipe cannot be edited while the queue is executing it (bash reads scripts incrementally).
FA=/dev/shm/fanom_2026-09-24
LOG=$FA/logs/LAD_JANITOR.log
for i in $(seq 1 480); do
  for D in $FA/ladder/*_s42 $FA/ladder/*_s2027; do
    [ -d "$D" ] || continue
    B=$(basename $D); LBL=${B%_s*}; SD=${B##*_s}
    S=$FA/receipts/SER_LAD_${LBL}_s${SD}.npz
    if [ -s "$S" ] && [ -s "$D/FA_B8TRCPT_RECEIPT.json" ] && ls $D/*.npz >/dev/null 2>&1; then
      sz=$(du -sm $D | cut -f1)
      rm -f $D/*.npz
      echo "$(date -u +%H:%M:%SZ) freed $B npz (${sz}MB) -- series $(basename $S) present" >> $LOG
    fi
  done
  sleep 120
done
