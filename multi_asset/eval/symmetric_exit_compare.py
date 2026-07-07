"""PRINCIPLED symmetric long-short, 4 EXIT rules, real perp price, drift-neutral throughout.
Critiques addressed: (1) short-only was regime-fitting (signal symmetric) -> test SYMMETRIC LS. (2) opposite-tail exit
holds ~40min >> 10-min horizon -> rides drift -> compare exits MATCHED to horizon.

ENTRY: long if causal-demeaned yhat >= top-tail (trailing dist), short if <= bottom-tail. gate=2.5% (best from sweep).
EXITS:
  (a) SIGNAL-DECAY : close when |yhat| falls back inside the trailing 50<->tail band (signal left the tail toward 0).
  (b) FIXED-HORIZON: hold exactly H nodes (~600s = 1 node) then close.
  (c) HOLD-WHILE-PERSISTS: stay while yhat stays in its tail; close when it leaves the tail.
  (d) OPPOSITE-TAIL : close only on opposite tail or max-hold (baseline; the old one).
PnL = real perp log(mid) signed by side. DRIFT-NEUTRAL = per-trade pnl minus (random-position drift over same hold)
  = pnl - side*(node_drift*held). For long, drift helps in up-market; for short, in down-market; subtracting isolates alpha.
REPORT per (exit x side): per-trade gross, avg hold, n, NET Sharpe @ RT {3.4, 2.0, 8.0}, and DRIFT-NEUTRAL net @ 3.4.
Shuffle-null (permute yhat) on the best drift-neutral config. Exact Sharpe = mean/sd*sqrt(n/span*365).
Run on SERVER: PYTHONPATH=. python multi_asset/eval/symmetric_exit_compare.py
"""
from __future__ import annotations
import numpy as np, argparse, csv as _csv, gzip, os
from collections import deque
from datetime import datetime, timezone, timedelta
BOOK="/mnt/storage/btcusdt_copy_2023-01-01_2026-05-31/dl-tardis/book_snapshot_25"; VENUE="binance-futures"
def load_csv(p):
    rows=list(_csv.DictReader(open(p)))
    ts=np.array([int(r["timestamp_us"]) for r in rows]); mon=np.array([r["month"] for r in rows])
    qd=np.array([float(r["pred_q50_demean_raw"]) for r in rows]); o=np.argsort(ts); return mon[o],ts[o],qd[o]
def day_list(ts):
    t0=datetime.fromtimestamp(ts.min()/1e6,tz=timezone.utc).date(); t1=datetime.fromtimestamp(ts.max()/1e6,tz=timezone.utc).date()
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
def node_mid(node_ts):
    TS=[];MID=[]
    for d in day_list(node_ts):
        r=load_day(d)
        if r: TS.append(r[0]);MID.append(r[1])
    if not TS: return None
    TS=np.concatenate(TS);MID=np.concatenate(MID);o=np.argsort(TS);TS=TS[o];MID=MID[o]
    idx=np.searchsorted(TS,node_ts,side="right")-1; nm=np.full(len(node_ts),np.nan); v=idx>=0; nm[v]=MID[idx[v]]
    gap=np.full(len(node_ts),1e18); gap[v]=node_ts[v]-TS[idx[v]]; nm[gap>5_000_000]=np.nan
    return nm
def make_nodes(tm,qm):
    idx=[0];last=tm[0]
    for i in range(1,len(tm)):
        if tm[i]-last>=(600-90)*1_000_000: idx.append(i); last=tm[i]
    idx=np.array(idx); return tm[idx],qm[idx]
def tq(sig,tn,win,ql,qh):
    n=len(sig);tl=np.full(n,np.nan);th=np.full(n,np.nan);md=np.full(n,np.nan);dq=deque()
    for i in range(n):
        dq.append((tn[i],sig[i]))
        while dq and dq[0][0]<tn[i]-win: dq.popleft()
        if len(dq)>=50:
            v=np.fromiter((x for _,x in dq),float); tl[i]=np.quantile(v,ql); th[i]=np.quantile(v,qh); md[i]=np.quantile(v,0.5)
    return tl,th,md
def backtest(tn,sig,mid,gate,win,exit_rule,H=1,max_hold=36):
    tl,th,md=tq(sig,tn,win,gate,1-gate)
    node_dr=np.full(len(mid),np.nan)
    vmid=mid[~np.isnan(mid)]
    nd=(np.log(vmid[-1]/vmid[0])/(len(vmid)-1)) if len(vmid)>2 else 0.0  # avg per-node log drift this month
    pos=0;ep=0.0;held=0;tr=[]  # (side, gross_bps, drift_bps, hold)
    for i in range(len(sig)):
        s=sig[i]; m=mid[i]
        if np.isnan(m):
            if pos!=0: held+=1
            continue
        if pos==0:
            if not np.isnan(th[i]):
                if s>=th[i]: pos=+1; ep=m; held=0
                elif s<=tl[i]: pos=-1; ep=m; held=0
        else:
            held+=1
            ex=False
            if exit_rule=="decay":   ex = (pos==+1 and s<md[i]) or (pos==-1 and s>md[i])  # back toward median
            elif exit_rule=="horizon": ex = held>=H
            elif exit_rule=="persist": ex = (pos==+1 and s<th[i]) or (pos==-1 and s>tl[i])  # left the tail
            elif exit_rule=="opposite": ex = (pos==+1 and s<=tl[i]) or (pos==-1 and s>=th[i])
            if ex or held>=max_hold:
                gross=pos*np.log(m/ep)*1e4
                drift=pos*(nd*held)*1e4  # drift a random same-side position earns over the hold
                tr.append((pos,gross,drift,held)); pos=0
    return tr
