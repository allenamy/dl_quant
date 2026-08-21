#!/bin/bash
# 第三种子: 加厚 A/B 判决 + 建立 RunPod 侧种子散布(解释 jpline 0.0466 是否高抽要用)
cd /workspace/code
export PYTHONPATH=/workspace/code
for JOB in "rb32 /workspace/data/wide_dl_rebuilt32.npz" "ch53 /workspace/data/wide_dl_53ch.npz"; do
  set -- $JOB
  echo "=== [$(date -u +%H:%M:%SZ)] ${1}_yr24_s3037 ==="
  python3 -u multi_asset/train/train_wide_harness.py \
    --wide_dl_path "$2" --target_horizon 24 --aux_horizons 1,24 \
    --encoder conformer --n_factor_heads 6 --n_xattn 1 \
    --d_model 64 --n_blocks 2 --seed 3037 \
    --save_tag "${1}_yr24_s3037" --tag "${1}_yr24_s3037" 2>&1 | tail -6
done
echo "=== seed3 完成 $(date -u) ==="
