#!/bin/bash
set -u
W=/mnt/storage/private/work_hsy; PD=$W/probe_artifacts; cd $W
run(){ TAG=$1; shift
  env "$@" LOOK=900 CAL=simple LEGS=101 PHI=0.45 FSEED=42 FPRED=f10_V2MAIN_s42.npy \
    /root/miniconda3/envs/hsy_v5push/bin/python w10_seat.py > $PD/w10_seat_$TAG.log 2>&1 || { echo "FAIL $TAG" >> $PD/seat_runner.log; exit 1; }
  mv $PD/w10_ablation_series.npz $PD/w10_seat_$TAG.npz; mv $PD/w10_ablation_summary.json $PD/w10_seat_$TAG.json; echo "done $TAG" >> $PD/seat_runner.log; }
run eq WRULE=eq
run iv WRULE=iv
run cap70 WRULE=msharpe WCAP=0.70
run cap60 WRULE=msharpe WCAP=0.60
run flr15 WRULE=msharpe WFLOOR=0.15
run flr25 WRULE=msharpe WFLOOR=0.25
echo SEAT_RUNS_DONE >> $PD/seat_runner.log
