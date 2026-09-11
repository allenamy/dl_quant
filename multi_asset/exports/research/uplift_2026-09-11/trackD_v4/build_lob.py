"""Causal 4h LOB panel from /workspace/lob_npz (PREREG AMENDMENT 2). Window = [E-3600, E)."""
import numpy as np, glob, os, sys, time, json
from multiprocessing import Pool
PW=np.load("/workspace/data/wide_panel_4h_v2ext.npz",allow_pickle=True)
TS=PW["ts"].astype(np.int64); SYM=[str(s) for s in PW["symbols"]]
CI={s:i for i,s in enumerate(SYM)}
OUT="/workspace/uplift_2026-09-11/lob"
os.makedirs(OUT,exist_ok=True)
IB1,IA1,IB5,IA5 = 4,7,0,11   # bands [-5,-4,-3,-2,-1,-0.2,0.2,1,2,3,4,5]
def one(f):
    sym=os.path.basename(f)[:-4]
    ci=CI.get(sym)
    if ci is None: return None
    try: d=np.load(f)
    except Exception: return None
    t=d["ts"].astype(np.int64); L=np.asarray(d["lnot"],np.float32)
    N=np.expm1(np.clip(L,0,60))
    lo=np.searchsorted(t,TS-3600,"left"); hi=np.searchsorted(t,TS,"left")
    n=len(TS)
    res=np.full((n,4),np.nan,np.float32)
    cols=[IB1,IA1,IB5,IA5]
    C=np.zeros((len(t)+1,4)); K=np.zeros((len(t)+1,4))
    for a,c in enumerate(cols):
        v=N[:,c]; ok=np.isfinite(v)
        C[1:,a]=np.cumsum(np.where(ok,v,0.0)); K[1:,a]=np.cumsum(ok)
    for i in range(n):
        a,b=lo[i],hi[i]
        if b-a<20: continue
        cnt=K[b]-K[a]
        if (cnt<20).any(): continue
        m=(C[b]-C[a])/cnt     # mean notional in each of the 4 bands
        b1,a1,b5,a5=m
        s1=b1+a1; s5=b5+a5
        if s1<=0 or s5<=0: continue
        res[i,0]=(b1-a1)/s1
        res[i,1]=(b5-a5)/s5
        res[i,2]=np.log(s5/s1)
        res[i,3]=np.log(s1)
    return ci,res
if __name__=="__main__":
    fs=sorted(glob.glob("/workspace/lob_npz/*.npz"))
    M=np.full((len(TS),len(SYM),4),np.nan,np.float32)
    t0=time.time(); done=0
    with Pool(8) as p:
        for r in p.imap_unordered(one,fs,chunksize=4):
            done+=1
            if r is not None:
                ci,res=r; M[:,ci,:]=res
            if done%100==0: print(f"{done}/{len(fs)} {time.time()-t0:.0f}s",flush=True)
    names=["LOBIMB1","LOBIMB5","LOBSLOPE","LOBDEPTH"]
    for k,nm in enumerate(names):
        np.savez_compressed(f"{OUT}/{nm}.npz",symbols=PW["symbols"],ts=TS,mat=M[:,:,k])
    # causal 7-day (42-anchor) innovation of IMB1
    A=M[:,:,0].astype(np.float64); D=np.full(A.shape,np.nan,np.float32)
    C=np.zeros((A.shape[0]+1,A.shape[1])); K=np.zeros_like(C)
    ok=np.isfinite(A); C[1:]=np.cumsum(np.where(ok,A,0.0),0); K[1:]=np.cumsum(ok,0)
    for i in range(42,A.shape[0]):
        cnt=K[i]-K[i-42]; mu=np.where(cnt>=10,(C[i]-C[i-42])/np.maximum(cnt,1),np.nan)
        D[i]=(A[i]-mu).astype(np.float32)
    np.savez_compressed(f"{OUT}/LOBIMB1D.npz",symbols=PW["symbols"],ts=TS,mat=D)
    cov={nm: float(np.isfinite(M[:,:,k]).mean()) for k,nm in enumerate(names)}
    yr=np.array([time.gmtime(int(t)).tm_year for t in TS])
    byyear={str(y): float(np.isfinite(M[yr==y,:,0]).sum(1).mean()) for y in [2022,2023,2024,2025,2026]}
    json.dump({"coverage":cov,"mean_names_with_LOBIMB1_by_year":byyear},open(f"{OUT}/COVERAGE.json","w"),indent=1)
    print("LOB PANEL DONE", json.dumps(byyear), time.time()-t0)
