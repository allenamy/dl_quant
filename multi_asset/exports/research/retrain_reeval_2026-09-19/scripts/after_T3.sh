#!/bin/bash
# after_T3.sh — bounded wait (<= 90 min) for T3_ALL_DONE, then the T3 book replays (SLOW = SLOW_T3, F10 = A1 files).
W=/workspace/retrain_reeval_2026-09-19; echo $(ps -o pgid= $$ | tr -d " ") > $W/AFTER_T3.pgid; n=0
until grep -aq "T3_ALL_DONE" $W/logs/commands.txt; do grep -aq "END\[T3 months\] rc=[1-9]" $W/logs/commands.txt && { echo "AFTER_T3 abort: T3 failed" >> $W/logs/commands.txt; exit 3; }; sleep 30; n=$((n+1)); [ $n -gt 180 ] && { echo "AFTER_T3 timeout" >> $W/logs/commands.txt; exit 9; }; done
bash $W/device/run_book_batch.sh T3 $W/king/SLOW_T3.npy "f10_v4RAW_s{s}.npy"
