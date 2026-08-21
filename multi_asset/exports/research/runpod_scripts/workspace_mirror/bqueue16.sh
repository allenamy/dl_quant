#!/bin/bash
while ! grep -q A1F_DONE /workspace/a1_queue2.log 2>/dev/null; do sleep 180; done
echo "=== FAST2 ctxk s42 start $(date -u) ==="
env PYTORCH_CUDA_ALLOC_CONF=expandable_segments:True /usr/bin/python3 -u /workspace/pod_fast2.py ctxk > /workspace/fast2_ctxk.log 2>&1
tail -2 /workspace/fast2_ctxk.log
echo BQUEUE16_DONE
