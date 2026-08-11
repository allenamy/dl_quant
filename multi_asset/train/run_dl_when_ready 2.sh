#!/bin/bash
# Auto-launch the DL stage-2 gated run the moment seq_cache finishes building.
# Survives agent turn-end / rate-limit (nohup'd, server-side). 0B, 2026-07-08.
# Single pre-registered run: pooled M0 Conformer stem, y_3600 residual-on-funding target,
# pinball + 0.1*LambdaRankIC, sigma-gate BEST, 3-fold walk-forward, kill gates locked.
set -u
ROOT=/mnt/storage/private/work_hsy/quant_research_multi_asset
# seq_cache done = the build's FINAL "[seq]" summary line (startup is the 1st "[seq]" line).
until [ "$(grep -c '^\[seq\]' /tmp/seq_cache.log 2>/dev/null)" -ge 2 ]; do sleep 30; done
sleep 5
cd "$ROOT"
source /root/miniconda3/etc/profile.d/conda.sh
conda activate hsy_v5push
echo "[orch] seq_cache ready ($(ls multi_asset/exports/seq_cache/*.npz | wc -l) days) -> launching DL stage-2 $(date)" > /tmp/dl_stage2.log
python -u multi_asset/train/train_temporal_spatial.py \
    --milestone 0 --horizon 3600 \
    --w_pin 1.0 --w_rank 0.1 --w_huber 0.0 \
    --resid_on_funding --kill_gates \
    --save_tag fund_resid_h3600 >> /tmp/dl_stage2.log 2>&1
echo "[orch] DL EXIT $?" >> /tmp/dl_stage2.log
