#!/bin/bash
while ! grep -q BQUEUE9_DONE /workspace/bqueue9.log 2>/dev/null; do sleep 120; done
for SPEC in 'base 42' 'oi2 42' 'oix 42'; do
  set -- $SPEC
  echo "=== FAST $1 s$2 start $(date -u) ==="
  env SEED=$2 PYTORCH_CUDA_ALLOC_CONF=expandable_segments:True /usr/bin/python3 -u /workspace/pod_fast.py $1 > /workspace/fast_$1_s$2.log 2>&1
  tail -2 /workspace/fast_$1_s$2.log
done
echo BQUEUE10_DONE
