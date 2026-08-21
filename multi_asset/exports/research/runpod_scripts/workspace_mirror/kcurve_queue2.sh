#!/bin/bash
while kill -0 2279 2>/dev/null; do sleep 20; done
cd /workspace
NTOP=400 SEED=3037 BATCH=4 python3 pod_kcurve.py > kcurve_K400_s3037.log 2>&1
echo QUEUE2_DONE >> /workspace/kcurve_queue.log
