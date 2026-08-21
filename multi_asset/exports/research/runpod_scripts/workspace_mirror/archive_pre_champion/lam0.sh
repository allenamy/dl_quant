#!/bin/bash
# ★ 冠军配置复原实验: lam_orth=0 (记忆: champion=lamorth0_xattn, lam_orth 1.0=penalized)
# 预测: rb32+xattn+lam0 ≈ 0.045 (S1 干净记录). 若中 ⇒ 全天系统性偏低结案 = 默认值陷阱第三例
# (xattn 默认 false / 面板默认脏 / lam_orth 默认惩罚)。
B4=$(pgrep -of "bash /workspace/bk4.sh"); [ -n "$B4" ] && while kill -0 "$B4" 2>/dev/null; do sleep 20; done
cd /workspace/code && export PYTHONPATH=/workspace/code
for S in 42 2027; do
  echo "=== [$(date -u +%H:%M:%SZ)] rb32_lam0_yr24_s${S} ==="
  python3 -u multi_asset/train/train_wide_harness.py \
    --wide_dl_path /workspace/data/wide_dl_prodmask32.npz --target_horizon 24 --aux_horizons 1,24 \
    --encoder conformer --n_factor_heads 6 --xattn --n_xattn 1 --d_model 64 --n_blocks 2 \
    --lam_orth 0 --year_folds --year_folds_from 2022 --embargo_days 10 --seed "$S" \
    --save_tag "rb32_lam0_s${S}" --tag "rb32_lam0_s${S}" 2>&1 | tail -4
done
echo "=== [$(date -u +%H:%M:%SZ)] rb32_lam0_yr4_s42 (对 S1 的 4h 口径) ==="
python3 -u multi_asset/train/train_wide_harness.py \
  --wide_dl_path /workspace/data/wide_dl_pm32_hz.npz --target_horizon 4 \
  --encoder conformer --n_factor_heads 6 --xattn --n_xattn 1 --d_model 64 --n_blocks 2 \
  --lam_orth 0 --year_folds --year_folds_from 2022 --embargo_days 10 --seed 42 \
  --save_tag rb32_lam0_yr4_s42 --tag rb32_lam0_yr4_s42 2>&1 | tail -4
echo "=== lam0 实验完成 $(date -u) ==="
