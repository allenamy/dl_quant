#!/bin/bash
W=/workspace/retrain_reeval_2026-09-19; echo $(ps -o pgid= $$ | tr -d " ") > $W/A1REPRO.pgid
for s in 42 2027; do bash $W/device/run_book_arm.sh A1R $s /workspace/fp2_2026-09/king_v4/SLOW_v4.npy f10_v4RAW_s$s.npy > $W/logs/book_A1R_s$s.out 2>&1 & done; wait
echo "A1REPRO_DONE $(date -u +%FT%TZ)" >> $W/logs/commands.txt
