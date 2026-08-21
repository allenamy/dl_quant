#!/bin/bash
cd /workspace
rm -f rebuild.lock
/usr/bin/python3 -u pod_rebuild.py > rebuild.log 2>&1 || { echo CHAIN2_REBUILD_FAIL; exit 1; }
/usr/bin/python3 -u verify_cache.py > verify_cache.log 2>&1 || { echo CHAIN2_VERIFY_FAIL; exit 1; }
nohup env PYTORCH_CUDA_ALLOC_CONF=expandable_segments:True /usr/bin/python3 -u pod_d0b.py > d0b.log 2>&1 &
echo CHAIN2_D0B_LAUNCHED
