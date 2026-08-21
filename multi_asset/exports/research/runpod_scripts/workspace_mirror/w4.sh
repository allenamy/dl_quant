#!/bin/bash
# ★ W4 滚动重训回放(记忆钦定的"真解", 从未做过) —— 零新代码: 用已有的 wf_folds 通用走前折。
# 装置: --n_folds 8 --test_frac 0.45 => 测试段约占后 45% 天数, 切成 8 块, 每块 ~4 个月,
#       【每折都在其之前的全部数据上重训】= 4 个月重训一次的滚动世代。
# 对照: 冠军的 --year_folds = 每年重训一次。两者在【重叠测试期】(约 2024-06 起)上比逐锚 IC。
# 预注册判据(写于起跑之前):
#   主判: 重叠期上 滚动(4月) 的 ens IC ≥ 年度重训 + 0.003, 且逐块 IC 差 ≥0 的块占比 > 60%
#   副读: 残差 IC 与 残Q4(风格/残差卡); σŷ/σy ≥ 0.02
#   ★ 会红的方向: 若 ≤0, 则"更频繁重训"这条(记忆里被称作 regime 适应的真解)在本项目【被证伪】,
#     且它是最后一条结构性新鲜度杠杆 —— 那意味着 regime 问题在模型侧无解, 只剩书级/执行侧。
# 等 GPU 降到 <=2 臂再起(W3 还有两臂在跑), 按数量不按文本。
while [ $(nvidia-smi --query-compute-apps=pid --format=csv,noheader | wc -l) -ge 3 ]; do sleep 60; done
export PYTORCH_CUDA_ALLOC_CONF=expandable_segments:True
cd /workspace/code || exit 1
export PYTHONPATH=/workspace/code
python3 -u multi_asset/train/train_wide_harness.py \
  --wide_dl_path /workspace/data/wide_dl_pm32_hz.npz --target_horizon 4 --aux_horizons 1,24 \
  --encoder conformer --n_factor_heads 6 --xattn --n_xattn 1 --lam_orth 0 \
  --d_model 64 --n_blocks 2 --n_folds 8 --test_frac 0.45 --embargo_days 10 \
  --seed 42 --save_tag roll8_yr4 --tag roll8_yr4 > /workspace/loss_roll8_yr4.log 2>&1
python3 /workspace/style_resid.py roll8_yr4 >> /workspace/w4_cards.txt 2>&1
touch /workspace/w4.done
echo "=== W4 完成 $(date -u) ==="
