#!/bin/bash
# scaling 大臂重跑(OOM 修复): 等全部训练器退净 + expandable_segments + 大模型减 batch
while pgrep -f "train_wide_harness" > /dev/null; do sleep 60; done
sleep 10
export PYTORCH_CUDA_ALLOC_CONF=expandable_segments:True
cd /workspace/code && export PYTHONPATH=/workspace/code
R() { D="$1"; BL="$2"; BH="$3"; S="$4"; T="$5"; python3 -u multi_asset/train/train_wide_harness.py \
  --wide_dl_path /workspace/data/wide_dl_prodmask32.npz --target_horizon 24 --aux_horizons 1,24 \
  --encoder conformer --n_factor_heads 6 --xattn --n_xattn 1 --lam_orth 0 \
  --d_model "$D" --n_blocks "$BL" --batch_hours "$BH" \
  --year_folds --year_folds_from 2022 --embargo_days 10 \
  --seed "$S" --save_tag "$T" --tag "$T" 2>&1 | tail -3; }
for S in 42 2027; do echo "=== [$(date -u +%H:%M:%SZ)] d128b4_s$S ==="; R 128 4 8 "$S" "scale_d128b4_s$S"; done
for S in 42 2027; do echo "=== [$(date -u +%H:%M:%SZ)] d256b4_s$S ==="; R 256 4 4 "$S" "scale_d256b4_s$S"; done
echo "=== [$(date -u +%H:%M:%SZ)] yr12_s2027 (y12 高值复种) ==="
python3 -u multi_asset/train/train_wide_harness.py \
  --wide_dl_path /workspace/data/wide_dl_pm32_hz.npz --target_horizon 12 --aux_horizons 1,24 \
  --encoder conformer --n_factor_heads 6 --xattn --n_xattn 1 --lam_orth 0 \
  --d_model 64 --n_blocks 2 --year_folds --year_folds_from 2022 --embargo_days 10 \
  --seed 2027 --save_tag rb32_lam0_yr12_s2027 --tag rb32_lam0_yr12_s2027 2>&1 | tail -3
echo "=== scale2 完成 $(date -u) ==="
