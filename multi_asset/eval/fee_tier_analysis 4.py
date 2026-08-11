"""EXACT net-taker analysis at a given RT fee, from the saved short25 trade-level data (/tmp/short25_trades.npz).
RAW vs DRIFT-NEUTRAL (clean alpha = gross - drift_component). Exact annualized Sharpe = mean/sd * sqrt(n/span*365).
Per-month net-taker positive count + bootstrap CI on net-taker Sharpe (resample trades with replacement).
Run on SERVER: PYTHONPATH=. python multi_asset/eval/fee_tier_analysis.py --rt 3.4
"""
from __future__ import annotations
import numpy as np, argparse
def sharpe(x, tpy): return x.mean()/(x.std()+1e-12)*np.sqrt(tpy)
def main():
    ap=argparse.ArgumentParser(); ap.add_argument("--rt",type=float,default=3.4); ap.add_argument("--npz",default="/tmp/short25_trades.npz")
    a=ap.parse_args()
    z=np.load(a.npz,allow_pickle=True)
    g=z["gross"].astype(float); dc=z["drift_comp"].astype(float); mo=z["month"]; span=float(z["span_days"])
    n=len(g); tpy=n/span*365; RT=a.rt
    clean=g-dc  # drift-neutral per-trade alpha
    print(f"=== SHORT-ONLY +-2.5% net @ RT taker={RT}bps (n={n}, span={span:.0f}d, tpy={tpy:.0f}) ===")
    # 1. RAW
    raw_net=g-RT
    print(f"\n1. RAW (incl down-trend drift harvest):")
    print(f"   gross edge={g.mean():+.3f}bps -> NET={raw_net.mean():+.3f}bps | net-taker Sharpe={sharpe(raw_net,tpy):+.3f}")
    # 2. DRIFT-NEUTRAL
    cl_net=clean-RT
    print(f"\n2. DRIFT-NEUTRAL (regime-robust alpha):")
    print(f"   clean edge={clean.mean():+.3f}bps (drift comp={dc.mean():+.3f}) -> NET={cl_net.mean():+.3f}bps | net-taker Sharpe={sharpe(cl_net,tpy):+.3f}")
    # 3. PER-MONTH net-taker (raw + clean)
    print(f"\n3. PER-MONTH net-taker edge @ {RT}bps RT:")
    pos_raw=0; pos_cl=0; nmo=0
    for M in sorted(set(mo.tolist())):
        m=mo==M; nmo+=1
        rn=(g[m]-RT).mean(); cn=(clean[m]-RT).mean()
        pos_raw+=rn>0; pos_cl+=cn>0
        print(f"   {M}: n={m.sum():3d} RAW-net={rn:+6.2f} CLEAN-net={cn:+6.2f}")
    print(f"   => RAW net-positive: {pos_raw}/{nmo} months | CLEAN net-positive: {pos_cl}/{nmo} months")
    # 4. BOOTSTRAP CI on net-taker Sharpe (resample trades w/ replacement, 5000x)
    rng=np.random.default_rng(0); B=5000
    def boot(x):
        s=np.empty(B)
        for b in range(B):
            idx=rng.integers(0,n,n); s[b]=sharpe(x[idx],tpy)
        return np.percentile(s,[2.5,50,97.5])
    rci=boot(raw_net); cci=boot(cl_net)
    print(f"\n4. BOOTSTRAP 95% CI on net-taker Sharpe (5000x resample):")
    print(f"   RAW         : median={rci[1]:+.2f} CI=[{rci[0]:+.2f}, {rci[2]:+.2f}]  {'(excludes 0)' if rci[0]>0 else '(INCLUDES 0)'}")
    print(f"   DRIFT-NEUTRAL: median={cci[1]:+.2f} CI=[{cci[0]:+.2f}, {cci[2]:+.2f}]  {'(excludes 0)' if cci[0]>0 else '(INCLUDES 0)'}")
    # also: drop the 2025-11 outlier, recompute clean net Sharpe (outlier dependence)
    m11=mo!="2025_11"
    cl_net_no11=clean[m11]-RT; tpy2=m11.sum()/span*365
    print(f"\n5. OUTLIER check (drop 2025-11): CLEAN net-taker Sharpe = {sharpe(cl_net_no11,tpy2):+.3f} (was {sharpe(cl_net,tpy):+.3f}); n={m11.sum()}")
    print("DONE_FEETIER.")
if __name__=="__main__": main()
