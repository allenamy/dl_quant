#!/bin/bash
# L1SM 书层回放: 各 preds → w10 hardened(频带装置 FTRIM off) → 判官(BASE=jpline 同装置基线) + 跨机对照
set -u
W=/mnt/storage/private/work_hsy; PD=$W/probe_artifacts; cd $W
PY=/root/miniconda3/envs/hsy_v5push/bin/python
rp(){ OUTN=$1; SEED=$2; PRED=$3
  env LOOK=900 WRULE=msharpe CAL=simple LEGS=101 PHI=0.45 FSEED=$SEED FPRED=$PRED FTRIM_MODE=off $PY w10_ftrim_band.py > $PD/$OUTN.log 2>&1 || { echo "FAIL $OUTN" >> $PD/l1sm_post.log; exit 1; }
  mv $PD/w10_ablation_series.npz $PD/$OUTN.npz; mv $PD/w10_ablation_summary.json $PD/$OUTN.json; echo "done $OUTN" >> $PD/l1sm_post.log; }
rp w10_canonpred_jp_s42 42 f10_V2MAINJP_s42.npy
rp w10_seat_l1sm_t05 42 f10_L1SM_t05_s42.npy
rp w10_seat_l1sm_t10 42 f10_L1SM_t10_s42.npy
rp w10_seat_l1sm_t20 42 f10_L1SM_t20_s42.npy
rp w10_canonpred_jp_s2027 2027 f10_V2MAINJP_s2027.npy
cp $PD/w10_canonpred_jp_s42.npz $PD/w10_seat_v2mainjp_xcheck.npz
echo "== 跨机对照(BASE=pod canon s42)"; $PY jp_regime_arms_judge.py 2>&1 | grep -E "^\[w10_seat_v2mainjp_xcheck|judge\]"
echo "== L1SM vs 同装置基线"; BASE=w10_canonpred_jp_s42 $PY jp_regime_arms_judge.py 2>&1 | grep -E "^\[w10_seat_l1sm|judge\]|CFG_SAME.*l1sm"
echo L1SM_POST_DONE >> $PD/l1sm_post.log
