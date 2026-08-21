#!/bin/bash
cd /workspace
export PYTHONPATH=/workspace/code
python3 -u mask_arm.py || exit 1
cd /workspace/code
echo "=== [$(date -u +%H:%M:%SZ)] ch54_yr24_s42 (存在掩码臂) ==="
python3 -u multi_asset/train/train_wide_harness.py \
  --wide_dl_path /workspace/data/wide_dl_54ch.npz --target_horizon 24 --aux_horizons 1,24 \
  --encoder conformer --n_factor_heads 6 --n_xattn 1 --d_model 64 --n_blocks 2 --seed 42 \
  --save_tag ch54_yr24_s42 --tag ch54_yr24_s42 2>&1 | tail -6
echo "=== mask 臂完成 $(date -u) ==="
