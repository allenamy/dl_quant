#!/bin/bash
# chain_t3c.sh — t3c_revalidation: (i) identity: knobs off × {prod, log} × {42, 2027} vs health_check M1_UPIT_{cal}_s{seed}_ccal; (ii) arms T3c (KMOD_F10=0.5) / T3 (KMOD=0.5 KMOD_L=0.5) / T3b (KMOD_AGREE=0.5) / T2 (KTAIL=1) × {prod, log} × {42, 2027}; (iii) V4 fixed seat 0.21 (W3FIX) base + T3c × {42, 2027} prod. Env verbatim from health_check/chain_m1.sh (M1_UPIT_*_ccal).
cd /workspace/review_scratch/allweather_trackC/t3c; HC=/workspace/review_scratch/health_check
COMMON="LEGS=101 CAL=log SLOW_NPY=/workspace/shadow_bundle_v3/slow_pred_pinned.npy WRULE=msharpe LOOK=900 MEMBERS_TOPN=829 FTRIM=zero PHI=0.45 UMASK_SCOPE=m1"
UP=$HC/masks/umask_UPIT.npz; CB=$HC/calib/costb_fee_steady.json
sha256sum w10_health.py $UP $CB >> logs/chain_t3c.log
for cal in log prod; do for s in 42 2027; do bash run_arm.sh B0_${cal}_s${s} $cal w10_health.py $COMMON FSEED=$s UMASK_NPZ=$UP COSTB_JSON=$CB > logs/B0_${cal}_s${s}.out 2>&1 & done; done; wait
: > logs/check_equiv.log
for s in 42 2027; do
  /workspace/venv/bin/python check_equiv_t3c.py dev/probe_artifacts/w10_ablation_series_B0_log_s${s}.npz $HC/dev/probe_artifacts/w10_ablation_series_M1_UPIT_log_s${s}_ccal.npz "knobs off log s$s vs health_check M1_UPIT_log_s${s}_ccal" >> logs/check_equiv.log 2>&1 || echo "EQUIV_FAIL log s$s" >> logs/chain_t3c.log
  /workspace/venv/bin/python check_equiv_t3c.py dev_alt/probe_artifacts/w10_ablation_series_B0_prod_s${s}.npz $HC/dev_alt/probe_artifacts/w10_ablation_series_M1_UPIT_prod_s${s}_ccal.npz "knobs off prod s$s vs health_check M1_UPIT_prod_s${s}_ccal" >> logs/check_equiv.log 2>&1 || echo "EQUIV_FAIL prod s$s" >> logs/chain_t3c.log
done
echo "IDENTITY_PASS_COUNT $(grep -c '^PASS' logs/check_equiv.log) / 4 $(date -u +%FT%TZ)" >> logs/chain_t3c.log
grep -q EQUIV_FAIL logs/chain_t3c.log && { echo "ABORT identity failed" >> logs/chain_t3c.log; exit 1; }
for cal in prod log; do for s in 42 2027; do
  bash run_arm.sh T3c_${cal}_s${s} $cal w10_health.py $COMMON FSEED=$s UMASK_NPZ=$UP COSTB_JSON=$CB KMOD_F10=0.5 > logs/T3c_${cal}_s${s}.out 2>&1 &
  bash run_arm.sh T3_${cal}_s${s} $cal w10_health.py $COMMON FSEED=$s UMASK_NPZ=$UP COSTB_JSON=$CB KMOD=0.5 KMOD_L=0.5 > logs/T3_${cal}_s${s}.out 2>&1 &
  bash run_arm.sh T3b_${cal}_s${s} $cal w10_health.py $COMMON FSEED=$s UMASK_NPZ=$UP COSTB_JSON=$CB KMOD_AGREE=0.5 > logs/T3b_${cal}_s${s}.out 2>&1 &
  bash run_arm.sh T2_${cal}_s${s} $cal w10_health.py $COMMON FSEED=$s UMASK_NPZ=$UP COSTB_JSON=$CB KTAIL=1 > logs/T2_${cal}_s${s}.out 2>&1 &
done; wait; done
for s in 42 2027; do
  bash run_arm.sh V4B0_prod_s${s} prod w10_health.py $COMMON FSEED=$s UMASK_NPZ=$UP COSTB_JSON=$CB W3FIX=0.21,0,0.79 > logs/V4B0_prod_s${s}.out 2>&1 &
  bash run_arm.sh V4T3c_prod_s${s} prod w10_health.py $COMMON FSEED=$s UMASK_NPZ=$UP COSTB_JSON=$CB W3FIX=0.21,0,0.79 KMOD_F10=0.5 > logs/V4T3c_prod_s${s}.out 2>&1 &
done; wait
grep -l -E "Traceback|AssertionError" dev/logs/*.log dev_alt/logs/*.log >> logs/chain_t3c.log 2>/dev/null
sha256sum dev/probe_artifacts/w10_ablation_series_*.npz dev_alt/probe_artifacts/w10_ablation_series_*.npz >> logs/chain_t3c.log
echo "CHAIN_T3C_DONE $(date -u +%FT%TZ)" >> logs/chain_t3c.log
