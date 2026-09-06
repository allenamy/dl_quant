#!/bin/bash
# launch_yearly_save.sh — addendum §11 diagnostic: yearly-fold V2MAIN (gate form) with the yearly_save patch (state dicts + all-anchor scores), seed $1.
SEED=$1; B=/workspace/review_scratch/allweather_trackB; PY=/workspace/venv/bin/python; cd $B || exit 2
O=$B/mE1_constseed/yearly_out; mkdir -p $O/preds $O/results $O/models $O/preds_fold; ln -sfn /workspace/f8_ext/data $O/data
CMD="env ARM=V2MAIN_YS V2=1 SEED=$SEED F10_DLW=/workspace/dlw_ext F10_OUT=$O $PY $B/pod_f10_train_yearly_save.py"
T0=$(date +%s); echo "CMD[YS s$SEED] $(date -u +%FT%TZ) gpu_mem=$(nvidia-smi --query-gpu=memory.used --format=csv,noheader) : $CMD" >> logs/commands.txt
$CMD > logs/train_YS_s$SEED.log 2>&1 & P=$!; echo "PID[YS s$SEED] python $P (launcher $$) $(date -u +%FT%TZ)" >> logs/commands.txt; wait $P; rc=$?
echo "END[YS s$SEED] python $P rc=$rc $(date -u +%FT%TZ) wall $(( $(date +%s) - T0 )) s; F10_TRAIN_DONE: $(grep -c F10_TRAIN_DONE logs/train_YS_s$SEED.log); preds sha $(sha256sum $O/preds/f10_V2MAIN_YS_s$SEED.npy | cut -c1-16)" >> logs/commands.txt
