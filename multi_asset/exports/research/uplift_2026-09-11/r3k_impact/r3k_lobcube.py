"""R3-CRITICAL-1 step A: causal per-anchor LOB depth cube from /workspace/lob_npz.
Binance bookDepth semantics (confirmed from /workspace/f10/lob_consolidate_pod.py L28-38 and
100%-monotone check): lnot[:,j] = log1p(CUMULATIVE quote notional within |bands[j]| percent of mid,
on the side given by the sign of bands[j]).  Window = [E-3600, E)  (causal, same rule as
/workspace/uplift_2026-09-11/build_lob.py which the round-1 LOB axis used)."""
import numpy as np, glob, os, time, json
from multiprocessing import Pool
PW=np.load("/workspace/data/wide_panel_4h_v2ext.npz",allow_pickle=True)
TS=PW["ts"].astype(np.int64); SYM=[str(s) for s in PW["symbols"]]
CI={s:i for i,s in enumerate(SYM)}
OUT="/workspace/uplift_2026-09-11/r3k"
os.makedirs(OUT,exist_ok=True)
MINSNAP=20
def one(f):
    sym=os.path.basename(f)[:-4]
    ci=CI.get(sym)
    if ci is None: return None
    try: d=np.load(f)
    except Exception: return None
    t=d["ts"].astype(np.int64)
    N=np.expm1(np.clip(np.asarray(d["lnot"],np.float32),0,60)).astype(np.float64)  # cumulative notional USDT
    lo=np.searchsorted(t,TS-3600,"left"); hi=np.searchsorted(t,TS,"left")
    n=len(TS); res=np.full((n,12),np.nan,np.float32)
    C=np.zeros((len(t)+1,12)); K=np.zeros((len(t)+1,12))
    ok=np.isfinite(N)
    C[1:]=np.cumsum(np.where(ok,N,0.0),0); K[1:]=np.cumsum(ok,0)
    for i in range(n):
        a,b=lo[i],hi[i]
        if b-a<MINSNAP: continue
        cnt=K[b]-K[a]
        good=cnt>=MINSNAP
        if not good.any(): continue
        m=np.where(good,(C[b]-C[a])/np.maximum(cnt,1),np.nan)
        res[i]=m
    return ci,res
if __name__=="__main__":
    fs=sorted(glob.glob("/workspace/lob_npz/*.npz"))
    M=np.full((len(TS),len(SYM),12),np.nan,np.float32)
    t0=time.time(); done=0; hit=0
    with Pool(12) as p:
        for r in p.imap_unordered(one,fs,chunksize=2):
            done+=1
            if r is not None:
                ci,res=r; M[:,ci,:]=res; hit+=1
            if done%100==0: print(f"{done}/{len(fs)} matched={hit} {time.time()-t0:.0f}s",flush=True)
    np.savez(OUT+"/lobcube.npz",ts=TS,symbols=PW["symbols"],bands=np.array([-5,-4,-3,-2,-1,-0.2,0.2,1,2,3,4,5],np.float32),cum=M)
    yr=np.array([time.gmtime(int(t)).tm_year for t in TS])
    cov={str(y): float(np.isfinite(M[yr==y,:,6]).sum(1).mean()) for y in sorted(set(yr.tolist()))}
    print("LOBCUBE DONE matched_symbols=%d  mean names with ask0.2 by year=%s  %.0fs"%(hit,json.dumps(cov),time.time()-t0))
    json.dump({"matched_symbols":hit,"mean_names_by_year":cov,"MINSNAP":MINSNAP},open(OUT+"/LOBCUBE_COV.json","w"),indent=1)
