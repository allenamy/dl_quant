#!/bin/bash
# ★ 预注册验证臂(判据先行写入 LOG E35): dQ4 >= +0.005 双种子同向 vs y4 基线 Q4 0.0368; d全期 >= -0.002
# 无参数展开 —— 两条命令字面写死种子, 杜绝 $1 转义陷阱
export PYTORCH_CUDA_ALLOC_CONF=expandable_segments:True
cd /workspace/code || exit 1
export PYTHONPATH=/workspace/code
python3 -u multi_asset/train/train_wide_harness.py \
  --wide_dl_path /workspace/data/wide_dl_53ch.npz --target_horizon 4 --aux_horizons 1,24 \
  --encoder fusion2t --n_factor_heads 6 --xattn --n_xattn 1 --lam_orth 0 \
  --d_model 64 --n_blocks 2 --year_folds --year_folds_from 2022 --embargo_days 10 \
  --seed 42 --save_tag f2t_yr4_s42 --tag f2t_yr4_s42 > /workspace/f2t_y4_s42.log 2>&1 &
sleep 45
python3 -u multi_asset/train/train_wide_harness.py \
  --wide_dl_path /workspace/data/wide_dl_53ch.npz --target_horizon 4 --aux_horizons 1,24 \
  --encoder fusion2t --n_factor_heads 6 --xattn --n_xattn 1 --lam_orth 0 \
  --d_model 64 --n_blocks 2 --year_folds --year_folds_from 2022 --embargo_days 10 \
  --seed 2027 --save_tag f2t_yr4_s2027 --tag f2t_yr4_s2027 > /workspace/f2t_y4_s2027.log 2>&1 &
wait
echo "=== f2t_y4 完成"
