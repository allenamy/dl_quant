"""DESIGNED funding/OI x microstructure INTERACTION features (#1) + Ridge gate (strong + drift).
Mechanism (机制>堆叠): funding/OI is slow POSITIONING STATE -> must CONDITION how the book/trade signal is read
and flag the regime-inversion, NOT be an additive per-step channel (that's the #29-penalty raw-concat, +0.0012
null). prior FiLM/router used the COARSE 6-ch regime_prior; the rich funding/OI x microstructure INTERACTIONS
are UNTESTED. A FEW designed features (leak-safe <=t):

 INT1 funding_sign x OBI         : book pressure read conditional on carry regime (long-carry vs short)
 INT2 dOI_norm x trade_flow      : OI up+buy = new-money momentum; OI down+sell = deleveraging/liq
 INT3 (topLS-1) x price_mom      : crowded-long + price DOWN = cascade risk = THE drift-inversion
 INT4 premium_chg x microprice   : basis-pressure x book lean
 INT5 funding_z x rvol           : carry extreme x volatility (squeeze setup)
 INT6 (taker_ls-1) x obi         : aggressive flow vs passive book
+ the raw positioning levels (funding_sign, dOI_norm, topLS-1) for the model to also read directly.

GATE: walk-forward Ridge [base book-snapshot] vs [base + interactions] vs [interactions-only], per-day-CLEAN +
DENSE Pearson, on 2025-10 (strong) + 2025-12, 2026-02 (DRIFT = key). dP>=+0.003 (esp drift) -> queue DL.
microstructure terms from the cache X (book/trade snapshot, <=t); funding/OI from designed() (verified leak-safe).
Run on SERVER: PYTHONPATH=. python multi_asset/data/funding_interaction_gate.py
"""
from __future__ import annotations
import numpy as np, glob, os, csv, warnings
from datetime import datetime, timezone
warnings.filterwarnings("ignore"); warnings.simplefilter("ignore")
from sklearn.linear_model import Ridge
from scipy.stats import pearsonr
CACHE="data/npz_v2arch"; MET="data/funding/btcusdt_metrics_5m.csv"; FUND="data/funding/btcusdt_funding.csv"
PREM="data/funding/btcusdt_premium_index_5m.csv"; BAR_US=300*1_000_000
# npz_v2arch channel idx (from builder): cross block at 80..87: x_mid_ratio_log=80, x_basis_bps=81, x_obi_diff=84,
# x_mpdev_diff=85, x_rvol_ratio_log=86, x_tradeflow_ratio=87; perp-trade net flow at 64+2=66 (pt_net_trade_flow_1s)
CH_MIDR=80; CH_OBI=84; CH_MPDEV=85; CH_RVOL=86; CH_TFLOW=87; CH_NTF=66
def parse_us(s): return int(datetime.strptime(s,"%Y-%m-%d %H:%M:%S").replace(tzinfo=timezone.utc).timestamp())*1_000_000
def f2(x):
    try: return float(x)
    except: return np.nan
def load_met():
    rows=[]
    with open(MET) as f:
        for r in csv.DictReader(f):
            try: rows.append((parse_us(r["create_time"]),f2(r["sum_open_interest"]),f2(r["sum_open_interest_value"]),f2(r["sum_toptrader_long_short_ratio"]),f2(r["sum_taker_long_short_vol_ratio"])))
            except Exception: continue
    a=np.array(rows); return a[np.argsort(a[:,0])]
def load_fund():
    rows=[]
    with open(FUND) as f:
        for r in csv.DictReader(f):
            try: rows.append((int(r["fundingTime_ms"])*1000,f2(r["fundingRate"])))
            except Exception: continue
    a=np.array(rows); return a[np.argsort(a[:,0])]
def load_prem():
    rows=[]
    with open(PREM) as f:
        for r in csv.DictReader(f):
            try: rows.append((int(r["openTime_ms"])*1000,f2(r["pidx_close"])))
            except Exception: continue
    a=np.array(rows); return a[np.argsort(a[:,0])]
M=load_met(); F=load_fund(); P=load_prem()
MT=M[:,0]; OI=M[:,1]; OIV=M[:,2]; TT=M[:,3]; TK=M[:,4]; PRICE=OIV/np.clip(OI,1e-9,None); FT=F[:,0]; FR=F[:,1]; PTT=P[:,0]; PV=P[:,1]

def pos_state(win_ts):
    """leak-safe <=t positioning state per window: funding_sign, funding_z, dOI_norm, topLS_dev, taker_dev,
    price_mom(6-bar), premium_chg."""
    cut=win_ts-BAR_US; im=np.searchsorted(MT,cut,side="right")-1; iff=np.searchsorted(FT,win_ts,side="right")-1
    ip=np.searchsorted(PTT,win_ts-BAR_US,side="right")-1
    N=len(win_ts); o=np.zeros((N,7)); v=(im>=0)&(iff>=0)&(ip>=0); iv=im[v]; ifv=iff[v]; ipv=ip[v]; K=6
    iK=np.clip(iv-K,0,None)
    dOI=(OI[iv]-OI[iK])/(np.abs(OI[iv])+1e-9); dP=(PRICE[iv]-PRICE[iK])/(np.abs(PRICE[iv])+1e-9)
    fz=np.zeros(len(ifv))
    for j,i in enumerate(ifv):
        lo=max(0,i-29); h=FR[lo:i+1]; fz[j]=(FR[i]-h.mean())/(h.std()+1e-9)
    pchg=(PV[ipv]-PV[np.clip(ipv-K,0,None)])
    o[v,0]=np.sign(FR[ifv]); o[v,1]=fz; o[v,2]=dOI; o[v,3]=TT[iv]-1.0; o[v,4]=TK[iv]-1.0; o[v,5]=dP; o[v,6]=pchg
    return np.nan_to_num(o)

