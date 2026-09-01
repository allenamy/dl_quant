#!/bin/bash
set -u
W=/mnt/storage/private/work_hsy; PD=$W/probe_artifacts
cd $W
for ARM in A1_v2cal A2_hl15 A3_hl7d A4_dmom A5_gap; do
 for S in 42 2027; do
  LOOK=900 WRULE=msharpe CAL=simple LEGS=101 PHI=0.45 FSEED=$S FPRED=f10_V2MAIN_s$S.npy FEMAT=$W/femat_$ARM.npz \
   /root/miniconda3/envs/hsy_v5push/bin/python w10_fundleg.py > $PD/w10_fund_${ARM}_s$S.log 2>&1 \
   || { echo "FAIL $ARM s$S" >> $PD/fundleg_runner.log; exit 1; }
  mv $PD/w10_ablation_series.npz $PD/w10_fund_${ARM}_s$S.npz
  mv $PD/w10_ablation_summary.json $PD/w10_fund_${ARM}_s$S.json
  echo "done $ARM s$S" >> $PD/fundleg_runner.log
 done
done
echo FUNDLEG_RUNS_DONE >> $PD/fundleg_runner.log
