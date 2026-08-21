#!/bin/bash
while ! grep -q A1F_DONE /workspace/a1_queue2.log 2>/dev/null; do sleep 300; done
while ! grep -q BQUEUE16_DONE /workspace/bqueue16.log 2>/dev/null; do sleep 180; done
for SPEC in 'nullck 8 1e-3 0 dlnull' 'film2 24 1e-3 0.2 r1' 'film2 24 6e-4 0.2 r2' 'film2 32 1e-3 0.3 r3'; do
  set -- $SPEC
  echo "=== RECIPE $1 E=$2 LR=$3 D=$4 tag=$5 $(date -u) ==="
  env EPOCHS=$2 LR=$3 DROP=$4 PYTORCH_CUDA_ALLOC_CONF=expandable_segments:True /usr/bin/python3 -u /workspace/pod_fast2.py $1 > /workspace/recipe_$5.log 2>&1
  tail -2 /workspace/recipe_$5.log
done
echo BQUEUE18_DONE
