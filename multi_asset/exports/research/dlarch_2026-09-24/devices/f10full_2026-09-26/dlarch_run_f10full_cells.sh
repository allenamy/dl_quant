#!/bin/sh
# dlarch_run_f10full_cells.sh -- PIPELINE the F10_FULL book-layer cells, one per seed as it finishes.
#
# Adapted from dlarch_run_t3_cells.sh (same claim/bound/receipt shape). Differences, each deliberate:
#
#  1 ARM. G1_T0_nomask_frac1 (--arm T0 --no-mask --train-frac 1.0). The arm name carries the fraction
#    because the trainer appends it off-default, so these cells cannot collide with the delivered
#    G1_T0_nomask ones.
#  2 --delete, after first getting my own reason for NOT deleting wrong and checking it. I had written
#    "keep the cells, because shuffle-future and the real-population G4/rank censuses are queued against
#    them". That was false, and I checked instead of shipping it: dlarch_g4_census.py and
#    dlarch_rank_path_control.py read NO cell file at all (they call the frozen chain on constructed or
#    trainer-side inputs), and dlarch_f10full_leak.py reads scores.npz, a TRAINING artifact. Every queued
#    consumer is trainer-side. Meanwhile the MEASURED quota headroom is 872 MB -- a 1.2 GB probe failed
#    with "Disk quota exceeded" after 872 MB -- while three cells need about 1.08 GB. So keeping all three
#    would have run the third one out of quota mid-write, and json.dump(x, open(p,"w")) does not raise on
#    a full disk, so the failure could have surfaced as a SILENTLY TRUNCATED receipt rather than an error.
#    Deleting per cell keeps peak usage at one cell. The retain device gates the delete on its four
#    preconditions and records the residual loss: any NEW question needing the 5-minute NAV for these
#    cells can only be answered by re-running them.
#  3 COMPLETENESS is checked twice, by different means: this script counts FOLD_RECEIPT.json files, and
#    dlarch_chain_run.py independently refuses a TRAIN_RECEIPT whose status is not the finished one. The
#    file count alone was not enough -- merge_folds writes TRAIN_RECEIPT.json from fold 1 with status
#    PARTIAL_FOLDS, so "the receipt exists" is true 22 folds before the arm is done.
#  4 NO waiting on the T0 cell queue. That queue reported done and holds no claims (both checked below,
#    because a done-marker is about "finished" and a claim is about "someone is working", and reading the
#    first as the second is how two chain_runs collided on seed 7).
#
# usage: sh dlarch_run_f10full_cells.sh "42 2027 7"
set -u
W=/workspace/dlarch_2026-09-24
PY=/workspace/venv/bin/python
SEEDS="${1:?usage: dlarch_run_f10full_cells.sh \"<seed list>\"}"
ARM=G1_T0_nomask_frac1
REF=$W/chain/ref_nc_s42X/runs/DLARCH_REF_NC_s42X_scaled_rule_raw_UAFE
REFTAG=DLARCH_REF_NC_s42X_scaled_rule_raw_UAFE
ENG=/dev/shm/news2_2026-09-23/engine
LOG=$W/CHAIN/f10full_cells_driver.log
NFOLD=23

say(){ echo "$(date -u +%H:%M:%SZ) [f10full-cells] $*" | tee -a "$LOG"; }

MYPGID=$(ps -o pgid= -p $$ | tr -d ' ')
printf 'pgid=%s pid=%s owner=dlarch driver=f10full_cells started=%s seeds=%s\n' \
  "$MYPGID" "$$" "$(date -u +%FT%TZ)" "$SEEDS" > "$W/CHAIN/f10full_cells_driver.pgid"
say "=== START (pgid $MYPGID) arm=$ARM seeds: $SEEDS ==="

[ -d "$REF" ] || { say "REFUSING: reference cell missing at $REF"; exit 9; }
NCLAIM=$(ls -d "$W"/CHAIN/.claim_* 2>/dev/null | grep -c .)
[ "$NCLAIM" -eq 0 ] || say "NOTE: $NCLAIM foreign claim(s) present; per-seed claims below still protect us"

