#!/bin/bash
# 1A 残差校正器【正确形态】: 载入训练好的冠军主干(同折) -> 冻结 -> 只训 B 塔(7,778 参数)
# 预注册判据(先于起跑写入 LOG E37): Δ全期 >= +0.003 且 ΔQ4 >= 0 双种子同向 vs y4 基线 (0.0456 / Q4 0.0368)
# 结构性零伤害: 主干不可被弱信噪比输入扰动 => 该臂【不可能】低于基线太多, 若低则说明门/塔本身在注入噪声
export PYTORCH_CUDA_ALLOC_CONF=expandable_segments:True
cd /workspace/code || exit 1
export PYTHONPATH=/workspace/code
python3 -u multi_asset/train/train_wide_harness.py   --wide_dl_path /workspace/data/wide_dl_allfam.npz --target_horizon 4 --aux_horizons 1,24   --encoder fusion2t --n_factor_heads 6 --xattn --n_xattn 1 --lam_orth 0   --d_model 64 --n_blocks 2 --year_folds --year_folds_from 2022 --embargo_days 10   --init_trunk_from /workspace/exports_train/rb32_lam0_yr4_s42 --freeze_trunk   --seed 42 --save_tag frz_allfam_s42 --tag frz_allfam_s42 > /workspace/frz_s42.log 2>&1
echo "=== frz 完成 $(date -u)"
