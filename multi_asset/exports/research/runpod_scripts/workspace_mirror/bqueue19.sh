#!/bin/bash
while ! grep -q A1V6_DONE /workspace/a1v6_main.log 2>/dev/null; do sleep 300; done
export PYTORCH_CUDA_ALLOC_CONF=expandable_segments:True
for ARM in tvol tmed; do
  echo "=== B1 标签降噪 $ARM $(date -u) ==="
  env EPOCHS=8 /usr/bin/python3 -u /workspace/pod_fast2.py $ARM > /workspace/label_$ARM.log 2>&1
  tail -2 /workspace/label_$ARM.log
done
echo BQUEUE19_DONE
