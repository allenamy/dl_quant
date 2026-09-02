#!/bin/bash
set -u
W=/mnt/storage/private/work_hsy; PD=$W/probe_artifacts; cd $W
run(){ TAG=$1; shift
  env "$@" LOOK=900 WRULE=msharpe CAL=simple LEGS=101 PHI=0.45 FSEED=42 FPRED=f10_V2MAIN_s42.npy \
    /root/miniconda3/envs/hsy_v5push/bin/python w10_side.py > $PD/w10_seat_$TAG.log 2>&1 || { echo "FAIL $TAG" >> $PD/side_runner.log; exit 1; }
  mv $PD/w10_ablation_series.npz $PD/w10_seat_$TAG.npz; mv $PD/w10_ablation_summary.json $PD/w10_seat_$TAG.json; echo "done $TAG" >> $PD/side_runner.log; }
run side_k15 SIDE_KAPPA=1.5
run side_k20 SIDE_KAPPA=2.0
run side_k05 SIDE_KAPPA=0.5
echo SIDE_DONE >> $PD/side_runner.log
