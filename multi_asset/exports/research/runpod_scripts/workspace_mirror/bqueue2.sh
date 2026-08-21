#!/bin/bash
while ! grep -q BQUEUE_DONE /workspace/bqueue.log 2>/dev/null; do sleep 120; done
for ARM in xattn film huber dcnv2; do
  echo "=== ARM2 $ARM start $(date -u) ==="
  env PYTORCH_CUDA_ALLOC_CONF=expandable_segments:True /usr/bin/python3 -u /workspace/pod_arm2.py $ARM > /workspace/arm2_$ARM.log 2>&1
  tail -2 /workspace/arm2_$ARM.log
done
echo BQUEUE2_DONE
