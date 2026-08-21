#!/bin/bash
while ! grep -q BQUEUE21_DONE /workspace/bqueue21.log 2>/dev/null; do sleep 300; done
while [ ! -f /workspace/data/feat51.npz ]; do sleep 120; done
export PYTORCH_CUDA_ALLOC_CONF=expandable_segments:True
echo "=== femb 稀疏嵌入+AutoInt交叉 s42 $(date -u) ==="
env EPOCHS=24 DROP=0.2 /usr/bin/python3 -u /workspace/pod_fast2.py femb > /workspace/break_femb.log 2>&1
tail -2 /workspace/break_femb.log
echo BQUEUE22_DONE
