#!/bin/bash
# PREREG AMENDMENT 5 A5.2: M-REPRO (derived trainer re-runs fold 202501) then the 24 new monthly folds 202301..202412 in 4 parallel shards (as the original
# v4b run). The GPU must be idle before the M-REPRO launch and before the shard launch; env copied verbatim from launch_mwf_v4b.sh. Writes only under $R/work/mwf_ext.
set -u
R=/workspace/object_b_2026-09-19; D=$R/devices; L=$R/logs; W=$R/work/mwf_ext; PY=/workspace/venv/bin/python
ST=$L/V4_GPU_STATUS.txt; echo "start $(date -u +%FT%TZ) pgid $(ps -o pgid= $$ | tr -d ' ')" > $ST
gpu_idle() { local apps used; apps=$(nvidia-smi --query-compute-apps=pid --format=csv,noheader | grep -c .); used=$(nvidia-smi --query-gpu=memory.used --format=csv,noheader,nounits | head -1 | tr -d ' '); [ "$apps" = "0" ] && [ "$used" -lt 500 ]; }
ENVB="env -i PATH=/usr/bin:/bin HOME=/root LC_CTYPE=C.UTF-8 ARM=V2MAIN V2=1 SEED=42 F10_DLW=/workspace/dlw_v4raw F10_OUT=/workspace/f8_v4 F10_GATE_JSON=/workspace/f8_v4/gates/F10_GATE_RAW.json EMBARGO=1 MWF_TAG=mE1cX7 BEST_EP_FIX=7"
gpu_idle || { echo "STOP before M-REPRO: GPU not idle $(date -u +%FT%TZ)" >> $ST; exit 4; }
mkdir -p $W/repro $W/shard0 $W/shard1 $W/shard2 $W/shard3
$ENVB MWF_OUT=$W/repro MONTHS=202501 nice -n 5 $PY -B $D/pod_f10_train_monthly_ext.py > $L/v4_mrepro.log 2>&1; echo "M-REPRO run rc=$? $(date -u +%FT%TZ)" >> $ST
gpu_idle || { echo "STOP before shards: GPU not idle $(date -u +%FT%TZ)" >> $ST; exit 4; }
MS=(202301 202302 202303 202304 202305 202306 202307 202308 202309 202310 202311 202312 202401 202402 202403 202404 202405 202406 202407 202408 202409 202410 202411 202412)
for k in 0 1 2 3; do
  M=$(for i in "${!MS[@]}"; do [ $((i % 4)) -eq $k ] && printf "%s," ${MS[$i]}; done | sed 's/,$//')
  ( $ENVB MWF_OUT=$W/shard$k MONTHS=$M nice -n 5 $PY -B $D/pod_f10_train_monthly_ext.py > $L/v4_shard$k.log 2>&1; echo "shard$k months $M rc=$? $(date -u +%FT%TZ)" >> $ST ) &
  sleep 60   # stagger the data-load memory peaks
done
wait; echo "DONE $(date -u +%FT%TZ)" >> $ST
