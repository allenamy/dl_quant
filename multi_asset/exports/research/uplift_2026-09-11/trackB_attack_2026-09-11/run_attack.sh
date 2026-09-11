#!/bin/bash
D=/workspace/uplift_2026-09-11/dev_tb
COMMON="LEGS=101 CAL=log WRULE=msharpe LOOK=900 MEMBERS_TOPN=829 FTRIM=zero PHI=0.45 UMASK_SCOPE=m1 UMASK_NPZ=/workspace/review_scratch/health_check/masks/umask_UPIT_CRYPTO.npz COSTB_JSON=/workspace/review_scratch/health_check/calib/costb_fee_steady.json"
V4K="SLOW_NPY=/workspace/review_scratch/king_v4/SLOW_v4.npy"
V3K="SLOW_NPY=/workspace/review_scratch/king_v4/SLOW_v3_on_v4axis.npy"
declare -a J=(
"AT_FIXBASE:W3FIX=0.21,0,0.79:$V4K:v4RAW"
"AT_FIXB5e4:W3FIX=0.21,0,0.79 TB_BAND=5e-4:$V4K:v4RAW"
"AT_FIXE005:W3FIX=0.21,0,0.79 TB_EMA=0.05:$V4K:v4RAW"
"AT_A0BASE::$V3K:A0"
"AT_A0B5e4:TB_BAND=5e-4:$V3K:A0"
"AT_A0E005:TB_EMA=0.05:$V3K:A0"
)
cd $D || exit 2
n=0
for a in "${J[@]}"; do
  IFS=":" read -r NM EV SL PR <<< "$a"
  for s in 42 2027; do
    TAG=${NM}_dyn_s$s
    [ -f $D/probe_artifacts/w10_ablation_series_${TAG}.npz ] && { echo "skip $TAG"; continue; }
    ( env $COMMON $SL $EV FSEED=$s FPRED=f10_${PR}_s$s.npy OUT_TAG=$TAG \
        OMP_NUM_THREADS=4 OPENBLAS_NUM_THREADS=4 MKL_NUM_THREADS=4 \
        /workspace/venv/bin/python /workspace/uplift_2026-09-11/w10_tb.py > $D/logs/$TAG.log 2>&1 ; echo "END $TAG rc=$?" ) &
    n=$((n+1))
    if [ $((n % 6)) -eq 0 ]; then wait; fi
  done
done
wait
echo ATTACKDONE
