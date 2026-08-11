"""TAIL-GATED ENTRY + HOLDING backtest (cost-dominated-signal best practice) on lambda0.1 causal-demeaned yhat.
Captures the CUMULATIVE entry->exit move (not the 10-min window) -> per-trade edge can exceed the RT cost floor.

PRICE PATH: reconstruct per-month by telescoping y_600 on a ~600s-spaced subgrid (validated: node-incr std == y_600 std).
SIGNAL: causal-demeaned q50 (production CSV), sampled at the same nodes.
ENTRY (tail-gated): trailing rolling distribution of the signal (causal, <=t). Open LONG when signal >= top-(q)% quantile,
  SHORT when <= bottom-(q)% quantile. Gates q in {5%, 2.5%, 10%}.
HOLDING: once in, HOLD until (a) signal crosses to the OPPOSITE tail (flip), or (b) mean-reverts past a hysteresis band
  through ~0 (|signal| below an inner band on the wrong side), subject to MIN-HOLD; force-exit at MAX-HOLD.
MEASURE per gate, and LONG vs SHORT separately:
  per-trade GROSS cumulative edge (bps) = p(exit)-p(entry) signed by side; #trades; avg hold (nodes & min); turnover/day;
  gross Sharpe (per-trade, annualized); NET per-trade + NET Sharpe at maker (RT 2bps) and taker (RT 8bps).
Run LOCAL: python multi_asset/eval/tail_holding_backtest.py --csv exports/final_l01/y600_l01_alwaysEMA_walkforward.csv
"""
from __future__ import annotations
import numpy as np, argparse, csv as _csv
from collections import deque

def load(path):
    rows=list(_csv.DictReader(open(path)))
    ts=np.array([int(r["timestamp_us"]) for r in rows])
    mon=np.array([r["month"] for r in rows])
    qd=np.array([float(r["pred_q50_demean_raw"]) for r in rows])  # causal-demeaned yhat (raw log-ret units)
    y=np.array([float(r["target_raw"]) for r in rows])           # y_600 fwd return (raw)
    o=np.argsort(ts); return mon[o],ts[o],qd[o],y[o]

def month_nodes(tm,qm,ym):
    # 600s-spaced subgrid + telescoped price path
    idx=[0]; last=tm[0]
    for i in range(1,len(tm)):
        if tm[i]-last >= (600-90)*1_000_000: idx.append(i); last=tm[i]
    idx=np.array(idx)
    sig=qm[idx]; tnode=tm[idx]
    price=np.zeros(len(idx))
    for k in range(len(idx)-1): price[k+1]=price[k]+ym[idx[k]]  # p(node k+1)=p(node k)+y_600(node k)
    return tnode,sig,price

def trailing_quantiles(sig, ts, win_ns, qlo, qhi):
    # causal trailing quantile thresholds (<=t)
    n=len(sig); tl=np.full(n,np.nan); th=np.full(n,np.nan); dq=deque()
    for i in range(n):
        dq.append((ts[i],sig[i]))
        while dq and dq[0][0] < ts[i]-win_ns: dq.popleft()
        if len(dq)>=50:
            vals=np.fromiter((v for _,v in dq),float)
            tl[i]=np.quantile(vals,qlo); th[i]=np.quantile(vals,qhi)
    return tl,th

def backtest_month(tnode,sig,price,win_ns,gate,min_hold,max_hold):
    # gate = tail fraction. LONG if sig>=top-(gate); SHORT if sig<=bottom-(gate).
    # HOLD until: (a) opposite tail (flip), or (b) signal mean-reverts THROUGH the trailing MEDIAN (true reversal),
    #   subject to MIN-HOLD; force-exit at MAX-HOLD. This RIDES the move (does not exit just for leaving the tail).
    tl,th=trailing_quantiles(sig,tnode,win_ns,gate,1-gate)
    med,_=trailing_quantiles(sig,tnode,win_ns,0.5,0.5)  # trailing median (mean-revert reference)
    pos=0; entry_p=0.0; held=0
    trades=[]  # (side, gross_ret, hold_nodes)
    for i in range(len(sig)):
        s=sig[i]
        if pos==0:
            if not np.isnan(th[i]):
                if s>=th[i]: pos=+1; entry_p=price[i]; held=0
                elif s<=tl[i]: pos=-1; entry_p=price[i]; held=0
        else:
            held+=1
            flip = (pos==+1 and not np.isnan(tl[i]) and s<=tl[i]) or (pos==-1 and not np.isnan(th[i]) and s>=th[i])
            # mean-revert through median: long exits when sig drops below median; short exits when sig rises above median
            revert = (pos==+1 and not np.isnan(med[i]) and s<med[i]) or (pos==-1 and not np.isnan(med[i]) and s>med[i])
            do_exit = (held>=min_hold and (flip or revert)) or held>=max_hold
            if do_exit:
                gross=pos*(price[i]-entry_p); trades.append((pos,gross,held))
                if flip and held>=min_hold:
                    newpos=-pos
                    if (newpos==+1 and s>=th[i]) or (newpos==-1 and s<=tl[i]): pos=newpos; entry_p=price[i]; held=0
                    else: pos=0
                else: pos=0
    return trades

