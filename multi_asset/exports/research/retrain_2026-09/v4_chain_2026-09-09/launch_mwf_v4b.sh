#!/bin/bash
# launch_mwf_v4.sh — PREREG_v4 §2.4: one shard of one (TARGET, SEED) chain. usage: launch_mwf_v4.sh <TARGET: RAW|CLIP> <SEED: 42|2027> <shard> <MONTHS csv>
T=$1; SD=$2; K=$3; M=$4; B=/workspace/review_scratch; PY=/workspace/venv/bin/python; cd $B || exit 2
case $T in RAW) DLW=/workspace/dlw_v4raw ;; CLIP) DLW=/workspace/dlw_hf3 ;; *) echo "bad target $T"; exit 2 ;; esac
case $SD in 42|2027) ;; *) echo "bad seed $SD"; exit 2 ;; esac
O=/workspace/f8_v4/${MWF_ROOT:-mwf}/${T}_s${SD}/shard$K; mkdir -p $O /workspace/f8_v4/logs
CMD="env ARM=V2MAIN V2=1 SEED=$SD F10_DLW=$DLW F10_OUT=/workspace/f8_v4 F10_GATE_JSON=/workspace/f8_v4/gates/F10_GATE_$T.json MWF_OUT=$O EMBARGO=1 MWF_TAG=mE1cX7 BEST_EP_FIX=7 MONTHS=$M $PY $B/pod_f10_train_monthly_v4.py"
T0=$(date +%s); echo "CMD[$T s$SD shard$K] $(date -u +%FT%TZ) gpu_mem=$(nvidia-smi --query-gpu=memory.used --format=csv,noheader) : $CMD" >> /workspace/f8_v4/logs/commands.txt
$CMD > /workspace/f8_v4/logs/train_${T}_s${SD}_shard$K.log 2>&1 & P=$!; echo "PID[$T s$SD shard$K] python $P (launcher $$) $(date -u +%FT%TZ)" >> /workspace/f8_v4/logs/commands.txt; wait $P; rc=$?
echo "END[$T s$SD shard$K] python $P rc=$rc $(date -u +%FT%TZ) wall $(( $(date +%s) - T0 )) s; folds done: $(ls $O/preds_fold/ 2>/dev/null | wc -l); MWF_TRAIN_DONE: $(grep -c MWF_TRAIN_DONE /workspace/f8_v4/logs/train_${T}_s${SD}_shard$K.log)" >> /workspace/f8_v4/logs/commands.txt
exit $rc
