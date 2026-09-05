#!/bin/bash
# launch_mwf_s2027.sh — dl_monthly_gate addendum (lead 09-05 ~14:55Z): re-train the 20 mE1 monthly folds with SEED=2027 using the dl_monthly_wf monthly trainer
# (pod_f10_train_monthly.py sha 7bb39f8d…, embargo 1, same inputs) with ONE patch: the env whitelist `SEED == 42` → `SEED in (42, 2027)` (the verbatim file refuses
# any other seed). Folds are sharded over parallel processes via MONTHS (per-fold RNG = SEED+YM ⇒ sharding has no effect on any fold); each shard has its own
# MWF_OUT so the per-process results json / stitched file cannot race; merge_mwf.py rebuilds the stitched ext-grid file from preds_fold/*.npz afterwards.
# usage: launch_mwf_s2027.sh <shard_id> <MONTHS csv>
K=$1; M=$2; B=/workspace/review_scratch/allweather_trackB; PY=/workspace/venv/bin/python; cd $B || exit 2
O=$B/mwf_s2027/shard$K; mkdir -p $O
CMD="env ARM=V2MAIN V2=1 SEED=2027 F10_DLW=/workspace/dlw_ext F10_OUT=/workspace/f8_ext MWF_OUT=$O EMBARGO=1 MONTHS=$M $PY $B/pod_f10_train_monthly_s2027.py"
T0=$(date +%s); echo "CMD[mE1s2027 shard$K] $(date -u +%FT%TZ) gpu_mem=$(nvidia-smi --query-gpu=memory.used --format=csv,noheader) : $CMD" >> logs/commands.txt
$CMD > logs/train_mE1_s2027_shard$K.log 2>&1 & P=$!; echo "PID[mE1s2027 shard$K] python $P (launcher $$) $(date -u +%FT%TZ)" >> logs/commands.txt; wait $P; rc=$?
echo "END[mE1s2027 shard$K] python $P rc=$rc $(date -u +%FT%TZ) wall $(( $(date +%s) - T0 )) s; folds done: $(ls $O/preds_fold/ 2>/dev/null | wc -l); MWF_TRAIN_DONE: $(grep -c MWF_TRAIN_DONE logs/train_mE1_s2027_shard$K.log)" >> logs/commands.txt
