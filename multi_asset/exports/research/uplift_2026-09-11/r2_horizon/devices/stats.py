import numpy as np, calendar, os, json
COLS=["ts","net","pnl","carry","cost","gross_total","gross_member","gross_sel","nsel","nmember","fires","leg_king","leg_rev24","leg_fund","w3_king","w3_rev24","w3_fund","turnover","net_ex","pnl_ex","carry_ex","cost_ex","netlong"]
C={c:i for i,c in enumerate(COLS)}
def T(*a): return calendar.timegm(a+(0,)*(6-len(a)))
R="/workspace/uplift_2026-09-11/r2_horizon"
HCP="/workspace/review_scratch/health_check/dev_v4/probe_artifacts"
WIN={"full":(T(2022,1,31),T(2026,8,31,20)+1),
     "full9918":(T(2022,1,1),T(2026,8,10,20)+1),
     "frozen":(T(2025,3,1),T(2026,8,10,20)+1),
     "2024on":(T(2024,1,1),T(2026,8,10,20)+1),
     "ext":(T(2026,8,11),T(2026,8,31,20)+1)}
def load(tag):
    if tag.startswith("A0"):
        A=np.load(HCP+"/w10_ablation_series_V4_"+tag+".npz",allow_pickle=True); Rr=np.asarray(A["d30_n2_c42_rec"],float)
    else:
        A=np.load(R+"/out/"+tag+".npz",allow_pickle=True); Rr=np.asarray(A["rec"],float)
    ts=np.round(Rr[:,0]).astype(np.int64)
    assert [str(x) for x in A["cols"]]==COLS, tag
    return ts,Rr
def gser(Rr): return Rr[:,C["net_ex"]]/Rr[:,C["gross_total"]]
def sh(x): return float(x.mean()/x.std(ddof=1)*np.sqrt(2190)) if len(x)>2 else np.nan
def maskw(ts,w): lo,hi=WIN[w]; return (ts>=lo)&(ts<hi)
def boot(x,ts,k,B=2000,paired=None):
    """UTC-day block bootstrap, 2000 resamples, rng default_rng([20260905,k])."""
    d=ts//86400; ud,inv=np.unique(d,return_inverse=True)
    idx=[np.where(inv==i)[0] for i in range(len(ud))]
    rng=np.random.default_rng([20260905,k]); out=np.empty(B)
    for b in range(B):
        pick=rng.integers(0,len(ud),len(ud))
        sel=np.concatenate([idx[p] for p in pick])
        out[b]=x[sel].mean()
    return out
def ci(bs,alpha): return float(np.percentile(bs,100*alpha/2)), float(np.percentile(bs,100*(1-alpha/2)))
def yearly(g,ts):
    import time
    yr=np.array([time.gmtime(int(t)).tm_year for t in ts]); o={}
    for y in range(2022,2027):
        m=yr==y
        if m.sum()>50: o[y]=(float(g[m].mean()),sh(g[m]))
    return o
