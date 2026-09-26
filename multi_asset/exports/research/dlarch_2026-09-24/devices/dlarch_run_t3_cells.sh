#!/bin/sh
# dlarch_run_t3_cells.sh -- PIPELINE the T3 book-layer cells (lead 2026-09-25).
#
# Each T3 seed's book cell runs as soon as THAT seed finishes training, instead of waiting for 3/3. The
# GATE's verdict still waits for 3/3 and is still produced by the device, not by this script -- this only
# removes dead time between "seed trained" and "cell run".
#
# PRECEDENCE: T0's cells have priority (they block fresh's family verdict and the DL book gate), so this
# waits until the T0 cell queue is finished AND holds no claims. A done-marker alone is not enough: a
# marker is about "finished", a claim is about "someone is working", and treating the first as the second
# is how two chain_runs collided on seed 7 today.
#
# WHY PAIRING AGAINST THE ALREADY-FREED T0 CELLS STILL WORKS (checked before writing this, because it
# would otherwise be a silent dead end): the gate's sd(d) pairs T3 against T0 of the SAME seed, and T0's
# PATH npz have already been freed. But the frozen judge's dbar(pn, po, m, days) reads only a["A"] and
# a["r"], and the retained small series carries exactly those -- `anchors` (9252,) and
# `r_per_path` (32, 9252). So d_k is recoverable two independent ways:
#   (i)  by linearity: d_k = dbar(T3_k - NC) - dbar(T0_k - NC), since both use the same pairing and mask;
#   (ii) directly, pairing the two small series through the frozen dbar.
# Both routes will be computed and required to agree, rather than trusting either alone.
#
# usage: sh dlarch_run_t3_cells.sh "42 2027 7"
set -u
W=/workspace/dlarch_2026-09-24
PY=/workspace/venv/bin/python
SEEDS="${1:?usage: dlarch_run_t3_cells.sh \"<seed list>\"}"
REF=$W/chain/ref_nc_s42X/runs/DLARCH_REF_NC_s42X_scaled_rule_raw_UAFE
REFTAG=DLARCH_REF_NC_s42X_scaled_rule_raw_UAFE
ENG=/dev/shm/news2_2026-09-23/engine
DRV=$W/CHAIN/cells_driver.log
LOG=$W/CHAIN/t3_cells_driver.log
DC="$PY -B $W/dlarch_done_check.py"   # completion is decided from content, never from a path existing (item 6)
FAILED=""
NFOLD=23                      # lead's ruling R10.4: 23 folds per T3 seed, not 14

say(){ echo "$(date -u +%H:%M:%SZ) [t3cells] $*" | tee -a "$LOG"; }

MYPGID=$(ps -o pgid= -p $$ | tr -d ' ')
printf 'pgid=%s pid=%s owner=dlarch driver=t3_cells started=%s seeds=%s\n' \
  "$MYPGID" "$$" "$(date -u +%FT%TZ)" "$SEEDS" > "$W/CHAIN/t3_cells_driver.pgid"
say "=== START (pgid $MYPGID) seeds: $SEEDS ==="

$DC cell "$REF" >> "$LOG" 2>&1 || { say "REFUSING: reference cell NOT complete at $REF (DONE_CHECK above)"; exit 9; }

# ---- wait for the T0 cell queue to be finished AND idle ----
for i in $(seq 1 180); do
  if grep -q ' === CELLS_DRIVER_DONE ===$' "$DRV" 2>/dev/null; then
    [ "$(ls -d "$W"/CHAIN/.claim_s* 2>/dev/null | grep -c .)" -eq 0 ] && break
  fi
  sleep 20
done
if ! grep -q ' === CELLS_DRIVER_DONE ===$' "$DRV" 2>/dev/null; then
  say "BOUND EXPIRED: T0 cell queue never reported done -- not starting T3 cells, reporting instead"
  exit 1
fi
say "T0 cell queue finished and idle; T0 retention receipts: $(ls -d $W/receipts/RETAIN_s*_2026-09-25.json 2>/dev/null | grep -c .)"

