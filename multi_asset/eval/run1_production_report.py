"""Run1 (best single model) production preds export + full base-model metric battery. CPU-only.
Caliber (0B-verified): denorm q50->bps = (pred[:,1]*y_sigma+y_median)*1e4; realized = production CSV
RAW y_true_ret_bps (NOT clipped npz targets — those corr only ~0.88 to raw on heavy tails). Node set =
Run1 valid (mask) ∩ has-raw-y. 2025_08/09 raw-y is PARTIAL (prod CSV covers 4315/3534 of the month).

Outputs:
  exports/run1_production_preds_from_2025_08.csv  (full pred trace: ts, month, y_pred_bps, y_true_bps, mask, has_ytrue)
  prints per-month + pooled battery for RUN1 and PRODUCTION side-by-side, cd-CLEAN + DENSE.
"""
import numpy as np, pandas as pd, os
from scipy.stats import pearsonr, spearmanr

MA = "/mnt/storage/private/work_hsy/quant_research_multi_asset"
MONTHS = ["2025_08","2025_09","2025_10","2025_11","2025_12","2026_01","2026_02","2026_03","2026_04","2026_05"]
HZ = 600*1000; DAY = 86400*1000                 # metrics run on timestamp_ms (MILLISECONDS)
RUN1_NPZ = MA + "/experiments/d1gate/d1_%s_run1/fold_0/ema_test_preds.npz"
PROD_CSV = MA + "/exports/final_l01/y600_backtest_dataset.csv"

# ------------- clean-sample selection (greedy per-day stride-600 non-overlap, µs) -------------
def clean_pool(t):
    """indices of a greedy ≥600s non-overlap sample, per UTC day, pooled (time order preserved)."""
    o = np.argsort(t); keep = []
    dk = t[o]//DAY
    for d in np.unique(dk):
        di = o[dk==d]; last = -1<<62
        for i in di:                       # di already time-sorted within day
            if t[i]-last >= HZ:
                keep.append(i); last = t[i]
    return np.array(sorted(keep), int)

# ------------- metrics -------------
def _P(q,y):  return float(pearsonr(q,y)[0])  if len(q)>10 and q.std()>1e-12 and y.std()>1e-12 else np.nan
def _S(q,y):  return float(spearmanr(q,y)[0]) if len(q)>10 and q.std()>1e-12 and y.std()>1e-12 else np.nan
def _beta(q,y): return float(np.cov(y,q)[0,1]/q.var()) if q.var()>1e-18 else np.nan
def _sigr(q,y): return float(q.std()/y.std()) if y.std()>1e-12 else np.nan

def cd_perday_P(q,y,t,fn=_P):
    dk=t//DAY; rs=[]
    for d in np.unique(dk):
        idx=np.where(dk==d)[0]; ti=t[idx]
        o=np.argsort(ti); last=-1<<62; sel=[]
        for j in o:
            if ti[j]-last>=HZ: sel.append(j); last=ti[j]
        if len(sel)>20:
            r=fn(q[idx][sel],y[idx][sel])
            if np.isfinite(r): rs.append(r)
    return float(np.mean(rs)) if rs else np.nan

def corr_r2(q,y):  r=_P(q,y);  return r*r if np.isfinite(r) else np.nan
def pred_r2(q,y):  return 1.0 - np.mean((y-q)**2)/np.var(y) if np.var(y)>1e-18 else np.nan

