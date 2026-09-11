#!/bin/bash
# run_uplift.sh — Track A arms on dev_v4 with w10_sleeve.py. usage: run_uplift.sh <TAG> <seed> <extra env...>
TAG=$1; S=$2; shift 2
H=/workspace/review_scratch/health_check; U=/workspace/uplift_2026-09-11; PY=/workspace/venv/bin/python
UP=$H/masks/umask_UPIT_CRYPTO.npz; CB=$H/calib/costb_fee_steady.json; K3=/workspace/review_scratch/king_v4/SLOW_v3_on_v4axis.npy
COMMON="LEGS=101 CAL=log WRULE=msharpe LOOK=900 MEMBERS_TOPN=829 PHI=0.45 UMASK_SCOPE=m1 UMASK_NPZ=$UP COSTB_JSON=$CB"
export OMP_NUM_THREADS=4 OPENBLAS_NUM_THREADS=4 MKL_NUM_THREADS=4
CMD="env $COMMON SLOW_NPY=$K3 FSEED=$S FPRED=f10_A0_s$S.npy $* OUT_TAG=$TAG $PY $U/w10_sleeve.py"
echo "CMD[$TAG] (cwd=$H/dev_v4) $(date -u +%FT%TZ): $CMD" >> $U/logs/commands.txt
cd $H/dev_v4 && $CMD > $U/logs/$TAG.log 2>&1; rc=$?
echo "END[$TAG] rc=$rc $(date -u +%FT%TZ)" >> $U/logs/commands.txt
# artifact lands in dev_v4/probe_artifacts; move to uplift dir (never overwrite a v4 artifact)
mv $H/dev_v4/probe_artifacts/w10_ablation_series_$TAG.npz $U/probe_artifacts/ 2>/dev/null
mv $H/dev_v4/probe_artifacts/w10_ablation_summary_$TAG.json $U/probe_artifacts/ 2>/dev/null
echo "rc=$rc $TAG"
