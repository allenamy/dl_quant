#!/bin/bash
# GATE P (round-3 placebo instrument): w10_sleeve.py with ALL knobs off must reproduce
# archived V4_A0_{dyn,fix}_s{42,2027} rec AND W bitwise.
H=/workspace/review_scratch/health_check; R=/workspace/uplift_2026-09-11/r3_placebo
UP=$H/masks/umask_UPIT_CRYPTO.npz; CB=$H/calib/costb_fee_steady.json
K3=/workspace/review_scratch/king_v4/SLOW_v3_on_v4axis.npy
COMMON="LEGS=101 CAL=log WRULE=msharpe LOOK=900 MEMBERS_TOPN=829 FTRIM=zero PHI=0.45 UMASK_SCOPE=m1 UMASK_NPZ=$UP COSTB_JSON=$CB"
export OMP_NUM_THREADS=4 OPENBLAS_NUM_THREADS=4 MKL_NUM_THREADS=4
cd $R/dev || exit 2
for s in 42 2027; do
  env $COMMON SLOW_NPY=$K3 FSEED=$s FPRED=f10_A0_s$s.npy OUT_TAG=GP_A0_dyn_s$s /workspace/venv/bin/python /workspace/uplift_2026-09-11/w10_sleeve.py > $R/dev/logs/GP_A0_dyn_s$s.log 2>&1 &
  env $COMMON SLOW_NPY=$K3 FSEED=$s FPRED=f10_A0_s$s.npy W3FIX=0.21,0,0.79 OUT_TAG=GP_A0_fix_s$s /workspace/venv/bin/python /workspace/uplift_2026-09-11/w10_sleeve.py > $R/dev/logs/GP_A0_fix_s$s.log 2>&1 &
done
wait
echo GATEP_RUNS_DONE
