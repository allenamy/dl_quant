import numpy as np, json, time, calendar, csv
PA="/workspace/review_scratch/health_check/dev_v4/probe_artifacts"
RT="/workspace/codex_research/uplift_regime_v4.csv"
def T(*x): return calendar.timegm(x+(0,)*(6-len(x)))
FW=(T(2025,3,1), T(2026,8,10,20))
def book(tag="A0_dyn_s42", arm="d30_n2_c42"):
    z=np.load(f"{PA}/w10_ablation_series_V4_{tag}.npz",allow_pickle=True)
    cols=[str(c) for c in z["cols"]]; rec=z[f"{arm}_rec"].astype(float)
    d={c:rec[:,i] for i,c in enumerate(cols)}
    d["ts"]=rec[:,cols.index("ts")].astype(np.int64)
    d["u"]=d["net_ex"]/d["gross_total"]
    d["cfg"]=json.loads(str(z["config_json"]))
    return d
def regime():
    rows=list(csv.DictReader(open(RT)))
    out={"ts":np.array([int(r["ts"]) for r in rows],dtype=np.int64)}
    for k in rows[0]:
        if k=="ts": continue
        out[k]=np.array([float(r[k]) if r[k] not in ("","nan","NaN") else np.nan for r in rows])
    return out
def sharpe(x,npy=2190):
    x=np.asarray(x,float); x=x[np.isfinite(x)]
    if len(x)<3 or x.std(ddof=1)==0: return float("nan")
    return float(x.mean()/x.std(ddof=1)*np.sqrt(npy))
def se_sharpe(n,npy=2190): return float(np.sqrt(npy/max(n,1)))
def trail_mean(x,K):
    x=np.asarray(x,float); out=np.full(len(x),np.nan)
    v=np.nan_to_num(x,nan=0.0); f=np.isfinite(x).astype(float)
    cs=np.concatenate([[0.],np.cumsum(v)]); cf=np.concatenate([[0.],np.cumsum(f)])
    for t in range(K,len(x)):
        c=cf[t]-cf[t-K]
        if c>=max(3,K//2): out[t]=(cs[t]-cs[t-K])/c
    return out
def trail_std(x,K):
    x=np.asarray(x,float); out=np.full(len(x),np.nan)
    for t in range(K,len(x)):
        w=x[t-K:t]; w=w[np.isfinite(w)]
        if len(w)>=max(3,K//2): out[t]=w.std(ddof=1)
    return out
def trail_pct(x,Kroll,Kref):
    rm=trail_mean(x,Kroll); n=len(x); out=np.full(n,np.nan)
    for t in range(Kref+Kroll,n):
        h=rm[t-Kref:t]; h=h[np.isfinite(h)]; c=rm[t]
        if len(h)>=Kref//2 and np.isfinite(c): out[t]=float((h<=c).mean())
    return out
def maxdd(cum):
    pk=np.maximum.accumulate(cum); return float(np.max(pk-cum))
