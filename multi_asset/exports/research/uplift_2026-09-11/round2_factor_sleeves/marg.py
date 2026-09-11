"""Marginal value of each round-2 candidate ON TOP of the round-1 state {A0, R1_ORTH_amihud},
equal-unit-vol fixed weights (no fitting). Paired block-bootstrap CI on the Sharpe difference
is not well defined, so we report the level/Sharpe and the paired g-difference CI."""
import numpy as np, sys
sys.path.insert(0,"/workspace/uplift_2026-09-11/r2_factor")
import lib2 as L
R="/workspace/uplift_2026-09-11/r2_factor"
A0p="/workspace/review_scratch/health_check/dev_v4/probe_artifacts/w10_ablation_series_V4_A0_dyn_s42.npz"
A=L.load(A0p); ts,g0=L.gser(A)
def get(p):
    Rr=L.load(p); t,g=L.gser(Rr); assert np.array_equal(t,ts); return g
ANN=np.sqrt(2190.0); m=L.msk(ts,*L.W["full22"])
AMI=get("/workspace/uplift_2026-09-11/trackD_v4/SL_ORTH_f_amihud_24h__p.npz")
C={"AMIRESID__p":get(R+"/out/SL2_ORTH_AMIRESID__p.npz"),
   "ASZSTAB__p":get(R+"/out/SL2_ORTH_ASZSTAB__p.npz"),
   "RESSKEW__m":get(R+"/out/SL2_ORTH_RESSKEW__m.npz"),
   "RESMOM_42__p":get(R+"/out/SL2_ORTH_RESMOM_42__p.npz"),
   "LIQSTAB__p":get(R+"/out/SL2_ORTH_LIQSTAB__p.npz")}
def blend(xs):
    xs=[x/np.nanstd(x[m]) for x in xs]; return sum(xs)/len(xs)
def sr(x): x=x[np.isfinite(x)]; return float(x.mean()/x.std(ddof=1)*ANN)
base=blend([g0,AMI]); sb=sr(base[m])
print("ROUND-1 STATE  A0 + R1_ORTH_amihud (equal unit-vol)   SR = %+0.3f   (SE %.2f)"%(sb,np.sqrt(2190/m.sum())))
print("adding each round-2 candidate as a third equal-unit-vol sleeve:")
for k,v in C.items():
    nb=blend([g0,AMI,v]); d=(nb-base)[m]
    lo,hi=L.boot(d,ts[m],21)
    print("  + %-14s SR %+0.3f  (dSR %+0.3f)   paired dg %+0.5f CI95 [%+0.5f,%+0.5f]"%(
        k,sr(nb[m]),sr(nb[m])-sb,np.nanmean(d),lo,hi))
nb=blend([g0,AMI,C["RESSKEW__m"],C["ASZSTAB__p"]])
print("  + RESSKEW + ASZSTAB together              SR %+0.3f  (dSR %+0.3f)"%(sr(nb[m]),sr(nb[m])-sb))
