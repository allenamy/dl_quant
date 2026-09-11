"""Mandatory placebo battery (methodology c) + in-book blend for the two near-misses."""
import numpy as np, os, sys, time
sys.path.insert(0,"/workspace/uplift_2026-09-11/r2_factor")
from drive import rz, orth, permute, run, SLCOM, IBCOM, B, FT, R
ZF=np.load(FT+"/_ZFUND.npy").astype(np.float64)
JOBS=[]
for fam,sgn,tg in (("RESSKEW",-1.0,"m"),("ASZSTAB",1.0,"p")):
    F=np.where(B,sgn*np.load(FT+"/"+fam+".npy").astype(np.float64),np.nan)
    Z=rz(F)
    JOBS += [("SL2_PERMFEAT_%s__%s"%(fam,tg), orth(rz(permute(F,20260911))), SLCOM),
             ("SL2_PERMORTH_%s__%s"%(fam,tg), orth(rz(permute(Z,20260912))), SLCOM),
             ("IB2_%s50"%fam,                  0.5*ZF+0.5*Z,                  IBCOM)]
t0=time.time()
for tag,M,com in JOBS:
    print("%-28s %s  %6.1fs"%(tag,run(tag,M,com),time.time()-t0),flush=True)
print("DONE")
