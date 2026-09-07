#!/bin/bash
set -u
W=/mnt/storage/private/work_hsy; PD=$W/probe_artifacts; cd $W
run(){ TAG=$1; SEED=$2; shift 2
  env "$@" LOOK=900 WRULE=msharpe CAL=simple LEGS=101 PHI=0.45 FSEED=$SEED FPRED=f10_V2MAIN_s$SEED.npy \
    /root/miniconda3/envs/hsy_v5push/bin/python w10_ftrim_band.py > $PD/w10_band_$TAG.log 2>&1 || { echo "FAIL $TAG" >> $PD/band_all10_runner.log; exit 1; }
  mv $PD/w10_ablation_series.npz $PD/w10_band_$TAG.npz; mv $PD/w10_ablation_summary.json $PD/w10_band_$TAG.json; echo "done $TAG" >> $PD/band_all10_runner.log; }
run pre_all10_zero 42 FTRIM_STAGE=pre FTRIM_MODE=zero FTRIM_LO=-1.0 FTRIM_HI=-0.0010
run pre_all10_zero_s2027 2027 FTRIM_STAGE=pre FTRIM_MODE=zero FTRIM_LO=-1.0 FTRIM_HI=-0.0010
run pre_deep60_zero_s2027 2027 FTRIM_STAGE=pre FTRIM_MODE=zero FTRIM_LO=-1.0 FTRIM_HI=-0.0060
echo BAND_ALL10_DONE >> $PD/band_all10_runner.log
