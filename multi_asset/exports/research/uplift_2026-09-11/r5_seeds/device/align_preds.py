"""ROUND 5: align the NEW homogeneous (V2=1) draws onto the v4 DL axis. align() VERBATIM from build_dev_v4.py.
Also: assert my V2=1 control seed 42 reproduces the ARCHIVED in-service pred array BITWISE, and print the
sha256 of every draw so the object identity of each seed is a receipt, not a seed number."""
import numpy as np, os, sys, json, hashlib
from scipy.stats import rankdata
R="/workspace/uplift_2026-09-11/r5_seeds"; DST=R+"/f8x/preds"
HCP="/workspace/review_scratch/health_check/dev_v4/f8_2026-08-22/preds"
ARCH="/workspace/f8_ext/preds"
EX=np.load("/workspace/dlw_ext/data/dlw_targets.npz",allow_pickle=True)["E_ts"].astype(np.int64)
tt=np.load("/workspace/dlw_v4raw/data/dlw_targets.npz",allow_pickle=True)["E_ts"].astype(np.int64)
def align(P,src_E,dst_E):
    o=np.full((len(dst_E),P.shape[1]),np.nan,np.float32)
    r={int(t):i for i,t in enumerate(src_E)}
    for k,t in enumerate(dst_E):
        i=r.get(int(t))
        if i is not None: o[k]=P[i]
    return o
def sha(p): return hashlib.sha256(open(p,"rb").read()).hexdigest()[:16]
OUT={"draws":{}}
# ---- control: my V2=1 seed 42 must equal the archived in-service pred bitwise ----
myc=R+"/f8_s42/preds/f10_V2MAIN_s42.npy"
arc=ARCH+"/f10_V2MAIN_s42.npy"
A=np.load(myc); B=np.load(arc)
OUT["control_s42"]={"mine_sha":sha(myc),"archived_sha":sha(arc),
  "bitwise_equal":bool(A.shape==B.shape and np.array_equal(np.isnan(A),np.isnan(B)) and np.array_equal(A[~np.isnan(A)],B[~np.isnan(B)]))}
print("CONTROL s42 V2=1 full-whitelist vs ARCHIVED in-service:",OUT["control_s42"])
for S in ("7","101","1234","31337"):
    p=R+"/f8_s%s/preds/f10_V2MAIN_s%s.npy"%(S,S)
    assert os.path.exists(p),p
    Y=np.load(p); assert Y.shape[0]==len(EX),(Y.shape,len(EX))
    q=DST+"/f10_A0_s%s.npy"%S
    np.save(q,align(Y,EX,tt))
    OUT["draws"]["s"+S]={"raw":p,"raw_sha":sha(p),"aligned":q,"aligned_sha":sha(q)}
    print("aligned s%s raw_sha %s"%(S,sha(p)),flush=True)
for S in ("42","2027"):
    OUT["draws"]["s"+S]={"raw":ARCH+"/f10_V2MAIN_s%s.npy"%S,"raw_sha":sha(ARCH+"/f10_V2MAIN_s%s.npy"%S),
                         "aligned":HCP+"/f10_A0_s%s.npy"%S,"aligned_sha":sha(HCP+"/f10_A0_s%s.npy"%S)}
# ---- prediction-layer dispersion among the HOMOGENEOUS set ----
REF={}
for S in ("42","2027","7","101","1234","31337"):
    q=DST+"/f10_A0_s%s.npy"%S
    REF["s"+S]=np.load(q if os.path.exists(q) else HCP+"/f10_A0_s%s.npy"%S)
def xr(A,B):
    cs=[]
    for i in range(A.shape[0]):
        ok=np.isfinite(A[i])&np.isfinite(B[i])
        if ok.sum()<50: continue
        a=rankdata(A[i][ok]); b=rankdata(B[i][ok]); sa,sb=a.std(),b.std()
        if sa>0 and sb>0: cs.append(float(((a-a.mean())*(b-b.mean())).mean()/(sa*sb)))
    return float(np.mean(cs))
ks=["s42","s2027","s7","s101","s1234","s31337"]
M={}
print("\n=== per-anchor cross-sectional rank corr, HOMOGENEOUS (V2=1) draws ===")
print("%-8s"%""+"".join("%10s"%k for k in ks))
for a in ks:
    row=[]
    for b in ks:
        if a==b: row.append(1.0); continue
        key=tuple(sorted((a,b)))
        if key not in M: M[key]=xr(REF[a],REF[b])
        row.append(M[key])
    print("%-8s"%a+"".join("%10.4f"%v for v in row))
OUT["dl_rank_corr"]={"%s|%s"%k:v for k,v in M.items()}
json.dump(OUT,open(R+"/receipts/ALIGN.json","w"),indent=1,default=str)
print("ALIGN_DONE")
