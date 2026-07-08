#!/bin/bash
# M0 seed-robustness: re-run the AUDITED M0 config (fund_resid_h3600) at seeds 43 & 44, seed-only
# change (SAME pipeline/folds/gates), serial on the single GPU. For 0C's seed-stability eval. 0B.
set -u
ROOT=/mnt/storage/private/work_hsy/quant_research_multi_asset
cd "$ROOT"
source /root/miniconda3/etc/profile.d/conda.sh
conda activate hsy_v5push
echo "[seeds] start $(date)" > /tmp/m0_seeds.log
for S in 43 44; do
    echo "[seeds] === seed $S ===" >> /tmp/m0_seeds.log
    python -u multi_asset/train/train_temporal_spatial.py \
        --milestone 0 --horizon 3600 \
        --w_pin 1.0 --w_rank 0.1 --w_huber 0.0 \
        --resid_on_funding --kill_gates \
        --seed "$S" --save_tag "fund_resid_h3600_s$S" > "/tmp/m0_s$S.log" 2>&1
    echo "[seeds] seed $S exit $?" >> /tmp/m0_seeds.log
done
echo "[seeds] M0 SEEDS DONE $(date)" >> /tmp/m0_seeds.log
