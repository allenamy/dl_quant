#!/bin/bash
# chain_b0.sh — seat_round2 step 1: B0 baseline rerun with the patched device (w10_seat2.py) in all four cells {prod,log}×{42,2027},
# then the bitwise equivalence receipt against health_check M1_UPIT_{cal}_s{seed}_ccal (all four rec/W arrays + config minus self-report keys).
# Primary-arm command copied verbatim from health_check/logs/commands.txt (M1_UPIT_prod_s42_ccal), device file name changed only.
set -u
ROOT=/workspace/review_scratch/seat_round2; cd $ROOT
COMMON="LEGS=101 CAL=log SLOW_NPY=/workspace/shadow_bundle_v3/slow_pred_pinned.npy WRULE=msharpe LOOK=900 MEMBERS_TOPN=829 FTRIM=zero PHI=0.45"
UP=/workspace/review_scratch/health_check/masks/umask_UPIT.npz
CB=/workspace/review_scratch/health_check/calib/costb_fee_steady.json
sha256sum w10_seat2.py w10_health_orig.py $UP $CB /workspace/shadow_bundle_v3/slow_pred_pinned.npy >> logs/chain_b0.log
for cal in log prod; do for s in 42 2027; do
  bash run_arm.sh B0_${cal}_s${s} $cal w10_seat2.py $COMMON FSEED=$s UMASK_SCOPE=m1 UMASK_NPZ=$UP COSTB_JSON=$CB > logs/B0_${cal}_s${s}.out 2>&1 &
done; done
wait
ok=1
for cal in log prod; do for s in 42 2027; do
  case $cal in log) d=dev ;; prod) d=dev_alt ;; esac
  /workspace/venv/bin/python check_equiv.py $d/probe_artifacts/w10_ablation_series_B0_${cal}_s${s}.npz /workspace/review_scratch/health_check/$d/probe_artifacts/w10_ablation_series_M1_UPIT_${cal}_s${s}_ccal.npz "B0_${cal}_s${s} (w10_seat2.py default path) vs health_check M1_UPIT_${cal}_s${s}_ccal" >> logs/check_equiv.log 2>&1 || ok=0
done; done
[ $ok = 1 ] && echo "B0_EQUIV_ALL_PASS $(date -u +%FT%TZ)" >> logs/chain_b0.log || echo "B0_EQUIV_FAIL $(date -u +%FT%TZ)" >> logs/chain_b0.log
sha256sum dev/probe_artifacts/w10_ablation_series_B0_*.npz dev_alt/probe_artifacts/w10_ablation_series_B0_*.npz >> logs/chain_b0.log
echo "CHAIN_B0_DONE $(date -u +%FT%TZ)" >> logs/chain_b0.log
