"""TAKER-OPTIMIZED tail+holding sweep on REAL perp book-mid (short-side focus).
Goal: longer holds riding bigger cumulative moves so per-trade GROSS edge EXCEEDS ~8bps taker RT.

Loads real perp mid ONCE per month (cached), maps to prediction nodes (<=t, causal), then sweeps:
  * gate (tail fraction): 0.10, 0.05, 0.025, 0.01
  * exit rule = "hold-while-persists": stay SHORT until signal mean-reverts past an EXIT quantile that is
    WIDER (closer to median or beyond) -> rides the trend. exit_q in {median(0.5), 0.6, 0.7} of trailing dist.
  * min_hold in {3, 6, 12, 24} nodes (~30min..4h)
  * max_hold in {36, 72, 144} nodes (~6h..24h)
Per config (REAL price, short-side): per-trade GROSS edge (bps), #trades, avg hold, trades/day,
  NET-TAKER edge + NET-TAKER annualized Sharpe (RT 8bps), and NET-maker (RT 2bps) for reference.
Reports the TAKER-Sharpe-MAX config. Sharpe = edge/sd * sqrt(n/span_days*365).
Run on SERVER: PYTHONPATH=. python multi_asset/eval/tail_holding_taker_sweep.py --csv <prod.csv>
"""
from __future__ import annotations
import numpy as np, argparse, csv as _csv, gzip, os
from collections import deque
from datetime import datetime, timezone, timedelta

BOOK="/mnt/storage/btcusdt_copy_2023-01-01_2026-05-31/dl-tardis/book_snapshot_25"; VENUE="binance-futures"

def load_csv(path):
    rows=list(_csv.DictReader(open(path)))
    ts=np.array([int(r["timestamp_us"]) for r in rows]); mon=np.array([r["month"] for r in rows])
    qd=np.array([float(r["pred_q50_demean_raw"]) for r in rows]); o=np.argsort(ts)
    return mon[o],ts[o],qd[o]

def day_list(ts):
    t0=datetime.fromtimestamp(ts.min()/1e6,tz=timezone.utc).date(); t1=datetime.fromtimestamp(ts.max()/1e6,tz=timezone.utc).date()
    out=[]; d=t0
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

def node_mid(node_ts):
    TS=[];MID=[]
    for d in day_list(node_ts):
        r=load_day(d)
        if r: TS.append(r[0]); MID.append(r[1])
    if not TS: return None
    TS=np.concatenate(TS);MID=np.concatenate(MID);o=np.argsort(TS);TS=TS[o];MID=MID[o]
    idx=np.searchsorted(TS,node_ts,side="right")-1; nm=np.full(len(node_ts),np.nan); v=idx>=0; nm[v]=MID[idx[v]]
    gap=np.full(len(node_ts),1e18); gap[v]=node_ts[v]-TS[idx[v]]; nm[gap>5_000_000]=np.nan
    return nm

def make_nodes(tm,qm):
    idx=[0]; last=tm[0]
    for i in range(1,len(tm)):
        if tm[i]-last>=(600-90)*1_000_000: idx.append(i); last=tm[i]
    idx=np.array(idx); return tm[idx],qm[idx]

def tq(sig,tn,win,qs):
    # compute multiple trailing quantiles at once: qs = list of quantile levels
    n=len(sig); outs=[np.full(n,np.nan) for _ in qs]; dq=deque()
    for i in range(n):
        dq.append((tn[i],sig[i]))
        while dq and dq[0][0]<tn[i]-win: dq.popleft()
        if len(dq)>=50:
            v=np.fromiter((x for _,x in dq),float)
            for j,q in enumerate(qs): outs[j][i]=np.quantile(v,q)
    return outs

def short_backtest(tn,sig,mid,tl,exitq,min_hold,max_hold):
    # SHORT only: enter when sig<=tl (bottom tail); HOLD while sig stays below exitq (persists); exit when sig>=exitq or max_hold
    pos=0;ep=0.0;held=0;tr=[]
    for i in range(len(sig)):
        s=sig[i]; m=mid[i]
        if np.isnan(m):
            if pos!=0: held+=1
            continue
        if pos==0:
            if not np.isnan(tl[i]) and s<=tl[i]: pos=-1; ep=m; held=0
        else:
            held+=1
            revert = not np.isnan(exitq[i]) and s>=exitq[i]
            if (held>=min_hold and revert) or held>=max_hold:
                tr.append((np.log(ep/m)*1e4, held)); pos=0  # short gross bps = log(entry/exit)
    return tr

