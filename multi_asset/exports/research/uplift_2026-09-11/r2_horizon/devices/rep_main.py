import numpy as np, sys, json, glob, os
sys.path.insert(0,"/workspace/uplift_2026-09-11/r2_horizon")
from stats import *
K_DECL=44
t0,R0=load("A0_dyn_s42"); g0=gser(R0)
tags=sorted(os.path.basename(p)[:-4] for p in glob.glob(R+"/out/*.npz"))
tags=[t for t in tags if t.startswith(("A_","B_","C_","D_","PL_"))]
out={}
print("%-16s %+8s %7s %7s %8s %8s %7s %8s %8s %8s %7s"%("arm","fullbps","Sh","yrs+","corrA0","carry%","turn","CIlo","CIhi","Blo","Bhi"))
for tg in tags:
    ts,Rr=load(tg); g=gser(Rr)
    m=maskw(ts,"full")
    gm=g[m]; tsm=ts[m]
    yr=yearly(g,ts); nyp=sum(1 for v in yr.values() if v[0]>0)
    cf=Rr[m,C["carry_ex"]].sum()/Rr[m,C["net_ex"]].sum()
    cr=float(np.corrcoef(gm,g0[m])[0,1])
    k=abs(hash(tg))%100000
    bs=boot(gm,tsm,k)
    lo,hi=ci(bs,0.05); blo,bhi=ci(bs,0.05/K_DECL)
    out[tg]=dict(full=float(gm.mean()),sharpe=sh(gm),yrs=nyp,corr=cr,carry=float(cf),
                 turn=float(Rr[m,C["turnover"]].mean()),ci=[lo,hi],bonf=[blo,bhi],
                 yearly={str(a):b[0] for a,b in yr.items()})
    print("%-16s %+8.3f %+7.2f %5d/5 %+8.3f %+8.2f %7.4f %+8.3f %+8.3f %+8.3f %+8.3f"%(tg,gm.mean(),sh(gm),nyp,cr,cf,Rr[m,C["turnover"]].mean(),lo,hi,blo,bhi))
json.dump(out,open(R+"/RESULT_abcd.json","w"),indent=1)
