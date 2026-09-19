#!/bin/bash
# run_batch1.sh — stream T batch 1: the §2 self-check gate (TRAIN_FRAC=0.85, folds 202501 + 202608, both seeds) together with the T2 2026 fold
# (202601 at 0.85, both seeds; T2's 2025 fold IS the 202501 gate fold — same recipe, same cutoff). No T1 fold is run here.
# Launched under setsid; the PGID is written to $W/BATCH1.pgid. Kill only by that PGID.
W=/workspace/retrain_reeval_2026-09-19; S=$W/device; echo $(ps -o pgid= $$ | tr -d ' ') > $W/BATCH1.pgid
echo "BATCH1 start $(date -u +%FT%TZ) pgid=$(cat $W/BATCH1.pgid)" >> $W/logs/commands.txt
bash $S/memguard.sh batch1 30 || { echo "BATCH1 memguard rc=$? — not launched" >> $W/logs/commands.txt; exit 9; }
P=""
for SD in 42 2027; do
  for M in 202501 202608 202601; do
    bash $S/launch_tf.sh SELFCHK $SD 0.85 m$M $M & P="$P $!"; sleep 40
  done
done
RC=""; for p in $P; do wait $p; RC="$RC $?"; done
echo "BATCH1 shards done rcs=[$RC] $(date -u +%FT%TZ)" >> $W/logs/commands.txt
/workspace/venv/bin/python $S/selfcheck_tf.py $W/mwf/SELFCHK $W/receipts/SELFCHECK_tf085.json > $W/logs/selfcheck.log 2>&1; rc=$?
echo "END[selfcheck] rc=$rc $(tail -1 $W/logs/selfcheck.log) $(date -u +%FT%TZ)" >> $W/logs/commands.txt
echo "BATCH1_DONE $(date -u +%FT%TZ)" >> $W/logs/commands.txt
