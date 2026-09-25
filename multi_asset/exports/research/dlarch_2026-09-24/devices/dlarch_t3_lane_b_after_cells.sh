#!/bin/sh
# dlarch_t3_lane_b_after_cells.sh -- start T3 lane B the moment the book-layer cell queue is done.
#
# WHY AUTOMATED: the engine cells have priority and each needs 24 GiB by its own gate. Measured, two T3
# lanes leave ~21.5 GiB, so the next cell's gate would refuse and the priority queue would stall. The
# switch to two lanes therefore has to happen exactly when the cell queue ends -- and if it waits for me
# to notice, that is dead GPU time.
#
# WHAT IT WILL NOT DO:
#   * it does not start lane B while any cell claim is still held, even if the driver's done-marker
#     appeared (a marker is about "finished", a claim is about "someone is working" -- conflating those
#     is exactly how two chain_runs ended up on seed 7 today);
#   * it does not decide anything about T3 itself; lane B takes seeds via the same atomic mkdir claims,
#     so it cannot collide with lane A no matter when it starts;
#   * it has a bound. If the cell queue has not finished within the bound it exits and says so, rather
#     than lurking forever -- a waiter that can only succeed turns a stall into silence.
#
# usage: sh dlarch_t3_lane_b_after_cells.sh
set -u
W=/workspace/dlarch_2026-09-24
DRV=$W/CHAIN/cells_driver.log
LOG=$W/T3_lane_b_switch.log

say(){ echo "$(date -u +%H:%M:%SZ) [laneB-switch] $*" | tee -a "$LOG"; }

MYPGID=$(ps -o pgid= -p $$ | tr -d ' ')
printf 'pgid=%s pid=%s owner=dlarch job=t3_lane_b_switch started=%s\n' \
  "$MYPGID" "$$" "$(date -u +%FT%TZ)" > "$W/T3_lane_b_switch.pgid"
say "=== waiting for the cell queue to finish (pgid $MYPGID) ==="

DONE=0
for i in $(seq 1 180); do            # bound: 180 x 20 s = 60 min
  if grep -q CELLS_DRIVER_DONE "$DRV" 2>/dev/null; then
    HELD=$(ls -d "$W"/CHAIN/.claim_s* 2>/dev/null | grep -c .)
    if [ "$HELD" -eq 0 ]; then DONE=1; break; fi
    say "done-marker present but $HELD claim(s) still held -- NOT starting yet"
  fi
  sleep 20
done

if [ "$DONE" -ne 1 ]; then
  say "BOUND EXPIRED (60 min) without a clean finish: marker=$(grep -c CELLS_DRIVER_DONE "$DRV" 2>/dev/null) claims_held=$(ls -d "$W"/CHAIN/.claim_s* 2>/dev/null | grep -c .)"
  say "NOT starting lane B -- report this instead of assuming"
  exit 1
fi

say "cell queue finished and no claims held; cells with retention receipts: $(ls -d $W/receipts/RETAIN_s*_2026-09-25.json 2>/dev/null | grep -c .)/8"
say "headroom now: $(awk 'NR==FNR{m=$1;next}/^anon /{a=$2}/^shmem /{s=$2}END{printf "%.2f",(m-a-s)/1073741824}' /sys/fs/cgroup/memory.max /sys/fs/cgroup/memory.stat) GiB"
# lane B walks the seed list in the OPPOSITE order, so it claims the seed lane A is least likely to be on
say "starting T3 lane B with reversed seed order"
DLARCH_LANE=B exec sh "$W/dlarch_run_T3_lane.sh" "7 2027 42"
