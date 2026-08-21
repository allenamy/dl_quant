#!/bin/bash
until grep -q PANEL_DONE /workspace/panel_wide.log 2>/dev/null; do sleep 20; done
cd /workspace && python3 pod_zoo_scan.py > zoo_scan.log 2>&1
echo ZOO_QUEUE_DONE >> /workspace/zoo_scan.log
