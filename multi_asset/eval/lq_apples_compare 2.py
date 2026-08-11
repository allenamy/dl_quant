"""APPLES-TO-APPLES 2b effect: SAME-CHECKPOINT (EMA-vs-EMA) and SAME-CALIBER per-month delta-P(lambda0.5 - lambda0.1).
Answers: does 2b (lambda_quantile 0.5) genuinely beat lambda0.1, or do hurt months offset helped months (net wash)?
Reads lambda0.1 trajectory from experiments/wfEMA/ and lambda0.5 from experiments/wfEMA_lq05/.
Per month: DENSE P + per-day-CLEAN P + sigma + beta, for BOTH checkpoints (EMA primary; BEST shown too).
Then pooled mean delta-P (EMA-vs-EMA, the clean 2b effect) + sign tally (helped vs hurt).
Run on SERVER: PYTHONPATH=. python multi_asset/eval/lq_apples_compare.py
"""
from __future__ import annotations
import numpy as np, os
from scipy.stats import pearsonr
MONTHS=["2025_08","2025_09","2025_10","2025_11","2025_12","2026_01","2026_02","2026_03","2026_04","2026_05"]
HZ=600*1_000_000
def clean_idx(ts):
    o=np.argsort(ts); keep=[]; last=-1e18
    for i in range(len(o)):
        if ts[o[i]]-last>=HZ: keep.append(o[i]); last=ts[o[i]]
    return np.array(keep)
def load(path):
    if not os.path.exists(path): return None
    z=np.load(path,allow_pickle=True); pr=z["predictions"]
    q=(pr[:,1] if pr.ndim==2 else pr).astype(np.float64)
    return q, z["targets"].astype(np.float64), z["timestamps"].astype(np.int64)
def metrics(L):
    q,y,ts=L
    dP=pearsonr(q,y)[0]; b=np.cov(y,q)[0,1]/q.var() if q.var()>1e-12 else np.nan; sg=q.std()/(y.std()+1e-12)
    daykey=ts//(86400*1_000_000); rs=[]
    for dk in np.unique(daykey):
        m=daykey==dk; k=clean_idx(ts[m])
        if len(k)>20:
            qk=q[m][k]; yk=y[m][k]
            if qk.std()>1e-12:
                r=pearsonr(qk,yk)[0]
                if np.isfinite(r): rs.append(r)
    return dP,(np.mean(rs) if rs else np.nan),b,sg
def get(traj,mk,ck):
    fn=f"experiments/{traj}/wf_{mk}/fold_0/{'ema_' if ck=='EMA' else ''}test_preds.npz"
    L=load(fn); return metrics(L) if L else None

print("=== SAME-CHECKPOINT (EMA-vs-EMA) 2b effect: delta-P(lambda0.5 - lambda0.1), DENSE + per-day-CLEAN ===")
print(f"{'month':8s} | {'l01_DENSE':>9s} {'l05_DENSE':>9s} {'dD':>7s} | {'l01_CLEAN':>9s} {'l05_CLEAN':>9s} {'dC':>7s} | {'l01_b':>6s} {'l05_b':>6s} {'l05_sg':>6s}")
dDs=[];dCs=[];rows=0
for mk in MONTHS:
    a=get("wfEMA",mk,"EMA"); b=get("wfEMA_lq05",mk,"EMA")
    if a is None or b is None:
        miss="l01" if a is None else ""; miss+=" l05" if b is None else ""
        print(f"{mk:8s} | (missing: {miss.strip()})"); continue
    dD=b[0]-a[0]; dC=(b[1]-a[1]) if (np.isfinite(a[1]) and np.isfinite(b[1])) else np.nan
    dDs.append(dD);
    if np.isfinite(dC): dCs.append(dC)
    rows+=1
    print(f"{mk:8s} | {a[0]:+9.4f} {b[0]:+9.4f} {dD:+7.4f} | {a[1]:+9.4f} {b[1]:+9.4f} {dC:+7.4f} | {a[2]:+6.2f} {b[2]:+6.2f} {b[3]:6.3f}")
dDs=np.array(dDs); dCs=np.array(dCs)
print(f"\n=== POOLED NET 2b EFFECT (EMA-vs-EMA, {rows} overlapping months) ===")
if len(dDs):
    print(f"  DENSE : mean dP={dDs.mean():+.4f}  | helped(>0)={int((dDs>0).sum())}  hurt(<0)={int((dDs<0).sum())}  | per-month: {np.round(dDs,3).tolist()}")
if len(dCs):
    print(f"  CLEAN : mean dP={dCs.mean():+.4f}  | helped(>0)={int((dCs>0).sum())}  hurt(<0)={int((dCs<0).sum())}  | per-month: {np.round(dCs,3).tolist()}")
# also: BEST-vs-BEST for context
print("\n=== context: BEST-vs-BEST DENSE delta-P ===")
bDs=[]
for mk in MONTHS:
    a=get("wfEMA",mk,"BEST"); b=get("wfEMA_lq05",mk,"BEST")
    if a is None or b is None: continue
    bDs.append(b[0]-a[0])
if bDs: print(f"  BEST DENSE mean dP={np.mean(bDs):+.4f} helped={int((np.array(bDs)>0).sum())} hurt={int((np.array(bDs)<0).sum())} | {np.round(bDs,3).tolist()}")
print("\nVERDICT: 2b is a REAL lever only if pooled EMA-vs-EMA dP clearly >0 AND helped >> hurt. Else month-dependent wash.")
print("DONE_APPLES.")
