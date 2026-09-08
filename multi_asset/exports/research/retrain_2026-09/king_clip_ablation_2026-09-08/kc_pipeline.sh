#!/bin/bash
# Runs entirely on pod2: wait for DROP -> book chain -> judge. Writes PIPELINE_DONE / PIPELINE_FAIL.
AB=/workspace/review_scratch/king_clip_ablation
P=$AB/logs/pipeline.log
: > $P
echo "PIPELINE_START $(date -u +%FT%TZ)" >> $P
for i in $(seq 1 240); do
  if grep -q DROP_DONE $AB/logs/drop.log 2>/dev/null; then break; fi
  if grep -q Traceback $AB/logs/drop.log 2>/dev/null; then echo "PIPELINE_FAIL drop_traceback" >> $P; exit 1; fi
  if ! pgrep -f king_clip_ablation_drop.py > /dev/null; then echo "PIPELINE_FAIL drop_gone" >> $P; exit 1; fi
  sleep 30
done
grep -q DROP_DONE $AB/logs/drop.log || { echo "PIPELINE_FAIL drop_timeout" >> $P; exit 1; }
echo "DROP_OK $(date -u +%FT%TZ)" >> $P
cd /workspace/review_scratch/health_check || exit 1
bash chain_kingclip.sh >> $P 2>&1
grep -q CHAIN_KINGCLIP_DONE logs/chain_kingclip.log || { echo "PIPELINE_FAIL chain" >> $P; exit 1; }
echo "CHAIN_OK $(date -u +%FT%TZ)" >> $P
/workspace/venv/bin/python /workspace/review_scratch/judge_kingclip.py > $AB/logs/judge.log 2>&1
rc=$?
echo "JUDGE rc=$rc $(date -u +%FT%TZ)" >> $P
if [ $rc -ne 0 ]; then echo "PIPELINE_FAIL judge" >> $P; exit 1; fi
echo "PIPELINE_DONE $(date -u +%FT%TZ)" >> $P
