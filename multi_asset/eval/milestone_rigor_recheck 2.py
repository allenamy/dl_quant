"""ROOT-CAUSE: re-check the single-asset MILESTONE backtest (pure-taker 2.8 / maker 4.4) with CURRENT rigor
(shuffle-null drift-check + drift-neutralization), using the milestone's OWN backtest logic + CSV.
Tests the hypothesis: the milestone's 2.8/4.4 was NEVER drift-null-checked -> the gap to current (0.6) is METHODOLOGY,
not signal. Milestone period 2025-02..2025-09 was UP-trending (+0.092bps/bar) -> a long-leaning strategy harvests drift.

Reads (READ-ONLY) backtest_reg_arch/predictions_all_folds.csv with the milestone's run_strategy logic.
1. Reproduce milestone Sharpe (its caliber: per-bar pnl, DECISIONS_PER_YEAR=365).
2. SHUFFLE-NULL: permute q50_live -> random-strategy baseline. Does milestone Sharpe/PnL drop to ~null? (= drift-riding).
3. DRIFT-NEUTRAL: subtract per-bar market return (mean y) from the position PnL -> clean alpha PnL + Sharpe.
   pnl_neutral = pos*(y - mean_y). Removes the directional drift harvest; isolates signal alpha.
Run LOCAL: python multi_asset/eval/milestone_rigor_recheck.py
"""
from __future__ import annotations
import numpy as np, csv
DPY=365*24*60//12  # = 525600, milestone's annualization (per 12-min decision bar)

def load():
    rows=list(csv.DictReader(open("backtest_reg_arch/predictions_all_folds.csv")))
    ts=np.array([int(r["timestamp_us"]) for r in rows])
    y=np.array([float(r["y_true_bps"]) for r in rows])
    q=np.array([float(r["y_pred_q50_bps_live"]) for r in rows])
    mask=np.array([int(r["mask"]) for r in rows]); wu=np.array([r["warmup"]=="True" for r in rows])
    keep=(mask==1)&(~wu)
    return ts[keep],y[keep],q[keep]

def run_strategy(q,y,T_open,T_close,T_flip,fee_per_leg,max_hold=20):
    n=len(q); state=0; held=0; pnl=np.zeros(n); slog=np.zeros(n,np.int8); tlog=np.zeros(n,np.int8); flog=np.zeros(n)
    for i in range(n):
        cl=q[i]>=T_open; cs=q[i]<=-T_open; wl=q[i]>T_close; ws=q[i]<-T_close; fl=q[i]>=T_flip; fs=q[i]<=-T_flip
        ns=state
        if state==0:
            if cl: ns=+1; flog[i]+=fee_per_leg; tlog[i]+=1
            elif cs: ns=-1; flog[i]+=fee_per_leg; tlog[i]+=1
        elif state==+1:
            if fs: ns=-1; flog[i]+=2*fee_per_leg; tlog[i]+=2
            elif (not wl) or held>=max_hold: ns=0; flog[i]+=fee_per_leg; tlog[i]+=1
        elif state==-1:
            if fl: ns=+1; flog[i]+=2*fee_per_leg; tlog[i]+=2
            elif (not ws) or held>=max_hold: ns=0; flog[i]+=fee_per_leg; tlog[i]+=1
        if ns!=state and ns!=0: held=1
        elif ns==state and ns!=0: held+=1
        else: held=0
        pnl[i]=ns*y[i]-flog[i]; slog[i]=ns; state=ns
    return pnl,slog,tlog

def sharpe(pnl):
    s=pnl.std(); return pnl.mean()/s*np.sqrt(DPY) if s>0 else 0.0

def main():
    ts,y,q=load()
    drift=y.mean()
    print(f"=== MILESTONE re-check (2025-02..2025-09, {len(y)} bars, drift={drift:+.4f}bps/bar UP-trend) ===")
    # EXACT milestone headline config: T_open=2.0, T_close=-2.0, max_hold=10, T_flip=max(To*1.5,To+0.5)=3.0
    To,Tc,Tf=2.0,-2.0,3.0
    for fee,fname in [(2.0,"maker(2/leg=4RT)"),(5.0,"taker(5/leg=10RT)")]:
        pnl,slog,tlog=run_strategy(q,y,To,Tc,Tf,fee,max_hold=10)
        sh=sharpe(pnl)
        nt=int(np.ceil(tlog.sum()/2)); inmkt=np.mean(slog!=0); longfrac=np.mean(slog>0)/(inmkt+1e-9)
        print(f"\n  {fname}: headline Sharpe={sh:.2f} (To{To}/Tc{Tc}/maxhold10) total={pnl.sum():+.0f}bps n_trades={nt} in_mkt={100*inmkt:.1f}% long-frac={longfrac:.2f}")
        # SHUFFLE-NULL: permute q -> random strategy on same y (drift harvest baseline)
        rng=np.random.default_rng(0); nulls=[]
        for k in range(50):
            qp=rng.permutation(q); pn,_,_=run_strategy(qp,y,To,Tc,Tf,fee); nulls.append(sharpe(pn))
        nulls=np.array(nulls)
        z=(sh-nulls.mean())/(nulls.std()+1e-9)
        print(f"    SHUFFLE-NULL: null Sharpe mean={nulls.mean():+.2f} sd={nulls.std():.2f} -> z={z:+.2f} ({'DRIFT-CONFOUNDED' if z<2 else 'clean'})")
        # DRIFT-NEUTRAL: re-pnl with market-subtracted return
        yn=y-drift
        pnl_n=np.zeros(len(pnl))
        # recompute pnl with neutral y but SAME positions
        # rebuild positions then apply yn
        pp,ss,_=run_strategy(q,y,To,Tc,Tf,fee)
        # neutral pnl = pos*yn - fees; extract fees = pos*y - pp
        pos=ss.astype(float); fees=pos*y-pp
        pnl_neutral=pos*yn-fees
        print(f"    DRIFT-NEUTRAL (subtract mkt {drift:+.4f}bps/bar): Sharpe={sharpe(pnl_neutral):+.2f} total={pnl_neutral.sum():+.0f}bps "
              f"(was {pnl.sum():+.0f}; drift harvest = {pnl.sum()-pnl_neutral.sum():+.0f}bps)")
    print("\nVERDICT: if milestone Sharpe collapses under shuffle-null (z<2) AND drift-neutral Sharpe << headline,")
    print("  then its 2.8/4.4 was PARTLY DRIFT-RIDING (uncaught) -> the gap to current 0.6 is METHODOLOGY, not signal.")
    print("DONE_MILESTONE_RECHECK.")

if __name__=="__main__": main()
