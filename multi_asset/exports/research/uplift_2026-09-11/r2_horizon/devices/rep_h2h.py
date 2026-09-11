import numpy as np, sys
sys.path.insert(0,"/workspace/uplift_2026-09-11/r2_horizon")
from stats import *
KD=48
t0,R0=load("A0_dyn_s42"); g0=gser(R0)
print("%-10s %-9s %6s %+8s %-24s %-24s %8s %8s"%("arm","win","n","dmean","CI95","BONF48","turn","Sh(arm)"))
for tg in ["H_LAG50","H_AM24_50","H_AMI50","H_BOTH","IB_AMI50"]:
    ts,Rr=load(tg); gg=gser(Rr); assert (ts==t0).all()
    for w in ["full9918","full","frozen","ext"]:
        m=maskw(ts,w); d=gg[m]-g0[m]
        k=abs(hash(tg+w))%100000; bs=boot(d,ts[m],k)
        lo,hi=ci(bs,0.05); blo,bhi=ci(bs,0.05/KD)
        print("%-10s %-9s %6d %+8.3f [%+0.3f,%+0.3f]            [%+0.3f,%+0.3f]            %8.4f %+8.2f"%(
            tg,w,m.sum(),d.mean(),lo,hi,blo,bhi,Rr[m,C["turnover"]].mean(),sh(gg[m])))
print()
print("A0 on both full windows:")
for w in ["full9918","full"]:
    m=maskw(t0,w); print("   %-9s n=%d mean %+0.3f Sh %+0.2f turn %0.4f"%(w,m.sum(),g0[m].mean(),sh(g0[m]),R0[m,C["turnover"]].mean()))
print()
print("yearly of the in-book arms:")
for tg in ["A0_dyn_s42","H_LAG50","H_AMI50","H_BOTH"]:
    ts,Rr=load(tg); y=yearly(gser(Rr),ts); print("%-10s "%tg+"  ".join("%d %+0.3f"%(a,b[0]) for a,b in y.items()))
