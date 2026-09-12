#!/bin/bash
# r19: run the patched T2/T3 consumers; every output lands under r19_trackF_reindex/out_*; archives untouched.
R19=/workspace/uplift_2026-09-11/r19_trackF_reindex; D=$R19/devices; PY=/workspace/venv/bin/python; L=$R19/logs_consumers; mkdir -p $L
export OMP_NUM_THREADS=4 OPENBLAS_NUM_THREADS=4 MKL_NUM_THREADS=4
run(){ n=$1; shift; echo "START $n $(date -u +%FT%TZ)" >> $L/_status.txt; "$@" > $L/$n.log 2>&1; echo "END $n rc=$? $(date -u +%FT%TZ)" >> $L/_status.txt; }
run regcomp   $PY $D/regcomp_r19.py &
run j1_regime $PY $D/j1_regime_r19.py &
run regime_gb $PY $D/regime_gb_r19.py &
run r7_fuel   $PY $D/r7_fuel_r19.py &
run p3_b      $PY $D/p3_b_r19.py &
wait
run r7_screen $PY $D/r7_screen_r19.py &
run r7_screen2 $PY $D/r7_screen2_r19.py &
run r7_spec   $PY $D/r7_spec_r19.py &
run r7_withinyear $PY $D/r7_withinyear_r19.py &
run r7_final  $PY $D/r7_final_r19.py &
run p3_an     $PY $D/p3_an_r19.py &
wait
echo "ALL_DONE $(date -u +%FT%TZ)" >> $L/_status.txt
