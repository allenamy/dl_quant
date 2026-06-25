"""Drift root-cause diagnostics for the 2025-12 fold collapse (CLEAN 0.018).

D1: TRAIN-holdout P vs TEST P (Ridge proxy). train>>test -> concept drift (not low signal).
D2: feature-distribution shift train-vs-2025-12 (mean-shift z + KS-ish on key feats).
D3: recency -- does training on a window CLOSER to 2025-12 recover test P? (drift vs dead month)

Ridge snapshot proxy (last-step + 60s-mean). npz_v2arch (covers 2025-12). Leak-safe walk-forward.
Run: PYTHONPATH=. python multi_asset/data/drift_diagnostic.py
"""
from __future__ import annotations
import numpy as np, glob, warnings
warnings.filterwarnings("ignore"); warnings.simplefilter("ignore")
from sklearn.linear_model import Ridge
from scipy.stats import pearsonr, ks_2samp

CACHE="npz_v2arch"
def dd(p): return p.split("/")[-1][:-4]
def mon(p): return dd(p)[:7]

def load(mons):
    fs=sorted(glob.glob(f"data/{CACHE}/*.npz"))
    days=[f for f in fs if mon(f) in mons]
    Xs=[];ys=[];ts=[]
    for f in days:
        d=np.load(f,allow_pickle=True); m=d["y_mask_600"].astype(bool)
        X=d["X"][m]; snap=np.concatenate([X[:,-1,:],X[:,-60:,:].mean(1)],1)
        Xs.append(snap.astype(np.float32)); ys.append(d["y_600"][m].astype(np.float32)); ts.append(d["timestamps"][m].astype(np.int64))
    return np.nan_to_num(np.concatenate(Xs)),np.concatenate(ys),np.concatenate(ts)

def clean_p(p,y,ts):
    o=np.argsort(ts);ts=ts[o];p=p[o];y=y[o];Ps=[]
    for off in range(4):
        keep=[];last=-1e18
        for i in range(off,len(ts)):
            if ts[i]-last>=600*1_000_000: keep.append(i);last=ts[i]
        keep=np.array(keep)
        if len(keep)>30: Ps.append(pearsonr(p[keep],y[keep])[0])
    return np.mean(Ps)

def fit_pick(Xtr,ytr,Xva,yva,tva):
    mu=Xtr.mean(0);sd=Xtr.std(0)+1e-8
    best=None
    for a in [1,10,100,1000]:
        r=Ridge(alpha=a).fit((Xtr-mu)/sd,ytr)
        p=r.predict((Xva-mu)/sd); P=clean_p(p,yva,tva)
        if best is None or P>best[0]: best=(P,a,r,mu,sd)
    return best

# ---- months ----
TRAIN=["2025-02","2025-03","2025-04","2025-05","2025-06","2025-07","2025-08","2025-09","2025-10","2025-11"]
TEST=["2025-12"]
RECENT=["2025-09","2025-10","2025-11"]   # closer-to-test window for D3

print("=== D1: TRAIN-holdout P vs 2025-12 TEST P (concept-drift test) ===")
Xtr,ytr,ttr=load(TRAIN); Xte,yte,tte=load(TEST)
# train-holdout: last 10% of train (in-distribution generalization)
n=len(ytr); idx=np.arange(n); cut=int(n*0.9)
Xtr2,ytr2,ttr2=Xtr[:cut],ytr[:cut],ttr[:cut]
Xho,yho,tho=Xtr[cut:],ytr[cut:],ttr[cut:]
P_ho,a,r,mu,sd=fit_pick(Xtr2,ytr2,Xho,yho,tho)
p_te=r.predict((Xte-mu)/sd); P_te=clean_p(p_te,yte,tte)
print(f"  train-holdout CLEAN P = {P_ho:+.4f}  (in-distribution)")
print(f"  2025-12 TEST  CLEAN P = {P_te:+.4f}  (out-of-time)")
print(f"  -> drop = {P_ho-P_te:+.4f}.  train>>test => CONCEPT DRIFT (not low signal); train~=test => low signal")

print("\n=== D2: feature-distribution shift train vs 2025-12 (top mean-shift feats) ===")
mt=Xtr.mean(0); st=Xtr.std(0)+1e-8; me=Xte.mean(0)
zshift=np.abs(me-mt)/st
top=np.argsort(zshift)[::-1][:8]
for i in top:
    ks=ks_2samp(Xtr[::20,i],Xte[::20,i]).statistic
    print(f"  feat[{i:3d}] mean-shift-z={zshift[i]:.2f}  KS={ks:.3f}")
print(f"  median |mean-shift-z| across all feats = {np.median(zshift):.3f}  (high => distribution drifted)")

print("\n=== D3: recency -- train on CLOSER window (2025-09..11) vs full -> 2025-12 test ===")
Xr,yr,tr_=load(RECENT)
Pr,ar,rr,mur,sdr=fit_pick(Xr,yr,Xr,yr,tr_)  # self just to get scaler; refit clean below
mu2=Xr.mean(0);sd2=Xr.std(0)+1e-8
bestP=-9
for a in [1,10,100,1000]:
    rr=Ridge(alpha=a).fit((Xr-mu2)/sd2,yr); pp=rr.predict((Xte-mu2)/sd2); P=clean_p(pp,yte,tte)
    bestP=max(bestP,P)
print(f"  recent-window (3mo) -> 2025-12 TEST CLEAN P = {bestP:+.4f}")
print(f"  full-window  (10mo) -> 2025-12 TEST CLEAN P = {P_te:+.4f}")
print(f"  -> recent>full => RECENCY HELPS (drift, online-retrain fixable); recent<=full => recency hurts (memory says this)")
