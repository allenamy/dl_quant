#!/bin/bash
# 补测: 族塔(FusionTwoTower)在【冠军配置】下的增量 —— 原 f2t_x 臂是 lam_orth=1.0 默认惩罚, 判决作废
# 对照: ch53_lam0(扁平, 同面板同配置) 0.0387 / rb32_lam0(32ch 基线) 0.0474
while [ -n "$(nvidia-smi --query-compute-apps=pid --format=csv,noheader | head -1)" ]; do sleep 60; done
export PYTORCH_CUDA_ALLOC_CONF=expandable_segments:True
cd /workspace/code && export PYTHONPATH=/workspace/code
for S in 42 2027; do
  echo "=== [$(date -u +%H:%M:%SZ)] f2t_lam0_s$S ==="
  python3 -u multi_asset/train/train_wide_harness.py     --wide_dl_path /workspace/data/wide_dl_53ch.npz --target_horizon 24 --aux_horizons 1,24     --encoder fusion2t --n_factor_heads 6 --xattn --n_xattn 1 --lam_orth 0     --d_model 64 --n_blocks 2 --year_folds --year_folds_from 2022 --embargo_days 10     --seed $S --save_tag f2t_lam0_s$S --tag f2t_lam0_s$S 2>&1 | tail -3
done
echo "=== f2t_lam0 完成 $(date -u)"
