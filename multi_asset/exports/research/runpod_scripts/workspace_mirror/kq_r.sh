#!/bin/bash
while pgrep -f '[p]od_k3c' > /dev/null; do sleep 60; done
sleep 10
/usr/bin/python3 -u /workspace/pod_k3r.py > /workspace/k3r_clean.log 2>&1
echo KQR_DONE
