#!/bin/bash
F=/workspace/data/dlnative_5m_k7_f16.npz
while true; do
  if [ -f $F ]; then
    S1=$(stat -c%s $F); sleep 30; S2=$(stat -c%s $F)
    if [ "$S1" == "$S2" ] && [ "$S1" -gt 600000000 ]; then break; fi
  else sleep 30; fi
done
cd /workspace && nohup python3 pod_d0b.py > d0b.log 2>&1 &
echo FIRED at $(date -u)
