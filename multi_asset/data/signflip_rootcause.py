"""Sign-flip / per-month root-cause dig (FRESH, data-driven; no past-conclusion priors).

Target window 2025-08..2026-05. HARD QUESTION: WHY do some months sign-flip
(2024-08 beta -1.19; drift 2025-12, 2026-02)? Is the optimal LINEAR map itself
inverting (genuine return-mechanism inversion) or is it a model/staleness artifact?

R1  PER-MONTH SELF-FIT sign: fit Ridge IN-month (5-fold time-split), report in-month
    CLEAN P + beta sign. If a month's OWN best linear map is sign-stable & P>0, the
    signal exists there; a sign-flip in walk-forward is then a TRANSFER/staleness
    problem (fixable), NOT "no signal".

R2  TRANSFER matrix: train on month A's map, test on month B. Does the learned
    direction invert across the regime boundary? Pinpoints WHICH months break transfer.

R3  POSITIONING-REGIME state per month (causal, <=t): funding sign, OI trend,
    top/retail L/S, taker imbalance. Correlate regime-inversion with P/beta-inversion.

R4  RECENCY vs FULL vs RECENCY-WEIGHTED -> each test month (don't assume recency hurts).
    full(700d) vs recent(90d) vs recent(180d), CLEAN P on the test month.

All leak-safe: snapshot = last-step + 60s-mean of X (<=t). Funding/OI joined <=t.
Run on SERVER (needs npz_v2arch): PYTHONPATH=. python multi_asset/data/signflip_rootcause.py
"""
from __future__ import annotations
import numpy as np, glob, csv, warnings, os
from datetime import datetime, timezone
warnings.filterwarnings("ignore"); warnings.simplefilter("ignore")
from sklearn.linear_model import Ridge
from scipy.stats import pearsonr, spearmanr

CACHE = "data/npz_v2arch"
MET = "data/funding/btcusdt_metrics_5m.csv"
FUND = "data/funding/btcusdt_funding.csv"

def dd(p): return os.path.basename(p)[:-4]
def mon(p): return dd(p)[:7]

def load(mons):
    fs = sorted(glob.glob(f"{CACHE}/*.npz"))
    days = [f for f in fs if mon(f) in mons]
    Xs=[]; ys=[]; ts=[]
    for f in days:
        d = np.load(f, allow_pickle=True)
        m = d["y_mask_600"].astype(bool)
        if m.sum()==0: continue
        X = d["X"][m]
        snap = np.concatenate([X[:,-1,:], X[:,-60:,:].mean(1)], 1)
        Xs.append(snap.astype(np.float32))
        ys.append(d["y_600"][m].astype(np.float32))
        ts.append(d["timestamps"][m].astype(np.int64))
    if not Xs: return None
    return (np.nan_to_num(np.concatenate(Xs)), np.concatenate(ys), np.concatenate(ts))

def clean_p(p,y,ts):
    o=np.argsort(ts); ts=ts[o]; p=p[o]; y=y[o]; Ps=[]
    for off in range(4):
        keep=[]; last=-1e18
        for i in range(off,len(ts)):
            if ts[i]-last>=600*1_000_000: keep.append(i); last=ts[i]
        keep=np.array(keep)
        if len(keep)>30:
            r=pearsonr(p[keep],y[keep])[0]
            if np.isfinite(r): Ps.append(r)
    return float(np.mean(Ps)) if Ps else np.nan

def fit_best(Xtr,ytr):
    mu=Xtr.mean(0); sd=Xtr.std(0)+1e-8
    models=[]
    for a in [1,10,100,1000]:
        r=Ridge(alpha=a).fit((Xtr-mu)/sd,ytr); models.append((a,r))
    return mu,sd,models

def pred(mu,sd,r,X): return r.predict((X-mu)/sd)

TARGET=["2025-08","2025-09","2025-10","2025-11","2025-12","2026-01","2026-02","2026-03","2026-04","2026-05"]

# ---------- R1: per-month self-fit (does the signal exist in-month, sign-stable?) ----------
print("="*78)
print("R1  PER-MONTH SELF-FIT (in-month 5-split time CV; signal-existence & sign)")
print("="*78)
print(f"{'mon':8s} {'n':>7s} {'selfP':>8s} {'beta':>7s} {'sigP/y':>7s}  verdict")
permonth={}
for m in TARGET:
    L=load([m])
    if L is None: print(f"{m:8s}  (no data)"); continue
    X,y,ts=L; permonth[m]=L
    o=np.argsort(ts); X,y,ts=X[o],y[o],ts[o]
    n=len(y); fold=n//5; ps=[]; betas=[]; sig=[]
    for k in range(5):
        a=k*fold; b=(k+1)*fold if k<4 else n
        te=np.arange(a,b); tr=np.concatenate([np.arange(0,a),np.arange(b,n)])
        if len(tr)<500 or len(te)<200: continue
        mu,sd,models=fit_best(X[tr],y[tr])
        best=None
        for al,r in models:
            pp=pred(mu,sd,r,X[te]); P=clean_p(pp,y[te],ts[te])
            if best is None or (np.isfinite(P) and P>best[0]): best=(P,pp)
        if best is None or not np.isfinite(best[0]): continue
        pp=best[1]; ps.append(best[0])
        # beta y~p, sigma ratio
        if pp.std()>1e-9:
            betas.append(np.cov(y[te],pp)[0,1]/pp.var()); sig.append(pp.std()/ (y[te].std()+1e-12))
    selfP=np.nanmean(ps) if ps else np.nan
    beta=np.nanmean(betas) if betas else np.nan
    sg=np.nanmean(sig) if sig else np.nan
    v = "SIGNAL+sign-ok" if (selfP>0.02 and beta>0) else ("INVERTED" if beta<0 else "weak/none")
    print(f"{m:8s} {n:7d} {selfP:+8.4f} {beta:+7.2f} {sg:7.3f}  {v}")

