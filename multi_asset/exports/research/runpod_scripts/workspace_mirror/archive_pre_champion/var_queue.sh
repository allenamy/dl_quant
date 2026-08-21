#!/bin/bash
# ★ 年折装置方差测定: 同面板(生产还原)同配置, 只换种子。
# 判读: 若散布 ≥±0.008, 则 0.0466 与 0.0348 同分布 —— "缺口"主要是方差, 环境不必再追;
#       且【任何小于 ~0.01 的 Δ 在年折装置上不可测】, 这条会改写全部判据。
cd /workspace/code
export PYTHONPATH=/workspace/code
for S in 2027 3037 4047; do
  echo "=== [$(date -u +%H:%M:%SZ)] pm32_yf_s${S} ==="
  python3 -u multi_asset/train/train_wide_harness.py \
    --wide_dl_path /workspace/data/wide_dl_prodmask32.npz --target_horizon 24 --aux_horizons 1,24 \
    --encoder conformer --n_factor_heads 6 --xattn --n_xattn 1 --d_model 64 --n_blocks 2 \
    --year_folds --year_folds_from 2022 --embargo_days 10 --seed "$S" \
    --save_tag "pm32_yf_s${S}" --tag "pm32_yf_s${S}" 2>&1 | tail -5
done
echo "=== 方差测定完成 $(date -u) ==="
