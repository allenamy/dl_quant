#!/bin/bash
# 生产掩码臂: 等 queue_x 退出(按 PID) → 建面板 → 与 recon2 完全同配置训练
QX=$(pgrep -of "bash queue_x.sh")
[ -n "$QX" ] && while kill -0 "$QX" 2>/dev/null; do sleep 20; done
cd /workspace && export PYTHONPATH=/workspace/code
python3 -u prodmask.py || exit 1
cd /workspace/code
echo "=== [$(date -u +%H:%M:%SZ)] pm32_recon: 生产掩码 + h24_C 全配置 ==="
python3 -u multi_asset/train/train_wide_harness.py \
  --wide_dl_path /workspace/data/wide_dl_prodmask32.npz --target_horizon 24 --aux_horizons 1,24 \
  --encoder conformer --n_factor_heads 6 --xattn --n_xattn 1 --d_model 64 --n_blocks 2 \
  --year_folds --year_folds_from 2022 --embargo_days 10 --seed 42 \
  --save_tag pm32_recon --tag pm32_recon 2>&1 | tail -10
echo "=== 生产掩码臂完成 $(date -u) ==="
