import numpy as np, sys
sys.path.insert(0,"/workspace/uplift_2026-09-11/r2_horizon")
from stats import *
KD=48
t0,R0=load("A0_dyn_s42"); g0=gser(R0)
W="full9918"
print("standalone on %s:"%W)
for tg in ["A_REV1H__p","A_VOL1H__p","D_FCHG3D__m","E_MA6","E_BASE","C_TBF3D__p","C_AMI3D__p","PL_ORTHPERM__p","PLF_AMI3D__p","PLF_TBF3D__p"]:
    ts,Rr=load(tg); m=maskw(ts,W); gg=gser(Rr)[m]; G=Rr[m,C["gross_total"]]
    k=abs(hash(tg+W))%100000; bs=boot(gg,ts[m],k); lo,hi=ci(bs,0.05); blo,bhi=ci(bs,0.05/KD)
    cr=np.corrcoef(gg,g0[maskw(t0,W)])[0,1]
    cx=-(Rr[m,C["carry_ex"]]/G).mean()/gg.mean()
    y=yearly(gser(Rr),ts); npos=sum(1 for v in y.values() if v[0]>0)
    print("%-16s %+7.3f Sh %+5.2f corrA0 %+0.3f carryfrac %+7.3f yrs %d/5 CI95[%+0.3f,%+0.3f] B48[%+0.3f,%+0.3f]"%(
        tg,gg.mean(),sh(gg),cr,cx,npos,lo,hi,blo,bhi))
print()
print("in-book IB_TBF50 on %s:"%W)
ts,Rr=load("IB_TBF50"); m=maskw(ts,W); d=gser(Rr)[m]-g0[m]
bs=boot(d,ts[m],7777); lo,hi=ci(bs,0.05)
print("   dmean %+0.3f CI95 [%+0.3f,%+0.3f]"%(d.mean(),lo,hi))
