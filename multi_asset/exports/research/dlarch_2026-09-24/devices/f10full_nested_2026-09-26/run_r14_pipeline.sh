#!/bin/sh
# run_r14_pipeline.sh -- R1.4 end to end, EVERY step owned by a process in ONE process group (protocol 10-f):
#   step 1  identity control (--force-epoch 7, seed 42, folds 2023,202609) + dlarch_nested_identity.py;
#           not GREEN => the pipeline STOPS here, nothing else starts.
#   step 2  training, TWO GPU lanes (lead 18:0xZ): A = 42 then 7, B = 2027; each seed through
#           dlarch_f10full_launch.py (pins the trainer sha before exec).
#   step 3  book cells: dlarch_run_nested_cells.sh started alongside step 2, pipelined per seed, own run gate.
#   step 4  verdict: dlarch_nested_verdict.py once step 2 and step 3 both ended clean.
# Waiters must pin to this PGID (in r14.pgid) and to r14.log; success = a line that STARTS with
# 'R14_PIPELINE_DONE rc=0'. Any other R14_PIPELINE_* line, or a Traceback in r14.log, is a failure.
set -u
W=/workspace/dlarch_2026-09-24
A=$W/f10full_nested_2026-09-26
PIN=39839252b95914b1ed9195f77c8959e930979fa79331dfe1b947bc5847be365a
PY=/workspace/venv/bin/python
LOG=$A/r14.log
CLAIM=$W/CHAIN/.claim_R14
MYPGID=$(ps -o pgid= -p $$ | tr -d ' ')
mkdir "$CLAIM" 2>/dev/null || { echo "$(date -u +%T) REFUSING: $CLAIM exists" >> "$LOG"; exit 4; }
echo "pgid=$MYPGID pid=$$ owner=dlarch job=r14_pipeline started=$(date -u +%FT%TZ)" | tee "$CLAIM/owner" > "$A/r14.pgid"
say(){ echo "$(date -u +%H:%M:%SZ) [r14] $*" >> "$LOG"; }
stop(){ say "$1"; echo "R14_PIPELINE_STOPPED $1" >> "$LOG"; rm -rf "$CLAIM"; exit 1; }
say "=== START pgid=$MYPGID trainer pin $PIN ==="
say "gpu: $(nvidia-smi --query-gpu=utilization.gpu,memory.used --format=csv,noheader)"
launch(){  # $1 = receipt name, rest = trainer args
  R=$1; shift
  env -u PWD -u _ env -i PATH=/usr/bin:/bin HOME=/root LC_CTYPE=C "$PY" "$W/dlarch_f10full_launch.py" \
      PATH,HOME,LC_CTYPE "$A" "$PIN" "$A/PREFLIGHT_F10FULL.json" "$A/receipts/$R" -- "$@"
}

# ---- step 0: write probe (lead: 2 GiB written AND read back before anything starts; df cannot see the quota) ----
PR=$W/.r14_write_probe
dd if=/dev/zero of="$PR" bs=1M count=2048 conv=fsync 2>> "$LOG"; DRC=$?
SZ=$(stat -c %s "$PR" 2>/dev/null || echo 0)
if [ $DRC -ne 0 ] || [ "$SZ" -ne 2147483648 ] || ! cmp -s -n 2147483648 "$PR" /dev/zero; then
  rm -f "$PR"; stop "write probe failed (dd rc=$DRC, size $SZ of 2147483648, or read-back mismatch)"
fi
rm -f "$PR"; say "step 0: 2 GiB write probe written, fsynced, read back byte-identical, removed"

# ---- step 1: identity control ----
say "step 1: identity control (force-epoch 7) start"
launch LAUNCH_IDCTL_s42.json --arm T0 --no-mask --train-frac 1.0 --nested-epoch --force-epoch 7 --seed 42 \
    --folds 2023,202609 --out-root "$A/idctl" >> "$A/idctl.log" 2>&1 || stop "identity-control training rc!=0"
