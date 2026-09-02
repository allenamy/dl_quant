#!/bin/bash
set -u
W=/mnt/storage/private/work_hsy; PD=$W/probe_artifacts; cd $W
run(){ TAG=$1; shift
  env "$@" WRULE=msharpe CAL=simple LEGS=101 PHI=0.45 FSEED=42 FPRED=f10_V2MAIN_s42.npy \
    /root/miniconda3/envs/hsy_v5push/bin/python w10_seat.py > $PD/w10_seat_$TAG.log 2>&1 || { echo "FAIL $TAG" >> $PD/look_runner.log; exit 1; }
  mv $PD/w10_ablation_series.npz $PD/w10_seat_$TAG.npz; mv $PD/w10_ablation_summary.json $PD/w10_seat_$TAG.json; echo "done $TAG" >> $PD/look_runner.log; }
run look450 LOOK=450
run look1800 LOOK=1800
run look300 LOOK=300
echo LOOK_DONE >> $PD/look_runner.log
