#!/bin/bash
# 滚动季度 OOS king → meta 形状拼接(2022Q1 前用正典 SLOW)→ 回放臂(msharpe 动态席位 / +FTRIM+M1 / W3FIX)→ 判官 + 逐年
set -u; W=/mnt/storage/private/work_hsy; PD=$W/probe_artifacts; PY=/root/miniconda3/envs/hsy_v5push/bin/python; cd $W
for i in $(seq 1 120); do grep -q KING_ROLLQ_DONE $PD/king_rollq.log && break; sleep 15; done
$PY - <<PY
import numpy as np, json, time
W="/mnt/storage/private/work_hsy"; B=f"{W}/pod_backup_2026-08-21"
M=np.load(f"{B}/wide_fea_hist_meta.npz",allow_pickle=True); E=M["E_ts"].astype(np.int64); SLOW=np.load(f"{B}/slow_pred_hist_oos.npy")
TG=np.load(f"{W}/dlw_2026-08-22/data/dlw_targets.npz",allow_pickle=True); Ed=TG["E_ts"].astype(np.int64); syms_d=[str(s) for s in TG["symbols"]]
P=np.load(f"{W}/f8_2026-08-22/preds/f4_lgbm_K171_rollq.npy"); assert P.shape[1]==SLOW.shape[1]
Pw=np.load(f"{B}/wide_panel_4h_hist_v2.npz",allow_pickle=True); assert [str(s) for s in Pw["symbols"]]==syms_d, "symbol order mismatch"
mrow={int(t):i for i,t in enumerate(E)}; out=SLOW.copy(); n=0; first=None
for k,t in enumerate(Ed):
    i=mrow.get(int(t))
    if i is None or not np.isfinite(P[k]).any(): continue
    out[i]=P[k]; n+=1; first=first or int(t)
np.save(f"{W}/probe_artifacts/slow_pred_rollq_splice.npy", out.astype(np.float32))
print(f"splice: 覆盖 {n} 锚(自 {time.strftime('%Y-%m-%d',time.gmtime(first))}), 其余用正典 OOS; finite {np.isfinite(out).mean():.3f} vs 正典 {np.isfinite(SLOW).mean():.3f}")
rep=json.load(open(f"{W}/f8_2026-08-22/results/f4_lgbm_K171_rollq.json")); yrs={}
for q,v in rep.items(): yrs.setdefault(q[:4],[]).append(v["ic_raw"])
print("滚动 king 逐年 IC(raw y4):", {y:round(float(np.mean(v)),4) for y,v in sorted(yrs.items())}, "| 正典年折 OOS king IC(2025-26 月均 0.03-0.08)")
PY
run() { local TAG=$1; shift; env LOOK=900 WRULE=msharpe CAL=simple LEGS=101 PHI=0.45 OUT_TAG=$TAG "$@" $PY w10_universe.py > $PD/w10_$TAG.log 2>&1 || { echo "FAIL $TAG"; tail -n 3 $PD/w10_$TAG.log; return; }; mv $PD/w10_ablation_series_$TAG.npz $PD/w10_$TAG.npz; mv $PD/w10_ablation_summary_$TAG.json $PD/w10_$TAG.json; echo "done $TAG $(date -u +%H:%M)"; }
S=$PD/slow_pred_rollq_splice.npy
( run rk_ms_s42 FSEED=42 FPRED=f10_V2MAIN_s42.npy SLOW_NPY=$S ) & ( run rk_ms_s2027 FSEED=2027 FPRED=f10_V2MAIN_s2027.npy SLOW_NPY=$S ) & ( run rk_msF_s42 FSEED=42 FPRED=f10_V2MAIN_s42.npy SLOW_NPY=$S FTRIM=zero MEMBERS_TOPN=829 TRADE_TOPN=400 ) & ( run rk_fxF_s42 FSEED=42 FPRED=f10_V2MAIN_s42.npy SLOW_NPY=$S FTRIM=zero MEMBERS_TOPN=829 TRADE_TOPN=400 W3FIX=0.21,0,0.79 ) & wait
J() { BASE=$1 SEEDTAG=$2 RUN_FILTER=$3 $PY jp_regime_arms_judge.py 2>&1 | grep "^\[w10_rk" | sed "s/np.float64(\([-0-9.]*\))/\1/g" | cut -c1-235; }
sed -i 's/+glob.glob(f"{PD}\/w10_lf_\*.npz")/+glob.glob(f"{PD}\/w10_lf_*.npz")+glob.glob(f"{PD}\/w10_rk_*.npz")/' jp_regime_arms_judge.py
echo "---- 滚动 king(msharpe 动态席位) vs canonpred"; J w10_canonpred_s42 s42 rk_ms_s42; J w10_canonpred_s2027 s2027 rk_ms_s2027
echo "---- 滚动 king + FTRIM + M1(ms) vs N829T400F_ms"; J w10_uni2_N829T400F_ms_s42 s42 rk_msF_s42
echo "---- 滚动 king + FTRIM + M1(fx) vs N829T400F_fx"; J w10_uni2_N829T400F_fx_s42 s42 rk_fxF_s42
echo "---- 逐年(2.0× 复利)"; $PY jp_lf_yearly.py canonpred_s42="msharpe 基(陈旧 king)" rk_ms_s42="msharpe 滚动 king s42" rk_ms_s2027="msharpe 滚动 king s2027" uni2_N829T400F_ms_s42="FTRIM+M1 ms 基" rk_msF_s42="FTRIM+M1 ms 滚动 king" uni2_N829T400F_fx_s42="E 基 fx" rk_fxF_s42="E fx 滚动 king"
echo ROLLQ_KING_REPLAY_DONE
