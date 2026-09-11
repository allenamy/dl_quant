"""Round-2 reduction library. Statistic copied verbatim from judge_v4 semantics:
g = net_ex / gross_total, bps per anchor per unit gross. Paired per anchor, UTC-day block bootstrap
2000 resamples, rng numpy.default_rng([20260905, k])."""
import numpy as np, json
COLS=None
def load(p):
    global COLS
    A=np.load(p,allow_pickle=True)
    c=[str(x) for x in A["cols"]]; COLS={n:i for i,n in enumerate(c)}
    R=A["d30_n2_c42_rec"] if "d30_n2_c42_rec" in A.files else A["rec"]
    return R
def gser(R):
    C=COLS
    return R[:,C["ts"]].astype(np.int64), R[:,C["net_ex"]]/R[:,C["gross_total"]]*1.0
def parts(R):
    C=COLS; gt=R[:,C["gross_total"]]
    return dict(net=R[:,C["net_ex"]]/gt, pnl=R[:,C["pnl_ex"]]/gt,
                carry=R[:,C["carry_ex"]]/gt, cost=R[:,C["cost_ex"]]/gt, turn=R[:,C["turnover"]]/gt)
# windows (ts are ms epoch)
def msk(ts,a,b):
    import datetime as dt
    f=lambda s: int(dt.datetime.strptime(s,"%Y-%m-%d").replace(tzinfo=dt.timezone.utc).timestamp())
    return (ts>=f(a))&(ts<f(b))
W={"full":("2022-01-31","2026-09-01"),        # n=10039
   "full22":("2022-01-01","2026-08-11"),      # n=9918
   "frozen":("2025-03-01","2026-08-11"),      # n=3168
   "y2024on":("2024-01-01","2026-08-11"),
   "oos":("2026-08-11","2026-09-01")}         # n=121
# NOTE: rec ts are UNIX SECONDS (verified: rec[0,0]=1643587200 = 2022-01-31 00:00Z; rec[-1,0]=1788134400 = 2026-08-31 00:00Z)
ANN=np.sqrt(2190.0)
def sharpe(g):
    g=g[np.isfinite(g)]
    return float(g.mean()/g.std(ddof=1)*ANN) if len(g)>2 and g.std(ddof=1)>0 else float("nan")
def daykey(ts):
    return (ts//86400).astype(np.int64)
def boot(d,ts,k,n=2000):
    """paired difference d per anchor -> CI95 by UTC-day block bootstrap"""
    ok=np.isfinite(d); d=d[ok]; ts=ts[ok]
    dk=daykey(ts); ud,inv=np.unique(dk,return_inverse=True)
    idx=[np.where(inv==i)[0] for i in range(len(ud))]
    rng=np.random.default_rng([20260905,k])
    out=np.empty(n)
    for b in range(n):
        pick=rng.integers(0,len(ud),len(ud))
        out[b]=np.concatenate([idx[p] for p in pick]).size and d[np.concatenate([idx[p] for p in pick])].mean()
    return float(np.percentile(out,2.5)),float(np.percentile(out,97.5))
def years(ts,g):
    import datetime as dt
    yr=np.array([dt.datetime.fromtimestamp(t,dt.timezone.utc).year for t in ts])
    return {int(y):float(np.nansum(g[yr==y])) for y in np.unique(yr)}
