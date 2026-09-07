#!/bin/bash
set -u
W=/mnt/storage/private/work_hsy; PD=$W/probe_artifacts; cd $W
run(){ DEV=$1; OUTN=$2; SEED=$3; shift 3
  env "$@" W3FIX="0.21,0,0.79" LOOK=900 WRULE=msharpe CAL=simple LEGS=101 PHI=0.45 FSEED=$SEED FPRED=f10_V2MAIN_s$SEED.npy \
    /root/miniconda3/envs/hsy_v5push/bin/python $DEV > $PD/$OUTN.log 2>&1 || { echo "FAIL $OUTN" >> $PD/batch10_runner.log; exit 1; }
  mv $PD/w10_ablation_series.npz $PD/$OUTN.npz; mv $PD/w10_ablation_summary.json $PD/$OUTN.json; echo "done $OUTN" >> $PD/batch10_runner.log; }
run w10_side.py w10_canonfix_s42 42 SIDE_KAPPA=1.0
run w10_side.py w10_canonfix_s2027 2027 SIDE_KAPPA=1.0
run w10_side.py w10_seat_fix_side_k30 42 SIDE_KAPPA=3.0
run w10_side.py w10_seat_fix_side_k80 42 SIDE_KAPPA=8.0
run w10_side.py w10_seat_fix_side_k30_s2027 2027 SIDE_KAPPA=3.0
run w10_side.py w10_seat_fix_side_k80_s2027 2027 SIDE_KAPPA=8.0
run w10_side_band.py w10_band_fix_all10z 42 SIDE_KAPPA=1.0 FTRIM_STAGE=pre FTRIM_MODE=zero FTRIM_LO=-1.0 FTRIM_HI=-0.0010
run w10_side_band.py w10_band_fix_combo_k30 42 SIDE_KAPPA=3.0 FTRIM_STAGE=pre FTRIM_MODE=zero FTRIM_LO=-1.0 FTRIM_HI=-0.0010
echo BATCH10_DONE >> $PD/batch10_runner.log
