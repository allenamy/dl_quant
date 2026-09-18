#!/bin/bash
# PREREG R (RESULT §2 R3) limited-budget replication approved by the user 2026-09-18: A1 arm (retrained chain) seed 42 and A0 seed 2027; baseline + r3 th=0.20 each
cd /workspace/fp2_2026-09; export RUN_ARM_ROOT=/workspace/fp2_2026-09/health_check RUN_ARM_PY=/workspace/venv/bin/python
UP=/workspace/fx_data_2026-09-13/out/inject/umask_UPIT_CRYPTO_tradable_W24H.npz
COMMON="LEGS=101 CAL=log WRULE=msharpe LOOK=900 MEMBERS_TOPN=829 FTRIM=zero PHI=0.45 UMASK_SCOPE=m1 UMASK_NPZ=$UP COSTB_JSON=/workspace/fp2_2026-09/health_check/calib/costb_fee_steady.json"
K3=/workspace/fp2_2026-09/king_v4/SLOW_v3_on_v4axis.npy; K4=/workspace/fp2_2026-09/king_v4/SLOW_v4.npy
for arm in "A1 42 $K4 f10_v4RAW_s42.npy" "A0 2027 $K3 f10_A0_s2027.npy"; do set -- $arm; A=$1; S=$2; SL=$3; FP=$4
  for spec in none "r3:th=0.20"; do tag=$( [ "$spec" = none ] && echo OVLnone || echo OVL_$(echo "$spec" | tr ":=," "___") )
    bash devices_v4chain/run_arm.sh V4_${A}_dyn_s${S}_$tag v4 w10_health_overlay.py $COMMON SLOW_NPY=$SL FSEED=$S FPRED=$FP OVERLAY=$spec > overlay/r3rep_${A}_s${S}_$tag.out 2>&1; echo "$A s$S $spec rc=$? $(date -u +%FT%TZ)" >> overlay/variants_r3rep.log
  done
done
echo "R3REP_DONE $(date -u +%FT%TZ)" >> overlay/variants_r3rep.log
