#!/bin/bash
while ! grep -q BQUEUE4_DONE /workspace/bqueue4.log 2>/dev/null; do sleep 120; done
echo "=== ARM5 xfd s42 start $(date -u) ==="
env PYTORCH_CUDA_ALLOC_CONF=expandable_segments:True /usr/bin/python3 -u /workspace/pod_arm5.py xfd > /workspace/arm5_xfd.log 2>&1
tail -2 /workspace/arm5_xfd.log
if grep -q '录取' /workspace/arm4_prem.log 2>/dev/null; then
  echo "=== ARM5 xfdp s42 start $(date -u) ==="
  env PYTORCH_CUDA_ALLOC_CONF=expandable_segments:True /usr/bin/python3 -u /workspace/pod_arm5.py xfdp > /workspace/arm5_xfdp.log 2>&1
  tail -2 /workspace/arm5_xfdp.log
fi
echo "=== ARM5 xfd s2027 复验 start $(date -u) ==="
env SEED=2027 PYTORCH_CUDA_ALLOC_CONF=expandable_segments:True /usr/bin/python3 -u /workspace/pod_arm5.py xfd > /workspace/arm5_xfd_s2027.log 2>&1
tail -2 /workspace/arm5_xfd_s2027.log
echo BQUEUE5_DONE
