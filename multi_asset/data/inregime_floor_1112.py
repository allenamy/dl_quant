"""IN-REGIME signal-floor for 2025-11 and 2025-12 (decisive: sigma-collapse-fixable vs signal-dead).
Oracle in-regime Ridge: fit AND test WITHIN the month, leak-safe time-CV (5 contiguous folds, train on 4 test 1,
no overlap across the fold boundary via 600s embargo). If in-regime Ridge finds signal (>0.03) but production DL
~0 -> signal EXISTS, DL FAILED (sigma-collapse, FIXABLE). If in-regime Ridge ~0 -> genuine signal-dead.
Compares to 2025-10 (healthy, DL +0.096) as the positive control.
snapshot = last-step + 60s-mean (npz_v2arch, book+trade). Per-day-CLEAN eval (no cross-day pooling).
Run on SERVER: PYTHONPATH=. python multi_asset/data/inregime_floor_1112.py
"""
from __future__ import annotations
import numpy as np, glob, os, warnings
warnings.filterwarnings("ignore"); warnings.simplefilter("ignore")
from sklearn.linear_model import Ridge
from scipy.stats import pearsonr

CACHE="data/npz_v2arch"
def dd(p): return os.path.basename(p)[:-4]
def load(mon):
    fs=sorted(glob.glob(f"{CACHE}/*.npz")); days=[f for f in fs if dd(f)[:7]==mon]
    Xs=[];ys=[];ts=[]
    for f in days:
        d=np.load(f,allow_pickle=True); m=d["y_mask_600"].astype(bool)
        if m.sum()==0: continue
        X=d["X"][m]; snap=np.concatenate([X[:,-1,:],X[:,-60:,:].mean(1)],1)
        Xs.append(snap.astype(np.float32)); ys.append(d["y_600"][m].astype(np.float32)); ts.append(d["timestamps"][m].astype(np.int64))
    if not Xs: return None
    return np.nan_to_num(np.concatenate(Xs)), np.concatenate(ys), np.concatenate(ts)
def clean_idx(ts,off=0):
    o=np.argsort(ts);keep=[];last=-1e18
    for i in range(off,len(o)):
        if ts[o[i]]-last>=600*1_000_000: keep.append(o[i]);last=ts[o[i]]
    return np.array(keep)
def perday_clean(p,y,ts):
    daykey=ts//(86400*1_000_000); rs=[]
    for dk in np.unique(daykey):
        m=daykey==dk; k=clean_idx(ts[m],0)
        if len(k)>20:
            pk=p[m][k]; yk=y[m][k]
            if pk.std()>1e-12:
                r=pearsonr(pk,yk)[0]
                if np.isfinite(r): rs.append(r)
    return (np.mean(rs) if rs else np.nan), len(rs)
def fit(Xtr,ytr,Xte,a):
    mu=Xtr.mean(0);sd=Xtr.std(0)+1e-8
    return Ridge(alpha=a).fit((Xtr-mu)/sd,ytr).predict((Xte-mu)/sd)

def inregime(mon):
    """TRUE in-regime oracle: INTERLEAVED K-fold (train+test from the SAME within-month distribution) with a
    per-test-point 600s embargo (drop train windows within 600s of ANY test point -> leak-safe re y-autocorr).
    This measures whether the month's features CAN predict y IN-DISTRIBUTION (the signal floor), unlike the
    contiguous-block CV which conflates non-stationary sub-period transfer."""
    L=load(mon)
    if L is None: return None
    X,y,ts=L; o=np.argsort(ts); X,y,ts=X[o],y[o],ts[o]
    n=len(y); rng=np.random.default_rng(0)
    foldid=rng.integers(0,5,size=n)   # interleaved random folds
    ps=[]
    for k in range(5):
        te=np.where(foldid==k)[0]; tr=np.where(foldid!=k)[0]
        if len(tr)<800 or len(te)<200: continue
        # embargo: drop any train window within 600s of a test window (sorted-merge for speed)
        tte=np.sort(ts[te])
        keep=np.ones(len(tr),bool)
        pos=np.searchsorted(tte,ts[tr])
        for j,p_ in enumerate(pos):
            lo=tte[max(p_-1,0)]; hi=tte[min(p_,len(tte)-1)]
            if abs(ts[tr[j]]-lo)<600_000_000 or abs(ts[tr[j]]-hi)<600_000_000: keep[j]=False
        tr=tr[keep]
        if len(tr)<800: continue
        best=-9
        for al in [1,10,100,1000]:
            p=fit(X[tr],y[tr],X[te],al); pc,_=perday_clean(p,y[te],ts[te])
            if np.isfinite(pc): best=max(best,pc)
        if best>-9: ps.append(best)
    return (np.mean(ps) if ps else np.nan), n

print("IN-REGIME SIGNAL-FLOOR (oracle within-month Ridge, leak-safe 5-fold, per-day CLEAN)")
print(f"{'month':8s} {'in-regime-P':>12s} {'N':>7s}  vs production-DL")
dl={"2025-10":"+0.096(healthy)","2025-11":"+0.022 b2.16 s0.010","2025-12":"+0.007 b0.69 s0.010"}
for mon in ["2025-10","2025-11","2025-12"]:
    r=inregime(mon)
    if r is None: print(f"{mon:8s} (no data)"); continue
    p,n=r
    verdict="SIGNAL EXISTS (DL failed=sigma-collapse FIXABLE)" if p>0.03 else ("WEAK ~0 (likely signal-dead)" if p<0.015 else "BORDERLINE")
    print(f"{mon:8s} {p:+12.4f} {n:7d}  DL={dl.get(mon,'?')}  -> {verdict}")
print("\nDONE_INREGIME.")
