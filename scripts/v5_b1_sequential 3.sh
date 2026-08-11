#!/usr/bin/env bash
# Sequential launcher for V5 B.1 backbone screen on pod.
#
# Skips configs whose fold_0/test_preds.npz already exists (idempotent).
# Logs each run separately so the orchestrator can be restarted safely.
#
# Usage (on pod):
#   bash scripts/v5_b1_sequential.sh

set -u
cd "$(dirname "$0")/.."

OUT=experiments/v5_screen/B1
mkdir -p "$OUT" logs

run_one() {
  local NAME="$1"
  local CFG="$2"
  local LOG="logs/v5_b1_${NAME}.log"
  local PRED_PATH="$OUT/$NAME/fold_0/test_preds.npz"

  if [ -f "$PRED_PATH" ]; then
    echo "[SKIP] $NAME: $PRED_PATH already exists"
    return 0
  fi

  echo "[B1] === Starting $NAME at $(date -u +%FT%TZ) ==="
  PYTHONUNBUFFERED=1 python -u scripts/v5_run_one.py \
    --name "$NAME" \
    --config "$CFG" \
    --out-base "$OUT" \
    > "$LOG" 2>&1
  local RC=$?
  echo "[B1] === Done $NAME rc=$RC at $(date -u +%FT%TZ) ==="

  if [ $RC -eq 0 ] && [ -f "$PRED_PATH" ]; then
    echo "[B1] $NAME PASSED — running comprehensive eval"
    python scripts/v5_eval_comprehensive.py \
      --exp-dir "$OUT/$NAME" \
      --n-folds 1 \
      --out "exports/v5_b1_${NAME}.md" \
      2>&1 | tee -a "$LOG" | tail -25
  fi
  return $RC
}

run_one v4base    configs/v5/screen/backbone_v4base.json
run_one attention configs/v5/screen/backbone_attention.json
run_one mamba     configs/v5/screen/backbone_mamba.json
run_one emapool   configs/v5/screen/backbone_emapool.json

echo
echo "[B1] All runs complete at $(date -u +%FT%TZ). See exports/v5_b1_*.md"
