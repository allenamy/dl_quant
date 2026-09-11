import numpy as np, json, time, calendar
PA="/workspace/review_scratch/health_check/dev_v4/probe_artifacts"
def T(*x): return calendar.timegm(x+(0,)*(6-len(x)))
FW=(T(2025,3,1), T(2026,8,10,20))
def load(tag, arm):
    z=np.load(f"{PA}/w10_ablation_series_V4_{tag}.npz",allow_pickle=True)
    cols=[str(c) for c in z["cols"]]; rec=z[f"{arm}_rec"].astype(float)
    d={c:rec[:,i] for i,c in enumerate(cols)}
    d["ts"]=rec[:,cols.index("ts")].astype(np.int64)
    return d
def sh(x,npy=2190):
    x=np.asarray(x,float); x=x[np.isfinite(x)]
    return x.mean()/x.std(ddof=1)*np.sqrt(npy) if len(x)>2 else float("nan")
for tag in ("A0_dyn_s42","A0_dyn_s2027","A1_dyn_s42"):
    for arm in ("S0","d30_n2_c42"):
        d=load(tag,arm); ts=d["ts"]
        u=d["net_ex"]/d["gross_total"]
        m=(ts>=FW[0])&(ts<=FW[1])
        ne=d["net_ex"][m].mean(); gt=d["gross_total"][m].mean()
        print("%-14s %-12s n=%5d  mean_u=%+.4f  sharpe=%+.3f  net_ex=%+.5f gross=%.4f" % (tag,arm,m.sum(),u[m].mean(),sh(u[m]),ne,gt))
    # yearly per-gross % for d30
    d=load(tag,"d30_n2_c42"); ts=d["ts"]; u=d["net_ex"]/d["gross_total"]
    yr=np.array([time.gmtime(int(t)).tm_year for t in ts])
    out={}
    for y in range(2022,2027):
        s=(yr==y)
        if y==2026: s=s&(ts<=FW[1])
        out[y]=round(float(np.nansum(u[s]))*100,2)
    print("   d30 by_year cum %%gross:",out)
