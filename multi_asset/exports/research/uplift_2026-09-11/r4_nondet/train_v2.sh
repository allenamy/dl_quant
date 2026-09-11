#!/bin/bash
# P4 -- TRUE same-seed replication of the IN-SERVICE F10/V2MAIN recipe.
# DIFFERENCE FROM r3_xib/train_seeds.sh (and from my own D1..D8, which copied it): **V2=1**.
#   /workspace/pod_f10_train_ext.py L91:  V2 = int(os.environ.get("V2", "0"))
# V2=1 is the composed-chain mode (msharpe leg weights x [model, rev24, fund] inside the training loop,
# L214-217) -- i.e. the "differentiable book loss" object the book actually rides. Every other launcher on
# this pod sets it: pod_accept.sh L8, pod_ple_seq.sh L14/37/40, f11_chain.sh L16, gpu_queue.sh L6.
# The trainer's own report json does NOT record V2, so a replication that reads only the json cannot see it.
set -u
R=/workspace/uplift_2026-09-11/r4_nondet
L=$1
mkdir -p $R/f8_$L/preds $R/f8_$L/results $R/f8_$L/models
ln -sfn /workspace/f8_ext/data $R/f8_$L/data
env V2=1 ARM=V2MAIN SEED=42 COST=3.52 LDD=0.25 AFIX=0 EPOCHS=15 LR=3e-4 \
    F10_DLW=/workspace/dlw_ext F10_OUT=$R/f8_$L \
    /workspace/venv/bin/python /workspace/pod_f10_train_ext.py > $R/logs/train_$L.log 2>&1
echo "TRAIN_RC[$L,V2=1]=$? $(date -u +%FT%TZ)" >> $R/logs/train_status.txt
