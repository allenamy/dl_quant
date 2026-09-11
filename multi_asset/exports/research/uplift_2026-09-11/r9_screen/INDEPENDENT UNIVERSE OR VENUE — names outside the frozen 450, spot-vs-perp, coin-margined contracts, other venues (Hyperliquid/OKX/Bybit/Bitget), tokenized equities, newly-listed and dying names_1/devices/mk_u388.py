"""Universe-restriction control: Binance funding EMA masked to EXACTLY the 388 OKX-listed names,
cold-started at the same instant. Isolates 'different venue' from 'smaller universe'.
ENV WHITELIST (E-0826-D) = EMPTY SET."""
import os
_F=("LEGS","CAL","WRULE","LOOK","PHI","UMASK_NPZ","UMASK_SCOPE","FSEED","FPRED","COSTB_JSON",
    "MEMBERS_TOPN","FTRIM","SLOW_NPY","W3FIX","FEMAT_NPZ","OUT_TAG")
assert not [k for k in _F if k in os.environ], [k for k in _F if k in os.environ]
import numpy as np, hashlib, json
OUT="/workspace/r9okx"
fe=np.load(f"{OUT}/fe_mats.npz",allow_pickle=True)
TS=fe["ts"]; SY=np.array([str(x) for x in fe["symbols"]])
OKXM=fe["FE_OKX"]; BC=fe["FE_BINCOLD"]; BW=fe["FE_BINWARM"]
has_okx=np.isfinite(OKXM).any(axis=0)          # the 388 names OKX actually lists
rep={"n_okx_names":int(has_okx.sum())}
for tag,M in (("BINCOLD388",BC),("BINWARM388",BW)):
    X=np.where(has_okx[None,:],M,np.nan).astype(np.float32)
    np.savez_compressed(f"{OUT}/femat_{tag}.npz", ts=TS, symbols=SY, mat=X)
    rep[f"sha16_{tag}"]=hashlib.sha256(open(f"{OUT}/femat_{tag}.npz","rb").read()).hexdigest()[:16]
    rep[f"finite_{tag}"]=float(np.isfinite(X).mean())
# also: OKX values but only where Binance also has a value (identical support) - symmetry check
both=np.isfinite(OKXM)&np.isfinite(BC)
for tag,M in (("OKX_SUP",OKXM),("BINCOLD_SUP",BC)):
    X=np.where(both,M,np.nan).astype(np.float32)
    np.savez_compressed(f"{OUT}/femat_{tag}.npz", ts=TS, symbols=SY, mat=X)
    rep[f"sha16_{tag}"]=hashlib.sha256(open(f"{OUT}/femat_{tag}.npz","rb").read()).hexdigest()[:16]
    rep[f"finite_{tag}"]=float(np.isfinite(X).mean())
print(json.dumps(rep,indent=1)); json.dump(rep,open(f"{OUT}/u388_report.json","w"),indent=1)
