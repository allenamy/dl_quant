#!/bin/bash
# P4 item 1: determinism-regime probe. $1=label $2=mode $3=EPOCHS
#   off  = nothing changed (in-service regime)
#   cw   = ONLY CUBLAS_WORKSPACE_CONFIG=:4096:8 (no torch flag changed)
#   full = use_deterministic_algorithms(True) + cudnn.deterministic + TF32 off + CUBLAS_WORKSPACE_CONFIG=:4096:8
#   warn = use_deterministic_algorithms(True, warn_only=True)  -- enumeration only
# Everything else is the IN-SERVICE recipe verbatim; EPOCHS is the only recipe knob varied (labelled).
set -u
R=/workspace/uplift_2026-09-11/r4_nondet
L=$1; M=$2; E=$3
BASE="ARM=V2MAIN SEED=42 COST=3.52 LDD=0.25 AFIX=0 EPOCHS=$E LR=3e-4 F10_DLW=/workspace/dlw_ext F10_OUT=$R/f8_$L"
case "$M" in
  off)  EXTRA="DETMODE=off" ;;
  cw)   EXTRA="DETMODE=off CUBLAS_WORKSPACE_CONFIG=:4096:8" ;;
  full) EXTRA="DETMODE=full CUBLAS_WORKSPACE_CONFIG=:4096:8" ;;
  warn) EXTRA="DETMODE=warn" ;;
  tf32) EXTRA="DETMODE=tf32" ;;
  *) echo "bad mode $M"; exit 2 ;;
esac
mkdir -p $R/f8_$L/preds $R/f8_$L/results $R/f8_$L/models
ln -sfn /workspace/f8_ext/data $R/f8_$L/data
env $BASE $EXTRA /workspace/venv/bin/python $R/det_wrap.py > $R/logs/probe_$L.log 2>&1
echo "PROBE_RC[$L,$M,ep$E]=$? $(date -u +%FT%TZ)" >> $R/logs/train_status.txt