LEFT="$SEEDS"
for round in $(seq 1 240); do            # bound: 240 x 60 s = 4 h
  NEWLEFT=""
  for S in $LEFT; do
    TR=$W/T3/$ARM/f10_s$S/TRAIN_RECEIPT.json
    NF=$(ls -d "$W/T3/$ARM/f10_s$S"/*/FOLD_RECEIPT.json 2>/dev/null | grep -c .)
    if [ ! -f "$TR" ] || [ "$NF" -lt "$NFOLD" ]; then
      NEWLEFT="$NEWLEFT $S"
      continue
    fi
    TAG=DLARCH_${ARM}_s${S}_scaled_rule_raw_UAFE
    CELL=$W/chain/${ARM}_s$S/runs/$TAG
    OUT=$W/receipts/RETAIN_F10FULL_s${S}_2026-09-26.json
    EL=$W/CHAIN/engine_F10FULL_s$S.log
    if [ -d "$OUT" ]; then say "seed $S: already retained, skipping"; continue; fi
    if ! mkdir "$W/CHAIN/.claim_F10FULL_s$S" 2>/dev/null; then
      say "seed $S: already claimed by another runner -- skipping, not racing it"
      continue
    fi
    printf 'pgid=%s pid=%s claimed=%s\n' "$MYPGID" "$$" "$(date -u +%FT%TZ)" \
      > "$W/CHAIN/.claim_F10FULL_s$S/owner"

    FREE_MB=$(( $(df -k --output=avail "$W" 2>/dev/null | tail -1) / 1024 ))
    say "seed $S: trained ($NF/$NFOLD folds); df-avail ${FREE_MB} MB (NOTE: df shows the whole disk and"
    say "          does NOT see this account's quota -- the real headroom was measured at 872 MB by a"
    say "          write probe, so the per-seed delete below is what keeps us inside it)"
    say "seed $S: book cell start"
    echo "=== attempt $(date -u +%FT%TZ) by pgid $MYPGID ===" >> "$EL"
    env -i PATH=/usr/bin:/bin HOME=/root LC_CTYPE=C "$PY" -B "$W/dlarch_chain_run.py" \
        PATH,HOME,LC_CTYPE "$W/CHAIN/F10FULL_s$S" --seed "$S" --train-arm "$ARM" --engine >> "$EL" 2>&1
    RC=$?
    say "seed $S: engine rc=$RC  $(grep -h 'engine gate' "$EL" | tail -1)"
    if [ $RC -ne 0 ]; then
      tail -5 "$EL" | tee -a "$LOG"
      rm -rf "$W/CHAIN/.claim_F10FULL_s$S"
      continue
    fi
    say "seed $S: retention start (--delete after its four preconditions; residual loss is recorded)"
    env -i PATH=/usr/bin:/bin HOME=/root LC_CTYPE=C "$PY" -B "$W/dlarch_cell_retain.py" \
        --env-whitelist PATH,HOME,LC_CTYPE --cell "$CELL" --tag "$TAG" \
        --control-cell "$REF" --control-tag "$REFTAG" --engine "$ENG" \
        --out "$OUT" --delete --cell-root "$W/chain/${ARM}_s$S" > "$W/CHAIN/retain_F10FULL_s$S.log" 2>&1
    say "seed $S: retention rc=$?  $(grep -h 'P1 judge table' "$W/CHAIN/retain_F10FULL_s$S.log" | tail -1)"
    say "seed $S: $(grep -h 'DLARCH_CELL_RETAIN' "$W/CHAIN/retain_F10FULL_s$S.log" | tail -1)"
    say "seed $S: workspace usage now $(du -sh $W 2>/dev/null | cut -f1)"
    rm -rf "$W/CHAIN/.claim_F10FULL_s$S"
  done
  LEFT=$(echo "$NEWLEFT" | sed 's/^ *//')
  [ -z "$LEFT" ] && break
  sleep 60
done
if [ -n "$LEFT" ]; then
  say "BOUND EXPIRED with seeds still untrained: $LEFT -- their cells were NOT run"
  say "=== F10FULL_CELLS_DRIVER_DONE_WITH_MISSING ==="
  exit 1
fi
say "all F10_FULL cells done"
say "=== F10FULL_CELLS_DRIVER_DONE ==="
