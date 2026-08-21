#!/bin/bash
while ! grep -q BQUEUE3_DONE /workspace/bqueue3.log 2>/dev/null; do sleep 120; done
for ARM in xf prem apool; do
  echo "=== ARM4 $ARM start $(date -u) ==="
  env PYTORCH_CUDA_ALLOC_CONF=expandable_segments:True /usr/bin/python3 -u /workspace/pod_arm4.py $ARM > /workspace/arm4_$ARM.log 2>&1
  tail -2 /workspace/arm4_$ARM.log
done
echo BQUEUE4_DONE
