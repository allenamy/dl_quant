#!/bin/bash
R6=/workspace/uplift_2026-09-11/r6
PY=/workspace/venv/bin/python
until [ -f $R6/dl/klines_dl_receipt.json ]; do sleep 30; done
echo "[$(date -u +%H:%M:%SZ)] klines done -> funding" >> $R6/logs/super.log
$PY $R6/r6_fetch_funding.py > $R6/logs/fetch_funding.log 2>&1
echo "[$(date -u +%H:%M:%SZ)] funding rc=$? -> chain" >> $R6/logs/super.log
bash $R6/r6_chain.sh >> $R6/logs/super.log 2>&1
echo "[$(date -u +%H:%M:%SZ)] chain rc=$?" >> $R6/logs/super.log
