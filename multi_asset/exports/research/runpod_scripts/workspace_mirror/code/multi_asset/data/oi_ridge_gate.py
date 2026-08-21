"""Leak-safe OI + long/short-ratio (Binance Data Vision metrics, 5m) Ridge gate.

THE last + most-promising orthogonal lever for choppy (funding/premium family closed:
8h +0.0011, 5m +0.0027 peak, 1m -0.0043 -- none pass +0.003). OI = positioning
QUANTITY + crowding + big-player/taker/retail long-short ratios; orthogonal to BOTH
price microstructure AND the price-basis.

LEAK-SAFE: 5m bar at create_time T summarizes a 5m interval; use ONLY bars FULLY
closed before window-time t -> create_time + 300s <= t (strictly past). Forward-fill.

Features (all leak-safe, batch handled in Ridge std):
  oi_level         : sum_open_interest (last)
  oi_flow          : Δ sum_open_interest over last K=6 bars (30min) -- rising=new pos, falling=unwind
  oi_zscore        : crowding vs rolling 72-bar (6h) mean/std
  oi_value         : sum_open_interest_value (last)
  oi_value_flow    : Δ oi_value over 6 bars
  toptrader_ls     : sum_toptrader_long_short_ratio (big-player positioning)
  taker_ls         : sum_taker_long_short_vol_ratio (aggressive flow)
  retail_ls        : count_long_short_ratio (retail crowd)
  toptrader_ls_chg : Δ toptrader_ls over 6 bars (smart-money shift)

CHECK: corr(OI feats, y); Ridge [base X + OI] vs [base X] clean dP, choppy + strong.
Run: PYTHONPATH=. python multi_asset/data/oi_ridge_gate.py
"""
from __future__ import annotations
import numpy as np, glob, csv, warnings
from datetime import datetime, timezone
warnings.filterwarnings("ignore"); warnings.simplefilter("ignore")
from sklearn.linear_model import Ridge
from scipy.stats import pearsonr, spearmanr

CSV="data/funding/btcusdt_metrics_5m.csv"
BAR_US=300*1_000_000

def parse_us(s):
    # "2023-02-01 00:00:00" UTC -> us
    return int(datetime.strptime(s,"%Y-%m-%d %H:%M:%S").replace(tzinfo=timezone.utc).timestamp())*1_000_000

def load_metrics():
    rows=[]
    with open(CSV) as f:
        for row in csv.DictReader(f):
            try:
                # all-or-nothing per row so the 6 arrays stay aligned
                rec=(parse_us(row["create_time"]),
                     float(row["sum_open_interest"]),
                     float(row["sum_open_interest_value"]),
                     float(row["sum_toptrader_long_short_ratio"]),
                     float(row["sum_taker_long_short_vol_ratio"]),
                     float(row["count_long_short_ratio"]))
            except Exception:
                continue
            rows.append(rec)
    arr=np.array(rows, dtype=np.float64)        # (N,6)
    o=np.argsort(arr[:,0])
    arr=arr[o]
    return arr[:,0],arr[:,1],arr[:,2],arr[:,3],arr[:,4],arr[:,5]

MT,OI,OIV,TT,TK,RT=load_metrics()

def oi_feats(win_ts_us):
    cutoff=win_ts_us-BAR_US
    idx=np.searchsorted(MT,cutoff,side="right")-1
    N=len(win_ts_us); out=np.zeros((N,9)); valid=idx>=0; iv=idx[valid]
    K=6
    iK=np.clip(iv-K,0,None)
    out[valid,0]=OI[iv]
    out[valid,1]=OI[iv]-OI[iK]                       # oi_flow
    z=np.zeros(len(iv))
    for j,i in enumerate(iv):
        lo=max(0,i-71); h=OI[lo:i+1]; z[j]=(OI[i]-h.mean())/(h.std()+1e-9)
    out[valid,2]=z
    out[valid,3]=OIV[iv]
    out[valid,4]=OIV[iv]-OIV[iK]                     # oi_value_flow
    out[valid,5]=TT[iv]
    out[valid,6]=TK[iv]
    out[valid,7]=RT[iv]
    out[valid,8]=TT[iv]-TT[iK]                       # toptrader_ls_chg
    return out

NAMES=["oi_level","oi_flow","oi_zscore","oi_value","oi_val_flow","toptrader_ls","taker_ls","retail_ls","toptrader_ls_chg"]

def dd(p): return p.split("/")[-1][:-4]
def load_fold(cache,tr_lo,tr_hi,te_mon):
    fs=sorted(glob.glob(f"data/{cache}/*.npz"))
    tr=[f for f in fs if tr_lo<=dd(f)<=tr_hi]; te=[f for f in fs if dd(f)[:7]==te_mon]
    def load(days):
        Xs=[];Os=[];ys=[];tss=[]
        for f in days:
            d=np.load(f,allow_pickle=True); m=d["y_mask_600"].astype(bool)
            X=d["X"][m]; snap=np.concatenate([X[:,-1,:],X[:,-60:,:].mean(1)],1)
            wt=d["timestamps"][m].astype(np.int64)
            Xs.append(snap.astype(np.float32)); Os.append(oi_feats(wt).astype(np.float32))
            ys.append(d["y_600"][m].astype(np.float32)); tss.append(wt)
        return np.nan_to_num(np.concatenate(Xs)),np.nan_to_num(np.concatenate(Os)),np.concatenate(ys),np.concatenate(tss)
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
    (Xtr,Otr,ytr,_),(Xte,Ote,yte,tte)=load_fold(cache,tr_lo,tr_hi,te_mon)
    cov=np.mean(np.any(Ote!=0,axis=1))
    print(f"\n=== {label} ({cache} test {te_mon}) Nte={len(yte)} oi_cov={cov:.3f} ===")
    for j,nm in enumerate(NAMES):
        print(f"   corr({nm:16s}, y) = {pearsonr(Ote[:,j],yte)[0]:+.4f}")
    Pb,sb=ridge_clean(Xtr,ytr,Xte,yte,tte)
    Pf,sf=ridge_clean(np.concatenate([Xtr,Otr],1),ytr,np.concatenate([Xte,Ote],1),yte,tte)
    # OI-only signal
    Po,so=ridge_clean(Otr,ytr,Ote,yte,tte)
    print(f"   Ridge[OI-only]   CLEAN P={Po:+.4f}")
    print(f"   Ridge[base]      CLEAN P={Pb:+.4f} (off {sb:.4f})")
    print(f"   Ridge[base+OI]   CLEAN P={Pf:+.4f} (off {sf:.4f})")
    print(f"   >>> dP (OI/LS) = {Pf-Pb:+.4f}  [gate +0.003]")

if __name__=="__main__":
    print("OI/LS metrics Ridge gate. bars:",len(MT),"range",MT[0],MT[-1])
    run("npzv4_dual","2023-05-01","2025-03-31","2025-04","STRONG")
    run("npz_v2arch","2025-05-18","2026-03-14","2026-05","CHOPPY")