# ---- poll for trained T3 seeds; run each cell as soon as its seed is complete ----
LEFT="$SEEDS"
for round in $(seq 1 180); do            # bound: 180 x 60 s = 3 h
  NEWLEFT=""
  for S in $LEFT; do
    TR=$W/T3/T3_clamp/f10_s$S/TRAIN_RECEIPT.json
    NF=$(ls -d "$W/T3/T3_clamp/f10_s$S"/*/FOLD_RECEIPT.json 2>/dev/null | grep -c .)
    if [ ! -f "$TR" ] || [ "$NF" -lt "$NFOLD" ]; then
      NEWLEFT="$NEWLEFT $S"
      continue
    fi
    TAG=DLARCH_T3_clamp_s${S}_scaled_rule_raw_UAFE
    CELL=$W/chain/T3_clamp_s$S/runs/$TAG
    OUT=$W/receipts/RETAIN_T3_s${S}_2026-09-25.json
    EL=$W/CHAIN/engine_T3_s$S.log
    if $DC retain "$OUT" --root "$W" >> "$LOG" 2>&1; then say "seed $S: T3 retention already COMPLETE (content-checked), skipping"; continue; fi
    if ! mkdir "$W/CHAIN/.claim_T3_s$S" 2>/dev/null; then
      say "seed $S: T3 cell already claimed by another runner -- skipping, not racing it"
      continue
    fi
    printf 'pgid=%s pid=%s claimed=%s\n' "$MYPGID" "$$" "$(date -u +%FT%TZ)" > "$W/CHAIN/.claim_T3_s$S/owner"

    say "seed $S: trained ($NF/$NFOLD folds) -> T3 book cell start"
    echo "=== attempt $(date -u +%FT%TZ) by pgid $MYPGID ===" >> "$EL"
    env -i PATH=/usr/bin:/bin HOME=/root LC_CTYPE=C "$PY" -B "$W/dlarch_chain_run.py" \
        PATH,HOME,LC_CTYPE "$W/CHAIN/T3_s$S" --seed "$S" --train-arm T3_clamp --engine >> "$EL" 2>&1
    RC=$?
    say "seed $S: engine rc=$RC  $(grep -h 'engine gate' "$EL" | tail -1)"
    if [ $RC -ne 0 ]; then
      tail -5 "$EL" | tee -a "$LOG"
      rm -rf "$W/CHAIN/.claim_T3_s$S"
      continue
    fi
    say "seed $S: retention start"
    env -i PATH=/usr/bin:/bin HOME=/root LC_CTYPE=C "$PY" -B "$W/dlarch_cell_retain.py" \
        --env-whitelist PATH,HOME,LC_CTYPE --cell "$CELL" --tag "$TAG" \
        --control-cell "$REF" --control-tag "$REFTAG" --engine "$ENG" \
        --out "$OUT" --delete --cell-root "$W/chain/T3_clamp_s$S" > "$W/CHAIN/retain_T3_s$S.log" 2>&1
    say "seed $S: retention rc=$?  $(grep -h 'P1 judge table' "$W/CHAIN/retain_T3_s$S.log" | tail -1)"
    $DC retain "$OUT" --root "$W" >> "$LOG" 2>&1 || { FAILED="$FAILED $S"; say "seed $S: retention NOT complete -- counted as FAILED"; }
    say "seed $S: $(grep -h 'DLARCH_CELL_RETAIN' "$W/CHAIN/retain_T3_s$S.log" | tail -1)"
    say "seed $S: usage now $(du -sh $W 2>/dev/null | cut -f1)"
    rm -rf "$W/CHAIN/.claim_T3_s$S"
  done
  LEFT=$(echo "$NEWLEFT" | sed 's/^ *//')
  [ -z "$LEFT" ] && break
  sleep 60
done
if [ -n "$LEFT" ]; then
  say "BOUND EXPIRED with seeds still untrained: $LEFT  -- cells for these were NOT run"
fi
if [ -n "$LEFT" ] || [ -n "$FAILED" ]; then
  say "=== T3_CELLS_DRIVER_INCOMPLETE untrained:${LEFT:-none} failed:${FAILED:-none} ==="; exit 1
fi
say "all T3 cells done"
say "=== T3_CELLS_DRIVER_DONE ==="
