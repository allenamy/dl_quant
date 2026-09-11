import numpy as np, sys, glob, os
sys.path.insert(0,"/workspace/uplift_2026-09-11/r2_horizon")
from stats import *
t0,R0=load("A0_dyn_s42"); g0=gser(R0)
m0=maskw(t0,"full")
def dec(tg):
    ts,Rr=load(tg); m=maskw(ts,"full"); G=Rr[m,C["gross_total"]]
    return dict(net=(Rr[m,C["net_ex"]]/G).mean(),pnl=(Rr[m,C["pnl_ex"]]/G).mean(),
                carry=(Rr[m,C["carry_ex"]]/G).mean(),cost=(Rr[m,C["cost_ex"]]/G).mean(),
                turn=Rr[m,C["turnover"]].mean())
print("%-16s %8s %8s %8s %8s %8s %10s"%("arm","net","pnl","carry","cost","turn","cost/turn"))
for tg in ["A0_dyn_s42","E_BASE","PL_ORTHPERM__p","PL_ORTHPERM__m","A_REV1H__p","A_REV1H__m","A_AMI1H__p","B_AMI12H__p","C_AMI3D__p","C_TBF3D__p","C_TBF3D__m","A_VOL1H__p","A_VOL1H__m","B_TBF12H__p","D_FCHG3D__m"]:
    d=dec(tg)
    print("%-16s %+8.3f %+8.3f %+8.3f %+8.4f %8.4f %10.3f"%(tg,d["net"],d["pnl"],d["carry"],d["cost"],d["turn"],d["cost"]/d["turn"]))
# round-1 comparison: correlation of my AMI arms to round-1 ORTH_amihud sleeve
T1="/workspace/uplift_2026-09-11/trackD_v4"
import os
for cand in ["SL_ORTH_f_amihud_24h__p","SL_ORTH_f_asz_24h__m","SL_f_tbf_24h__p","SL_ORTH_D_SURP__m"]:
    p=T1+"/"+cand+".npz"
    if not os.path.exists(p): print("missing",cand); continue
    A=np.load(p,allow_pickle=True); Rr=np.asarray(A["rec"],float); ts=np.round(Rr[:,0]).astype(np.int64)
    g=Rr[:,C["net_ex"]]/Rr[:,C["gross_total"]]; m=maskw(ts,"full")
    print("\nROUND1 %-26s full %+0.3f Sh %+0.2f turn %0.4f corrA0 %+0.3f"%(cand,g[m].mean(),sh(g[m]),Rr[m,C["turnover"]].mean(),np.corrcoef(g[m],g0[m0])[0,1]))
    for tg in ["A_AMI1H__p","B_AMI12H__p","C_AMI3D__p","C_TBF3D__p","B_TBF12H__p","A_VOL1H__p","D_FCHG3D__m"]:
        ts2,R2=load(tg); g2=gser(R2); m2=maskw(ts2,"full")
        print("    corr to %-14s %+0.3f"%(tg,np.corrcoef(g[m],g2[m2])[0,1]))
