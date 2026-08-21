#!/bin/bash
# 等 GPU 降到 <=2 臂再起(留余量), 按数量而非文本
while [ $(nvidia-smi --query-compute-apps=pid --format=csv,noheader | wc -l) -ge 3 ]; do sleep 60; done
bash /workspace/frz.sh
