#!/bin/bash
set -u
W=/mnt/storage/private/work_hsy; PD=$W/probe_artifacts; cd $W
run(){ TAG=$1; SEED=$2; shift 2
  env "$@" LOOK=900 WRULE=msharpe CAL=simple LEGS=101 PHI=0.45 FSEED=$SEED FPRED=f10_V2MAIN_s$SEED.npy FTRIM_STAGE=pre FTRIM_MODE=zero FTRIM_LO=-1.0 FTRIM_HI=-0.0010 \
    /root/miniconda3/envs/hsy_v5push/bin/python w10_side_band.py > $PD/w10_band_$TAG.log 2>&1 || { echo "FAIL $TAG" >> $PD/batch9_runner.log; exit 1; }
  mv $PD/w10_ablation_series.npz $PD/w10_band_$TAG.npz; mv $PD/w10_ablation_summary.json $PD/w10_band_$TAG.json; echo "done $TAG" >> $PD/batch9_runner.log; }
run combo_all10z_k80 42 SIDE_KAPPA=8.0
run combo_all10z_k80_s2027 2027 SIDE_KAPPA=8.0
run combo_all10z_k50 42 SIDE_KAPPA=5.0
run combo_all10z_k50_s2027 2027 SIDE_KAPPA=5.0
echo BATCH9_DONE >> $PD/batch9_runner.log
