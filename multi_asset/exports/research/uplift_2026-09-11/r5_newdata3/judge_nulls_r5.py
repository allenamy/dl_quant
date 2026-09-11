"""r5nd/judge_nulls_r5.py -- TURNOVER-MATCHED NULL BATTERY, pairwise, statistic and bootstrap verbatim
from r4_p1/b1_pairwise.py. Reports BOTH pnl_ex (gross of carry and cost) and g (net), plus turnover,
so a margin that is really a churn-cost margin cannot hide. E-0911-A: first 900 device rows dropped."""
import numpy as np, json, sys
R="/workspace/uplift_2026-09-11/r5nd"; O=R+"/arms"
def rd(p):
    Z=np.load(p,allow_pickle=True); Rr=np.asarray(Z["rec"],float); ix={str(c):i for i,c in enumerate(Z["cols"])}
    ts=Rr[:,ix["ts"]].astype(np.int64); gt=Rr[:,ix["gross_total"]]
    g=np.where(gt>0,Rr[:,ix["net_ex"]]/np.maximum(gt,1e-12),np.nan)
    p_=np.where(gt>0,Rr[:,ix["pnl_ex"]]/np.maximum(gt,1e-12),np.nan)
    return ts,g,p_,Rr[:,ix["turnover"]]
def ep(s): return int((np.datetime64(s)-np.datetime64("1970-01-01T00:00:00"))/np.timedelta64(1,"s"))
SP={"FULL_pw":(ep("2022-01-01T00:00"),ep("2026-08-10T20:00"))}
def ser(tag,st,sd,sp):
    ts,g,p_,to=rd(O+"/R5S_%s_%s_s%s.npz"%(tag,st,sd)); lo,hi=SP[sp]
    m=(ts>=lo)&(ts<=hi)&np.isfinite(g); m[:900]=False
    return ts[m],g[m],p_[m],to[m]
def db(ts):
    d=(ts//86400).astype(np.int64); u,inv=np.unique(d,return_inverse=True); return [np.where(inv==i)[0] for i in range(len(u))]
def boot(dg,ts,k,B=2000):
    bl=db(ts); rng=np.random.default_rng([20260905,k]); nb=len(bl); mo=np.empty(B)
    for b in range(B): mo[b]=dg[np.concatenate([bl[i] for i in rng.integers(0,nb,nb)])].mean()
    return [round(float(np.percentile(mo,2.5)),4),round(float(np.percentile(mo,97.5)),4)]
FAM={"SL_AGE50":["N50_SHIFT101","N50_SHIFT503","N50_SHIFT1009","N50_RELAB1","N50_RELAB2","N50_RELAB3"],
     "SL_AGEMOD100":["NM_SHIFT101","NM_SHIFT503","NM_SHIFT1009","NM_RELAB1","NM_RELAB2","NM_RELAB3"]}
OUT={}
for BASE,NUL in FAM.items():
    print("\n######",BASE)
    print("%-8s %-4s %-14s %6s %8s %8s %9s %-20s %8s %8s %-20s %8s"%(
        "seat","seed","null","n","base_g","null_g","dg","dg_CI95","base_pnl","null_pnl","dpnl_CI95","d_turn"))
    for st in ("dyn","fix"):
        for sd in ("42","2027"):
            tb,gb,pb,tob=ser(BASE,st,sd,"FULL_pw")
            wins_g=True; wins_p=True
            for j,a in enumerate(NUL):
                ta,ga,pa,toa=ser(a,st,sd,"FULL_pw"); ts=np.intersect1d(tb,ta)
                ib=np.searchsorted(tb,ts); ia=np.searchsorted(ta,ts)
                dg=gb[ib]-ga[ia]; dp=pb[ib]-pa[ia]
                cig=boot(dg,ts,k=j); cip=boot(dp,ts,k=j+10)
                wins_g&= (dg.mean()>0); wins_p&= (dp.mean()>0)
                print("%-8s %-4s %-14s %6d %8.4f %8.4f %+9.4f %-20s %8.4f %8.4f %-20s %+8.5f"%(
                    st,sd,a,len(ts),gb[ib].mean(),ga[ia].mean(),dg.mean(),str(cig),
                    pb[ib].mean(),pa[ia].mean(),str(cip),tob[ib].mean()-toa[ia].mean()))
                OUT["%s|%s|s%s|%s"%(BASE,st,sd,a)]={"n":len(ts),"base_g":round(float(gb[ib].mean()),4),
                    "null_g":round(float(ga[ia].mean()),4),"dg":round(float(dg.mean()),4),"dg_CI95":cig,
                    "base_pnl_ex":round(float(pb[ib].mean()),4),"null_pnl_ex":round(float(pa[ia].mean()),4),
                    "dpnl_CI95":cip,"d_turnover":round(float(tob[ib].mean()-toa[ia].mean()),5)}
            OUT["%s|%s|s%s|BEATS_ALL"%(BASE,st,sd)]={"g":bool(wins_g),"pnl_ex":bool(wins_p)}
            print("   -> beats all nulls on g:",wins_g," on pnl_ex:",wins_p)
json.dump(OUT,open(R+"/JUDGE_nulls_r5.json","w"),indent=1)
print("NULLS_JUDGE_DONE")
