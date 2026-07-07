"""Stage-2: does CAUSAL positioning-regime conditioning PREVENT the per-month sign-flip?

Root-cause finding (from CSV dig): 2026-02..04 = positioning INVERSION
(funding sign-flips -> negative; OI value collapses ~$10bn->$6bn = deleverage;
toptrader L/S 2.2 -> 0.88 = net-short). Hypothesis: the microstructure->return
directional map learned in a long-carry regime INVERTS in the short/deleveraged
regime. A model that CONDITIONS on the causal positioning state (<=t) can flip its
sign and avoid the catastrophic negative months.

PER-MONTH WALK-FORWARD over the TARGET WINDOW 2025-08..2026-05:
  for each test month m: train Ridge on prior 700d, test m (CLEAN P + beta).
  4 model variants:
    A base           : X-snapshot only                       (current-model proxy)
    B base+designed  : + 11 leak-safe positioning feats (additive; old gate)
    C regime-interact: X-snapshot * regime_sign_gate  (lets direction FLIP)
                       gate = tanh(w . [funding_sign, dOI_sign, topLS-1])  -> here we
                       use the simplest mechanistic gate: sign of a causal
                       "long-carry vs short-deleverage" score, and FIT SEPARATE maps
                       per regime bucket (interaction = regime-specific linear model).
    D base+designed+interact (full)

HARD TARGET CHECK: every month P>=0.025, NO negative/sign-flip month.
All leak-safe: snapshot <=t; metrics/funding joined <=t. Reuses designed() from the
OI gate (copied here to be standalone).
Run on SERVER: PYTHONPATH=. python multi_asset/data/regime_signfix_gate.py
"""
from __future__ import annotations
import numpy as np, glob, csv, warnings, os
from datetime import datetime, timezone
warnings.filterwarnings("ignore"); warnings.simplefilter("ignore")
from sklearn.linear_model import Ridge
from scipy.stats import pearsonr

CACHE="data/npz_v2arch"
MET="data/funding/btcusdt_metrics_5m.csv"; FUND="data/funding/btcusdt_funding.csv"
BAR_US=300*1_000_000

def parse_us(s): return int(datetime.strptime(s,"%Y-%m-%d %H:%M:%S").replace(tzinfo=timezone.utc).timestamp())*1_000_000
def f2(x):
    try: return float(x)
    except: return np.nan
def load_metrics():
    rows=[]
    with open(MET) as f:
        for r in csv.DictReader(f):
            try: rows.append((parse_us(r["create_time"]),f2(r["sum_open_interest"]),f2(r["sum_open_interest_value"]),f2(r["sum_toptrader_long_short_ratio"]),f2(r["sum_taker_long_short_vol_ratio"]),f2(r["count_long_short_ratio"])))
            except Exception: continue
    a=np.array(rows); a=a[np.argsort(a[:,0])]; return a
def load_funding():
    rows=[]
    with open(FUND) as f:
        for r in csv.DictReader(f):
            try: rows.append((int(r["fundingTime_ms"])*1000,f2(r["fundingRate"])))
            except Exception: continue
    a=np.array(rows); return a[np.argsort(a[:,0])]

M=load_metrics(); F=load_funding()
MT=M[:,0]; OI=M[:,1]; OIV=M[:,2]; TT=M[:,3]; TK=M[:,4]; RT=M[:,5]
PRICE=OIV/np.clip(OI,1e-9,None); FT=F[:,0]; FR=F[:,1]

