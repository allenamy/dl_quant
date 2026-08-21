#!/bin/bash
while pgrep -f "pod_kcurve" | grep -qv 2051 && kill -0 1627 2>/dev/null; do sleep 20; done
cd /workspace
NTOP=110 SEED=42 BATCH=6 python3 pod_kcurve.py > kcurve_K110_s42.log 2>&1
echo QUEUE_POD_DONE >> /workspace/kcurve_queue.log
