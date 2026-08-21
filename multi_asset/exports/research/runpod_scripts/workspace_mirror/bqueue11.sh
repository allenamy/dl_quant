#!/bin/bash
while ! grep -q BQUEUE10_DONE /workspace/bqueue10.log 2>/dev/null; do sleep 120; done
echo "=== FAST sgn s42 start $(date -u) ==="
env PYTORCH_CUDA_ALLOC_CONF=expandable_segments:True /usr/bin/python3 -u /workspace/pod_fast.py sgn > /workspace/fast_sgn_s42.log 2>&1
tail -2 /workspace/fast_sgn_s42.log
/usr/bin/python3 -u /workspace/score_rules.py > /workspace/score_rules.log 2>&1
tail -6 /workspace/score_rules.log
echo BQUEUE11_DONE
