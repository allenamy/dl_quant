"""ITEM 5 — BEST-PRACTICE TRADING SCHEME (single-asset BTC y_600, lambda0.1 trajectory).
Honest net-of-cost backtest implementing the item-5 design (beta unstable -> NOT magnitude sizing):
  * SIGN/RANK sizing: position in {-1,0,+1} from the SIGNAL sign (not beta-scaled magnitude).
  * CAUSAL sliding-window demean of q50 (<=t) -> removes persistent long/short bias.
  * CONFIDENCE GATE: only OPEN when |demeaned-signal-rank| in the top tail (|z| >= T_open over a trailing window);
    HYSTERESIS: close only when signal weakens past T_close (< T_open) -> low flip rate.
  * MIN-HOLD / MAX-HOLD: hold >= min_hold bars; force-exit at max_hold (caps overlap & churn).
  * NET-OF-COST: per-leg fee swept over realistic retail maker/taker scenarios. Sharpe on a per-DECISION basis.
Predictions read from the production CSV (raw bps). Reports: gross IC of traded set, turnover, gross/net Sharpe,
ann-return, % time in market, vs the cost floor. Honest verdict on tradeability.
Run LOCAL: python multi_asset/eval/trading_scheme_l01.py --csv exports/final_l01/y600_l01_alwaysEMA_walkforward.csv
"""
from __future__ import annotations
import numpy as np, argparse, csv as _csv
from collections import deque

def load_csv(path):
    mons=[];ts=[];q=[];qd=[];y=[]
    with open(path) as f:
        r=_csv.DictReader(f)
        for row in r:
            mons.append(row["month"]); ts.append(int(row["timestamp_us"]))
            q.append(float(row["pred_q50_raw"])); qd.append(float(row["pred_q50_demean_raw"])); y.append(float(row["target_raw"]))
    o=np.argsort(np.array(ts))
    return (np.array(mons)[o], np.array(ts)[o], np.array(q)[o]*1e4, np.array(qd)[o]*1e4, np.array(y)[o]*1e4)  # -> bps

def trailing_z(sig, ts, win_ns):
    # causal z-score of signal over trailing time window (for confidence gating, <=t)
    out=np.zeros_like(sig); dq=deque(); s=0.0; s2=0.0; n=0
    for i in range(len(sig)):
        dq.append((ts[i],sig[i])); s+=sig[i]; s2+=sig[i]*sig[i]; n+=1
        while dq and dq[0][0] < ts[i]-win_ns:
            t0,v0=dq.popleft(); s-=v0; s2-=v0*v0; n-=1
        if n>30:
            mu=s/n; var=max(s2/n-mu*mu,1e-12); out[i]=(sig[i]-mu)/np.sqrt(var)
        else: out[i]=0.0
    return out

def run(sigz, y, fee_per_leg, T_open, T_close, min_hold, max_hold):
    # sigz = causal confidence z of the (demeaned) signal; trade sign(sigz) gated by |sigz|
    pos=0; held=0; pnl=[]; fees=0.0; trades=0; in_mkt=0
    npos=len(sigz)
    for i in range(npos):
        z=sigz[i]
        # realize PnL of CURRENT position over this bar's forward return y[i] (y is the t->t+600 return)
        if pos!=0:
            pnl.append(pos*y[i]); in_mkt+=1; held+=1
        else:
            pnl.append(0.0)
        # decide next position (decision uses info <=t; y[i] already realized above for the existing pos)
        want = (+1 if z>=T_open else (-1 if z<=-T_open else 0))
        if pos==0:
            if want!=0: pos=want; fees+=fee_per_leg; trades+=1; held=0
        else:
            weak = abs(z) < T_close
            flip = (want!=0 and np.sign(want)!=np.sign(pos))
            if held<min_hold and not flip:
                pass  # honor min-hold (unless a hard flip)
            elif flip:
                pos=want; fees+=2*fee_per_leg; trades+=2; held=0  # close+open
            elif weak or held>=max_hold:
                pos=0; fees+=fee_per_leg; trades+=1; held=0  # close
    pnl=np.array(pnl)
    gross=pnl.sum(); net=gross-fees
    # per-decision Sharpe: use per-bar pnl net of amortized fee
    per_bar_net = pnl.copy()
    # amortize fees onto the bars where trades happened is complex; use aggregate Sharpe on net daily-equivalent
    # Sharpe on the in-market bar returns (net): subtract avg fee per in-market bar
    nz = pnl[pnl!=0]
    if len(nz)>2 and nz.std()>1e-9:
        net_mean = (gross-fees)/max(in_mkt,1)
        sharpe = net_mean/ (nz.std()) * np.sqrt(52560)  # 52560 = 600s bars/yr (10-min decisions)
    else: sharpe=0.0
    frac_mkt=in_mkt/npos
    return dict(gross=gross,net=net,fees=fees,trades=trades,frac_mkt=frac_mkt,sharpe=sharpe,n=npos)

