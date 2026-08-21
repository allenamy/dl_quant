#!/bin/bash
while ! grep -q A1V5_DONE /workspace/a1v5_main.log 2>/dev/null; do sleep 300; done
export PYTORCH_CUDA_ALLOC_CONF=expandable_segments:True
echo "=== resd 残差连接解锁 $(date -u) ==="
env RESD=1 EPOCHS=24 DROP=0.2 /usr/bin/python3 -u /workspace/pod_fast2.py film2 > /workspace/repr_resd.log 2>&1
tail -2 /workspace/repr_resd.log
echo "=== midx 中层跨资产注意力 $(date -u) ==="
env MIDX=1 EPOCHS=24 DROP=0.2 /usr/bin/python3 -u /workspace/pod_fast2.py film2 > /workspace/repr_midx.log 2>&1
tail -2 /workspace/repr_midx.log
echo A1V6_DONE
