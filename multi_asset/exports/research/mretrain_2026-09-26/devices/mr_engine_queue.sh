#!/bin/bash
# mr_engine_queue.sh <ORDER_FILE>  -- runs the family's engine cells ONE AT A TIME, in the order file's order (lines "LABEL SEED").
# Team rule (lead 2026-09-26): at most two engine cells in parallel ACROSS the team => start only if the shared run gate
# (memgate.sh: cgroup headroom >= 24 GiB, /dev/shm free >= 4 GiB) passes AND at most ONE other bt_launch group exists.
# Waits are bound to run identity (§10-c): the recorded PGID must stay alive until a line-anchored verdict appears;
# Traceback / No space / PGID gone without a verdict => STOP (marker written, queue exits non-zero).
set -uo pipefail
ORDER=$1; QMODE=${2:-family}   # rootcause = descriptive single-condition cells (fresh2 2026-09-27): no red/family reading, no family gate
R=/dev/shm/mretrain_2026-09-26; N=/dev/shm/news2_2026-09-23; PV=/workspace/venv/bin/python
FSAVE=/dev/shm/fresh_2026-09-23/devices/fa_ladsave.py; GATE=/dev/shm/fresh_2026-09-23/devices/memgate.sh
L=$R/logs/engine; mkdir -p $L $R/series
say() { echo "$(date -u +%Y-%m-%dT%H:%M:%SZ) $*" | tee -a $L/queue.log; }
case $QMODE in family) ML=$R/logs/master.log;; rootcause) ML=$R/logs/rootcause.log;; ksr) ML=$R/logs/ksr.log;;   # registered log of the job running this queue
  *) echo "unknown queue mode $QMODE" >&2; exit 1;; esac
