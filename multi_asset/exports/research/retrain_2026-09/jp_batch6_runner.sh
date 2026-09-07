#!/bin/bash
set -u
W=/mnt/storage/private/work_hsy; PD=$W/probe_artifacts; cd $W
run(){ DEV=$1; PFX=$2; TAG=$3; SEED=$4; shift 4
  env "$@" LOOK=900 WRULE=msharpe CAL=simple LEGS=101 PHI=0.45 FSEED=$SEED FPRED=f10_V2MAIN_s$SEED.npy \
    /root/miniconda3/envs/hsy_v5push/bin/python $DEV > $PD/${PFX}_$TAG.log 2>&1 || { echo "FAIL $TAG" >> $PD/batch6_runner.log; exit 1; }
  mv $PD/w10_ablation_series.npz $PD/${PFX}_$TAG.npz; mv $PD/w10_ablation_summary.json $PD/${PFX}_$TAG.json; echo "done $TAG" >> $PD/batch6_runner.log; }
run w10_side.py w10_seat side_k15_s2027 2027 SIDE_KAPPA=1.5
run w10_side.py w10_seat side_k20_s2027 2027 SIDE_KAPPA=2.0
run w10_side.py w10_seat side_k30 42 SIDE_KAPPA=3.0
run w10_side.py w10_seat side_k30_s2027 2027 SIDE_KAPPA=3.0
run w10_side_band.py w10_band combo_all10z_k20 42 SIDE_KAPPA=2.0 FTRIM_STAGE=pre FTRIM_MODE=zero FTRIM_LO=-1.0 FTRIM_HI=-0.0010
run w10_side_band.py w10_band combo_all10z_k20_s2027 2027 SIDE_KAPPA=2.0 FTRIM_STAGE=pre FTRIM_MODE=zero FTRIM_LO=-1.0 FTRIM_HI=-0.0010
echo BATCH6_DONE >> $PD/batch6_runner.log
