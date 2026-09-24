#!/bin/bash
# Wait for P3 to SUCCEED, then run P4. The gate is the P3_CORRECTED_DONE marker, which run_p3_legs_f10.sh
# only reaches after `[ $R42 -eq 0 ] && [ $R2027 -eq 0 ]` under `set -e` -- so it means both F10 seeds
# exited 0, not merely that the script stopped. Waiting on "the process is gone" would also fire on a crash.
set -u
W=/dev/shm/news2_2026-09-23; L=$W/logs
while true; do
  if grep -q "P3_CORRECTED_DONE" $L/p3_corrected.log 2>/dev/null; then echo "P3 succeeded at $(date -u +%H:%M:%SZ)"; break; fi
  if ! pgrep -f "run_p3_legs_f10.sh" > /dev/null 2>&1 && ! pgrep -f "news2_train_f10.py" > /dev/null 2>&1; then
    echo "ABORT: P3 is no longer running and never wrote P3_CORRECTED_DONE -- not starting P4"; tail -5 $L/p3_corrected.log; exit 3
  fi
  sleep 30
done
bash $W/devices/run_p4_chain.sh
