#!/bin/bash
# records END/wall-clock for the already-running E60 python (launched by run_train.sh at 07:21:56Z; loop killed after lead approval)
R=/workspace/review_scratch/dl_monthly_wf; cd $R; P=$1; T0=$(date -u -d 2026-09-05T07:21:56Z +%s)
while kill -0 $P 2>/dev/null; do sleep 20; done
rc=$(grep -c "MWF_TRAIN_DONE mE60" logs/train_mE60.log); echo "END[E60] python pid $P exited $(date -u +%FT%TZ) MWF_TRAIN_DONE_lines=$rc wall $(( $(date +%s) - T0 )) s (from 07:21:56Z)" >> logs/commands.txt
