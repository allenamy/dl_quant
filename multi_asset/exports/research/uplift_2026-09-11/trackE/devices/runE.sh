#!/bin/bash
# TRACK E runner (PREREG sha 79acb030). usage: runE.sh <TAG> <ENV...>
TAG=$1; shift
H=/workspace/review_scratch/health_check; U=/workspace/uplift_2026-09-11; PY=/workspace/venv/bin/python
UP=$H/masks/umask_UPIT_CRYPTO.npz; CB=$H/calib/costb_fee_steady.json; K3=/workspace/review_scratch/king_v4/SLOW_v3_on_v4axis.npy
COMMON="LEGS=101 CAL=log WRULE=msharpe LOOK=900 MEMBERS_TOPN=829 FTRIM=zero PHI=0.45 UMASK_SCOPE=m1 UMASK_NPZ=$UP COSTB_JSON=$CB SLOW_NPY=$K3"
export OMP_NUM_THREADS=2 OPENBLAS_NUM_THREADS=2 MKL_NUM_THREADS=2
CMD="env $COMMON $* OUT_TAG=$TAG PD_OUT=$U/artifacts $PY $U/w10_seat.py"
echo "CMD[$TAG] $(date -u +%FT%TZ): $CMD" >> $U/logs/commands.txt
cd $H/dev_v4 && $CMD > $U/logs/$TAG.log 2>&1; rc=$?
echo "END[$TAG] rc=$rc $(date -u +%FT%TZ)" >> $U/logs/commands.txt
[ $rc -ne 0 ] && tail -20 $U/logs/$TAG.log
exit $rc
