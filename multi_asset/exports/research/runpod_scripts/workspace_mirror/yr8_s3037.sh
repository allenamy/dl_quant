#!/bin/bash
while [ -n "$(nvidia-smi --query-compute-apps=pid --format=csv,noheader | head -1)" ]; do sleep 60; done
export PYTORCH_CUDA_ALLOC_CONF=expandable_segments:True
cd /workspace/code && export PYTHONPATH=/workspace/code
python3 -u multi_asset/train/train_wide_harness.py   --wide_dl_path /workspace/data/wide_dl_pm32_hz.npz --target_horizon 8 --aux_horizons 1,24   --encoder conformer --n_factor_heads 6 --xattn --n_xattn 1 --lam_orth 0   --d_model 64 --n_blocks 2 --year_folds --year_folds_from 2022 --embargo_days 10   --seed 3037 --save_tag rb32_lam0_yr8_s3037 --tag rb32_lam0_yr8_s3037 2>&1 | tail -3
echo "=== yr8_s3037 完成 $(date -u)"