def main():
    ap=argparse.ArgumentParser(); ap.add_argument("--csv",default="exports/final_l01/y600_l01_alwaysEMA_walkforward.csv")
    ap.add_argument("--win",type=int,default=86400); ap.add_argument("--maker",type=float,default=2.0); ap.add_argument("--taker",type=float,default=8.0)
    a=ap.parse_args(); win=a.win*1_000_000
    mon,ts,qd=load_csv(a.csv); span_days=(ts.max()-ts.min())/(86400*1e6)
    # precompute per-month nodes, mid, and the quantile series we need
    GATES=[0.10,0.05,0.025,0.01]; EXITQS=[0.5,0.6,0.7]
    qlevels=sorted(set(GATES+EXITQS))
    months=[]
    print(f"=== loading real perp mid per month (once) ===")
    for M in sorted(set(mon)):
        m=mon==M; tn,sig=make_nodes(ts[m],qd[m]); mid=node_mid(tn)
        if mid is None: print(f"  {M}: no book"); continue
        qser=dict(zip(qlevels, tq(sig,tn,win,qlevels)))
        months.append((M,tn,sig,mid,qser)); print(f"  {M}: nodes={len(tn)} midcov={np.mean(~np.isnan(mid)):.2f}")
    print(f"\n=== TAKER-optimized SHORT sweep (REAL price, RT taker {a.taker}bps / maker {a.maker}bps) ===")
    print(f"{'gate':>6s} {'exitq':>5s} {'mnH':>4s} {'mxH':>4s} | {'n':>5s} {'tr/d':>5s} {'hold_nd':>7s} {'edge':>7s} | {'NETtak':>7s} {'Stak':>6s} | {'NETmak':>7s} {'Smak':>6s}")
    results=[]
    for g in GATES:
        for eq in EXITQS:
            for mnH in [3,6,12,24]:
                for mxH in [36,72,144]:
                    if mxH<mnH: continue
                    alltr=[]
                    for (M,tn,sig,mid,qser) in months:
                        tl=qser[g]; exq=qser[eq]
                        alltr += short_backtest(tn,sig,mid,tl,exq,mnH,mxH)
                    if len(alltr)<30: continue
                    e=np.array([t[0] for t in alltr]); h=np.array([t[1] for t in alltr])
                    n=len(e); sd=e.std()+1e-9; tpy=n/span_days*365; trd=n/span_days
                    edge=e.mean(); nett=edge-a.taker; netm=edge-a.maker
                    Stak=nett/sd*np.sqrt(tpy); Smak=netm/sd*np.sqrt(tpy)
                    results.append((Stak,g,eq,mnH,mxH,n,trd,h.mean(),edge,nett,netm,Smak))
    # print top by taker Sharpe + a few references
    results.sort(reverse=True)
    for r in results[:12]:
        Stak,g,eq,mnH,mxH,n,trd,hold,edge,nett,netm,Smak=r
        print(f"{g:6.3f} {eq:5.2f} {mnH:4d} {mxH:4d} | {n:5d} {trd:5.1f} {hold:7.1f} {edge:+7.2f} | {nett:+7.2f} {Stak:+6.2f} | {netm:+7.2f} {Smak:+6.2f}")
    if results:
        best=results[0]
        print(f"\n=== TAKER-Sharpe-MAX: gate {best[1]} exitq {best[2]} minH {best[3]} maxH {best[4]} ===")
        print(f"  per-trade GROSS edge={best[8]:+.2f}bps | NET-taker={best[9]:+.2f}bps | trades/day={best[6]:.1f} | avg hold={best[7]:.1f}nd (~{best[7]*10:.0f}min)")
        print(f"  NET-TAKER annualized Sharpe={best[0]:+.2f}  (vs single-asset milestone pure-taker 2.8)")
        verdict="NET-POSITIVE at taker" if best[9]>0 else "still net-NEGATIVE at taker"
        print(f"  VERDICT: {verdict}")
    print("DONE_TAKERSWEEP.")

if __name__=="__main__": main()
