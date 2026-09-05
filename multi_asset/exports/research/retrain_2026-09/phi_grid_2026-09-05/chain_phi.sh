#!/bin/bash
# chain_phi.sh — PREREG_dl_monthly_gate_and_phi_grid_2026-09-05 §B: 8 new device runs (φ ∈ {0.25, 0.35, 0.55, 0.65} × seeds {42, 2027}) on the phi_grid
# dev_alt layout (label (iii)), everything else = health_check main arm (U-PIT, UMASK_SCOPE=m1, LEGS=101, LOOK=900, msharpe, FTRIM=zero, fee-only COSTB_JSON).
# φ = 0.45 and φ = 0 are NOT rerun: the judge loads the f10_caliber prod artifacts and asserts their sha256 against the archived MANIFEST values.
ROOT=/workspace/review_scratch/phi_grid; cd $ROOT
echo "CMD[chain_phi] $(date -u +%FT%TZ): bash chain_phi.sh" >> logs/commands.txt
COMMON="LEGS=101 CAL=log SLOW_NPY=/workspace/shadow_bundle_v3/slow_pred_pinned.npy WRULE=msharpe LOOK=900 MEMBERS_TOPN=829 FTRIM=zero"
UP=$ROOT/masks/umask_UPIT.npz; CB=$ROOT/calib/costb_fee_steady.json
for phi in 0.25 0.35 0.55 0.65; do tag=phi$(echo $phi | tr -d '.'); for s in 42 2027; do
  bash run_arm.sh prod_${tag}_s${s} prod w10_health.py $COMMON PHI=$phi FSEED=$s UMASK_SCOPE=m1 UMASK_NPZ=$UP COSTB_JSON=$CB > logs/prod_${tag}_s${s}.out 2>&1 &
done; done
wait
echo "RUNS_DONE $(date -u +%FT%TZ)" >> logs/chain_phi.log
grep -H "END\[" logs/commands.txt | tail -8 >> logs/chain_phi.log
sha256sum w10_health.py masks/umask_UPIT.npz calib/costb_fee_steady.json dev_alt/probe_artifacts/w10_ablation_series_*.npz >> logs/chain_phi.log
echo "CMD[judge_phi] $(date -u +%FT%TZ): /workspace/venv/bin/python judge_phi.py" >> logs/commands.txt
/workspace/venv/bin/python judge_phi.py > logs/judge_phi.log 2>&1; echo "JUDGE rc=$? $(date -u +%FT%TZ)" >> logs/chain_phi.log
echo "CHAIN_PHI_DONE $(date -u +%FT%TZ)" >> logs/chain_phi.log
