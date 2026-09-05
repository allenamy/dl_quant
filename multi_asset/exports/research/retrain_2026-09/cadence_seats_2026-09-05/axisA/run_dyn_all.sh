#!/bin/bash
# run_dyn_all.sh — all four kings' L-dyn arms (16 runs, 4 threads each) in parallel.
ROOT=/workspace/review_scratch/cadence_seats/axisA
cd $ROOT
for k in pinned rollm rollm1 rollw1; do bash run_arms_dyn.sh $k > logs/run_arms_dyn_$k.out 2>&1 & done
wait
echo "DYN_ALL_DONE $(date -u +%Y-%m-%dT%H:%M:%SZ)" | tee -a logs/commands.txt
