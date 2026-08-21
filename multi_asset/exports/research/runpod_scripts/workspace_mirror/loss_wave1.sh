#!/bin/bash
# ★ 损失设计第一波(y4 = 部署视界且种子噪声最紧 sd=0.0004; 3 路并发)
# 预注册判据见 DESIGN_loss_2026-08-09.md §判据 —— 主判是【残差 IC】, 不是总分 IC
export PYTORCH_CUDA_ALLOC_CONF=expandable_segments:True
cd /workspace/code || exit 1
export PYTHONPATH=/workspace/code
R() {  # $1=tag $2=extra
  python3 -u multi_asset/train/train_wide_harness.py \
    --wide_dl_path /workspace/data/wide_dl_pm32_hz.npz --target_horizon 4 --aux_horizons 1,24 \
    --encoder conformer --n_factor_heads 6 --xattn --n_xattn 1 --lam_orth 0 \
    --d_model 64 --n_blocks 2 --year_folds --year_folds_from 2022 --embargo_days 10 \
    --seed 42 --save_tag "$1" --tag "$1" $2 > /workspace/loss_$1.log 2>&1
  python3 /workspace/style_resid.py "$1" >> /workspace/loss_wave1_cards.txt 2>&1
  echo "[$(date -u +%H:%M:%SZ)] 完成 $1"
}
R ls_sty03 "--lam_style 0.3" &
sleep 45
R ls_sty10 "--lam_style 1.0" &
sleep 45
R ls_icv05 "--lam_icvar 0.5" &
wait
touch /workspace/loss_wave1.done
echo "=== 损失第一波完成 $(date -u) ==="