def causal_beta_rescale(q,y,t,win_days=30,emb_days=1,min_rows=200):
    """ŷ'=β̂_trail·ŷ; β̂ from OLS(y~ŷ) over a trailing win_days window of LABEL-CLOSED rows
    (t_j+LAG<=t_i, t_j>t_i-W-LAG). Vectorised via prefix sums + searchsorted -> O(n log n)."""
    W=win_days*DAY; LAG=HZ+emb_days*DAY; n=len(q)
    o=np.argsort(t,kind="mergesort"); ts=t[o]; qs=q[o]; ys=y[o]
    # prefix sums (index 0 = empty)
    cy=np.concatenate([[0.],np.cumsum(ys)]); cq=np.concatenate([[0.],np.cumsum(qs)])
    cyq=np.concatenate([[0.],np.cumsum(ys*qs)]); cqq=np.concatenate([[0.],np.cumsum(qs*qs)])
    hi=np.searchsorted(ts, ts-LAG, side="right")          # rows with t_j <= t_i-LAG
    lo=np.searchsorted(ts, ts-W-LAG, side="right")         # rows with t_j <= t_i-W-LAG (exclusive lower)
    cnt=hi-lo
    sy=cy[hi]-cy[lo]; sq=cq[hi]-cq[lo]; syq=cyq[hi]-cyq[lo]; sqq=cqq[hi]-cqq[lo]
    cnt_s=np.where(cnt>0,cnt,1)
    cov=syq/cnt_s - (sy/cnt_s)*(sq/cnt_s)
    var=sqq/cnt_s - (sq/cnt_s)**2
    bo=np.where((cnt>=min_rows)&(var>1e-18), cov/np.where(var>1e-18,var,1.0), np.nan)
    fv=np.where(np.isfinite(bo))[0]
    if len(fv):
        seed=bo[fv[0]]
        for k in range(len(bo)):
            if not np.isfinite(bo[k]): bo[k]=bo[k-1] if k>0 else seed
    b=np.empty(n); b[o]=np.clip(np.nan_to_num(bo,nan=1.0),0.25,10.0)
    return b*q

def diracc(q,y):
    m=y!=0
    return float(np.mean(np.sign(q[m])==np.sign(y[m]))) if m.sum()>0 else np.nan
def diracc_bigmove(q,y):
    s=y.std(); m=(np.abs(y)>s)&(y!=0)
    return float(np.mean(np.sign(q[m])==np.sign(y[m]))) if m.sum()>10 else np.nan
def diracc_tail(q,y,frac=0.2):
    qd=q-q.mean(); thr=np.quantile(np.abs(qd),1-frac); m=(np.abs(qd)>=thr)&(y!=0)
    return float(np.mean(np.sign(q[m])==np.sign(y[m]))) if m.sum()>10 else np.nan

def bin_mono(q,y,nb=10):
    if len(q)<nb*5: return None
    edges=np.quantile(q,np.linspace(0,1,nb+1)); edges[-1]+=1e-9
    idx=np.clip(np.digitize(q,edges)-1,0,nb-1)
    means=np.array([y[idx==b].mean() if (idx==b).sum()>0 else np.nan for b in range(nb)])
    counts=np.array([(idx==b).sum() for b in range(nb)])
    valid=np.isfinite(means)
    sp=float(spearmanr(np.arange(nb)[valid],means[valid])[0]) if valid.sum()>2 else np.nan
    ups=int(np.sum(np.diff(means[valid])>0)); steps=valid.sum()-1
    return dict(means=means,counts=counts,spearman=sp,up=ups,steps=steps)

def ls_bias(q):  return float(q.mean())      # temporal demean target = 0; report raw mean(pred) bps

# ------------- assemble Run1 preds (denorm q50) + raw y join -------------
prod=pd.read_csv(PROD_CSV); prod=prod[["timestamp_ms","y_pred_raw","y_true_ret_bps","month"]].copy()
cy=dict(zip(prod.timestamp_ms.values.astype(np.int64), prod.y_true_ret_bps.values.astype(float)))

rows=[]
for mk in MONTHS:
    z=np.load(RUN1_NPZ%mk,allow_pickle=True); pr=z["predictions"]
    q=(pr[:,1] if pr.ndim==2 else pr).astype(float)
    ts=z["timestamps"].astype(np.int64)                    # µs
    ysig=float(z["y_sigma"]); ymed=float(z["y_median"])
    pred_bps=(q*ysig+ymed)*1e4
    m=z["mask"].astype(bool) if "mask" in z.files else np.ones(len(q),bool)
    ts_ms=ts//1000
    for i in range(len(q)):
        yt=cy.get(int(ts_ms[i]),np.nan)
        rows.append((int(ts_ms[i]),mk,float(pred_bps[i]),yt,bool(m[i]),ts[i]))
