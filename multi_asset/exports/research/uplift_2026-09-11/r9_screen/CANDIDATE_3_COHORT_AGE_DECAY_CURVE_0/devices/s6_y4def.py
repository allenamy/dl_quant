#!/usr/bin/env python3
"""E-0904-F GUARD. The surveyor CLAIMED (unverified) that meta_newprod_v4.npz y4 is
prod(1+ret5)-1 over bars E+1..E+48, window [E+5m, E+4h+5m). Verify against the pinned holefix2
5m cache -- do not trust the claim, and do not infer from any filename. ENV WHITELIST = EMPTY SET."""
import os, json, zipfile, hashlib
import numpy as np
_CE=["LEGS","PHI","CAL","MEMBERS_TOPN","COSTB_JSON","PANEL_IN","V2","OUT_TAG"]
assert sorted([k for k in _CE if k in os.environ])==[]
def _f(*a,**k): raise AssertionError("E-0904-F guard: no env var may be read")
os.environ.get=_f
C5="/workspace/data/dlnative_5m_wide829_f16_holefix2.npz"
META="/workspace/review_scratch/refute_C6_2/altrun/meta_newprod_v4.npz"
z=np.load(C5, allow_pickle=True)
ts5=z["ts"].astype(np.int64); sym5=[str(s) for s in z["symbols"]]; ch=[str(c) for c in z["ch"]]
print("ch =",ch,flush=True)
D=z["data"]; print("data",D.shape,D.dtype,flush=True)
MT=np.load(META,allow_pickle=True); E_ts=MT["E_ts"].astype(np.int64); y4=np.asarray(MT["y4"])
# locate the return channel WITHOUT guessing from position: match by channel name
cand=[i for i,c in enumerate(ch) if c.lower() in ("ret","ret5","r","logret","close_ret")]
print("return-channel candidates by name:",[(i,ch[i]) for i in cand],flush=True)
r5i = cand[0] if cand else 0
rmap={int(t):k for k,t in enumerate(ts5)}
rng=np.random.default_rng([20260905,7])
out={"ch":ch,"data_shape":list(D.shape),"return_channel_index":int(r5i),"return_channel_name":ch[r5i],
     "sha256_16_cache":hashlib.sha256(open(C5,'rb').read()).hexdigest()[:16] if False else "not_hashed_5.7GB",
     "forms":{}}
res={"SUM_E1_E48":[], "PROD_E1_E48":[], "SUM_E0_E47":[], "PROD_E0_E47":[]}
nchk=0
idxs=rng.choice(np.arange(2000,len(E_ts)-1),size=300,replace=False)
for i in idxs:
    k=rmap.get(int(E_ts[i]))
    if k is None or k+49>len(ts5): continue
    cols=rng.choice(829,size=12,replace=False)
    y=y4[i,cols].astype(np.float64)
    a=D[k+1:k+49, cols, r5i].astype(np.float64)     # E+1..E+48
    b=D[k:k+48,   cols, r5i].astype(np.float64)     # E..E+47
    for nm,arr,fn in (("SUM_E1_E48",a,lambda x:np.nansum(x,0)),
                      ("PROD_E1_E48",a,lambda x:np.nanprod(1+x,0)-1),
                      ("SUM_E0_E47",b,lambda x:np.nansum(x,0)),
                      ("PROD_E0_E47",b,lambda x:np.nanprod(1+x,0)-1)):
        v=fn(arr); ok=np.isfinite(y)&np.isfinite(v)
        if ok.any(): res[nm].append(np.abs(v[ok]-y[ok]))
    nchk+=1
for nm,L in res.items():
    if L:
        v=np.concatenate(L); out["forms"][nm]={"n":int(len(v)),"median_abs_err":float(np.median(v)),
            "p90_abs_err":float(np.percentile(v,90)),"max_abs_err":float(v.max())}
out["anchors_checked"]=nchk
out["VERDICT"]=min(out["forms"],key=lambda k:out["forms"][k]["median_abs_err"])
open("/workspace/uplift_2026-09-11/r9_screen/Y4DEF_r9screen.json","w").write(json.dumps(out,indent=1))
print(json.dumps(out,indent=1))
