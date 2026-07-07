"""Shuffle-null sentinel for the snapshot-skip lever (the NEW component vs base DL).

The snapshot-skip adds a learned LINEAR readout of x_feat[:,-1,:] (last-step features, <=t) to
the DL output. Its only new capacity is that linear map. This sentinel verifies that map cannot
MANUFACTURE signal: fit it (Ridge proxy on last-step features) with REAL y vs PERMUTED y, on the
3 test months (walk-forward: train prior 700d, test month, CLEAN P). PERMUTED-y must collapse to
~0 (within noise). If permuted-y P is materially >0, the readout is leaking (reject).

REAL vs SHUFFLE on last-step snapshot features (the snapshot-skip's exact input):
Run on SERVER: PYTHONPATH=. python multi_asset/data/snapshot_skip_shufflenull.py
"""
from __future__ import annotations
import numpy as np, glob, os, warnings
warnings.filterwarnings("ignore"); warnings.simplefilter("ignore")
from sklearn.linear_model import Ridge
from scipy.stats import pearsonr

def dd(p): return os.path.basename(p)[:-4]
def cache_for(mon): return "data/npzv4_dual" if mon<="2025-09" else "data/npz_v2arch"

def load(mons, cache):
    fs=sorted(glob.glob(f"{cache}/*.npz")); days=[f for f in fs if dd(f)[:7] in mons]
    Xs=[];ys=[];ts=[]
    for f in days:
        d=np.load(f,allow_pickle=True); m=d["y_mask_600"].astype(bool)
        if m.sum()==0: continue
        X=d["X"][m]; snap=X[:,-1,:]   # LAST-STEP ONLY (the snapshot-skip's exact input)
        Xs.append(snap.astype(np.float32)); ys.append(d["y_600"][m].astype(np.float32)); ts.append(d["timestamps"][m].astype(np.int64))
    if not Xs: return None
    # align channel count across caches by truncating to min (npzv4_dual=72, npz_v2arch=88)
    return np.nan_to_num(np.concatenate(Xs)), np.concatenate(ys), np.concatenate(ts)

def clean_p(p,y,ts):
    o=np.argsort(ts);ts=ts[o];p=p[o];y=y[o];Ps=[]
    for off in range(4):
        keep=[];last=-1e18
        for i in range(off,len(ts)):
            if ts[i]-last>=600*1_000_000: keep.append(i);last=ts[i]
        keep=np.array(keep)
        if len(keep)>30:
            r=pearsonr(p[keep],y[keep])[0]
            if np.isfinite(r): Ps.append(r)
    return float(np.mean(Ps)) if Ps else np.nan

def fit_eval(Xtr,ytr,Xte,yte,tte):
    mu=Xtr.mean(0);sd=Xtr.std(0)+1e-8
    best=-9
    for a in [1,10,100,1000]:
        p=Ridge(alpha=a).fit((Xtr-mu)/sd,ytr).predict((Xte-mu)/sd)
        P=clean_p(p,yte,tte)
        if np.isfinite(P): best=max(best,P)
    return best

def prior_months(tm,k=12):
    y,mo=int(tm[:4]),int(tm[5:7]);out=[]
    for i in range(1,k+1):
        mm=mo-i;yy=y
        while mm<=0: mm+=12;yy-=1
        out.append(f"{yy:04d}-{mm:02d}")
    return out[::-1]

rng=np.random.default_rng(42)
print("SNAPSHOT-SKIP SHUFFLE-NULL (last-step Ridge proxy; REAL y vs PERMUTED y)")
print(f"{'month':8s} {'REAL P':>8s} {'SHUF P (mean+-std of 3)':>26s}  verdict")
for tm in ["2025-08","2025-09","2025-10"]:
    cache=cache_for(tm)
    Te=load([tm],cache)
    pm=[x for x in prior_months(tm) if x[:7]]
    # train months must share cache with test for channel alignment; restrict to same-cache months
    pm=[x for x in pm if cache_for(x)==cache]
    Tr=load(pm,cache)
    if Te is None or Tr is None: print(f"{tm:8s} (no data)"); continue
    Xtr,ytr,_=Tr; Xte,yte,tte=Te
    real=fit_eval(Xtr,ytr,Xte,yte,tte)
    shuf=[]
    for s in range(3):
        yp=rng.permutation(ytr)
        shuf.append(fit_eval(Xtr,yp,Xte,yte,tte))
    sm=np.nanmean(shuf); ss=np.nanstd(shuf)
    ok = "PASS (null~0)" if abs(sm) < max(0.010, abs(real)*0.3) else "FAIL (leak!)"
    print(f"{tm:8s} {real:+8.4f}   {sm:+.4f} +- {ss:.4f}        {ok}")
print("DONE_SHUFNULL.")
