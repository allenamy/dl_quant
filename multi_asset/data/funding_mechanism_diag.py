"""WHY does funding/OI not help? Specific-mechanism diagnostic (not 'exhausted').
5 points, all leak-safe (<=t). CPU. Reuses the cache for book-feat corr (#1) + funding CSVs for horizon (#3).

#1 ORTHOGONALITY: corr(funding/OI designed feats, book/microstructure snapshot feats) on 2025-12 (drift).
   high |corr| -> redundant; low -> genuinely orthogonal.
#2 UNIVARIATE: funding/OI feats ALONE -> y_600 (walk-forward Ridge, per-day CLEAN). ~0 -> no power at 10min.
#3 *HORIZON*: build forward returns at 600s / 3600s(1h) / 14400s(4h) from the 5m metrics implied-price
   (PRICE=OI_value/OI, the perp positioning price) AND premium-index level; test funding/OI feats -> each
   horizon (in-sample corr + Ridge). Does predictive power APPEAR at longer horizons?
#4 NON-LINEAR: funding/OI feats -> y_600 via shallow GBM (sklearn) vs Ridge -> does non-linear beat linear?
#5 SANITY: funding/OI varies, aligned, shows drift-month regime structure (print stats per month).
Run on SERVER: PYTHONPATH=. python multi_asset/data/funding_mechanism_diag.py
"""
from __future__ import annotations
import numpy as np, glob, os, csv, warnings
from datetime import datetime, timezone
warnings.filterwarnings("ignore"); warnings.simplefilter("ignore")
from sklearn.linear_model import Ridge
from sklearn.ensemble import HistGradientBoostingRegressor
from scipy.stats import pearsonr, spearmanr
MET="data/funding/btcusdt_metrics_5m.csv"; FUND="data/funding/btcusdt_funding.csv"; PREM="data/funding/btcusdt_premium_index_5m.csv"
def parse_us(s): return int(datetime.strptime(s,"%Y-%m-%d %H:%M:%S").replace(tzinfo=timezone.utc).timestamp())*1_000_000
def f2(x):
    try: return float(x)
    except: return np.nan
def load_met():
    rows=[]
    with open(MET) as f:
        for r in csv.DictReader(f):
            try: rows.append((parse_us(r["create_time"]),f2(r["sum_open_interest"]),f2(r["sum_open_interest_value"]),f2(r["sum_toptrader_long_short_ratio"]),f2(r["sum_taker_long_short_vol_ratio"]),f2(r["count_long_short_ratio"])))
            except Exception: continue
    a=np.array(rows); return a[np.argsort(a[:,0])]
def load_fund():
    rows=[]
    with open(FUND) as f:
        for r in csv.DictReader(f):
            try: rows.append((int(r["fundingTime_ms"])*1000,f2(r["fundingRate"])))
            except Exception: continue
    a=np.array(rows); return a[np.argsort(a[:,0])]
M=load_met(); F=load_fund()
MT=M[:,0]; OI=M[:,1]; OIV=M[:,2]; TT=M[:,3]; TK=M[:,4]; RT=M[:,5]; PRICE=OIV/np.clip(OI,1e-9,None); FT=F[:,0]; FR=F[:,1]
def mon_us(mon):
    y,mo=int(mon[:4]),int(mon[5:7]); a=parse_us(f"{mon}-01 00:00:00")
    mm=mo+1;yy=y
    if mm>12: mm=1;yy+=1
    b=parse_us(f"{yy:04d}-{mm:02d}-01 00:00:00"); return a,b

