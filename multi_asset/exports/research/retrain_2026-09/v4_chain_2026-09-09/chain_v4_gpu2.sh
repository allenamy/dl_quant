#!/bin/bash
# chain_v4_gpu2.sh — reordered remainder of chain_v4_post_export.sh (reason: V3′ on RAW s42 shows the RAW-target spectrum collapsed vs HF2 CLIP FIX7; A2 (CLIP target) isolates it, so CLIP s42 first). Same launch/merge steps, resume-safe.
R=/workspace/review_scratch; PY=/workspace/venv/bin/python; L=$R/v4_commands.txt; cd $R || exit 2
say(){ echo "[$(date -u +%FT%TZ)] $*" >> $L; }
SH0=202501,202505,202509,202601,202605; SH1=202502,202506,202510,202602,202606; SH2=202503,202507,202511,202603,202607; SH3=202504,202508,202512,202604,202608
for TS in "CLIP 42" "RAW 2027" "CLIP 2027"; do set -- $TS; T=$1; SD=$2
  say "F10 chain $T s$SD start (gpu2 order)"; bash launch_mwf_v4.sh $T $SD 0 $SH0 & bash launch_mwf_v4.sh $T $SD 1 $SH1 & bash launch_mwf_v4.sh $T $SD 2 $SH2 & bash launch_mwf_v4.sh $T $SD 3 $SH3 & wait
  say "F10 chain $T s$SD shards ended: $(grep -a -c "^END\[$T s$SD shard.*rc=0" /workspace/f8_v4/logs/commands.txt)/4 rc=0"
  $PY merge_mwf_v4.py $T $SD > /workspace/f8_v4/logs/merge_${T}_s${SD}.log 2>&1; say "merge $T s$SD rc=$? $(tail -1 /workspace/f8_v4/logs/merge_${T}_s${SD}.log | cut -c1-80)"
done
say "CHAIN_V4_GPU2_DONE"
