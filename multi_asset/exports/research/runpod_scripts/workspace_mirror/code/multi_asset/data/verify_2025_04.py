"""Re-verify the 2025-04 "0.10 strong month" on HONEST discipline (Ridge caliber + bounce + net-of-cost).
Given 2025-10's 0.169 was a bid-ask bounce and 2025-08's claimed 0.0845 dropped to honest 0.057, check whether
2025-04 is similarly inflated. (The DL claim 0.1054/0.1165 needs a DL run; this is the fast Ridge/caliber cut.)

 1. RIDGE CLEAN vs DENSE per-alpha on 2025-04 (npzv4_dual, snapshot=last-step+60s-mean), leak-safe walk-forward.
 2. BOUNCE-CHECK: pt_vwap_return_1s.last (trade) vs MID 1s-return reversion with y_600. If trade>>mid -> bounce.
 3. NET-OF-COST: sigma(y600), top-decile fade edge of the dominant feature vs cost.
 4. Is 2025-04's Ridge IC explained by the SAME vwap-bounce feature (univariate) or by tradeable mid features?
npzv4_dual = 72ch (64 spot + 8 cross). NOTE: npzv4_dual has NO perp-trade block, so pt_vwap_return_1s may be
ABSENT -- if so, the bounce feature isn't even present here, and 2025-04's IC (if high) is a DIFFERENT source.
Run on SERVER: PYTHONPATH=. python multi_asset/data/verify_2025_04.py
"""
from __future__ import annotations
import numpy as np, glob, os, warnings
warnings.filterwarnings("ignore"); warnings.simplefilter("ignore")
from sklearn.linear_model import Ridge
from scipy.stats import pearsonr

CACHE="data/npzv4_dual"
def dd(p): return os.path.basename(p)[:-4]
def load(mons):
    fs=sorted(glob.glob(f"{CACHE}/*.npz")); days=[f for f in fs if dd(f)[:7] in mons]
    Xs=[];Ls=[];Ms=[];ys=[];ts=[]
    nch=None
    for f in days:
        d=np.load(f,allow_pickle=True); m=d["y_mask_600"].astype(bool)
        if m.sum()==0: continue
        X=d["X"][m]; nch=X.shape[2]
        snap=np.concatenate([X[:,-1,:],X[:,-60:,:].mean(1)],1)
        Xs.append(snap.astype(np.float32))
        # mid 1s return from x_mid_ratio_log (channel index depends on layout; npzv4_dual cross starts at 64)
        # try to locate x_mid_ratio_log = first cross channel (64) per the builder
        Ms.append((X[:,-1,64]-X[:,-2,64]).astype(np.float32))
        ys.append(d["y_600"][m].astype(np.float32)); ts.append(d["timestamps"][m].astype(np.int64))
    if not Xs: return None
    return (np.nan_to_num(np.concatenate(Xs)), np.nan_to_num(np.concatenate(Ms)),
            np.concatenate(ys), np.concatenate(ts), nch)

def clean_idx(ts,off=0):
    o=np.argsort(ts);keep=[];last=-1e18
    for i in range(off,len(o)):
        if ts[o[i]]-last>=600*1_000_000: keep.append(o[i]);last=ts[o[i]]
    return np.array(keep)
def dense_p(p,y): r=pearsonr(p,y)[0]; return r if np.isfinite(r) else np.nan
def clean_p(p,y,ts):
    Ps=[]
    for off in range(4):
        k=clean_idx(ts,off)
        if len(k)>30:
            r=pearsonr(p[k],y[k])[0]
            if np.isfinite(r): Ps.append(r)
    return (np.mean(Ps) if Ps else np.nan), (np.std(Ps) if Ps else np.nan), (len(clean_idx(ts,0)))
def fit(Xtr,ytr,Xte,a):
    mu=Xtr.mean(0);sd=Xtr.std(0)+1e-8
    return Ridge(alpha=a).fit((Xtr-mu)/sd,ytr).predict((Xte-mu)/sd)
def prior_months(tm,k=12):
    y,mo=int(tm[:4]),int(tm[5:7]);out=[]
    for i in range(1,k+1):
        mm=mo-i;yy=y
        while mm<=0: mm+=12;yy-=1
        out.append(f"{yy:04d}-{mm:02d}")
    return out[::-1]

tm="2025-04"
Tr=load(prior_months(tm)); Te=load([tm])
if Tr is None or Te is None:
    print("NO DATA for 2025-04 in npzv4_dual"); raise SystemExit
Xtr,Mtr,ytr,ttr,nch=Tr; Xte,Mte,yte,tte,_=Te
print(f"=== 2025-04 HONEST RE-VERIFY (npzv4_dual, {nch}ch) Ntr={len(ytr)} Nte={len(yte)} ===")
print("\n[1] RIDGE per-alpha DENSE vs CLEAN (leak-safe):")
bestc=-9;besta=None
for a in [1,10,100,1000]:
    p=fit(Xtr,ytr,Xte,a); dP=dense_p(p,yte); cP,cs,N=clean_p(p,yte,tte)
    print(f"  alpha={a:>4d} DENSE={dP:+.4f} CLEAN={cP:+.4f} (off-std {cs:.4f}, N/off~{N})")
    if cP>bestc: bestc=cP;besta=a
print(f"  -> BEST CLEAN Ridge = {bestc:+.4f} (alpha {besta})  [vs claimed DL 0.1054 adaptive / 0.1165 mh180]")
# 95% CI
_,_,N=clean_p(fit(Xtr,ytr,Xte,besta),yte,tte); ci=1.96/np.sqrt(max(N-3,1))
print(f"  95% CI ±{ci:.4f}")

print("\n[2] BOUNCE-CHECK (does npzv4_dual even have trade-vwap? + mid reversion):")
k=clean_idx(tte,0)
# mid 1s return reversion
print(f"  MID 1s-return (x_mid_ratio_log diff) univ-CLEAN vs y600 = {pearsonr(Mte[k],yte[k])[0]:+.4f}")
# top Ridge features by |coef| + univariate
r=Ridge(alpha=besta).fit((Xtr-Xtr.mean(0))/(Xtr.std(0)+1e-8),ytr)
mu=Xtr.mean(0);sd=Xtr.std(0)+1e-8; Xte_s=(Xte-mu)/sd
top=np.argsort(np.abs(r.coef_))[::-1][:8]
print("  top Ridge features (idx<%d=last-step, >=%d=60s-mean) univ-CLEAN-P:"%(nch,nch))
for j in top:
    base=j if j<nch else j-nch; tag="last" if j<nch else "mean"
    print(f"    ch{base}.{tag} coef={r.coef_[j]:+.3f} univ={pearsonr(Xte_s[k,j],yte[k])[0]:+.4f}")

print("\n[3] NET-OF-COST:")
ysig=yte.std()*1e4
print(f"  sigma(y600)={ysig:.2f}bps; IC*sigma={bestc*ysig:.3f}bps")
# AR1
yk=yte[k]; ar1=pearsonr(yk[:-1],yk[1:])[0] if len(yk)>30 else np.nan
print(f"  AR1(y600 non-overlap)={ar1:+.4f}")
print("\nDONE_2504.")
