#!/bin/bash
# chain_train.sh — identity receipts first (gate), then KR then KC sequentially (each ≤ 12 threads), then the replay arms; heartbeat line every 60 s in logs/heartbeat.log (liveness probe = training PID alive).
ROOT=/workspace/review_scratch/cadence_seats/axisA_incremental; cd $ROOT
echo "CHAIN_START $(date -u +%FT%TZ)" >> logs/chain_train.log
( while true; do echo "HB $(date -u +%FT%TZ) load $(cut -d' ' -f1-3 /proc/loadavg) train_pids $(pgrep -f 'train_incremental.py' | tr '\n' ' ')" >> logs/heartbeat.log; sleep 60; done ) & HBPID=$!
bash run_train.sh ident >> logs/chain_train.log 2>&1 || { echo "ABORT ident rc!=0 $(date -u +%FT%TZ)" >> logs/chain_train.log; kill $HBPID; exit 1; }
grep -q "IDENTITY_DONE all_identities_hold True" logs/train_ident.log || { echo "ABORT identity receipts do not all hold $(date -u +%FT%TZ)" >> logs/chain_train.log; kill $HBPID; exit 1; }
bash run_train.sh KR >> logs/chain_train.log 2>&1 || { echo "ABORT KR rc!=0 $(date -u +%FT%TZ)" >> logs/chain_train.log; kill $HBPID; exit 1; }
bash run_train.sh KC >> logs/chain_train.log 2>&1 || { echo "ABORT KC rc!=0 $(date -u +%FT%TZ)" >> logs/chain_train.log; kill $HBPID; exit 1; }
echo "TRAIN_DONE $(date -u +%FT%TZ)" >> logs/chain_train.log
bash run_arms_inc.sh >> logs/chain_train.log 2>&1
kill $HBPID; echo "CHAIN_DONE $(date -u +%FT%TZ)" >> logs/chain_train.log
