"""Placebos (methodology c) + in-book blend for the one arm that cleared standalone SR>=1.5,
plus a raw (un-orthogonalised) contrast."""
import numpy as np, os, sys, json, time
sys.path.insert(0,"/workspace/uplift_2026-09-11/r2_factor")
from drive import rz, orth, permute, run, SLCOM, IBCOM, B, FT, R
F=np.where(B,np.load(FT+"/AMIRESID.npy").astype(np.float64),np.nan)
ZF=np.load(FT+"/_ZFUND.npy").astype(np.float64)
Z=rz(F)
JOBS=[
 ("SL2_PERMFEAT_AMIRESID__p", orth(rz(permute(F,20260911))), SLCOM),   # placebo 1: permuted FEATURE, then orth
 ("SL2_PERMORTH_AMIRESID__p", orth(rz(permute(Z,20260912))), SLCOM),   # placebo 2: orth operator on a permuted rank
 ("SL2_RAW_AMIRESID__p",      Z,                              SLCOM),   # un-orthogonalised contrast
 ("IB2_PARITY",               ZF,                             IBCOM),   # must reproduce A0
 ("IB2_AMIRESID50",           0.5*ZF+0.5*Z,                   IBCOM),
 ("IB2_AMIRESID25",           0.75*ZF+0.25*Z,                 IBCOM),
]
t0=time.time()
for tag,M,com in JOBS:
    print("%-28s %s  %6.1fs"%(tag,run(tag,M,com),time.time()-t0),flush=True)
print("DONE")
