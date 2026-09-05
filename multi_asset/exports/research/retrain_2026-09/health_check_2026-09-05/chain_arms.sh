#!/bin/bash
# chain_arms.sh — rebuild masks (listing fix), run the 4 default-cost U-PIT arms (PREREG §3) in parallel, first metrics pass (+ the equivalence artifact as the M1+T400 reference form).
cd /workspace/review_scratch/health_check
/workspace/venv/bin/python build_umask.py > logs/build_umask.log 2>&1 || { echo "MASK_FAIL $(date -u +%FT%TZ)" >> logs/chain_arms.log; exit 1; }
sha256sum masks/umask_UPIT.npz masks/umask_UFROZEN.npz masks/btc_rv30.npz >> logs/chain_arms.log
COMMON="LEGS=101 CAL=log SLOW_NPY=/workspace/shadow_bundle_v3/slow_pred_pinned.npy WRULE=msharpe LOOK=900 MEMBERS_TOPN=829 FTRIM=zero PHI=0.45 UMASK_SCOPE=trade"
UP=/workspace/review_scratch/health_check/masks/umask_UPIT.npz
for cal in log prod; do for s in 42 2027; do
  bash run_arm.sh UPIT_${cal}_s${s}_cdef $cal w10_health.py $COMMON FSEED=$s UMASK_NPZ=$UP > logs/UPIT_${cal}_s${s}_cdef.out 2>&1 &
done; done
wait
rm -f masks/regime_series.npz
/workspace/venv/bin/python health_metrics.py dev/probe_artifacts/w10_ablation_series_eq_patched_pinned_log_s42.npz dev/probe_artifacts/w10_ablation_series_UPIT_log_s42_cdef.npz dev/probe_artifacts/w10_ablation_series_UPIT_log_s2027_cdef.npz dev_alt/probe_artifacts/w10_ablation_series_UPIT_prod_s42_cdef.npz dev_alt/probe_artifacts/w10_ablation_series_UPIT_prod_s2027_cdef.npz > logs/health_metrics_1.log 2>&1
echo "METRICS1 rc=$? $(date -u +%FT%TZ)" >> logs/chain_arms.log
echo "CHAIN_ARMS_DONE $(date -u +%FT%TZ)" >> logs/chain_arms.log
