#!/bin/bash
# chain_k2.sh — wait for D1 to finish, then launch K2 (MODE=monthly1). Detached via nohup. Sequential so each LGBM fit keeps n_jobs=48 uncontended.
ROOT=/workspace/review_scratch/cadence_seats/axisA
cd $ROOT
echo "chain_k2 start $(date -u +%Y-%m-%dT%H:%M:%SZ)"
until grep -qE "^DONE d1|Traceback" logs/d1.log; do sleep 15; done
echo "d1 finished $(date -u +%Y-%m-%dT%H:%M:%SZ): $(grep -E '^(D1 RECEIPT|SAVED|DONE|Traceback)' logs/d1.log | cut -c1-300)"
bash launch_train.sh monthly1
echo "CHAIN_K2_LAUNCHED $(date -u +%Y-%m-%dT%H:%M:%SZ)"
