#!/bin/bash
# Track F arsenal: per-leg / per-form books on the v4 tree, in-service COMMON except the varied knob.
R=/workspace/uplift_2026-09-11/trackF
H=/workspace/review_scratch/health_check
UP=$H/masks/umask_UPIT_CRYPTO.npz; CB=$H/calib/costb_fee_steady.json
K3=/workspace/review_scratch/king_v4/SLOW_v3_on_v4axis.npy
COMMON="CAL=log WRULE=msharpe LOOK=900 MEMBERS_TOPN=829 FTRIM=zero UMASK_SCOPE=m1 UMASK_NPZ=$UP COSTB_JSON=$CB SLOW_NPY=$K3 FSEED=42 FPRED=f10_A0_s42.npy"
run(){ bash $R/runF.sh "$1" $COMMON "${@:2}"; }
case "$1" in
 parity) run PARITY_A0_dyn_s42 LEGS=101 PHI=0.45 ;;
 arsenal)
   run AR_KF_p0    LEGS=101 PHI=0 &
   run AR_FUND     LEGS=001 PHI=0 &
   run AR_KING     LEGS=100 PHI=0 &
   wait
   run AR_REV      LEGS=010 PHI=0 &
   run AR_ALL3_p45 LEGS=111 PHI=0.45 &
   run AR_ALL3_p0  LEGS=111 PHI=0 &
   wait
   run AR_F10      LEGS=101 PHI=1.0 &
   run AR_KF_noftrim LEGS=101 PHI=0.45 FTRIM=off &
   wait ;;
esac
