#!/bin/bash
# rider_chain.sh — rider arm remainder (a1_chain.sh halted at rider_inputs on the 138 pre-panel META anchors; fixed rider_spotsup.py skips them):
# rider inputs (spot-support matrix + interaction table) -> device runs b in {0.5, 1.0} x seeds {42, 2027} (identity b=0 archived) -> paired Δ (RULE=rider). Logged.
set -u
ROOT=/workspace/review_scratch/allweather_trackA; PY=/workspace/venv/bin/python; RL="bash $ROOT/scripts/run_logged.sh"
cd $ROOT
echo "RIDER_CHAIN_START $(date -u +%FT%TZ)" >> logs/chain.log
$RL rider_inputs A1_NPZ=$ROOT/features/a1_feat_shift0.npz OUT_NPZ=$ROOT/rider/spotsup_qvr24h.npz OUT_JSON=$ROOT/results/rider_interaction.json $PY scripts/rider_spotsup.py || { echo "RIDER_HALT rider_inputs" >> logs/chain.log; exit 2; }
for s in 42 2027; do for b in 0.5 1.0; do
  bash scripts/run_rider.sh R_b${b}_s${s} $s $b $ROOT/rider/spotsup_qvr24h.npz > logs/rider_R_b${b}_s${s}.out 2>&1 &
done; done
wait
for s in 42 2027; do for b in 0.5 1.0; do
  echo "CMD[rider_paired_b${b}_s${s}] $(date -u +%FT%TZ): RULE=rider s2_paired_delta.py ID_b0_s${s} R_b${b}_s${s}" >> logs/commands.txt
  RULE=rider $PY scripts/s2_paired_delta.py rider/dev_alt/probe_artifacts/w10_ablation_series_ID_b0_s${s}.npz rider/dev_alt/probe_artifacts/w10_ablation_series_R_b${b}_s${s}.npz results/rider_paired_b${b}_s${s}.json > logs/rider_paired_b${b}_s${s}.log 2>&1
done; done
sha256sum results/rider_*.json rider/spotsup_qvr24h.npz rider/dev_alt/probe_artifacts/*.npz >> logs/SHA256SUMS_RIDER.txt
echo "RIDER_CHAIN_DONE $(date -u +%FT%TZ)" >> logs/chain.log
