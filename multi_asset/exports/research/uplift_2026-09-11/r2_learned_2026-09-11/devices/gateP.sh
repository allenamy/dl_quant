#!/bin/bash
# GATE P: all six knobs off => w10_sleeve.py must reproduce archived A0 bitwise.
set -e
H=/workspace/review_scratch/health_check
R2=/workspace/uplift_2026-09-11/r2_learned
UP=$H/masks/umask_UPIT_CRYPTO.npz; CB=$H/calib/costb_fee_steady.json
K3=/workspace/review_scratch/king_v4/SLOW_v3_on_v4axis.npy
COMMON="LEGS=101 CAL=log WRULE=msharpe LOOK=900 MEMBERS_TOPN=829 FTRIM=zero PHI=0.45 UMASK_SCOPE=m1 UMASK_NPZ=$UP COSTB_JSON=$CB"
export OMP_NUM_THREADS=6 OPENBLAS_NUM_THREADS=6 MKL_NUM_THREADS=6
cd $R2/dev
for s in 42 2027; do
  for form in dyn fix; do
    EX=""; [ $form = fix ] && EX="W3FIX=0.21,0,0.79"
    env $COMMON SLOW_NPY=$K3 FSEED=$s FPRED=f10_A0_s$s.npy $EX OUT_TAG=GP_A0_${form}_s$s /workspace/venv/bin/python $R2/w10_sleeve.py > logs/GP_A0_${form}_s$s.log 2>&1 &
  done
done
wait
echo GATEP_RUNS_DONE
