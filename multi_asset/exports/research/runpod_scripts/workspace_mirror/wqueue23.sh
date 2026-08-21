#!/bin/bash
# 宽宇宙探针队列: 等 femb 收尾(bqueue22 全链末端)后独占 GPU
while ! grep -q FAST_femb_DONE /workspace/break_femb.log 2>/dev/null; do sleep 120; done
sleep 30
/usr/bin/python3 -u /workspace/pod_wide.py > /workspace/wide_s42.log 2>&1
tail -3 /workspace/wide_s42.log
echo WQUEUE23_DONE
