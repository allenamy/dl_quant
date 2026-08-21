#!/bin/bash
while ! grep -q BQUEUE11_DONE /workspace/bqueue11.log 2>/dev/null; do sleep 120; done
echo "=== FAST film2 s42 start $(date -u) ==="
env PYTORCH_CUDA_ALLOC_CONF=expandable_segments:True /usr/bin/python3 -u /workspace/pod_fast.py film2 > /workspace/fast_film2_s42.log 2>&1
tail -2 /workspace/fast_film2_s42.log
echo BQUEUE12_DONE
