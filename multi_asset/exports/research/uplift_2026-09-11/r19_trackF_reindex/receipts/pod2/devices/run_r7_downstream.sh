#!/bin/bash
# r19: after the corrected R7_FUEL.npz exists, run the five r7 downstream analyses on it (outputs -> r19/out_r7f2 only).
R19=/workspace/uplift_2026-09-11/r19_trackF_reindex; D=$R19/devices; PY=/workspace/venv/bin/python; L=$R19/logs_consumers
export OMP_NUM_THREADS=4 OPENBLAS_NUM_THREADS=4 MKL_NUM_THREADS=4
until grep -q "^END r7_fuel rc=0" $L/_status.txt; do sleep 5; done
run(){ n=$1; shift; echo "START $n $(date -u +%FT%TZ)" >> $L/_status.txt; "$@" > $L/$n.log 2>&1; echo "END $n rc=$? $(date -u +%FT%TZ)" >> $L/_status.txt; }
run r7_screen $PY $D/r7_screen_r19.py &
run r7_screen2 $PY $D/r7_screen2_r19.py &
run r7_spec $PY $D/r7_spec_r19.py &
run r7_withinyear $PY $D/r7_withinyear_r19.py &
run r7_final $PY $D/r7_final_r19.py &
wait
echo "R7_DOWNSTREAM_DONE $(date -u +%FT%TZ)" >> $L/_status.txt
