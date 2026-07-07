"""POST-CHECKLIST on the ACTUAL winner: SHORT-ONLY gate +-2.5% (real perp mid).
Raw +4.44bps/maker S+1.5 is PROVISIONAL until null + drift-neutral clear it.
1. SHUFFLE-NULL: permute yhat 50x -> random-short null mean + z (the +-10% short was 50% drift).
2. DRIFT-NEUTRAL: per-trade short pnl minus the drift a random short earns over the same hold -> clean edge + clean maker Sharpe.
3. PER-MONTH: n per month, edge per month, # positive, worst month (n=540 pooled is small).
Reuses real-price book loader. Run on SERVER: PYTHONPATH=. python multi_asset/eval/short25_postcheck.py
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
        if r: TS.append(r[0]); MID.append(r[1])
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
def tq(sig,tn,win,ql):
    n=len(sig);tl=np.full(n,np.nan);md=np.full(n,np.nan);dq=deque()
    for i in range(n):
        dq.append((tn[i],sig[i]))
        while dq and dq[0][0]<tn[i]-win: dq.popleft()
        if len(dq)>=50:
            v=np.fromiter((x for _,x in dq),float); tl[i]=np.quantile(v,ql); md[i]=np.quantile(v,0.5)
    return tl,md
def short_bt(tn,sig,mid,gate,win,min_hold=3,max_hold=36,return_holds=False):
    tl,md=tq(sig,tn,win,gate)
    pos=0;ep=0.0;held=0;tr=[]; ei=0
    for i in range(len(sig)):
        s=sig[i]; m=mid[i]
        if np.isnan(m):
            if pos!=0: held+=1
            continue
        if pos==0:
            if not np.isnan(tl[i]) and s<=tl[i]: pos=-1; ep=m; ei=i; held=0
        else:
            held+=1
            revert = not np.isnan(md[i]) and s>md[i]
            if (held>=min_hold and revert) or held>=max_hold:
                g=np.log(ep/m)*1e4; tr.append((g,held,ei,i)); pos=0
    return tr
def main():
    ap=argparse.ArgumentParser(); ap.add_argument("--csv",default="exports/final_l01/y600_l01_alwaysEMA_walkforward.csv")
    ap.add_argument("--gate",type=float,default=0.025); ap.add_argument("--win",type=int,default=86400)
    a=ap.parse_args(); win=a.win*1_000_000
    mon,ts,qd=load_csv(a.csv); span=(ts.max()-ts.min())/(86400*1e6)
    print(f"=== SHORT-ONLY gate +-{a.gate*100:.1f}% POST-CHECKLIST (real perp mid) ===",flush=True)
    cache=[]
    for M in sorted(set(mon)):
        m=mon==M; tn,sig=make_nodes(ts[m],qd[m]); mid=node_mid(tn)
        if mid is None: print(f"  {M}: no book",flush=True); continue
        cache.append((M,tn,sig,mid)); print(f"  {M}: nodes={len(tn)} midcov={np.mean(~np.isnan(mid)):.2f}",flush=True)
    # real run + per-month + build a price series per month for drift baseline
    allg=[]; permonth=[]
    drift_comp_all=[]; trade_month=[]
    for (M,tn,sig,mid) in cache:
        tr=short_bt(tn,sig,mid,a.gate,win)
        gs=[t[0] for t in tr]
        # drift component per trade: market log-move over same hold (a random short earns -mkt; baseline = -avg_node_drift*held)
        # avg per-node log drift this month from mid:
        vmid=mid[~np.isnan(mid)]
        node_dr=np.log(vmid[-1]/vmid[0])/(len(vmid)-1) if len(vmid)>2 else 0.0
        dcs=[-(node_dr*t[1])*1e4 for t in tr]  # what random short earns from drift over each trade's hold
        drift_comp_all+=dcs
        allg+=gs
        trade_month+=[M]*len(gs)
        if gs: permonth.append((M,len(gs),float(np.mean(gs))))
    allg=np.array(allg); dca=np.array(drift_comp_all); trade_month=np.array(trade_month)
    # dump trade-level data for downstream fee-tier analysis
    np.savez("/tmp/short25_trades.npz", gross=allg, drift_comp=dca, month=trade_month, span_days=span)
    print(f"  [saved {len(allg)} trades -> /tmp/short25_trades.npz]",flush=True)
    n=len(allg); sd=allg.std()+1e-9; tpy=n/span*365
    edge=allg.mean(); nm=edge-2.0; nt=edge-8.0
    print(f"\n=== RAW (PROVISIONAL): n={n} edge={edge:+.2f}bps Sgross={edge/sd*np.sqrt(tpy):+.2f} | NETmak={nm:+.2f}(S{nm/sd*np.sqrt(tpy):+.2f}) NETtak={nt:+.2f}(S{nt/sd*np.sqrt(tpy):+.2f}) tpy={tpy:.0f}",flush=True)
    # drift-neutral
    alpha=allg-dca
    print(f"  DRIFT component (random-short harvest)={dca.mean():+.2f}bps | DRIFT-NEUTRAL clean edge={alpha.mean():+.2f}bps "
          f"clean-maker Sharpe={(alpha.mean()-2.0)/(alpha.std()+1e-9)*np.sqrt(tpy):+.2f} clean-gross Sharpe={alpha.mean()/(alpha.std()+1e-9)*np.sqrt(tpy):+.2f}",flush=True)
    # per-month
    print("  PER-MONTH: "+" | ".join(f"{M}:n{c}e{e:+.1f}" for M,c,e in permonth),flush=True)
    pos_m=sum(1 for _,_,e in permonth if e>0)
    print(f"    months positive: {pos_m}/{len(permonth)} | worst: {min(permonth,key=lambda x:x[2])}",flush=True)
    # shuffle-null permute yhat
    rng=np.random.default_rng(0); nulls=[]
    for k in range(50):
        tot=[]
        for (M,tn,sig,mid) in cache:
            tr=short_bt(tn,rng.permutation(sig),mid,a.gate,win); tot+=[t[0] for t in tr]
        if tot: nulls.append(np.mean(tot))
    nulls=np.array(nulls)
    print(f"\n  SHUFFLE-NULL (permute yhat 50x): null edge mean={nulls.mean():+.2f} sd={nulls.std():.2f} -> z={(edge-nulls.mean())/(nulls.std()+1e-9):+.2f}",flush=True)
    print(f"  => signal increment above random-short = {edge-nulls.mean():+.2f}bps (raw {edge:+.2f} - null {nulls.mean():+.2f})",flush=True)
    print("DONE_SHORT25.",flush=True)
if __name__=="__main__": main()
