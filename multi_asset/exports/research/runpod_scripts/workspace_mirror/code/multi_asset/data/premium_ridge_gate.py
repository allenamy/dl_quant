"""Leak-safe PREMIUM-INDEX (5m) feature overlay + Ridge gate + corr-vs-basis.

Premium index pidx_close = (perp mark - spot index)/index = the continuous signal
driving 8h funding. Q: is the FINE-GRAINED (5m) premium better than the 8h funding
(marginal) AND is it just our perp-spot basis (already tested = marginal/regime)?

LEAK-SAFE: at window t (us), use most recent 5m bar with openTime <= t (strictly
past; a 5m bar opened at T summarizes [T,T+5m) but we only use bars whose openTime
<= t, i.e. fully-or-partially-past bars; to be strict we require openTime+300s<=t so
the bar is FULLY closed before t).

CHECK 1: corr(premium_level, basis_z / x_basis_bps) — if >0.8, premium == basis.
CHECK 2: Ridge [base X + premium] vs [base X], clean ΔP strong+choppy.

Run: PYTHONPATH=. python multi_asset/data/premium_ridge_gate.py
"""
from __future__ import annotations
import numpy as np, glob, csv, warnings
warnings.filterwarnings("ignore"); warnings.simplefilter("ignore")
from sklearn.linear_model import Ridge
from scipy.stats import pearsonr, spearmanr

PREM_CSV="data/funding/btcusdt_premium_index_5m.csv"

def load_prem():
    t=[];c=[]
    with open(PREM_CSV) as f:
        for row in csv.DictReader(f):
            t.append(int(row["openTime_ms"])*1000); c.append(float(row["pidx_close"]))
    o=np.argsort(t); return np.array(t)[o], np.array(c)[o]

PT_US, PC = load_prem()
BAR_US=300*1_000_000

def prem_feats(win_ts_us):
    """4 leak-safe premium features from bars FULLY closed before t."""
    # last bar with openTime + 300s <= t  ->  openTime <= t - 300s
    cutoff = win_ts_us - BAR_US
    idx = np.searchsorted(PT_US, cutoff, side="right") - 1
    N=len(win_ts_us); out=np.zeros((N,4))
    valid=idx>=0; iv=idx[valid]
    lvl=PC[iv]
    iK=np.clip(iv-6,0,None); mom=PC[iv]-PC[iK]          # Δ over ~30min (6 bars)
    z=np.zeros_like(lvl)
    for j,i in enumerate(iv):
        lo=max(0,i-71); h=PC[lo:i+1]; z[j]=(PC[i]-h.mean())/(h.std()+1e-9)  # 6h roll
    iK2=np.clip(iv-1,0,None); iK3=np.clip(iv-2,0,None)
    accel=(PC[iv]-PC[iK2])-(PC[iK2]-PC[iK3])             # 2nd diff
    out[valid,0]=lvl;out[valid,1]=mom;out[valid,2]=z;out[valid,3]=accel
    return out

PNAMES=["prem_level","prem_mom","prem_zscore","prem_accel"]

def dd(p): return p.split("/")[-1][:-4]

def load_fold(cache, tr_lo,tr_hi, te_mon):
    fs=sorted(glob.glob(f"data/{cache}/*.npz"))
    tr=[f for f in fs if tr_lo<=dd(f)<=tr_hi]; te=[f for f in fs if dd(f)[:7]==te_mon]
    # find basis channel: prefer X_basis basis_z; else cross x_basis_bps
    def load(days):
        Xs=[];Ps=[];Bs=[];ys=[];tss=[]
        for f in days:
            d=np.load(f,allow_pickle=True); m=d["y_mask_600"].astype(bool)
            X=d["X"][m]; snap=np.concatenate([X[:,-1,:],X[:,-60:,:].mean(1)],1)
            wt=d["timestamps"][m].astype(np.int64)
            Xs.append(snap.astype(np.float32)); Ps.append(prem_feats(wt).astype(np.float32))
            ys.append(d["y_600"][m].astype(np.float32)); tss.append(wt)
            # basis: X_basis basis_z (idx 3) last-step, else cross x_basis_bps
            if "X_basis" in d.files:
                bn=list(d["basis_names"]); bi=bn.index("basis_z") if "basis_z" in bn else 3
                Bs.append(d["X_basis"][m][:,-1,bi].astype(np.float32))
            elif "cross_names" in d.files and "x_basis_bps" in list(d["cross_names"]):
                ci=list(d["cross_names"]).index("x_basis_bps"); Bs.append(X[:,-1,64+ci].astype(np.float32))
            else: Bs.append(np.zeros(m.sum(),dtype=np.float32))
        return (np.nan_to_num(np.concatenate(Xs)),np.nan_to_num(np.concatenate(Ps)),
                np.nan_to_num(np.concatenate(Bs)),np.concatenate(ys),np.concatenate(tss))
    return load(tr),load(te)

def clean_p(p,y,ts):
    o=np.argsort(ts);ts=ts[o];p=p[o];y=y[o];Ps=[]
    for off in range(4):
        keep=[];last=-1e18
        for i in range(off,len(ts)):
            if ts[i]-last>=600*1_000_000: keep.append(i);last=ts[i]
        keep=np.array(keep)
        if len(keep)>30: Ps.append(pearsonr(p[keep],y[keep])[0])
    return np.mean(Ps),np.std(Ps)

def ridge_clean(Xtr,ytr,Xte,yte,tte):
    mu=Xtr.mean(0);sd=Xtr.std(0)+1e-8;Xtr=(Xtr-mu)/sd;Xte=(Xte-mu)/sd
    best=(-9,0)
    for a in [1,10,100,1000]:
        p=Ridge(alpha=a).fit(Xtr,ytr).predict(Xte); P,s=clean_p(p,yte,tte)
        if P>best[0]: best=(P,s)
    return best

def run(cache,tr_lo,tr_hi,te_mon,label):
    (Xtr,Ptr,Btr,ytr,_),(Xte,Pte,Bte,yte,tte)=load_fold(cache,tr_lo,tr_hi,te_mon)
    cov=np.mean(np.any(Pte!=0,axis=1))
    print(f"\n=== {label} ({cache} test {te_mon}) Nte={len(yte)} prem_cov={cov:.3f} ===")
    # CHECK 1: corr(premium_level, basis)
    cb=pearsonr(Pte[:,0],Bte)[0] if Bte.std()>0 else float("nan")
    print(f"   corr(prem_level, basis) = {cb:+.4f}  (>0.8 => premium == basis)")
    for j,nm in enumerate(PNAMES):
        print(f"   corr({nm:12s}, y) = {pearsonr(Pte[:,j],yte)[0]:+.4f}")
    Pb,sb=ridge_clean(Xtr,ytr,Xte,yte,tte)
    Pf,sf=ridge_clean(np.concatenate([Xtr,Ptr],1),ytr,np.concatenate([Xte,Pte],1),yte,tte)
    print(f"   Ridge[base]      CLEAN P={Pb:+.4f} (off {sb:.4f})")
    print(f"   Ridge[base+prem] CLEAN P={Pf:+.4f} (off {sf:.4f})")
    print(f"   >>> dP (premium) = {Pf-Pb:+.4f}  [gate +0.003]")

if __name__=="__main__":
    print("PREMIUM-INDEX 5m Ridge gate. bars:",len(PT_US))
    run("npzv4_dual","2023-05-01","2025-03-31","2025-04","STRONG")
    run("npz_v2arch","2025-05-18","2026-03-14","2026-05","CHOPPY")
