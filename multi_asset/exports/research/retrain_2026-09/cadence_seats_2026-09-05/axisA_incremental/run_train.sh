#!/bin/bash
# run_train.sh <ident|KR|KC> — one training run, foreground, threads capped at 12 (OMP + NJOBS); command appended verbatim to logs/commands.txt.
MODE=$1; [ -n "$MODE" ] || { echo "usage: run_train.sh <ident|KR|KC>"; exit 2; }
ROOT=/workspace/review_scratch/cadence_seats/axisA_incremental; cd $ROOT
export OMP_NUM_THREADS=12 OPENBLAS_NUM_THREADS=12 MKL_NUM_THREADS=12
CMD="cd $ROOT && MODE=$MODE NJOBS=12 OMP_NUM_THREADS=12 /workspace/venv/bin/python train_incremental.py > logs/train_$MODE.log 2>&1"
echo "CMD[train $MODE] $(date -u +%FT%TZ): $CMD" >> logs/commands.txt
MODE=$MODE NJOBS=12 /workspace/venv/bin/python train_incremental.py > logs/train_$MODE.log 2>&1; rc=$?
echo "END[train $MODE] rc=$rc $(date -u +%FT%TZ)" >> logs/commands.txt
grep -E "^(CONFIG|PREP|FOLDS|START RECEIPT|KR_IDENTITY|KC_IDENTITY|KC_SKLEARN_PATH|IDENTITY_DONE|SAVED|IC_AGE|DONE|Traceback|AssertionError)" logs/train_$MODE.log | cut -c1-600
exit $rc