def dd(p): return os.path.basename(p)[:-4]
def load_month(mon):
    fs=sorted(glob.glob(f"{CACHE}/*.npz")); days=[f for f in fs if dd(f)[:7]==mon]
    Bs=[];Is=[];ys=[];ts=[]
    for f in days:
        d=np.load(f,allow_pickle=True); m=d["y_mask_600"].astype(bool)
        if m.sum()==0: continue
        X=d["X"][m]; snap=np.concatenate([X[:,-1,:],X[:,-60:,:].mean(1)],1)  # base book/trade snapshot
        wt=d["timestamps"][m].astype(np.int64); ps=pos_state(wt)
        # microstructure terms (last-step)
        obi=X[:,-1,CH_OBI]; tflow=X[:,-1,CH_TFLOW]; ntf=X[:,-1,CH_NTF]; mpdev=X[:,-1,CH_MPDEV]; rvol=X[:,-1,CH_RVOL]; midr=X[:,-1,CH_MIDR]
        fs_,fz_,dOI_,topdev_,takdev_,pmom_,pchg_=[ps[:,k] for k in range(7)]
        INT=np.stack([
            fs_*obi,            # INT1 funding_sign x OBI
            dOI_*tflow,         # INT2 dOI x trade_flow
            dOI_*ntf,           # INT2b dOI x net-trade-flow
            topdev_*pmom_,      # INT3 crowded-long x price_mom (cascade)
            pchg_*mpdev,        # INT4 premium_chg x microprice_dev
            fz_*rvol,           # INT5 funding_z x rvol
            takdev_*obi,        # INT6 taker_ls x obi
            fs_, dOI_, topdev_, # raw positioning levels
        ],1).astype(np.float32)
        Bs.append(snap.astype(np.float32)); Is.append(np.nan_to_num(INT)); ys.append(d["y_600"][m].astype(np.float32)); ts.append(wt)
    if not Bs: return None
    return np.nan_to_num(np.concatenate(Bs)), np.concatenate(Is), np.concatenate(ys), np.concatenate(ts)

def clean_pd(p,y,ts):
    daykey=ts//(86400*1_000_000); rs=[]
    for dk in np.unique(daykey):
        m=daykey==dk; o=np.argsort(ts[m]); tsm=ts[m][o]; pm=p[m][o]; ym=y[m][o]
        keep=[];last=-1e18
        for i in range(len(tsm)):
            if tsm[i]-last>=600_000_000: keep.append(i);last=tsm[i]
        keep=np.array(keep)
        if len(keep)>20 and pm[keep].std()>1e-9:
            r=pearsonr(pm[keep],ym[keep])[0]
            if np.isfinite(r): rs.append(r)
    return np.mean(rs) if rs else np.nan
def dense(p,y): r=pearsonr(p,y)[0]; return r if np.isfinite(r) else np.nan
def fit(Xtr,ytr,Xte):
    mu=Xtr.mean(0);sd=Xtr.std(0)+1e-8; c=int(len(ytr)*0.9); best=None
    for a in [1,10,100,1000]:
        r=Ridge(alpha=a).fit((Xtr[:c]-mu)/sd,ytr[:c]); ph=r.predict((Xtr[c:]-mu)/sd)
        s=pearsonr(ph,ytr[c:])[0] if ph.std()>1e-9 else -9
        if best is None or s>best[0]: best=(s,a)
    return Ridge(alpha=best[1]).fit((Xtr-mu)/sd,ytr).predict((Xte-mu)/sd)
def prior_months(tm,k=12):
    y,mo=int(tm[:4]),int(tm[5:7]);out=[]
    for i in range(1,k+1):
        mm=mo-i;yy=y
        while mm<=0: mm+=12;yy-=1
        out.append(f"{yy:04d}-{mm:02d}")
    return out[::-1]

print("DESIGNED funding/OI x microstructure INTERACTION Ridge gate (per-day CLEAN + DENSE)")
print(f"{'month':8s} {'base_pd':>8s} {'base+INT_pd':>11s} {'dP_pd':>7s} {'INTonly_pd':>10s} {'base_D':>7s} {'b+INT_D':>8s} {'dP_D':>6s}")
for tm in ["2025-10","2025-12","2026-02"]:
    pm=[x for x in prior_months(tm) if x>="2024-01"]
    # load train = concat prior months
    trB=[];trI=[];trY=[];trT=[]
    for x in pm:
        L=load_month(x)
        if L: trB.append(L[0]);trI.append(L[1]);trY.append(L[2]);trT.append(L[3])
    Te=load_month(tm)
    if not trB or Te is None: print(f"{tm:8s} (no data)"); continue
    Btr=np.concatenate(trB);Itr=np.concatenate(trI);ytr=np.concatenate(trY)
    Bte,Ite,yte,tte=Te
    pB=fit(Btr,ytr,Bte); pBI=fit(np.concatenate([Btr,Itr],1),ytr,np.concatenate([Bte,Ite],1)); pI=fit(Itr,ytr,Ite)
    bpd=clean_pd(pB,yte,tte); bipd=clean_pd(pBI,yte,tte); ipd=clean_pd(pI,yte,tte)
    bD=dense(pB,yte); biD=dense(pBI,yte)
    print(f"{tm:8s} {bpd:+8.4f} {bipd:+11.4f} {bipd-bpd:+7.4f} {ipd:+10.4f} {bD:+7.4f} {biD:+8.4f} {biD-bD:+6.4f}")
print("\nVERDICT: dP (base+INT minus base) >= +0.003 esp on DRIFT (2025-12, 2026-02) -> interactions carry value -> DL.")
print("DONE_FUNDINT.")
