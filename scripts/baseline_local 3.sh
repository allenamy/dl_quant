#!/usr/bin/env bash
# Run Ridge/XGBoost baselines LOCALLY on a subset of V4 NPZs.
# Uses --use-last-timestep so memory fits on a laptop (~500 MB instead of 80 GB).
#
# Why:
#  - Pod's /workspace/quant_research/data/npz_v4/ is ~82 GB. We only need a
#    window large enough for at least one fold (train + val + test).
#  - For a fair Ridge/XGB baseline on V4 features, use last-timestep features
#    (same as V3 baseline convention) — the fully-flattened (L, F) Ridge in
#    evaluate_baselines was a coding artefact, not a proper comparison.
#
# Steps:
#   1. rsync a subset of days from pod to data/npz_v4_local/
#   2. Run evaluate_baselines with --use-last-timestep
#   3. Results land in experiments/baselines_v4_local/
#
# Usage:
#   ./scripts/baseline_local.sh [months_to_download] [train_days] [val_days] [test_days]
# Defaults: download 8 months (2023-01..2023-08), use first 150 days as train,
# 20 val, 30 test (fits one fold from the head of that range).
set -euo pipefail

cd "$(dirname "$0")/.."

MONTHS="${1:-2023-01 2023-02 2023-03 2023-04 2023-05 2023-06 2023-07 2023-08}"
TRAIN_DAYS="${2:-150}"
VAL_DAYS="${3:-20}"
TEST_DAYS="${4:-30}"

HOST="213.192.2.108"
PORT="40087"
KEY="$HOME/.ssh/runpod_ed25519"

LOCAL_NPZ_DIR="data/npz_v4_local"
OUT_DIR="experiments/baselines_v4_local"
LOG_DIR="logs"
mkdir -p "$LOCAL_NPZ_DIR" "$OUT_DIR" "$LOG_DIR"

echo "=== [1/3] rsync subset of NPZs from pod ==="
echo "  months: $MONTHS"

# Build include patterns like --include='2023-01-*.npz'
INCLUDES=()
for m in $MONTHS; do
    INCLUDES+=(--include="${m}-*.npz")
done

rsync -avz --progress \
    "${INCLUDES[@]}" \
    --exclude='*' \
    -e "ssh -i $KEY -p $PORT -o StrictHostKeyChecking=no" \
    "root@$HOST:/workspace/quant_research/data/npz_v4/" \
    "$LOCAL_NPZ_DIR/" 2>&1 | tail -20

N_DAYS=$(ls "$LOCAL_NPZ_DIR"/*.npz 2>/dev/null | wc -l | tr -d ' ')
echo "  downloaded $N_DAYS days"

if [ "$N_DAYS" -lt $((TRAIN_DAYS + VAL_DAYS + TEST_DAYS)) ]; then
    echo "ERROR: need at least $((TRAIN_DAYS + VAL_DAYS + TEST_DAYS)) days, have $N_DAYS"
    exit 1
fi

echo ""
echo "=== [2/3] Run baselines with --use-last-timestep ==="
LOG_FILE="$LOG_DIR/baseline_local_$(date +%Y%m%d_%H%M).log"

python -m src.baselines.evaluate_baselines \
    --npz-dir "$LOCAL_NPZ_DIR" \
    --output-dir "$OUT_DIR" \
    --device cpu \
    --train-days "$TRAIN_DAYS" \
    --val-days "$VAL_DAYS" \
    --test-days "$TEST_DAYS" \
    --fold-stride 1 \
    --horizon-key y_180 \
    --mask-key y_mask_180 \
    --use-last-timestep \
    2>&1 | tee "$LOG_FILE"

echo ""
echo "=== [3/3] Summary ==="
for f in "$OUT_DIR"/*.json; do
    if [ -f "$f" ]; then
        echo "  $f:"
        python -c "
import json, sys
d = json.load(open('$f'))
for k, v in d.items():
    if isinstance(v, dict):
        for kk, vv in v.items():
            print(f'    {k}.{kk}: {vv}')
    else:
        print(f'    {k}: {v}')
" 2>/dev/null || cat "$f" | head -30
    fi
done

echo "  log: $LOG_FILE"
echo "  results dir: $OUT_DIR/"
