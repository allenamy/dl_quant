#!/bin/bash
# mr_engine_queue.sh <ORDER_FILE>  -- runs the family's engine cells ONE AT A TIME, in the order file's order (lines "LABEL SEED").
# Team rule (lead 2026-09-26): at most two engine cells in parallel ACROSS the team => start only if the shared run gate
# (memgate.sh: cgroup headroom >= 24 GiB, /dev/shm free >= 4 GiB) passes AND at most ONE other bt_launch group exists.
# Waits are bound to run identity (§10-c): the recorded PGID must stay alive until a line-anchored verdict appears;
# Traceback / No space / PGID gone without a verdict => STOP (marker written, queue exits non-zero).
set -uo pipefail
ORDER=$1
R=/dev/shm/mretrain_2026-09-26; N=/dev/shm/news2_2026-09-23; PV=/workspace/venv/bin/python
FSAVE=/dev/shm/fresh_2026-09-23/devices/fa_ladsave.py; GATE=/dev/shm/fresh_2026-09-23/devices/memgate.sh
L=$R/logs/engine; mkdir -p $L $R/series
say() { echo "$(date -u +%Y-%m-%dT%H:%M:%SZ) $*" | tee -a $L/queue.log; }
stop() { say "STOP: $*"; echo "$*" > $R/ENGINE_QUEUE_STOPPED; exit 1; }
say "ENGINE_QUEUE_START pgid=$(ps -o pgid= -p $$ | tr -d ' ') order=$ORDER"
while read -r LBL S; do
  [ -z "$LBL" ] && continue
  W=$R/arms/$LBL
  [ -e $W/DONE_s$S ] && { say "skip $LBL s$S (DONE)"; continue; }
  while [ ! -e $W/READY_s$S ]; do
    [ -e $W/FAILED ] && stop "$LBL prep FAILED"
    [ -e $R/PREP_QUEUE_STOPPED ] && stop "prep queue stopped before $LBL was ready"
    [ -e $R/PREP_QUEUE_DONE ] && [ ! -e $W/READY_s$S ] && stop "prep queue done but $LBL s$S never READY"
    sleep 60
  done
  while :; do
    MY=$(ps -o pgid= -p $$ | tr -d ' ')
    NOTHER=$(ps -eo pgid,args | grep "bt_launch\.py" | grep -v grep | awk -v me="$MY" '$1 != me {print $1}' | sort -u | grep -c .)
    if [ "$NOTHER" -le 1 ] && bash $GATE > $L/gate_last.log 2>&1; then break; fi
    sleep 120
  done
  say "launch $LBL s$S (other groups $NOTHER; $(tail -1 $L/gate_last.log))"
  LOG=$L/engine_${LBL}_s$S.log
  cd $N/engine
  setsid env -i PATH=/usr/bin:/bin HOME=/root nice -n 12 $PV -B bt_launch.py PATH,HOME,LC_CTYPE \
    $W/configs/RUN_CONFIG_MR_s$S.json --resume mr_${LBL}_$S > $LOG 2>&1 < /dev/null &
  sleep 5; PG=$(ps -o pgid= -p $! | tr -d ' ')
  echo "{\"label\":\"$LBL\",\"seed\":\"$S\",\"pgid\":\"$PG\",\"started_utc\":\"$(date -u +%Y-%m-%dT%H:%M:%SZ)\"}" > $L/PGID_${LBL}_s$S.json
  while :; do
    grep -qE "^BT_LAUNCH VERDICT=" $LOG && break
    grep -qE "^Traceback|No space left" $LOG && stop "$LBL s$S engine error (see $LOG)"
    [ -n "$PG" ] && ! ps -o pid= -g $PG > /dev/null 2>&1 && { sleep 5; grep -qE "^BT_LAUNCH VERDICT=" $LOG && break; stop "$LBL s$S PGID $PG gone without a verdict"; }
    sleep 20
  done
  grep -qE "^BT_LAUNCH VERDICT=PASS" $LOG || stop "$LBL s$S verdict not PASS"
  CELL=$W/pod_s$S/runs/NEWS2_s${S}X_scaled_rule_raw_UAFE
  SER=$R/series/SER_${LBL}_s$S.npz
  env -i PATH=/usr/bin:/bin HOME=/root nice -n 15 $PV -B $FSAVE PATH,HOME,LC_CTYPE $CELL $SER >> $L/save.log 2>&1 || stop "$LBL s$S save failed"
  $PV -c "import numpy,sys; z=numpy.load(sys.argv[1]); assert z['r_per_path'].shape[0]==32" "$SER" || stop "$LBL s$S series unreadable"
  rm -rf "$CELL"; [ "$LBL" != A0_m0 ] && rm -f $W/targets/TARGETS_NEWS2_s$S.npz
  touch $W/DONE_s$S
  say "done $LBL s$S $(sha256sum $SER | cut -c1-16)"
done < $ORDER
say "ENGINE_QUEUE_DONE"
