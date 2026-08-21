#!/bin/bash
cd /workspace/code
export PYTHONPATH=/workspace/code
P=/workspace/data/wide_dl_metrics21.npz
# A/B 只差【主目标视界】一个变量: 4h(现役口径) vs 24h(已预注册、5/5 年占优、但从未部署)
for H in 4 24; do
  echo "=== [$(date -u +%H:%M:%SZ)] metrics21 YR${H} ==="
  python3 -u multi_asset/train/train_wide_harness.py \
    --wide_dl_path "$P" --target_horizon "$H" --aux_horizons 1,24 \
    --encoder conformer --n_factor_heads 6 --n_xattn 1 \
    --d_model 64 --n_blocks 2 --seed 42 \
    --save_tag "met21_yr${H}" --tag "met21_yr${H}" 2>&1 | tail -70
done
echo "=== A/B 完成 $(date -u) ==="
