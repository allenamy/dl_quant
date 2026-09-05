#!/bin/bash
R=/workspace/review_scratch/dl_monthly_wf; PY=/workspace/venv/bin/python; cd $R || exit 2
CMD="env ARM=V2MAIN V2=1 SEED=42 F10_DLW=/workspace/dlw_ext F10_OUT=/workspace/f8_ext MWF_OUT=$R EMBARGO=1 $PY $R/pod_f10_train_monthly.py"
T0=$(date +%s); echo "CMD[E1] $(date -u +%FT%TZ): $CMD" >> logs/commands.txt
$CMD >> logs/train_mE1.log 2>&1 & P=$!; echo "PID[E1] python $P (launcher $$) $(date -u +%FT%TZ)" >> logs/commands.txt; wait $P; rc=$?
echo "END[E1] rc=$rc $(date -u +%FT%TZ) wall $(( $(date +%s) - T0 )) s" >> logs/commands.txt
