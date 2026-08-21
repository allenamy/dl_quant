#!/bin/bash
while ! grep -q BQUEUE12_DONE /workspace/bqueue12.log 2>/dev/null; do sleep 120; done
for ARM in hyb proto moe; do
  echo "=== FAST2 $ARM s42 start $(date -u) ==="
  env PYTORCH_CUDA_ALLOC_CONF=expandable_segments:True /usr/bin/python3 -u /workspace/pod_fast2.py $ARM > /workspace/fast2_$ARM.log 2>&1
  tail -2 /workspace/fast2_$ARM.log
done
echo BQUEUE13_DONE
