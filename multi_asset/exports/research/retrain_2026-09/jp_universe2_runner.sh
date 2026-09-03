#!/bin/bash
# PREREG_universe_dyn_2026-09-04 §1 臂 · 4 并行道 · s42 · 双口径(msharpe / W3FIX)。env 逐字抄 jp_universe_runner.sh 并加 OUT_TAG/W3FIX/MEMBERS_TOPN。
set -u
W=/mnt/storage/private/work_hsy; PD=$W/probe_artifacts; PY=/root/miniconda3/envs/hsy_v5push/bin/python
cd $W
run() { # $1 arm  $2 caliber(ms|fx)  $3 seed
  local A=$1 C=$2 S=$3 TAG=uni2_${1}_${2}_s$3 EXTRA=""
  case $A in
    N400r) EXTRA="MEMBERS_TOPN=400";; N500) EXTRA="MEMBERS_TOPN=500";; N600) EXTRA="MEMBERS_TOPN=600";;
    *) EXTRA="UMASK_NPZ=$PD/umask_$A.npz";;
  esac
  [ "$C" = fx ] && EXTRA="$EXTRA W3FIX=0.21,0,0.79"
  env LOOK=900 WRULE=msharpe CAL=simple LEGS=101 PHI=0.45 FSEED=$S FPRED=f10_V2MAIN_s$S.npy OUT_TAG=$TAG $EXTRA \
    $PY w10_universe.py > $PD/w10_$TAG.log 2>&1 || { echo "FAIL $TAG" >> $PD/uni2_runner.log; return; }
  mv $PD/w10_ablation_series_$TAG.npz $PD/w10_$TAG.npz; mv $PD/w10_ablation_summary_$TAG.json $PD/w10_$TAG.json
  echo "done $TAG $(date -u +%H:%M)" >> $PD/uni2_runner.log
}
lane() { for A in "$@"; do run $A ms 42; run $A fx 42; done; echo "LANE_DONE $*" >> $PD/uni2_runner.log; }
lane A14 A30 A60 &
lane F_M F_Q F_Y &
lane N300 H_300_400 N400r &
lane N500 N600 &
wait; echo UNI2_S42_DONE >> $PD/uni2_runner.log
