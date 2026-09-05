#!/bin/bash
# launch_variant.sh — dl_monthly_wf: run one variant (EMBARGO=60|1) of the monthly trainer, resume-aware (finished folds skipped by the trainer),
# recording CMD / python PID / END rc / wall-clock in logs/commands.txt.   usage: nohup bash launch_variant.sh <60|1> <label> &
E=$1; LBL=$2; R=/workspace/review_scratch/dl_monthly_wf; PY=/workspace/venv/bin/python; cd $R || exit 2
CMD="env ARM=V2MAIN V2=1 SEED=42 F10_DLW=/workspace/dlw_ext F10_OUT=/workspace/f8_ext MWF_OUT=$R EMBARGO=$E $PY $R/pod_f10_train_monthly.py"
T0=$(date +%s); echo "CMD[$LBL] $(date -u +%FT%TZ): $CMD" >> logs/commands.txt
$CMD >> logs/train_mE$E.log 2>&1 & P=$!; echo "PID[$LBL] python $P (launcher $$) $(date -u +%FT%TZ)" >> logs/commands.txt; wait $P; rc=$?
echo "END[$LBL] python $P rc=$rc $(date -u +%FT%TZ) wall $(( $(date +%s) - T0 )) s; MWF_TRAIN_DONE lines in log: $(grep -c "MWF_TRAIN_DONE mE$E" logs/train_mE$E.log)" >> logs/commands.txt
