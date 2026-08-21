#!/bin/bash
while ! grep -q A1V4_DONE /workspace/a1v4_main.log 2>/dev/null; do sleep 300; done
export PYTORCH_CUDA_ALLOC_CONF=expandable_segments:True
echo "=== r4 batch32+sqrtLR (单资产最强训练受据移植) $(date -u) ==="
env EPOCHS=24 LR=1.4e-3 DROP=0.2 BATCH=32 /usr/bin/python3 -u /workspace/pod_fast2.py film2 > /workspace/recipe_r4.log 2>&1
tail -2 /workspace/recipe_r4.log
echo "=== r5 ch192 喂饱重测 $(date -u) ==="
env EPOCHS=24 LR=1e-3 DROP=0.2 CHW=192 /usr/bin/python3 -u /workspace/pod_fast2.py film2 > /workspace/recipe_r5.log 2>&1
tail -2 /workspace/recipe_r5.log
echo A1V5_DONE
