#!/bin/bash
while ! grep -q BQUEUE6_DONE /workspace/bqueue6.log 2>/dev/null; do sleep 120; done
for SPEC in 'xda 2027' 'xd 42' 'xd 2027'; do
  set -- $SPEC
  echo "=== ARM7 $1 s$2 start $(date -u) ==="
  env SEED=$2 PYTORCH_CUDA_ALLOC_CONF=expandable_segments:True /usr/bin/python3 -u /workspace/pod_arm5.py $1 > /workspace/arm7_$1_s$2.log 2>&1
  tail -2 /workspace/arm7_$1_s$2.log
done
echo BQUEUE7_DONE
