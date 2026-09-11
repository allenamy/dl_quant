#!/bin/bash
# GATE P for NEW DATA 4 (LOB-as-information). Env whitelist asserted verbatim (E-0826-D).
HC=/workspace/review_scratch/health_check
D=/workspace/uplift_2026-09-11/r5_lob/dev
PY=/workspace/venv/bin/python
DEV=/workspace/uplift_2026-09-11/w10_sleeve.py
export OMP_NUM_THREADS=4 OPENBLAS_NUM_THREADS=4 MKL_NUM_THREADS=4
COMMON="CAL=log WRULE=msharpe LOOK=900 MEMBERS_TOPN=829 UMASK_SCOPE=m1 UMASK_NPZ=$HC/masks/umask_UPIT_CRYPTO.npz COSTB_JSON=$HC/calib/costb_fee_steady.json SLOW_NPY=/workspace/review_scratch/king_v4/SLOW_v3_on_v4axis.npy LEGS=101 PHI=0.45 FTRIM=zero"
for s in 42 2027; do
  for form in dyn fix; do
    if [ $form = fix ]; then EX="W3FIX=0.21,0,0.79"; else EX=""; fi
    TAG=GP5_A0_${form}_s${s}
    echo "CMD[$TAG] (cwd=$D) env $COMMON $EX FSEED=$s FPRED=f10_A0_s${s}.npy OUT_TAG=$TAG $PY $DEV" >> /workspace/uplift_2026-09-11/r5_lob/commands.txt
    ( cd $D && env $COMMON $EX FSEED=$s FPRED=f10_A0_s${s}.npy OUT_TAG=$TAG $PY $DEV > $D/logs/$TAG.log 2>&1 ) &
  done
done
wait
echo GATEP5_RUNS_DONE
