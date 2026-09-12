#!/bin/bash
# run19.sh <TAG> <ENV...> — one w10_trackF.py run in the r19 mirror tree; env passed verbatim; command logged.
TAG=$1; shift
R19=/workspace/uplift_2026-09-11/r19_trackF_reindex; T=$R19/dev_v4F19; DEV=$R19/w10_trackF.py
PY=/workspace/venv/bin/python
export OMP_NUM_THREADS=4 OPENBLAS_NUM_THREADS=4 MKL_NUM_THREADS=4
CMD="env $* OUT_TAG=_$TAG $PY $DEV"
echo "CMD[$TAG] $(date -u +%FT%TZ): (cwd=$T) $CMD" >> $R19/commands.txt
cd $T && $CMD > $T/logs/$TAG.log 2>&1; rc=$?
echo "END[$TAG] rc=$rc $(date -u +%FT%TZ)" >> $R19/commands.txt
grep -aE "^(CONFIG |RECEIPT_EX d30|DONE|Traceback|AssertionError|TF regime labels|TF seat pools)" $T/logs/$TAG.log | cut -c1-300
exit $rc
