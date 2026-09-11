#!/usr/bin/env python3
"""Empirical distribution of 17-calendar-day windows in the live-caliber backtest, and where the
realized live window 2026-08-26..09-11 sits. Unit for BOTH: bps of GROSS, summed over the window."""
import numpy as np, json, time, math
OUT="/Users/haosiyu/Desktop/quant_research/multi_asset/exports/research/uplift_2026-09-11"
z=np.load(f"{OUT}/backtest_daily_unitgross.npz",allow_pickle=True)
day=np.array([str(x) for x in z["day"]]); bps=z["bps"].astype(float); nan_=z["nanch"].astype(int)
# calendar-complete daily index (fill missing calendar days with 0 -> device has all 6 anchors every day)
import datetime as dt
d0=dt.date(int(day[0][:4]),int(day[0][4:6]),int(day[0][6:8])); d1=dt.date(int(day[-1][:4]),int(day[-1][4:6]),int(day[-1][6:8]))
idx={k:v for k,v in zip(day,bps)}
alld=[]; allv=[]
c=d0
while c<=d1:
    k=c.strftime("%Y%m%d"); alld.append(k); allv.append(idx.get(k,np.nan)); c+=dt.timedelta(days=1)
alld=np.array(alld); allv=np.array(allv)
print("missing calendar days in device:", int(np.isnan(allv).sum()), "of", len(allv))
allv=np.nan_to_num(allv)

LIVE_SUM=-91.0125469180  # bps of gross, 2026-08-26..09-11, 96 anchors (live_anchor_series.py)
LIVE_MEAN=-0.9480        # bps/anchor/gross
W=17

def windows(lo,hi):
    m=(alld>=lo)&(alld<=hi); v=allv[m]; dd=alld[m]
    s=np.convolve(v,np.ones(W),mode="valid")
    return dd[:len(s)],s

for lab,lo,hi in (("2024-01-01..2026-08-30","20240101","20260830"),
                  ("2025-01-01..2026-08-30","20250101","20260830"),
                  ("2026 only","20260101","20260830"),
                  ("2022-01-31..2026-08-30 (king absent 22-23)","20220131","20260830")):
    dd,s=windows(lo,hi)
    n=len(s); ndays=n+W-1; neff=ndays/W
    below=int((s<=LIVE_SUM).sum()); pct=100*below/n
    # Gaussian tail on the window distribution
    zsc=(LIVE_SUM-s.mean())/s.std(ddof=1)
    # p-value with effective (non-overlapping) sample size: binomial CI on the empirical fraction
    se_emp=math.sqrt(max(pct/100*(1-pct/100),1e-12)/max(neff,1))*100
    print(f"\n[{lab}] windows={n} (overlapping) | calendar days={ndays} | NON-OVERLAPPING n_eff={neff:.1f}")
    print(f"   window sum (bps of gross): mean {s.mean():+.1f}  sd {s.std(ddof=1):.1f}  min {s.min():+.1f}  p05 {np.percentile(s,5):+.1f}  p50 {np.percentile(s,50):+.1f}  p95 {np.percentile(s,95):+.1f}  max {s.max():+.1f}")
    print(f"   LIVE {LIVE_SUM:+.1f} -> PERCENTILE {pct:.2f}%  ({below}/{n} backtest windows were this bad or worse)")
    print(f"   z vs window distribution = {zsc:+.2f} ; empirical p (one-sided) = {pct/100:.4f} +- {se_emp/100:.4f} (SE from n_eff={neff:.1f})")
    # worst windows
    o=np.argsort(s)[:5]
    print(f"   5 worst backtest windows start: "+", ".join(f"{dd[i]}:{s[i]:+.0f}" for i in o))

# ---- per-anchor view: is the live window's MEAN consistent with the backtest's mean?
za=np.load("/Users/haosiyu/cc_tmp/claude-501/-Users-haosiyu-Desktop-quant-research/b9646a9e-31a1-4eb3-a08b-e8ea13fdceb0/scratchpad/w10/w10_ablation_series_pod_live_w3fix_callog_s42.npz",allow_pickle=True)
cols=[str(c) for c in za["cols"]]; rec=za["d30_n2_c42_rec"]
ts=rec[:,cols.index("ts")].astype(np.int64); u=rec[:,cols.index("net_ex")].astype(float)/rec[:,cols.index("gross_total")].astype(float)
Y=np.array([time.gmtime(int(t)).tm_year for t in ts])
print("\n== per-anchor moments, bps of gross ==")
for lab,m in (("2024on",Y>=2024),("2025-26",Y>=2025),("2026",Y==2026)):
    x=u[m]; print(f"   backtest {lab}: n={m.sum()} mean {x.mean():+.3f} sd {x.std(ddof=1):.2f} Sharpe_ann {x.mean()/x.std(ddof=1)*np.sqrt(2190):+.2f}")
print(f"   LIVE window  : n=96 mean {LIVE_MEAN:+.3f} sd 35.77 Sharpe_ann {LIVE_MEAN/35.77*np.sqrt(2190):+.2f}")
for lab,m in (("2024on",Y>=2024),("2025-26",Y>=2025),("2026",Y==2026)):
    x=u[m]; se=x.std(ddof=1)/np.sqrt(96)
    zs=(LIVE_MEAN-x.mean())/se
    from math import erf,sqrt
    p=0.5*(1+erf(zs/sqrt(2)))
    print(f"   H0: live window drawn from backtest {lab}: gap {LIVE_MEAN-x.mean():+.3f} bps/anchor, SE(96 anchors)={se:.3f}, z={zs:+.2f}, one-sided p={p:.4f}")
    # block-aware SE: 17 daily blocks
    dsd=None
