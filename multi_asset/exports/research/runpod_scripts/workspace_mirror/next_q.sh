#!/bin/bash
while [ -n "$(nvidia-smi --query-compute-apps=pid --format=csv,noheader | head -1)" ]; do sleep 60; done
export PYTORCH_CUDA_ALLOC_CONF=expandable_segments:True
cd /workspace/code && export PYTHONPATH=/workspace/code
R() { python3 -u multi_asset/train/train_wide_harness.py   --wide_dl_path "$1" --target_horizon 4 --aux_horizons 1,24   --encoder conformer --n_factor_heads 6 --xattn --n_xattn 1 --lam_orth 0   --d_model 64 --n_blocks 2 --year_folds --year_folds_from 2022 --embargo_days 10   $2 --seed "$3" --save_tag "$4" --tag "$4" 2>&1 | tail -3; }
P=/workspace/data/wide_dl_pm32_hz.npz
U=/workspace/data/wide_dl_pm32_hz_u137.npz
for S in 42 2027; do echo "=== [$(date -u +%H:%M:%SZ)] film_yr4_s$S ==="; R $P --film $S film_yr4_s$S; done
for S in 42 2027; do echo "=== [$(date -u +%H:%M:%SZ)] u137_yr4_s$S ==="; R $U "" $S u137_yr4_s$S; done
echo "=== next_q 完成 $(date -u)"
