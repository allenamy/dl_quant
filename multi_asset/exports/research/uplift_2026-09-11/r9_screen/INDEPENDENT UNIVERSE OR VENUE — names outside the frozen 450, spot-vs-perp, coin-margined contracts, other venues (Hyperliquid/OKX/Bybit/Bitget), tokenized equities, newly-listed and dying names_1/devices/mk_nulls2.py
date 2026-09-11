"""CIRCULAR SHIFT nulls confined to the rows where the OKX matrix is finite, so the null keeps the
same number of live anchors as the real arm (a plain forward shift pushed the 560-row OKX block off
the end of the axis - SHIFT503 and SHIFT1009 came out byte-identical, which is the tell).
ENV WHITELIST (E-0826-D) = EMPTY SET."""
import os
_F=("LEGS","CAL","WRULE","LOOK","PHI","UMASK_NPZ","UMASK_SCOPE","FSEED","FPRED","COSTB_JSON",
    "MEMBERS_TOPN","FTRIM","SLOW_NPY","W3FIX","FEMAT_NPZ","OUT_TAG")
assert not [k for k in _F if k in os.environ], [k for k in _F if k in os.environ]
import numpy as np, hashlib, json
OUT="/workspace/r9okx"
z=np.load(f"{OUT}/femat_OKX.npz",allow_pickle=True); TS=z["ts"]; SY=z["symbols"]; M=z["mat"]
live=np.where(np.isfinite(M).any(axis=1))[0]
a,b=int(live[0]),int(live[-1])+1
rep={"live_rows":[a,b],"n_live":b-a}
for k in (53,101,251):
    X=M.copy(); X[a:b]=np.roll(M[a:b],k,axis=0)
    p=f"{OUT}/femat_NULLCSHIFT{k}.npz"; np.savez_compressed(p,ts=TS,symbols=SY,mat=X)
    rep[f"CSHIFT{k}"]=hashlib.sha256(open(p,"rb").read()).hexdigest()[:16]
print(json.dumps(rep,indent=1)); json.dump(rep,open(f"{OUT}/nulls2_sha.json","w"),indent=1)
