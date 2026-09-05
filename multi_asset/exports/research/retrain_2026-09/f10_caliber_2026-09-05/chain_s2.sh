#!/bin/bash
# chain_s2.sh — PREREG_f10_caliber_sensitivity_2026-09-05 §2: primary health_check arm (U-PIT, UMASK_SCOPE=m1, LEGS=101, LOOK=900, msharpe, FTRIM=zero,
# fee-only COSTB_JSON, seeds 42/2027) at PHI=0 and PHI=0.45 under three layouts (log = label i, prod = label iii, sum1 = label ii) = 12 runs;
# then bitwise equivalence of the four PHI=0.45 log/prod runs vs health_check M1_UPIT_{log,prod}_s{seed}_ccal; then the judge.
cd /workspace/review_scratch/f10_caliber
echo "CMD[chain_s2] $(date -u +%FT%TZ): bash chain_s2.sh" >> logs/commands.txt
[ -f meta/meta_newsum_f10cal.npz ] || { echo "missing meta/meta_newsum_f10cal.npz (run s0_build_labels.py first)"; exit 1; }
COMMON="LEGS=101 CAL=log SLOW_NPY=/workspace/shadow_bundle_v3/slow_pred_pinned.npy WRULE=msharpe LOOK=900 MEMBERS_TOPN=829 FTRIM=zero"
UP=/workspace/review_scratch/f10_caliber/masks/umask_UPIT.npz; CB=/workspace/review_scratch/f10_caliber/calib/costb_fee_steady.json
for cal in log prod sum1; do for s in 42 2027; do
  bash run_arm.sh ${cal}_phi0_s${s} $cal w10_health.py $COMMON PHI=0 FSEED=$s UMASK_SCOPE=m1 UMASK_NPZ=$UP COSTB_JSON=$CB > logs/${cal}_phi0_s${s}.out 2>&1 &
  bash run_arm.sh ${cal}_phi045_s${s} $cal w10_health.py $COMMON PHI=0.45 FSEED=$s UMASK_SCOPE=m1 UMASK_NPZ=$UP COSTB_JSON=$CB > logs/${cal}_phi045_s${s}.out 2>&1 &
done; done
wait
echo "RUNS_DONE $(date -u +%FT%TZ)" >> logs/chain_s2.log
grep -H "END\[" logs/commands.txt | tail -12 >> logs/chain_s2.log
HC=/workspace/review_scratch/health_check
for s in 42 2027; do
  /workspace/venv/bin/python check_equiv.py dev/probe_artifacts/w10_ablation_series_log_phi045_s${s}.npz $HC/dev/probe_artifacts/w10_ablation_series_M1_UPIT_log_s${s}_ccal.npz "log PHI=0.45 s$s vs HC M1_UPIT_log_s${s}_ccal" >> logs/check_equiv.log 2>&1 || echo "EQUIV_FAIL log s$s" >> logs/chain_s2.log
  /workspace/venv/bin/python check_equiv.py dev_alt/probe_artifacts/w10_ablation_series_prod_phi045_s${s}.npz $HC/dev_alt/probe_artifacts/w10_ablation_series_M1_UPIT_prod_s${s}_ccal.npz "prod PHI=0.45 s$s vs HC M1_UPIT_prod_s${s}_ccal" >> logs/check_equiv.log 2>&1 || echo "EQUIV_FAIL prod s$s" >> logs/chain_s2.log
done
echo "EQUIV_DONE $(date -u +%FT%TZ)" >> logs/chain_s2.log
sha256sum w10_health.py masks/umask_UPIT.npz calib/costb_fee_steady.json meta/meta_newsum_f10cal.npz dev/probe_artifacts/w10_ablation_series_*.npz dev_alt/probe_artifacts/w10_ablation_series_*.npz dev_alt2/probe_artifacts/w10_ablation_series_*.npz >> logs/chain_s2.log
echo "CMD[judge_s2] $(date -u +%FT%TZ): /workspace/venv/bin/python judge_s2.py" >> logs/commands.txt
/workspace/venv/bin/python judge_s2.py > logs/judge_s2.log 2>&1; echo "JUDGE rc=$? $(date -u +%FT%TZ)" >> logs/chain_s2.log
echo "CHAIN_S2_DONE $(date -u +%FT%TZ)" >> logs/chain_s2.log
