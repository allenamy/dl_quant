#!/bin/bash
# runF.sh <TAG> <ENV...> — one Track F device run in the mirrored tree. Artifacts stay under /workspace/uplift_2026-09-11/trackF/.
TAG=$1; shift
T=/workspace/uplift_2026-09-11/trackF/dev_v4F; DEV=/workspace/uplift_2026-09-11/trackF/w10_health_copy.py
PY=/workspace/venv/bin/python
export OMP_NUM_THREADS=4 OPENBLAS_NUM_THREADS=4 MKL_NUM_THREADS=4
CMD="env $* OUT_TAG=_$TAG $PY $DEV"
echo "CMD[$TAG] $(date -u +%FT%TZ): (cwd=$T) $CMD" >> /workspace/uplift_2026-09-11/trackF/commands.txt
cd $T && $CMD > $T/logs/$TAG.log 2>&1; rc=$?
echo "END[$TAG] rc=$rc $(date -u +%FT%TZ)" >> /workspace/uplift_2026-09-11/trackF/commands.txt
grep -aE "^(CONFIG |RECEIPT_EX d30|DONE|Traceback|AssertionError)" $T/logs/$TAG.log | cut -c1-400
exit $rc
