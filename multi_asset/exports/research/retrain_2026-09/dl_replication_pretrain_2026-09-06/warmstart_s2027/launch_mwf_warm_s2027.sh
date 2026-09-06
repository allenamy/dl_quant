#!/bin/bash
# launch_mwf_warm_s2027.sh — PREREG_dl_warmstart_replication_2026-09-06: ONE process runs the 20 monthly folds IN ORDER
# (warm-start chain, seed 2027). usage: launch_mwf_warm_s2027.sh <ARM: W1_s2027|W2_s2027>
ARM=$1; B=/workspace/review_scratch/allweather_trackB; PY=/workspace/venv/bin/python; cd $B || exit 2
INIT=$B/mE1_constseed/yearly_out/models/f10_V2MAIN_YS_s2027_2025.pt
[ -f "$INIT" ] || { echo "missing INIT $INIT"; exit 3; }
case $ARM in W1_s2027) KN="INIT_STATE=$INIT LR=3e-4"; TAG=mE1w1s27 ;; W2_s2027) KN="INIT_STATE=$INIT LR=1e-4"; TAG=mE1w2s27 ;; *) echo "bad arm $ARM"; exit 2 ;; esac
O=$B/warmstart/$ARM; mkdir -p $O
CMD="env ARM=V2MAIN V2=1 SEED=2027 F10_DLW=/workspace/dlw_ext F10_OUT=/workspace/f8_ext MWF_OUT=$O EMBARGO=1 MWF_TAG=$TAG $KN $PY $B/pod_f10_train_monthly_warmstart_s2027.py"
T0=$(date +%s); echo "CMD[$ARM] $(date -u +%FT%TZ) gpu_mem=$(nvidia-smi --query-gpu=memory.used --format=csv,noheader) du=$(du -sm /workspace | cut -f1)MiB : $CMD" >> logs/commands.txt
$CMD >> logs/train_${ARM}.log 2>&1 & P=$!; echo "PID[$ARM] python $P (launcher $$) $(date -u +%FT%TZ)" >> logs/commands.txt; wait $P; rc=$?
echo "END[$ARM] python $P rc=$rc $(date -u +%FT%TZ) wall $(( $(date +%s) - T0 )) s; folds done: $(ls $O/preds_fold/ 2>/dev/null | wc -l); MWF_TRAIN_DONE: $(grep -c MWF_TRAIN_DONE logs/train_${ARM}.log)" >> logs/commands.txt
