#!/bin/bash
# run_all.sh — queue the remaining axis-B arms (48 total = 6 rules × 2 kings × 2 calibers × 2 seeds, minus the 4 launched at 23:35Z:
# "R0 pinned log 42" (equivalence receipt) and the smoke arms "R2/R4/R5 rollm log 42"), 6 in parallel via xargs. Single launcher — no second queue may be started.
ROOT=/workspace/review_scratch/cadence_seats/axisB; cd $ROOT
: > logs/arms_queue.txt
for rule in R0 R1 R2 R3 R4 R5; do for king in rollm pinned; do for cal in log prod; do for seed in 42 2027; do
  tag="$rule $king $cal $seed"
  case "$tag" in "R0 pinned log 42"|"R2 rollm log 42"|"R4 rollm log 42"|"R5 rollm log 42") continue ;; esac
  echo "$tag" >> logs/arms_queue.txt
done; done; done; done
echo "QUEUE $(wc -l < logs/arms_queue.txt) arms $(date -u +%FT%TZ)" | tee -a logs/commands.txt
xargs -P 6 -L 1 bash -c 'bash run_axisB.sh $0 $1 $2 $3 > logs/launch_$0_$1_$2_$3.out 2>&1' < logs/arms_queue.txt
echo "RUN_ALL_DONE $(date -u +%FT%TZ)" | tee -a logs/commands.txt
