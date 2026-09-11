import numpy as np, sys, json
sys.path.insert(0,"/workspace/uplift_2026-09-11/r2_horizon")
from stats import *
KD=48
t0,R0=load("A0_dyn_s42"); g0=gser(R0)
def full(tag):
    ts,Rr=load(tag); m=maskw(ts,"full"); G=Rr[m,C["gross_total"]]; gg=gser(Rr)[m]
    return dict(ts=ts[m],g=gg,mean=float(gg.mean()),sh=sh(gg),
      pnl=float((Rr[m,C["pnl_ex"]]/G).mean()),carry=float((Rr[m,C["carry_ex"]]/G).mean()),
      cost=float((Rr[m,C["cost_ex"]]/G).mean()),turn=float(Rr[m,C["turnover"]].mean()))
print("=== A3 slow-hold arms, placebos, cost stress (full cycle 2022-01-31..2026-08-31, n=10039) ===")
print("%-18s %8s %7s %8s %8s %8s %8s %8s %8s %8s"%("arm","bps","Sh","pnl","carry","cost","turn","corrA0","B48lo","B48hi"))
for tg in ["C_AMI3D__p","A3_AMI3D_MA6__p","A3_AMI3D_MA18__p","C_TBF3D__p","A3_TBF3D_MA6__p","A3_TBF3D_MA18__p","PLF_AMI3D__p","PLF_TBF3D__p","CS_AMI3D__p","CS_TBF3D__p","CS_A0ref","A0_dyn_s42"]:
    d=full(tg); k=abs(hash(tg))%100000; bs=boot(d["g"],d["ts"],k)
    blo,bhi=ci(bs,0.05/KD); cr=float(np.corrcoef(d["g"],g0[maskw(t0,"full")])[0,1])
    print("%-18s %+8.3f %+7.2f %+8.3f %+8.3f %+8.4f %8.4f %+8.3f %+8.3f %+8.3f"%(tg,d["mean"],d["sh"],d["pnl"],d["carry"],d["cost"],d["turn"],cr,blo,bhi))
print()
print("=== multi-window for the two leads ===")
print("%-18s %-8s %6s %8s %7s"%("arm","win","n","bps","Sh"))
for tg in ["A0_dyn_s42","C_AMI3D__p","A3_AMI3D_MA18__p","C_TBF3D__p"]:
    ts,Rr=load(tg); gg=gser(Rr)
    for w in ["full","frozen","2024on","ext"]:
        m=maskw(ts,w); print("%-18s %-8s %6d %+8.3f %+7.2f"%(tg,w,m.sum(),gg[m].mean(),sh(gg[m])))
print()
print("=== IN-BOOK dose: paired delta vs A0 (same anchors), full cycle and frozen ===")
print("%-10s %-8s %+9s %-22s %-22s %8s"%("arm","win","dmean","CI95","BONF48","turn"))
m0f=maskw(t0,"full")
for tg in ["IB_AMI25","IB_AMI50","IB_AMI75","IB_TBF25","IB_TBF50","IB_TBF75"]:
    ts,Rr=load(tg); gg=gser(Rr); assert (ts==t0).all()
    for w in ["full","frozen"]:
        m=maskw(ts,w); d=gg[m]-g0[m]
        k=abs(hash(tg+w))%100000; bs=boot(d,ts[m],k)
        lo,hi=ci(bs,0.05); blo,bhi=ci(bs,0.05/KD)
        print("%-10s %-8s %+9.3f [%+0.3f,%+0.3f]        [%+0.3f,%+0.3f]        %8.4f"%(tg,w,d.mean(),lo,hi,blo,bhi,Rr[m,C["turnover"]].mean()))
print()
print("=== yearly (bps/anchor/gross) ===")
for tg in ["A0_dyn_s42","C_AMI3D__p","A3_AMI3D_MA18__p","C_TBF3D__p","IB_AMI50","IB_TBF50"]:
    ts,Rr=load(tg); y=yearly(gser(Rr),ts)
    print("%-18s "%tg+"  ".join("%d %+0.3f"%(a,b[0]) for a,b in y.items()))
