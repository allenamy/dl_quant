import numpy as np, sys
sys.path.insert(0,"/workspace/uplift_2026-09-11/r2_horizon")
from stats import *
t0,R0=load("A0_dyn_s42"); g0=gser(R0)
print("%-12s %-8s %8s %7s %8s %8s %8s %8s"%("arm","win","bps","Sharpe","turn","carry%","cost","corrA0"))
rows={}
for tag in ["E_BASE","E_MA3","E_MA6","E_MA18","E_STEP3","E_STEP6","E_STEP18"]:
    ts,Rr=load(tag); g=gser(Rr); assert (ts==t0).all()
    rows[tag]=(ts,Rr,g)
    for w in ["full","frozen"]:
        m=maskw(ts,w)
        cf=Rr[m,C["carry_ex"]].sum()/Rr[m,C["net_ex"]].sum()
        cs=Rr[m,C["cost_ex"]].sum()/Rr[m,C["gross_total"]][m].sum() if False else (Rr[m,C["cost_ex"]]/Rr[m,C["gross_total"]]).mean()
        cr=np.corrcoef(g[m],g0[m])[0,1]
        print("%-12s %-8s %+8.3f %+7.2f %8.4f %+8.2f %8.4f %+8.3f"%(tag,w,g[m].mean(),sh(g[m]),Rr[m,C["turnover"]].mean(),cf,cs,cr))
print()
print("yearly bps/anchor/gross")
for tag in rows:
    ts,Rr,g=rows[tag]; y=yearly(g,ts)
    print("%-12s "%tag+" ".join("%d %+0.3f"%(k,v[0]) for k,v in y.items()))
