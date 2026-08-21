#!/bin/bash
# 视界表@冠军配置补全: y4 第二种子(定案件) + y8/y12 单种子
RV=$(pgrep -of "bash /workspace/recover.sh"); [ -n "$RV" ] && while kill -0 "$RV" 2>/dev/null; do sleep 30; done
cd /workspace/code && export PYTHONPATH=/workspace/code
R() { H="$1"; S="$2"; T="$3"; python3 -u multi_asset/train/train_wide_harness.py \
  --wide_dl_path /workspace/data/wide_dl_pm32_hz.npz --target_horizon "$H" --aux_horizons 1,24 \
  --encoder conformer --n_factor_heads 6 --xattn --n_xattn 1 --lam_orth 0 \
  --d_model 64 --n_blocks 2 --year_folds --year_folds_from 2022 --embargo_days 10 \
  --seed "$S" --save_tag "$T" --tag "$T" 2>&1 | tail -3; }
echo "=== [$(date -u +%H:%M:%SZ)] lam0_yr4_s2027 ==="; R 4 2027 rb32_lam0_yr4_s2027
echo "=== [$(date -u +%H:%M:%SZ)] lam0_yr8_s42 ===";  R 8 42   rb32_lam0_yr8_s42
echo "=== [$(date -u +%H:%M:%SZ)] lam0_yr12_s42 ==="; R 12 42  rb32_lam0_yr12_s42
echo "=== h2 完成 $(date -u) ==="
