#!/bin/sh
# dlarch_run_cells.sh -- run the remaining T0 book-layer cells one at a time, then retain each.
#
# ONE AT A TIME, on purpose: each engine run needs ~24 GiB by its own config, and the run gate inside
# dlarch_chain_run.py is what decides whether it may start (foreign bt_launch groups, cgroup headroom,
# /dev/shm). This script never second-guesses that gate -- it just serialises the work so the gate is
# asked once per cell instead of several at once.
#
# WHY A SCRIPT AND NOT A LOOP TYPED INTO ssh: a chain typed as `cd X && cmd1 & cmd2 &` backgrounds the
# WHOLE chain, so the `cd` never applies to cmd2 -- that is exactly how engine cell s7 ended up looking
# for /root/dlarch_chain_run.py. Absolute paths everywhere here, and the script is transferred and md5
# compared before running (generation is transmission).
#
# RESUMABLE: a cell whose log already carries the producer's own DLARCH_CHAIN line is skipped, and a cell
# whose retention receipt already exists is not retained twice. So this can be re-run after any stop.
#
# usage: sh dlarch_run_cells.sh "11 23 101 3 5"
set -u
W=/workspace/dlarch_2026-09-24
PY=/workspace/venv/bin/python
SEEDS="${1:?usage: dlarch_run_cells.sh \"<seed list>\"}"
REF=$W/chain/ref_nc_s42X/runs/DLARCH_REF_NC_s42X_scaled_rule_raw_UAFE
REFTAG=DLARCH_REF_NC_s42X_scaled_rule_raw_UAFE
ENG=/dev/shm/news2_2026-09-23/engine
LOG=$W/CHAIN/cells_driver.log
DC="$PY -B $W/dlarch_done_check.py"   # completion is decided from content, never from a path existing (item 6)
FAILED=""

say(){ echo "$(date -u +%H:%M:%SZ) [cells] $*" | tee -a "$LOG"; }

MYPGID=$(ps -o pgid= -p $$ | tr -d ' ')
printf 'pgid=%s pid=%s owner=dlarch driver=run_cells started=%s seeds=%s\n' \
  "$MYPGID" "$$" "$(date -u +%FT%TZ)" "$SEEDS" > "$W/CHAIN/cells_driver.pgid"
say "=== START seeds: $SEEDS  (pgid $MYPGID) ==="

$DC cell "$REF" >> "$LOG" 2>&1 || { say "REFUSING: reference cell NOT complete at $REF (DONE_CHECK above) -- dbar is a PAIRED difference and cannot be formed without it"; exit 9; }

for S in $SEEDS; do
  EL=$W/CHAIN/engine_s$S.log
  TAG=DLARCH_T0_s${S}_scaled_rule_raw_UAFE
  CELL=$W/chain/s$S/runs/$TAG
  OUT=$W/receipts/RETAIN_s${S}_2026-09-25.json

  # ---- ATOMIC CLAIM, before anything else ----------------------------------------------------------
  # `mkdir` is atomic, so exactly one runner can own a seed. This is not paranoia about two drivers: on
  # the first launch I had ALREADY hand-started seed 7, and the driver's "is it done?" test was
  # `grep DLARCH_CHAIN <log>` -- which is false for a cell that is still RUNNING. So it started a second
  # chain_run on the same seed, the two rebuilt each other's tree, and BOTH died with "combo failed".
  # "The log lacks the done marker" is not the same as "nothing is working on it".
  if ! mkdir "$W/CHAIN/.claim_s$S" 2>/dev/null; then
    say "seed $S: already claimed by another runner ($W/CHAIN/.claim_s$S exists) -- skipping, NOT racing it"
    continue
  fi
  printf 'pgid=%s pid=%s claimed=%s\n' "$MYPGID" "$$" "$(date -u +%FT%TZ)" > "$W/CHAIN/.claim_s$S/owner"

  # ---- engine, unless the producer already announced completion for this cell ----
  if [ -f "$EL" ] && grep -q "DLARCH_CHAIN seed=$S " "$EL" 2>/dev/null; then
    say "seed $S: engine already done (producer's own DLARCH_CHAIN line present), skipping"
  else
    say "seed $S: engine start"
    # >> not >: the previous attempt's log is EVIDENCE. Clobbering it destroyed the only record of what
    # the hand-started s7 run had done, which is how its state became unknown rather than diagnosable.
    echo "=== attempt $(date -u +%FT%TZ) by pgid $MYPGID ===" >> "$EL"
    env -i PATH=/usr/bin:/bin HOME=/root LC_CTYPE=C "$PY" -B "$W/dlarch_chain_run.py" \
        PATH,HOME,LC_CTYPE "$W/CHAIN/s$S" --seed "$S" --engine >> "$EL" 2>&1
    RC=$?
    say "seed $S: engine rc=$RC  $(grep -h 'engine gate' "$EL" | tail -1)"
    if [ $RC -ne 0 ]; then
      say "seed $S: FAILED -- last lines follow; moving to the next seed rather than stopping the queue"
      tail -5 "$EL" | tee -a "$LOG"
      rm -rf "$W/CHAIN/.claim_s$S"    # rm -rf, not rmdir: the claim dir holds an owner file
      continue
    fi
  fi

  # ---- retention: the four preconditions are the gate that PERMITS freeing the PATH npz ----
  if $DC retain "$OUT" --root "$W" >> "$LOG" 2>&1; then
    say "seed $S: retention already COMPLETE (content-checked), skipping"
    rm -rf "$W/CHAIN/.claim_s$S"
    continue
  fi
  if [ ! -d "$CELL" ]; then
    say "seed $S: no cell dir at $CELL -- cannot retain"
    rm -rf "$W/CHAIN/.claim_s$S"
    continue
  fi
  say "seed $S: retention start"
  env -i PATH=/usr/bin:/bin HOME=/root LC_CTYPE=C "$PY" -B "$W/dlarch_cell_retain.py" \
      --env-whitelist PATH,HOME,LC_CTYPE --cell "$CELL" --tag "$TAG" \
      --control-cell "$REF" --control-tag "$REFTAG" --engine "$ENG" \
      --out "$OUT" --delete --cell-root "$W/chain/s$S" > "$W/CHAIN/retain_s$S.log" 2>&1
  RC=$?
  say "seed $S: retention rc=$RC  $(grep -h 'P1 judge table' "$W/CHAIN/retain_s$S.log" | tail -1)"
  say "seed $S: $(grep -h 'DLARCH_CELL_RETAIN' "$W/CHAIN/retain_s$S.log" | tail -1)"
  $DC retain "$OUT" --root "$W" >> "$LOG" 2>&1 || { FAILED="$FAILED $S"; say "seed $S: retention rc=$RC but NOT complete -- counted as FAILED"; }
  say "seed $S: usage now $(du -sh $W 2>/dev/null | cut -f1)"
  rm -rf "$W/CHAIN/.claim_s$S"
done
if [ -n "$FAILED" ]; then say "=== CELLS_DRIVER_INCOMPLETE failed:$FAILED ==="; exit 1; fi
say "=== CELLS_DRIVER_DONE ==="
