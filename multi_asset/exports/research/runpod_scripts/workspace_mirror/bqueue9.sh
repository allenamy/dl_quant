#!/bin/bash
while ! grep -q BQUEUE8_DONE /workspace/bqueue8.log 2>/dev/null; do sleep 120; done
echo "=== WAVE oi start $(date -u) ==="
env PYTORCH_CUDA_ALLOC_CONF=expandable_segments:True /usr/bin/python3 -u /workspace/pod_wave.py oi > /workspace/wave_oi.log 2>&1
tail -2 /workspace/wave_oi.log
echo BQUEUE9_DONE
