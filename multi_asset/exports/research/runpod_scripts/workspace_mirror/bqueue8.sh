#!/bin/bash
while ! grep -q BQUEUE7_DONE /workspace/bqueue7.log 2>/dev/null; do sleep 120; done
for ARM in qh xrk mtcn aux pw ptst itr; do
  echo "=== WAVE $ARM start $(date -u) ==="
  env PYTORCH_CUDA_ALLOC_CONF=expandable_segments:True /usr/bin/python3 -u /workspace/pod_wave.py $ARM > /workspace/wave_$ARM.log 2>&1
  tail -2 /workspace/wave_$ARM.log
done
echo BQUEUE8_DONE
