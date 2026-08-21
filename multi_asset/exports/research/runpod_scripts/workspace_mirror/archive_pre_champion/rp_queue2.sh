#!/bin/bash
# 驱动: 自建32 -> metrics 全史重建 -> 53ch 装配 -> 4 连 GPU A/B (严格串行)
cd /workspace
set -e
export PYTHONPATH=/workspace/code
echo "=== [$(date -u +%H:%M:%SZ)] step2: 32ch 自建 ==="
python3 -u rebuild32_step2.py
echo "=== [$(date -u +%H:%M:%SZ)] metrics 全史重建 ==="
python3 -u build_metrics_panel.py
echo "=== [$(date -u +%H:%M:%SZ)] 53ch 装配 ==="
python3 -u assemble_53ch.py
cd /workspace/code
for JOB in "rb32 /workspace/data/wide_dl_rebuilt32.npz 42" "ch53 /workspace/data/wide_dl_53ch.npz 42" "rb32 /workspace/data/wide_dl_rebuilt32.npz 2027" "ch53 /workspace/data/wide_dl_53ch.npz 2027"; do
  set -- $JOB
  echo "=== [$(date -u +%H:%M:%SZ)] ${1}_yr24_s${3} ==="
  python3 -u multi_asset/train/train_wide_harness.py \
    --wide_dl_path "$2" --target_horizon 24 --aux_horizons 1,24 \
    --encoder conformer --n_factor_heads 6 --n_xattn 1 \
    --d_model 64 --n_blocks 2 --seed "$3" \
    --save_tag "${1}_yr24_s${3}" --tag "${1}_yr24_s${3}" 2>&1 | tail -12
done
echo "=== 队列全部完成 $(date -u) ==="
