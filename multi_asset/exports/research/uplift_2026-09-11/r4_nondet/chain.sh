#!/bin/bash
# P4 chain: fires once all 12 trainings report TRAIN_RC.
set -u
R=/workspace/uplift_2026-09-11/r4_nondet
PY=/workspace/venv/bin/python
cd $R
while [ "$(grep -c TRAIN_RC logs/train_status.txt 2>/dev/null || echo 0)" -lt 12 ]; do sleep 30; done
echo "=== TRAIN STATUS ==="; cat logs/train_status.txt
grep -h F10_TRAIN_DONE logs/train_D*.log logs/train_R*.log
echo "=== VERIFY TRAIN (sha / va / input shas) ==="
$PY verify_train.py D1,D2,D3,D4,D5,D6,D7,D8,R1,R2,R3,R4 2>&1 | tail -40
echo "=== ALIGN ==="
$PY align_p4.py D1,D2,D3,D4,D5,D6,D7,D8,R1,R2,R3,R4 2>&1 | tail -25
echo "=== DEVICE at FITTED cost PWR230k ==="
$PY runner.py D1,D2,D3,D4,D5,D6,D7,D8,R1,R2,R3,R4 PWR230k 2>&1 | tail -30
echo "=== ANALYZE ==="
$PY analyze_p4.py '{"SAME_SEED42_V2ONE":["R1","R2","R3","R4","42"],"SAME_SEED42_V2ZERO":["D1","D2","D3","D4","D5","D6","D7","D8","REP42"],"SEEDS_V2ZERO":["7","101","1234","31337"],"ARCHIVED_V2ONE":["42","2027"]}' SEEDS_V2ZERO 2>&1 | tail -120
echo "CHAIN_P4_DONE"
