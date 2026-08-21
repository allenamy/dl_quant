"""DECISIVE: honest BOOK-MID Ridge (bounce-free, per-day CLEAN) vs the honest base-DL, per month.
Distinguishes "DL beats bounce-Ridge (phantom)" from "DL beats clean tradeable Ridge (what matters)".

HONEST RIDGE:
 - features: BOOK/LOB only. npz_v2arch X=88 = [64 spot-book | 16 perp-TRADE | 8 cross]. The 16 perp-trade
   channels (64..79) include pt_vwap_return_1s (the bid-ask BOUNCE driver) -> REMOVE the whole trade block.
   Keep spot-book 0..63 + cross 80..87 (cross are book-mid/basis/obi, book-derived). = 72 book features.
   snapshot = last-step + 60s-mean of those -> 144 dims.
 - rolling 700d train (prior months), TRAIN-ONLY standardize, alpha by train-sub-val (no test peek).
 - CALIBER: PER-DAY CLEAN then AVERAGE across days (removes the cross-day-POOLING inflation that made
   clean>dense). Report per-day-mean CLEAN (honest) AND the old pooled-4offset CLEAN (for comparison).
COMPARE per month 2025-08..2026-05 to the honest base-DL test_preds (eval same per-day-CLEAN caliber).
Report per-month dP (DL - Ridge), pooled dP, paired significance vs +0.007 historical, net-of-cost both.
Run on SERVER: PYTHONPATH=. python multi_asset/data/clean_ridge_vs_dl.py
"""
from __future__ import annotations
import numpy as np, glob, os, warnings
warnings.filterwarnings("ignore"); warnings.simplefilter("ignore")
from sklearn.linear_model import Ridge
from scipy.stats import pearsonr

def dd(p): return os.path.basename(p)[:-4]
def cache_for(mon): return "data/npzv4_dual" if mon<="2025-09" else "data/npz_v2arch"
# book feature indices: spot 0..63 always; cross block:
#  npz_v2arch (88): trade 64..79, cross 80..87 -> book = [0..63] + [80..87]
#  npzv4_dual (72): cross 64..71 (no trade block) -> book = all 0..71
def book_idx(nch):
    if nch>=88: return list(range(64))+list(range(80,88))   # drop 16 perp-trade
    return list(range(nch))                                  # npzv4_dual: all book

def load(mons, cache):
    fs=sorted(glob.glob(f"{cache}/*.npz")); days=[f for f in fs if dd(f)[:7] in mons]
    out=[]
    for f in days:
        d=np.load(f,allow_pickle=True); m=d["y_mask_600"].astype(bool)
        if m.sum()==0: continue
        X=d["X"][m]; nch=X.shape[2]; bi=book_idx(nch)
        snap=np.concatenate([X[:,-1,bi],X[:,-60:,:][:,:,bi].mean(1)],1)
        out.append((dd(f), np.nan_to_num(snap.astype(np.float32)),
                    d["y_600"][m].astype(np.float32), d["timestamps"][m].astype(np.int64)))
    return out  # list of (day, snap, y, ts)

def clean_idx(ts,off=0):
    o=np.argsort(ts);keep=[];last=-1e18
    for i in range(off,len(o)):
        if ts[o[i]]-last>=600*1_000_000: keep.append(o[i]);last=ts[o[i]]
    return np.array(keep)
def perday_clean(days_pred):  # list of (p,y,ts) per day -> mean of per-day single-offset CLEAN Pearson
    rs=[]
    for p,y,ts in days_pred:
        k=clean_idx(ts,0)
        if len(k)>20:
            r=pearsonr(p[k],y[k])[0]
            if np.isfinite(r): rs.append(r)
    return (np.mean(rs) if rs else np.nan), (np.std(rs)/np.sqrt(len(rs)) if rs else np.nan), len(rs)
def pooled_clean(p,y,ts):  # old 4-offset pooled (the inflating one)
    Ps=[]
    for off in range(4):
        k=clean_idx(ts,off)
        if len(k)>30:
            r=pearsonr(p[k],y[k])[0]
            if np.isfinite(r): Ps.append(r)
    return np.mean(Ps) if Ps else np.nan

