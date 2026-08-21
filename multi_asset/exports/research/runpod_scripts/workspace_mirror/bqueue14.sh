#!/bin/bash
while ! grep -q BQUEUE13_DONE /workspace/bqueue13.log 2>/dev/null; do sleep 120; done
for SPEC in 'sf 42' 'sf 2027' 'film2 2027' 'sgn 2027'; do
  set -- $SPEC
  echo "=== FAST2 $1 s$2 start $(date -u) ==="
  env SEED=$2 PYTORCH_CUDA_ALLOC_CONF=expandable_segments:True /usr/bin/python3 -u /workspace/pod_fast2.py $1 > /workspace/fast2_$1_s$2.log 2>&1
  tail -2 /workspace/fast2_$1_s$2.log
done
echo BQUEUE14_DONE
