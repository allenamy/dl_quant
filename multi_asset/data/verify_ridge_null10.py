"""Tighten the shuffle-null: 10 seeds on 2025-10/11 (the suspicious 0.1+ months).
The 3-seed permute-TRAIN-y null was +0.061+-0.115 / +0.038+-0.040 -- noisy, possibly consistent with 0
(0.5-0.9 sigma) OR a real leak. 10 seeds + a proper z-stat settles it. Also adds a BLOCK-permute (shuffle
y in time-contiguous blocks) which preserves y autocorrelation -- if the 'leak' is just y-AR1 aligning with
slow features, block-perm null will be HIGHER than iid-perm (diagnostic).

Decisive: if permute-TRAIN-y null mean is within ~2 sigma of 0 over 10 seeds -> ceiling REAL (the +0.169 is
genuine leak-safe signal). If it's clearly >0 (>2-3 sigma) -> leak, re-baseline.
Run on SERVER: PYTHONPATH=. python multi_asset/data/verify_ridge_null10.py
"""
from __future__ import annotations
import numpy as np, glob, os, warnings
warnings.filterwarnings("ignore"); warnings.simplefilter("ignore")
from sklearn.linear_model import Ridge
from scipy.stats import pearsonr

CACHE="data/npz_v2arch"
def dd(p): return os.path.basename(p)[:-4]
def load(mons):
    fs=sorted(glob.glob(f"{CACHE}/*.npz")); days=[f for f in fs if dd(f)[:7] in mons]
    Xs=[];ys=[];ts=[]
    for f in days:
        d=np.load(f,allow_pickle=True); m=d["y_mask_600"].astype(bool)
        if m.sum()==0: continue
        X=d["X"][m]; snap=np.concatenate([X[:,-1,:],X[:,-60:,:].mean(1)],1)
        Xs.append(snap.astype(np.float32)); ys.append(d["y_600"][m].astype(np.float32)); ts.append(d["timestamps"][m].astype(np.int64))
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
def fit(Xtr,ytr,Xte,a=1000):
    mu=Xtr.mean(0);sd=Xtr.std(0)+1e-8
    return Ridge(alpha=a).fit((Xtr-mu)/sd,ytr).predict((Xte-mu)/sd)
def prior_months(tm,k=12):
    y,mo=int(tm[:4]),int(tm[5:7]);out=[]
    for i in range(1,k+1):
        mm=mo-i;yy=y
        while mm<=0: mm+=12;yy-=1
        out.append(f"{yy:04d}-{mm:02d}")
    return out[::-1]
def block_perm(y, rng, blk=300):
    n=len(y); nb=n//blk; idx=np.arange(n)
    order=rng.permutation(nb)
    parts=[idx[b*blk:(b+1)*blk] for b in order]+[idx[nb*blk:]]
    return y[np.concatenate(parts)]

rng=np.random.default_rng(123)
for tm in ["2025-10","2025-11"]:
    pm=prior_months(tm); Xtr,ytr,ttr=load(pm); Xte,yte,tte=load([tm])
    real=clean_p(fit(Xtr,ytr,Xte),yte,tte)
    iid=[]; blk=[]
    for s in range(10):
        iid.append(clean_p(fit(Xtr,rng.permutation(ytr),Xte),yte,tte))
        blk.append(clean_p(fit(Xtr,block_perm(ytr,rng),Xte),yte,tte))
    iid=np.array(iid); blk=np.array(blk)
    z_iid=iid.mean()/(iid.std()/np.sqrt(len(iid))+1e-12)
    z_blk=blk.mean()/(blk.std()/np.sqrt(len(blk))+1e-12)
    print(f"\n### {tm}: REAL CLEAN={real:+.4f}")
    print(f"  iid-perm-TRAIN-y null: mean={iid.mean():+.4f} std={iid.std():.4f} (z={z_iid:+.2f})  vals={np.round(iid,3)}")
    print(f"  block-perm-TRAIN-y null: mean={blk.mean():+.4f} std={blk.std():.4f} (z={z_blk:+.2f})")
    verdict="REAL (null~0)" if abs(iid.mean())<0.015 and abs(z_iid)<3 else ("LEAK" if iid.mean()>0.03 else "BORDERLINE")
    print(f"  real/null ratio = {real/(abs(iid.mean())+1e-6):.1f}x | VERDICT: {verdict}")
print("\nDONE_NULL10.")
