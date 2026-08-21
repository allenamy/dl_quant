#!/bin/bash
until grep -q KCURVE_RESID_DONE /workspace/kcurveR_K400_s42.log 2>/dev/null; do sleep 15; done
cd /workspace && python3 pod_orthjudge.py > orthjudge.log 2>&1
