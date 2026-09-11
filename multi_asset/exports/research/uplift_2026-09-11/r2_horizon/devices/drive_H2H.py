"""Head-to-head, identical anchors, bitwise-parity injection: round-1 XIB_LAG50 vs my IB_AMI50 vs both."""
import numpy as np, sys
from multiprocessing import Pool
sys.path.insert(0,"/workspace/uplift_2026-09-11/r2_horizon")
from common import *
F=np.load(R+"/feats_r2.npz",allow_pickle=True); g=lambda k: np.asarray(F[k],np.float64)
AMI3D=g("RET_MABS_864")/np.exp(g("LQV_MEAN_864"))
ZA3=ZR(orth(AMI3D))
AM24=np.asarray(PW["f_amihud_24h"],np.float64)
ZA24=ZR(AM24)
ZLAG=np.full_like(ZA24,np.nan); ZLAG[1:]=ZA24[:-1]        # round-1 XIB_LAG50: 24h window ends one anchor before E
JOBS=[("H_LAG50",fill(0.5*ZF+0.5*ZLAG)[0]),
      ("H_AMI50",fill(0.5*ZF+0.5*ZA3)[0]),
      ("H_BOTH",fill(0.5*ZF+0.25*ZLAG+0.25*ZA3)[0]),
      ("H_AM24_50",fill(0.5*ZF+0.5*ZA24)[0])]
def work(a): return run(a[0],a[1],IBCOM,None,keepW=False)
if __name__=="__main__":
    with Pool(4) as p:
        for r in p.imap_unordered(work,JOBS): pass
    print("DONE")
