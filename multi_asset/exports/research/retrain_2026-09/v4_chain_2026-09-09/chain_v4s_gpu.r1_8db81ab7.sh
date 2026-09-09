#!/bin/bash
# chain_v4s_gpu.sh — PREREG_fea89_stable_trend G3: RAW x {42,2027} on f8_v4s (stable trend fea89), legs v4b, FIX7 20 folds; then merge.
R=/workspace/review_scratch; PY=/workspace/venv/bin/python; L=$R/v4_commands.txt; cd $R || exit 2; export MWF_ROOT=mwf_v4s
say(){ echo "[$(date -u +%FT%TZ)] $*" >> $L; }
SH0=202501,202505,202509,202601,202605; SH1=202502,202506,202510,202602,202606; SH2=202503,202507,202511,202603,202607; SH3=202504,202508,202512,202604,202608
for TS in "RAW 42" "RAW 2027"; do set -- $TS; T=$1; SD=$2
  say "F10 chain $T s$SD start (v4s: stable trend fea89, legs v4b)"; bash launch_mwf_v4s.sh $T $SD 0 $SH0 & bash launch_mwf_v4s.sh $T $SD 1 $SH1 & bash launch_mwf_v4s.sh $T $SD 2 $SH2 & bash launch_mwf_v4s.sh $T $SD 3 $SH3 & wait
  say "F10 chain $T s$SD shards ended: $(grep -a -c "^END\[$T s$SD shard.*rc=0" /workspace/f8_v4s/logs/commands.txt)/4 rc=0 (cumulative incl. bad-legs runs)"
  $PY merge_mwf_v4s.py $T $SD > /workspace/f8_v4s/logs/merge_v4b_${T}_s${SD}.log 2>&1; say "merge v4s $T s$SD rc=$? $(tail -1 /workspace/f8_v4s/logs/merge_v4b_${T}_s${SD}.log | cut -c1-80)"
done
say "CHAIN_V4S_GPU_DONE"
