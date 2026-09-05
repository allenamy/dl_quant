#!/bin/bash
# launch_train.sh <d1|monthly1|weekly1> — detached training launch; command appended verbatim to logs/commands.txt
MODE=$1; [ -n "$MODE" ] || { echo "usage: launch_train.sh <d1|monthly1|weekly1>"; exit 2; }
ROOT=/workspace/review_scratch/cadence_seats/axisA
cd $ROOT
CMD="cd $ROOT && nohup bash -c \"MODE=$MODE NJOBS=48 /workspace/venv/bin/python pod_king_cadence.py > logs/$MODE.log 2>&1\" > logs/nohup_$MODE.out 2>&1 < /dev/null &"
echo "CMD[train $MODE] $(date -u +%Y-%m-%dT%H:%M:%SZ): $CMD" | tee -a logs/commands.txt
nohup bash -c "MODE=$MODE NJOBS=48 /workspace/venv/bin/python pod_king_cadence.py > logs/$MODE.log 2>&1" > logs/nohup_$MODE.out 2>&1 < /dev/null &
echo "launched pid $!"
