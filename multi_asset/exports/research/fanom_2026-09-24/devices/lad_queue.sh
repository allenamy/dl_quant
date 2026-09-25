#!/bin/bash
# Ladder queue: 2 FRESH baselines then 8 arm cells, STRICTLY one engine cell at a time.
# Each item waits on the run gate, which refuses while ANY other bt_launch is running (including my own previous one).
W=/dev/shm/fresh_2026-09-23; FA=/dev/shm/fanom_2026-09-24; F=/dev/shm/fresh_2026-09-23
LOG=$FA/logs/LAD_QUEUE.log
: > $LOG
run_item () {   # $1..$4 passed through to lad_pipe.sh
  local desc="$*"
  local try=0
  while : ; do
    try=$((try+1))
    if bash $W/devices/memgate.sh 3000 >> $LOG 2>&1; then break; fi
    if [ $try -ge 240 ]; then echo "[GATE TIMEOUT] $desc" >> $LOG; return 9; fi
    sleep 60
  done
  echo "[START] $desc (gate open after $((try-1)) waits)" >> $LOG
  if bash $W/devices/lad_pipe.sh "$@" >> $LOG 2>&1; then
    echo "[DONE] $desc rc=0" >> $LOG
  else
    echo "[FAIL] $desc rc=$?" >> $LOG; return 1
  fi
}
run_item baseline $F FRESH 42    || { echo "[ABORT] FRESH baseline s42" >> $LOG; exit 1; }
run_item baseline $F FRESH 2027  || { echo "[ABORT] FRESH baseline s2027" >> $LOG; exit 1; }
for SEED in 42 2027; do
  run_item arm KZ        KZ    $SEED || { echo "[ABORT] KZ s$SEED"   >> $LOG; exit 1; }
  run_item arm WL        WL    $SEED || { echo "[ABORT] WL s$SEED"   >> $LOG; exit 1; }
  run_item arm F10       F10   $SEED || { echo "[ABORT] F10 s$SEED"  >> $LOG; exit 1; }
  run_item arm KZ,WL     KZWL  $SEED || { echo "[ABORT] KZWL s$SEED" >> $LOG; exit 1; }
done
echo "[ALL_TEN_DONE]" >> $LOG
