#!/bin/bash
# run_equiv.sh — device equivalence receipts BEFORE any new arm: pinned (K0) and rollm (K1) L-fix arms in my dev/ + dev_alt/ layouts,
# then bitwise comparison vs the port baseline / rolling_king / refute_C6_2 artifacts (check_equiv.py).
ROOT=/workspace/review_scratch/cadence_seats/axisA; PY=/workspace/venv/bin/python
cd $ROOT
bash run_arms.sh pinned > logs/run_arms_pinned.out 2>&1 &
bash run_arms.sh rollm  > logs/run_arms_rollm.out 2>&1 &
wait
echo "EQUIV_RUNS_DONE $(date -u +%Y-%m-%dT%H:%M:%SZ)" | tee -a logs/commands.txt
echo "CMD[check_equiv pinned] $(date -u +%Y-%m-%dT%H:%M:%SZ): cd $ROOT && $PY check_equiv.py pinned" | tee -a logs/commands.txt
$PY check_equiv.py pinned > logs/check_equiv_pinned.log 2>&1
echo "CMD[check_equiv rollm] $(date -u +%Y-%m-%dT%H:%M:%SZ): cd $ROOT && $PY check_equiv.py rollm" | tee -a logs/commands.txt
$PY check_equiv.py rollm > logs/check_equiv_rollm.log 2>&1
cat logs/check_equiv_pinned.log logs/check_equiv_rollm.log
echo "EQUIV_DONE"
