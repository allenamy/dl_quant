"""FEASIBILITY: is a PRICE-SPACE book signal recoverable from ldep, given float16 + log1p storage?
Decisive test: book-implied log price change over 4h vs the panel realised 4h return."""
import numpy as np, glob, os, time
from multiprocessing import Pool
P=np.load("/workspace/data/wide_panel_4h_v2ext.npz",allow_pickle=True)
TS=P["ts"].astype(np.int64); SYM=[str(s) for s in P["symbols"]]; CI={s:i for i,s in enumerate(SYM)}
Y4=np.asarray(P["f_rev_4h"],np.float64)
IB1,IA1,IB5,IA5=4,7,0,11
def one(f):
    sym=os.path.basename(f)[:-4]; ci=CI.get(sym)
    if ci is None: return None
    d=np.load(f); t=d["ts"].astype(np.int64)
    if len(t)<5000: return None
    L=np.asarray(d["lnot"],np.float64); D=np.asarray(d["ldep"],np.float64)
    # implied log VWAP per band (log1p bias ~ 1/Q, guarded by Q threshold)
    Q1b=np.expm1(np.clip(D[:,IB1],0,60)); Q1a=np.expm1(np.clip(D[:,IA1],0,60))
    p1b=L[:,IB1]-D[:,IB1]; p1a=L[:,IA1]-D[:,IA1]
    p5b=L[:,IB5]-D[:,IB5]; p5a=L[:,IA5]-D[:,IA5]
    g=(Q1b>1e4)&(Q1a>1e4)&np.isfinite(p1b)&np.isfinite(p1a)&np.isfinite(p5b)&np.isfinite(p5a)
    m1=np.where(g,0.5*(p1b+p1a),np.nan); m5=np.where(g,0.5*(p5b+p5a),np.nan)
    def cum(x):
        ok=np.isfinite(x); C=np.zeros(len(x)+1); K=np.zeros(len(x)+1)
        C[1:]=np.cumsum(np.where(ok,x,0.0)); K[1:]=np.cumsum(ok); return C,K
    C1,K1=cum(m1); C5,K5=cum(m5)
    # END window = last 30 min before E
    i0=np.searchsorted(t,TS-1800,"left"); i1=np.searchsorted(t,TS,"left")
    n=K1[i1]-K1[i0]
    mm1=np.where(n>=20,(C1[i1]-C1[i0])/np.maximum(n,1),np.nan)
    n5=K5[i1]-K5[i0]
    mm5=np.where(n5>=20,(C5[i1]-C5[i0])/np.maximum(n5,1),np.nan)
    return ci,mm1,mm5
if __name__=="__main__":
    fs=sorted(glob.glob("/workspace/lob_npz/*.npz"))
    rng=np.random.default_rng([20260911,41]); fs=[fs[i] for i in rng.choice(len(fs),60,replace=False)]
    M1=np.full((len(TS),len(SYM)),np.nan); M5=np.full((len(TS),len(SYM)),np.nan)
    t0=time.time()
    with Pool(10) as p:
        for r in p.imap_unordered(one,fs,chunksize=1):
            if r: ci,a,b=r; M1[:,ci]=a; M5[:,ci]=b
    print("built %.0fs  finite m1 %.4f"%(time.time()-t0,np.isfinite(M1).mean()))
    dM=np.full(M1.shape,np.nan); dM[1:]=M1[1:]-M1[:-1]
    ok=np.isfinite(dM)&np.isfinite(Y4)
    print("n pairs",ok.sum())
    x=dM[ok]; y=Y4[ok]
    print("corr(dBookPrice_4h, panel Y4) = %.5f"%np.corrcoef(x,y)[0,1])
    print("std(dBook)=%.5f std(Y4)=%.5f  slope=%.4f"%(x.std(),y.std(),np.polyfit(y,x,1)[0]))
    r=x-y
    print("residual std = %.5f (=%.1f bps)  -> noise/signal in 4h return units %.3f"%(r.std(),r.std()*1e4,r.std()/y.std()))
    # BTILT scale
    bt=M1-M5; okb=np.isfinite(bt)
    print("BTILT: finite %.4f  std %.5f (%.1f bps)  median %.5f"%(okb.mean(),np.nanstd(bt),np.nanstd(bt)*1e4,np.nanmedian(bt)))