def main():
    ap=argparse.ArgumentParser(); ap.add_argument("--csv",default="exports/final_l01/y600_l01_alwaysEMA_walkforward.csv")
    ap.add_argument("--confwin",type=int,default=86400,help="trailing conf-z window seconds (1 day)")
    a=ap.parse_args()
    mons,ts,q,qd,y = load_csv(a.csv)
    print(f"=== TRADING SCHEME (lambda0.1, {len(y)} decisions, {len(set(mons))} months) ===")
    print(f"  raw q50 bps: mean={q.mean():+.3f} std={q.std():.3f} | demeaned: mean={qd.mean():+.3f} std={qd.std():.3f} | y bps: mean={y.mean():+.3f} std={y.std():.3f}")
    # gross IC reference
    ic=np.corrcoef(qd,y)[0,1]
    absy=np.abs(y)
    print(f"  gross DENSE IC (demeaned q50 vs y) = {ic:+.4f}")
    print(f"  ORACLE sign(y) gross (no fee): mean|y|={absy.mean():.3f}bps Sharpe={absy.mean()/absy.std()*np.sqrt(52560):.1f} (hindsight upper bd)")
    # confidence z of demeaned signal (causal)
    sigz=trailing_z(qd, ts, a.confwin*1_000_000)
    # cost scenarios (per-leg bps): retail maker 2.0, realistic maker 2.9 (70/30), mixed 3.5, taker 5.0
    fee_legs=[(2.0,"pure maker (2.0/leg=4.0 RT)"),(2.9,"realistic maker (5.8 RT)"),(3.5,"mixed maker/taker (7.0 RT)"),(5.0,"pure taker (10.0 RT)")]
    # threshold grid (confidence gate + hysteresis + holds)
    grid=[]
    for T_open in [0.5,1.0,1.5,2.0]:
        for T_close in [0.2,0.5]:
            if T_close>=T_open: continue
            for min_hold in [1,3]:
                for max_hold in [6,18]:
                    grid.append((T_open,T_close,min_hold,max_hold))
    print(f"\n  {'fee_leg':>26s} | {'T_o/T_c/mnH/mxH':>16s} | {'frac_mkt':>8s} {'trades':>6s} {'grossbps':>9s} {'netbps':>8s} {'Sharpe':>7s}")
    best={}
    for fee,fname in fee_legs:
        bestrow=None
        for (To,Tc,mnH,mxH) in grid:
            r=run(sigz,y,fee,To,Tc,mnH,mxH)
            score=r["net"]
            if bestrow is None or score>bestrow[0]: bestrow=(score,(To,Tc,mnH,mxH),r)
        _,(To,Tc,mnH,mxH),r=bestrow
        print(f"  {fname:>26s} | {To:.1f}/{Tc:.1f}/{mnH}/{mxH:>2} | {r['frac_mkt']:8.3f} {r['trades']:6d} {r['gross']:+9.0f} {r['net']:+8.0f} {r['sharpe']:+7.2f}")
        best[fname]=r
    # ---- DECISIVE clean economics on NON-OVERLAPPING decisions (no overlap inflation) ----
    HZ=600*1_000_000; keep=[]; last=-1e18
    for i in range(len(ts)):
        if ts[i]-last>=HZ: keep.append(i); last=ts[i]
    keep=np.array(keep); qn=qd[keep]; yn=y[keep]
    icn=np.corrcoef(qn,yn)[0,1]
    pt=np.sign(qn)*yn  # trade-every per-trade gross edge (bps)
    dpy=52560
    print(f"\n=== DECISIVE non-overlap economics ({len(keep)} non-overlapping 600s decisions) ===")
    print(f"  non-overlap IC={icn:+.4f} | trade-every per-trade GROSS edge={pt.mean():+.3f}bps (std {pt.std():.1f}) | gross Sharpe={pt.mean()/pt.std()*np.sqrt(dpy):+.2f}")
    for fee,fname in [(4.0,"pure maker RT"),(5.8,"realistic maker RT"),(10.0,"pure taker RT")]:
        print(f"    NET @ {fname:22s} ({fee}bps): per-trade {pt.mean()-fee:+.2f}bps  Sharpe={(pt.mean()-fee)/pt.std()*np.sqrt(dpy):+.1f}")
    for tq in [0.5,0.8,0.9]:
        thr=np.quantile(np.abs(qn),tq); m=np.abs(qn)>=thr; ptg=np.sign(qn[m])*yn[m]
        print(f"    CONF-GATE top {(1-tq)*100:.0f}% |sig|: n={m.sum()} edge={ptg.mean():+.2f}bps net@maker4={ptg.mean()-4.0:+.2f} net@taker10={ptg.mean()-10.0:+.2f}")
    print(f"\n  VERDICT: per-trade GROSS edge {pt.mean():+.2f}bps (gated up to ~+2bps) << RT cost 4-10bps -> COST-DOMINATED.")
    print(f"  Signal REAL (gross Sharpe ~4, IC ~0.05) but NOT tradeable net-of-cost. Research-stage. Same as single-asset BTC y_600.")
    print("DONE_TRADING.")

if __name__=="__main__": main()
