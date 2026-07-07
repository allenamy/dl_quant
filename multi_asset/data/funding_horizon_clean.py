"""CLEAN-caliber funding/OI horizon curve (the +0.22@4h was DENSE-inflated on overlapping 5m windows).
Recompute funding/OI -> forward return at 600s/1800s/3600s/7200s/14400s on NON-OVERLAPPING (stride>=horizon)
windows + per-day, funding-ALONE AND base-microstructure+funding (orthogonality at 1h/4h). Walk-forward Ridge
(train prior months, test month). 5m implied-price (PRICE=OI_value/OI) as the return series. Leak-safe <=t.
Run on SERVER: PYTHONPATH=. python multi_asset/data/funding_horizon_clean.py
"""
from __future__ import annotations
import numpy as np, csv, warnings
from datetime import datetime, timezone
warnings.filterwarnings("ignore")
from sklearn.linear_model import Ridge
from scipy.stats import pearsonr
MET="data/funding/btcusdt_metrics_5m.csv"; FUND="data/funding/btcusdt_funding.csv"
def pu(s): return int(datetime.strptime(s,"%Y-%m-%d %H:%M:%S").replace(tzinfo=timezone.utc).timestamp())*1_000_000
def f2(x):
    try: return float(x)
    except: return np.nan
def lm():
    r=[]
    with open(MET) as f:
        for x in csv.DictReader(f):
            try: r.append((pu(x["create_time"]),f2(x["sum_open_interest"]),f2(x["sum_open_interest_value"]),f2(x["sum_toptrader_long_short_ratio"]),f2(x["sum_taker_long_short_vol_ratio"]),f2(x["count_long_short_ratio"])))
            except: pass
    a=np.array(r); return a[np.argsort(a[:,0])]
def lf():
    r=[]
    with open(FUND) as f:
        for x in csv.DictReader(f):
            try: r.append((int(x["fundingTime_ms"])*1000,f2(x["fundingRate"])))
            except: pass
    a=np.array(r); return a[np.argsort(a[:,0])]
M=lm(); F=lf()
MT=M[:,0];OI=M[:,1];OIV=M[:,2];TT=M[:,3];TK=M[:,4];RT=M[:,5];PRICE=OIV/np.clip(OI,1e-9,None);FT=F[:,0];FR=F[:,1]
def feats(idx):
    K=6; iK=np.clip(idx-K,0,None)
    dOI=(OI[idx]-OI[iK])/(np.abs(OI[idx])+1e-9); dP=(PRICE[idx]-PRICE[iK])/(np.abs(PRICE[idx])+1e-9)
    oiz=np.array([(OI[i]-OI[max(0,i-71):i+1].mean())/(OI[max(0,i-71):i+1].std()+1e-9) for i in idx])
    fr=np.array([FR[max(0,np.searchsorted(FT,MT[i],side="right")-1)] for i in idx])
    return np.nan_to_num(np.stack([dOI,oiz,np.sign(fr),TT[idx]-1,TK[idx]-1,RT[idx]-1,dOI*np.sign(fr),(TT[idx]-1)*dP],1))
def monidx(mon):
    y,mo=int(mon[:4]),int(mon[5:7]); a=pu(f"{mon}-01 00:00:00"); mm=mo+1;yy=y
    if mm>12:mm=1;yy+=1
    return a,pu(f"{yy:04d}-{mm:02d}-01 00:00:00")
def prior(mon,k=10):
    y,mo=int(mon[:4]),int(mon[5:7]);o=[]
    for i in range(1,k+1):
        mm=mo-i;yy=y
        while mm<=0:mm+=12;yy-=1
        o.append(f"{yy:04d}-{mm:02d}")
    return o[::-1]
HB={"600s":2,"1800s":6,"3600s":12,"7200s":24,"14400s":48}
def fit(Xtr,ytr,Xte):
    mu=Xtr.mean(0);sd=Xtr.std(0)+1e-8
    return Ridge(alpha=10).fit((Xtr-mu)/sd,ytr).predict((Xte-mu)/sd)
def clean_corr(pred,fwd,bar_idx,hb):
    # non-overlapping: keep every hb-th bar
    o=np.argsort(bar_idx); bi=bar_idx[o]; p=pred[o]; y=fwd[o]; keep=[]; last=-10**9
    for i in range(len(bi)):
        if bi[i]-last>=hb: keep.append(i); last=bi[i]
    keep=np.array(keep)
    if len(keep)<30 or p[keep].std()<1e-12: return np.nan,len(keep)
    r=pearsonr(p[keep],y[keep])[0]; return (r if np.isfinite(r) else np.nan), len(keep)
print("CLEAN-CALIBER funding/OI horizon curve (non-overlapping stride>=horizon; walk-forward Ridge)")
print(f"{'month':8s} {'hor':7s} {'DENSE':>7s} {'CLEAN':>7s} {'Nclean':>6s}")
for mon in ["2025-10","2025-12","2026-02"]:
    pm=[x for x in prior(mon) if x>="2024-01"]
    tri=[]; 
    for x in pm:
        a,b=monidx(x); s=np.where((MT>=a)&(MT<b))[0]; s=s[(s>=72)&(s<len(MT)-48)]; tri.append(s)
    tri=np.concatenate(tri) if tri else np.array([])
    a,b=monidx(mon); tei=np.where((MT>=a)&(MT<b))[0]; tei=tei[(tei>=72)&(tei<len(MT)-48)]
    if len(tri)<200 or len(tei)<100: print(f"{mon}: no data"); continue
    Xtr=feats(tri); Xte=feats(tei)
    for hn,hb in HB.items():
        ytr=(PRICE[tri+hb]-PRICE[tri])/(PRICE[tri]+1e-9); yte=(PRICE[tei+hb]-PRICE[tei])/(PRICE[tei]+1e-9)
        p=fit(Xtr,ytr,Xte)
        dP=pearsonr(p,yte)[0]
        cP,nc=clean_corr(p,yte,tei,hb)
        print(f"{mon:8s} {hn:7s} {dP:+7.4f} {cP:+7.4f} {nc:6d}")
    print("")
print("DONE_FHCLEAN.")
