#!/bin/bash
# chain_v4_gpu3.sh — AMENDMENT 5 rerun of all four F10 chains with legs v4b (in-service legs policy). MWF_ROOT=mwf_v4b (fresh dirs; the mwf/ runs with the bad legs are kept as invalid receipts).
R=/workspace/review_scratch; PY=/workspace/venv/bin/python; L=$R/v4_commands.txt; cd $R || exit 2; export MWF_ROOT=mwf_v4b
say(){ echo "[$(date -u +%FT%TZ)] $*" >> $L; }
SH0=202501,202505,202509,202601,202605; SH1=202502,202506,202510,202602,202606; SH2=202503,202507,202511,202603,202607; SH3=202504,202508,202512,202604,202608
for TS in "RAW 42" "RAW 2027" "CLIP 42" "CLIP 2027"; do set -- $TS; T=$1; SD=$2
  say "F10 chain $T s$SD start (gpu3, legs v4b)"; bash launch_mwf_v4b.sh $T $SD 0 $SH0 & bash launch_mwf_v4b.sh $T $SD 1 $SH1 & bash launch_mwf_v4b.sh $T $SD 2 $SH2 & bash launch_mwf_v4b.sh $T $SD 3 $SH3 & wait
  say "F10 chain $T s$SD shards ended: $(grep -a -c "^END\[$T s$SD shard.*rc=0" /workspace/f8_v4/logs/commands.txt)/4 rc=0 (cumulative incl. bad-legs runs)"
  $PY merge_mwf_v4b.py $T $SD > /workspace/f8_v4/logs/merge_v4b_${T}_s${SD}.log 2>&1; say "merge v4b $T s$SD rc=$? $(tail -1 /workspace/f8_v4/logs/merge_v4b_${T}_s${SD}.log | cut -c1-80)"
done
say "CHAIN_V4_GPU3_DONE"
