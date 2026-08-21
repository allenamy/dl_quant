#!/bin/bash
# 链2: 只重跑 slow(IC门) + extweek 判官. 复用已完成的 cache/panel/fea 产物.
cd /workspace
L="/workspace/ext_chain2_$(date -u +%s).log"
ln -sf "$L" /workspace/ext_chain2.log
echo "=== chain2 start $(date -u +%FT%TZ)" >> "$L"
python3 pod_slow_ext.py >> "$L" 2>&1
grep -q SLOW_EXT_DONE "$L" || { echo ABORT_SLOW >> "$L"; exit 1; }
python3 pod_extweek.py >> "$L" 2>&1
grep -q EXTWEEK_DONE "$L" || { echo ABORT_EXTWEEK >> "$L"; exit 1; }
echo "=== chain2 ALL_DONE $(date -u +%FT%TZ)" >> "$L"
