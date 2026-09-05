#!/bin/bash
# chain_k3.sh — reads the frozen D1 decision from d1_curve.json; if K3 == RUN, waits for K2 (monthly1) to finish and launches K3 (weekly1).
ROOT=/workspace/review_scratch/cadence_seats/axisA; PY=/workspace/venv/bin/python
cd $ROOT
until [ -f d1_curve.json ]; do sleep 15; done
K3=$($PY -c "import json;print(json.load(open('d1_curve.json'))['decision']['K3'])")
echo "D1 decision K3=$K3 $(date -u +%Y-%m-%dT%H:%M:%SZ)"
if [ "$K3" = "RUN" ]; then
  until grep -qE "^DONE monthly1|Traceback" logs/monthly1.log 2>/dev/null; do sleep 15; done
  echo "monthly1 finished $(date -u +%Y-%m-%dT%H:%M:%SZ)"
  bash launch_train.sh weekly1
  echo "CHAIN_K3_LAUNCHED $(date -u +%Y-%m-%dT%H:%M:%SZ)"
else
  echo "CHAIN_K3_SKIPPED (D1: no measurable decay)"
fi
