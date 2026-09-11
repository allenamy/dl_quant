#!/bin/bash
# TRACK B arms on dev_tb. usage: run_tb.sh
D=/workspace/uplift_2026-09-11/dev_tb
COMMON="LEGS=101 CAL=log WRULE=msharpe LOOK=900 MEMBERS_TOPN=829 FTRIM=zero PHI=0.45 UMASK_SCOPE=m1 UMASK_NPZ=/workspace/review_scratch/health_check/masks/umask_UPIT_CRYPTO.npz COSTB_JSON=/workspace/review_scratch/health_check/calib/costb_fee_steady.json SLOW_NPY=/workspace/review_scratch/king_v4/SLOW_v4.npy"
declare -a ARMS=(
"BASE:"
"BAND5e4:TB_BAND=5e-4"
"BAND1e3:TB_BAND=1e-3"
"BAND2e3:TB_BAND=2e-3"
"EMA005:TB_EMA=0.05"
"EMA003:TB_EMA=0.03"
"EMA020:TB_EMA=0.20"
"TOPD50:TB_TOPD=50"
"TOPD100:TB_TOPD=100"
"TOPD200:TB_TOPD=200"
"CAD2:TB_CAD=2"
"CAD3:TB_CAD=3"
"CAD6:TB_CAD=6"
"HOLD2:TB_HOLD=2"
"HOLD3:TB_HOLD=3"
"HOLD6:TB_HOLD=6"
)
cd $D || exit 2
n=0
for a in "${ARMS[@]}"; do
  NM="${a%%:*}"; EV="${a#*:}"
  for s in 42 2027; do
    TAG=TB_${NM}_dyn_s$s
    [ -f $D/probe_artifacts/w10_ablation_series_${TAG}.npz ] && { echo "skip $TAG"; continue; }
    ( env $COMMON $EV FSEED=$s FPRED=f10_v4RAW_s$s.npy OUT_TAG=$TAG \
        OMP_NUM_THREADS=4 OPENBLAS_NUM_THREADS=4 MKL_NUM_THREADS=4 \
        /workspace/venv/bin/python /workspace/uplift_2026-09-11/w10_tb.py > $D/logs/$TAG.log 2>&1 ; echo "END $TAG rc=$?" ) &
    n=$((n+1))
    if [ $((n % 10)) -eq 0 ]; then wait; fi
  done
done
wait
echo ALLDONE
