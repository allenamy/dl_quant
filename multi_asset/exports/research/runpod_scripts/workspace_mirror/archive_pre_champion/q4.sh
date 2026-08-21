#!/bin/bash
# D1: y4/y24 第三种子(排在 q3 之后)
for W in q3.sh h2.sh recover.sh; do PID=$(pgrep -of "bash /workspace/$W" 2>/dev/null); [ -n "$PID" ] && while kill -0 "$PID" 2>/dev/null; do sleep 30; done; done
cd /workspace/code && export PYTHONPATH=/workspace/code
for CFG in "4 rb32_lam0_yr4_s3037" "24 rb32_lam0_s3037"; do
  set -- $CFG
  echo "=== [$(date -u +%H:%M:%SZ)] $2 ==="
  python3 -u multi_asset/train/train_wide_harness.py \
    --wide_dl_path /workspace/data/wide_dl_pm32_hz.npz --target_horizon "$1" --aux_horizons 1,24 \
    --encoder conformer --n_factor_heads 6 --xattn --n_xattn 1 --lam_orth 0 \
    --d_model 64 --n_blocks 2 --year_folds --year_folds_from 2022 --embargo_days 10 \
    --seed 3037 --save_tag "$2" --tag "$2" 2>&1 | tail -3
done
echo "=== q4 完成 $(date -u) ==="
