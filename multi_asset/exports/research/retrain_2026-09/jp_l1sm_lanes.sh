#!/bin/bash
# L1SM 训练双 lane @jpline 3090(PREREG_l1_softmin_2026-09-02 时序声明逐字)
set -u
W=/mnt/storage/private/work_hsy; cd $W; PD=$W/probe_artifacts
PY=/root/miniconda3/envs/hsy_v5push/bin/python
fit(){ ARM=$1; SEED=$2; TAU=$3; LANE=$4
  env V2=1 F10_DLW=$W/dlw_2026-08-22 F10_OUT=$W/f8_2026-08-22 SEED=$SEED ARM=$ARM SM_TAU=$TAU $PY pod_f10_train_ext.py > $PD/l1sm_${ARM}_s$SEED.log 2>&1 \
    && echo "done $ARM s$SEED" >> $PD/l1sm_lane$LANE.log || { echo "FAIL $ARM s$SEED" >> $PD/l1sm_lane$LANE.log; exit 1; }; }
laneA(){ fit V2MAINJP 42 0 A; fit L1SM_t05 42 0.5 A; fit V2MAINJP 2027 0 A; echo LANEA_DONE >> $PD/l1sm_laneA.log; }
laneB(){ fit L1SM_t10 42 1.0 B; fit L1SM_t20 42 2.0 B; echo LANEB_DONE >> $PD/l1sm_laneB.log; }
rm -f $PD/l1sm_laneA.log $PD/l1sm_laneB.log
laneA & laneB & wait