grep -q Traceback "$A/idctl.log" && stop "identity-control training Traceback"
env -i PATH=/usr/bin:/bin HOME=/root LC_CTYPE=C "$PY" -B "$A/devices_scratch/dlarch_nested_identity.py" PATH,HOME,LC_CTYPE \
    "$A/idctl/G1_T0_nomask_frac1_nestep_forceep7/f10_s42" "$W/T3/G1_T0_nomask_frac1/f10_s42" \
    /dev/shm/news2_2026-09-23/work/f10_s42 2023,202609 "$A/receipts/NESTED_IDENTITY_s42.json" >> "$LOG" 2>&1
grep -q '^NESTED_IDENTITY GREEN=True ' "$LOG" || stop "identity control NOT GREEN"
say "step 1: identity control GREEN"

# ---- step 3 (started first so it is polling when seed 42 lands) ----
sh "$A/devices_scratch/dlarch_run_nested_cells.sh" "42 2027 7" > "$W/CHAIN/nested_cells.out" 2>&1 &
CELLS=$!
say "step 3: cells driver pid $CELLS"

# ---- step 2: training, TWO GPU lanes (lead 18:0xZ: allowed, the engine run gate is enforced separately
#      by the cells driver). Lane A = 42 then 7, lane B = 2027. Each lane is a child of this process group
#      with its own log; a lane writes "LANE_<x>_DONE rc=<n>" at line start when it ends. ----
lane(){  # $1 = lane name, rest = seeds
  L=$1; shift; LRC=0
  for S in "$@"; do
    say "step 2: lane $L seed $S start"
    launch LAUNCH_MAIN_s$S.json --arm T0 --no-mask --train-frac 1.0 --nested-epoch --seed "$S" >> "$A/main_lane$L.log" 2>&1
    RC=$?
    say "step 2: lane $L seed $S rc=$RC $(grep -h "^DLARCH_TRAIN_DONE .*seed=$S " "$A/main_lane$L.log" | tail -1)"
    if [ $RC -ne 0 ]; then LRC=$RC; break; fi
  done
  echo "LANE_${L}_DONE rc=$LRC" >> "$A/main_lane$L.log"
  return $LRC
}
lane A 42 7 & LA=$!
lane B 2027 & LB=$!
say "step 2: lane A pid $LA, lane B pid $LB"
TRAIN_OK=1
wait $LA || TRAIN_OK=0
wait $LB || TRAIN_OK=0
grep -q '^LANE_A_DONE rc=0$' "$A/main_laneA.log" || TRAIN_OK=0
grep -q '^LANE_B_DONE rc=0$' "$A/main_laneB.log" || TRAIN_OK=0
grep -q Traceback "$A/main_laneA.log" "$A/main_laneB.log" && TRAIN_OK=0

# ---- wait for step 3 (if training failed, the cells driver would wait out its 12 h bound for seeds
#      that can never finish: stop it -- it is this pipeline's own child, pid recorded above) ----
if [ $TRAIN_OK -ne 1 ]; then kill "$CELLS" 2>/dev/null; say "step 3: cells driver pid $CELLS stopped because training failed"; fi
wait $CELLS; CRC=$?
say "step 3: cells driver rc=$CRC"
[ $TRAIN_OK -eq 1 ] || stop "training failed"
[ $CRC -eq 0 ] && grep -q '^NESTED_CELLS_DRIVER_DONE$' "$W/CHAIN/nested_cells_driver.log" || stop "cells driver not DONE"

# ---- step 4: verdict ----
cd "$W" && env -i PATH=/usr/bin:/bin HOME=/root LC_CTYPE=C "$PY" -B "$A/devices_scratch/dlarch_nested_verdict.py" PATH,HOME,LC_CTYPE \
    "$W" "$A/receipts/NESTED_IDENTITY_s42.json" "$W/receipts/NESTEP_VERDICT.json" >> "$LOG" 2>&1 || stop "verdict device rc!=0"
grep -q Traceback "$LOG" && stop "Traceback in pipeline log"
rm -rf "$CLAIM"
echo "R14_PIPELINE_DONE rc=0 $(grep -h '^NESTEP_VERDICT=' "$LOG" | tail -1)" >> "$LOG"
