#!/bin/bash
# 队列2: navfloor_carry 完成后 → basis 门(双跑) → 2024 归因. 串行防 CPU 争抢.
cd /workspace
L="/workspace/queue2_$(date -u +%s).log"
ln -sf "$L" /workspace/queue2.log
for i in $(seq 1 240); do
  grep -q NAVFLOOR_CARRY_DONE navfloor_carry.log 2>/dev/null && break
  sleep 30
done
grep -q NAVFLOOR_CARRY_DONE navfloor_carry.log || { echo Q2_ABORT_NAVFLOOR_TIMEOUT >> "$L"; exit 1; }
echo "=== basis gate $(date -u +%FT%TZ)" >> "$L"
python3 pod_basis_gate.py >> "$L" 2>&1
grep -q BASIS_DONE "$L" || echo Q2_BASIS_ERROR >> "$L"
echo "=== attrib $(date -u +%FT%TZ)" >> "$L"
python3 pod_2024_attrib.py >> "$L" 2>&1
grep -q ATTRIB_DONE "$L" || echo Q2_ATTRIB_ERROR >> "$L"
echo "=== queue2 done $(date -u +%FT%TZ)" >> "$L"
