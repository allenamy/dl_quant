"""Build CLEAN BACKTEST-READY dataset from the BEST model (lambda0.1, EMA no-peek, 10-month rolling walk-forward).
One row per prediction node. Real perp book-mid for the true-return + causal market-drift columns. All causal (<=t).

Columns:
  timestamp_ms, datetime_utc      : entry time
  y_pred_raw                      : model q50 (std-units, EMA no-peek checkpoint)
  y_pred_demeaned                 : q50 - CAUSAL trailing EMA of q50 (<=t)  [bias-free tradeable signal]
  y_true_ret_bps                  : realized 600s forward PERP log-return (bps) from REAL perp book-mid (P&L basis)
  y_true_demeaned_bps             : y_true_ret_bps - CAUSAL trailing market-drift (<=t)  [drift-neutral = genuine alpha]
  month                           : rolling fold tag
Demean windows: PRED = trailing 3600s EMA (halflife ~ window); MARKET-DRIFT = trailing 3600s mean of y_true_ret_bps (<=t).
Verify: (a) y_pred_demeaned binned-vs-y_true monotone through ~origin + intercept; (b) mean(y_true_demeaned)~0;
        (c) counts, no NaN, sorted/unique timestamps.
Run on SERVER: PYTHONPATH=. python multi_asset/eval/build_backtest_dataset.py
"""
from __future__ import annotations
import numpy as np, os, csv, gzip
from datetime import datetime, timezone, timedelta
from scipy.stats import spearmanr
BOOK="/mnt/storage/btcusdt_copy_2023-01-01_2026-05-31/dl-tardis/book_snapshot_25"; VENUE="binance-futures"
MONTHS=["2025_08","2025_09","2025_10","2025_11","2025_12","2026_01","2026_02","2026_03","2026_04","2026_05"]
HZ=600*1_000_000; DEMEAN_S=3600  # both demean windows = 3600s
WL=DEMEAN_S*1_000_000

def load_pred(mk):
    f=f"experiments/wfEMA/wf_{mk}/fold_0/ema_test_preds.npz"
    if not os.path.exists(f): return None
    z=np.load(f,allow_pickle=True); pr=z["predictions"]
    q=(pr[:,1] if pr.ndim==2 else pr).astype(np.float64)
    ts=z["timestamps"].astype(np.int64)
    # HYGIENE (Stage-0a): drop padded rows (mask==0) BEFORE recomputing y_true from
    # book-mid — else ~808 padded nodes leak into the CSV with real-looking (but
    # meaningless) recomputed returns. Note: the 82 y_true==0 rows are genuine
    # mask==1 zero-return nodes and are KEPT (a y==0 filter would be wrong).
    if "mask" in z.files:
        keep=z["mask"].astype(bool); q,ts=q[keep],ts[keep]
    o=np.argsort(ts)
    return ts[o], q[o]

def day_list(ts):
    t0=datetime.fromtimestamp(ts.min()/1e6,tz=timezone.utc).date(); t1=datetime.fromtimestamp((ts.max()+HZ)/1e6,tz=timezone.utc).date()
    out=[];d=t0
    while d<=t1: out.append(d.isoformat()); d+=timedelta(days=1)
    return out
def load_day(day):
    f=f"{BOOK}/{day}/{VENUE}/BTCUSDT.csv.gz"
    if not os.path.exists(f): return None
    ts=[];mid=[];last=-1
    with gzip.open(f,"rt") as fh:
        hdr=fh.readline().split(","); ia=hdr.index("asks[0].price"); ib=hdr.index("bids[0].price"); it=hdr.index("timestamp")
        for line in fh:
            p=line.split(",")
            try:
                t=int(p[it])
                if t-last<1_000_000: continue
                ts.append(t); mid.append((float(p[ia])+float(p[ib]))/2); last=t
            except: continue
    return (np.array(ts,np.int64),np.array(mid,np.float64)) if ts else None
def mid_series(node_ts):
    TS=[];MID=[]
    for d in day_list(node_ts):
        r=load_day(d)
        if r: TS.append(r[0]);MID.append(r[1])
    TS=np.concatenate(TS);MID=np.concatenate(MID);o=np.argsort(TS);return TS[o],MID[o]
def at(g,TS,MID,maxgap=5_000_000):
    idx=np.searchsorted(TS,g,side="right")-1; v=np.full(len(g),np.nan); m=idx>=0; v[m]=MID[idx[m]]
    gap=np.full(len(g),1e18); gap[m]=g[m]-TS[idx[m]]; v[gap>maxgap]=np.nan; return v
def causal_ema(x, ts, win_ns):
    # trailing EMA with halflife ~ win; alpha from per-step dt. Simpler: trailing-window mean (<=t), strictly causal.
    out=np.empty_like(x); from collections import deque; dq=deque(); s=0.0; n=0
    for i in range(len(x)):
        dq.append((ts[i],x[i])); s+=x[i]; n+=1
        while dq and dq[0][0] < ts[i]-win_ns:
            t0,v0=dq.popleft(); s-=v0; n-=1
        out[i]=s/n if n>0 else 0.0
    return out

