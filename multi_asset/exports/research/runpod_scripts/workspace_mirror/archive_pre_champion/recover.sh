#!/bin/bash
# 丢失三臂重跑(磁盘满死于存档) → scaling 阶梯
cd /workspace/code && export PYTHONPATH=/workspace/code
R() { P="$1"; H="$2"; shift 2; python3 -u multi_asset/train/train_wide_harness.py \
  --wide_dl_path "$P" --target_horizon "$H" --aux_horizons 1,24 \
  --encoder conformer --n_factor_heads 6 --xattn --n_xattn 1 --lam_orth 0 \
  --d_model 64 --n_blocks 2 --year_folds --year_folds_from 2022 --embargo_days 10 \
  "$@" 2>&1 | tail -3; }
Rf() { P="$1"; H="$2"; shift 2; python3 -u multi_asset/train/train_wide_harness.py \
  --wide_dl_path "$P" --target_horizon "$H" --aux_horizons 1,24 \
  --encoder fusion2t --n_factor_heads 6 --xattn --n_xattn 1 \
  --d_model 64 --n_blocks 2 --year_folds --year_folds_from 2022 --embargo_days 10 \
  "$@" 2>&1 | tail -3; }
echo "=== [$(date -u +%H:%M:%SZ)] lam0_yr4 重跑 ==="
R /workspace/data/wide_dl_pm32_hz.npz 4 --seed 42 --save_tag rb32_lam0_yr4_s42 --tag rb32_lam0_yr4_s42
for S in 42 2027; do
  echo "=== [$(date -u +%H:%M:%SZ)] bk45_yr8_s${S} 重跑 ==="
  Rf /workspace/data/wide_dl_45ch.npz 8 --seed "$S" --save_tag "bk45_yr8_s${S}" --tag "bk45_yr8_s${S}"
done
for CFG in "128 2 d128b2" "128 4 d128b4" "256 4 d256b4"; do
  set -- $CFG
  for S in 42 2027; do
    echo "=== [$(date -u +%H:%M:%SZ)] scale_${3}_s${S} ==="
    python3 -u multi_asset/train/train_wide_harness.py \
      --wide_dl_path /workspace/data/wide_dl_prodmask32.npz --target_horizon 24 --aux_horizons 1,24 \
      --encoder conformer --n_factor_heads 6 --xattn --n_xattn 1 --lam_orth 0 \
      --d_model "$1" --n_blocks "$2" --year_folds --year_folds_from 2022 --embargo_days 10 \
      --seed "$S" --save_tag "scale_${3}_s${S}" --tag "scale_${3}_s${S}" 2>&1 | tail -3
  done
done
echo "=== recover+ladder 完成 $(date -u) ==="
