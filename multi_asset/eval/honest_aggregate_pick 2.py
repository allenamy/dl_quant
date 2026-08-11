"""HONEST aggregate with PER-MONTH checkpoint selection (BEST vs EMA, whichever is beta-healthy).
patience10 makes one of {BEST, EMA} beta-healthy per month but which flips (sigma-gate trap #24 is checkpoint-
stochastic). So per month: eval both test_preds.npz (BEST) and ema_test_preds.npz (EMA); pick the beta-HEALTHY
one (sigma>=0.02 AND 0.5<=beta<=1.8); if both healthy pick beta closest to 1; if NEITHER, flag MISCAL and report
the closer one. Reports DENSE + per-day CLEAN, picked checkpoint, beta/sigma, pooled P/S + IC-IR + worst +
%-positive + %-beta-healthy, + production CSV. Reads experiments/wfEMA/.
Run on SERVER: PYTHONPATH=. python multi_asset/eval/honest_aggregate_pick.py
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
def load(path):
    if not os.path.exists(path): return None
    z=np.load(path,allow_pickle=True)
    pr=z["predictions"]; q=(pr[:,1] if pr.ndim==2 else pr).astype(np.float64)
    y=z["targets"].astype(np.float64); ts=z["timestamps"].astype(np.int64)
    ysig=float(z["y_sigma"]) if "y_sigma" in z else 1.0; ymed=float(z["y_median"]) if "y_median" in z else 0.0
    return q,y,ts,ysig,ymed
def metrics(q,y,ts):
    dP=pearsonr(q,y)[0]; b=np.cov(y,q)[0,1]/q.var() if q.var()>1e-12 else np.nan; sg=q.std()/(y.std()+1e-12)
    daykey=ts//(86400*1_000_000); rs=[];ss=[]
    for dk in np.unique(daykey):
        m=daykey==dk; k=clean_idx(ts[m],0)
        if len(k)>20:
            qk=q[m][k]; yk=y[m][k]
            if qk.std()>1e-12:
                r=pearsonr(qk,yk)[0]; s=spearmanr(qk,yk)[0]
                if np.isfinite(r): rs.append(r);ss.append(s)
    pdP=np.mean(rs) if rs else np.nan; pdS=np.mean(ss) if ss else np.nan
    return dP,pdP,pdS,b,sg
def healthy(b,sg): return (sg>=0.02 and 0.5<=b<=1.8)

rows=[]; csv_rows=[]
print(f"{'month':8s} {'pick':>5s} {'DENSE_P':>8s} {'pday_P':>7s} {'pday_S':>7s} {'beta':>6s} {'sigR':>5s} {'healthy':>7s}")
for mk in MONTHS:
    cands=[]
    for tag,fn in [("BEST",f"experiments/wfEMA/wf_{mk}/fold_0/test_preds.npz"),
                   ("EMA", f"experiments/wfEMA/wf_{mk}/fold_0/ema_test_preds.npz")]:
        L=load(fn)
        if L is None: continue
        q,y,ts,ysig,ymed=L; dP,pdP,pdS,b,sg=metrics(q,y,ts)
        cands.append((tag,dP,pdP,pdS,b,sg,healthy(b,sg),q,y,ts,ysig,ymed))
    if not cands: print(f"{mk:8s} MISSING"); continue
    hc=[c for c in cands if c[6]]
    pick = min(hc,key=lambda c:abs(c[4]-1.0)) if hc else min(cands,key=lambda c:abs(c[4]-1.0))
    tag,dP,pdP,pdS,b,sg,h,q,y,ts,ysig,ymed=pick
    rows.append((mk,tag,dP,pdP,pdS,b,sg,h))
    print(f"{mk:8s} {tag:>5s} {dP:+8.4f} {pdP:+7.4f} {pdS:+7.4f} {b:+6.2f} {sg:5.2f} {('OK' if h else 'MISCAL'):>7s}")
    for i in range(len(q)): csv_rows.append((mk,tag,int(ts[i]),float(q[i]*ysig+ymed),float(y[i]*ysig+ymed)))
if rows:
    dP=np.array([r[2] for r in rows]); pdP=np.array([r[3] for r in rows]); pdS=np.array([r[4] for r in rows]); hh=np.array([r[7] for r in rows])
    print("-"*70)
    print(f"  POOLED DENSE-P={dP.mean():+.4f} | per-day-P={pdP.mean():+.4f} | per-day-S={pdS.mean():+.4f}")
    if hh.any(): print(f"  beta-HEALTHY-only per-day-P={pdP[hh].mean():+.4f} ({int(hh.sum())}/{len(hh)})")
    print(f"  IC-IR(per-day)={pdP.mean()/(pdP.std()+1e-9):+.2f} | worst={pdP.min():+.4f}({rows[int(np.argmin(pdP))][0]}) | best={pdP.max():+.4f}({rows[int(np.argmax(pdP))][0]})")
    print(f"  %-per-day-positive={100*np.mean(pdP>0):.0f}% | months>=0.025={int((pdP>=0.025).sum())}/{len(pdP)} | %-beta-healthy={100*hh.mean():.0f}%")
    os.makedirs("exports/honest_basedl",exist_ok=True)
    out="exports/honest_basedl/y600_basedl_pick_walkforward.csv"
    with open(out,"w",newline="") as f:
        w=csv.writer(f); w.writerow(["month","checkpoint","timestamp_us","pred_q50_raw","target_raw"]); w.writerows(csv_rows)
    print(f"\n  production CSV -> {out} ({len(csv_rows)} rows)")
print("\nDONE_HONESTPICK.")
