#!/bin/bash
while ! grep -q BQUEUE19_DONE /workspace/bqueue19.log 2>/dev/null; do sleep 300; done
export PYTORCH_CUDA_ALLOC_CONF=expandable_segments:True
echo "=== IST 交错时空编码器 $(date -u) ==="
env IST=1 EPOCHS=8 /usr/bin/python3 -u /workspace/pod_fast2.py film2 > /workspace/break_ist.log 2>&1
tail -2 /workspace/break_ist.log
echo "=== relf 关系型特征 $(date -u) ==="
env EPOCHS=8 /usr/bin/python3 -u /workspace/pod_fast2.py relf > /workspace/break_relf.log 2>&1
tail -2 /workspace/break_relf.log
echo BQUEUE20_DONE
