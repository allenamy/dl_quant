#!/bin/bash
# Arms only (the two FRESH baselines are already done and their series saved). Strictly one engine cell at a time.
W=/dev/shm/fresh_2026-09-23; FA=/dev/shm/fanom_2026-09-24
LOG=$FA/logs/LAD_QUEUE2.log
: > $LOG
run_item () {
  local desc="$*"; local try=0
  while : ; do
    try=$((try+1))
    if bash $W/devices/memgate.sh 3000 >> $LOG 2>&1; then break; fi
    if [ $try -ge 240 ]; then echo "[GATE TIMEOUT] $desc" >> $LOG; return 9; fi
    sleep 60
  done
  echo "[START] $desc (gate open after $((try-1)) waits)" >> $LOG
  if bash $W/devices/lad_pipe.sh "$@" >> $LOG 2>&1; then echo "[DONE] $desc rc=0" >> $LOG
  else echo "[FAIL] $desc rc=$?" >> $LOG; return 1; fi
}
for SEED in 42 2027; do
  for A in "KZ KZ" "WL WL" "F10 F10" "KZ,WL KZWL"; do
    set -- $A
    run_item arm "$1" "$2" $SEED || { echo "[ABORT] $2 s$SEED" >> $LOG; exit 1; }
  done
done
echo "[ALL_EIGHT_ARMS_DONE]" >> $LOG
