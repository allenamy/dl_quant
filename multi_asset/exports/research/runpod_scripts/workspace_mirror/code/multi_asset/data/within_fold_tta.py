"""WITHIN-FOLD test-time adaptation for 2026-02 (the FIXABLE drift fold).

Drift-floor showed 2026-02 has in-regime signal (held-out Ridge CLEAN +0.0456) but a
PAST-trained model regresses (drift). LEVER: adapt the readout on REALIZED within-2026-02
history (strictly leak-safe: only windows whose target is already settled by prediction
time) -> capture the drifted in-regime relationship -> approach +0.0456.

DIFFERENT from the refuted online-retrain (that used pre-fold 3mo on the signal-DEAD 2025-12).
Here the WITHIN-fold signal EXISTS (+0.0456).

LEAK-SAFE rolling: process 2026-02 windows in time order. A window at cutoff t is PREDICTED
using a Ridge readout fit ONLY on windows whose (cutoff + 600s) <= t  (target realized strictly
before t). Re-fit the readout every REFIT_EVERY windows on the growing realized history.
Compares: (a) STATIC = readout fit on a PRE-fold reference (the drifted/stale model proxy) vs
(b) ADAPTIVE = rolling within-fold readout. Snapshot feats (proxy for the frozen DL features).

Run: PYTHONPATH=. python multi_asset/data/within_fold_tta.py
"""
from __future__ import annotations
import numpy as np, glob, warnings
warnings.filterwarnings("ignore"); warnings.simplefilter("ignore")
from sklearn.linear_model import Ridge
from scipy.stats import pearsonr

HOR_US=600*1_000_000
def dd(p): return p.split("/")[-1][:-4]
def load(mon):
    fs=sorted(glob.glob("data/npz_v2arch/*.npz")); days=[f for f in fs if dd(f)[:7]==mon]
    Xs=[];ys=[];ts=[]
    for f in days:
        d=np.load(f,allow_pickle=True); m=d["y_mask_600"].astype(bool)
        X=d["X"][m]; snap=np.concatenate([X[:,-1,:],X[:,-60:,:].mean(1)],1)
        Xs.append(snap.astype(np.float32)); ys.append(d["y_600"][m].astype(np.float32)); ts.append(d["timestamps"][m].astype(np.int64))
    X=np.nan_to_num(np.concatenate(Xs)); y=np.concatenate(ys); t=np.concatenate(ts)
    o=np.argsort(t); return X[o],y[o],t[o]

def clean_idx(ts):
    keep=[];last=-1e18
    for i in range(len(ts)):
        if ts[i]-last>=HOR_US: keep.append(i);last=ts[i]
    return np.array(keep)

# reference (pre-fold) months to simulate the stale/drifted prior model
REF=["2025-10","2025-11","2025-12","2026-01"]
def load_ref():
    Xs=[];ys=[]
    for mon in REF:
        try: X,y,_=load(mon); Xs.append(X);ys.append(y)
        except: pass
    return np.concatenate(Xs),np.concatenate(ys)

print("=== WITHIN-FOLD TTA on 2026-02 (signal EXISTS, drift-floor CLEAN +0.0456) ===")
X,y,ts=load("2026-02")
print(f"2026-02 windows={len(y)}")
Xr,yr=load_ref()
mu=Xr.mean(0);sd=Xr.std(0)+1e-8
# (a) STATIC: readout fit on pre-fold REF (stale model proxy), applied to all 2026-02
rstat=Ridge(alpha=100).fit((Xr-mu)/sd,yr)
p_static=rstat.predict((X-mu)/sd)
# (b) ADAPTIVE: rolling within-fold. warm-start from REF, refit on realized 2026-02 history.
REFIT=200; WARM=300   # need >=WARM realized windows before adapting; refit every REFIT
p_adapt=p_static.copy()
n=len(y); last_fit=-10**9
cur=rstat; cmu,csd=mu,sd
for i in range(n):
    # realized set: windows j with ts[j]+HOR <= ts[i]  (target settled strictly before t_i)
    # (ts sorted) -> realized prefix where ts[j] <= ts[i]-HOR
    cutoff=ts[i]-HOR_US
    nreal=np.searchsorted(ts,cutoff,side="right")
    if nreal>=WARM and (i-last_fit)>=REFIT:
        Xh=np.concatenate([Xr, X[:nreal]]); yh=np.concatenate([yr, y[:nreal]])  # warm-start: ref + realized within-fold
        cmu=Xh.mean(0);csd=Xh.std(0)+1e-8
        cur=Ridge(alpha=100).fit((Xh-cmu)/csd,yh); last_fit=i
    p_adapt[i]=cur.predict(((X[i]-cmu)/csd).reshape(1,-1))[0]

ci=clean_idx(ts)
def rep(name,p):
    P=pearsonr(p,y)[0]; b=np.polyfit(p,y,1)[0]
    Pc=pearsonr(p[ci],y[ci])[0]; bc=np.polyfit(p[ci],y[ci],1)[0]
    print(f"  {name:22s} DENSE P={P:+.4f} b={b:+.2f} | CLEAN P={Pc:+.4f} b={bc:+.2f}")
rep("STATIC (stale prior)",p_static)
rep("ADAPTIVE (within-fold)",p_adapt)
print(f"  >>> within-fold TTA dP CLEAN = {pearsonr(p_adapt[ci],y[ci])[0]-pearsonr(p_static[ci],y[ci])[0]:+.4f}  (target -> floor +0.0456)")
# shuffle-null: adapt on PERMUTED within-fold y -> should NOT beat static
yp=y.copy(); np.random.RandomState(0).shuffle(yp)
pn=p_static.copy(); cur=rstat;cmu,csd=mu,sd;last_fit=-10**9
for i in range(n):
    nreal=np.searchsorted(ts,ts[i]-HOR_US,side="right")
    if nreal>=WARM and (i-last_fit)>=REFIT:
        Xh=np.concatenate([Xr,X[:nreal]]);yh=np.concatenate([yr,yp[:nreal]])
        cmu=Xh.mean(0);csd=Xh.std(0)+1e-8;cur=Ridge(alpha=100).fit((Xh-cmu)/csd,yh);last_fit=i
    pn[i]=cur.predict(((X[i]-cmu)/csd).reshape(1,-1))[0]
print(f"  shuffle-null (adapt on permuted-y) CLEAN P={pearsonr(pn[ci],y[ci])[0]:+.4f} (must ~ static, NOT > adaptive)")
