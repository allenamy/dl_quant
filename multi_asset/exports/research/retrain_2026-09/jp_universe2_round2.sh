#!/bin/bash
# PREREG_universe_dyn §1 第二轮(掩码 v2, 首现修正): A14/A30/A60, F_M/F_Q/F_Y, N500X14/N600X14 · s42 双口径 · 4 道
set -u; W=/mnt/storage/private/work_hsy; PD=$W/probe_artifacts; PY=/root/miniconda3/envs/hsy_v5push/bin/python; cd $W
run() { local A=$1 C=$2 S=$3 TAG=uni2_${1}_${2}_s$3 EXTRA=""
  case $A in N500X14) EXTRA="MEMBERS_TOPN=500 UMASK_NPZ=$PD/umask_X14.npz";; N600X14) EXTRA="MEMBERS_TOPN=600 UMASK_NPZ=$PD/umask_X14.npz";; *) EXTRA="UMASK_NPZ=$PD/umask_$A.npz";; esac
  [ "$C" = fx ] && EXTRA="$EXTRA W3FIX=0.21,0,0.79"
  env LOOK=900 WRULE=msharpe CAL=simple LEGS=101 PHI=0.45 FSEED=$S FPRED=f10_V2MAIN_s$S.npy OUT_TAG=$TAG $EXTRA $PY w10_universe.py > $PD/w10_$TAG.log 2>&1 || { echo "FAIL $TAG" >> $PD/uni2_runner.log; return; }
  mv $PD/w10_ablation_series_$TAG.npz $PD/w10_$TAG.npz; mv $PD/w10_ablation_summary_$TAG.json $PD/w10_$TAG.json; echo "done $TAG $(date -u +%H:%M)" >> $PD/uni2_runner.log; }
lane() { for A in "$@"; do run $A ms 42; run $A fx 42; done; }
lane A14 A30 & lane A60 F_M & lane F_Q F_Y & lane N500X14 N600X14 & wait; echo UNI2_ROUND2_DONE >> $PD/uni2_runner.log
