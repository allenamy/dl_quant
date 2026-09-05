#!/bin/bash
# run_arm.sh — one device run under review_scratch/v2main_fold2026/replay (copied from health_check/run_arm.sh; ROOT changed; dev_alt_ext layout added).
# usage: run_arm.sh <TAG> <dev|dev_alt|dev_alt_ext> <DEVICE_FILE relative to replay/> <ENV assignments...>
TAG=$1; LAY=$2; DEV=$3; shift 3
ROOT=/workspace/review_scratch/v2main_fold2026/replay; PY=/workspace/venv/bin/python
case $LAY in dev|dev_alt|dev_alt_ext) d=$ROOT/$LAY ;; *) echo "bad layout $LAY"; exit 2 ;; esac
[ -f "$ROOT/$DEV" ] || { echo "missing device $ROOT/$DEV"; exit 3; }
export OMP_NUM_THREADS=4 OPENBLAS_NUM_THREADS=4 MKL_NUM_THREADS=4
CMD="env $* OUT_TAG=$TAG $PY ../$DEV"
echo "CMD[$TAG] (cwd=$d) $(date -u +%FT%TZ): $CMD" >> $ROOT/../logs/commands.txt
cd $d && $CMD > $d/logs/$TAG.log 2>&1; rc=$?
echo "END[$TAG] rc=$rc $(date -u +%FT%TZ)" >> $ROOT/../logs/commands.txt
grep -E "^(CONFIG|SLOW override|F10 leg source|F10 OOS|MEMBERS_TOPN|UMASK|COSTB|CONFIG_HEALTH|RECEIPT_EX d30|DONE|Traceback|AssertionError|NOTE)" $d/logs/$TAG.log | cut -c1-600
exit $rc
