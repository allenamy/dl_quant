#!/bin/bash
# ★ 预注册验证臂(判据已先行写入 LOG E35): ΔQ4 >= +0.005 双种子同向 vs y4 基线 Q4 0.0368; Δ全期 >= -0.002
export PYTORCH_CUDA_ALLOC_CONF=expandable_segments:True
cd /workspace/code && export PYTHONPATH=/workspace/code
R() { python3 -u multi_asset/train/train_wide_harness.py   --wide_dl_path /workspace/data/wide_dl_53ch.npz --target_horizon 4 --aux_horizons 1,24   --encoder fusion2t --n_factor_heads 6 --xattn --n_xattn 1 --lam_orth 0   --d_model 64 --n_blocks 2 --year_folds --year_folds_from 2022 --embargo_days 10   --seed "$1" --save_tag f2t_yr4_s$1 --tag f2t_yr4_s$1 2>&1 | tail -3; }
R 42 > /workspace/f2t_y4_s42.log 2>&1 &
sleep 45
R 2027 > /workspace/f2t_y4_s2027.log 2>&1 &
wait
echo "=== f2t_y4 完成 \$(date -u)"