def summ(trades, span_days, rt_cost_bps_maker=2.0, rt_cost_bps_taker=8.0):
    if not trades: return None
    arr=np.array([t[1] for t in trades])*1e4  # bps cumulative gross
    sides=np.array([t[0] for t in trades]); holds=np.array([t[2] for t in trades])
    def block(mask,label):
        a=arr[mask]; h=holds[mask]
        if len(a)==0: return f"  {label:6s}: (no trades)"
        gross=a.mean(); sd=a.std()+1e-9; n=len(a)
        tpy=n/span_days*365
        shg=gross/sd*np.sqrt(tpy)
        nm=gross-rt_cost_bps_maker; nt=gross-rt_cost_bps_taker
        shm=nm/sd*np.sqrt(tpy); sht=nt/sd*np.sqrt(tpy)
        return (f"  {label:6s}: n={n:4d} edge={gross:+6.2f}bps hold={h.mean():4.1f}nd(~{h.mean()*10:.0f}min) "
                f"| Sgross={shg:+5.1f} | NETmaker {nm:+6.2f}(S{shm:+5.1f}) NETtaker {nt:+6.2f}(S{sht:+5.1f})")
    return "\n".join([block(np.ones(len(arr),bool),"ALL"),block(sides==+1,"LONG"),block(sides==-1,"SHORT")])

def main():
    ap=argparse.ArgumentParser(); ap.add_argument("--csv",default="exports/final_l01/y600_l01_alwaysEMA_walkforward.csv")
    ap.add_argument("--win",type=int,default=86400,help="trailing distribution window seconds (default 1 day)")
    a=ap.parse_args()
    mon,ts,qd,y=load(a.csv)
    # build nodes per month
    months=[];
    for M in sorted(set(mon)):
        m=mon==M; tnode,sig,price=month_nodes(ts[m],qd[m],y[m]); months.append((M,tnode,sig,price))
    span_days=(ts.max()-ts.min())/(86400*1e6)
    win_ns=a.win*1_000_000
    print(f"=== TAIL-GATED ENTRY + HOLDING backtest (lambda0.1 causal-demeaned yhat) ===")
    print(f"  {len(months)} months, span {span_days:.0f}d, trailing-dist window {a.win/3600:.0f}h. RT cost: maker 2bps, taker 8bps.")
    print(f"  PnL = cumulative price(exit)-price(entry), signed. Long top-tail / short bottom-tail.\n")
    for gate,gname in [(0.10,"+-10% (reference)"),(0.05,"+-5%"),(0.025,"+-2.5%")]:
        allt=[]
        for (M,tnode,sig,price) in months:
            allt += backtest_month(tnode,sig,price,win_ns,gate,min_hold=3,max_hold=36)
        print(f"--- GATE {gname} (min-hold 3nd~30min, max-hold 36nd~6h, exit on flip OR mean-revert-through-median) ---")
        s=summ(allt,span_days)
        print(s if s else "  (no trades)")
        # turnover/day
        if allt: print(f"  turnover: {len(allt)/span_days:.1f} trades/day")
        print()
    print("KEY: does per-trade GROSS edge exceed RT cost (maker 2 / taker 8) -> NET-POSITIVE? Watch LONG vs SHORT asymmetry.")
    print("DONE_TAILHOLD.")

if __name__=="__main__": main()
