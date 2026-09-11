"""A/B/C/D families: 1h / 12h / 3d lookback + funding at other horizons. All ORTHOGONALISED vs the deployed fund rank."""
import numpy as np, sys, os
from multiprocessing import Pool
sys.path.insert(0,"/workspace/uplift_2026-09-11/r2_horizon")
from common import *
F=np.load(R+"/feats_r2.npz",allow_pickle=True)
assert np.array_equal(F["ts"].astype(np.int64),TS)
g=lambda k: np.asarray(F[k],np.float64)
IVf=np.where(np.isfinite(PW["f_fund_iv"])&(np.asarray(PW["f_fund_iv"])>0),np.asarray(PW["f_fund_iv"],np.float64),8.0)
RN8=np.nan_to_num(np.asarray(PW["f_fund_now"],np.float64),nan=0.0)*(8.0/IVf)
RN8=np.where(np.isfinite(np.asarray(PW["f_fund_now"])),RN8,np.nan)
FE2=np.asarray(PW["f_fund_ema_v2"],np.float64)
def lagrank(Z,L):
    o=np.full(Z.shape,np.nan); o[L:]=Z[:-L]; return o
ZRN=ZR(RN8); ZFE2=ZR(FE2)
RAW={
 "A_REV1H":   -g("RET_SUM_12"),
 "A_VOL1H":    g("RET_MSQ_12"),
 "A_TBF1H":    g("TBF_MEAN_12"),
 "A_AMI1H":    g("RET_MABS_12")/np.exp(g("LQV_MEAN_12")),
 "A_QVS1H":    g("LQV_MEAN_12")-g("LQV_MEAN_288"),
 "A_CPOS1H":   g("CPOS_MEAN_12"),
 "B_REV12H":  -g("RET_SUM_144"),
 "B_AMI12H":   g("RET_MABS_144")/np.exp(g("LQV_MEAN_144")),
 "B_TBF12H":   g("TBF_MEAN_144"),
 "C_AMI3D":    g("RET_MABS_864")/np.exp(g("LQV_MEAN_864")),
 "C_TBF3D":    g("TBF_MEAN_864"),
 "C_QVTR3D":   g("LQV_MEAN_864")-g("LQV_MEAN_8640"),
 "D_FCHG12H":  ZRN-lagrank(ZRN,3),
 "D_FCHG3D":   ZRN-lagrank(ZRN,18),
 "D_FSLOPE":   ZF-ZFE2,
}
rng=np.random.default_rng(20260911)
PERM=np.full(ZF.shape,np.nan)
for i in range(ZF.shape[0]):
    ok=np.isfinite(ZF[i])
    if ok.sum()>=10:
        v=ZF[i,ok].copy(); rng.shuffle(v); PERM[i,ok]=v
JOBS=[]
for nm,X in RAW.items():
    O=orth(X)
    JOBS.append((nm+"__p",fill(O)[0]))
    JOBS.append((nm+"__m",fill(-O)[0]))
JOBS.append(("PL_ORTHPERM__p",fill(orth(PERM))[0]))
JOBS.append(("PL_ORTHPERM__m",fill(-orth(PERM))[0]))
def work(a):
    tag,M=a; return run(tag,M,SLCOM,None,keepW=False)
if __name__=="__main__":
    only=sys.argv[1:]
    JJ=[j for j in JOBS if not only or any(o in j[0] for o in only)]
    print("arms:",len(JJ),flush=True)
    with Pool(6) as p:
        for r in p.imap_unordered(work,JJ): pass
    print("DONE")
