#!/bin/bash
cd /workspace/fp2_2026-09; while ! grep -q R6B_DONE overlay/variants_r6b.log 2>/dev/null; do sleep 15; done
export RUN_ARM_ROOT=/workspace/fp2_2026-09/health_check RUN_ARM_PY=/workspace/venv/bin/python
UP=/workspace/fx_data_2026-09-13/out/inject/umask_UPIT_CRYPTO_tradable_W24H.npz
COMMON="LEGS=101 CAL=log WRULE=msharpe LOOK=900 MEMBERS_TOPN=829 FTRIM=zero PHI=0.45 UMASK_SCOPE=m1 UMASK_NPZ=$UP COSTB_JSON=/workspace/fp2_2026-09/health_check/calib/costb_fee_steady.json SLOW_NPY=/workspace/fp2_2026-09/king_v4/SLOW_v3_on_v4axis.npy FSEED=42 FPRED=f10_A0_s42.npy"
for spec in "r6s:k=1,q=0.95,s=0.5" "r6s:k=1,q=0.98,s=0.5" "r6s:k=2,q=0.95,s=0.5" "r6s:k=2,q=0.98,s=0.5"; do
  tag=$(echo "$spec" | tr ":=," "___"); bash devices_v4chain/run_arm.sh V4_A0_dyn_s42_OVL_$tag v4 w10_health_overlay.py $COMMON OVERLAY=$spec > overlay/$tag.out 2>&1; echo "$spec rc=$? $(date -u +%FT%TZ)" >> overlay/variants_r6s.log
done
echo "R6S_DONE $(date -u +%FT%TZ)" >> overlay/variants_r6s.log
