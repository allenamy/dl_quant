#!/usr/bin/env bash
# B.1 stretch — longer lookback + wider model variants. Run AFTER core 4 backbones.
set -u
cd "$(dirname "$0")/.."
OUT=experiments/v5_screen/B1
mkdir -p "$OUT" logs

run_one() {
  local NAME="$1"; local CFG="$2"
  local LOG="logs/v5_b1_${NAME}.log"
  local PRED="$OUT/$NAME/fold_0/test_preds.npz"
  if [ -f "$PRED" ]; then echo "[SKIP] $NAME"; return 0; fi
  echo "[B1-stretch] === Starting $NAME at $(date -u +%FT%TZ) ==="
  PYTHONUNBUFFERED=1 python -u scripts/v5_run_one.py --name "$NAME" --config "$CFG" --out-base "$OUT" > "$LOG" 2>&1
  local RC=$?
  echo "[B1-stretch] === Done $NAME rc=$RC at $(date -u +%FT%TZ) ==="
  if [ $RC -eq 0 ] && [ -f "$PRED" ]; then
    python scripts/v5_eval_comprehensive.py --exp-dir "$OUT/$NAME" --n-folds 1 --out "exports/v5_b1_${NAME}.md" 2>&1 | tee -a "$LOG" | tail -25
  fi
}

# Stretch order: cheaper first (wide), then long-context
run_one attention_wide configs/v5/screen/backbone_attention_wide.json
run_one attention_long configs/v5/screen/backbone_attention_long.json
run_one mamba_long     configs/v5/screen/backbone_mamba_long.json

echo "[B1-stretch] All stretch runs done at $(date -u +%FT%TZ)"
