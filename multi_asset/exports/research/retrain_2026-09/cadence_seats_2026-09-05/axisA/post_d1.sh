#!/bin/bash
# post_d1.sh — after D1 finishes: D1 curve (frozen decision on K3), LightGBM-bits noise floor, and the K1-replicate L-fix book runs (noise floor at book level).
ROOT=/workspace/review_scratch/cadence_seats/axisA; PY=/workspace/venv/bin/python
cd $ROOT
until grep -qE "^DONE d1|Traceback" logs/d1.log; do sleep 15; done
grep -q "^DONE d1" logs/d1.log || { echo "D1 FAILED"; exit 1; }
echo "CMD[d1_curve] $(date -u +%Y-%m-%dT%H:%M:%SZ): cd $ROOT && $PY d1_curve.py > logs/d1_curve.log 2>&1" | tee -a logs/commands.txt
$PY d1_curve.py > logs/d1_curve.log 2>&1; echo "d1_curve rc=$?"
echo "CMD[noise_floor] $(date -u +%Y-%m-%dT%H:%M:%SZ): cd $ROOT && $PY noise_floor.py > logs/noise_floor.log 2>&1" | tee -a logs/commands.txt
$PY noise_floor.py > logs/noise_floor.log 2>&1; echo "noise_floor rc=$?"
bash run_arms.sh k1rep > logs/run_arms_k1rep.out 2>&1; echo "k1rep arms rc=$?"
echo "POST_D1_DONE $(date -u +%Y-%m-%dT%H:%M:%SZ)"
