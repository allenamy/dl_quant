#!/bin/sh
# dlarch_run_nested_cells.sh -- R1.4 book-layer cells, one per seed as its training finishes.
# Derived from dlarch_run_f10full_cells.sh AFTER its item-6 class fix (3201239af): completion is judged by
# dlarch_done_check.py from content, never from a path existing. Differences, each deliberate:
#  1 ARM G1_T0_nomask_frac1_nestep; retention receipts RETAIN_NESTEP_s<seed>; its own claims and logs.
#  2 TEAM RUN GATE (lead 2026-09-26: at most TWO engine cells in parallel across the team): before each
#    chain_run this driver waits until at most ONE foreign bt_launch process group exists (read from the
#    process table by PGID, never signalled). chain_run's own gate (<=2 foreign) then passes trivially.
#  3 Bound 12 h (training of three sequential seeds is ~6 h).
#  4 Ends with a line that STARTS with the marker (no timestamp prefix) so a waiter can anchor on it.
# usage: sh dlarch_run_nested_cells.sh "42 2027 7"
set -u
W=/workspace/dlarch_2026-09-24
PY=/workspace/venv/bin/python
SEEDS="${1:?usage: dlarch_run_f10full_cells.sh \"<seed list>\"}"
ARM=G1_T0_nomask_frac1_nestep
REF=$W/chain/ref_nc_s42X/runs/DLARCH_REF_NC_s42X_scaled_rule_raw_UAFE
REFTAG=DLARCH_REF_NC_s42X_scaled_rule_raw_UAFE
ENG=/dev/shm/news2_2026-09-23/engine
LOG=$W/CHAIN/nested_cells_driver.log
NFOLD=23
DC="$PY -B $W/dlarch_done_check.py"   # completion is decided from content, never from a path existing (item 6)
FAILED=""

say(){ echo "$(date -u +%H:%M:%SZ) [nested-cells] $*" | tee -a "$LOG"; }

MYPGID=$(ps -o pgid= -p $$ | tr -d ' ')
printf 'pgid=%s pid=%s owner=dlarch driver=nested_cells started=%s seeds=%s\n' \
  "$MYPGID" "$$" "$(date -u +%FT%TZ)" "$SEEDS" > "$W/CHAIN/nested_cells_driver.pgid"
say "=== START (pgid $MYPGID) arm=$ARM seeds: $SEEDS ==="

$DC cell "$REF" >> "$LOG" 2>&1 || { say "REFUSING: reference cell NOT complete at $REF (DONE_CHECK above)"; exit 9; }
NCLAIM=$(ls -d "$W"/CHAIN/.claim_* 2>/dev/null | grep -c .)
[ "$NCLAIM" -eq 0 ] || say "NOTE: $NCLAIM foreign claim(s) present; per-seed claims below still protect us"

