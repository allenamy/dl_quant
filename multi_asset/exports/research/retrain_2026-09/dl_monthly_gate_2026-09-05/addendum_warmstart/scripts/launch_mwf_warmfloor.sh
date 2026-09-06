#!/bin/bash
# launch_mwf_warmfloor.sh — PREREG_incremental_retrain §1 末句: W1+FLOOR5 combination arm (warm-start chain + BEST_EP_FLOOR=5), ONE sequential process. usage: launch_mwf_warmfloor.sh <ARM: W1F5|WF0ident> [MONTHS]
ARM=$1; M=${2:-}; B=/workspace/review_scratch/allweather_trackB; PY=/workspace/venv/bin/python; cd $B || exit 2
INIT=$B/mE1_constseed/yearly_out/models/f10_V2MAIN_YS_s42_2025.pt
case $ARM in W1F5) KN="INIT_STATE=$INIT LR=3e-4 BEST_EP_FLOOR=5"; TAG=mE1w1F5 ;; WF0ident) KN="LR=3e-4 BEST_EP_FLOOR=0"; TAG=mE1c ;; *) echo "bad arm $ARM"; exit 2 ;; esac
O=$B/warmstart/$ARM; mkdir -p $O; MENV=""; [ -n "$M" ] && MENV="MONTHS=$M"
CMD="env ARM=V2MAIN V2=1 SEED=42 F10_DLW=/workspace/dlw_ext F10_OUT=/workspace/f8_ext MWF_OUT=$O EMBARGO=1 MWF_TAG=$TAG $KN $MENV $PY $B/pod_f10_train_monthly_warm_earlystop.py"
T0=$(date +%s); echo "CMD[$ARM] $(date -u +%FT%TZ) gpu_mem=$(nvidia-smi --query-gpu=memory.used --format=csv,noheader) : $CMD" >> logs/commands.txt
$CMD >> logs/train_${ARM}.log 2>&1 & P=$!; echo "PID[$ARM] python $P (launcher $$) $(date -u +%FT%TZ)" >> logs/commands.txt; wait $P; rc=$?
echo "END[$ARM] python $P rc=$rc $(date -u +%FT%TZ) wall $(( $(date +%s) - T0 )) s; folds done: $(ls $O/preds_fold/ 2>/dev/null | wc -l); MWF_TRAIN_DONE: $(grep -c MWF_TRAIN_DONE logs/train_${ARM}.log)" >> logs/commands.txt
