#!/bin/bash
# a1_chain.sh — family A1 (spot vs perp): parse -> features at shifts -2..+3 -> guards -> S1 gate (BASE, A1, A2, A1A2) -> rider inputs
# (spot-support matrix + interaction table) -> rider device runs b in {0.5, 1.0} x seeds {42, 2027} (identity b=0 runs already archived) -> paired Δ. Every command logged.
set -u
ROOT=/workspace/review_scratch/allweather_trackA; PY=/workspace/venv/bin/python; RL="bash $ROOT/scripts/run_logged.sh"
cd $ROOT
echo "A1_CHAIN_START $(date -u +%FT%TZ)" >> logs/chain.log
# source arrays come from stream_a1.py (QUOTA MODE stream-parse-and-delete); require its DL_DONE receipt
grep -q "^DL_DONE" logs/stream_a1.log || { echo "A1_HALT stream_a1 not done" >> logs/chain.log; exit 2; }
FILES=""
for j in -2 -1 0 1 2 3; do
  $RL a1_fea_j$j STAGE=features SHIFT=$j OUT=$ROOT/features/a1_feat_shift$j.npz $PY scripts/build_a1_spot.py || { echo "A1_HALT fea $j" >> logs/chain.log; exit 2; }
  FILES="$FILES,$j=$ROOT/features/a1_feat_shift$j.npz"
done
$RL a1_guards FILES="${FILES#,}" TAG=A1 OUT_JSON=$ROOT/results/guards_A1.json $PY scripts/guards_trackA.py || { echo "A1_HALT guards" >> logs/chain.log; exit 2; }
$RL s1_ALL FEA_IN=/workspace/data/wide_fea_v2ext.npy META_IN=/workspace/data/wide_fea_v2ext_meta.npz NEWF=$ROOT/features/a1_feat_shift0.npz,$ROOT/features/a2_feat_shift0.npz ARMS="BASE:;A1:0;A2:1;A1A2:0,1" SEEDS=42,2027 OUT_JSON=$ROOT/results/s1_ALL.json PRED_DIR=$ROOT/results/preds NJOBS=24 $PY scripts/trackA_gate_s1.py || { echo "A1_HALT s1" >> logs/chain.log; exit 2; }
# rider (runs regardless of S1; the frozen precondition = A1 passes the two guards, checked in the RESULT, not here)
$RL rider_inputs A1_NPZ=$ROOT/features/a1_feat_shift0.npz OUT_NPZ=$ROOT/rider/spotsup_qvr24h.npz OUT_JSON=$ROOT/results/rider_interaction.json $PY scripts/rider_spotsup.py || { echo "A1_HALT rider_inputs" >> logs/chain.log; exit 2; }
for s in 42 2027; do for b in 0.5 1.0; do
  bash scripts/run_rider.sh R_b${b}_s${s} $s $b $ROOT/rider/spotsup_qvr24h.npz > logs/rider_R_b${b}_s${s}.out 2>&1 &
done; done
wait
for s in 42 2027; do for b in 0.5 1.0; do
  echo "CMD[rider_paired_b${b}_s${s}] $(date -u +%FT%TZ): RULE=rider s2_paired_delta.py ID_b0_s${s} R_b${b}_s${s}" >> logs/commands.txt
  RULE=rider $PY scripts/s2_paired_delta.py rider/dev_alt/probe_artifacts/w10_ablation_series_ID_b0_s${s}.npz rider/dev_alt/probe_artifacts/w10_ablation_series_R_b${b}_s${s}.npz results/rider_paired_b${b}_s${s}.json > logs/rider_paired_b${b}_s${s}.log 2>&1
done; done
sha256sum features/a1_*.npy features/a1_feat_shift*.npz results/guards_A1.json results/s1_ALL.json results/rider_*.json rider/spotsup_qvr24h.npz rider/dev_alt/probe_artifacts/*.npz >> logs/SHA256SUMS_A1.txt
echo "A1_CHAIN_DONE $(date -u +%FT%TZ)" >> logs/chain.log
