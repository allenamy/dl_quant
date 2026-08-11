#!/usr/bin/env bash
# Fold 2 verification of top fold-0 backbones — ensure cross-fold stability before B.2.
# Picks top 3 backbones by fold-0 P and re-runs each on fold 2.

set -u
cd "$(dirname "$0")/.."

# Hard-coded top candidates (fold-0 leaders so far + late_fusion as new variant)
CANDIDATES=(mamba v4base late_fusion)

OUT=experiments/v5_screen/B1_fold2
mkdir -p "$OUT" logs

run_fold2() {
  local NAME="$1"; local CFG="configs/v5/screen/backbone_${NAME}.json"
  if [ ! -f "$CFG" ]; then echo "[F2] config missing: $CFG"; return 1; fi
  local LOG="logs/v5_b1_${NAME}_fold2.log"
  local PRED="$OUT/$NAME/fold_2/test_preds.npz"
  if [ -f "$PRED" ] && [ $(stat -c%s "$PRED") -gt 1000 ]; then
    echo "[F2] SKIP $NAME (already done)"; return 0
  fi
  rm -rf "$OUT/$NAME"
  echo "[F2] === $NAME fold 2 at $(date -u +%FT%TZ) ==="
  PYTHONUNBUFFERED=1 python -u scripts/v5_run_one.py --name "$NAME" --config "$CFG" --out-base "$OUT" --start-fold 2 --max-folds 1 > "$LOG" 2>&1
  local RC=$?
  echo "[F2] === Done $NAME rc=$RC ==="
  if [ $RC -eq 0 ] && [ -f "$PRED" ]; then
    python scripts/v5_eval_comprehensive.py --exp-dir "$OUT/$NAME" --n-folds 1 --out "exports/v5_b1_${NAME}_fold2.md" 2>&1 | tail -25
  fi
}

# Fix the n-folds reading: eval_comprehensive expects fold_0/, but we have fold_2/
# Simplest: copy fold_2 to fold_0 view for eval (NPZ filename is what matters)
eval_fold2() {
  local NAME="$1"
  local SRC="$OUT/$NAME/fold_2/test_preds.npz"
  if [ ! -f "$SRC" ]; then return 1; fi
  # Use eval script with manual fold targeting
  python -c "
import sys
sys.path.insert(0, 'scripts')
from v5_eval_comprehensive import compute_v5_metrics, check_v5_gates, load_fold
from pathlib import Path
data = load_fold(Path(''))
m = compute_v5_metrics(data['y_lr'], data['yp_lr'], data['mask'])
gates = check_v5_gates(m)
print(f' fold 2: P={m[\"P\"]:.4f} S={m[\"S\"]:.4f} beta={m[\"beta\"]:.3f} sigma_ratio={m[\"sigma_ratio\"]:.3f} bin_S={m[\"bin_S\"]:.3f} top_E_y={m[\"top_decile_y_bps\"]:.3f}bps spread={m[\"top_minus_bottom_bps\"]:.3f}bps')
" > exports/v5_b1_${NAME}_fold2.md
  cat exports/v5_b1_${NAME}_fold2.md
}

for cand in "${CANDIDATES[@]}"; do
  run_fold2 "$cand"
  eval_fold2 "$cand"
done

echo
echo "[F2] === Fold 2 verification done at $(date -u +%FT%TZ) ==="
echo "Cross-fold leaderboard:"
for cand in "${CANDIDATES[@]}"; do
  echo "  --- $cand ---"
  cat exports/v5_b1_${cand}.md 2>/dev/null | grep -E '^\| P |^\| S |^\| beta' | head -3
  cat exports/v5_b1_${cand}_fold2.md 2>/dev/null
done