R=pd.DataFrame(rows,columns=["timestamp_ms","month","y_pred_bps","y_true_bps","mask","ts_us"]).sort_values("ts_us").reset_index(drop=True)
R["has_ytrue"]=np.isfinite(R.y_true_bps)

# export (full trace, drop internal ts_us helper -> re-add datetime)
exp=R[["timestamp_ms","month","y_pred_bps","y_true_bps","mask","has_ytrue"]].copy()
exp["datetime_utc"]=pd.to_datetime(exp.timestamp_ms,unit="ms").dt.strftime("%Y-%m-%d %H:%M:%S")
exp=exp[["timestamp_ms","datetime_utc","month","y_pred_bps","y_true_bps","mask","has_ytrue"]]
OUT=MA+"/exports/run1_production_preds_from_2025_08.csv"
exp.to_csv(OUT,index=False)
nval=int(exp["mask"].sum()); nyt=int(exp.has_ytrue.sum())
print(f"EXPORT: {OUT}  ({len(exp)} rows, {nval} valid, {nyt} with raw-y)")

# eval set = valid & has raw y
E=R[R["mask"] & R.has_ytrue].copy()

# ------------- per-month + pooled battery, RUN1 vs PROD -------------
def battery_rows(df_q, df_y, df_t):
    q=df_q.values.astype(float); y=df_y.values.astype(float); t=df_t.values.astype(np.int64)
    ci=clean_pool(t); qc,yc,tc=q[ci],y[ci],t[ci]
    qr=causal_beta_rescale(q,y,t)
    d=dict(
      P_cd=cd_perday_P(q,y,t,_P), P_clean=_P(qc,yc), P_dense=_P(q,y),
      S_cd=cd_perday_P(q,y,t,_S), S_clean=_S(qc,yc), S_dense=_S(q,y),  # noqa
      corrR2_clean=corr_r2(qc,yc), corrR2_dense=corr_r2(q,y),
      predR2raw_clean=pred_r2(qc,yc), predR2raw_dense=pred_r2(q,y),
      predR2resc_clean=pred_r2(qr[ci],yc), predR2resc_dense=pred_r2(qr,y),
      DA_clean=diracc(qc,yc), DA_dense=diracc(q,y),
      DAbig_clean=diracc_bigmove(qc,yc), DAbig_dense=diracc_bigmove(q,y),
      DAtail_clean=diracc_tail(qc,yc), DAtail_dense=diracc_tail(q,y),
      beta_clean=_beta(qc,yc), beta_dense=_beta(q,y),
      sigr_clean=_sigr(qc,yc), sigr_dense=_sigr(q,y),
      bias_clean=ls_bias(qc), bias_dense=ls_bias(q),
      n_clean=len(ci), n_dense=len(q))
    return d, (qc,yc)

# production series on the SAME nodes (join prod preds to E by ts)
pp=dict(zip(prod.timestamp_ms.values.astype(np.int64), prod.y_pred_raw.values.astype(float)))
E["prod_pred"]=E.timestamp_ms.map(pp)
Ep=E[np.isfinite(E.prod_pred)].copy()

print(f"\nEVAL nodes: Run1 {len(E)} | Run1∩prod {len(Ep)}")
hdr=["month","n_cl","P_cd","P_cln","P_den","S_cln","S_den","corR2cl","pR2raw","pR2resc","DAcl","DAbig","DAtail","beta","sigr","bias"]
def fmt(mk,d):
    return (f"{mk:>8s} {d['n_clean']:5d} {d['P_cd']:+.4f} {d['S_cd']:+.4f} {d['P_dense']:+.4f} "
            f"{d['S_dense']:+.4f} {d['P_clean']:+.4f} {d['corrR2_clean']:.4f} {d['predR2raw_clean']:+.3f} "
            f"{d['predR2resc_clean']:+.3f} {d['DA_clean']:.3f} {d['DAbig_clean']:.3f} {d['DAtail_clean']:.3f} "
            f"{d['beta_clean']:+.2f} {d['sigr_clean']:.3f} {d['bias_clean']:+.3f}")