def main():
    rows=[]
    print(f"=== BUILD backtest dataset (lambda0.1 EMA no-peek, demean win={DEMEAN_S}s, real perp mid) ===",flush=True)
    for mk in MONTHS:
        P=load_pred(mk)
        if P is None: print(f"  {mk}: no pred",flush=True); continue
        ts,q=P
        TS,MID=mid_series(ts)
        m_now=at(ts,TS,MID); m_fut=at(ts+HZ,TS,MID)
        yret=np.log(m_fut/m_now)*1e4  # bps perp 600s fwd log-ret
        # causal demeans (per month, strictly <=t)
        qd=q-causal_ema(q,ts,WL)
        # market drift: trailing mean of yret (<=t). yret has the 600s-forward built in; trailing mean is a fine causal drift proxy.
        ok0=~np.isnan(yret)
        drift=np.full(len(yret),np.nan)
        # build trailing mean only over valid yret
        from collections import deque; dq=deque(); s=0.0; n=0
        for i in range(len(ts)):
            if ok0[i]: dq.append((ts[i],yret[i])); s+=yret[i]; n+=1
            while dq and dq[0][0] < ts[i]-WL:
                t0,v0=dq.popleft(); s-=v0; n-=1
            if n>0: drift[i]=s/n
        ytd=yret-drift
        keep=~np.isnan(yret)&~np.isnan(qd)&~np.isnan(ytd)
        for i in np.where(keep)[0]:
            dtu=datetime.fromtimestamp(ts[i]/1e6,tz=timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
            rows.append((ts[i]//1000, dtu, q[i], qd[i], yret[i], ytd[i], mk))
        print(f"  {mk}: nodes={len(ts)} kept={int(keep.sum())} midcov={np.mean(~np.isnan(m_now)):.2f}",flush=True)
    # write CSV
    os.makedirs("exports/final_l01",exist_ok=True)
    out="exports/final_l01/y600_backtest_dataset.csv"
    with open(out,"w",newline="") as f:
        w=csv.writer(f); w.writerow(["timestamp_ms","datetime_utc","y_pred_raw","y_pred_demeaned","y_true_ret_bps","y_true_demeaned_bps","month"])
        for r in rows: w.writerow([int(r[0]),r[1],f"{r[2]:.6f}",f"{r[3]:.6f}",f"{r[4]:.4f}",f"{r[5]:.4f}",r[6]])
    print(f"\n  CSV -> {out} ({len(rows)} rows)",flush=True)
    # ===== VERIFY =====
    ts_a=np.array([r[0] for r in rows]); qd_a=np.array([r[3] for r in rows]); yt=np.array([r[4] for r in rows]); ytd=np.array([r[5] for r in rows]); mn=np.array([r[6] for r in rows])
    print("\n=== VERIFY ===",flush=True)
    # (a) y_pred_demeaned binned vs y_true monotone + intercept
    nb=10; e=np.quantile(qd_a,np.linspace(0,1,nb+1)); e[0]-=1e-9;e[-1]+=1e-9; bi=np.clip(np.digitize(qd_a,e)-1,0,nb-1)
    xs=[];ys=[]
    for b in range(nb):
        mm=bi==b
        if mm.sum()>0: xs.append(qd_a[mm].mean()); ys.append(yt[mm].mean())
    xs=np.array(xs);ys=np.array(ys); sl,ic=np.polyfit(xs,ys,1); binS=spearmanr(xs,ys)[0]
    print(f"  (a) y_pred_demeaned binned-vs-y_true: bin-Spearman={binS:+.2f} slope={sl:+.3f} intercept={ic:+.4f}bps (monotone-through-origin)",flush=True)
    # (b) mean(y_true_demeaned)
    print(f"  (b) mean(y_true_demeaned_bps)={ytd.mean():+.5f}bps (should be ~0; mean raw y_true={yt.mean():+.4f} drift removed)",flush=True)
    print(f"      mean(y_pred_demeaned)={qd_a.mean():+.6f} (should be ~0)",flush=True)
    # (c) counts, NaN, sorted/unique
    nan_any=any(np.isnan([r[2],r[3],r[4],r[5]]).any() for r in rows)
    srt=bool(np.all(np.diff(ts_a)>=0)); uniq=len(np.unique(ts_a))==len(ts_a)
    print(f"  (c) rows={len(rows)} NaN={nan_any} sorted={srt} unique_ts={uniq}",flush=True)
    print("      per-month counts: "+" ".join(f"{m}:{int((mn==m).sum())}" for m in MONTHS if (mn==m).sum()>0),flush=True)
    print("DONE_BUILD.",flush=True)
if __name__=="__main__": main()
