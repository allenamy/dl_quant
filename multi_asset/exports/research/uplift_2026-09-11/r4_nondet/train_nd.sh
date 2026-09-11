#!/bin/bash
# P4 DRAW: a SAME-SEED (42) re-training of the IN-SERVICE F10/V2MAIN recipe.
# Invocation copied VERBATIM from r3_xib/train_seeds.sh; the ONLY difference is F10_OUT (a per-draw tree,
# because every draw writes the same filename f10_V2MAIN_s42.npy) and SEED is pinned to 42 instead of varying.
# Device: /workspace/pod_f10_train_ext.py sha256 93cc2cdf925a1dada9190a5d86664d28c811d9ba0ecf3eaf377d54fc554f2598
# Recipe VERBATIM from f8_ext/results/f10_V2MAIN_s42.json (the IN-SERVICE artifact):
#   arm V2MAIN cost 3.52 ldd 0.25 afix 0 epochs 15 lr 3e-4 win 96 burn 24 stride 48 embargo 60
# Inputs: F10_DLW=/workspace/dlw_ext  <- the lineage the IN-SERVICE s42 pred came from. This is a deliberate,
#   labelled exception to the v4 caliber pin: the object under study IS the in-service training run, and a
#   re-draw of it requires its own inputs. NOTHING from this tree is used as a v4 accounting number; the
#   book-layer evaluation downstream rides the pinned v4 device and the v4 axis.
set -u
R=/workspace/uplift_2026-09-11/r4_nondet
L=$1
env ARM=V2MAIN SEED=42 COST=3.52 LDD=0.25 AFIX=0 EPOCHS=15 LR=3e-4 \
    F10_DLW=/workspace/dlw_ext F10_OUT=$R/f8_$L \
    /workspace/venv/bin/python /workspace/pod_f10_train_ext.py > $R/logs/train_$L.log 2>&1
echo "TRAIN_RC[$L]=$? $(date -u +%FT%TZ)" >> $R/logs/train_status.txt