print("\n===== RUN1 per-month (CLEAN=pooled non-overlap; P_cd=per-day-avg headline) =====")
print("   month  n_cl   P_cd   S_cd  P_den  S_den  P_cln corR2cl pR2raw pR2res  DAcl DAbig DAtail  beta  sigr   bias")
allmet={}
for mk in MONTHS:
    sub=E[E.month==mk]
    if len(sub)<50:
        print(f"{mk:>8s}  (n={len(sub)}, too few — raw-y coverage gap)"); continue
    d,_=battery_rows(sub.y_pred_bps,sub.y_true_bps,sub.timestamp_ms); allmet[mk]=d
    print(fmt(mk,d))
dpool,_=battery_rows(E.y_pred_bps,E.y_true_bps,E.timestamp_ms); allmet["POOLED"]=dpool
print(fmt("POOLED",dpool))

print("\n===== PRODUCTION per-month (same nodes, prod y_pred_raw) =====")
print("   month  n_cl   P_cd   S_cd  P_den  S_den  P_cln corR2cl pR2raw pR2res  DAcl DAbig DAtail  beta  sigr   bias")
for mk in MONTHS:
    sub=Ep[Ep.month==mk]
    if len(sub)<50:
        print(f"{mk:>8s}  (n={len(sub)})"); continue
    d,_=battery_rows(sub.prod_pred,sub.y_true_bps,sub.timestamp_ms)
    print(fmt(mk,d))
dpp,_=battery_rows(Ep.prod_pred,Ep.y_true_bps,Ep.timestamp_ms)
print(fmt("POOLED",dpp))

# ------------- bin monotonicity (pooled clean) -------------
ci=clean_pool(E.timestamp_ms.values.astype(np.int64))
qc=E.y_pred_bps.values[ci]; yc=E.y_true_bps.values[ci]
bm=bin_mono(qc,yc)
print(f"\n===== BIN MONOTONICITY (Run1 pooled CLEAN n={len(qc)}, decile ŷ -> mean realized y) =====")
print("  bin:  " + " ".join(f"{i:6d}" for i in range(10)))
print("  ŷ̄ y_bps:" + " ".join(f"{v:6.2f}" for v in bm['means']))
print("  n:    " + " ".join(f"{c:6d}" for c in bm['counts']))
print(f"  monotonicity: spearman(bin_mean_y, bin_idx)={bm['spearman']:+.3f}  up-steps={bm['up']}/{bm['steps']}")
# per-month monotonicity breaks
print("  per-month bin-monotonicity spearman:", end=" ")
for mk in MONTHS:
    sub=E[E.month==mk]
    if len(sub)<100: print(f"{mk.split('_')[1]}=NA",end=" "); continue
    cci=clean_pool(sub.timestamp_ms.values.astype(np.int64))
    b2=bin_mono(sub.y_pred_bps.values[cci],sub.y_true_bps.values[cci])
    print(f"{mk[2:]}={b2['spearman']:+.2f}" if b2 else f"{mk[2:]}=NA",end=" ")
print()

# coverage flag
print("\n===== COVERAGE (raw-y ground truth per month) =====")
for mk in MONTHS:
    tot=int((R.month==mk).sum()); val=int(((R.month==mk)&R["mask"]).sum()); yy=int(((R.month==mk)&R["mask"]&R.has_ytrue).sum())
    flag="FULL" if yy/max(val,1)>0.98 else ("PARTIAL raw-y" if yy>0 else "NONE")
    warm=" (calib-warmup: prod backtest ê=0)" if mk in ("2025_08","2025_09") else ""
    print(f"  {mk}: valid={val} raw-y={yy} ({100*yy/max(val,1):.0f}%) {flag}{warm}")
print("DONE_REPORT")
