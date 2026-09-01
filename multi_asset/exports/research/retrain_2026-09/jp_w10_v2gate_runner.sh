#!/bin/bash
# 门V2 四跑 runner @jpline: 同装置(w10 hardened 逐字, 零改动)顺序回放 old/new × s42/s2027, 每跑后改名防踩。
# 前置: preds 已放 f8_2026-08-22/preds/f10_V2MAIN_s{S}_{OLD9,NEW9}.npy; 装置 = work_hsy/w10_ablation_replay_hardened.py
set -u
W=/mnt/storage/private/work_hsy
PD=$W/probe_artifacts
cd $W
for RUN in s42_OLD9 s42_NEW9 s2027_OLD9 s2027_NEW9; do
  S=${RUN%%_*}; TAG=${RUN#*_}
  echo "== w10 $RUN $(date -u +%H:%M)"
  LOOK=900 WRULE=msharpe CAL=simple LEGS=101 PHI=0.45 FSEED=${S#s} \
    FPRED=f10_V2MAIN_${S}_${TAG}.npy \
    python3 w10_ablation_replay_hardened.py > $PD/w10_v2gate_${RUN}.log 2>&1 \
    || { echo "W10_FAIL $RUN"; exit 1; }
  mv $PD/w10_ablation_series.npz $PD/w10_v2gate_${RUN}.npz
  mv $PD/w10_ablation_summary.json $PD/w10_v2gate_${RUN}.json
done
echo W10_V2GATE_RUNS_DONE
