"""HONEST aggregate — CAUSAL checkpoint selection (no test-peek). Reports 4 selection rules:
 1. FIXED always-EMA  -> NO-PEEK HEADLINE (smoother/robust, fixed rule across all months)
 2. FIXED always-BEST -> no-peek alternative
 3. VAL-CAUSAL pick   -> per month pick the checkpoint whose VALIDATION calibration is healthier
    (val_sigma_ratio from metrics.json, <=t; tie-break val_composite). Legitimate causal selection.
 4. TEST-beta ORACLE  -> per month pick by TEST beta-health = ORACLE UPPER BOUND (test-peeking, NOT tradeable)
The val checkpoint metrics live in metrics.json: top-level = BEST (sigma_gate), .ema = EMA. Reads experiments/wfEMA/.
Per-month: DENSE + per-day CLEAN, beta/sigma. Pooled P/S + IC-IR + worst + %-positive + %-beta-healthy per rule.
Production CSV from the NO-PEEK headline (always-EMA).
Run on SERVER: PYTHONPATH=. python multi_asset/eval/honest_aggregate_causal.py
"""
from __future__ import annotations
import numpy as np, os, csv, json
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
    return dP,(np.mean(rs) if rs else np.nan),(np.mean(ss) if ss else np.nan),b,sg
def healthy(b,sg): return (sg>=0.02 and 0.5<=b<=1.8)

# gather per-month both checkpoints + their VAL metrics (causal)
data={}
for mk in MONTHS:
    base=f"experiments/wfEMA_lq05/wf_{mk}/fold_0"
    mj={}
    if os.path.exists(f"{base}/metrics.json"):
        try: mj=json.load(open(f"{base}/metrics.json"))
        except: mj={}
    val_best_sig=mj.get("best_ckpt_sigma_ratio", mj.get("val_sigma_ratio",np.nan))
    val_ema_sig=(mj.get("ema") or {}).get("val_sigma_ratio",np.nan)
    val_best_comp=mj.get("val_composite",np.nan); val_ema_comp=(mj.get("ema") or {}).get("val_composite",np.nan)
    cks={}
    for tag,fn in [("BEST",f"{base}/test_preds.npz"),("EMA",f"{base}/ema_test_preds.npz")]:
        L=load(fn)
        if L: cks[tag]=(L, metrics(*L[:3]))
    if cks: data[mk]=(cks, val_best_sig, val_ema_sig, val_best_comp, val_ema_comp)

def pooled(sel):  # sel: mk -> tag
    pds=[]; dPs=[]; pss=[]; hh=[]
    for mk,tag in sel.items():
        if mk not in data or tag not in data[mk][0]: continue
        (_, (dP,pdP,pdS,b,sg))=data[mk][0][tag]
        dPs.append(dP); pds.append(pdP); pss.append(pdS); hh.append(healthy(b,sg))
    pds=np.array(pds); dPs=np.array(dPs); pss=np.array(pss); hh=np.array(hh)
    return pds,dPs,pss,hh
def report(name, sel):
    pds,dPs,pss,hh=pooled(sel)
    if len(pds)==0: print(f"  {name}: no data"); return
    print(f"  {name:22s} per-day-P={pds.mean():+.4f} DENSE-P={dPs.mean():+.4f} S={pss.mean():+.4f} | IC-IR={pds.mean()/(pds.std()+1e-9):+.2f} | worst={pds.min():+.4f} | %+={100*np.mean(pds>0):.0f}% | %bh={100*hh.mean():.0f}%")

# selection rules
sel_ema={mk:"EMA" for mk in data}
sel_best={mk:"BEST" for mk in data}
sel_valcausal={}
for mk,(cks,vbs,ves,vbc,vec) in data.items():
    # causal: pick checkpoint with healthier VAL sigma (closest to a healthy ~0.05, prefer >=0.02), tie val_composite
    cand=[]
    if "BEST" in cks: cand.append(("BEST",vbs,vbc))
    if "EMA" in cks: cand.append(("EMA",ves,vec))
    # prefer val_sigma in [0.02, 0.15] healthy band; else higher composite
    ok=[c for c in cand if np.isfinite(c[1]) and 0.02<=c[1]<=0.20]
    pick=(max(ok,key=lambda c:(c[2] if np.isfinite(c[2]) else -9)) if ok else max(cand,key=lambda c:(c[2] if np.isfinite(c[2]) else -9)))
    sel_valcausal[mk]=pick[0]
sel_testoracle={}
for mk,(cks,*_ ) in data.items():
    best=None
    for tag,(_,(dP,pdP,pdS,b,sg)) in cks.items():
        score=(1 if healthy(b,sg) else 0, -abs(b-1.0))
        if best is None or score>best[0]: best=(score,tag)
    sel_testoracle[mk]=best[1]

print(f"=== per-month VAL-causal vs TEST-oracle pick (months={len(data)}) ===")
print(f"{'month':8s} {'valpick':>7s} {'val_bsig':>8s} {'val_esig':>8s} {'testpick':>8s}")
for mk in MONTHS:
    if mk not in data: continue
    _,vbs,ves,_,_=data[mk]
    print(f"{mk:8s} {sel_valcausal[mk]:>7s} {vbs:8.3f} {ves:8.3f} {sel_testoracle.get(mk,'?'):>8s}")
print("\n=== POOLED by selection rule ===")
report("FIXED always-EMA (HEADLINE)", sel_ema)
report("FIXED always-BEST", sel_best)
report("VAL-causal pick", sel_valcausal)
report("TEST-beta ORACLE (upper bd)", sel_testoracle)
# production CSV from no-peek headline (always-EMA)
csv_rows=[]
for mk in MONTHS:
    if mk in data and "EMA" in data[mk][0]:
        (L,_)=data[mk][0]["EMA"]; q,y,ts,ysig,ymed=L
        for i in range(len(q)): csv_rows.append((mk,"EMA",int(ts[i]),float(q[i]*ysig+ymed),float(y[i]*ysig+ymed)))
if csv_rows:
    os.makedirs("exports/honest_lq05",exist_ok=True)
    out="exports/honest_lq05/y600_lq05_alwaysEMA_walkforward.csv"
    with open(out,"w",newline="") as f:
        w=csv.writer(f); w.writerow(["month","checkpoint","timestamp_us","pred_q50_raw","target_raw"]); w.writerows(csv_rows)
    print(f"\n  NO-PEEK production CSV (always-EMA) -> {out} ({len(csv_rows)} rows)")
print("\nDONE_CAUSAL.")
