#!/bin/bash
# 家族判决复核 @ 冠军配置: ch53(32+metrics 扁平) 双种子 —— 红队点②的定案件
while [ -n "$(nvidia-smi --query-compute-apps=pid --format=csv,noheader | head -1)" ]; do sleep 60; done
sleep 10
export PYTORCH_CUDA_ALLOC_CONF=expandable_segments:True
cd /workspace/code && export PYTHONPATH=/workspace/code
for S in 42 2027; do
  echo "=== [$(date -u +%H:%M:%SZ)] ch53_lam0_s${S} ==="
  python3 -u multi_asset/train/train_wide_harness.py \
    --wide_dl_path /workspace/data/wide_dl_53ch.npz --target_horizon 24 --aux_horizons 1,24 \
    --encoder conformer --n_factor_heads 6 --xattn --n_xattn 1 --lam_orth 0 \
    --d_model 64 --n_blocks 2 --year_folds --year_folds_from 2022 --embargo_days 10 \
    --seed "$S" --save_tag "ch53_lam0_s${S}" --tag "ch53_lam0_s${S}" 2>&1 | tail -3
done
echo "=== confirm_q 完成 $(date -u) ==="
