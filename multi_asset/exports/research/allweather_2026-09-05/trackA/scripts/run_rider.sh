#!/bin/bash
# run_rider.sh — one rider-device run in the health-check main-arm form (chain_all.sh COMMON + UPIT mask + live-calibrated cost, prod caliber = dev_alt).
# usage: run_rider.sh <TAG> <FSEED> <SPOTSUP_B> [SPOTSUP_NPZ]   (SPOTSUP_B=0 => identity run, no matrix)
# Verbatim main-arm env from /workspace/review_scratch/health_check/chain_all.sh (2026-09-05): LEGS=101 CAL=log SLOW_NPY=pinned WRULE=msharpe LOOK=900
# MEMBERS_TOPN=829 FTRIM=zero PHI=0.45 UMASK_SCOPE=trade UMASK_NPZ=masks/umask_UPIT.npz COSTB_JSON=calib/costb_fee_steady.json; OMP 4 threads as run_arm.sh.
ROOT=/workspace/review_scratch/allweather_trackA; R=$ROOT/rider; PY=/workspace/venv/bin/python
TAG=$1; FSEED=$2; B=$3; NPZ=$4
COMMON="LEGS=101 CAL=log SLOW_NPY=/workspace/shadow_bundle_v3/slow_pred_pinned.npy WRULE=msharpe LOOK=900 MEMBERS_TOPN=829 FTRIM=zero PHI=0.45 UMASK_SCOPE=trade"
UP=/workspace/review_scratch/health_check/masks/umask_UPIT.npz; CB=/workspace/review_scratch/health_check/calib/costb_fee_steady.json
EXTRA="FSEED=$FSEED UMASK_NPZ=$UP COSTB_JSON=$CB SPOTSUP_B=$B"
[ -n "$NPZ" ] && EXTRA="$EXTRA SPOTSUP_NPZ=$NPZ"
export OMP_NUM_THREADS=4 OPENBLAS_NUM_THREADS=4 MKL_NUM_THREADS=4
CMD="env $COMMON $EXTRA OUT_TAG=$TAG $PY ../w10_health_spotsup.py"
echo "CMD[rider_$TAG] (cwd=$R/dev_alt) $(date -u +%FT%TZ): $CMD" >> $ROOT/logs/commands.txt
cd $R/dev_alt && $CMD > $R/dev_alt/logs/$TAG.log 2>&1; rc=$?
echo "END[rider_$TAG] rc=$rc $(date -u +%FT%TZ)" >> $ROOT/logs/commands.txt
grep -E "^(CONFIG|SLOW override|F10 OOS|SPOTSUP|UMASK|CONFIG_HEALTH|RECEIPT_EX d30|DONE|Traceback|AssertionError)" $R/dev_alt/logs/$TAG.log | cut -c1-600
exit $rc
