#!/bin/bash
# a2_chain.sh — family A2 (premium index): parse -> features at right-edge shifts -2..+3 -> guards -> S1 gate (BASE + A2). Every command logged.
set -u
ROOT=/workspace/review_scratch/allweather_trackA; PY=/workspace/venv/bin/python; RL="bash $ROOT/scripts/run_logged.sh"
cd $ROOT
echo "A2_CHAIN_START $(date -u +%FT%TZ)" >> logs/chain.log
if grep -q "^PARSE_DONE" logs/a2_parse.log 2>/dev/null && [ -s features/premidx_5m.npy ]; then
  echo "A2 parse already done (QUOTA MODE: source zips deleted after parse; never re-run parse)" >> logs/chain.log
else
  $RL a2_parse STAGE=parse NPROC=16 $PY scripts/build_a2_premidx.py || { echo "A2_HALT parse" >> logs/chain.log; exit 2; }
  grep -q "^PARSE_DONE" logs/a2_parse.log || { echo "A2_HALT parse-nodone" >> logs/chain.log; exit 2; }
fi
FILES=""
for j in -2 -1 0 1 2 3; do
  $RL a2_fea_j$j STAGE=features SHIFT=$j OUT=$ROOT/features/a2_feat_shift$j.npz $PY scripts/build_a2_premidx.py || { echo "A2_HALT fea $j" >> logs/chain.log; exit 2; }
  FILES="$FILES,$j=$ROOT/features/a2_feat_shift$j.npz"
done
$RL a2_guards FILES="${FILES#,}" TAG=A2 OUT_JSON=$ROOT/results/guards_A2.json $PY scripts/guards_trackA.py || { echo "A2_HALT guards" >> logs/chain.log; exit 2; }
$RL s1_A2 FEA_IN=/workspace/data/wide_fea_v2ext.npy META_IN=/workspace/data/wide_fea_v2ext_meta.npz NEWF=$ROOT/features/a2_feat_shift0.npz ARMS="BASE:;A2:0" SEEDS=42,2027 OUT_JSON=$ROOT/results/s1_A2.json PRED_DIR=$ROOT/results/preds NJOBS=24 $PY scripts/trackA_gate_s1.py || { echo "A2_HALT s1" >> logs/chain.log; exit 2; }
sha256sum features/premidx_5m.npy features/a2_feat_shift*.npz results/guards_A2.json results/s1_A2.json >> logs/SHA256SUMS_A2.txt
echo "A2_CHAIN_DONE $(date -u +%FT%TZ)" >> logs/chain.log
