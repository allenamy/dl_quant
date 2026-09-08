import numpy as np, json, calendar, time
PA="/workspace/review_scratch/allweather_trackB/replay/dev_alt/probe_artifacts"
COLS=["ts","net","pnl","carry","cost","gross_total","gross_member","gross_sel","nsel","nmember","fires","leg_king","leg_rev24","leg_fund","w3_king","w3_rev24","w3_fund","turnover","net_ex","pnl_ex","carry_ex","cost_ex","netlong"]
def L(p):
    z=np.load(p,allow_pickle=True); return {c:z["d30_n2_c42_rec"][:,i] for i,c in enumerate(COLS)}
B=L(f"{PA}/w10_ablation_series_G_mE1cX7_R0_spl42.npz"); C=L(f"{PA}/w10_ablation_series_G_FIX7_UCRYPTO.npz")
ts=B["ts"].astype(np.int64); days=ts//86400
yr=np.array([time.gmtime(int(t)).tm_year for t in ts])
CUT=calendar.timegm((2026,8,10,20,0,0)); T2503=calendar.timegm((2025,3,1,0,0,0)); T24=calendar.timegm((2024,1,1,0,0,0)); T26=calendar.timegm((2026,1,1,0,0,0))
gB=B["net_ex"]/B["gross_total"]; gC=C["net_ex"]/C["gross_total"]
tB=B["turnover"]/B["gross_total"]; tC=C["turnover"]/C["gross_total"]
rng=np.random.default_rng(20260905)
def boot(x,m,NB=2000):
    v=x[m]; d=days[m]; ud,inv=np.unique(d,return_inverse=True); nd=len(ud)
    s=np.bincount(inv,weights=v,minlength=nd); c=np.bincount(inv,minlength=nd)
    idx=rng.integers(0,nd,size=(NB,nd)); mn=s[idx].sum(1)/c[idx].sum(1)
    return float(v.mean()),float(np.percentile(mn,2.5)),float(np.percentile(mn,97.5)),float((mn>0).mean())
def sh(x): return float(x.mean()/x.std(ddof=1)*np.sqrt(2190)) if len(x)>2 and x.std(ddof=1)>0 else float("nan")
def dd(x): c=np.cumsum(x); return float(np.max(np.maximum.accumulate(c)-c))
WINS=[(f"{y} 全年",(yr==y)&(ts<=CUT)) for y in (2022,2023,2024,2025)]+[("2026≤cut",(ts>=T26)&(ts<=CUT)),("★冻结 2025-03→cut",(ts>=T2503)&(ts<=CUT)),("2024→26≤cut",(ts>=T24)&(ts<=CUT)),("全史≤cut",ts<=CUT)]
print("## 表1 · 水平(每 gross bps/锚; 全周期逐年, 负年份显式 — E-0904-B)")
print(f"| {'窗':<18s} | {'n':>5s} | {'BASE 均值':>9s} | {'S':>6s} | {'maxDD':>6s} | {'换手':>7s} | {'CRYPTO 均值':>11s} | {'S':>6s} | {'maxDD':>6s} | {'换手':>7s} |")
print("|"+"---|"*10)
for lab,m in WINS:
    if m.sum()<20: continue
    a,b=gB[m],gC[m]
    print(f"| {lab:<18s} | {int(m.sum()):>5d} | {a.mean():>+9.3f} | {sh(a):>+6.2f} | {dd(a):>6.0f} | {tB[m].mean():>7.5f} | {b.mean():>+11.3f} | {sh(b):>+6.2f} | {dd(b):>6.0f} | {tC[m].mean():>7.5f} |")
print("\n## 表2 · 配对差 CRYPTO − BASE(逐锚 Δg, UTC 日块自举 2000 种子 20260905)")
print(f"| {'窗':<18s} | {'Δ':>8s} | {'CI95':>22s} | {'P>0':>5s} | {'ΔSharpe':>8s} | {'ΔmaxDD':>7s} | {'Δ换手%':>8s} |")
print("|"+"---|"*7)
for lab,m in WINS:
    if m.sum()<20: continue
    d=gC-gB; mu,lo,hi,p=boot(d,m)
    print(f"| {lab:<18s} | {mu:>+8.4f} | [{lo:>+8.4f}, {hi:>+8.4f}] | {p:>5.2f} | {sh(gC[m])-sh(gB[m]):>+8.3f} | {dd(gC[m])-dd(gB[m]):>+7.0f} | {(tC[m].mean()/tB[m].mean()-1)*100:>+7.2f}% |")
print("\n## 表3 · 换算与对账")
for lab,m in (("★冻结主窗",(ts>=T2503)&(ts<=CUT)),("2026≤cut",(ts>=T26)&(ts<=CUT)),("2024→26",(ts>=T24)&(ts<=CUT)),("全史",ts<=CUT)):
    mu,lo,hi,_=boot(gC-gB,m)
    print(f"  {lab:<12s} Δ {mu:+.4f} bps/gross ⇒ {mu*43.8:+.2f}% NAV/年 @2×  CI [{lo*43.8:+.2f}%, {hi*43.8:+.2f}%]")
mu,_,_,_=boot(gC-gB,(ts>=T24)&(ts<=CUT))
print(f"\n  既有受据「U-FROZEN − U-PIT = +0.45~0.52 bps/锚, 全记为前视」")
print(f"  本臂测得【品种类别】成分(2024→26) = {mu:+.4f} bps/锚")
for g in (0.45,0.52): print(f"    ⇒ 占 +{g:.2f} 的 {mu/g*100:.1f}%; 前视残余 {g-mu:+.4f} bps/锚 ({(g-mu)/g*100:.1f}%)")
