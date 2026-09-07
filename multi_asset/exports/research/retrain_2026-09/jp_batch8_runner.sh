#!/bin/bash
set -u
W=/mnt/storage/private/work_hsy; PD=$W/probe_artifacts; cd $W; PY=/root/miniconda3/envs/hsy_v5push/bin/python
$PY jp_femat_tr.py > $PD/femat_tr.log 2>&1 || { echo "FAIL femat" >> $PD/batch8_runner.log; exit 1; }
run(){ TAG=$1; SEED=$2; FM=$3
  env LOOK=900 WRULE=msharpe CAL=simple LEGS=101 PHI=0.45 FSEED=$SEED FPRED=f10_V2MAIN_s$SEED.npy FEMAT=$PD/$FM $PY w10_fundleg.py > $PD/w10_seat_$TAG.log 2>&1 || { echo "FAIL $TAG" >> $PD/batch8_runner.log; exit 1; }
  mv $PD/w10_ablation_series.npz $PD/w10_seat_$TAG.npz; mv $PD/w10_ablation_summary.json $PD/w10_seat_$TAG.json; echo "done $TAG" >> $PD/batch8_runner.log; }
run fundtr_l01 42 femat_tr_l01.npz
run fundtr_l02 42 femat_tr_l02.npz
run fundtr_l03 42 femat_tr_l03.npz
echo BATCH8_DONE >> $PD/batch8_runner.log