# ---------- #3 + #5: funding/OI -> forward returns at multiple horizons (5m grid, native to the slow data) ----------
print("="*78); print("#3 HORIZON: funding/OI features -> forward return at 600s / 3600s(1h) / 14400s(4h)")
print("   (forward return from 5m metrics implied-price PRICE=OI_value/OI; leak-safe: feat<=t, ret strictly fwd)")
print("="*78)
def fund_feats_at(idx):
    """designed funding/OI feats at metrics-bar indices idx (all <=t by construction)."""
    K=6; iK=np.clip(idx-K,0,None)
    dOI=(OI[idx]-OI[iK])/(np.abs(OI[idx])+1e-9); dP=(PRICE[idx]-PRICE[iK])/(np.abs(PRICE[idx])+1e-9)
    oiz=np.array([ (OI[i]-OI[max(0,i-71):i+1].mean())/(OI[max(0,i-71):i+1].std()+1e-9) for i in idx])
    # funding at <=t
    fr=np.array([ FR[max(0,np.searchsorted(FT,MT[i],side="right")-1)] for i in idx])
    feats=np.stack([dOI, oiz, np.sign(fr), TT[idx]-1.0, TK[idx]-1.0, RT[idx]-1.0, dOI*np.sign(fr), (TT[idx]-1.0)*dP],1)
    return np.nan_to_num(feats)
HOR_BARS={"600s(10m)":2,"3600s(1h)":12,"14400s(4h)":48}  # 5m bars
for mon in ["2025-10","2025-12","2026-02"]:
    a,b=mon_us(mon); sel=np.where((MT>=a)&(MT<b))[0]
    if len(sel)<200: print(f"{mon}: too few bars"); continue
    sel=sel[(sel>=72)&(sel<len(MT)-48)]  # room for history + 4h forward
    X=fund_feats_at(sel)
    print(f"\n{mon} (n={len(sel)} 5m-bars):")
    for hn,hb in HOR_BARS.items():
        fwd=(PRICE[sel+hb]-PRICE[sel])/(PRICE[sel]+1e-9)
        # univariate best |corr| among feats + Ridge CV (simple 5-fold interleaved)
        unis=[abs(pearsonr(X[:,k],fwd)[0]) for k in range(X.shape[1])]
        # Ridge in-month interleaved 5-fold
        rng=np.random.default_rng(0); fid=rng.integers(0,5,len(sel)); ps=[]
        for k in range(5):
            te=fid==k; tr=~te
            if tr.sum()<50 or te.sum()<20: continue
            mu=X[tr].mean(0);sd=X[tr].std(0)+1e-8
            p=Ridge(alpha=10).fit((X[tr]-mu)/sd,fwd[tr]).predict((X[te]-mu)/sd)
            r=pearsonr(p,fwd[te])[0]
            if np.isfinite(r): ps.append(r)
        print(f"   {hn:12s} fwd_ret_std={fwd.std()*1e4:6.1f}bps | best-univ|corr|={max(unis):.4f} | Ridge-CV corr={np.mean(ps) if ps else float('nan'):+.4f}")

# ---------- #5 SANITY: funding/OI regime structure per month ----------
print("\n"+"="*78); print("#5 SANITY: funding/OI varies + drift-month regime structure")
print("="*78)
for mon in ["2025-10","2025-12","2026-02"]:
    a,b=mon_us(mon); sel=np.where((MT>=a)&(MT<b))[0]
    if len(sel)<10: continue
    fr=np.array([FR[max(0,np.searchsorted(FT,MT[i],side='right')-1)] for i in sel])
    print(f"  {mon}: funding_bps mean={np.nanmean(fr)*1e4:+.2f} std={np.nanstd(fr)*1e4:.2f} | topLS mean={np.nanmean(TT[sel]):.2f} | OIval$bn={np.nanmean(OIV[sel])/1e9:.2f} | dOI%(mo)={(OI[sel[-1]]-OI[sel[0]])/OI[sel[0]]*100:+.1f}")
print("\nINTERPRETATION: if Ridge-CV corr RISES with horizon (600s~0 -> 1h/4h>>0) => WRONG-HORIZON (funding/OI")
print("predicts slow moves, not 10min). If ~0 at ALL horizons => no directional power. (#1/#2/#4 in companion gate.)")
print("DONE_FUNDMECH.")
