#!/bin/bash
# queue3: zoo56 双种子(冠军配置) — 特征扩容的 DL 判决(排在 h2 之后)
H2=$(pgrep -of "bash h2.sh"); [ -n "$H2" ] && while kill -0 "$H2" 2>/dev/null; do sleep 30; done
RV=$(pgrep -of "bash recover.sh"); [ -n "$RV" ] && while kill -0 "$RV" 2>/dev/null; do sleep 30; done
cd /workspace/code && export PYTHONPATH=/workspace/code
for S in 42 2027; do
  echo "=== [$(date -u +%H:%M:%SZ)] zoo56_yr24_s${S} ==="
  python3 -u multi_asset/train/train_wide_harness.py \
    --wide_dl_path /workspace/data/wide_dl_55ch.npz --target_horizon 24 --aux_horizons 1,24 \
    --encoder conformer --n_factor_heads 6 --xattn --n_xattn 1 --lam_orth 0 \
    --d_model 64 --n_blocks 2 --year_folds --year_folds_from 2022 --embargo_days 10 \
    --seed "$S" --save_tag "zoo56_yr24_s${S}" --tag "zoo56_yr24_s${S}" 2>&1 | tail -3
done
echo "=== q3 完成 $(date -u) ==="
