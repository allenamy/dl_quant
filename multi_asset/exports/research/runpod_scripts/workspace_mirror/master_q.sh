#!/bin/bash
# ★ 单一串行主队列 —— 终结多队列接力竞态(双开/OOM共驻/抢跑 三事故)
# 本队列启动前提: 调用方已确认无其他 trainer 存活
export PYTORCH_CUDA_ALLOC_CONF=expandable_segments:True
cd /workspace/code && export PYTHONPATH=/workspace/code
R() { python3 -u multi_asset/train/train_wide_harness.py \
  --wide_dl_path "$1" --target_horizon "$2" --aux_horizons 1,24 \
  --encoder conformer --n_factor_heads 6 --xattn --n_xattn 1 --lam_orth 0 \
  --d_model "$3" --n_blocks "$4" --batch_hours "$5" \
  --year_folds --year_folds_from 2022 --embargo_days 10 \
  --seed "$6" --save_tag "$7" --tag "$7" 2>&1 | tail -3; }
PM=/workspace/data/wide_dl_prodmask32.npz
HZ=/workspace/data/wide_dl_pm32_hz.npz
echo "=== [$(date -u +%H:%M:%SZ)] D1: yr4_s3037 ===";  R $HZ 4  64 2 16 3037 rb32_lam0_yr4_s3037
echo "=== [$(date -u +%H:%M:%SZ)] D1: yr24_s3037 ==="; R $PM 24 64 2 16 3037 rb32_lam0_s3037
echo "=== [$(date -u +%H:%M:%SZ)] yr12_s2027 ===";     R $HZ 12 64 2 16 2027 rb32_lam0_yr12_s2027
echo "=== [$(date -u +%H:%M:%SZ)] d128b4_s42 ===";     R $PM 24 128 4 8 42   scale_d128b4_s42
echo "=== [$(date -u +%H:%M:%SZ)] d128b4_s2027 ===";   R $PM 24 128 4 8 2027 scale_d128b4_s2027
echo "=== [$(date -u +%H:%M:%SZ)] d256b4_s42 ===";     R $PM 24 256 4 4 42   scale_d256b4_s42
echo "=== [$(date -u +%H:%M:%SZ)] d256b4_s2027 ===";   R $PM 24 256 4 4 2027 scale_d256b4_s2027
echo "=== master_q 完成 $(date -u) ==="
