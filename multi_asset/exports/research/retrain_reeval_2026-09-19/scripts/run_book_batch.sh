#!/bin/bash
# run_book_batch.sh <ARM> <SLOW abs> <FPRED pattern with {s}> — both seeds of one book arm through run_book_arm.sh (PGID recorded per call).
W=/workspace/retrain_reeval_2026-09-19; A=$1; SL=$2; FPP=$3; echo $(ps -o pgid= $$ | tr -d " ") > $W/BOOK_$A.pgid
for s in 42 2027; do FP=${FPP//\{s\}/$s}; bash $W/device/run_book_arm.sh $A $s $SL $FP > $W/logs/book_${A}_s$s.out 2>&1 & done; wait
echo "BOOK_BATCH_DONE[$A] $(date -u +%FT%TZ)" >> $W/logs/commands.txt
