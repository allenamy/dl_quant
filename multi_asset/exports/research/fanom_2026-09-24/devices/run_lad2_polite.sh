#!/bin/bash
# Ladder two ends x two seeds, clean RN8. Yields to dlarch on a TIGHTER threshold than my own floor.
# Ends (lead 2026-09-26): swap ONLY RN8, both ends; `none` keeps the NEW_S root so the original G definition holds.
set -u
D=/dev/shm/fresh_2026-09-23/devices
N=/dev/shm/news_2026-09-23; F=/dev/shm/fresh_2026-09-23; NC=/dev/shm/news2_2026-09-23
TIGHT_HEAD=28000; TIGHT_SHM=6144; MAX_WAIT_MIN=600
run_end () {   # legs f10 prefix label seed
  local legs=$1 f10=$2 prefix=$3 label=$4 s=$5 waited=0
  while : ; do
    bash "$D/memgate.sh" "$TIGHT_HEAD" "$TIGHT_SHM" > /tmp/lad2gate.log 2>&1 && break
    if [ "$waited" -ge "$MAX_WAIT_MIN" ]; then echo "GIVING UP: gate never opened for $label s$s"; tail -2 /tmp/lad2gate.log; exit 9; fi
    [ $((waited % 20)) -eq 0 ] && { echo "$(date -u +%H:%M:%SZ) yielding before $label s$s:"; tail -1 /tmp/lad2gate.log; }
    sleep 120; waited=$((waited + 2))
  done
  echo "===== $label s$s (gate open after ${waited}m) ====="
  bash "$D/lad2_pipe.sh" "$legs" "$f10" "$prefix" "$NC" RN8 "$label" "$s"
  local rc=$?; echo "  pipe_rc=$rc"
  [ "$rc" -ne 0 ] && { echo "STOPPING: $label s$s rc=$rc"; exit "$rc"; }
}
for s in 42 2027; do
  run_end "$N" "$N" NEWS  CLEANRN8_NONE   "$s"
  run_end "$F" "$F" FRESH CLEANRN8_ALLNEW "$s"
done
echo "ALL LAD2 DONE"
ls -la /dev/shm/fanom_2026-09-24/receipts/SER_LAD2_*.npz
