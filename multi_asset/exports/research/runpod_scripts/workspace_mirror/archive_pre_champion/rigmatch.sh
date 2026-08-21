#!/bin/bash
# 同装置对齐: 五折 @embargo=10 (h24_C 的尺) — 等 seed3 队列退出后接力(按 PID 等)
S3PID=$(pgrep -of "bash seed3.sh")
[ -n "$S3PID" ] && while kill -0 "$S3PID" 2>/dev/null; do sleep 20; done
cd /workspace/code
export PYTHONPATH=/workspace/code
echo "=== [$(date -u +%H:%M:%SZ)] rb32_yr24_rig5f (五折 emb10, h24_C 同尺) ==="
python3 -u multi_asset/train/train_wide_harness.py \
  --wide_dl_path /workspace/data/wide_dl_rebuilt32.npz --target_horizon 24 --aux_horizons 1,24 \
  --encoder conformer --n_factor_heads 6 --n_xattn 1 --d_model 64 --n_blocks 2 \
  --n_folds 5 --embargo_days 10 --seed 42 \
  --save_tag rb32_yr24_rig5f --tag rb32_yr24_rig5f 2>&1 | tail -8
echo "=== rigmatch 完成 $(date -u) ==="
