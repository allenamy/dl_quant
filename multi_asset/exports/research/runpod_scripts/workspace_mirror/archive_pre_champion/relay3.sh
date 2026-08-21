#!/bin/bash
# 等全部在跑的 train/queue 退出 → 关键判别实验: 同 A/B 但只用 2024+ 年折
# (metrics 填充边界在 2023-06; 若 53ch 在纯有数区间翻正 ⇒ 病根=填充断层, 不是信息)
cd /workspace/code
export PYTHONPATH=/workspace/code
while pgrep -f "train_wide_harness" > /dev/null; do sleep 30; done
while pgrep -f "rp_queue2.sh" > /dev/null; do sleep 10; done
for JOB in "rb32 /workspace/data/wide_dl_rebuilt32.npz" "ch53 /workspace/data/wide_dl_53ch.npz"; do
  set -- $JOB
  echo "=== [$(date -u +%H:%M:%SZ)] ${1}_yr24_yf24 (2024+ 年折) ==="
  python3 -u multi_asset/train/train_wide_harness.py \
    --wide_dl_path "$2" --target_horizon 24 --aux_horizons 1,24 \
    --encoder conformer --n_factor_heads 6 --n_xattn 1 \
    --d_model 64 --n_blocks 2 --seed 42 --year_folds_from 2024 \
    --save_tag "${1}_yr24_yf24" --tag "${1}_yr24_yf24" 2>&1 | tail -8
done
echo "=== 判别实验完成 $(date -u) ==="
