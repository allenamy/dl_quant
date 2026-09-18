#!/bin/bash
cd /workspace/fp2_2026-09; export RUN_ARM_ROOT=/workspace/fp2_2026-09/health_check RUN_ARM_PY=/workspace/venv/bin/python
UP=/workspace/fx_data_2026-09-13/out/inject/umask_UPIT_CRYPTO_tradable_W24H.npz
COMMON="LEGS=101 CAL=log WRULE=msharpe LOOK=900 MEMBERS_TOPN=829 FTRIM=zero PHI=0.45 UMASK_SCOPE=m1 UMASK_NPZ=$UP COSTB_JSON=/workspace/fp2_2026-09/health_check/calib/costb_fee_steady.json SLOW_NPY=/workspace/fp2_2026-09/king_v4/SLOW_v3_on_v4axis.npy FSEED=42 FPRED=f10_A0_s42.npy"
for c in 0.969 0.9868 0.966 0.984; do bash devices_v4chain/run_arm.sh V4_A0_dyn_s42_OVL_r6c_c_$c v4 w10_health_overlay.py $COMMON OVERLAY=r6c:c=$c > overlay/r6c_$c.out 2>&1; echo "r6c:c=$c rc=$? $(date -u +%FT%TZ)" >> overlay/variants_r6n.log; done
for spec in "r6n:k=1,q=0.95,s=0.5,ncap=0.05" "r6n:k=1,q=0.95,s=0.5,ncap=0.10" "r6n:k=2,q=0.95,s=0.5,ncap=0.05" "r6n:k=2,q=0.95,s=0.5,ncap=0.10"; do
  tag=$(echo "$spec" | tr ":=," "___"); bash devices_v4chain/run_arm.sh V4_A0_dyn_s42_OVL_$tag v4 w10_health_overlay.py $COMMON OVERLAY=$spec > overlay/$tag.out 2>&1; echo "$spec rc=$? $(date -u +%FT%TZ)" >> overlay/variants_r6n.log
done
echo "R6N_DONE $(date -u +%FT%TZ)" >> overlay/variants_r6n.log
