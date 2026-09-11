"""AMENDMENT 2 extension: TBF horizon ladder 7d/14d/30d + AMI7D. K 36 -> 44."""
import numpy as np, sys
from multiprocessing import Pool
sys.path.insert(0,"/workspace/uplift_2026-09-11/r2_horizon")
from common import *
F=np.load(R+"/feats_r2b.npz",allow_pickle=True); assert np.array_equal(F["ts"].astype(np.int64),TS)
g=lambda k: np.asarray(F[k],np.float64)
RAW={"C_TBF7D":g("TBF_MEAN_2016"),"C_TBF14D":g("TBF_MEAN_4032"),"C_TBF30D":g("TBF_MEAN_8640"),
     "C_AMI7D":g("RET_MABS_2016")/np.exp(g("LQV_MEAN_2016"))}
JOBS=[]
for nm,X in RAW.items():
    O=orth(X); JOBS.append((nm+"__p",fill(O)[0])); JOBS.append((nm+"__m",fill(-O)[0]))
def work(a): return run(a[0],a[1],SLCOM,None,keepW=False)
if __name__=="__main__":
    with Pool(8) as p:
        for r in p.imap_unordered(work,JOBS): pass
    print("DONE")