def designed(win_ts_us):
    cut=win_ts_us-BAR_US
    im=np.searchsorted(MT,cut,side="right")-1
    iff=np.searchsorted(FT,win_ts_us,side="right")-1
    N=len(win_ts_us); out=np.zeros((N,11)); v=(im>=0)&(iff>=0); iv=im[v]; ifv=iff[v]
    K=6; iK=np.clip(iv-K,0,None)
    dOI=OI[iv]-OI[iK]; dP=PRICE[iv]-PRICE[iK]
    dOIn=dOI/(np.abs(OI[iv])+1e-9); dPn=dP/(np.abs(PRICE[iv])+1e-9)
    oiz=np.zeros(len(iv))
    for j,i in enumerate(iv):
        lo=max(0,i-71); h=OI[lo:i+1]; oiz[j]=(OI[i]-h.mean())/(h.std()+1e-9)
    fz=np.zeros(len(ifv))
    for j,i in enumerate(ifv):
        lo=max(0,i-29); h=FR[lo:i+1]; fz[j]=(FR[i]-h.mean())/(h.std()+1e-9)
    oi_accel=(OI[iv]-OI[iK])-(OI[iK]-OI[np.clip(iv-2*K,0,None)])
    out[v,0]=dOIn; out[v,1]=dPn; out[v,2]=np.sign(dOI)*np.sign(dP); out[v,3]=dOIn*dPn
    out[v,4]=np.sign(dP)*np.maximum(-np.sign(dOI),0); out[v,5]=fz*oiz; out[v,6]=TK[iv]
    out[v,7]=TK[iv]-1.0-np.sign(dOI); out[v,8]=TT[iv]-1.0; out[v,9]=RT[iv]-1.0
    out[v,10]=oi_accel/(np.abs(OI[iv])+1e-9)
    return out

def regime_score(win_ts_us):
    """Causal 'long-carry(+1) vs short-deleverage(-1)' continuous score, <=t.
    score = funding_sign + (topLS-1)_sign  (both <=t). Long-carry regime: funding>0 &
    topLS>1 -> +; deleverage/short: funding<0 & topLS<1 -> -."""
    iff=np.searchsorted(FT,win_ts_us,side="right")-1
    cut=win_ts_us-BAR_US; im=np.searchsorted(MT,cut,side="right")-1
    N=len(win_ts_us); s=np.zeros(N); v=(iff>=0)&(im>=0)
    s[v]=np.tanh(FR[iff[v]]*5e3) + np.tanh((TT[im[v]]-1.0))
    return s   # roughly in [-2,2]; sign = regime

def dd(p): return os.path.basename(p)[:-4]
def load_days(days):
    Xs=[];Ds=[];Rs=[];ys=[];ts=[]
    for f in days:
        d=np.load(f,allow_pickle=True); m=d["y_mask_600"].astype(bool)
        if m.sum()==0: continue
        X=d["X"][m]; snap=np.concatenate([X[:,-1,:],X[:,-60:,:].mean(1)],1)
        wt=d["timestamps"][m].astype(np.int64)
        Xs.append(snap.astype(np.float32)); Ds.append(designed(wt).astype(np.float32))
        Rs.append(regime_score(wt).astype(np.float32)); ys.append(d["y_600"][m].astype(np.float32)); ts.append(wt)
    if not Xs: return None
    return (np.nan_to_num(np.concatenate(Xs)),np.nan_to_num(np.concatenate(Ds)),
            np.nan_to_num(np.concatenate(Rs)),np.concatenate(ys),np.concatenate(ts))

def files_for(mons):
    fs=sorted(glob.glob(f"{CACHE}/*.npz")); return [f for f in fs if dd(f)[:7] in mons]
def prior_months(testmon,k):
    y,mo=int(testmon[:4]),int(testmon[5:7]); out=[]
    for i in range(1,k+1):
        mm=mo-i; yy=y
        while mm<=0: mm+=12; yy-=1
        out.append(f"{yy:04d}-{mm:02d}")
    return out[::-1]

def clean_metrics(p,y,ts):
    o=np.argsort(ts); ts=ts[o]; p=p[o]; y=y[o]; Ps=[]; bs=[]; sg=[]
    for off in range(4):
        keep=[]; last=-1e18
        for i in range(off,len(ts)):
            if ts[i]-last>=600*1_000_000: keep.append(i); last=ts[i]
        keep=np.array(keep)
        if len(keep)>30:
            pp=p[keep]; yy=y[keep]; r=pearsonr(pp,yy)[0]
            if np.isfinite(r):
                Ps.append(r)
                if pp.std()>1e-9: bs.append(np.cov(yy,pp)[0,1]/pp.var()); sg.append(pp.std()/(yy.std()+1e-12))
    return (float(np.mean(Ps)) if Ps else np.nan, float(np.mean(bs)) if bs else np.nan, float(np.mean(sg)) if sg else np.nan)

