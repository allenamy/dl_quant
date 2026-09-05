#!/bin/bash
# chain_identity.sh — carry_layers identity receipt: all layers off × {prod, log} × {42, 2027} vs the archived health_check M1_UPIT_{cal}_s{seed}_ccal artifacts (env verbatim from health_check/chain_m1.sh).
cd /workspace/review_scratch/allweather_trackC/carry_layers; HC=/workspace/review_scratch/health_check
COMMON="LEGS=101 CAL=log SLOW_NPY=/workspace/shadow_bundle_v3/slow_pred_pinned.npy WRULE=msharpe LOOK=900 MEMBERS_TOPN=829 FTRIM=zero PHI=0.45"
UP=$HC/masks/umask_UPIT.npz; CB=$HC/calib/costb_fee_steady.json
sha256sum w10_carry.py w10_health_orig.py $UP $CB >> logs/chain_identity.log
for cal in log prod; do for s in 42 2027; do
  bash run_arm.sh B0_${cal}_s${s} $cal w10_carry.py $COMMON FSEED=$s UMASK_SCOPE=m1 UMASK_NPZ=$UP COSTB_JSON=$CB > logs/B0_${cal}_s${s}.out 2>&1 &
done; done; wait
: > logs/check_equiv.log
for s in 42 2027; do
  /workspace/venv/bin/python check_equiv_cl.py dev/probe_artifacts/w10_ablation_series_B0_log_s${s}.npz $HC/dev/probe_artifacts/w10_ablation_series_M1_UPIT_log_s${s}_ccal.npz "layers off log s$s vs health_check M1_UPIT_log_s${s}_ccal" >> logs/check_equiv.log 2>&1 || echo "EQUIV_FAIL log s$s" >> logs/chain_identity.log
  /workspace/venv/bin/python check_equiv_cl.py dev_alt/probe_artifacts/w10_ablation_series_B0_prod_s${s}.npz $HC/dev_alt/probe_artifacts/w10_ablation_series_M1_UPIT_prod_s${s}_ccal.npz "layers off prod s$s vs health_check M1_UPIT_prod_s${s}_ccal" >> logs/check_equiv.log 2>&1 || echo "EQUIV_FAIL prod s$s" >> logs/chain_identity.log
done
echo "IDENTITY_PASS_COUNT $(grep -c '^PASS' logs/check_equiv.log) / 4 $(date -u +%FT%TZ)" >> logs/chain_identity.log
sha256sum dev/probe_artifacts/w10_ablation_series_B0_*.npz dev_alt/probe_artifacts/w10_ablation_series_B0_*.npz >> logs/chain_identity.log
echo "CHAIN_IDENTITY_DONE $(date -u +%FT%TZ)" >> logs/chain_identity.log
