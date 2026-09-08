#!/bin/bash
# chain_ucrypto.sh — 2026-09-08 ADDENDUM 5: the six cited chain_m1 arms with UMASK_NPZ swapped to umask_UPIT_CRYPTO.npz. One key changed, nothing else.
cd /workspace/review_scratch/health_check
COMMON="LEGS=101 CAL=log SLOW_NPY=/workspace/shadow_bundle_v3/slow_pred_pinned.npy WRULE=msharpe LOOK=900 MEMBERS_TOPN=829 FTRIM=zero PHI=0.45"
UC=/workspace/review_scratch/health_check/masks/umask_UPIT_CRYPTO.npz
CB=/workspace/review_scratch/health_check/calib/costb_fee_steady.json
sha256sum w10_health.py $UC $CB >> logs/chain_ucrypto.log
for s in 42 2027; do
  bash run_arm.sh M1_UCRYPTO_prod_s${s}_ccal  prod w10_health.py $COMMON FSEED=$s UMASK_SCOPE=m1      UMASK_NPZ=$UC COSTB_JSON=$CB                    > logs/M1_UCRYPTO_prod_s${s}_ccal.out 2>&1 &
  bash run_arm.sh MEM_UCRYPTO_prod_s${s}_ccal prod w10_health.py $COMMON FSEED=$s UMASK_SCOPE=members UMASK_NPZ=$UC COSTB_JSON=$CB                    > logs/MEM_UCRYPTO_prod_s${s}_ccal.out 2>&1 &
  bash run_arm.sh FIX_UCRYPTO_prod_s${s}_ccal prod w10_health.py $COMMON FSEED=$s UMASK_SCOPE=m1      UMASK_NPZ=$UC COSTB_JSON=$CB W3FIX=0.21,0,0.79 > logs/FIX_UCRYPTO_prod_s${s}_ccal.out 2>&1 &
done
wait
A=""
for s in 42 2027; do for p in M1 MEM FIX; do A="$A dev_alt/probe_artifacts/w10_ablation_series_${p}_UCRYPTO_prod_s${s}_ccal.npz"; done; done
/workspace/venv/bin/python health_metrics.py $A > logs/health_metrics_ucrypto.log 2>&1
echo "METRICS rc=$? $(date -u +%FT%TZ)" >> logs/chain_ucrypto.log
sha256sum dev_alt/probe_artifacts/w10_ablation_series_*_UCRYPTO_*.npz >> logs/chain_ucrypto.log
echo "CHAIN_UCRYPTO_DONE $(date -u +%FT%TZ)" >> logs/chain_ucrypto.log
