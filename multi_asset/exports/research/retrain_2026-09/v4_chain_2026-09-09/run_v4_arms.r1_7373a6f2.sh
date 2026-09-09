#!/bin/bash
# run_v4_arms.sh — PREREG_v4 §2.5 book-layer arms on the dev_v4 tree (RAW accounting). usage: run_v4_arms.sh <ARM: A0|A1|A2|A3> [seeds="42 2027"]
ARM=$1; SEEDS=${2:-"42 2027"}; H=/workspace/review_scratch/health_check; cd $H || exit 2
UP=$H/masks/umask_UPIT_CRYPTO.npz; CB=$H/calib/costb_fee_steady.json; K3=/workspace/review_scratch/king_v4/SLOW_v3_on_v4axis.npy; K4=/workspace/review_scratch/king_v4/SLOW_v4.npy
COMMON="LEGS=101 CAL=log WRULE=msharpe LOOK=900 MEMBERS_TOPN=829 FTRIM=zero PHI=0.45 UMASK_SCOPE=m1 UMASK_NPZ=$UP COSTB_JSON=$CB"
for s in $SEEDS; do
  case $ARM in A0) SL=$K3; FP=f10_A0_s$s.npy ;; A1) SL=$K4; FP=f10_v4RAW_s$s.npy ;; A2) SL=$K4; FP=f10_v4CLIP_s$s.npy ;; A3) SL=$K4; FP=f10_A0_s$s.npy ;; *) echo "bad arm $ARM"; exit 2 ;; esac
  [ -f $H/dev_v4/f8_2026-08-22/preds/$FP ] || { echo "missing FPRED $FP"; exit 3; }
  bash run_arm.sh V4_${ARM}_dyn_s$s v4 w10_health.py $COMMON SLOW_NPY=$SL FSEED=$s FPRED=$FP > $H/dev_v4/logs/V4_${ARM}_dyn_s$s.out 2>&1 &
  bash run_arm.sh V4_${ARM}_fix_s$s v4 w10_health.py $COMMON SLOW_NPY=$SL FSEED=$s FPRED=$FP W3FIX=0.21,0,0.79 > $H/dev_v4/logs/V4_${ARM}_fix_s$s.out 2>&1 &
done; wait; grep -a -E "^END\[V4_${ARM}_" $H/logs/commands.txt | tail -4
