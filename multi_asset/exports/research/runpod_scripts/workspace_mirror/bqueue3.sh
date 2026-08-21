#!/bin/bash
while ! grep -q BQUEUE2_DONE /workspace/bqueue2.log 2>/dev/null; do sleep 120; done
for ARM in seed2027 dense; do
  echo "=== ARM3 $ARM start $(date -u) ==="
  env PYTORCH_CUDA_ALLOC_CONF=expandable_segments:True /usr/bin/python3 -u /workspace/pod_arm3.py $ARM > /workspace/arm3_$ARM.log 2>&1
  tail -2 /workspace/arm3_$ARM.log
done
echo BQUEUE3_DONE
