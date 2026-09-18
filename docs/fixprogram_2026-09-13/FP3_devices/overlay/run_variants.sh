#!/bin/bash
# FP3-R overlay variants (PREREG §2 grid), each = frozen engine + one rule; tags OVL_<name>
cd /workspace/fp2_2026-09; export RUN_ARM_ROOT=/workspace/fp2_2026-09/health_check RUN_ARM_PY=/workspace/venv/bin/python
UP=/workspace/fx_data_2026-09-13/out/inject/umask_UPIT_CRYPTO_tradable_W24H.npz
COMMON="LEGS=101 CAL=log WRULE=msharpe LOOK=900 MEMBERS_TOPN=829 FTRIM=zero PHI=0.45 UMASK_SCOPE=m1 UMASK_NPZ=$UP COSTB_JSON=/workspace/fp2_2026-09/health_check/calib/costb_fee_steady.json SLOW_NPY=/workspace/fp2_2026-09/king_v4/SLOW_v3_on_v4axis.npy FSEED=42 FPRED=f10_A0_s42.npy"
for spec in "r1a:q=0.90,s=0.5" "r1a:q=0.95,s=0.5" "r1a:q=0.95,s=0" "r1b:q=0.95,s=0.5" "r2:c=0.5" "r2:c=1.0" "r3:th=0.20" "r3:th=0.30" "r3f" "r4:win=360"; do
  tag=$(echo "$spec" | tr ":=," "___"); bash devices_v4chain/run_arm.sh V4_A0_dyn_s42_OVL_$tag v4 w10_health_overlay.py $COMMON OVERLAY=$spec > overlay/$tag.out 2>&1; echo "$spec rc=$? $(date -u +%FT%TZ)" >> overlay/variants.log
done
echo "VARIANTS_DONE $(date -u +%FT%TZ)" >> overlay/variants.log
