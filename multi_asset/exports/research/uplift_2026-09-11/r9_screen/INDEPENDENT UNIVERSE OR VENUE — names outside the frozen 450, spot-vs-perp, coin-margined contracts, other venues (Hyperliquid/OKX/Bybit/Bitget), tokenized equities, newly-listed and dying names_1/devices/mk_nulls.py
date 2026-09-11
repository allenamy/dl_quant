"""Turnover-matched nulls on the OKX fund matrix, same two families as
/workspace/uplift_2026-09-11/r3_attack_b9646/null.py (SHIFT_k, RELAB_k). NOT the defective per-anchor
permutation placebo. Purpose here: establish the FLOOR of rho-to-A0 imposed by the book machinery and
the 386-name universe, so we can say whether the candidate's rho=0.35 carries information.
ENV WHITELIST (E-0826-D) = EMPTY SET."""
import os
_F=("LEGS","CAL","WRULE","LOOK","PHI","UMASK_NPZ","UMASK_SCOPE","FSEED","FPRED","COSTB_JSON",
    "MEMBERS_TOPN","FTRIM","SLOW_NPY","W3FIX","FEMAT_NPZ","OUT_TAG")
assert not [k for k in _F if k in os.environ], [k for k in _F if k in os.environ]
import numpy as np, hashlib, json
OUT="/workspace/r9okx"
z=np.load(f"{OUT}/femat_OKX.npz",allow_pickle=True)
TS=z["ts"]; SY=z["symbols"]; M=z["mat"]
rep={}
for k in (101,503,1009):                       # SHIFT: advance the whole matrix by k anchors
    X=np.full_like(M,np.nan); X[k:]=M[:-k]
    p=f"{OUT}/femat_NULLSHIFT{k}.npz"; np.savez_compressed(p,ts=TS,symbols=SY,mat=X)
    rep[f"SHIFT{k}"]=hashlib.sha256(open(p,"rb").read()).hexdigest()[:16]
for k in (1,2,3):                              # RELAB: ONE fixed symbol permutation at every anchor
    rng=np.random.default_rng([20260905,k]); perm=rng.permutation(M.shape[1])
    X=M[:,perm]
    p=f"{OUT}/femat_NULLRELAB{k}.npz"; np.savez_compressed(p,ts=TS,symbols=SY,mat=X)
    rep[f"RELAB{k}"]=hashlib.sha256(open(p,"rb").read()).hexdigest()[:16]
print(json.dumps(rep,indent=1)); json.dump(rep,open(f"{OUT}/nulls_sha.json","w"),indent=1)
