#!/bin/bash
# run_train.sh — dl_monthly_wf: sequential GPU campaign, ONE training process at a time (lead's rule).
# E60 (existing fold convention) over 2025-01..2026-08, then E1 (K2 convention). Idempotent: finished folds are skipped by the trainer.
# usage: nohup bash run_train.sh > logs/run_train.out 2>&1 &
R=/workspace/review_scratch/dl_monthly_wf; PY=/workspace/venv/bin/python; cd $R || exit 2
mkdir -p logs
[ -f $R/pod_f10_train_monthly.py ] || { echo "trainer missing"; exit 3; }
echo "LAUNCH $(date -u +%FT%TZ) gpu_mem_used=$(nvidia-smi --query-gpu=memory.used --format=csv,noheader) other_train_procs=$(ps aux | grep -v grep | grep -c 'pod_f10_train')" >> logs/commands.txt
for E in 60 1; do
  CMD="env ARM=V2MAIN V2=1 SEED=42 F10_DLW=/workspace/dlw_ext F10_OUT=/workspace/f8_ext MWF_OUT=$R EMBARGO=$E $PY $R/pod_f10_train_monthly.py"
  echo "CMD[E$E] $(date -u +%FT%TZ): $CMD" >> logs/commands.txt
  $CMD >> logs/train_mE$E.log 2>&1; rc=$?
  echo "END[E$E] rc=$rc $(date -u +%FT%TZ)" >> logs/commands.txt
  [ $rc -eq 0 ] || { echo "TRAIN_FAILED E$E rc=$rc $(date -u +%FT%TZ)" >> logs/commands.txt; exit $rc; }
done
echo "TRAIN_ALL_DONE $(date -u +%FT%TZ)" >> logs/commands.txt
