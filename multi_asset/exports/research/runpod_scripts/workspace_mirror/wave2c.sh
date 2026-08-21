#!/bin/bash
# ★ 第二波 v3(依 λ=0.3 也崩溃 + 事后投影更优 重排):
#  - 训练时风格惩罚整条判负(0.3 与 1.0 双双崩溃; 事后投影残差 IC 0.0306 vs 训练惩罚 0.0048 = 6×)
#  - 只保留 λ=0.03 一臂作【实现病理 vs 真实信号结构】的判别: 若 0.03 仍崩 => 是我的实现有梯度病理;
#    若 0.03 正常 => 是剂量-反应, 风格确实是信号的真实组成部分。这个区分对未来所有惩罚类设计都要用。
#  - 释放的槽位给波动目标参照(W3 前置), 稳定性轴等 icv05 报了再定量纲。
while [ ! -f /workspace/loss_wave1.done ]; do sleep 60; done
sleep 20
export PYTORCH_CUDA_ALLOC_CONF=expandable_segments:True
cd /workspace/code || exit 1
export PYTHONPATH=/workspace/code
R() {
  python3 -u multi_asset/train/train_wide_harness.py \
    --wide_dl_path /workspace/data/wide_dl_pm32_hz.npz --target_horizon 4 --aux_horizons 1,24 \
    --encoder conformer --n_factor_heads 6 --xattn --n_xattn 1 --lam_orth 0 \
    --d_model 64 --n_blocks 2 --year_folds --year_folds_from 2022 --embargo_days 10 \
    --seed 42 --save_tag "$1" --tag "$1" $2 > /workspace/loss_$1.log 2>&1
  python3 /workspace/style_resid.py "$1" >> /workspace/loss_wave2_cards.txt 2>&1
  echo "[$(date -u +%H:%M:%SZ)] 完成 $1"
}
R ls_sty003 "--lam_style 0.03" &
sleep 45
R volt_ref "--target_npz /workspace/data/target_volrank.npz" &
wait
touch /workspace/loss_wave2.done
echo "=== 第二波 v3 完成 $(date -u) ==="
