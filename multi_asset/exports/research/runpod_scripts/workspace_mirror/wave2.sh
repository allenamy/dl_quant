#!/bin/bash
# ★ 第二波: 补完两条 λ 阶梯 + 波动目标 DL 参照。
# 设计理由: 这三个臂【在第一波任何结果下都有信息量】——
#   λ 阶梯的形状本身是结论(E31 的剂量-反应就是这么得到的), 无论方向正负;
#   波动目标参照是 W3(档位空间塔)的对照基准, 完全独立于损失轴。
# 等待用【文件标记】而非进程(silent-watcher-death 教训)。
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
R ls_sty30 "--lam_style 3.0" &
sleep 45
R ls_icv20 "--lam_icvar 2.0" &
sleep 45
R volt_ref "--target_npz /workspace/data/target_volrank.npz" &
wait
touch /workspace/loss_wave2.done
echo "=== 第二波完成 $(date -u) ==="
