import sys; sys.path.insert(0,"/workspace/uplift_2026-09-11/trackC")
from lib import *
import numpy as np, json, time, calendar
z=np.load("/workspace/uplift_2026-09-11/trackC/cand_v4.npz")
ts=z["ts"]; u=z["u"]; n=len(u); Y=np.array([time.gmtime(int(t)).tm_year for t in ts])
COST_BPS_PER_UNIT_TURNOVER=3.52   # receipt turnover_cost_reaudit_2026_08_21
BOOT_BLOCK=30; BOOT_N=2000; RNG=np.random.default_rng(20260911)
def daily(x, ts):
    dk=np.array([int(t)//86400 for t in ts]); out=[]; keys=[]
    for d in np.unique(dk):
        s=dk==d
        if s.sum()==6: out.append(x[s].sum()); keys.append(d)
    return np.array(out), np.array(keys)
def metrics(g, lab, span):
    gg=g[span]; uu=u[span]; tt=ts[span]
    dg=np.abs(np.diff(np.concatenate([[gg[0]],gg])))
    cost=COST_BPS_PER_UNIT_TURNOVER*dg
    rr=gg*uu-cost
    dd,_=daily(rr,tt)
    cum=np.cumsum(rr)
    nav_daily=2.0*dd/1e4    # fraction of NAV at 2.0x gross
    cv=np.sort(dd)[:max(1,int(0.05*len(dd)))].mean()
    return dict(label=lab,n=int(span.sum()),mean=float(rr.mean()),sharpe=sharpe(rr),se_sharpe=se_sharpe(int(span.sum())),
                maxdd=maxdd(cum),cvar5_daily=float(cv),worst_day=float(dd.min()),
                worst_month=worst_month(rr,tt),breach=float((nav_daily<-0.04).mean()),ndays=int(len(dd)),
                dg_mean=float(dg.mean()),cost_mean=float(cost.mean()),gmean=float(gg.mean()),
                by_year={int(y):dict(sharpe=sharpe(rr[Y[span]==y]),cum=float(rr[Y[span]==y].sum()/100)) for y in np.unique(Y[span]) if (Y[span]==y).sum()>100},
                ret=rr)
def worst_month(rr,tt):
    mk=np.array([time.gmtime(int(t)).tm_year*100+time.gmtime(int(t)).tm_mon for t in tt])
    return float(min(rr[mk==m].sum() for m in np.unique(mk)))
def boot_dsharpe(a,b):
    m=len(a); nb=m//BOOT_BLOCK; out=np.empty(BOOT_N)
    starts=np.arange(0,m-BOOT_BLOCK+1)
    for i in range(BOOT_N):
        s=RNG.choice(starts,nb); idx=(s[:,None]+np.arange(BOOT_BLOCK)[None,:]).ravel()
        out[i]=sharpe(a[idx])-sharpe(b[idx])
    return out
def build_pct(xname,Kroll,Kref):
    key=f"__p_{xname}_{Kroll}_{Kref}"
    return trail_pct(z[xname.replace("_pctsrc","")],Kroll,Kref)
SRC={"bookvol":trail_std(u,30),"disp":z["disp_bps_trail30"],"sigfund":z["fund_sd_trail30"],
     "fundema":z["fundema_sd_trail30"],"turn":z["turnover_trail30"]}
REFS={"1y":2190,"6m":1095,"2y":4380}
P={}
for nm,x in SRC.items():
    for rl,R in REFS.items():
        pp=np.full(n,np.nan)
        for t in range(R,n):
            h=x[t-R:t]; h=h[np.isfinite(h)]; c=x[t]
            if len(h)>=R//2 and np.isfinite(c): pp[t]=float((h<=c).mean())
        P[f"{nm}_{rl}"]=pp
np.savez("/workspace/uplift_2026-09-11/trackC/pct_v4.npz",ts=ts,**P)
print("percentiles built:",list(P))
