"""DECISIVE premise-check: is the Ridge +0.169 (2025-10) / +0.111 (2025-11) ceiling REAL or an artifact?

The snapshot-skip premise rests on "Ridge = ceiling the DL under-captures". Verify rigorously:
 1. CALIBER: report DENSE vs CLEAN (non-overlap >=600s, 4-offset) -- the headline must be CLEAN.
 2. LEAK-SAFE: train strictly prior months, standardize on TRAIN ONLY, features <=t (last-step+60s-mean),
    month-boundary embargo (train = prior months, test = the month).
 3. SHUFFLE-NULL: permute the TEST-month future y, refit-predict-eval -> must collapse to ~0. Also permute
    TRAIN y (refit) -> test P must collapse. Both confirm no future leakage.
 4. ROBUSTNESS: report P for EACH alpha (1/10/100/1000) and 3 seeds (seed only affects shuffle); is +0.169
    a single-alpha outlier or stable across alpha?
Exactly the signfix-gate Ridge (snapshot = last-step + 60s-mean of full X).
Run on SERVER: PYTHONPATH=. python multi_asset/data/verify_ridge_ceiling.py
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
        X=d["X"][m]
        snap=np.concatenate([X[:,-1,:], X[:,-60:,:].mean(1)],1)  # EXACT signfix-gate snapshot
        Xs.append(snap.astype(np.float32)); ys.append(d["y_600"][m].astype(np.float32)); ts.append(d["timestamps"][m].astype(np.int64))
    if not Xs: return None
    return np.nan_to_num(np.concatenate(Xs)), np.concatenate(ys), np.concatenate(ts)

def dense_p(p,y):
    r=pearsonr(p,y)[0]; return r if np.isfinite(r) else np.nan
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

def fit(Xtr,ytr,Xte,alpha):
    mu=Xtr.mean(0);sd=Xtr.std(0)+1e-8   # TRAIN-ONLY standardization
    return Ridge(alpha=alpha).fit((Xtr-mu)/sd,ytr).predict((Xte-mu)/sd)

def prior_months(tm,k=12):
    y,mo=int(tm[:4]),int(tm[5:7]);out=[]
    for i in range(1,k+1):
        mm=mo-i;yy=y
        while mm<=0: mm+=12;yy-=1
        out.append(f"{yy:04d}-{mm:02d}")
    return out[::-1]

rng=np.random.default_rng(0)
# MATCH signfix_gate EXACTLY: it used CACHE=npz_v2arch for BOTH train and test (all months),
# train = prior_months(tm,12) ALL from npz_v2arch (which covers 2024-01+). The earlier verify
# BUG filtered train to same-cache-as-test AND split npzv4_dual/npz_v2arch -> crippled the train
# set (1 month) -> artificially low + noisy shuffle-null. Fix: use npz_v2arch for the 2025-10+
# tests (matches signfix), npzv4_dual only for <=2025-09 tests.
TESTS=["2025-10","2025-11","2025-08"]
print("DECISIVE RIDGE CEILING VERIFICATION (snapshot=last-step+60s-mean, leak-safe walk-forward)")
print("MATCHED to signfix_gate: full 12-prior-month train from the test month's cache")
print("="*92)
for tm in TESTS:
    cache=cache_for(tm)
    # train from the SAME cache as test, ALL 12 prior months that exist in that cache (no cross-cache split)
    pm=prior_months(tm,12)
    Tr=load(pm,cache); Te=load([tm],cache)
    if Tr is None or Te is None: print(f"{tm}: no data (cache={cache})"); continue
    Xtr,ytr,_=Tr; Xte,yte,tte=Te
    print(f"\n### {tm}  (cache={cache}, Ntr={len(ytr)}, Nte={len(yte)})")
    # 1+4: per-alpha DENSE + CLEAN (real y)
    print(f"  {'alpha':>6s} {'DENSE-P':>9s} {'CLEAN-P':>9s}")
    best_clean=-9; best_a=None
    for a in [1,10,100,1000]:
        p=fit(Xtr,ytr,Xte,a); dP=dense_p(p,yte); cP=clean_p(p,yte,tte)
        print(f"  {a:>6d} {dP:+9.4f} {cP:+9.4f}")
        if np.isfinite(cP) and cP>best_clean: best_clean=cP; best_a=a
    print(f"  -> BEST CLEAN = {best_clean:+.4f} (alpha={best_a})")
    # 3: shuffle-null -- permute TEST y (refit not needed; just eval pred vs shuffled y) AND permute TRAIN y (refit)
    p=fit(Xtr,ytr,Xte,best_a)
    shTe=[]; shTr=[]
    for s in range(3):
        yte_sh=rng.permutation(yte); shTe.append(clean_p(p,yte_sh,tte))
        ytr_sh=rng.permutation(ytr); p2=fit(Xtr,ytr_sh,Xte,best_a); shTr.append(clean_p(p2,yte,tte))
    print(f"  SHUFFLE-NULL(permute TEST-y): CLEAN P = {np.nanmean(shTe):+.4f} +- {np.nanstd(shTe):.4f}  (must ~0)")
    print(f"  SHUFFLE-NULL(permute TRAIN-y refit): CLEAN P = {np.nanmean(shTr):+.4f} +- {np.nanstd(shTr):.4f}  (must ~0)")
    verdict = "REAL" if (best_clean>0.03 and abs(np.nanmean(shTe))<0.012 and abs(np.nanmean(shTr))<0.012) else "SUSPECT"
    print(f"  VERDICT: {verdict}")
print("\nDONE_VERIFY.")