PQ=$R/PREP_QUEUE; [ "$QMODE" = family ] || PQ=$R/PREP_QUEUE_$QMODE   # prep-queue end markers scoped to the job that writes them
. $R/devices/mr_stop.sh   # stop scope inherited from the dispatcher (mr_master / rc_hybrid: mr_scope_begin); unset => every launch refused
[ "${MR_MASTER_LOG:-$ML}" = "$ML" ] || { echo "stop scope log ${MR_MASTER_LOG} != this queue's registered log $ML" >&2; exit 1; }
halt() { say "HALT (no launch): $*"; exit 1; }   # a STOP already stands in $ML (or no scope): exit without writing a second STOP
stop() { say "STOP: $*"; [ "$QMODE" = family ] && echo "$*" > $R/ENGINE_QUEUE_STOPPED; echo "$(date -u +%Y-%m-%dT%H:%M:%SZ) STOP: engine queue: $*" >> $ML; exit 1; }
say "ENGINE_QUEUE_START pgid=$(ps -o pgid= -p $$ | tr -d ' ') order=$ORDER"
while read -r LBL S; do
  [ -z "$LBL" ] && continue
  W=$R/arms/$LBL
  [ -e $W/DONE_s$S ] && { say "skip $LBL s$S (DONE)"; continue; }
  while [ ! -e $W/READY_s$S ]; do
    [ -e $W/FAILED ] && stop "$LBL prep FAILED"
    [ -e ${PQ}_STOPPED ] && stop "prep queue stopped before $LBL was ready"
    [ -e ${PQ}_DONE ] && [ ! -e $W/READY_s$S ] && stop "prep queue done but $LBL s$S never READY"
    mr_stopped && halt "family STOP while waiting for $LBL s$S READY"
    sleep 60
  done
  while [ -e $R/PAUSE ]; do mr_stopped && halt "family STOP during PAUSE before $LBL s$S"; sleep 60; done          # courtesy pause for other agents' priority cells (between cells only)
  # lead's team priority (2026-09-26): 1 dlarch R1.4, 2 alloc R/O, 3 this family (red + A0/A1), 4 alloc candidates, 5 news2 D seg 5,
  # 6 this family's A3. Shared convention: an agent with a cell READY and waiting drops /dev/shm/ENGINE_PRIORITY/p<rank>_<name>.waiting;
  # this queue (rank MY_RANK) does not launch while any file with a smaller rank exists.
  MY_RANK=3; [[ "$LBL" == A3_* ]] && MY_RANK=6
  while ls /dev/shm/ENGINE_PRIORITY/p[1-9]_*.waiting > /dev/null 2>&1 && \
        [ -n "$(ls /dev/shm/ENGINE_PRIORITY/ | sed -n 's/^p\([1-9]\)_.*\.waiting$/\1/p' | awk -v r=$MY_RANK '$1 < r')" ]; do mr_stopped && halt "family STOP during priority wait before $LBL s$S"; sleep 60; done
  while :; do
    MY=$(ps -o pgid= -p $$ | tr -d ' ')
    NOTHER=$(ps -eo pgid,args | grep "bt_launch\.py" | grep -v grep | awk -v me="$MY" '$1 != me {print $1}' | sort -u | grep -c .)
    if [ "$NOTHER" -le 1 ] && bash $GATE > $L/gate_last.log 2>&1; then break; fi
    mr_stopped && halt "family STOP during capacity wait before $LBL s$S"
    sleep 120
  done
  say "launch $LBL s$S (other groups $NOTHER; $(tail -1 $L/gate_last.log))"
  LOG=$L/engine_${LBL}_s$S.log
  cd $N/engine
  mr_guard "engine $LBL s$S" || halt "family STOP before launching $LBL s$S"; setsid env -i PATH=/usr/bin:/bin HOME=/root nice -n 12 $PV -B bt_launch.py PATH,HOME,LC_CTYPE \
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
  say "done $LBL s$S $(sha256sum $SER | cut -c1-16) king_P=$(grep -o '"P": "[0-9a-f]\{16\}' $W/receipts/KING_IDENTITY.json 2>/dev/null | cut -c7-)"   # rule §7: score sha per cell
  # rule §0.4 red control + engine-reproducibility control, executed HERE as soon as its four series exist (§10-f: a process
  # executor, not the session). Not PASS => the family stops (rule §0), before any further cell.
  if [ "$QMODE" = family ] && [ ! -e $R/RED_READ_PASS ] && ls $R/series/SER_RED_m0_s42.npz $R/series/SER_RED_m0_s2027.npz $R/series/SER_A0_m0_s42.npz $R/series/SER_A0_m0_s2027.npz > /dev/null 2>&1; then
    mkdir -p $R/receipts
    (cd $R/devices && env -i PATH=/usr/bin:/bin HOME=/root $PV -B mr_read.py PATH,HOME,LC_CTYPE red $R/receipts/MR_READ_red.json > $L/read_red.log 2>&1)
    say "$(grep -h '^MR_READ mode=red' $L/read_red.log | cut -c1-200)"
    grep -qE "^MR_READ mode=red sha=[0-9a-f]{64} FAIL=\[\]$" $L/read_red.log || stop "red / engine-reproducibility control not PASS (see $L/read_red.log) -> family stops (rule section 0)"
    touch $R/RED_READ_PASS; say "RED_READ_PASS"
  fi
done < $ORDER
say "ENGINE_QUEUE_DONE mode=$QMODE"
[ "$QMODE" = family ] || exit 0
# rule §1-§4 applied mechanically by the committed reading device (process executor; exit 4 = INCOMPLETE is reported, not hidden)
(cd $R/devices && env -i PATH=/usr/bin:/bin HOME=/root $PV -B mr_read.py PATH,HOME,LC_CTYPE family $R/receipts/MR_READ_family.json > $L/read_family.log 2>&1); rc=$?
say "READ_FAMILY rc=$rc $(grep -h '^MR_READ\|VERDICT=' $L/read_family.log | tr '\n' ' ' | cut -c1-400)"
