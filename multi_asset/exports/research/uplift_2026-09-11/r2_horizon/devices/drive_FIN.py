"""Amendment-3 arms + placebos + cost stress + in-book dose."""
import numpy as np, sys, os
from multiprocessing import Pool
sys.path.insert(0,"/workspace/uplift_2026-09-11/r2_horizon")
from common import *
F=np.load(R+"/feats_r2.npz",allow_pickle=True)
g=lambda k: np.asarray(F[k],np.float64)
AMI3D=g("RET_MABS_864")/np.exp(g("LQV_MEAN_864"))
TBF3D=g("TBF_MEAN_864")
O_AMI=orth(AMI3D); O_TBF=orth(TBF3D)
def ma(Z,N):
    o=np.full(Z.shape,np.nan)
    for i in range(Z.shape[0]):
        with np.errstate(all="ignore"): o[i]=np.nanmean(Z[max(0,i-N+1):i+1],0)
    return o
rng=np.random.default_rng(20260912)
def perm(X):
    P=np.full(X.shape,np.nan)
    for i in range(X.shape[0]):
        ok=BASE[i]&np.isfinite(X[i])
        if ok.sum()>=10:
            v=X[i,ok].copy(); rng.shuffle(v); P[i,ok]=v
    return P
CBI="/workspace/uplift_2026-09-11/attack_trackD_newalpha/costb_illiq.json"
SL_IL=[x for x in SLCOM if not x.startswith("COSTB_JSON")]+["COSTB_JSON="+CBI]
JOBS=[]
# A3 candidates: slower holding of the two orthogonalised sleeves
for nm,O in [("AMI3D",O_AMI),("TBF3D",O_TBF)]:
    for N in (6,18):
        JOBS.append(("A3_%s_MA%d__p"%(nm,N),fill(ma(O,N))[0],SLCOM,None))
# placebos (not candidates)
JOBS.append(("PLF_AMI3D__p",fill(orth(perm(AMI3D)))[0],SLCOM,None))
JOBS.append(("PLF_TBF3D__p",fill(orth(perm(TBF3D)))[0],SLCOM,None))
# cost stress (same arms, illiquidity-scaled tiers)
JOBS.append(("CS_AMI3D__p",fill(O_AMI)[0],SL_IL,None))
JOBS.append(("CS_TBF3D__p",fill(O_TBF)[0],SL_IL,None))
JOBS.append(("CS_A0ref",FE1,[x for x in IBCOM if not x.startswith("COSTB_JSON")]+["COSTB_JSON="+CBI],None))
# in-book dose: fund leg score -> (1-w)*rank(fund) + w*orth-sleeve rank
for w in (0.25,0.5,0.75):
    JOBS.append(("IB_TBF%02d"%int(w*100),fill((1-w)*ZF+w*ZR(O_TBF))[0],IBCOM,None))
    JOBS.append(("IB_AMI%02d"%int(w*100),fill((1-w)*ZF+w*ZR(O_AMI))[0],IBCOM,None))
def work(a): return run(a[0],a[1],a[2],a[3],keepW=False)
if __name__=="__main__":
    with Pool(8) as p:
        for r in p.imap_unordered(work,JOBS): pass
    print("DONE")
