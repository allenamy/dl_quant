#!/bin/bash
while ! grep -q BQUEUE14_DONE /workspace/bqueue14.log 2>/dev/null; do sleep 120; done
echo "=== FAST2 ty1 s42 start $(date -u) ==="
env PYTORCH_CUDA_ALLOC_CONF=expandable_segments:True /usr/bin/python3 -u /workspace/pod_fast2.py ty1 > /workspace/fast2_ty1.log 2>&1
tail -2 /workspace/fast2_ty1.log
echo BQUEUE15_DONE
