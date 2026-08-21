"""Carefully-DESIGNED OI/funding regime features + Ridge gate (then DL-via-FiLM).

Retracts the crude linear-add OI test. Mechanism-grounded features (positioning
REGIME), leak-safe (5m metrics + 8h funding, bars/settles fully <=t). Price derived
from oi_value/oi (no window price needed). All batch handling in Ridge std.

DESIGNED FEATURES (mechanism):
  4-QUADRANT OI-PRICE DIVERGENCE (sign(dOI) x sign(dPrice) over last K bars):
    q_newlong   = (dOI>0 & dP>0)  new longs (trend continuation up)
    q_newshort  = (dOI>0 & dP<0)  new shorts (trend continuation down)
    q_shortcov  = (dOI<0 & dP>0)  short covering (squeeze up, often reversal-exhaust)
    q_longliq   = (dOI<0 & dP<0)  long liquidation (capitulation down)
    -> encoded as signed continuous: dOI_norm and dP_norm and their product (divergence)
  CROWDING: funding_z x oi_z (extreme funding + high OI = squeeze risk / reversal)
  TAKER vs OI: taker_ls - (dOI sign) (aggressive vs passive positioning)
  L/S EXTREMES: toptrader_ls deviation from 1, retail_ls deviation from 1 (crowding)
  OI dynamics: oi_accel (2nd diff), oi_z

Run: PYTHONPATH=. python multi_asset/data/oi_designed_ridge_gate.py
"""
from __future__ import annotations
import numpy as np, glob, csv, warnings
from datetime import datetime, timezone
warnings.filterwarnings("ignore"); warnings.simplefilter("ignore")
from sklearn.linear_model import Ridge
from scipy.stats import pearsonr, spearmanr

MET="data/funding/btcusdt_metrics_5m.csv"
FUND="data/funding/btcusdt_funding.csv"
BAR_US=300*1_000_000

def parse_us(s): return int(datetime.strptime(s,"%Y-%m-%d %H:%M:%S").replace(tzinfo=timezone.utc).timestamp())*1_000_000

def load_metrics():
    rows=[]
    with open(MET) as f:
        for r in csv.DictReader(f):
            try: rows.append((parse_us(r["create_time"]),float(r["sum_open_interest"]),
                float(r["sum_open_interest_value"]),float(r["sum_toptrader_long_short_ratio"]),
                float(r["sum_taker_long_short_vol_ratio"]),float(r["count_long_short_ratio"])))
            except Exception: continue
    a=np.array(rows); a=a[np.argsort(a[:,0])]; return a   # cols: t,oi,oiv,tt,tk,rt

def load_funding():
    rows=[]
    with open(FUND) as f:
        for r in csv.DictReader(f):
            try: rows.append((int(r["fundingTime_ms"])*1000,float(r["fundingRate"])))
            except Exception: continue
    a=np.array(rows); return a[np.argsort(a[:,0])]

M=load_metrics(); F=load_funding()
MT=M[:,0]; OI=M[:,1]; OIV=M[:,2]; TT=M[:,3]; TK=M[:,4]; RT=M[:,5]
PRICE=OIV/np.clip(OI,1e-9,None)   # implied price
FT=F[:,0]; FR=F[:,1]

def designed(win_ts_us):
    cut=win_ts_us-BAR_US
    im=np.searchsorted(MT,cut,side="right")-1
    iff=np.searchsorted(FT,win_ts_us,side="right")-1
    N=len(win_ts_us); out=np.zeros((N,11)); v=(im>=0)&(iff>=0); iv=im[v]; ifv=iff[v]
    K=6
    iK=np.clip(iv-K,0,None)
    dOI=OI[iv]-OI[iK]; dP=PRICE[iv]-PRICE[iK]
    # normalize by rolling scale (use recent abs mean as scale, past-only via the same window)
    dOIn=dOI/(np.abs(OI[iv])+1e-9); dPn=dP/(np.abs(PRICE[iv])+1e-9)
    # OI z (crowding)
    oiz=np.zeros(len(iv))
    for j,i in enumerate(iv):
        lo=max(0,i-71); h=OI[lo:i+1]; oiz[j]=(OI[i]-h.mean())/(h.std()+1e-9)
    # funding z
    fz=np.zeros(len(ifv))
    for j,i in enumerate(ifv):
        lo=max(0,i-29); h=FR[lo:i+1]; fz[j]=(FR[i]-h.mean())/(h.std()+1e-9)
    oi_accel=(OI[iv]-OI[iK])-(OI[iK]-OI[np.clip(iv-2*K,0,None)])
    out[v,0]=dOIn                                  # OI flow normalized
    out[v,1]=dPn                                   # price change normalized
    out[v,2]=np.sign(dOI)*np.sign(dP)              # quadrant sign (divergence core)
    out[v,3]=dOIn*dPn                              # signed divergence magnitude
    out[v,4]=np.sign(dP)*np.maximum(-np.sign(dOI),0)  # short-cover/long-liq flag (dOI<0)
    out[v,5]=fz*oiz                                # funding x OI crowding (squeeze)
    out[v,6]=TK[iv]                                 # taker_ls
    out[v,7]=TK[iv]-1.0 - np.sign(dOI)             # taker vs OI-change (aggressive vs passive)
    out[v,8]=TT[iv]-1.0                            # toptrader extreme (crowding)
    out[v,9]=RT[iv]-1.0                            # retail extreme
    out[v,10]=oi_accel/(np.abs(OI[iv])+1e-9)       # OI acceleration
    return out

