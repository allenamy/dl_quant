#!/bin/bash
# s2027 双种子确认(PREREG_xregime 第二批录取候选): 与 s42 runner 逐字同, 仅 FSEED/FPRED/TAG 后缀改
set -u
W=/mnt/storage/private/work_hsy; PD=$W/probe_artifacts; cd $W
run(){ TAG=$1; shift
  env "$@" LOOK=900 WRULE=msharpe CAL=simple LEGS=101 PHI=0.45 FSEED=2027 FPRED=f10_V2MAIN_s2027.npy \
    /root/miniconda3/envs/hsy_v5push/bin/python w10_ftrim_band.py > $PD/w10_band_$TAG.log 2>&1 || { echo "FAIL $TAG" >> $PD/band_pre_s2027_runner.log; exit 1; }
  mv $PD/w10_ablation_series.npz $PD/w10_band_$TAG.npz; mv $PD/w10_ablation_summary.json $PD/w10_band_$TAG.json; echo "done $TAG" >> $PD/band_pre_s2027_runner.log; }
run pre_m30m10_zero_s2027 FTRIM_STAGE=pre FTRIM_MODE=zero FTRIM_LO=-0.0030 FTRIM_HI=-0.0010
run pre_m30m10_half_s2027 FTRIM_STAGE=pre FTRIM_MODE=half FTRIM_LO=-0.0030 FTRIM_HI=-0.0010
run pre_m60m10_zero_s2027 FTRIM_STAGE=pre FTRIM_MODE=zero FTRIM_LO=-0.0060 FTRIM_HI=-0.0010
echo BAND_PRE_S2027_DONE >> $PD/band_pre_s2027_runner.log
