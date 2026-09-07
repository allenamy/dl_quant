import numpy as np, json, time, calendar
PA="/workspace/review_scratch/allweather_trackB/replay/dev_alt/probe_artifacts"
G_="/workspace/review_scratch/dl_monthly_gate/replay/dev_alt/probe_artifacts"
COLS=["ts","net","pnl","carry","cost","gross_total","gross_member","gross_sel","nsel","nmember","fires","leg_king","leg_rev24","leg_fund","w3_king","w3_rev24","w3_fund","turnover","net_ex","pnl_ex","carry_ex","cost_ex","netlong"]
ARM="d30_n2_c42"
A={"yearly_s42":f"{G_}/w10_ablation_series_BASE_s42.npz",
   "FIX7":f"{PA}/w10_ablation_series_G_mE1cX7_R0_spl42.npz",
   "CONST42":f"{PA}/w10_ablation_series_G_mE1c_R0_spl42.npz"}
D={}
for k,p in A.items():
    z=np.load(p,allow_pickle=True); R=z[f"{ARM}_rec"]; D[k]={c:R[:,i] for i,c in enumerate(COLS)}
ts=D["yearly_s42"]["ts"].astype(np.int64)
yr=np.array([time.gmtime(int(t)).tm_year for t in ts])
CUT=calendar.timegm((2026,8,10,20,0,0)); T2503=calendar.timegm((2025,3,1,0,0,0)); T24=calendar.timegm((2024,1,1,0,0,0))
def sh(x): return float(x.mean()/x.std(ddof=1)*np.sqrt(2190)) if len(x)>2 and x.std(ddof=1)>0 else float("nan")
def mdd(x): c=np.cumsum(x); return float(np.max(np.maximum.accumulate(c)-c))
print(f"anchors {len(ts)}  {time.strftime('%Y-%m-%d',time.gmtime(ts[0]))} → {time.strftime('%Y-%m-%d',time.gmtime(ts[-1]))}")
for k in A:
    g=D[k]["net_ex"]/D[k]["gross_total"]
    print(f"\n===== {k} (每 gross bps/锚) =====")
    print(f"{'窗':>26s} {'n':>5s} {'均值':>8s} {'Sharpe':>7s} {'maxDD':>7s} {'NAV%/yr@2x':>11s}")
    for lab,m in (("2022 全年",yr==2022),("2023 全年",yr==2023),("2024 全年",yr==2024),
                  ("2025 全年",yr==2025),("2026<=cut",(yr==2026)&(ts<=CUT)),
                  ("★冻结 2025-03→cut",(ts>=T2503)&(ts<=CUT)),
                  ("2024→26<=cut",(ts>=T24)&(ts<=CUT)),
                  ("全史<=cut",ts<=CUT)):
        x=g[m]
        if len(x)<10: print(f"{lab:>26s} {len(x):>5d}   (样本不足)"); continue
        print(f"{lab:>26s} {len(x):>5d} {x.mean():>+8.3f} {sh(x):>7.2f} {mdd(x):>7.0f} {x.mean()*43.8:>+10.1f}%")
print("\n注: FIX7/CONST42 的 2025 年之前的行是从 yearly_s42 拼接来的(spl42), 那几年不是该配方本身。")
