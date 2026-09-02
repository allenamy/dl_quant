#!/bin/bash
# L1SM 固定实盘席位口径(W3FIX): 各 τ preds → w10_side_band(SIDE 1.0, FTRIM off, W3FIX) → 判官 BASE=w10_canonfix_s42(canon 与 jp 基线 preds 逐位同)
set -u
W=/mnt/storage/private/work_hsy; PD=$W/probe_artifacts; cd $W; PY=/root/miniconda3/envs/hsy_v5push/bin/python
rp(){ OUTN=$1; SEED=$2; PRED=$3
  [ -f f8_2026-08-22/preds/$PRED ] || { echo "skip $OUTN (no pred)"; return; }
  env W3FIX="0.21,0,0.79" SIDE_KAPPA=1.0 FTRIM_MODE=off LOOK=900 WRULE=msharpe CAL=simple LEGS=101 PHI=0.45 FSEED=$SEED FPRED=$PRED $PY w10_side_band.py > $PD/$OUTN.log 2>&1 || { echo "FAIL $OUTN"; return; }
  mv $PD/w10_ablation_series.npz $PD/$OUTN.npz; mv $PD/w10_ablation_summary.json $PD/$OUTN.json; echo "done $OUTN"; }
for T in t05 t10 t20; do rp w10_seat_fix_l1sm_$T 42 f10_L1SM_${T}_s42.npy; done
echo "== L1SM 固定席位口径 vs 固定席位基线"; BASE=w10_canonfix_s42 $PY jp_regime_arms_judge.py 2>&1 | grep -E "^\[w10_seat_fix_l1sm|judge\]|基线"
$PY - <<PY
import numpy as np, time, os
PD="probe_artifacts"
def yr(run):
    z=np.load(f"{PD}/{run}.npz",allow_pickle=True); cols=[str(c) for c in z["cols"]]; rec=z["d30_n2_c42_rec"]
    ts=rec[:,cols.index("ts")].astype(np.int64); n=rec[:,cols.index("net_ex")].astype(float); y=np.array([time.gmtime(int(t)).tm_year for t in ts])
    return {Y:(n[y==Y].mean(), n[y==Y].mean()/(n[y==Y].std()+1e-12)*np.sqrt(2190)) for Y in (2023,2024,2025,2026)}
b=yr("w10_canonfix_s42"); print("固定席位 逐年 净/夏普: 基线 | " + " | ".join(t for t in ("t05","t10","t20") if os.path.exists(f"{PD}/w10_seat_fix_l1sm_{t}.npz")))
arms={t:yr(f"w10_seat_fix_l1sm_{t}") for t in ("t05","t10","t20") if os.path.exists(f"{PD}/w10_seat_fix_l1sm_{t}.npz")}
for Y in (2023,2024,2025,2026): print(f"  {Y}: {b[Y][0]:+.2f}/{b[Y][1]:.2f} | " + " | ".join(f"{arms[t][Y][0]:+.2f}/{arms[t][Y][1]:.2f}" for t in arms))
PY
echo L1SM_POST_FIX_DONE
