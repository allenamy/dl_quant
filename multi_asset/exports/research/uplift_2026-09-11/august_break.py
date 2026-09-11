#!/usr/bin/env python3
"""Did the BACKTEST itself break in Aug 2026? And clean-coverage window distribution
(F10 walk-forward OOS preds end 2026-08-10; after that the DL sub-book has no DL leg)."""
import numpy as np, time, math, datetime as dt
S="/Users/haosiyu/cc_tmp/claude-501/-Users-haosiyu-Desktop-quant-research/b9646a9e-31a1-4eb3-a08b-e8ea13fdceb0/scratchpad/w10"
OUT="/Users/haosiyu/Desktop/quant_research/multi_asset/exports/research/uplift_2026-09-11"
z=np.load(f"{S}/w10_ablation_series_pod_live_w3fix_callog_s42.npz",allow_pickle=True)
cols=[str(c) for c in z["cols"]]; rec=z["d30_n2_c42_rec"]
g=lambda k: rec[:,cols.index(k)].astype(float)
ts=rec[:,cols.index("ts")].astype(np.int64); u=g("net_ex")/g("gross_total")
lk,lr,lf=g("leg_king"),g("leg_rev24"),g("leg_fund")
DAY=np.array([time.strftime("%Y%m%d",time.gmtime(int(t))) for t in ts])
M=np.array([d[:6] for d in DAY])
print("== 2026 monthly, live-caliber arm, per unit gross; legs are RAW leg returns bps/anchor (unit gross, pre-book) ==")
print(f"{'month':>7} {'n':>4} {'book bps/anch':>13} {'sum %gross':>11} {'Sharpe':>7} {'king':>7} {'rev24':>7} {'fund':>7}")
for m in sorted(set(M[DAY>='20260101'].tolist())):
    s=M==m; x=u[s]
    print(f"{m:>7} {s.sum():>4} {x.mean():>+13.3f} {x.sum()/100:>+10.2f}% {x.mean()/x.std(ddof=1)*np.sqrt(2190):>+7.2f} {lk[s].mean():>+7.3f} {lr[s].mean():>+7.3f} {lf[s].mean():>+7.3f}")
for lab,lo,hi in (("2026-08 (F10 covered)","20260801","20260810"),("2026-08 (F10 MISSING)","20260811","20260830"),
                  ("2026-01..07","20260101","20260731"),("2026-08-26..08-30","20260826","20260830")):
    s=(DAY>=lo)&(DAY<=hi); x=u[s]
    print(f"  [{lab}] n={s.sum()} mean={x.mean():+.3f} bps sum={x.sum()/100:+.2f}%gross Sharpe={x.mean()/x.std(ddof=1)*np.sqrt(2190):+.2f} | king {lk[s].mean():+.2f} fund {lf[s].mean():+.2f}")

# rolling 17-day windows restricted to F10-complete coverage (window fully <= 2026-08-10)
idx={}
for d_,v in zip(DAY,u): idx[d_]=idx.get(d_,0)+v
d0=dt.date(2022,1,31); d1=dt.date(2026,8,30)
alld=[];allv=[]
c=d0
while c<=d1:
    k=c.strftime("%Y%m%d"); alld.append(k); allv.append(idx.get(k,0.0)); c+=dt.timedelta(days=1)
alld=np.array(alld); allv=np.array(allv); W=17
LIVE=-91.0125469180
def rep(lab,lo,hi):
    m=(alld>=lo)&(alld<=hi); v=allv[m]; dd=alld[m]
    s=np.convolve(v,np.ones(W),mode="valid"); n=len(s); neff=(n+W-1)/W
    below=int((s<=LIVE).sum())
    print(f"  [{lab}] n_win={n} n_eff={neff:.1f} mean={s.mean():+.0f} sd={s.std(ddof=1):.0f} | LIVE {LIVE:+.0f} pct={100*below/n:.2f}% (p={below/n:.3f})")
print("\n== 17-day window distribution, windows ENDING on or before 2026-08-10 (F10-complete) ==")
rep("2024-01-01..2026-08-10","20240101","20260810")
rep("2026-01-01..2026-08-10","20260101","20260810")
rep("2025-01-01..2026-08-10","20250101","20260810")

# power: how many anchors to distinguish backtest-2026 from zero-drift, given sd
for lab,mu,sd in (("2024on",0.658,27.01),("2025-26",1.501,29.94),("2026",3.099,34.46)):
    n95=(1.645*sd/mu)**2
    print(f"\n  POWER: to see backtest-{lab} drift ({mu:+.3f} bps/anchor, sd {sd:.1f}) at one-sided 95% you need "
          f"n={n95:.0f} anchors = {n95/6:.0f} days = {n95/6/30.4:.1f} months of live trading.")
print(f"\n  The live window is 96 anchors = 16 days. SE of its mean = 35.77/sqrt(96) = {35.77/math.sqrt(96):.2f} bps/anchor.")
