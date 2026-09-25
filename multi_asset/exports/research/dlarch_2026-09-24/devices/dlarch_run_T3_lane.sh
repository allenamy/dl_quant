#!/bin/sh
# dlarch_run_T3_lane.sh -- one lane of the T3 main arm (seeds frozen by lead R1.4: 42, 2027, 7).
#
# CROSS-LOAD PRECONDITION, measured not assumed (receipt crosslevel_t3_20260925T135848Z):
#   T3_CROSSLOAD_VERDICT=IDENTICAL  power=HAS_POWER  solo=252s loaded=364s slowdown=1.44x
#   concurrency during run B: 36/37 samples at 2 trainers (97.3%), criterion >= 95% declared beforehand.
# So two lanes are permitted. This script is ONE lane; run it twice with different orderings to get two.
#
# WHY ONE LANE FIRST: the book-layer engine cells have priority (lead 2026-09-25) and each engine run
# needs 24 GiB by its own config gate. Measured: engine alone leaves ~29.8 GiB; one T3 lane takes ~4 GiB
# (leaves ~25.5, gate passes); two lanes take ~8 GiB (leaves ~21.5, the NEXT cell's gate REFUSES and the
# engine queue stalls). So: one lane while cells are running, two once they are done.
#
# FOLD COUNT IS NOT SETTLED. The frozen budget row (R9.4) says 3 seeds x 14 folds, but R4.2 argues that
# 14 folds produce NO 2026 F10 scores, and a 2026-segment reading taken from such a run is not merely
# absent -- it comes back as "the book was HELD all through 2026", which LOOKS like a measurement. The
# book gate (revision 2/3) makes 2026 central. Pending lead's ruling this lane runs `--folds all` (23),
# whose FIRST 14 are exactly the pre-2026 folds -- so nothing done here is wasted under either ruling,
# and if lead rules 14 the lane is simply stopped once fold 14 lands.
#
# usage: DLARCH_LANE=A sh dlarch_run_T3_lane.sh "42 2027 7"
set -u
W=/workspace/dlarch_2026-09-24
DEV=$W/t3_2026-09-25                 # T3 lives in its OWN dir; the delivered path stays untouched
PY=/workspace/venv/bin/python
LANE="${DLARCH_LANE:-X}"
SEEDS="${1:?usage: dlarch_run_T3_lane.sh \"<seed list>\"}"
CLAIMS=$W/t3_claims
LOG=$W/T3_lane_$LANE.log
ARM=T3
mkdir -p "$CLAIMS"

say(){ echo "$(date -u +%H:%M:%SZ) [T3 lane $LANE] $*" | tee -a "$LOG"; }

MYPGID=$(ps -o pgid= -p $$ | tr -d ' ')
printf 'pgid=%s pid=%s lane=%s owner=dlarch arm=T3 started=%s seeds=%s\n' \
  "$MYPGID" "$$" "$LANE" "$(date -u +%FT%TZ)" "$SEEDS" > "$W/T3_lane_$LANE.pgid"

[ -f "$DEV/dlarch_train_f10.py" ] || { say "REFUSING: no trainer in $DEV"; exit 9; }
say "=== T3 LANE START seeds: $SEEDS (pgid $MYPGID, trainer $(sha256sum "$DEV/dlarch_train_f10.py" | cut -c1-16)) ==="

trainers(){ ps -eo pid,pgid,args | awk '$3 ~ /\/python$/ && /dlarch_train_f10\.py/' | grep -c . ; }

for S in $SEEDS; do
  if ! mkdir "$CLAIMS/$S" 2>/dev/null; then
    say "seed $S: already claimed, skipping (not racing it -- two runners on one seed rebuilt each other's tree once today)"
    continue
  fi
  printf 'pgid=%s lane=%s claimed=%s\n' "$MYPGID" "$LANE" "$(date -u +%FT%TZ)" > "$CLAIMS/$S/owner"

  # a killed run leaves ONE fold dir with no FOLD_RECEIPT and the trainer does mkdir(exist_ok=False).
  # Clean at the execution point, so the lane is self-healing regardless of how it was stopped.
  INC=0
  for fd in "$W/T3/T3_clamp/f10_s$S"/*/; do
    [ -d "$fd" ] || continue
    if [ ! -f "$fd/FOLD_RECEIPT.json" ]; then say "seed $S: removing incomplete fold $(basename "$fd")"; rm -rf "$fd"; INC=$((INC+1)); fi
  done
  [ $INC -gt 0 ] && say "seed $S: cleaned $INC incomplete fold dir(s)"

  say "seed $S: start  trainers_before=$(trainers)"
  env -i PATH=/usr/bin:/bin HOME=/root LC_CTYPE=C nice -n 5 "$PY" -B "$DEV/dlarch_train_f10.py" \
      --env-whitelist PATH,HOME,LC_CTYPE --arm "$ARM" --seed "$S" --folds all \
      >> "$W/logs_T3_lane${LANE}_s$S.log" 2>&1
  RC=$?
  say "seed $S: rc=$RC"
  if [ $RC -ne 0 ]; then
    tail -4 "$W/logs_T3_lane${LANE}_s$S.log" | tee -a "$LOG"
    say "seed $S: giving up, releasing the claim so the other lane may retry"
    rm -rf "$CLAIMS/$S"
    continue
  fi
  NF=$(ls -d "$W/T3/T3_clamp/f10_s$S"/*/FOLD_RECEIPT.json 2>/dev/null | grep -c .)
  say "seed $S: DONE folds=$NF oof=$(sha256sum "$W/T3/T3_clamp/f10_s$S/F10_OOF.npz" 2>/dev/null | cut -c1-16)"
done
say "=== T3 LANE DONE ==="
