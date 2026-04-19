#!/usr/bin/env bash
# V5-LH 3-fold × 3-seed driver. Run on pod after NPZ build + env setup.
#
# Usage:
#   cd /workspace/quant_research
#   export PATH=/usr/local/cuda/bin:$PATH
#   chmod +x scripts/v5_lh_run_all.sh
#   setsid bash scripts/v5_lh_run_all.sh </dev/null >logs/v5_lh_all.log 2>&1 &
#
# Expected runtime: 20-50 hrs depending on early-stop behavior.

set -u
mkdir -p logs
CONFIG=configs/v5_lh/v5_lh_base.json

for FOLD in 0 1 2; do
  for SEED in 1 2 3; do
    echo "==== V5-LH fold=$FOLD seed=$SEED start $(date -Is) ===="
    # -u = unbuffered stdout so `tee` and `tail -f` see progress in real time.
    PYTHONUNBUFFERED=1 python3 -u scripts/v5_lh_train.py \
        --config "$CONFIG" \
        --fold "$FOLD" \
        --seed "$SEED" \
        2>&1 | tee "logs/v5_lh_f${FOLD}_s${SEED}.log"
    echo "==== V5-LH fold=$FOLD seed=$SEED end $(date -Is) ===="
  done
done
echo "ALL V5-LH FOLDS COMPLETE $(date -Is)"