def stats(tr, span, label, rts=(3.4,2.0,8.0)):
    if len(tr)<20: return f"  {label:26s}: n={len(tr)} (too few)"
    g=np.array([t[1] for t in tr]); dr=np.array([t[2] for t in tr]); h=np.array([t[3] for t in tr])
    n=len(g); tpy=n/span*365; sd=g.std()+1e-12; clean=g-dr; sdc=clean.std()+1e-12
    def S(x): return x.mean()/(x.std()+1e-12)*np.sqrt(tpy)
    nets=" ".join(f"RT{rt}:{ (g.mean()-rt):+4.1f}(S{S(g-rt):+4.1f})" for rt in rts)
    return (f"  {label:26s}: n={n:4d} hold={h.mean():4.1f}nd edge={g.mean():+5.2f} | {nets} | "
            f"CLEAN-edge={clean.mean():+5.2f} CLEAN-net@3.4={clean.mean()-3.4:+4.1f}(S{S(clean-3.4):+4.1f})")
def main():
    ap=argparse.ArgumentParser(); ap.add_argument("--csv",default="exports/final_l01/y600_l01_alwaysEMA_walkforward.csv")
    ap.add_argument("--gate",type=float,default=0.025); ap.add_argument("--win",type=int,default=86400)
    a=ap.parse_args(); win=a.win*1_000_000
    mon,ts,qd=load_csv(a.csv); span=(ts.max()-ts.min())/(86400*1e6)
    print(f"=== SYMMETRIC L-S, 4 exits, real perp, gate +-{a.gate*100:.1f}%, span {span:.0f}d (CLEAN=drift-neutral) ===",flush=True)
    cache=[]
    for M in sorted(set(mon)):
        m=mon==M; tn,sig=make_nodes(ts[m],qd[m]); mid=node_mid(tn)
        if mid is None: print(f"  {M}: no book",flush=True); continue
        cache.append((M,tn,sig,mid)); print(f"  {M}: nodes={len(tn)} midcov={np.mean(~np.isnan(mid)):.2f}",flush=True)
    exits=[("decay","SIGNAL-DECAY"),("horizon","FIXED-HORIZON(1nd~600s)"),("persist","HOLD-WHILE-PERSISTS"),("opposite","OPPOSITE-TAIL")]
    best=None
    for ex,exname in exits:
        allt=[]
        for (M,tn,sig,mid) in cache: allt+=backtest(tn,sig,mid,a.gate,win,ex,H=1)
        L=[t for t in allt if t[0]==+1]; S=[t for t in allt if t[0]==-1]
        print(f"\n-- EXIT {exname} --",flush=True)
        print(stats(allt,span,"BOTH"),flush=True)
        print(stats(L,span,"LONG"),flush=True)
        print(stats(S,span,"SHORT"),flush=True)
        # track best by CLEAN net Sharpe @3.4 on BOTH
        if len(allt)>=20:
            g=np.array([t[1] for t in allt]); dr=np.array([t[2] for t in allt]); clean=g-dr
            tpy=len(g)/span*365; Sc=(clean.mean()-3.4)/(clean.std()+1e-12)*np.sqrt(tpy)
            if best is None or Sc>best[0]: best=(Sc,ex,exname)
    # shuffle-null on best exit (BOTH, drift-neutral net@3.4)
    if best:
        Sc,ex,exname=best
        print(f"\n=== BEST drift-neutral net@3.4 = {exname} (S{Sc:+.2f}) -> shuffle-null ===",flush=True)
        rng=np.random.default_rng(0); nulls=[]
        for k in range(40):
            allt=[]
            for (M,tn,sig,mid) in cache: allt+=backtest(tn,rng.permutation(sig),mid,a.gate,win,ex,H=1)
            if len(allt)>=20:
                g=np.array([t[1] for t in allt]); dr=np.array([t[2] for t in allt]); nulls.append((g-dr).mean())
        nulls=np.array(nulls)
        allt=[]
        for (M,tn,sig,mid) in cache: allt+=backtest(tn,sig,mid,a.gate,win,ex,H=1)
        g=np.array([t[1] for t in allt]); dr=np.array([t[2] for t in allt]); real=(g-dr).mean()
        print(f"  REAL clean edge={real:+.2f}bps | NULL mean={nulls.mean():+.2f} sd={nulls.std():.2f} z={(real-nulls.mean())/(nulls.std()+1e-9):+.2f}",flush=True)
    print("DONE_SYMEXIT.",flush=True)
if __name__=="__main__": main()
