#!/bin/bash
# DESIGN_book §4 预注册退路: book 在短视界复测(AR(1h)=0.102 ⇒ 24h 越过半衰期)
# 对照 hz4 双种子 0.0358 (32ch, y4)。判据同前: Δ≥+0.005 双种子同向才报方向。
cd /workspace/code && export PYTHONPATH=/workspace/code
R() { python3 -u multi_asset/train/train_wide_harness.py \
  --wide_dl_path "$1" --target_horizon "$2" --encoder "$3" --n_factor_heads 6 --xattn --n_xattn 1 \
  --d_model 64 --n_blocks 2 --year_folds --year_folds_from 2022 --embargo_days 10 --seed "$4" \
  --save_tag "$5" --tag "$5" 2>&1 | tail -4; }
for S in 42 2027; do
  echo "=== [$(date -u +%H:%M:%SZ)] bk45_yr4_s${S} (book 族塔 @ y4) ==="
  R /workspace/data/wide_dl_45ch.npz 4 fusion2t "$S" "bk45_yr4_s${S}"
done
for S in 42 2027; do
  echo "=== [$(date -u +%H:%M:%SZ)] bk45_yr8_s${S} (book 族塔 @ y8) ==="
  R /workspace/data/wide_dl_45ch.npz 8 fusion2t "$S" "bk45_yr8_s${S}"
done
echo "=== 短视界复测完成 $(date -u) ==="
