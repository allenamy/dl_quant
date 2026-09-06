#!/bin/bash
# chain_vc.sh — PREREG_tail_aware_sizing arms after the identity receipts hold: 8 runs (γ 0.5/1.0 × seeds 42/2027 × prod/log), 3 in parallel × OMP 4 = 12 threads,
# then judge_volcap.py. Every command verbatim in logs/commands.txt (via run_arm_vc.sh) and this chain's stages in logs/chain.log.
set -u
ROOT=/workspace/review_scratch/tail_aware_sizing; PY=/workspace/venv/bin/python
cd $ROOT
echo "VC_CHAIN_START $(date -u +%FT%TZ)" >> logs/chain.log
n=0
for cal in prod log; do for g in 0.5 1.0; do for s in 42 2027; do
  bash run_arm_vc.sh VC_${cal}_g${g}_s${s} $cal $g $s > logs/VC_${cal}_g${g}_s${s}.out 2>&1 &
  n=$((n+1)); if [ $((n % 3)) -eq 0 ]; then wait; fi
done; done; done
wait
for f in logs/VC_*_g0.5_*.out logs/VC_*_g1.0_*.out; do grep -q "^DONE" $f || { echo "VC_HALT $f" >> logs/chain.log; exit 2; }; done
echo "CMD[judge] $(date -u +%FT%TZ): judge_volcap.py $ROOT results/judge_volcap.json" >> logs/commands.txt
$PY judge_volcap.py $ROOT results/judge_volcap.json > logs/judge.log 2>&1 || { echo "VC_HALT judge" >> logs/chain.log; exit 2; }
sha256sum results/*.json dev/probe_artifacts/w10_ablation_series_VC_*.npz dev_alt/probe_artifacts/w10_ablation_series_VC_*.npz w10_volcap.py w10_health_orig.py device.diff > results/SHA256SUMS_pod.txt
echo "VC_CHAIN_DONE $(date -u +%FT%TZ)" >> logs/chain.log
