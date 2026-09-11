"""R5 NEW-DATA-4: PRICE-SPACE book features from the ldep array round 2 discarded as redundant.
Source: /workspace/lob_npz = Binance futures bookDepth daily archives, 30s grid, 12 cumulative bands
[-5,-4,-3,-2,-1,-0.2,+0.2,+1,+2,+3,+4,+5]% from mid; lnot=log1p(notional), ldep=log1p(size), float16.
EXACT price inversion (no log1p bias, which is ~1/Q and would be an illiquidity proxy = the round-2 trap):
   p_band = log(expm1(lnot)) - log(expm1(ldep)) = log(VWAP of the cumulative book out to that band)
Window W(i) = [E-14400, E)  (causal, identical to round-2 build_lob2.py). Bands 5/6 (+-0.2%) are NOT used:
they only exist from 2026-01 (verified diag2.py), which would confine any arm to one regime cell.
Features (all scale-free in quantity: multiplying every size by c leaves them unchanged):
  BTILT  = mean( m1 - m5 ),  m_k = (p_bid_k + p_ask_k)/2    near-vs-far book price centre of mass
  PSKEW  = mean( 2*(m1-m5)/(p1a-p1b) )                      the same tilt normalised by near-book price width
  PCURVA = mean( (p5a-p1a) - (p1b-p5b) )                    price-space extension asymmetry (1%->5%)
  MEND   = mean of m1 over [E-1800,E)  (endpoint, for BLEAD; combined with the panel later)
"""
import numpy as np, glob, os, time, json
from multiprocessing import Pool
PW=np.load("/workspace/data/wide_panel_4h_v2ext.npz",allow_pickle=True)
TS=PW["ts"].astype(np.int64); SYM=[str(s) for s in PW["symbols"]]; CI={s:i for i,s in enumerate(SYM)}
OUT="/workspace/uplift_2026-09-11/r5_lob/feat"; os.makedirs(OUT,exist_ok=True)
IB5,IB1,IA1,IA5=0,4,7,11
NOUT=4; MINW=120; MINE=20
def cum(x):
    ok=np.isfinite(x); C=np.zeros(len(x)+1); K=np.zeros(len(x)+1)
    C[1:]=np.cumsum(np.where(ok,x,0.0)); K[1:]=np.cumsum(ok); return C,K
def one(f):
    sym=os.path.basename(f)[:-4]; ci=CI.get(sym)
    if ci is None: return None
    try:
        d=np.load(f); t=d["ts"].astype(np.int64)
        L=np.asarray(d["lnot"],np.float64); D=np.asarray(d["ldep"],np.float64)
    except Exception: return None
    if len(t)<200: return None
    with np.errstate(all="ignore"):
        N=np.expm1(np.clip(L,0,60)); Q=np.expm1(np.clip(D,0,60))
        P=np.where((N>0)&(Q>0),np.log(np.maximum(N,1e-300))-np.log(np.maximum(Q,1e-300)),np.nan)
    p1b,p1a,p5b,p5a=P[:,IB1],P[:,IA1],P[:,IB5],P[:,IA5]
    g=np.isfinite(p1b)&np.isfinite(p1a)&np.isfinite(p5b)&np.isfinite(p5a)&(p1a>p1b)
    m1=np.where(g,0.5*(p1b+p1a),np.nan); m5=np.where(g,0.5*(p5b+p5a),np.nan)
    btilt=m1-m5
    pskew=np.where(g,2.0*btilt/np.maximum(p1a-p1b,1e-9),np.nan)
    pcurva=np.where(g,(p5a-p1a)-(p1b-p5b),np.nan)
    Cb,Kb=cum(btilt); Cs,Ks=cum(pskew); Cc,Kc=cum(pcurva); Cm,Km=cum(m1)
    i0=np.searchsorted(t,TS-14400,"left"); i1=np.searchsorted(t,TS,"left")
    j0=np.searchsorted(t,TS-1800,"left")
    res=np.full((len(TS),NOUT),np.nan)
    with np.errstate(all="ignore"):
        nW=Kb[i1]-Kb[i0]; ok=nW>=MINW
        res[:,0]=np.where(ok,(Cb[i1]-Cb[i0])/np.maximum(nW,1),np.nan)
        ns=Ks[i1]-Ks[i0]; res[:,1]=np.where(ns>=MINW,(Cs[i1]-Cs[i0])/np.maximum(ns,1),np.nan)
        nc=Kc[i1]-Kc[i0]; res[:,2]=np.where(nc>=MINW,(Cc[i1]-Cc[i0])/np.maximum(nc,1),np.nan)
        ne=Km[i1]-Km[j0]; res[:,3]=np.where(ne>=MINE,(Cm[i1]-Cm[j0])/np.maximum(ne,1),np.nan)
    return ci,res.astype(np.float32)
if __name__=="__main__":
    fs=sorted(glob.glob("/workspace/lob_npz/*.npz"))
    M=np.full((len(TS),len(SYM),NOUT),np.nan,np.float32)
    t0=time.time(); done=0; hit=0
    with Pool(12) as p:
        for r in p.imap_unordered(one,fs,chunksize=2):
            done+=1
            if r is not None: ci,res=r; M[:,ci,:]=res; hit+=1
            if done%100==0: print("%d/%d hit=%d %.0fs"%(done,len(fs),hit,time.time()-t0),flush=True)
    names=["BTILT","PSKEW","PCURVA","MEND"]
    for k,nm in enumerate(names):
        np.savez_compressed("%s/%s.npz"%(OUT,nm),symbols=PW["symbols"],ts=TS,mat=M[:,:,k])
    # BLEAD = 4h change of the endpoint book price minus the panel realised 4h trade return
    ME=M[:,:,3].astype(np.float64); dM=np.full(ME.shape,np.nan); dM[1:]=ME[1:]-ME[:-1]
    R4=np.asarray(PW["f_rev_4h"],np.float64)
    BLEAD=(dM-R4).astype(np.float32)
    np.savez_compressed("%s/BLEAD.npz"%OUT,symbols=PW["symbols"],ts=TS,mat=BLEAD)
    cov={nm:float(np.isfinite(M[:,:,k]).mean()) for k,nm in enumerate(names)}
    cov["BLEAD"]=float(np.isfinite(BLEAD).mean())
    yr=np.array([time.gmtime(int(t)).tm_year for t in TS])
    byyear={str(y):{nm:float(np.isfinite(M[yr==y,:,k]).sum(1).mean()) for k,nm in enumerate(names)} for y in [2022,2023,2024,2025,2026]}
    json.dump({"coverage":cov,"names_by_year":byyear,"files_hit":hit,"nfiles":len(fs)},open("%s/COVERAGE.json"%OUT,"w"),indent=1)
    print("DONE",json.dumps(byyear),time.time()-t0,flush=True)
