#!/bin/bash
# remaining ends: none s2027 + all_new both seeds (none s42 already PASSed and its series is saved)
set -u
D=/dev/shm/fresh_2026-09-23/devices
N=/dev/shm/news_2026-09-23; F=/dev/shm/fresh_2026-09-23; NC=/dev/shm/news2_2026-09-23
TIGHT_HEAD=28000; TIGHT_SHM=6144; MAX_WAIT_MIN=600
run_end () {
  local legs=$1 f10=$2 prefix=$3 label=$4 s=$5 waited=0
  if [ -s "/dev/shm/fanom_2026-09-24/receipts/SER_LAD2_${label}_s${s}.npz" ]; then
    echo "SKIP $label s$s: series already present"; return 0
  fi
  while : ; do
    bash "$D/memgate.sh" "$TIGHT_HEAD" "$TIGHT_SHM" > /tmp/l2g.log 2>&1 && break
    if [ "$waited" -ge "$MAX_WAIT_MIN" ]; then echo "GIVING UP: $label s$s"; exit 9; fi
    [ $((waited % 20)) -eq 0 ] && { echo "$(date -u +%H:%M:%SZ) yielding before $label s$s:"; tail -1 /tmp/l2g.log; }
    sleep 120; waited=$((waited + 2))
  done
  echo "===== $label s$s (gate open after ${waited}m) ====="
  bash "$D/lad2_pipe.sh" "$legs" "$f10" "$prefix" "$NC" RN8 "$label" "$s"
  local rc=$?; echo "  pipe_rc=$rc"
  [ "$rc" -ne 0 ] && { echo "STOPPING: $label s$s rc=$rc"; exit "$rc"; }
}
run_end "$F" "$F" FRESH CLEANRN8_ALLNEW 42
run_end "$N" "$N" NEWS  CLEANRN8_NONE   2027
run_end "$F" "$F" FRESH CLEANRN8_ALLNEW 2027
echo "ALL LAD2 REST DONE"; ls -la /dev/shm/fanom_2026-09-24/receipts/SER_LAD2_*.npz
