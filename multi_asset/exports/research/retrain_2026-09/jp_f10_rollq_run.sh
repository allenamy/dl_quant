#!/bin/bash
# 季度滚动 OOS F10(V2MAIN)→ 回放臂(msharpe 动态席位 / FTRIM+M1 fx / FTRIM+M1 ms)→ 判官 + 逐年
set -u; W=/mnt/storage/private/work_hsy; PD=$W/probe_artifacts; PY=/root/miniconda3/envs/hsy_v5push/bin/python; cd $W
for i in $(seq 1 240); do grep -q "F10_TRAIN_DONE" $PD/f10_rollq_s42.log && break; sleep 30; done
cp $W/f8_2026-08-22/preds/f10_V2MAIN_rollq_s42.npy $W/f10_V2MAIN_rollq_s42.npy
$PY - <<PY
import numpy as np; a=np.load("/mnt/storage/private/work_hsy/f10_V2MAIN_rollq_s42.npy"); b=np.load("/mnt/storage/private/work_hsy/f10_V2MAIN_s42.npy"); print("rollq preds", a.shape, "finite", round(float(np.isfinite(a).mean()),3), "| 正典年折 F10", b.shape, "finite", round(float(np.isfinite(b).mean()),3))
PY
run() { local TAG=$1; shift; env LOOK=900 WRULE=msharpe CAL=simple LEGS=101 PHI=0.45 OUT_TAG=$TAG "$@" $PY w10_universe.py > $PD/w10_$TAG.log 2>&1 || { echo "FAIL $TAG"; tail -n 3 $PD/w10_$TAG.log; return; }; mv $PD/w10_ablation_series_$TAG.npz $PD/w10_$TAG.npz; mv $PD/w10_ablation_summary_$TAG.json $PD/w10_$TAG.json; echo "done $TAG $(date -u +%H:%M)"; }
( run rf_ms_s42 FSEED=42 FPRED=f10_V2MAIN_rollq_s42.npy ) & ( run rf_fxF_s42 FSEED=42 FPRED=f10_V2MAIN_rollq_s42.npy FTRIM=zero MEMBERS_TOPN=829 TRADE_TOPN=400 W3FIX=0.21,0,0.79 ) & ( run rf_msF_s42 FSEED=42 FPRED=f10_V2MAIN_rollq_s42.npy FTRIM=zero MEMBERS_TOPN=829 TRADE_TOPN=400 ) & ( run rf_both_msF_s42 FSEED=42 FPRED=f10_V2MAIN_rollq_s42.npy SLOW_NPY=$PD/slow_pred_rollq_splice.npy FTRIM=zero MEMBERS_TOPN=829 TRADE_TOPN=400 ) & wait
sed -i 's/+glob.glob(f"{PD}\/w10_rk_\*.npz")/+glob.glob(f"{PD}\/w10_rk_*.npz")+glob.glob(f"{PD}\/w10_rf_*.npz")/' jp_regime_arms_judge.py
J() { BASE=$1 SEEDTAG=$2 RUN_FILTER=$3 $PY jp_regime_arms_judge.py 2>&1 | grep "^\[w10_rf" | sed "s/np.float64(\([-0-9.]*\))/\1/g" | cut -c1-235; }
echo "---- 滚动 F10(msharpe) vs canonpred"; J w10_canonpred_s42 s42 rf_ms_s42
echo "---- 滚动 F10 + FTRIM + M1: fx vs N829T400F_fx / ms vs N829T400F_ms"; J w10_uni2_N829T400F_fx_s42 s42 rf_fxF_s42; J w10_uni2_N829T400F_ms_s42 s42 rf_msF_s42
echo "---- 滚动 king + 滚动 F10 + FTRIM + M1(ms) vs N829T400F_ms"; J w10_uni2_N829T400F_ms_s42 s42 rf_both_msF_s42
echo "---- 逐年"; $PY jp_lf_yearly.py canonpred_s42="msharpe 基" rf_ms_s42="msharpe 滚动F10" uni2_N829T400F_ms_s42="FTRIM+M1 ms 基" rf_msF_s42="FTRIM+M1 ms 滚动F10" rf_both_msF_s42="FTRIM+M1 ms 滚动king+F10" uni2_N829T400F_fx_s42="E fx 基" rf_fxF_s42="E fx 滚动F10"
echo F10_ROLLQ_REPLAY_DONE
