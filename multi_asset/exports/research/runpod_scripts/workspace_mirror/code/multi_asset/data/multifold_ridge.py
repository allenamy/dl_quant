"""Multi-fold Ridge robustness (Ridge-before-DL fold characterization).

Discipline #14: single-fold unreliable. Before committing GPU to multi-fold DL,
characterize each fold's regime + linear signal with a fast walk-forward Ridge on
snapshot features. Gives per-fold + pooled linear baseline the adaptive DL must
beat, and flags any fold where the signal sign reverses.

Folds (test month -> cache; train = ~prior 10 months in that cache, embargo built
into the >=600s clean eval):
  2025-04 npzv4_dual  (STRONG, anchor)
  2024-10 npzv4_dual  (2024-Q4)
  2025-08 npzv4_dual  (recent strong-ish)
  2025-12 npz_v2arch  (drift / transition)
  2026-02 npz_v2arch  (choppy/weak)
  2026-05 npz_v2arch  (CHOPPY, anchor)

Run: PYTHONPATH=. python multi_asset/data/multifold_ridge.py
"""
from __future__ import annotations
import numpy as np, glob, warnings
warnings.filterwarnings("ignore"); warnings.simplefilter("ignore")
from sklearn.linear_model import Ridge
from scipy.stats import pearsonr, spearmanr

def dd(p): return p.split("/")[-1][:-4]
def mon(p): return dd(p)[:7]

def months_before(cache, test_mon, k=10):
    fs=sorted(glob.glob(f"data/{cache}/*.npz"))
    allm=sorted({mon(f) for f in fs})
    if test_mon not in allm: return None,None
    i=allm.index(test_mon)
    train_m=allm[max(0,i-k):i]
    return train_m, fs

def load(cache, mons):
    fs=sorted(glob.glob(f"data/{cache}/*.npz"))
    days=[f for f in fs if mon(f) in mons]
    Xs=[];ys=[];tss=[]
    for f in days:
        d=np.load(f,allow_pickle=True); m=d["y_mask_600"].astype(bool)
        X=d["X"][m]
        snap=np.concatenate([X[:,-1,:],X[:,-60:,:].mean(1)],1)
        Xs.append(snap.astype(np.float32)); ys.append(d["y_600"][m].astype(np.float32))
        tss.append(d["timestamps"][m].astype(np.int64))
    if not Xs: return None,None,None
    return np.nan_to_num(np.concatenate(Xs)),np.concatenate(ys),np.concatenate(tss)

def clean_metrics(p,y,ts):
    o=np.argsort(ts);ts=ts[o];p=p[o];y=y[o]
    Ps=[];Ss=[];bs=[]
    for off in range(4):
        keep=[];last=-1e18
        for i in range(off,len(ts)):
            if ts[i]-last>=600*1_000_000: keep.append(i);last=ts[i]
        keep=np.array(keep)
        if len(keep)>30:
            pk,yk=p[keep],y[keep]
            Ps.append(pearsonr(pk,yk)[0]); Ss.append(spearmanr(pk,yk)[0])
            b=np.polyfit(pk,yk,1)[0]; bs.append(b)
    return np.mean(Ps),np.mean(Ss),np.mean(bs)

def dense_metrics(p,y):
    P=pearsonr(p,y)[0];S=spearmanr(p,y)[0];b=np.polyfit(p,y,1)[0]
    # decile monotonicity: mean y per pred-decile increasing?
    q=np.argsort(p);dec=np.array_split(q,10);mu=[y[d].mean() for d in dec]
    mono=np.corrcoef(np.arange(10),mu)[0,1]
    # directional accuracy
    da=np.mean(np.sign(p)==np.sign(y))
    return P,S,b,mono,da

FOLDS=[("2025-04","npzv4_dual","STRONG"),("2024-10","npzv4_dual","2024Q4"),
       ("2025-08","npzv4_dual","rec-strong"),("2025-12","npz_v2arch","drift"),
       ("2026-02","npz_v2arch","choppy-wk"),("2026-05","npz_v2arch","CHOPPY")]

print("fold      regime     cache       N_te  D_P     D_S     C_P     C_S    beta  mono   DA")
print("-"*92)
allP=[]
for tm,cache,reg in FOLDS:
    trm,_=months_before(cache,tm,10)
    if trm is None: print(f"{tm} {reg} -- not in {cache}"); continue
    Xtr,ytr,_=load(cache,trm); Xte,yte,tte=load(cache,[tm])
    if Xtr is None or Xte is None: print(f"{tm} -- no data"); continue
    mu=Xtr.mean(0);sd=Xtr.std(0)+1e-8;Xtrn=(Xtr-mu)/sd;Xten=(Xte-mu)/sd
    # pick alpha by clean P
    best=None
    for a in [1,10,100,1000]:
        p=Ridge(alpha=a).fit(Xtrn,ytr).predict(Xten)
        cP,_,_=clean_metrics(p,yte,tte)
        if best is None or cP>best[0]: best=(cP,a,p)
    p=best[2]
    dP,dS,db,mono,da=dense_metrics(p,yte)
    cP,cS,cb=clean_metrics(p,yte,tte)
    allP.append(cP)
    print(f"{tm} {reg:10s} {cache:11s} {len(yte):5d} {dP:+.4f} {dS:+.4f} {cP:+.4f} {cS:+.4f} {cb:+.2f} {mono:+.2f} {da:.3f}")
print("-"*92)
print(f"POOLED clean-P mean={np.mean(allP):+.4f}  min={np.min(allP):+.4f}  sign-consistent={'YES' if np.all(np.array(allP)>0) else 'NO (a fold reversed!)'}")
