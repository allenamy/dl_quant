#!/bin/bash
# launch_mwf_earlystop.sh — PREREG_dl_monthly_earlystop: one shard of one arm. usage: launch_mwf_earlystop.sh <ARM: FLOOR5|FIX7|FLOOR0> <shard> <MONTHS csv>
ARM=$1; K=$2; M=$3; B=/workspace/review_scratch/allweather_trackB; PY=/workspace/venv/bin/python; cd $B || exit 2
case $ARM in FLOOR5) KN="BEST_EP_FLOOR=5"; TAG=mE1cF5 ;; FIX7) KN="BEST_EP_FIX=7"; TAG=mE1cX7 ;; FLOOR0) KN="BEST_EP_FLOOR=0"; TAG=mE1c ;; *) echo "bad arm $ARM"; exit 2 ;; esac
O=$B/earlystop/$ARM/shard$K; mkdir -p $O
CMD="env ARM=V2MAIN V2=1 SEED=42 F10_DLW=/workspace/dlw_ext F10_OUT=/workspace/f8_ext MWF_OUT=$O EMBARGO=1 MWF_TAG=$TAG $KN MONTHS=$M $PY $B/pod_f10_train_monthly_earlystop.py"
T0=$(date +%s); echo "CMD[$ARM shard$K] $(date -u +%FT%TZ) gpu_mem=$(nvidia-smi --query-gpu=memory.used --format=csv,noheader) : $CMD" >> logs/commands.txt
$CMD > logs/train_${ARM}_shard$K.log 2>&1 & P=$!; echo "PID[$ARM shard$K] python $P (launcher $$) $(date -u +%FT%TZ)" >> logs/commands.txt; wait $P; rc=$?
echo "END[$ARM shard$K] python $P rc=$rc $(date -u +%FT%TZ) wall $(( $(date +%s) - T0 )) s; folds done: $(ls $O/preds_fold/ 2>/dev/null | wc -l); MWF_TRAIN_DONE: $(grep -c MWF_TRAIN_DONE logs/train_${ARM}_shard$K.log)" >> logs/commands.txt
