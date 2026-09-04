import numpy as np, time, sys
PD="probe_artifacts"
def load(tag):
    z=np.load(f"{PD}/w10_{tag}.npz",allow_pickle=True); cols=[str(c) for c in z["cols"]]; rec=z["d30_n2_c42_rec"]; g=lambda k: rec[:,cols.index(k)].astype(float)
    return rec[:,cols.index("ts")].astype(np.int64), g("net_ex"), g("w3_king"), g("w3_fund")
yr=lambda ts: np.array([time.gmtime(int(t)).tm_year for t in ts])
def yearly(tag,lab):
    ts,ne,wk,wf=load(tag); Y=yr(ts); row=[]
    for y in range(2022,2027):
        s=Y==y; x=2.0*ne[s]/1e4; eq=np.cumprod(1+x); row.append(f"{y} {eq[-1]**(2190/len(x))-1:+.0%}/S{x.mean()/(x.std()+1e-12)*np.sqrt(2190):.2f}")
    s=Y>=2023; x=2.0*ne[s]/1e4; s2=Y>=2025; x2=2.0*ne[s2]/1e4
    print(f"  [{lab}] "+" | ".join(row)+f" || 2023+ S{x.mean()/x.std()*np.sqrt(2190):.2f} DD{(np.cumprod(1+x)/np.maximum.accumulate(np.cumprod(1+x))-1).min():.0%} | 2025-26 S{x2.mean()/x2.std()*np.sqrt(2190):.2f} | 席位 fund 均 2023+ {wf[s].mean():.2f}")
for tag,lab in sys.argv[1:] and [a.split("=",1) for a in sys.argv[1:]] or []: yearly(tag,lab)
