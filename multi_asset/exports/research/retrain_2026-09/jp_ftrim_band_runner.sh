#!/bin/bash
set -u
W=/mnt/storage/private/work_hsy; PD=$W/probe_artifacts; cd $W
run(){ TAG=$1; shift
  env "$@" LOOK=900 WRULE=msharpe CAL=simple LEGS=101 PHI=0.45 FSEED=42 FPRED=f10_V2MAIN_s42.npy \
    /root/miniconda3/envs/hsy_v5push/bin/python w10_ftrim_band.py > $PD/w10_band_$TAG.log 2>&1 || { echo "FAIL $TAG" >> $PD/band_runner.log; exit 1; }
  mv $PD/w10_ablation_series.npz $PD/w10_band_$TAG.npz; mv $PD/w10_ablation_summary.json $PD/w10_band_$TAG.json; echo "done $TAG" >> $PD/band_runner.log; }
run m30m10_half FTRIM_MODE=half FTRIM_LO=-0.0030 FTRIM_HI=-0.0010
run m30m10_zero FTRIM_MODE=zero FTRIM_LO=-0.0030 FTRIM_HI=-0.0010
run m10z_half  FTRIM_MODE=half FTRIM_LO=-0.0010 FTRIM_HI=0.0
run m60m10_half FTRIM_MODE=half FTRIM_LO=-0.0060 FTRIM_HI=-0.0010
echo BAND_RUNS_DONE >> $PD/band_runner.log
