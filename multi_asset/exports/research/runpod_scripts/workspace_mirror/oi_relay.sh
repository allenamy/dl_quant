#!/bin/bash
while ! grep -q METRICS_DL_DONE /workspace/metrics_dl.log 2>/dev/null; do sleep 300; done
rm -f /workspace/oi.lock
/usr/bin/python3 -u /workspace/pod_build_oi.py > /workspace/oi_build.log 2>&1
tail -1 /workspace/oi_build.log
