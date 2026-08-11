"""FINAL DELIVERABLE (lambda0.1 default trajectory). Builds items 1/3/4 of the deliverable:
 1. Per-month table: DENSE + per-day-CLEAN Pearson/S/beta/sigma/DA (EMA = no-peek headline). Pooled + IC-IR + worst + %pos + %sigma-healthy.
 3. MONOTONICITY/CALIBRATION: decile-bin q50, plot MEAN realized y per bin (x=pred-bin mean q50, y=realized mean). Monotone-through-origin? intercept/slope via OLS on binned points + on raw. PNG pooled + per-month grid.
 4. CAUSAL SLIDING-WINDOW DEMEAN: subtract TRAILING rolling-mean of q50 (<=t, NOT full-sample) -> remove persistent long/short bias. Binned calibration BEFORE vs AFTER, intercept before/after, IC before/after (must not hurt).
Reads experiments_local/wfEMA/ (or --dir). Headline abs-Pearson at sigma>=0.02. Outputs PNG + prints table.
Run LOCAL: python multi_asset/eval/final_deliverable_l01.py [--dir experiments_local/wfEMA] [--win 600]
"""
from __future__ import annotations
import numpy as np, os, argparse, csv
import matplotlib; matplotlib.use("Agg")
import matplotlib.pyplot as plt
from scipy.stats import pearsonr, spearmanr
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
    y=z["targets"].astype(np.float64); ts=z["timestamps"].astype(np.int64)
    ysig=float(z["y_sigma"]) if "y_sigma" in z else 1.0; ymed=float(z["y_median"]) if "y_median" in z else 0.0
    # HYGIENE (Stage-0a): drop padded rows (mask==0, y==0). ~808 across 10 months
    # leaked into aggregates + backtest CSV; they must NEVER be scored.
    if "mask" in z.files:
        keep=z["mask"].astype(bool); q,y,ts=q[keep],y[keep],ts[keep]
    o=np.argsort(ts); return q[o],y[o],ts[o],ysig,ymed

def perday_clean(q,y,ts):
    daykey=ts//(86400*1_000_000); rs=[];ss=[]
    for dk in np.unique(daykey):
        m=daykey==dk; k=clean_idx(ts[m])
        if len(k)>20:
            qk=q[m][k]; yk=y[m][k]
            if qk.std()>1e-12:
                r=pearsonr(qk,yk)[0]; s=spearmanr(qk,yk)[0]
                if np.isfinite(r): rs.append(r);ss.append(s)
    return (np.mean(rs) if rs else np.nan),(np.mean(ss) if ss else np.nan)

def dense_metrics(q,y):
    P=pearsonr(q,y)[0]; S=spearmanr(q,y)[0]
    b=np.cov(y,q)[0,1]/q.var() if q.var()>1e-12 else np.nan; sg=q.std()/(y.std()+1e-12)
    DA=np.mean(np.sign(q)==np.sign(y))
    return P,S,b,sg,DA

def decile_calib(q,y,nb=10):
    # bin by q50 deciles; return (mean q50 per bin, mean realized y per bin, counts)
    edges=np.quantile(q,np.linspace(0,1,nb+1)); edges[0]-=1e-9; edges[-1]+=1e-9
    bi=np.clip(np.digitize(q,edges)-1,0,nb-1)
    xs=[];ys=[];ns=[]
    for b in range(nb):
        m=bi==b
        if m.sum()>0: xs.append(q[m].mean()); ys.append(y[m].mean()); ns.append(int(m.sum()))
    return np.array(xs),np.array(ys),np.array(ns)

def causal_demean(q,ts,win_ns):
    # subtract TRAILING rolling mean of q over a time window (<=t). Causal (no future).
    o=np.argsort(ts); ts_s=ts[o]; q_s=q[o]; out=np.empty_like(q_s)
    # two-pointer trailing window
    lo=0; csum=0.0; cnt=0
    from collections import deque
    dq=deque()  # store q values in window
    j=0
    for i in range(len(q_s)):
        # expand to include i
        dq.append((ts_s[i],q_s[i])); csum+=q_s[i]; cnt+=1
        # shrink from left: keep only ts >= ts_s[i]-win_ns (strictly trailing incl current)
        while dq and dq[0][0] < ts_s[i]-win_ns:
            t0,v0=dq.popleft(); csum-=v0; cnt-=1
        out[i]=q_s[i]-(csum/cnt if cnt>0 else 0.0)
    # unsort
    res=np.empty_like(out); res[o]=out; return res

