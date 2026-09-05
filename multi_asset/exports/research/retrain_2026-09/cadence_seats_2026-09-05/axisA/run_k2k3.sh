#!/bin/bash
# run_k2k3.sh — K2 (rollm1) and K3 (rollw1) L-fix arms in both calibers (4 processes x 4 threads), then weekly age curve (addendum) and IC/legs tables.
ROOT=/workspace/review_scratch/cadence_seats/axisA; PY=/workspace/venv/bin/python
cd $ROOT
bash run_arms.sh rollm1 > logs/run_arms_rollm1.out 2>&1 &
bash run_arms.sh rollw1 > logs/run_arms_rollw1.out 2>&1 &
echo "CMD[d1w_curve] $(date -u +%Y-%m-%dT%H:%M:%SZ): cd $ROOT && $PY d1w_curve.py > logs/d1w_curve.log 2>&1" | tee -a logs/commands.txt
$PY d1w_curve.py > logs/d1w_curve.log 2>&1; echo "d1w_curve rc=$?"
echo "CMD[ic_legs all kings] $(date -u +%Y-%m-%dT%H:%M:%SZ): cd $ROOT && $PY ic_legs.py > logs/ic_legs.log 2>&1" | tee -a logs/commands.txt
$PY ic_legs.py > logs/ic_legs.log 2>&1; echo "ic_legs rc=$?"
wait
echo "K2K3_ARMS_DONE $(date -u +%Y-%m-%dT%H:%M:%SZ)" | tee -a logs/commands.txt
