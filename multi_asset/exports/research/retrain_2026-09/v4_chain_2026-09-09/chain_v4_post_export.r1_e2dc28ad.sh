#!/bin/bash
# chain_v4_post_export.sh — PREREG_v4 §2.4–2.5 queue: dev_v4 tree -> legs v4 -> (wait STEP1_PASS marker) -> 4 F10 chains x 4 shards (sequential chains) -> merge.
R=/workspace/review_scratch; PY=/workspace/venv/bin/python; L=$R/v4_commands.txt; cd $R || exit 2
say(){ echo "[$(date -u +%FT%TZ)] $*" >> $L; }
grep -q BUNDLE_DONE $R/export_v4.log || { say "post_export: export not done"; exit 3; }
say "post_export: build_dev_v4"; $PY build_dev_v4.py > build_dev_v4.log 2>&1 || { say FAIL_build_dev_v4; exit 1; }
say "post_export: legs v4"; env LEGS_TG=/workspace/dlw_v4raw/data/dlw_targets.npz LEGS_META=/workspace/data/wide_fea_v4_meta.npz LEGS_PRED=/workspace/shadow_bundle_v4/slow_pred_pinned.npy LEGS_OUT=/workspace/f8_v4/data/f10v2_legs.npz $PY pod_legs_v4.py > legs_v4.log 2>&1 || { say FAIL_legs_v4; exit 1; }
grep -q LEGS_V4_DONE legs_v4.log || { say FAIL_legs_v4_marker; exit 1; }
while [ ! -f /workspace/f8_v4/gates/STEP1_PASS ]; do sleep 60; done; say "post_export: STEP1_PASS marker seen, launching F10 chains"
SH0=202501,202505,202509,202601,202605; SH1=202502,202506,202510,202602,202606; SH2=202503,202507,202511,202603,202607; SH3=202504,202508,202512,202604,202608
for TS in "RAW 42" "RAW 2027" "CLIP 42" "CLIP 2027"; do set -- $TS; T=$1; SD=$2
  say "F10 chain $T s$SD start"; bash launch_mwf_v4.sh $T $SD 0 $SH0 & bash launch_mwf_v4.sh $T $SD 1 $SH1 & bash launch_mwf_v4.sh $T $SD 2 $SH2 & bash launch_mwf_v4.sh $T $SD 3 $SH3 & wait
  say "F10 chain $T s$SD shards ended: $(grep -a -c "^END\[$T s$SD shard.*rc=0" /workspace/f8_v4/logs/commands.txt)/4 rc=0"
  $PY merge_mwf_v4.py $T $SD > /workspace/f8_v4/logs/merge_${T}_s${SD}.log 2>&1; say "merge $T s$SD rc=$? $(tail -1 /workspace/f8_v4/logs/merge_${T}_s${SD}.log | cut -c1-80)"
done
say "CHAIN_V4_POST_EXPORT_DONE"
