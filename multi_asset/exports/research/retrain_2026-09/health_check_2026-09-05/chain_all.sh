#!/bin/bash
# chain_all.sh — FINAL: rebuild masks (listing fix v2), run the 10 PREREG §3 arms on the final mask files, metrics on 10 arms + the equivalence artifact (M1+T400 reference form).
cd /workspace/review_scratch/health_check
/workspace/venv/bin/python build_umask.py > logs/build_umask_final.log 2>&1 || { echo "MASK_FAIL $(date -u +%FT%TZ)" >> logs/chain_all.log; exit 1; }
sha256sum masks/umask_UPIT.npz masks/umask_UFROZEN.npz masks/btc_rv30.npz calib/costb_fee_steady.json >> logs/chain_all.log
COMMON="LEGS=101 CAL=log SLOW_NPY=/workspace/shadow_bundle_v3/slow_pred_pinned.npy WRULE=msharpe LOOK=900 MEMBERS_TOPN=829 FTRIM=zero PHI=0.45 UMASK_SCOPE=trade"
UP=/workspace/review_scratch/health_check/masks/umask_UPIT.npz; UF=/workspace/review_scratch/health_check/masks/umask_UFROZEN.npz; CB=/workspace/review_scratch/health_check/calib/costb_fee_steady.json
for cal in log prod; do for s in 42 2027; do
  bash run_arm.sh UPIT_${cal}_s${s}_cdef $cal w10_health.py $COMMON FSEED=$s UMASK_NPZ=$UP > logs/UPIT_${cal}_s${s}_cdef.out 2>&1 &
  bash run_arm.sh UPIT_${cal}_s${s}_ccal $cal w10_health.py $COMMON FSEED=$s UMASK_NPZ=$UP COSTB_JSON=$CB > logs/UPIT_${cal}_s${s}_ccal.out 2>&1 &
done; done
for s in 42 2027; do
  bash run_arm.sh UFROZEN_prod_s${s}_ccal prod w10_health.py $COMMON FSEED=$s UMASK_NPZ=$UF COSTB_JSON=$CB > logs/UFROZEN_prod_s${s}_ccal.out 2>&1 &
done
wait
rm -f masks/regime_series.npz
A="dev/probe_artifacts/w10_ablation_series_eq_patched_pinned_log_s42.npz"
for s in 42 2027; do for c in cdef ccal; do A="$A dev/probe_artifacts/w10_ablation_series_UPIT_log_s${s}_${c}.npz dev_alt/probe_artifacts/w10_ablation_series_UPIT_prod_s${s}_${c}.npz"; done; A="$A dev_alt/probe_artifacts/w10_ablation_series_UFROZEN_prod_s${s}_ccal.npz"; done
/workspace/venv/bin/python health_metrics.py $A > logs/health_metrics_final.log 2>&1
echo "METRICS rc=$? $(date -u +%FT%TZ)" >> logs/chain_all.log
sha256sum dev/probe_artifacts/w10_ablation_series_*.npz dev_alt/probe_artifacts/w10_ablation_series_*.npz results/*.json >> logs/chain_all.log
echo "CHAIN_ALL_DONE $(date -u +%FT%TZ)" >> logs/chain_all.log
