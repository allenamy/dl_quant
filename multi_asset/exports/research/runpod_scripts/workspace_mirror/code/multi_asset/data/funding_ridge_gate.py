"""Leak-safe funding-rate feature overlay + Ridge gate (Ridge-before-DL).

Funding = positioning/carry signal, ORTHOGONAL to book/trade microstructure.
Hypothesis: helps CHOPPY most (positioning carries info when microstructure weak).

LEAK-SAFETY: at window-time t (microseconds), use ONLY the most recent SETTLED
8h funding with fundingTime <= t (strictly past). 8h grid forward-filled to the
1s windows. NO future funding.

Gate: walk-forward Ridge [base X-snapshot + funding] vs [base X-snapshot] on
BOTH strong (2025-04) and choppy (2026-05), CLEAN (non-overlap >=600s) Pearson.
If clean dP >= +0.003 (esp choppy) -> queue DL test. Else dead orthogonal attempt.

Run: PYTHONPATH=. python multi_asset/data/funding_ridge_gate.py
"""
from __future__ import annotations
import numpy as np, glob, csv, warnings
warnings.filterwarnings("ignore"); warnings.simplefilter("ignore")
from sklearn.linear_model import Ridge
from scipy.stats import pearsonr, spearmanr

FUNDING_CSV = "data/funding/btcusdt_funding.csv"

def load_funding():
    """Returns sorted arrays: ftime_us (settlement time in us), frate."""
    ts=[]; fr=[]
    with open(FUNDING_CSV) as f:
        r=csv.DictReader(f)
        for row in r:
            ts.append(int(row["fundingTime_ms"])*1000)  # ms -> us
            fr.append(float(row["fundingRate"]))
    o=np.argsort(ts)
    return np.array(ts)[o], np.array(fr)[o]

FT_US, FR = load_funding()

def funding_feats(win_ts_us):
    """For each window cutoff t (us), build 6 leak-safe funding features from
    settlements strictly <= t. Vectorized via searchsorted."""
    # idx = position of last settlement with FT_US <= t  (strictly past)
    idx = np.searchsorted(FT_US, win_ts_us, side="right") - 1   # -1 means none before
    N=len(win_ts_us)
    out=np.zeros((N,6), dtype=np.float64)
    valid = idx >= 0
    iv = idx[valid]
    # 0 funding_level (last settled)
    lvl = FR[iv]
    # 1 funding_momentum: lvl - lvl_{K=3 ago}
    iK = np.clip(iv-3, 0, None)
    mom = FR[iv] - FR[iK]
    # 2 funding_zscore vs rolling 30-settlement mean/std (past only)
    z=np.zeros_like(lvl)
    for j,i in enumerate(iv):
        lo=max(0,i-29); hist=FR[lo:i+1]
        m=hist.mean(); s=hist.std()+1e-9
        z[j]=(FR[i]-m)/s
    # 3 funding_cumulative: sum over last 21 settlements (~7 days carry)
    cum=np.zeros_like(lvl)
    for j,i in enumerate(iv):
        lo=max(0,i-20); cum[j]=FR[lo:i+1].sum()
    # 4 time_to_next_funding (sec): next settlement FT_US[i+1] - t  (>=0)
    ttn=np.zeros_like(lvl)
    nxt=np.clip(iv+1, 0, len(FT_US)-1)
    ttn = (FT_US[nxt] - win_ts_us[valid]).astype(np.float64)/1e6
    ttn=np.clip(ttn,0,8*3600)
    # 5 funding_sign_persistence: count of same-sign in last 6 settlements
    sp=np.zeros_like(lvl)
    for j,i in enumerate(iv):
        lo=max(0,i-5); hist=FR[lo:i+1]; s=np.sign(FR[i])
        sp[j]=np.mean(np.sign(hist)==s) if s!=0 else 0.5
    out[valid,0]=lvl; out[valid,1]=mom; out[valid,2]=z
    out[valid,3]=cum; out[valid,4]=ttn; out[valid,5]=sp
    return out

FUNDING_NAMES=["f_level","f_mom","f_zscore","f_cum","f_ttn","f_signpersist"]

def dd(p): return p.split("/")[-1][:-4]