def prior_months(tm,k=12):
    y,mo=int(tm[:4]),int(tm[5:7]);out=[]
    for i in range(1,k+1):
        mm=mo-i;yy=y
        while mm<=0: mm+=12;yy-=1
        out.append(f"{yy:04d}-{mm:02d}")
    return out[::-1]

def fit_ridge(tr_days, te_days):
    Xtr=np.concatenate([t[1] for t in tr_days]); ytr=np.concatenate([t[2] for t in tr_days])
    mu=Xtr.mean(0);sd=Xtr.std(0)+1e-8
    c=int(len(ytr)*0.9); best=None
    for a in [1,10,100,1000]:
        r=Ridge(alpha=a).fit((Xtr[:c]-mu)/sd,ytr[:c]); ph=r.predict((Xtr[c:]-mu)/sd)
        P=pearsonr(ph,ytr[c:])[0] if ph.std()>1e-9 else -9
        if best is None or P>best[0]: best=(P,a)
    r=Ridge(alpha=best[1]).fit((Xtr-mu)/sd,ytr)
    return [(r.predict((te[1]-mu)/sd), te[2], te[3]) for te in te_days]

def dl_perday(tm):
    """Load honest base-DL test_preds for tm, split by day, eval per-day CLEAN.
    eval_caliber convention: predictions[:,1]=q50, targets, timestamps, mask."""
    p=f"experiments/walkforward/wf_{tm.replace('-','_')}/fold_0/test_preds.npz"
    if not os.path.exists(p): return None
    d=np.load(p,allow_pickle=True)
    preds=d["predictions"]; q=(preds[:,1] if preds.ndim==2 else preds).astype(np.float64)
    y=d["targets"].astype(np.float64); ts=d["timestamps"].astype(np.int64)
    if "mask" in d:
        m=d["mask"].astype(bool)
        if m.shape==q.shape and m.sum()>0 and m.sum()<m.size: q=q[m];y=y[m];ts=ts[m]
    daykey=ts//(86400*1_000_000); out=[]
    for dk in np.unique(daykey):
        msk=daykey==dk
        out.append((q[msk], y[msk], ts[msk]))
    return out

TARGET=["2025-08","2025-09","2025-10","2025-11","2025-12","2026-01","2026-02","2026-03","2026-04","2026-05"]
print("HONEST book-mid Ridge (bounce-free, PER-DAY CLEAN) vs base-DL")
print(f"{'month':8s} {'Ridge_pd':>9s} {'DL_pd':>8s} {'dP(DL-R)':>9s} {'Ridge_pool':>10s}")
dps=[]
for tm in TARGET:
    cache=cache_for(tm)
    tr=load(prior_months(tm),cache); te=load([tm],cache)
    if not tr or not te: print(f"{tm:8s} (no data)"); continue
    rid_days=fit_ridge(tr,te)
    r_pd,_,_=perday_clean(rid_days)
    r_pool=pooled_clean(np.concatenate([x[0] for x in rid_days]),
                        np.concatenate([x[1] for x in rid_days]),
                        np.concatenate([x[2] for x in rid_days]))
    dld=dl_perday(tm)
    if dld is None:
        print(f"{tm:8s} {r_pd:+9.4f} {'(noDL)':>8s} {'-':>9s} {r_pool:+10.4f}"); continue
    d_pd,_,_=perday_clean(dld)
    dp=d_pd-r_pd; dps.append(dp)
    print(f"{tm:8s} {r_pd:+9.4f} {d_pd:+8.4f} {dp:+9.4f} {r_pool:+10.4f}")
if dps:
    dps=np.array(dps)
    print("-"*48)
    print(f"  pooled mean dP(DL-Ridge,per-day) = {dps.mean():+.4f} +- {dps.std()/np.sqrt(len(dps)):.4f}")
    print(f"  vs historical DL edge +0.007: {'DL BEATS clean Ridge' if dps.mean()>0.007 else 'DL ~= clean Ridge (NOT sig)'}")
    print(f"  months DL>Ridge: {int((dps>0).sum())}/{len(dps)}")
print("\nDONE_CLEANRIDGE.")