LEFT="$SEEDS"
for round in $(seq 1 720); do            # bound: 720 x 60 s = 12 h
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
    OUT=$W/receipts/RETAIN_NESTEP_s${S}.json
    EL=$W/CHAIN/engine_NESTEP_s$S.log
    if $DC retain "$OUT" --root "$W" >> "$LOG" 2>&1; then say "seed $S: retention already COMPLETE (content-checked), skipping"; continue; fi
    if ! mkdir "$W/CHAIN/.claim_NESTEP_s$S" 2>/dev/null; then
      say "seed $S: already claimed by another runner -- skipping, not racing it"
      continue
    fi
    printf 'pgid=%s pid=%s claimed=%s\n' "$MYPGID" "$$" "$(date -u +%FT%TZ)" \
      > "$W/CHAIN/.claim_NESTEP_s$S/owner"

    FREE_MB=$(( $(df -k --output=avail "$W" 2>/dev/null | tail -1) / 1024 ))
    say "seed $S: trained ($NF/$NFOLD folds); df-avail ${FREE_MB} MB (NOTE: df shows the whole disk and"
    say "          does NOT see this account's quota -- the real headroom was measured at 872 MB by a"
    say "          write probe, so the per-seed delete below is what keeps us inside it)"
    # ---- team run gate: at most ONE foreign bt_launch group, so mine makes two ----
    for g in $(seq 1 240); do
      NF_ENG=$(ps -eo pgid=,args= | awk -v me="$MYPGID" '$1 != me && $0 ~ /bt_launch[.]py/ {print $1}' | sort -u | grep -c .)
      [ "$NF_ENG" -le 1 ] && break
      [ "$g" -eq 1 ] && say "seed $S: run gate -- $NF_ENG foreign engine groups, waiting for <= 1"
      sleep 60
    done
    if [ "$NF_ENG" -gt 1 ]; then
      say "seed $S: run gate never opened in 4 h ($NF_ENG foreign groups) -- cell NOT run, counted as FAILED"
      FAILED="$FAILED $S"; rm -rf "$W/CHAIN/.claim_NESTEP_s$S"; continue
    fi
    say "seed $S: run gate passed (foreign engine groups $NF_ENG)"
    say "seed $S: book cell start"
    echo "=== attempt $(date -u +%FT%TZ) by pgid $MYPGID ===" >> "$EL"
    env -i PATH=/usr/bin:/bin HOME=/root LC_CTYPE=C "$PY" -B "$W/dlarch_chain_run.py" \
        PATH,HOME,LC_CTYPE "$W/CHAIN/NESTEP_s$S" --seed "$S" --train-arm "$ARM" --engine >> "$EL" 2>&1
    RC=$?
    say "seed $S: engine rc=$RC  $(grep -h 'engine gate' "$EL" | tail -1)"
    if [ $RC -ne 0 ]; then
      tail -5 "$EL" | tee -a "$LOG"
      rm -rf "$W/CHAIN/.claim_NESTEP_s$S"
      continue
    fi
    say "seed $S: retention start (--delete after its four preconditions; residual loss is recorded)"
    env -i PATH=/usr/bin:/bin HOME=/root LC_CTYPE=C "$PY" -B "$W/dlarch_cell_retain.py" \
        --env-whitelist PATH,HOME,LC_CTYPE --cell "$CELL" --tag "$TAG" \
        --control-cell "$REF" --control-tag "$REFTAG" --engine "$ENG" \
        --out "$OUT" --delete --cell-root "$W/chain/${ARM}_s$S" > "$W/CHAIN/retain_NESTEP_s$S.log" 2>&1
    say "seed $S: retention rc=$?  $(grep -h 'P1 judge table' "$W/CHAIN/retain_NESTEP_s$S.log" | tail -1)"
    say "seed $S: $(grep -h 'DLARCH_CELL_RETAIN' "$W/CHAIN/retain_NESTEP_s$S.log" | tail -1)"
    $DC retain "$OUT" --root "$W" >> "$LOG" 2>&1 || { FAILED="$FAILED $S"; say "seed $S: retention NOT complete -- counted as FAILED"; }
    say "seed $S: workspace usage now $(du -sh $W 2>/dev/null | cut -f1)"
    rm -rf "$W/CHAIN/.claim_NESTEP_s$S"
  done
  LEFT=$(echo "$NEWLEFT" | sed 's/^ *//')
  [ -z "$LEFT" ] && break
  sleep 60
done
if [ -n "$LEFT" ]; then
  say "BOUND EXPIRED with seeds still untrained: $LEFT -- their cells were NOT run"
  say "=== NESTED_CELLS_DRIVER_INCOMPLETE untrained: $LEFT ==="; echo "NESTED_CELLS_DRIVER_INCOMPLETE" >> "$LOG"
  exit 1
fi
if [ -n "$FAILED" ]; then say "=== NESTED_CELLS_DRIVER_INCOMPLETE failed:$FAILED ==="; echo "NESTED_CELLS_DRIVER_INCOMPLETE" >> "$LOG"; exit 1; fi
say "all R1.4 cells done"
say "=== NESTED_CELLS_DRIVER_DONE ==="
echo "NESTED_CELLS_DRIVER_DONE" >> "$LOG"
