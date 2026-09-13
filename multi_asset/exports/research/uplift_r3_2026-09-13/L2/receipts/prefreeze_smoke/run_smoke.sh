#!/bin/bash
cd /workspace/uplift_r3_2026-09-13/L2_smoke2 || exit 2
for dev in l2_b_build.py l2_b_selftest.py l2_b_fit.py l2_b_null.py l2_b_judge.py; do
  bash devices/run_l2.sh $dev; rc=$?
  echo "SMOKE $dev rc=$rc" >> receipts/SMOKE_CHAIN.txt
  [ $rc -ne 0 ] && break
done
echo "SMOKE_CHAIN_DONE" >> receipts/SMOKE_CHAIN.txt
