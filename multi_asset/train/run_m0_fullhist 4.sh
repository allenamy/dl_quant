#!/bin/bash
# M0 FULL-HISTORY walk-forward RETRAINING replay (2023H1..2025H2). Waits for the seq_cache + mh_targets
# extensions (2022-01..) to finish, then launches the retraining (single locked M0 config, funding-
# residual target from the full-history funding_ema cache, expanding-train folds — NO weight look-ahead).
# 0C pre-reg: --kill_gates ON (fold-A val-rankIC<0.005@ep8 -> KILL+stop; sigma<0.01 -> KILL fold;
# a KILL is a FINDING). 3 YEAR folds A/B/C (tr2022->te2023 / tr2022-23->te2024 / tr2022-24->te2025).
# 0B, 2026-07-09.
set -u
ROOT=/mnt/storage/private/work_hsy/quant_research_multi_asset
until grep -q "\[seq\] done" /tmp/seq_ext.log 2>/dev/null && grep -q "\[mh_long\] done" /tmp/mh_ext.log 2>/dev/null; do
    sleep 60
done
sleep 15
cd "$ROOT"
source /root/miniconda3/etc/profile.d/conda.sh
conda activate hsy_v5push
echo "[orch] prereqs ready ($(ls multi_asset/exports/seq_cache/*.npz | wc -l) seq days) -> M0 full-hist retraining $(date)" > /tmp/m0_fullhist.log
python -u multi_asset/train/train_temporal_spatial.py \
    --milestone 0 --horizon 3600 \
    --w_pin 1.0 --w_rank 0.1 --w_huber 0.0 \
    --resid_on_funding --funding_dir funding_ema_hist --fh_folds --kill_gates --seed 42 \
    --save_tag m0_fullhist_wf >> /tmp/m0_fullhist.log 2>&1
echo "[orch] M0 FULLHIST EXIT $?" >> /tmp/m0_fullhist.log
