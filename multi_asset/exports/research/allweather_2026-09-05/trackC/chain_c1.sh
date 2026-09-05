#!/bin/bash
# chain_c1.sh — Track C C1: (i) identity receipt AGEW=0 on the health_check main-arm configuration (M1 · U-PIT · prod/log · s42/s2027 · live fee tiers) vs the archived health_check artifacts;
# (ii) dose arms AGEW ∈ {0.5, 1.0, 2.0} × seeds {42, 2027} × calibers {prod (primary), log (secondary)}; (iii) sha receipts. Verbatim env from health_check/chain_m1.sh (M1_UPIT_*_ccal arms).
cd /workspace/review_scratch/allweather_trackC
HC=/workspace/review_scratch/health_check
COMMON="LEGS=101 CAL=log SLOW_NPY=/workspace/shadow_bundle_v3/slow_pred_pinned.npy WRULE=msharpe LOOK=900 MEMBERS_TOPN=829 FTRIM=zero PHI=0.45"
UP=$HC/masks/umask_UPIT.npz; CB=$HC/calib/costb_fee_steady.json
sha256sum w10_agew.py w10_health_orig.py $UP $CB >> logs/chain_c1.log
for cal in log prod; do for s in 42 2027; do
  bash run_arm.sh A0_${cal}_s${s} $cal w10_agew.py $COMMON FSEED=$s UMASK_SCOPE=m1 UMASK_NPZ=$UP COSTB_JSON=$CB AGEW=0 > logs/A0_${cal}_s${s}.out 2>&1 &
done; done
wait
: > logs/check_equiv.log
for s in 42 2027; do
  /workspace/venv/bin/python check_equiv_c.py dev/probe_artifacts/w10_ablation_series_A0_log_s${s}.npz $HC/dev/probe_artifacts/w10_ablation_series_M1_UPIT_log_s${s}_ccal.npz "AGEW=0 log s$s vs health_check M1_UPIT_log_s${s}_ccal" >> logs/check_equiv.log 2>&1 || echo "EQUIV_FAIL log s$s" >> logs/chain_c1.log
  /workspace/venv/bin/python check_equiv_c.py dev_alt/probe_artifacts/w10_ablation_series_A0_prod_s${s}.npz $HC/dev_alt/probe_artifacts/w10_ablation_series_M1_UPIT_prod_s${s}_ccal.npz "AGEW=0 prod s$s vs health_check M1_UPIT_prod_s${s}_ccal" >> logs/check_equiv.log 2>&1 || echo "EQUIV_FAIL prod s$s" >> logs/chain_c1.log
done
grep -c "^PASS" logs/check_equiv.log | xargs -I{} echo "IDENTITY_PASS_COUNT {} / 4 $(date -u +%FT%TZ)" >> logs/chain_c1.log
grep -q EQUIV_FAIL logs/chain_c1.log && { echo "ABORT: identity failed $(date -u +%FT%TZ)" >> logs/chain_c1.log; exit 1; }
for cal in prod log; do for s in 42 2027; do for a in 0.5 1.0 2.0; do
  t=$(echo $a | tr -d .)
  bash run_arm.sh A${t}_${cal}_s${s} $cal w10_agew.py $COMMON FSEED=$s UMASK_SCOPE=m1 UMASK_NPZ=$UP COSTB_JSON=$CB AGEW=$a > logs/A${t}_${cal}_s${s}.out 2>&1 &
done; done; wait; done
sha256sum dev/probe_artifacts/w10_ablation_series_A*.npz dev_alt/probe_artifacts/w10_ablation_series_A*.npz >> logs/chain_c1.log
echo "CHAIN_C1_DONE $(date -u +%FT%TZ)" >> logs/chain_c1.log
