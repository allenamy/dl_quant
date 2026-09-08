import numpy as np, json, calendar, time
hole=set(json.load(open("/tmp/hole.json")))
A=np.load("/workspace/dlw_ext/data/dlw_targets.npz",allow_pickle=True)
E=A["E_ts"].astype(np.int64); Y=A["y4s"]; nA=len(E)
z=np.load("/workspace/review_scratch/allweather_trackB/replay/dev_alt/probe_artifacts/w10_ablation_series_G_mE1cX7_R0_spl42.npz",allow_pickle=True)
syms=[str(s) for s in z["symbols"]]; W=z["d30_n2_c42_W"]; R=z["d30_n2_c42_rec"]
ts=R[:,0].astype(np.int64); gt=R[:,5]; pnl=R[:,2]
off=int(np.searchsorted(E,ts[0]))
idx={s:i for i,s in enumerate(syms)}; cols=np.array([idx[s] for s in hole if s in idx])
yr=np.array([time.gmtime(int(t)).tm_year for t in ts])
CUT=calendar.timegm((2026,8,10,20,0,0)); T2503=calendar.timegm((2025,3,1,0,0,0))
# 逐锚: 这些名字的 gross 占比 与 pnl 贡献
gh=np.abs(W[:,cols]).sum(1)
ph=np.array([float(np.nansum(W[i,cols]*np.nan_to_num(Y[off+i,cols])))*1e4 for i in range(len(ts))])
print(f"{'窗':>22s} {'锚':>5s} {'gross占比均':>11s} {'gross占比max':>12s} {'该组pnl':>9s} {'总pnl':>9s} {'占比':>7s}")
def row(lab,m):
    if m.sum()<5: return
    g=np.where(gt>0, gh/np.maximum(gt,1e-12),0)[m]
    print(f"{lab:>22s} {int(m.sum()):>5d} {g.mean()*100:>10.3f}% {g.max()*100:>11.3f}% {ph[m].sum():>+9.0f} {pnl[m].sum():>+9.0f} {ph[m].sum()/pnl[m].sum()*100 if pnl[m].sum()!=0 else 0:>6.1f}%")
for y in (2022,2023,2024,2025,2026): row(f"{y} 全年",(yr==y)&(ts<=CUT))
row("★冻结 2025-03→cut",(ts>=T2503)&(ts<=CUT))
row("全史 ≤cut",ts<=CUT)
row("Aug11-30 2026",(ts>=calendar.timegm((2026,8,11,0,0,0)))&(ts<=calendar.timegm((2026,8,30,20,0,0))))
print("\n★ 该组是否影响【配对差】: 各臂共享同一宇宙与同一 W 构造 ⇒ 常模; 但【水平/Sharpe】是另一本书的")
