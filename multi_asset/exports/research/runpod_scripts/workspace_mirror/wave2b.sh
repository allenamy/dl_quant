#!/bin/bash
# ★ 第二波(v2, 依 λ=1.0 崩溃实测重排): 风格惩罚的量纲已知 ——
#   惩罚值 = 风格份额 ≈0.46, 而 rank 损失 ≈0.89 ⇒ λ=1.0 等于半个主目标, 必崩。
#   合理扰动应在 rank 损失的百分之几 ⇒ 阶梯改为 {0.03, 0.10}, 与在跑的 0.30 合成三点。
#   原 λ=3.0 臂【撤销】(确定性浪费); icvar 2.0 也撤, 等 icv05 报了再定量纲。
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
R ls_sty010 "--lam_style 0.10" &
sleep 45
R volt_ref "--target_npz /workspace/data/target_volrank.npz" &
wait
touch /workspace/loss_wave2.done
echo "=== 第二波 v2 完成 $(date -u) ==="
