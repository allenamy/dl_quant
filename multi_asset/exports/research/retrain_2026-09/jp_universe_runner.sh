#!/bin/bash
set -u
W=/mnt/storage/private/work_hsy; PD=$W/probe_artifacts
cd $W
for U in U0 U1 U2; do
 for S in 42 2027; do
  LOOK=900 WRULE=msharpe CAL=simple LEGS=101 PHI=0.45 FSEED=$S FPRED=f10_V2MAIN_s$S.npy UMASK_NPZ=$W/umask_$U.npz \
   /root/miniconda3/envs/hsy_v5push/bin/python w10_universe.py > $PD/w10_uni_${U}_s$S.log 2>&1 \
   || { echo "FAIL $U s$S" >> $PD/uni_runner.log; exit 1; }
  mv $PD/w10_ablation_series.npz $PD/w10_uni_${U}_s$S.npz
  mv $PD/w10_ablation_summary.json $PD/w10_uni_${U}_s$S.json
  echo "done $U s$S" >> $PD/uni_runner.log
 done
done
echo UNIVERSE_RUNS_DONE >> $PD/uni_runner.log
