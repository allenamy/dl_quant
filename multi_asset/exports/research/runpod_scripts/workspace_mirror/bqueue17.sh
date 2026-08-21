#!/bin/bash
while ! grep -q BQUEUE16_DONE /workspace/bqueue16.log 2>/dev/null; do sleep 180; done
for ARM in ordctr xdeep; do
  echo "=== MOAT $ARM s42 start $(date -u) ==="
  env PYTORCH_CUDA_ALLOC_CONF=expandable_segments:True /usr/bin/python3 -u /workspace/pod_fast2.py $ARM > /workspace/fast2_$ARM.log 2>&1
  tail -2 /workspace/fast2_$ARM.log
done
echo BQUEUE17_DONE
