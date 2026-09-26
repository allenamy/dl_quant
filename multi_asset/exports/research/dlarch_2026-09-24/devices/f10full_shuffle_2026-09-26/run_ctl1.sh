#!/bin/sh
# run_ctl1.sh -- control 1 (shuffle-future), prereg C1.11.3: retrain fold 202609 ONLY, seed 42, on labels
# permuted inside each anchor's (member AND finite) cells; recipe otherwise = the F10_FULL main arm
# (--arm T0 --no-mask --train-frac 1.0). Then the frozen-criterion verdict (dlarch_ctl1_verdict.py).
#
# Launch line = the main arm's (run_f10full_main.sh) with three declared differences: the shuffle arm dir
# and its pinned trainer sha, --folds 202609, --shuffle-labels. Nothing else changes.
#
# CLAIM: an atomic mkdir; a second runner exits without touching anything. PGID + pid written into the
# claim and into ctl1.pgid. SUCCESS for a waiter = a line that STARTS with 'CTL1_RUN_DONE rc=0' AND a
# line that starts with 'CTL1_VERDICT='; any 'Traceback' in ctl1.log is a failure.
set -u
W=/workspace/dlarch_2026-09-24
A=$W/f10full_shuffle_2026-09-26
PIN=526794e8dceefff2e35f290c6aadc99074edcc7a7468bda81aee15ab6a69af77
PY=/workspace/venv/bin/python
LOG=$A/ctl1.log
FOLD=$W/T3/G1_T0_nomask_SHUFFLED_frac1/f10_s42/202609
CLAIM=$W/CHAIN/.claim_CTL1_s42

MYPGID=$(ps -o pgid= -p $$ | tr -d ' ')
if ! mkdir "$CLAIM" 2>/dev/null; then
  echo "$(date -u +%H:%M:%SZ) REFUSING: $CLAIM exists -- another runner holds control 1" | tee -a "$LOG"; exit 4
fi
printf 'pgid=%s pid=%s owner=dlarch job=ctl1_shuffle started=%s\n' "$MYPGID" "$$" "$(date -u +%FT%TZ)" \
  | tee "$CLAIM/owner" > "$A/ctl1.pgid"
say(){ echo "$(date -u +%H:%M:%SZ) [ctl1] $*" | tee -a "$LOG"; }
say "=== START pgid=$MYPGID pid=$$ ==="
# ordering fact, recorded as a field at start: the shuffled arm must have produced nothing yet
N0=$(find "$W/T3" -path '*SHUFFLED*' -type f 2>/dev/null | wc -l)
say "shuffled_outputs_before_start=$N0"
[ "$N0" -eq 0 ] || { say "REFUSING: shuffled outputs already exist"; rm -rf "$CLAIM"; exit 5; }
say "gpu before: $(nvidia-smi --query-gpu=utilization.gpu,memory.used --format=csv,noheader)"

env -u PWD -u _ env -i PATH=/usr/bin:/bin HOME=/root LC_CTYPE=C "$PY" "$W/dlarch_f10full_launch.py" \
    PATH,HOME,LC_CTYPE "$A" "$PIN" "$A/PREFLIGHT_F10FULL.json" "$A/receipts/LAUNCH_CTL1_s42.json" \
    -- --arm T0 --no-mask --train-frac 1.0 --seed 42 --folds 202609 --shuffle-labels >> "$LOG" 2>&1
RC=$?
say "training rc=$RC"
if [ $RC -ne 0 ] || grep -q Traceback "$LOG"; then
  say "=== CTL1_TRAIN_FAILED ==="; echo "CTL1_RUN_DONE rc=1" >> "$LOG"; rm -rf "$CLAIM"; exit 1
fi

cd "$W" && env -i PATH=/usr/bin:/bin HOME=/root LC_CTYPE=C "$PY" -B "$W/dlarch_ctl1_verdict.py" \
    PATH,HOME,LC_CTYPE "$FOLD" "$W/receipts/CTL1_POWER_202609_2026-09-26.json" "$W/dlarch_ctl1_power.py" \
    "$W/receipts/CTL1_VERDICT_2026-09-26.json" >> "$LOG" 2>&1
RC=$?
say "verdict rc=$RC"
rm -rf "$CLAIM"
if [ $RC -ne 0 ] || grep -q Traceback "$LOG"; then echo "CTL1_RUN_DONE rc=1" >> "$LOG"; exit 1; fi
echo "CTL1_RUN_DONE rc=0" >> "$LOG"
