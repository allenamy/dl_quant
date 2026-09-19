#!/bin/bash
# AMENDMENT 6 extension chain A0_ext (OBJB_DATA=x0918r), sequenced for the 20 GB budget:
#   1. after A0_main has finished (LAUNCH_DONE): object-B targets of A0_main (b_targets.py, small)
#   2. A0_ext P1 over the full axis (~6 GB; runs beside the v4 arm's P2)
#   3. after the v4 arm's P2 has finished: A0_ext P2 (score reuse where every scorer input is bitwise equal; 4 workers for the new anchors) + P3
#   4. targets of A0_ext, then EXT-REPRO (A0_ext vs A0_main on the 10,039 common anchors)
# The P2 sandboxes (/dev/shm/object_b_p2/w<k>) are shared by name between runs, hence strictly sequential P2 stages.
# Every step waits until the cgroup keeps >= 20 GiB available after the step's own need. Own PGID recorded; kills nothing.
R=/workspace/object_b_2026-09-19; ST=$R/logs/EXT_CHAIN_STATUS.txt; A0LOG=$R/logs/launch_A0_main.log; V4LOG=$R/logs/launch_V4_main.log
PY=/workspace/venv/bin/python; ENVB="env -i PATH=/usr/bin:/bin HOME=/root LC_CTYPE=C.UTF-8"
echo "armed $(date -u +%FT%TZ) pgid $(ps -o pgid= $$ | tr -d ' ')" > $ST
CGMAX=$(( $(cat /sys/fs/cgroup/memory.max) / 1073741824 ))
wait_mem() {   # $1 = own need in GiB
  while true; do
    USED=$(awk '/^(anon|shmem) /{s+=$2} END {printf "%d", s/1073741824}' /sys/fs/cgroup/memory.stat)
    if [ $(( CGMAX - USED - $1 )) -ge 20 ]; then break; fi
    echo "waiting memory for $1 GiB: used ${USED} of ${CGMAX} $(date -u +%FT%TZ)" >> $ST; sleep 120
  done
}
until grep -q '^LAUNCH_DONE' $A0LOG; do
  if grep -q 'Traceback' $A0LOG; then echo "A0 failed; stop $(date -u +%FT%TZ)" >> $ST; exit 3; fi
  sleep 60
done
echo "A0 done $(date -u +%FT%TZ)" >> $ST
cd $R/devices
$ENVB nice -n 10 $PY -B b_targets.py A0_main > $R/logs/targets_A0_main.log 2>&1; echo "targets A0_main rc=$? $(date -u +%FT%TZ)" >> $ST
wait_mem 7
$ENVB OBJB_DATA=x0918r nice -n 10 $PY -B b_launch.py --tag A0_ext --start 2022-01-31T00:00:00Z --end 2026-09-18T20:00:00Z --workers 4 --stages P1 \
  > $R/logs/launch_A0_ext_P1.log 2>&1; rc=$?; echo "A0_ext P1 rc=$rc $(date -u +%FT%TZ)" >> $ST; [ $rc -eq 0 ] || exit 4
cp $R/receipts/RUN_CONFIG_A0_ext.json $R/receipts/RUN_CONFIG_A0_ext_P1.json
until grep -q '^P2 {' $V4LOG 2>/dev/null || grep -q 'Traceback' $V4LOG 2>/dev/null; do sleep 60; done
echo "v4 P2 finished or failed $(date -u +%FT%TZ)" >> $ST
wait_mem 11
$ENVB OBJB_DATA=x0918r nice -n 10 $PY -B b_launch.py --tag A0_ext --start 2022-01-31T00:00:00Z --end 2026-09-18T20:00:00Z --workers 4 --stages P2,P3 \
  --reuse-p2 A0_main > $R/logs/launch_A0_ext_P23.log 2>&1; rc=$?; echo "A0_ext P2,P3 rc=$rc $(date -u +%FT%TZ)" >> $ST; [ $rc -eq 0 ] || exit 5
$ENVB OBJB_DATA=x0918r nice -n 10 $PY -B b_targets.py A0_ext > $R/logs/targets_A0_ext.log 2>&1; echo "targets A0_ext rc=$? $(date -u +%FT%TZ)" >> $ST
$ENVB nice -n 10 $PY -B ext_repro_check.py A0_main A0_ext > $R/logs/ext_repro_A0_ext.log 2>&1; echo "EXT-REPRO rc=$? $(date -u +%FT%TZ)" >> $ST
echo "DONE $(date -u +%FT%TZ)" >> $ST