# ---------- R2: transfer matrix (which regime boundary inverts the direction?) ----------
print("\n"+"="*78)
print("R2  TRANSFER MATRIX  train row-month -> test col-month  (CLEAN P; neg=inversion)")
print("="*78)
mons=[m for m in TARGET if m in permonth]
# fit one map per month (full month), then cross-apply
maps={}
for m in mons:
    X,y,ts=permonth[m]; mu,sd,models=fit_best(X,y)
    # pick alpha by in-month self clean P
    best=None
    for al,r in models:
        pp=pred(mu,sd,r,X); P=clean_p(pp,y,ts)
        if best is None or (np.isfinite(P) and P>best[0]): best=(P,al,r)
    maps[m]=(mu,sd,best[2])
hdr="train\\test "+" ".join(f"{c[5:]:>6s}" for c in mons)
print(hdr)
for tr in mons:
    mu,sd,r=maps[tr]; row=[]
    for te in mons:
        Xe,ye,tse=permonth[te]; pp=pred(mu,sd,r,Xe); P=clean_p(pp,ye,tse)
        row.append(f"{P:+6.3f}" if np.isfinite(P) else "  nan ")
    print(f"{tr:>9s} "+" ".join(row))

# ---------- R3: positioning regime per month (causal state) ----------
def f2(x):
    try: return float(x)
    except: return np.nan
def load_metrics_month():
    rows={}
    with open(MET) as f:
        for r in csv.DictReader(f):
            try: t=datetime.strptime(r["create_time"],"%Y-%m-%d %H:%M:%S")
            except: continue
            rows.setdefault(t.strftime("%Y-%m"),[]).append((f2(r["sum_open_interest"]),f2(r["sum_open_interest_value"]),f2(r["count_long_short_ratio"]),f2(r["sum_toptrader_long_short_ratio"]),f2(r["sum_taker_long_short_vol_ratio"])))
    return rows
def load_fund_month():
    rows={}
    with open(FUND) as f:
        for r in csv.DictReader(f):
            try: t=datetime.strptime(r["datetime_utc"],"%Y-%m-%d %H:%M:%S")
            except: continue
            rows.setdefault(t.strftime("%Y-%m"),[]).append(f2(r["fundingRate"]))
    return rows
print("\n"+"="*78)
print("R3  POSITIONING REGIME per month (causal aggregates)")
print("="*78)
met=load_metrics_month(); fund=load_fund_month()
print(f"{'mon':8s} {'OIval$bn':>9s} {'dOI%':>7s} {'topLS':>7s} {'retLS':>7s} {'takerLS':>8s} {'f8h_bps':>8s}")
for m in TARGET:
    if m not in met: continue
    a=np.array(met[m]); oival=a[:,1]; rls=a[:,2]; tls=a[:,3]; kls=a[:,4]; oi=a[:,0]
    doi=(oi[-1]-oi[0])/(oi[0]+1e-9)*100
    fr=np.array(fund.get(m,[np.nan]))
    print(f"{m:8s} {np.nanmean(oival)/1e9:9.2f} {doi:7.2f} {np.nanmean(tls):7.3f} {np.nanmean(rls):7.3f} {np.nanmean(kls):8.3f} {np.nanmean(fr)*1e4:8.3f}")

# ---------- R4: recency vs full vs recency-weighted -> each test month ----------
print("\n"+"="*78)
print("R4  RECENCY  train-window -> test-month CLEAN P  (full vs 90d vs 180d)")
print("="*78)
import datetime as _dt
def prior_months(testmon, k):
    y,mo=int(testmon[:4]),int(testmon[5:7]); out=[]
    for i in range(1,k+1):
        mm=mo-i; yy=y
        while mm<=0: mm+=12; yy-=1
        out.append(f"{yy:04d}-{mm:02d}")
    return out[::-1]
ALLPRIOR=["2024-10","2024-11","2024-12","2025-01","2025-02","2025-03","2025-04","2025-05","2025-06","2025-07"]+TARGET
print(f"{'testmon':8s} {'full(~10mo)':>12s} {'recent3mo':>10s} {'recent6mo':>10s}  best")
for tm in ["2025-12","2026-02","2026-03","2026-04"]:
    if tm not in permonth: continue
    Xe,ye,tse=permonth[tm]
    res={}
    for tag,k in [("full",10),("r3",3),("r6",6)]:
        pm=[x for x in prior_months(tm,k) if x in ALLPRIOR]
        L=load(pm)
        if L is None: res[tag]=np.nan; continue
        Xt,yt,_=L; mu,sd,models=fit_best(Xt,yt)
        best=-9
        for al,r in models:
            pp=pred(mu,sd,r,Xe); P=clean_p(pp,ye,tse)
            if np.isfinite(P): best=max(best,P)
        res[tag]=best if best>-9 else np.nan
    bt=max(res,key=lambda k:(res[k] if np.isfinite(res[k]) else -9))
    print(f"{tm:8s} {res['full']:+12.4f} {res['r3']:+10.4f} {res['r6']:+10.4f}  {bt}")
print("\nDONE.")
