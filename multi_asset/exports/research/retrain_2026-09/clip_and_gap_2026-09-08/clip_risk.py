"""Restated LEVEL and RISK for the default citation arm, with the clip corrected on the 135 affected anchors."""
import numpy as np, time, calendar
COLS=["ts","net","pnl","carry","cost","gross_total","gross_member","gross_sel","nsel","nmember","fires","leg_king","leg_rev24","leg_fund","w3_king","w3_rev24","w3_fund","turnover","net_ex","pnl_ex","carry_ex","cost_ex","netlong"]
C={c:i for i,c in enumerate(COLS)}; CUT=calendar.timegm((2026,8,10,20,0,0)); APY=2190
D=np.load("/workspace/review_scratch/clip_restate.npz")["out"]
dmap={int(r[0]):r[1] for r in D}
def load(tag):
    A=np.load("/workspace/review_scratch/health_check/dev_alt/probe_artifacts/w10_ablation_series_%s.npz"%tag,allow_pickle=True)
    R=A["d30_n2_c42_rec"]; ts=R[:,C["ts"]].astype(np.int64)
    g=R[:,C["net_ex"]]/R[:,C["gross_total"]]
    return ts,g
def stats(ts,g,lab):
    m=ts<=CUT; t=ts[m]; x=g[m]
    yr=np.array([time.gmtime(int(v)).tm_year for v in t])
    out={}
    for name,sel in [("2022",yr==2022),("2023",yr==2023),("2024",yr==2024),("2025",yr==2025),
                     ("2026",yr==2026),("2024-26",t>=calendar.timegm((2024,1,1,0,0,0))),("full",np.ones(len(t),bool))]:
        v=x[sel]; s=float(v.mean()/v.std(ddof=1)*np.sqrt(APY)) if v.std(ddof=1)>0 else float("nan")
        r=v/1e4*2.0   # NAV returns at 2x
        nav=np.cumprod(1+r); dd=1-nav/np.maximum.accumulate(nav)
        d=t[sel]//86400; ud,inv=np.unique(d,return_inverse=True)
        dayr=np.array([np.prod(1+r[inv==k])-1 for k in range(len(ud))])
        out[name]=(len(v),float(v.mean()),s,100*float(dd.max()),100*float(dayr.min()),int((dayr<=-0.0268).sum()),int((dayr<=-0.04).sum()))
    return out
for tag in ["M1_UCRYPTO_prod_s42_ccal","M1_UCRYPTO_prod_s2027_ccal"]:
    ts,g=load(tag); g2=g.copy()
    n=0
    for i,t in enumerate(ts):
        if int(t) in dmap: g2[i]=g[i]+dmap[int(t)]; n+=1
    a=stats(ts,g,"rec"); b=stats(ts,g2,"true")
    print("\n===== %s  (%d anchors corrected) ====="%(tag,n))
    print("%-8s %6s | %-34s | %-34s"%("window","n","RECORDED  bps/anch  S  maxDD%  wDay%  n268 n4","CLIP-CORRECTED"))
    for k in ["2022","2023","2024","2025","2026","2024-26","full"]:
        A=a[k]; B=b[k]
        print("%-8s %6d | %+7.4f %5.2f %6.2f %7.2f %3d %2d | %+7.4f %5.2f %6.2f %7.2f %3d %2d"%(
            k,A[0],A[1],A[2],A[3],A[4],A[5],A[6],B[1],B[2],B[3],B[4],B[5],B[6]))
