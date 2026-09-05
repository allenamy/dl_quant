#!/bin/bash
# launch_train.sh — Track B (PREREG_allweather_programme §3 Track B): one fit of the patched trainer pod_f10_train_dro.py in the 09-01 gate
# yearly-fold form (folds 2023/2024/2025/2026, train < test year, EMB 60; recipe ARM V2MAIN: V2=1 COST 3.52 LDD 0.25 EPOCHS 15 LR 3e-4).
# Writes only under /workspace/review_scratch/allweather_trackB/ (F10_OUT=$B/f8_out; f8_out/data is a symlink to /workspace/f8_ext/data, read-only).
# usage: launch_train.sh <LABEL> <SEED> <DRO_T> <SS_W>      e.g. launch_train.sh IDENT 42 inf 0 | B1 42 0.5 0 | B2 42 inf 1.0 | B3 42 0.5 1.0
LBL=$1; SEED=$2; DRO=$3; SSW=$4; B=/workspace/review_scratch/allweather_trackB; PY=/workspace/venv/bin/python; cd $B || exit 2
[ -n "$SSW" ] || { echo "usage: launch_train.sh <LABEL> <SEED> <DRO_T> <SS_W>"; exit 2; }
ARM=V2MAIN_${LBL}
CMD="env ARM=$ARM V2=1 SEED=$SEED DRO_T=$DRO SS_W=$SSW F10_DLW=/workspace/dlw_ext F10_OUT=$B/f8_out $PY $B/pod_f10_train_dro.py"
T0=$(date +%s); echo "CMD[$LBL s$SEED] $(date -u +%FT%TZ) gpu_mem=$(nvidia-smi --query-gpu=memory.used --format=csv,noheader) : $CMD" >> logs/commands.txt
$CMD > logs/train_${LBL}_s${SEED}.log 2>&1 & P=$!; echo "PID[$LBL s$SEED] python $P (launcher $$) $(date -u +%FT%TZ)" >> logs/commands.txt; wait $P; rc=$?
echo "END[$LBL s$SEED] python $P rc=$rc $(date -u +%FT%TZ) wall $(( $(date +%s) - T0 )) s; F10_TRAIN_DONE: $(grep -c F10_TRAIN_DONE logs/train_${LBL}_s${SEED}.log); preds sha $(sha256sum f8_out/preds/f10_${ARM}_s${SEED}.npy 2>/dev/null | cut -c1-16)" >> logs/commands.txt
