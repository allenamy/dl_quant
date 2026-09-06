#!/bin/bash
# launch_mwf_constseed.sh — addendum §11: mE1 monthly folds with CONSTANT seed 42 (pod_f10_train_monthly_constseed.py), embargo 1, tag mE1c, sharded via MONTHS.
K=$1; M=$2; B=/workspace/review_scratch/allweather_trackB; PY=/workspace/venv/bin/python; cd $B || exit 2
O=$B/mE1_constseed/shard$K; mkdir -p $O
CMD="env ARM=V2MAIN V2=1 SEED=42 F10_DLW=/workspace/dlw_ext F10_OUT=/workspace/f8_ext MWF_OUT=$O EMBARGO=1 MWF_TAG=mE1c MONTHS=$M $PY $B/pod_f10_train_monthly_constseed.py"
T0=$(date +%s); echo "CMD[mE1c shard$K] $(date -u +%FT%TZ) gpu_mem=$(nvidia-smi --query-gpu=memory.used --format=csv,noheader) : $CMD" >> logs/commands.txt
$CMD > logs/train_mE1c_shard$K.log 2>&1 & P=$!; echo "PID[mE1c shard$K] python $P (launcher $$) $(date -u +%FT%TZ)" >> logs/commands.txt; wait $P; rc=$?
echo "END[mE1c shard$K] python $P rc=$rc $(date -u +%FT%TZ) wall $(( $(date +%s) - T0 )) s; folds done: $(ls $O/preds_fold/ 2>/dev/null | wc -l); MWF_TRAIN_DONE: $(grep -c MWF_TRAIN_DONE logs/train_mE1c_shard$K.log)" >> logs/commands.txt
