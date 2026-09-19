#!/bin/bash
# memguard.sh — coordination with the axis_0919 agent (its king feature builder peaks at 50-58 GB of the 61 GB cgroup).
# Blocks until (a) no process whose command line contains axis_0919 has RSS > 20 GB and (b) cgroup headroom (memory.max - memory.current) >= NEED_GB.
# "free" is read as cgroup headroom: host `free -g` reports the whole 247 GB machine, not this container's 61 GB limit; memory.current also counts
# reclaimable page cache, so the test is conservative. Bounded: gives up (rc 9) after MAX_WAIT_MIN minutes. Every poll is logged.
# usage: memguard.sh <label> [NEED_GB=30] [MAX_WAIT_MIN=720]
L=$1; NEED=${2:-30}; MAXW=${3:-720}; W=/workspace/retrain_reeval_2026-09-19; n=0
while :; do
  cur=$(cat /sys/fs/cgroup/memory.current); max=$(cat /sys/fs/cgroup/memory.max); head=$(( (max - cur) / 1073741824 ))
  ax=$(ps -eo rss=,cmd= | grep -a axis_0919 | grep -v grep | awk '{s=$1; if (s>m) m=s} END {print int(m/1048576)}')
  axn=$(ps -eo cmd= | grep -a axis_0919 | grep -v grep | wc -l)
  echo "MEMGUARD[$L] $(date -u +%FT%TZ) cg_headroom_GB=$head need=$NEED axis_0919_procs=$axn axis_0919_max_rss_GB=${ax:-0}" >> $W/logs/memguard.log
  if [ "$head" -ge "$NEED" ] && [ "${ax:-0}" -le 20 ]; then echo "MEMGUARD_OK[$L] $(date -u +%FT%TZ)" >> $W/logs/memguard.log; exit 0; fi
  n=$((n+1)); [ $((n*3)) -ge $MAXW ] && { echo "MEMGUARD_TIMEOUT[$L]" >> $W/logs/memguard.log; exit 9; }
  sleep 180
done
