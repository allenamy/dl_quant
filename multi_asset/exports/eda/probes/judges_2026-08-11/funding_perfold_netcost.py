"""Per-fold net-cost robustness of funding_ema: is the break-even 18.8 all-fold or fold-1-driven?
Compute the operating-alpha (0.02) break-even + gross Sharpe separately for each fold's test days."""
import sys, glob, numpy as np, os.path as op
sys.path.insert(0,"/mnt/storage/private/work_hsy/quant_research_multi_asset")
from multi_asset.eval.backtest_longshort import rank_weights
MA="/mnt/storage/private/work_hsy/quant_research_multi_asset"; TAG="fund_ema_h3600"; MIN=5; H=3600
d=op.join(MA,"multi_asset/exports/train",TAG)
ref=np.load(op.join(d,"panel_ref.npz"),allow_pickle=True); Y=ref["Y"]; CL=ref["CL"]; ts=ref["ts"].astype(np.int64); day=ref["day"].astype(np.int64)
T,S=Y.shape; per_yr=365*24*3600/H; ann=np.sqrt(per_yr)
# fold assignment: which fold's te_rows covers each row
foldof=np.full(T,-1)
for fi,f in enumerate(sorted(glob.glob(op.join(d,"fold_*_preds.npz")))):
    z=np.load(f); foldof[z["te_rows"]]=fi
pred=np.full((T,S),np.nan)
for f in sorted(glob.glob(op.join(d,"fold_*_preds.npz"))):
    z=np.load(f); pred[z["te_rows"]]=z["pred"][z["te_rows"]]

def be_for(rows, alpha=0.02):
    tw=[]; Yr=[]; ic=[]
    for t in rows:
        v=CL[t]&np.isfinite(pred[t])&np.isfinite(Y[t])
        if v.sum()<MIN: continue
        idx=np.where(v)[0]; w=np.zeros(S); w[idx]=rank_weights(pred[t,idx]); tw.append(w); Yr.append(np.where(v,Y[t],0.0))
        from scipy.stats import spearmanr as sp
        r=sp(pred[t,idx],Y[t,idx]).correlation
        if np.isfinite(r): ic.append(r)
    tw=np.array(tw); Yr=np.array(Yr); n=len(tw)
    if n<20: return None
    held=np.zeros(S); g=np.empty(n); tn=np.empty(n)
    for k in range(n):
        new=alpha*tw[k]+(1-alpha)*held; tn[k]=np.abs(new-held).sum(); g[k]=float((new*Yr[k]).sum()); held=new
    be=g.mean()/tn.mean()*1e4 if tn.mean()>1e-12 else np.nan
    net2=g-tn*(2e-4); sh2=net2.mean()/net2.std()*ann if net2.std()>0 else np.nan
    return dict(n=n, meanIC=float(np.mean(ic)), be=float(be), grossSh=float(g.mean()/g.std()*ann) if g.std()>0 else np.nan,
                netSh_c2=float(sh2), net_c2_ann=float(net2.mean()*per_yr*1e4))

print(f"funding_ema per-fold net-cost (operating α=0.02, cost @2bps/side):")
print(f"{'fold':>6s} {'n':>5s} {'meanIC':>8s} {'BE/side':>8s} {'grossSh':>8s} {'netSh@2':>8s} {'net@2 ann bps':>13s}")
for fi in [0,1,2]:
    rows=np.where(foldof==fi)[0]; r=be_for(rows)
    if r: print(f"{fi:6d} {r['n']:5d} {r['meanIC']:+8.4f} {r['be']:8.3f} {r['grossSh']:8.2f} {r['netSh_c2']:8.2f} {r['net_c2_ann']:13.0f}")
    else: print(f"{fi:6d}  (too few)")
allr=be_for(np.where(foldof>=0)[0]); print(f"{'ALL':>6s} {allr['n']:5d} {allr['meanIC']:+8.4f} {allr['be']:8.3f} {allr['grossSh']:8.2f} {allr['netSh_c2']:8.2f} {allr['net_c2_ann']:13.0f}")
print("DONE")
