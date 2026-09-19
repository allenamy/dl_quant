#!/bin/bash
# run_batch2_T1.sh — stream T arm T1 (TRAIN_FRAC = 1.0, 20 monthly folds x 2 seeds). Refuses unless the §2 self-check receipt is GATE=PASS.
# Shards = the A1 round-robin (v4_months.shards over MONTHS_ALL, n=4); both seeds concurrently (8 processes). PGID -> $W/BATCH2.pgid.
W=/workspace/retrain_reeval_2026-09-19; S=$W/device; PY=/workspace/venv/bin/python; echo $(ps -o pgid= $$ | tr -d ' ') > $W/BATCH2.pgid
G=$($PY -c "import json;print(json.load(open('$W/receipts/SELFCHECK_tf085.json'))['GATE'])" 2>/dev/null)
[ "$G" = PASS ] || { echo "BATCH2 REFUSED self-check gate=$G" >> $W/logs/commands.txt; exit 3; }
echo "BATCH2 start $(date -u +%FT%TZ) pgid=$(cat $W/BATCH2.pgid) selfcheck=$G" >> $W/logs/commands.txt
bash $S/memguard.sh batch2 30 || { echo "BATCH2 memguard rc=$? — not launched" >> $W/logs/commands.txt; exit 9; }
SH=("202501,202505,202509,202601,202605" "202502,202506,202510,202602,202606" "202503,202507,202511,202603,202607" "202504,202508,202512,202604,202608")
P=""
for SD in 42 2027; do for K in 0 1 2 3; do bash $S/launch_tf.sh T1 $SD 1.0 $K ${SH[$K]} & P="$P $!"; sleep 30; done; done
RC=""; for p in $P; do wait $p; RC="$RC $?"; done
echo "BATCH2 shards done rcs=[$RC] $(date -u +%FT%TZ)" >> $W/logs/commands.txt
for SD in 42 2027; do $PY $S/merge_streamT.py T1 $SD >> $W/logs/merge_T1.log 2>&1; echo "END[merge T1 s$SD] rc=$? $(date -u +%FT%TZ)" >> $W/logs/commands.txt; done
echo "BATCH2_DONE $(date -u +%FT%TZ)" >> $W/logs/commands.txt
