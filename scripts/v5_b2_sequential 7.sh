#!/usr/bin/env bash
# Sequential launcher for V5 B.2 loss screen on pod.
#
# Run AFTER B.1 winner identified and configs generated via v5_b2_gen_configs.py.
# Skips configs whose fold_0/test_preds.npz already exists (idempotent).

set -u
cd "$(dirname "$0")/.."

OUT=experiments/v5_screen/B2
mkdir -p "$OUT" logs

run_one() {
  local NAME="$1"
  local CFG="$2"
  local LOG="logs/v5_b2_${NAME}.log"
  local PRED_PATH="$OUT/$NAME/fold_0/test_preds.npz"

  if [ -f "$PRED_PATH" ]; then
    echo "[SKIP] $NAME: $PRED_PATH already exists"
    return 0
  fi

  echo "[B2] === Starting $NAME at $(date -u +%FT%TZ) ==="
  PYTHONUNBUFFERED=1 python -u scripts/v5_run_one.py \
    --name "$NAME" \
    --config "$CFG" \
    --out-base "$OUT" \
    > "$LOG" 2>&1
  local RC=$?
  echo "[B2] === Done $NAME rc=$RC at $(date -u +%FT%TZ) ==="

  if [ $RC -eq 0 ] && [ -f "$PRED_PATH" ]; then
    echo "[B2] $NAME PASSED — running comprehensive eval"
    python scripts/v5_eval_comprehensive.py \
      --exp-dir "$OUT/$NAME" \
      --n-folds 1 \
      --out "exports/v5_b2_${NAME}.md" \
      2>&1 | tee -a "$LOG" | tail -25
  fi
  return $RC
}

run_one quantile configs/v5/screen/loss_quantile.json
run_one huber    configs/v5/screen/loss_huber.json
run_one nll      configs/v5/screen/loss_nll.json

echo
echo "[B2] All loss runs complete at $(date -u +%FT%TZ). See exports/v5_b2_*.md"
