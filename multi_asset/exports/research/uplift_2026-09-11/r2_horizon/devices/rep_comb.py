import numpy as np, sys, itertools
sys.path.insert(0,"/workspace/uplift_2026-09-11/r2_horizon")
from stats import *
t0,R0=load("A0_dyn_s42")
def G(tag,w="full9918"):
    ts,Rr=load(tag); m=maskw(ts,w); return gser(Rr)[m]
W="full9918"
NM=["A0_dyn_s42","C_AMI3D__p","A3_AMI3D_MA18__p","C_TBF3D__p","A_VOL1H__p","D_FCHG3D__m"]
S={n:G(n,W) for n in NM}
print("correlation matrix of standalone g series, %s (n=%d)"%(W,len(S[NM[0]])))
print("%-18s"%""+"".join("%12s"%n[:11] for n in NM))
for a in NM:
    print("%-18s"%a[:18]+"".join("%+12.3f"%np.corrcoef(S[a],S[b])[0,1] for b in NM))
print()
print("standalone Sharpe (SE=%.2f):"%np.sqrt(2190/len(S[NM[0]])))
for n in NM: print("   %-20s %+0.3f bps  Sh %+0.2f"%(n,S[n].mean(),sh(S[n])))
print()
print("equal-weight multi-book arithmetic (each book pays its own cost = lower bound):")
for combo in [("A0_dyn_s42","C_AMI3D__p"),("A0_dyn_s42","C_TBF3D__p"),
              ("A0_dyn_s42","C_AMI3D__p","C_TBF3D__p"),
              ("A0_dyn_s42","A3_AMI3D_MA18__p","C_TBF3D__p")]:
    x=np.mean([S[c] for c in combo],0)
    print("   %-50s mean %+0.3f Sh %+0.2f"%(" + ".join(c[:14] for c in combo),x.mean(),sh(x)))
print()
print("in-book deployable forms, %s:"%W)
for tg in ["A0_dyn_s42","H_LAG50","H_AMI50","H_BOTH"]:
    x=G(tg,W); print("   %-12s mean %+0.3f Sh %+0.2f  (SE %.2f)"%(tg,x.mean(),sh(x),np.sqrt(2190/len(x))))
