#!/bin/bash
# Run gate. Two conditions, both added after 2026-09-25: the 04:33Z `oom_kill 9` and the lead's rule
# "do not start two engine cells at once".
#   1. cgroup memory headroom = memory.max - anon - shmem. df on /dev/shm alone is NOT the constraint:
#      shmem counts against the cgroup and anon spikes during a run.
#   2. NO OTHER bt_launch may be running. This is checked by inspecting the process table for bt_launch
#      processes whose PGID is not mine -- not by name-based killing, which is forbidden on this shared host.
#      I never signal them; I refuse to start.
need_mib=${1:-3000}
M=$(cat /sys/fs/cgroup/memory.max 2>/dev/null || echo 0)
A=$(grep "^anon " /sys/fs/cgroup/memory.stat 2>/dev/null | awk '{print $2}')
S=$(grep "^shmem " /sys/fs/cgroup/memory.stat 2>/dev/null | awk '{print $2}')
case "$M" in ''|max) M=0 ;; esac
H=$(( (M - A - S) / 1024 / 1024 ))
D=$(df -BM /dev/shm | tail -1 | awk '{print $4}' | tr -d M)
MYPGID=$(ps -o pgid= -p $$ | tr -d ' ')
OTHER=$(ps -eo pgid,pid,cmd | grep -E "bt_launch\.py" | grep -v grep | awk -v me="$MYPGID" '$1 != me {print $1":"$2}' | sort -u | tr '\n' ' ')
echo "  rungate: cgroup headroom ${H}MiB, /dev/shm free ${D}MiB, need ${need_mib}MiB"
if [ -n "$OTHER" ]; then
  echo "  rungate: ANOTHER bt_launch IS RUNNING (pgid:pid = $OTHER) -> refusing to start (not signalling it)"
  exit 9
fi
echo "  rungate: no other bt_launch running"
if [ "$H" -lt "$need_mib" ] || [ "$D" -lt 1500 ]; then echo "  rungate: WAIT (insufficient headroom)"; exit 9; fi
echo "  rungate: OK"