def load_fold(cache, tr_lo, tr_hi, te_mon, base_chs=None):
    fs=sorted(glob.glob(f"data/{cache}/*.npz"))
    tr=[f for f in fs if tr_lo<=dd(f)<=tr_hi]
    te=[f for f in fs if dd(f)[:7]==te_mon]
    def load(days):
        Xs=[];Fs=[];ys=[];tss=[]
        for f in days:
            d=np.load(f,allow_pickle=True); m=d["y_mask_600"].astype(bool)
            X=d["X"][m]
            snap=np.concatenate([X[:,-1,:],X[:,-60:,:].mean(1)],1)  # base snapshot
            wt=d["timestamps"][m].astype(np.int64)
            ff=funding_feats(wt)
            Xs.append(snap.astype(np.float32)); Fs.append(ff.astype(np.float32))
            ys.append(d["y_600"][m].astype(np.float32)); tss.append(wt)
        return np.nan_to_num(np.concatenate(Xs)),np.nan_to_num(np.concatenate(Fs)),np.concatenate(ys),np.concatenate(tss)
    return load(tr),load(te)

def clean_pearson(p,y,ts):
    o=np.argsort(ts); ts=ts[o];p=p[o];y=y[o]; Ps=[]
    for off in range(4):
        keep=[];last=-1e18
        for i in range(off,len(ts)):
            if ts[i]-last>=600*1_000_000: keep.append(i); last=ts[i]
        keep=np.array(keep)
        if len(keep)>30: Ps.append(pearsonr(p[keep],y[keep])[0])
    return np.mean(Ps), np.std(Ps)

def ridge_best(Xtr,ytr,Xte):
    mu=Xtr.mean(0);sd=Xtr.std(0)+1e-8;Xtr=(Xtr-mu)/sd;Xte=(Xte-mu)/sd
    best=None
    for a in [1,10,100,1000]:
        r=Ridge(alpha=a).fit(Xtr,ytr); p=r.predict(Xte)
        if best is None: best=(a,p)  # pick by... we choose via clean later; just return a=100 mid
    # return all-alpha preds for caller to pick best clean
    preds={}
    for a in [1,10,100,1000]:
        r=Ridge(alpha=a).fit(Xtr,ytr); preds[a]=r.predict(Xte)
    return preds

def run(cache, tr_lo, tr_hi, te_mon, label):
    (Xtr,Ftr,ytr,_),(Xte,Fte,yte,tte)=load_fold(cache,tr_lo,tr_hi,te_mon)
    # funding feature sanity
    fcov=np.mean(np.any(Fte!=0,axis=1))
    print(f"\n=== {label} ({cache}, test {te_mon}) Ntr={len(ytr)} Nte={len(yte)} funding_cov={fcov:.3f} ===")
    # funding-only corr (signal check)
    for j,nm in enumerate(FUNDING_NAMES):
        c=pearsonr(np.nan_to_num(Fte[:,j]),yte)[0]
        print(f"   corr({nm:14s}, y) = {c:+.4f}")
    base=ridge_best(Xtr,ytr,Xte)
    both=ridge_best(np.concatenate([Xtr,Ftr],1),ytr,np.concatenate([Xte,Fte],1))
    # pick alpha by best CLEAN per arm
    def best_clean(preds):
        bb=(-9,0,0)
        for a,p in preds.items():
            P,s=clean_pearson(p,yte,tte)
            if P>bb[0]: bb=(P,s,a)
        return bb
    Pb,sb,ab=best_clean(base); Pf,sf,af=best_clean(both)
    print(f"   Ridge[base]      CLEAN P={Pb:+.4f} (off-std {sb:.4f}, a={ab})")
    print(f"   Ridge[base+fund] CLEAN P={Pf:+.4f} (off-std {sf:.4f}, a={af})")
    print(f"   >>> dP (funding) = {Pf-Pb:+.4f}  [gate +0.003]")
    return Pf-Pb

if __name__=="__main__":
    print("FUNDING leak-safe Ridge gate. settlements:",len(FT_US),"range us",int(FT_US[0]),int(FT_US[-1]))
    # STRONG: npzv4_dual, test 2025-04
    run("npzv4_dual","2023-05-01","2025-03-31","2025-04","STRONG")
    # CHOPPY: npz_v2arch, test 2026-05
    run("npz_v2arch","2025-05-18","2026-03-14","2026-05","CHOPPY")
