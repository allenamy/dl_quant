#!/bin/bash
# chain_arms.sh — carry_layers arms (PREREG_carry_layers_2026-09-05 §1): D 3 THR × 2 rules, H 2, L 2, combo 1 = 11 cells × seeds {42, 2027}, prod caliber, health_check main-arm form (env verbatim from health_check/chain_m1.sh M1_UPIT_*_ccal).
# Waits for the identity chain; aborts if any identity cell failed. DODGE_COST=7.84 at run time (15.8 re-priced by the judge from the saved Σ|w| via the cost column).
cd /workspace/review_scratch/allweather_trackC/carry_layers; HC=/workspace/review_scratch/health_check
while ! grep -q CHAIN_IDENTITY_DONE logs/chain_identity.log 2>/dev/null; do sleep 5; done
grep -q EQUIV_FAIL logs/chain_identity.log && { echo "ABORT identity failed $(date -u +%FT%TZ)" >> logs/chain_arms.log; exit 1; }
COMMON="LEGS=101 CAL=log SLOW_NPY=/workspace/shadow_bundle_v3/slow_pred_pinned.npy WRULE=msharpe LOOK=900 MEMBERS_TOPN=829 FTRIM=zero PHI=0.45 UMASK_SCOPE=m1"
UP=$HC/masks/umask_UPIT.npz; CB=$HC/calib/costb_fee_steady.json; ST=/workspace/review_scratch/allweather_trackC/carry_layers/data/sett_tables.npz
sha256sum w10_carry.py $ST $UP $CB >> logs/chain_arms.log
# batch 1: D prev (6) + H (4) ; batch 2: D oracle (6) + L (4) + combo (2)
for s in 42 2027; do
  for t in 6 10 15; do bash run_arm.sh D${t}_prev_prod_s${s} prod w10_carry.py $COMMON FSEED=$s UMASK_NPZ=$UP COSTB_JSON=$CB DODGE_THR=$t DODGE_RULE=prev DODGE_COST=7.84 SETT_NPZ=$ST > logs/D${t}_prev_prod_s${s}.out 2>&1 & done
  for k in 0.5 1.0; do kk=$(echo $k | tr -d .); bash run_arm.sh H${kk}_prod_s${s} prod w10_carry.py $COMMON FSEED=$s UMASK_NPZ=$UP COSTB_JSON=$CB HOUR_K=$k > logs/H${kk}_prod_s${s}.out 2>&1 & done
done; wait
for s in 42 2027; do
  for t in 6 10 15; do bash run_arm.sh D${t}_oracle_prod_s${s} prod w10_carry.py $COMMON FSEED=$s UMASK_NPZ=$UP COSTB_JSON=$CB DODGE_THR=$t DODGE_RULE=oracle DODGE_COST=7.84 SETT_NPZ=$ST > logs/D${t}_oracle_prod_s${s}.out 2>&1 & done
  for h in 10 20; do bash run_arm.sh L${h}_prod_s${s} prod w10_carry.py $COMMON FSEED=$s UMASK_NPZ=$UP COSTB_JSON=$CB LONG_HI=$h > logs/L${h}_prod_s${s}.out 2>&1 & done
  bash run_arm.sh X_prod_s${s} prod w10_carry.py $COMMON FSEED=$s UMASK_NPZ=$UP COSTB_JSON=$CB DODGE_THR=10 DODGE_RULE=prev DODGE_COST=7.84 SETT_NPZ=$ST HOUR_K=1.0 LONG_HI=10 > logs/X_prod_s${s}.out 2>&1 &
done; wait
grep -l -E "Traceback|AssertionError" dev_alt/logs/*.log >> logs/chain_arms.log 2>/dev/null
sha256sum dev_alt/probe_artifacts/w10_ablation_series_*.npz >> logs/chain_arms.log
echo "CHAIN_ARMS_DONE $(date -u +%FT%TZ)" >> logs/chain_arms.log
