#!/bin/bash
# memory probe for one P2 worker (object B); own PGID recorded; samples cgroup anon+shmem and /dev/shm usage every 0.5 s
R=/workspace/object_b_2026-09-19; L=$R/logs/memprobe_samples.txt; : > $L
echo "pgid $(ps -o pgid= $$ | tr -d ' ') start $(date -u +%FT%TZ)" > $R/logs/memprobe_status.txt
( while true; do echo "$(date -u +%T) $(grep -E '^(anon|shmem) ' /sys/fs/cgroup/memory.stat | awk '{printf "%s=%.2f ", $1, $2/2^30}') shm=$(du -sm /dev/shm/object_b_p2 2>/dev/null | cut -f1)" >> $L; sleep 0.5; done ) &
SP=$!
cd $R/devices && env -i PATH=/usr/bin:/bin HOME=/root LC_CTYPE=C.UTF-8 nice -n 10 /workspace/venv/bin/python -B b_launch.py --tag memprobe --start 2025-03-01T00:00:00Z --end 2025-03-01T08:00:00Z --workers 1 --stages P1,P2 > $R/logs/memprobe.log 2>&1
echo "rc=$? end $(date -u +%FT%TZ)" >> $R/logs/memprobe_status.txt
kill $SP
