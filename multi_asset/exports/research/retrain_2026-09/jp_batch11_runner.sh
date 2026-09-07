#!/bin/bash
set -u
W=/mnt/storage/private/work_hsy; PD=$W/probe_artifacts; cd $W
run(){ OUTN=$1; SEED=$2; K=$3
  env W3FIX="0.21,0,0.79" SIDE_KAPPA=$K LOOK=900 WRULE=msharpe CAL=simple LEGS=101 PHI=0.45 FSEED=$SEED FPRED=f10_V2MAIN_s$SEED.npy \
    /root/miniconda3/envs/hsy_v5push/bin/python w10_side.py > $PD/$OUTN.log 2>&1 || { echo "FAIL $OUTN" >> $PD/batch11_runner.log; exit 1; }
  mv $PD/w10_ablation_series.npz $PD/$OUTN.npz; mv $PD/w10_ablation_summary.json $PD/$OUTN.json; echo "done $OUTN" >> $PD/batch11_runner.log; }
run w10_seat_fix_side_k15 42 1.5
run w10_seat_fix_side_k20 42 2.0
run w10_seat_fix_side_k15_s2027 2027 1.5
run w10_seat_fix_side_k20_s2027 2027 2.0
echo BATCH11_DONE >> $PD/batch11_runner.log
