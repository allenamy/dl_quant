#!/usr/bin/env bash
# Post-B.1 master launcher (run after emapool completes).
#
# Steps:
# 1. Identify B.1 winner from v4base/emapool (mamba retry if install completed)
# 2. Launch B.2 loss screen on winner (quantile control + Huber + NLL)
# 3. Launch stretch (attention_long, mamba_long, attention_wide) if time

set -u
cd "$(dirname "$0")/.."

OUT_B1=experiments/v5_screen/B1
OUT_B2=experiments/v5_screen/B2
mkdir -p "$OUT_B2" logs

run_one_b2() {
  local NAME="$1"; local CFG="$2"
  local LOG="logs/v5_b2_${NAME}.log"
  local PRED="$OUT_B2/$NAME/fold_0/test_preds.npz"
  if [ -f "$PRED" ]; then echo "[B2] SKIP $NAME"; return 0; fi
  echo "[B2] === Starting $NAME at $(date -u +%FT%TZ) ==="
  PYTHONUNBUFFERED=1 python -u scripts/v5_run_one.py --name "$NAME" --config "$CFG" --out-base "$OUT_B2" > "$LOG" 2>&1
  local RC=$?
  echo "[B2] === Done $NAME rc=$RC at $(date -u +%FT%TZ) ==="
  if [ $RC -eq 0 ] && [ -f "$PRED" ]; then
    python scripts/v5_eval_comprehensive.py --exp-dir "$OUT_B2/$NAME" --n-folds 1 --out "exports/v5_b2_${NAME}.md" 2>&1 | tee -a "$LOG" | tail -25
  fi
}

# Step 1: Compare B.1 to find winner (v4base vs emapool, plus mamba if completed)
echo "=== Step 1: B.1 comparison ==="
python scripts/v5_b1_compare.py --out exports/v5_b1_summary.md 2>&1 | tail -20

# Determine winner: pick highest-P from completed (rc=0) backbones with valid test_preds.npz
WINNER=$(python -c "
import json, sys
from pathlib import Path
sys.path.insert(0, 'scripts')
from v5_eval_comprehensive import compute_v5_metrics, load_fold

best_p = -999
best_name = None
for name in ['v4base', 'attention', 'mamba', 'emapool']:
    p = Path(f'experiments/v5_screen/B1/{name}/fold_0/test_preds.npz')
    if p.exists() and p.stat().st_size > 1000:
        try:
            data = load_fold(p)
            m = compute_v5_metrics(data['y_lr'], data['yp_lr'], data['mask'])
            if m and m.get('P', -1) > best_p:
                best_p = m['P']; best_name = name
        except Exception as e:
            pass
print(best_name or 'v4base')
")
echo "B.1 winner: $WINNER (use this for B.2)"

# Step 2: Generate B.2 loss configs from winner
echo ""
echo "=== Step 2: Generate B.2 loss configs from winner=$WINNER ==="
python scripts/v5_b2_gen_configs.py --winner "$WINNER" 2>&1 | tail -5

# Step 3: Run B.2 sequential — quantile (control) + Huber + NLL
echo ""
echo "=== Step 3: B.2 loss screen ==="
run_one_b2 quantile configs/v5/screen/loss_quantile.json
run_one_b2 huber    configs/v5/screen/loss_huber.json
run_one_b2 nll      configs/v5/screen/loss_nll.json

# Step 4: B.2 comparison
echo ""
echo "=== Step 4: B.2 comparison ==="
python scripts/v5_b2_compare.py --out exports/v5_b2_summary.md 2>&1 | tail -15

echo ""
echo "[POST_B1] All done at $(date -u +%FT%TZ)"
