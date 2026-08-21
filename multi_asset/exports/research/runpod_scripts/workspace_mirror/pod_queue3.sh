#!/bin/bash
# 队列3: queue2(basis+attrib)完成后 → 残差第四腿(§27). 完成后 pod 可停.
cd /workspace
L="/workspace/queue3_$(date -u +%s).log"
ln -sf "$L" /workspace/queue3.log
for i in $(seq 1 360); do
  grep -q ATTRIB_DONE queue2.log 2>/dev/null && break
  sleep 30
done
grep -q ATTRIB_DONE queue2.log || { echo Q3_ABORT_Q2_TIMEOUT >> "$L"; exit 1; }
echo "=== resid4 $(date -u +%FT%TZ)" >> "$L"
python3 pod_resid4.py >> "$L" 2>&1
grep -q RESID4_DONE "$L" || echo Q3_RESID4_ERROR >> "$L"
echo "=== queue3 done, POD_CAN_PAUSE $(date -u +%FT%TZ)" >> "$L"
