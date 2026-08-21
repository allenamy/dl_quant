#!/bin/bash
while ! grep -q BQUEUE5_DONE /workspace/bqueue5.log 2>/dev/null; do sleep 120; done
for SPEC in 'xfda 42' 'xfda 2027' 'xda 42' 'fda 42' 'xfa 42'; do
  set -- $SPEC
  echo "=== ARM6 $1 s$2 start $(date -u) ==="
  env SEED=$2 PYTORCH_CUDA_ALLOC_CONF=expandable_segments:True /usr/bin/python3 -u /workspace/pod_arm5.py $1 > /workspace/arm6_$1_s$2.log 2>&1
  tail -2 /workspace/arm6_$1_s$2.log
done
echo BQUEUE6_DONE
