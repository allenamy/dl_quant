#!/bin/sh
# run_s2027_identity.sh -- lead ruling C1.7 (option b): the 2-fold identity control at seed 2027.
#
# WHAT IT ANSWERS. The gate's baseline at seed 7 is dlarch's own --no-mask product, not an in-service
# artifact, because news2's tree has an NC-recipe F10 only at s42 and s2027. G1 proved the two bitwise
# identical AT s42, on folds 2023 and 202609. This runs the SAME two folds at s2027, where both objects
# exist, so the inherited claim rests on two seeds instead of one -- or is refuted.
#
# TIMING. lead asked for "the gap between seeds". Measured: there is no gap -- run_f10full_main.sh is a
# `set -e` sequential loop and seed 2027 started in the SAME SECOND seed 42 finished (06:00:39Z). So this
# waits for seed 2027's 23 folds and then runs CONCURRENTLY with seed 7's training: 2 folds, about four
# minutes, ~2.6 GiB of GPU against a card with ample headroom. Running it any later would put it after the
# last training, and lead requires the result BEFORE the verdict.
#
# WRITES. --out-root into its own directory. At --train-frac 0.85 the arm string has no suffix, so it
# would otherwise land in T3/G1_T0_nomask/f10_s2027 -- inside the tree that holds delivered G1 cells.
# Nothing delivered is touched.
set -u
W=/workspace/dlarch_2026-09-24
A=$W/f10full_2026-09-26
PY=/workspace/venv/bin/python
PIN=db6771e30fb7d1befcf9bb77f4c0504131fc0d491e02dc45bab15ed04e5d8e61
OUT=$A/s2027_identity
LOG=$A/s2027_identity.log
say(){ echo "$(date -u +%H:%M:%SZ) [s2027-id] $*" | tee -a "$LOG"; }

say "=== START: waiting for F10_FULL seed 2027 to finish its 23 folds ==="
for i in $(seq 1 180); do
  NF=$(ls -d "$W/T3/G1_T0_nomask_frac1/f10_s2027"/*/FOLD_RECEIPT.json 2>/dev/null | grep -c .)
  if [ "$NF" -ge 23 ]; then say "seed 2027 training done ($NF/23)"; break; fi
  if ! pgrep -f "run_f10full_main.sh" >/dev/null 2>&1; then
    say "REFUSING: the main arm is no longer running and seed 2027 has only $NF/23 folds"
    say "=== S2027_IDENTITY_ABORTED_MAIN_GONE ==="; exit 3
  fi
  [ "$i" -eq 1 ] && say "  waiting (currently $NF/23)"
  sleep 30
done
NF=$(ls -d "$W/T3/G1_T0_nomask_frac1/f10_s2027"/*/FOLD_RECEIPT.json 2>/dev/null | grep -c .)
if [ "$NF" -lt 23 ]; then
  say "BOUND EXPIRED: seed 2027 still at $NF/23 after 90 min -- control NOT run"
  say "=== S2027_IDENTITY_BOUND_EXPIRED ==="; exit 1
fi

say "running 2 folds (2023, 202609) at --train-frac 0.85 --no-mask, seed 2027, into $OUT"
env -u PWD -u _ env -i PATH=/usr/bin:/bin HOME=/root LC_CTYPE=C "$PY" "$W/dlarch_f10full_launch.py" \
    PATH,HOME,LC_CTYPE "$A" "$PIN" "$A/PREFLIGHT_F10FULL.json" "$A/receipts/LAUNCH_S2027_ID.json" \
    -- --arm T0 --no-mask --train-frac 0.85 --seed 2027 --folds 2023,202609 --out-root "$OUT" \
    >> "$LOG" 2>&1
RC=$?
say "training rc=$RC"
if [ $RC -ne 0 ]; then say "=== S2027_IDENTITY_TRAIN_FAILED ==="; exit $RC; fi

say "bitwise comparison against the IN-SERVICE NC F10 at s2027"
env -i PATH=/usr/bin:/bin HOME=/root LC_CTYPE=C "$PY" "$W/dlarch_identity_compare.py" \
    --a /dev/shm/news2_2026-09-23/work/f10_s2027 \
    --b "$OUT/G1_T0_nomask/f10_s2027" \
    --folds 2023,202609 --label C1.7_s2027_nomask_vs_inservice_NC \
    --out "$A/receipts/S2027_IDENTITY_2026-09-26.json" \
    --env-whitelist PATH,HOME,LC_CTYPE >> "$LOG" 2>&1
say "comparison rc=$?  $(grep -h 'DLARCH_IDENTITY' "$LOG" | tail -1)"
grep -h -E 'POSITIVE_CONTROL|IDENTICAL|DIFFER' "$LOG" | tail -5 | tee -a "$LOG"
say "=== S2027_IDENTITY_DONE ==="