def main():
    ap=argparse.ArgumentParser(); ap.add_argument("--dir",default="experiments_local/wfEMA")
    ap.add_argument("--win",type=int,default=3600,help="causal demean window in SECONDS"); ap.add_argument("--ck",default="EMA")
    a=ap.parse_args(); win_ns=a.win*1_000_000
    rows=[]; data={}
    print(f"=== FINAL lambda0.1 trajectory ({a.ck} = no-peek headline) dir={a.dir} ===")
    print(f"{'month':8s} {'N':>6s} | {'DENSE-P':>8s} {'cd-CLEAN-P':>10s} {'DENSE-S':>8s} {'cd-CLEAN-S':>10s} | {'beta':>6s} {'sigma':>6s} {'DA':>5s} {'health':>6s}")
    for mk in MONTHS:
        L=load(f"{a.dir}/wf_{mk}/fold_0/{'ema_' if a.ck=='EMA' else ''}test_preds.npz")
        if L is None: print(f"{mk:8s}  (missing)"); continue
        q,y,ts,ysig,ymed=L; data[mk]=L
        P,S,b,sg,DA=dense_metrics(q,y); cP,cS=perday_clean(q,y,ts)
        health="OK" if (sg>=0.02 and 0.5<=b<=1.8) else "BAD"  # unified β band [0.5,1.8] (Stage-0a)
        print(f"{mk:8s} {len(q):6d} | {P:+8.4f} {cP:+10.4f} {S:+8.4f} {cS:+10.4f} | {b:+6.2f} {sg:6.3f} {DA:5.3f} {health:>6s}")
        rows.append((mk,P,cP,S,cS,b,sg,DA))
    if not rows: print("NO DATA"); return
    arr=np.array([(r[1],r[2],r[3],r[4],r[5],r[6]) for r in rows],float)
    dP,cP,dS,cS,bb,sg=arr.T
    print(f"\n=== POOLED ({len(rows)} months, EMA) ===")
    print(f"  DENSE-P mean={dP.mean():+.4f}  per-day-CLEAN-P mean={cP.mean():+.4f}  (headline abs-P at sigma>=0.02)")
    print(f"  DENSE-S mean={dS.mean():+.4f}  per-day-CLEAN-S mean={cS.mean():+.4f}")
    print(f"  IC-IR (per-day-CLEAN) = {cP.mean()/(cP.std()+1e-9):+.2f}  | worst-month cd-CLEAN-P={cP.min():+.4f} ({rows[int(cP.argmin())][0]})")
    bhealthy=100*np.mean((sg>=0.02)&(bb>=0.5)&(bb<=1.8))  # unified band [0.5,1.8] (Stage-0a)
    print(f"  %-positive (cd-CLEAN) = {100*np.mean(cP>0):.0f}%  | %-sigma-healthy = {100*np.mean(sg>=0.02):.0f}%  | %-health(σ≥.02 & β∈[.5,1.8]) = {bhealthy:.0f}%  | beta range [{bb.min():+.2f},{bb.max():+.2f}]")

    # ---- pooled arrays for calibration / demean (concat all months) ----
    Q=np.concatenate([data[m][0] for m in data]); Y=np.concatenate([data[m][1] for m in data])
    TS=np.concatenate([data[m][2] for m in data])
    # item 3: monotonicity / calibration (pooled, raw q50)
    xs,ys,ns=decile_calib(Q,Y)
    xq,yq,nq=decile_calib(Q,Y,nb=5)  # quintiles = stabler for low-IC
    # OLS on binned points (intercept, slope) and on raw
    sl_b,ic_b=np.polyfit(xs,ys,1); sl_r,ic_r=np.polyfit(Q,Y,1)
    mono=np.mean(np.diff(ys)>0)  # fraction of increasing steps (noisy for low-IC)
    monoq=np.mean(np.diff(yq)>0)
    binS=spearmanr(xs,ys)[0]; binSq=spearmanr(xq,yq)[0]  # rank-monotonicity (the honest measure)
    print(f"\n=== item3 MONOTONICITY/CALIBRATION (pooled, raw q50 std-units) ===")
    print(f"  bin-SPEARMAN (rank-monotone, PRIMARY) = decile {binS:+.2f} | quintile {binSq:+.2f}  (+1 = perfectly monotone ranking)")
    print(f"  frac-increasing-steps = decile {mono:.2f} | quintile {monoq:.2f}  (noisy for low-IC, adjacent-bin reversals are noise)")
    print(f"  binned OLS: slope={sl_b:+.3f} intercept={ic_b:+.5f}  | raw OLS: slope={sl_r:+.3f} intercept={ic_r:+.5f}")
    print(f"  NOTE: intercept ({ic_b:+.5f}) == pooled realized y_mean ({Y.mean():+.5f}); pred bias (q50_mean)={Q.mean():+.5f} ~0.")
    print(f"  => intercept is the TEST-PERIOD MARKET DRIFT, not a model long/short bias. Demeaning PRED removes pred-bias, not realized-y mean.")
    print(f"  quintile bin means realized y: {np.round(yq,4).tolist()}")

    # item 4: causal sliding-window demean (pooled, but demean computed per-month to respect month boundaries)
    Qd=np.concatenate([causal_demean(data[m][0],data[m][2],win_ns) for m in data])
    xs2,ys2,ns2=decile_calib(Qd,Y)
    sl_b2,ic_b2=np.polyfit(xs2,ys2,1)
    P_before=pearsonr(Q,Y)[0]; P_after=pearsonr(Qd,Y)[0]
    bias_before=Q.mean(); bias_after=Qd.mean()
    print(f"\n=== item4 CAUSAL SLIDING-WINDOW DEMEAN (trailing {a.win}s, <=t) ===")
    print(f"  pred-mean (long/short bias): before={bias_before:+.5f} -> after={bias_after:+.5f}")
    print(f"  binned intercept: before={ic_b:+.5f} -> after={ic_b2:+.5f}")
    print(f"  pooled DENSE IC: before={P_before:+.4f} -> after={P_after:+.4f}  (must NOT hurt)")

    # ---- PNG: pooled calibration before/after ----
    fig,axes=plt.subplots(1,2,figsize=(13,5))
    ax=axes[0]
    ax.axhline(0,color="gray",lw=0.6); ax.axvline(0,color="gray",lw=0.6)
    ax.plot(xs,ys,"o-",label=f"raw q50 (mono {mono:.2f}, ic {ic_b:+.4f})",color="C0")
    ax.plot(xs2,ys2,"s--",label=f"causal-demean {a.win}s (ic {ic_b2:+.4f})",color="C1")
    lim=max(abs(xs).max(),abs(xs2).max())*1.1
    ax.plot([-lim,lim],[sl_b*-lim+ic_b,sl_b*lim+ic_b],":",color="C0",alpha=0.5)
    ax.set_xlabel("pred-bin mean q50 (std units)"); ax.set_ylabel("realized mean y (std units)")
    ax.set_title(f"Decile calibration (pooled {len(data)} mo, EMA)\nmonotone-through-origin check"); ax.legend(fontsize=8)
    # per-month mini calibration
    ax=axes[1]
    for mk in data:
        q,y,ts,_,_=data[mk]; xm,ym,_=decile_calib(q,y)
        ax.plot(xm,ym,"-",alpha=0.6,label=mk)
    ax.axhline(0,color="gray",lw=0.6); ax.axvline(0,color="gray",lw=0.6)
    ax.set_xlabel("pred-bin mean q50"); ax.set_ylabel("realized mean y"); ax.set_title("Per-month decile calibration"); ax.legend(fontsize=6,ncol=2)
    os.makedirs("exports/final_l01",exist_ok=True)
    out="exports/final_l01/calibration_monotonicity.png"; plt.tight_layout(); plt.savefig(out,dpi=110); print(f"\n  PNG -> {out}")

    # production CSV (raw y, no-peek EMA, causal-demeaned q50 + raw q50)
    outcsv="exports/final_l01/y600_l01_alwaysEMA_walkforward.csv"
    with open(outcsv,"w",newline="") as f:
        w=csv.writer(f); w.writerow(["month","timestamp_us","pred_q50_raw","pred_q50_demean_raw","target_raw"])
        for mk in data:
            q,y,ts,ysig,ymed=data[mk]; qd=causal_demean(q,ts,win_ns)
            for i in range(len(q)):
                w.writerow([mk,int(ts[i]),f"{q[i]*ysig+ymed:.8e}",f"{qd[i]*ysig:.8e}",f"{y[i]*ysig+ymed:.8e}"])
    print(f"  production CSV -> {outcsv}")
    print("DONE_FINAL_L01.")

if __name__=="__main__": main()
