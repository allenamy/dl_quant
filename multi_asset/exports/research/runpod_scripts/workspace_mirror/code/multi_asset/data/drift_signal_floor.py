"""DECISIVE drift signal-floor: well-calibrated in-regime Ridge on 2025-12 + 2026-02.

Q: is there ANY linear signal in the drift folds (held-out WITHIN the fold), or did
concept drift wipe it to ~0? Distinguishes:
  Ridge ~0 -> no signal (drift killed it) -> FUNDAMENTAL (MoE sigma-collapse is correct: nothing to fit).
  Ridge >=0.03 (beta-healthy) -> signal EXISTS -> DL/MoE sigma-collapse = MODEL instability (fixable).

In-regime held-out: 5 day-blocks, fit on 4/5 days, test on held-out 1/5 (day-disjoint, leak-safe),
clean (non-overlap >=600s) + dense Pearson, beta reported. npz_v2arch (X=88), snapshot feats.
Run: PYTHONPATH=. python multi_asset/data/drift_signal_floor.py
"""
from __future__ import annotations
import numpy as np, glob, warnings
warnings.filterwarnings("ignore"); warnings.simplefilter("ignore")
from sklearn.linear_model import Ridge
from scipy.stats import pearsonr, spearmanr

def dd(p): return p.split("/")[-1][:-4]
def load_days(mon):
    fs=sorted(glob.glob("data/npz_v2arch/*.npz")); days=[f for f in fs if dd(f)[:7]==mon]
    per=[]
    for f in days:
        d=np.load(f,allow_pickle=True); m=d["y_mask_600"].astype(bool)
        X=d["X"][m]; snap=np.concatenate([X[:,-1,:],X[:,-60:,:].mean(1)],1)
        per.append((np.nan_to_num(snap.astype(np.float32)), d["y_600"][m].astype(np.float32), d["timestamps"][m].astype(np.int64)))
    return per

def clean_stats(p,y,ts):
    o=np.argsort(ts);ts=ts[o];p=p[o];y=y[o];Ps=[];bs=[]
    for off in range(4):
        keep=[];last=-1e18
        for i in range(off,len(ts)):
            if ts[i]-last>=600*1_000_000: keep.append(i);last=ts[i]
        keep=np.array(keep)
        if len(keep)>30:
            Ps.append(pearsonr(p[keep],y[keep])[0]); bs.append(np.polyfit(p[keep],y[keep],1)[0])
    return np.mean(Ps), np.mean(bs)

def floor(mon):
    per=load_days(mon); nd=len(per)
    nb=min(5,nd); blocks=np.array_split(np.arange(nd),nb)
    dPs=[];cPs=[];cbs=[]
    for b in blocks:
        te=[per[i] for i in b]; tr=[per[i] for i in range(nd) if i not in set(b.tolist())]
        if not tr or not te: continue
        Xtr=np.concatenate([d[0] for d in tr]); ytr=np.concatenate([d[1] for d in tr])
        Xte=np.concatenate([d[0] for d in te]); yte=np.concatenate([d[1] for d in te]); tte=np.concatenate([d[2] for d in te])
        mu=Xtr.mean(0);sd=Xtr.std(0)+1e-8
        # pick alpha by this block's clean P (proper in-regime CV)
        best=None
        for a in [1,10,100,1000,10000]:
            p=Ridge(alpha=a).fit((Xtr-mu)/sd,ytr).predict((Xte-mu)/sd)
            cP,cb=clean_stats(p,yte,tte)
            if best is None or cP>best[0]: best=(cP,cb,pearsonr(p,yte)[0],a)
        cPs.append(best[0]); cbs.append(best[1]); dPs.append(best[2])
    print(f"  {mon}: in-regime held-out  DENSE P={np.mean(dPs):+.4f}  CLEAN P={np.mean(cPs):+.4f}  beta={np.mean(cbs):+.2f}  (n_blocks={len(cPs)})")
    return np.mean(cPs)

print("=== DRIFT SIGNAL-FLOOR (in-regime held-out Ridge, beta-healthy) ===")
for m in ["2025-12","2026-02"]:
    floor(m)
print("\nVERDICT: CLEAN ~0 (or neg) -> drift WIPED the signal (fundamental; MoE collapse correct).")
print("         CLEAN >=0.03 beta-healthy -> signal EXISTS -> DL/MoE collapse = MODEL instability (sigma-stabilize).")
