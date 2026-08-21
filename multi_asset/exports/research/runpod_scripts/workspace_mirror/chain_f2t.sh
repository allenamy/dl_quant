#!/bin/bash
# 按【PID】串行化, 不轮询 GPU —— 修 next_q/f2t 双等待器竞态
while kill -0 36143 2>/dev/null; do sleep 60; done
sleep 30
bash /workspace/f2t_lam0.sh
