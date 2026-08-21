#!/bin/bash
# B 阶段接力器: 等 D0b 完成 → 四臂顺序淘汰赛 → GPU 不空转
while ! grep -q D0B_DONE /workspace/d0b.log 2>/dev/null; do sleep 120; done
for ARM in revin segate relch fundphase; do
  echo "=== ARM $ARM start $(date -u) ==="
  env PYTORCH_CUDA_ALLOC_CONF=expandable_segments:True /usr/bin/python3 -u /workspace/pod_arm.py $ARM > /workspace/arm_$ARM.log 2>&1
  tail -2 /workspace/arm_$ARM.log
done
echo BQUEUE_DONE