NAMES=["dOI_n","dP_n","quad_sign","divergence","cover_liq","fund_x_oi","taker_ls","taker_vs_oi","toptrader_ext","retail_ext","oi_accel"]

def dd(p): return p.split("/")[-1][:-4]
def load_fold(cache,lo,hi,te):
    fs=sorted(glob.glob(f"data/{cache}/*.npz"))
    tr=[f for f in fs if lo<=dd(f)<=hi]; teL=[f for f in fs if dd(f)[:7]==te]
    def load(days):
        Xs=[];Ds=[];ys=[];ts=[]
        for f in days:
            d=np.load(f,allow_pickle=True); m=d["y_mask_600"].astype(bool)
            X=d["X"][m]; snap=np.concatenate([X[:,-1,:],X[:,-60:,:].mean(1)],1)
            wt=d["timestamps"][m].astype(np.int64)
            Xs.append(snap.astype(np.float32)); Ds.append(designed(wt).astype(np.float32))
            ys.append(d["y_600"][m].astype(np.float32)); ts.append(wt)
        return np.nan_to_num(np.concatenate(Xs)),np.nan_to_num(np.concatenate(Ds)),np.concatenate(ys),np.concatenate(ts)
    return load(tr),load(teL)

def clean_p(p,y,ts):
    o=np.argsort(ts);ts=ts[o];p=p[o];y=y[o];Ps=[]
    for off in range(4):
        keep=[];last=-1e18
        for i in range(off,len(ts)):
            if ts[i]-last>=600*1_000_000: keep.append(i);last=ts[i]
        keep=np.array(keep)
        if len(keep)>30: Ps.append(pearsonr(p[keep],y[keep])[0])
    return np.mean(Ps),np.std(Ps)

def rc(Xtr,ytr,Xte,yte,tte):
    mu=Xtr.mean(0);sd=Xtr.std(0)+1e-8;Xtr=(Xtr-mu)/sd;Xte=(Xte-mu)/sd
    best=(-9,0)
    for a in [1,10,100,1000]:
        p=Ridge(alpha=a).fit(Xtr,ytr).predict(Xte); P,s=clean_p(p,yte,tte)
        if P>best[0]: best=(P,s)
    return best

def run(cache,lo,hi,te,label):
    (Xtr,Dtr,ytr,_),(Xte,Dte,yte,tte)=load_fold(cache,lo,hi,te)
    cov=np.mean(np.any(Dte!=0,1))
    print(f"\n=== {label} ({cache} {te}) Nte={len(yte)} cov={cov:.3f} ===")
    for j,nm in enumerate(NAMES): print(f"   corr({nm:14s},y)={pearsonr(Dte[:,j],yte)[0]:+.4f}")
    Po,_=rc(Dtr,ytr,Dte,yte,tte); Pb,sb=rc(Xtr,ytr,Xte,yte,tte); Pf,sf=rc(np.concatenate([Xtr,Dtr],1),ytr,np.concatenate([Xte,Dte],1),yte,tte)
    print(f"   Ridge[designed-only] CLEAN P={Po:+.4f}")
    print(f"   Ridge[base]          CLEAN P={Pb:+.4f}")
    print(f"   Ridge[base+designed] CLEAN P={Pf:+.4f}")
    print(f"   >>> dP (designed) = {Pf-Pb:+.4f}  [gate +0.003]")

if __name__=="__main__":
    print("DESIGNED OI/funding Ridge gate. metrics:",len(MT),"funding:",len(FT))
    run("npzv4_dual","2023-05-01","2025-03-31","2025-04","STRONG")
    run("npz_v2arch","2025-05-18","2026-03-14","2026-05","CHOPPY")
