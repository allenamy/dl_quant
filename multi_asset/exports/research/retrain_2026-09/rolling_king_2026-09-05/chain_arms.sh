#!/bin/bash
# chain_arms.sh — wait for each rolling training to finish, then run its STEP 3 arms (both calibers). Detached via nohup.
ROOT=/workspace/review_scratch/rolling_king
cd $ROOT
echo "chain start $(date -u +%Y-%m-%dT%H:%M:%SZ)"
until grep -qE "^DONE monthly|Traceback" logs/rollm.log; do sleep 20; done
echo "monthly finished $(date -u +%Y-%m-%dT%H:%M:%SZ): $(grep -E '^SAVED|^DONE|Traceback' logs/rollm.log | cut -c1-300)"
bash run_arms.sh rollm > logs/run_arms_rollm.out 2>&1
echo "rollm arms finished $(date -u +%Y-%m-%dT%H:%M:%SZ)"
until [ -f logs/rollq.log ] && grep -qE "^DONE quarterly|Traceback" logs/rollq.log; do sleep 20; done
echo "quarterly finished $(date -u +%Y-%m-%dT%H:%M:%SZ): $(grep -E '^SAVED|^DONE|Traceback' logs/rollq.log | cut -c1-300)"
bash run_arms.sh rollq > logs/run_arms_rollq.out 2>&1
echo "rollq arms finished $(date -u +%Y-%m-%dT%H:%M:%SZ)"
echo "CHAIN_DONE"
