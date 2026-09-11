"""Score-layer rank-IC (step e) for the round-2 LOB features. Accounting y4 from meta_newprod_v4 (RAW arm).
fwd k=0: feature at anchor i vs y4[i] = return over [E_i, E_i+4h).  bwd k=-1: vs y4[i-1] (the bar the window covers)."""
import numpy as np, json, calendar
MT=np.load("/workspace/review_scratch/refute_C6_2/altrun/meta_newprod_v4.npz",allow_pickle=True)
E=MT["E_ts"].astype(np.int64); Y=np.asarray(MT["y4"],np.float64); 
PW=np.load("/workspace/data/wide_panel_4h_v2ext.npz",allow_pickle=True)
ts=PW["ts"].astype(np.int64); sym=[str(s) for s in PW["symbols"]]
# VERIFIED not assumed: y4 column axis == panel symbol axis. Evidence (cmd /tmp/nm2.py):
# corr(panel Y4[i], y4[idx[i]]) = 0.9601 over 3.43e6 cells and corr(panel f_rev_4h[i], y4[idx[i]-1]) = 0.9588
# over 3.45e6 cells => same 829-column order AND y4[i] is the FORWARD 4h return from E_i.
assert Y.shape[1]==len(sym), (Y.shape,len(sym))
pos={int(t):i for i,t in enumerate(E)}
idx=np.array([pos.get(int(t),-1) for t in ts])
assert (idx>=0).all(), "panel anchor not in accounting axis"
FE1=np.asarray(PW["f_fund_ema_v1"],float); BASE=np.isfinite(FE1)
def rz(M):
    out=np.full(M.shape,np.nan)
    for i in range(M.shape[0]):
        v=M[i]; ok=np.isfinite(v); n=ok.sum()
        if n>=10: out[i,ok]=np.argsort(np.argsort(v[ok]))/max(n-1,1)-0.5
    return out
ZF=rz(np.where(BASE,FE1,np.nan))
def orth(Z):
    R=np.full(Z.shape,np.nan)
    for i in range(Z.shape[0]):
        ok=np.isfinite(Z[i])&np.isfinite(ZF[i])
        if ok.sum()<10: continue
        x=ZF[i][ok]; y=Z[i][ok]; vx=float((x*x).sum())
        b=float((x*y).sum()/vx) if vx>1e-12 else 0.0
        R[i][ok]=y-b*x
    return R
def ic(Z,k,lo,hi):
    """mean per-anchor Spearman between Z[i] and y4 at accounting row idx[i]+k"""
    vals=[]
    for i in range(len(ts)):
        if ts[i]<lo or ts[i]>=hi: continue
        j=idx[i]+k
        if j<0 or j>=len(E): continue
        a=Z[i]; b=Y[j]
        ok=np.isfinite(a)&np.isfinite(b)
        n=ok.sum()
        if n<20: continue
        ra=np.argsort(np.argsort(a[ok])).astype(float); rb=np.argsort(np.argsort(b[ok])).astype(float)
        ra-=ra.mean(); rb-=rb.mean()
        d=np.sqrt((ra*ra).sum()*(rb*rb).sum())
        if d>0: vals.append(float((ra*rb).sum()/d))
    v=np.array(vals)
    return (float(v.mean()), float(v.std(ddof=1)/np.sqrt(len(v))), len(v)) if len(v)>5 else (float("nan"),float("nan"),len(v))
def T(*a): return calendar.timegm(a+(0,)*(6-len(a)))
FULL=(T(2022,1,1),T(2026,8,10,20)+1)
LOB="/workspace/uplift_2026-09-11/r2/lob2"
F=["LDVOL","LIVOL","LSLASY","LDTREND","LCONVX","LDINNOV","LIMBINN","LDVOLR","_R1MEAN"]
out={}
# coverage / span
cov=None
for nm in F:
    z=np.load("%s/%s.npz"%(LOB,nm),allow_pickle=True); M=np.where(BASE,np.asarray(z["mat"],np.float64),np.nan)
    nfin=np.isfinite(M).sum(1)
    if nm=="LDVOL":
        first=int(np.argmax(nfin>=100)); out["_span"]={"first_anchor_ge100names":int(ts[first]),"n_from_there":int((ts>=ts[first]).sum())}
    Z=rz(M); ZO=orth(Z)
    e={"cov":float(np.isfinite(M).mean()),"median_names":float(np.median(nfin[nfin>0]))}
    for k in [0,-1,-2]:
        m,s,n=ic(Z,k,*FULL); e["raw_ic_k%d"%k]=[round(m,5),round(s,5),n]
        m,s,n=ic(ZO,k,*FULL); e["orth_ic_k%d"%k]=[round(m,5),round(s,5),n]
    out[nm]=e
    print(nm,json.dumps(e),flush=True)
# reference: amihud, orth amihud
AM=np.where(BASE,np.asarray(PW["f_amihud_24h"],float),np.nan)
for nm,Z in [("f_amihud_24h",rz(AM)),("ORTH_f_amihud_24h",orth(rz(AM)))]:
    e={}
    for k in [0,-1,-2]:
        m,s,n=ic(Z,k,*FULL); e["ic_k%d"%k]=[round(m,5),round(s,5),n]
    out[nm]=e; print(nm,json.dumps(e),flush=True)
json.dump(out,open("/workspace/uplift_2026-09-11/r2/IC_r2.json","w"),indent=1)
print("IC DONE")
