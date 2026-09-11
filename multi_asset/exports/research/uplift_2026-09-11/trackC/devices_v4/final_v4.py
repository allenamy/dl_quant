import sys; sys.path.insert(0,"/workspace/uplift_2026-09-11/trackC")
from lib import *
import numpy as np, json, time, calendar
z=np.load("/workspace/uplift_2026-09-11/trackC/cand_v4.npz"); Pz=np.load("/workspace/uplift_2026-09-11/trackC/pct_v4.npz")
ts=z["ts"]; u=z["u"]; n=len(u); Y=np.array([time.gmtime(int(t)).tm_year for t in ts])
def T(*x): return calendar.timegm(x+(0,)*(6-len(x)))
COST=3.52; FW=(T(2025,3,1),T(2026,8,10,20))
def daily(x,tt):
    dk=np.array([int(t)//86400 for t in tt]); o=[]
    for d in np.unique(dk):
        s=dk==d
        if s.sum()==6: o.append(x[s].sum())
    return np.array(o)
print("== BASELINE A0 (v4, dynamic seat) TAIL PROFILE, gross=2.0x NAV, per unit gross ==")
for lab,sp in (("FULL 2022-01..2026-08", np.isfinite(u)),
               ("FROZEN 2025-03..2026-08-10",(ts>=FW[0])&(ts<=FW[1])),
               ("2026 only", Y==2026)):
    rr=u[sp]; tt=ts[sp]; dd=daily(rr,tt); navd=2.0*dd/1e4
    cum=np.cumsum(rr)
    mk=np.array([time.gmtime(int(t)).tm_year*100+time.gmtime(int(t)).tm_mon for t in tt])
    wm=min(rr[mk==m].sum() for m in np.unique(mk))
    cv=float(np.sort(dd)[:max(1,int(round(0.05*len(dd))))].mean())
    print("  %-28s n=%5d Sh=%+.3f(SE %.2f) mean=%+.4f maxDD=%7.1f bps  worstMo=%+8.1f bps  CVaR5d=%+7.2f bps  worstDay=%+8.2f bps"
          %(lab,len(rr),sharpe(rr),se_sharpe(len(rr)),rr.mean(),maxdd(cum),wm,cv,dd.min()))
    print("     breach(-4.0%% equity @2.0x): %d/%d days = %.4f  (live: 1/34 = %.4f)"%((navd<-0.04).sum(),len(dd),(navd<-0.04).mean(),1/34))
print()
print("== G6 EXCHANGE RATE for the FAMILY of de-risk ladders (all 300), full-sample ==")
R=json.load(open("/workspace/uplift_2026-09-11/trackC/eval_v4.json"))
ok=[r for r in R if r["dd_red"]>0.01]
xr=[]
for r in ok:
    alpha_given=r["base_mean"]-r["mean"]            # bps/anchor given up (may be negative=gained)
    dd_removed=(r["base_maxdd"]-r["maxdd"])/100.0   # % of gross removed
    if dd_removed>0.5: xr.append(alpha_given/dd_removed)
xr=np.array(xr)
print("  n=%d variants with maxDD reduced >1%%.  exchange rate = (bps/anchor given up) per (1%% of gross maxDD removed)"%len(xr))
print("  median %+0.4f   p25 %+0.4f   p75 %+0.4f   frac<=0 (tail removed for FREE) %.2f"%(np.median(xr),np.percentile(xr,25),np.percentile(xr,75),(xr<=0).mean()))
print("  interpretation: median variant pays %+0.4f bps/anchor per 1%%-of-gross of maxDD removed."%np.median(xr))
print("  baseline mean is %+0.4f bps/anchor, so the median exchange rate is %.1f%% of the mean per 1%% of gross DD."%(np.mean([r["base_mean"] for r in ok]), 100*np.median(xr)/np.mean([r["base_mean"] for r in ok])))
print()
print("== TURNOVER COST OF GROSS SCALING (G8) ==")
dgs=np.array([r["dg"] for r in R]); cs=np.array([r["costm"] for r in R])
print("  mean |dg| per anchor: median %.5f (p95 %.5f) ; cost at 3.52 bps/unit: median %.5f bps/anchor (p95 %.5f)"%(np.median(dgs),np.percentile(dgs,95),np.median(cs),np.percentile(cs,95)))
print("  vs the book's own modelled turnover 2.31%%/anchor => gross scaling costs %.1f%% of what one anchor of name-level rebalancing costs."%(100*np.median(cs)/(3.52*0.0231)))
