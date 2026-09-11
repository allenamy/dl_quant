#!/bin/bash
# GATE P: w10_sleeve.py with all six knobs OFF must reproduce archived A0 arms BITWISE.
R=/workspace/uplift_2026-09-11/r2_horizon
H=/workspace/review_scratch/health_check; PY=/workspace/venv/bin/python
UP=$H/masks/umask_UPIT_CRYPTO.npz; CB=$H/calib/costb_fee_steady.json
K3=/workspace/review_scratch/king_v4/SLOW_v3_on_v4axis.npy
COMMON="LEGS=101 CAL=log WRULE=msharpe LOOK=900 MEMBERS_TOPN=829 PHI=0.45 FTRIM=zero UMASK_SCOPE=m1 UMASK_NPZ=$UP COSTB_JSON=$CB"
export OMP_NUM_THREADS=4 OPENBLAS_NUM_THREADS=4 MKL_NUM_THREADS=4
run(){ TAG=$1; S=$2; W3=$3
  EX=""; [ -n "$W3" ] && EX="W3FIX=$W3"
  cd $R/dev && env $COMMON SLOW_NPY=$K3 FSEED=$S FPRED=f10_A0_s$S.npy $EX OUT_TAG=$TAG $PY /workspace/uplift_2026-09-11/w10_sleeve.py > $R/dev/logs/$TAG.log 2>&1
  echo "rc=$? $TAG"; }
run GP_A0_dyn_s42 42 "" &
run GP_A0_dyn_s2027 2027 "" &
run GP_A0_fix_s42 42 "0.21,0,0.79" &
run GP_A0_fix_s2027 2027 "0.21,0,0.79" &
wait
