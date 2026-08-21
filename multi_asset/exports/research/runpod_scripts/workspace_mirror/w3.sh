#!/bin/bash
# ★ W3 档位空间塔 —— 预注册判据(写于起跑之前, 与 DESIGN_loss_2026-08-09 §3-W3 一致):
#   A) 收益目标 y4 : Δens >= +0.002 vs y4 基线 0.0460(筛门); 副读 残差Q4 vs 0.0183
#   B) 波动目标   : ens > 0.7373 + 0.005 = 0.7423 (volt_ref 已钉死基准, 32ch线性 Ridge 0.7208)
#   C) 收益目标 y12: Δens >= +0.002 vs y12 基线 0.0529
#   红线: σŷ/σy >= 0.02; 零初始化恒等已实测 max|d|=0.000e+00
#   会红的方向: 若三个目标全部不过, 则【档位空间结构】这条设计整体判负 —— 书族在收益/波动两类
#   目标上都已无路(线性/塔/冻结/空间四种形态), 该族退役。
export PYTORCH_CUDA_ALLOC_CONF=expandable_segments:True
cd /workspace/code || exit 1
export PYTHONPATH=/workspace/code
P=/workspace/data/wide_dl_book5t.npz
B="--encoder book5t --n_factor_heads 6 --xattn --n_xattn 1 --lam_orth 0 --d_model 64 --n_blocks 2 --year_folds --year_folds_from 2022 --embargo_days 10 --seed 42"
python3 -u multi_asset/train/train_wide_harness.py --wide_dl_path $P --target_horizon 4  --aux_horizons 1,24 $B --save_tag bk5t_yr4  --tag bk5t_yr4  > /workspace/loss_bk5t_yr4.log 2>&1 &
sleep 45
python3 -u multi_asset/train/train_wide_harness.py --wide_dl_path $P --target_horizon 4  --aux_horizons 1,24 $B --save_tag bk5t_vol  --tag bk5t_vol  --target_npz /workspace/data/target_volrank.npz > /workspace/loss_bk5t_vol.log 2>&1 &
sleep 45
python3 -u multi_asset/train/train_wide_harness.py --wide_dl_path $P --target_horizon 12 --aux_horizons 1,24 $B --save_tag bk5t_yr12 --tag bk5t_yr12 > /workspace/loss_bk5t_yr12.log 2>&1 &
wait
for t in bk5t_yr4 bk5t_vol bk5t_yr12; do python3 /workspace/style_resid.py $t >> /workspace/w3_cards.txt 2>&1; done
touch /workspace/w3.done
echo "=== W3 完成 $(date -u) ==="
