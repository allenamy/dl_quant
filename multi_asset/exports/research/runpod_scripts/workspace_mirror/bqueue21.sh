#!/bin/bash
while ! grep -q BQUEUE20_DONE /workspace/bqueue20.log 2>/dev/null; do sleep 300; done
export PYTORCH_CUDA_ALLOC_CONF=expandable_segments:True
echo "=== 表征组合 resd+midx s42 $(date -u) ==="
env RESD=1 MIDX=1 EPOCHS=24 DROP=0.2 /usr/bin/python3 -u /workspace/pod_fast2.py film2 > /workspace/repr_combo.log 2>&1
tail -2 /workspace/repr_combo.log
echo "=== 组合 s2027 复验 $(date -u) ==="
env SEED=2027 RESD=1 MIDX=1 EPOCHS=24 DROP=0.2 /usr/bin/python3 -u /workspace/pod_fast2.py film2 > /workspace/repr_combo_s2027.log 2>&1
tail -2 /workspace/repr_combo_s2027.log
echo BQUEUE21_DONE
