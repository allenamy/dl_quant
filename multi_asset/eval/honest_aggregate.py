"""HONEST aggregate of the base-DL walk-forward (2025-08..2026-05) -- corrected caliber.
The cross-day-POOLED 4-offset CLEAN inflates (clean>dense artifact). This reports the HONEST calibers:
  - DENSE: all test windows, Pearson(q50, target)   (within-month, no cross-day pooling)
  - PER-DAY CLEAN: per-day single-offset non-overlap (>=600s) Pearson, averaged across days  (the honest
    tradeable caliber; removes cross-day pooling)
  - beta (y on q50), sigma_ratio  -- flag mis-calibrated months (beta far from 1)
Uses BEST checkpoint (test_preds.npz). Aggregate: pooled DENSE/per-day P+S, IC-IR (monthly mean/std), worst,
%-positive. Also exports a production CSV (raw y = q*y_sigma + y_median).
Run on SERVER: PYTHONPATH=. python multi_asset/eval/honest_aggregate.py
"""
from __future__ import annotations
import numpy as np, os, csv
from scipy.stats import pearsonr, spearmanr

MONTHS=["2025_08","2025_09","2025_10","2025_11","2025_12","2026_01","2026_02","2026_03","2026_04","2026_05"]
HZ=600*1_000_000

def clean_idx(ts,off=0):
    o=np.argsort(ts);keep=[];last=-1e18
    for i in range(off,len(o)):
        if ts[o[i]]-last>=HZ: keep.append(o[i]);last=ts[o[i]]
    return np.array(keep)

def load(mk):
    p=f"experiments/walkforward/wf_{mk}/fold_0/test_preds.npz"
    if not os.path.exists(p): return None
    z=np.load(p,allow_pickle=True)
    pr=z["predictions"]; q=(pr[:,1] if pr.ndim==2 else pr).astype(np.float64)
    y=z["targets"].astype(np.float64); ts=z["timestamps"].astype(np.int64)
    ysig=float(z["y_sigma"]) if "y_sigma" in z else 1.0; ymed=float(z["y_median"]) if "y_median" in z else 0.0
    return q,y,ts,ysig,ymed

def dense(q,y):
    P=pearsonr(q,y)[0]; S=spearmanr(q,y)[0]
    b=np.cov(y,q)[0,1]/q.var() if q.var()>1e-12 else np.nan
    sg=q.std()/(y.std()+1e-12)
    return P,S,b,sg
def perday(q,y,ts):
    daykey=ts//(86400*1_000_000); rs=[]; ss=[]
    for dk in np.unique(daykey):
        m=daykey==dk; k=clean_idx(ts[m],0)
        if len(k)>20:
            qk=q[m][k]; yk=y[m][k]
            if qk.std()>1e-12:
                r=pearsonr(qk,yk)[0]; s=spearmanr(qk,yk)[0]
                if np.isfinite(r): rs.append(r); ss.append(s)
    return (np.mean(rs) if rs else np.nan), (np.mean(ss) if ss else np.nan), len(rs)

rows=[]; csv_rows=[]
print(f"{'month':8s} {'DENSE_P':>8s} {'perday_P':>9s} {'perday_S':>9s} {'beta':>6s} {'sigR':>5s} {'flag':>6s}")
for mk in MONTHS:
    L=load(mk)
    if L is None: print(f"{mk:8s} MISSING"); continue
    q,y,ts,ysig,ymed=L
    dP,dS,b,sg=dense(q,y); pdP,pdS,nd=perday(q,y,ts)
    flag="" if (0.5<=b<=1.8 and sg>=0.02) else "MISCAL"
    rows.append((mk,dP,pdP,pdS,b,sg))
    print(f"{mk:8s} {dP:+8.4f} {pdP:+9.4f} {pdS:+9.4f} {b:+6.2f} {sg:5.2f} {flag:>6s}")
    for i in range(len(q)):
        csv_rows.append((mk,int(ts[i]),float(q[i]*ysig+ymed),float(y[i]*ysig+ymed)))
if rows:
    dP=np.array([r[1] for r in rows]); pdP=np.array([r[2] for r in rows]); pdS=np.array([r[3] for r in rows])
    print("-"*60)
    print(f"  POOLED DENSE-P mean   = {dP.mean():+.4f}")
    print(f"  POOLED per-day-P mean = {pdP.mean():+.4f} | per-day-S = {pdS.mean():+.4f}  (HONEST tradeable caliber)")
    print(f"  IC-IR (per-day-P mean/std) = {pdP.mean()/(pdP.std()+1e-9):+.2f}")
    print(f"  worst month per-day-P = {pdP.min():+.4f} ({rows[int(np.argmin(pdP))][0]})")
    print(f"  best  month per-day-P = {pdP.max():+.4f} ({rows[int(np.argmax(pdP))][0]})")
    print(f"  %-months per-day-positive = {100*np.mean(pdP>0):.0f}% ({int((pdP>0).sum())}/{len(pdP)})")
    print(f"  months >= 0.025 (per-day) = {int((pdP>=0.025).sum())}/{len(pdP)}")
    # production CSV
    os.makedirs("exports/honest_basedl", exist_ok=True)
    out="exports/honest_basedl/y600_basedl_walkforward.csv"
    with open(out,"w",newline="") as f:
        w=csv.writer(f); w.writerow(["month","timestamp_us","pred_q50_raw","target_raw"])
        w.writerows(csv_rows)
    print(f"\n  production CSV -> {out} ({len(csv_rows)} rows)")
print("\nDONE_HONESTAGG.")