def ridge_pred(Xtr,ytr,Xte):
    mu=Xtr.mean(0); sd=Xtr.std(0)+1e-8
    # alpha chosen by a small in-train holdout (last 10%) to avoid test peeking
    n=len(ytr); c=int(n*0.9); best=None
    for a in [1,10,100,1000]:
        r=Ridge(alpha=a).fit((Xtr[:c]-mu)/sd,ytr[:c])
        ph=r.predict((Xtr[c:]-mu)/sd); P=pearsonr(ph,ytr[c:])[0] if ph.std()>1e-9 else -9
        if best is None or P>best[0]: best=(P,a)
    r=Ridge(alpha=best[1]).fit((Xtr-mu)/sd,ytr)
    return r.predict((Xte-mu)/sd)

def regime_interact_pred(Xtr,Rtr,ytr,Xte,Rte):
    """Fit SEPARATE Ridge per regime bucket (sign of regime score). Direction can flip."""
    out=np.zeros(len(Xte))
    for sgn in (+1,-1):
        trm = (np.sign(Rtr)==sgn) if sgn>0 else (np.sign(Rtr)<=0)
        tem = (np.sign(Rte)==sgn) if sgn>0 else (np.sign(Rte)<=0)
        if trm.sum()<800 or tem.sum()==0:
            # fallback: global map for this bucket
            if tem.sum()>0: out[tem]=ridge_pred(Xtr,ytr,Xte[tem])
            continue
        out[tem]=ridge_pred(Xtr[trm],ytr[trm],Xte[tem])
    return out

TARGET=["2025-08","2025-09","2025-10","2025-11","2025-12","2026-01","2026-02","2026-03","2026-04","2026-05"]
print("metrics rows:",len(MT)," funding rows:",len(FT))
print("="*94)
print("PER-MONTH WALK-FORWARD (train prior ~700d -> test month).  CLEAN P [beta]")
print("="*94)
print(f"{'month':8s} | {'A base':>14s} | {'B +design':>14s} | {'C reg-interact':>16s} | {'D full':>14s}")
agg={k:[] for k in "ABCD"}
for tm in TARGET:
    teL=files_for([tm])
    if not teL: print(f"{tm:8s} | (no test data)"); continue
    Te=load_days(teL)
    if Te is None: print(f"{tm:8s} | (empty)"); continue
    Xte,Dte,Rte,yte,tte=Te
    # train window: prior ~10 months available in cache (cache starts ~2024)
    pm=[x for x in prior_months(tm,12)]
    trL=files_for(pm)
    Tr=load_days(trL)
    if Tr is None: print(f"{tm:8s} | (no train)"); continue
    Xtr,Dtr,Rtr,ytr,ttr=Tr
    # A base
    pA=ridge_pred(Xtr,ytr,Xte); PA=clean_metrics(pA,yte,tte)
    # B base+designed
    XBtr=np.concatenate([Xtr,Dtr],1); XBte=np.concatenate([Xte,Dte],1)
    pB=ridge_pred(XBtr,ytr,XBte); PB=clean_metrics(pB,yte,tte)
    # C regime-interact (base, separate map per regime sign)
    pC=regime_interact_pred(Xtr,Rtr,ytr,Xte,Rte); PC=clean_metrics(pC,yte,tte)
    # D full: base+designed, regime-interact
    pD=regime_interact_pred(XBtr,Rtr,ytr,XBte,Rte); PD=clean_metrics(pD,yte,tte)
    for k,P in zip("ABCD",[PA,PB,PC,PD]): agg[k].append(P[0])
    def cell(P): return f"{P[0]:+.4f}[{P[1]:+.1f}]"
    print(f"{tm:8s} | {cell(PA):>14s} | {cell(PB):>14s} | {cell(PC):>16s} | {cell(PD):>14s}")
print("-"*94)
def summ(k):
    a=np.array([x for x in agg[k] if np.isfinite(x)])
    return f"mean={a.mean():+.4f} min={a.min():+.4f} %>=.025={100*np.mean(a>=0.025):.0f}% neg={int(np.sum(a<0))}"
for k in "ABCD": print(f"  {k}: {summ(k)}")
print("\nDONE_SIGNFIX.")
