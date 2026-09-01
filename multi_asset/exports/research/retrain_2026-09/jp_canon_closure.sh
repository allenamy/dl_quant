#!/bin/bash
# 终极闭环 R1: 原始正典 preds 三种子 → w10 hardened(逐字), 期望复现候选 §2 净/锚。
set -u
W=/mnt/storage/private/work_hsy; PD=$W/probe_artifacts
cd $W
for S in 42 2027 3037; do
  LOOK=900 WRULE=msharpe CAL=simple LEGS=101 PHI=0.45 FSEED=$S FPRED=f10_V2MAIN_s${S}.npy \
    /root/miniconda3/envs/hsy_v5push/bin/python w10_ablation_replay_hardened.py > $PD/w10_canonpred_s$S.log 2>&1 \
    || { echo "FAIL s$S"; exit 1; }
  mv $PD/w10_ablation_series.npz $PD/w10_canonpred_s$S.npz
  mv $PD/w10_ablation_summary.json $PD/w10_canonpred_s$S.json
  echo "done s$S"
done
echo CANON_CLOSURE_RUNS_DONE
