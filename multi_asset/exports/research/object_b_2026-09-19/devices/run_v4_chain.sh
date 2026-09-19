#!/bin/bash
# AMENDMENT 5 v4 arm: P2 + P3 over the A0 axis, reusing A0_main's P1 (members / fund state do not depend on the king model; P3 re-asserts
# member equality at every anchor). Starts only after A0_main's P2 has finished (the two P2 stages cannot share the 20 GB memory budget:
# probe logs/memprobe_samples.txt, ~1 GB per scorer worker + ~6 GB parent) and only when the cgroup keeps >= 20 GiB available after
# the v4 arm's own ~13 GB. 5 workers: with A0_main P3 alongside (~6 GB) the budget of 20 GB holds (12-worker P2 peaked at 21.85 GB).
# Own PGID recorded; kills nothing.
R=/workspace/object_b_2026-09-19; ST=$R/logs/V4_CHAIN_STATUS.txt; A0LOG=$R/logs/launch_A0_main.log
echo "armed $(date -u +%FT%TZ) pgid $(ps -o pgid= $$ | tr -d ' ')" > $ST
until grep -q '^P2 {' $A0LOG; do
  if grep -q 'Traceback' $A0LOG; then echo "A0 failed; v4 not started $(date -u +%FT%TZ)" >> $ST; exit 3; fi
  sleep 60
done
echo "A0 P2 done $(date -u +%FT%TZ)" >> $ST
CGMAX=$(( $(cat /sys/fs/cgroup/memory.max) / 1073741824 ))
while true; do
  USED=$(awk '/^(anon|shmem) /{s+=$2} END {printf "%d", s/1073741824}' /sys/fs/cgroup/memory.stat)
  if [ $(( CGMAX - USED - 13 )) -ge 20 ]; then break; fi
  echo "waiting memory: cgroup max ${CGMAX} used ${USED} GiB $(date -u +%FT%TZ)" >> $ST; sleep 120
done
free -g | head -2 >> $ST
cd $R/devices && env -i PATH=/usr/bin:/bin HOME=/root LC_CTYPE=C.UTF-8 OBJB_ARM=V4 nice -n 10 /workspace/venv/bin/python -B b_launch.py \
  --tag V4_main --start 2022-01-31T00:00:00Z --end 2026-08-31T00:00:00Z --workers 5 --stages P2,P3 --p1-from A0_main > $R/logs/launch_V4_main.log 2>&1
echo "V4_main rc=$? $(date -u +%FT%TZ)" >> $ST
