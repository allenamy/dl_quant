#!/bin/bash
while [ -n "$(nvidia-smi --query-compute-apps=pid --format=csv,noheader | head -1)" ]; do sleep 60; done
export PYTORCH_CUDA_ALLOC_CONF=expandable_segments:True
cd /workspace/code && export PYTHONPATH=/workspace/code
R() { python3 -u multi_asset/train/train_wide_harness.py   --wide_dl_path /workspace/data/wide_dl_pm32_hz.npz --target_horizon 4 --aux_horizons 1,8,12,24   --encoder conformer --n_factor_heads 6 --xattn --n_xattn 1 --lam_orth 0   --per_head_targets 4,8,12,12,24,24   --d_model 64 --n_blocks 2 --year_folds --year_folds_from 2022 --embargo_days 10   --seed "$1" --save_tag c3_pht_yr4_s"$1" --tag c3_pht_yr4_s"$1" 2>&1 | tail -4; }
echo "=== [$(date -u +%H:%M:%SZ)] c3_s42 ==="; R 42
echo "=== [$(date -u +%H:%M:%SZ)] c3_s2027 ==="; R 2027
echo "=== c3_queue 完成 $(date -u)"
