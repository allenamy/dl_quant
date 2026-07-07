"""REAL-PRICE verification of the tail+holding SHORT-side edge. Uses ACTUAL perp book-mid from btcusdt_copy
(binance-futures venue), NOT the telescoped y_600 reconstruction.

For each test month:
  * Parse perp book_snapshot_25 (binance-futures) -> mid = (asks[0].price+bids[0].price)/2, at us timestamps.
  * For each prediction NODE (the production-CSV timestamps), find the real perp mid at-or-before that ts (<=t, no look-ahead).
  * Tail-gated entry (trailing-dist quantile of causal-demeaned yhat, <=t) + HOLD (exit on opposite tail OR
    mean-revert through trailing median; min/max hold). Entry P&L = REAL mid(exit)-mid(entry), signed.
  * Round-trip cost charged per entry+exit (maker / taker).
  * SHUFFLE-NULL: permute yhat -> short-side edge should collapse to ~0.
  * Exact Sharpe: per-trade IR * sqrt(trades_per_year), trades_per_year = n_trades / span_days * 365.

Run on SERVER (needs btcusdt_copy): PYTHONPATH=. python multi_asset/eval/tail_holding_realprice.py --csv <prod.csv>
"""
from __future__ import annotations
import numpy as np, argparse, csv as _csv, gzip, os, glob
from collections import deque
from datetime import datetime, timezone

BOOK="/mnt/storage/btcusdt_copy_2023-01-01_2026-05-31/dl-tardis/book_snapshot_25"
VENUE="binance-futures"

def load_csv(path):
    rows=list(_csv.DictReader(open(path)))
    ts=np.array([int(r["timestamp_us"]) for r in rows])
    mon=np.array([r["month"] for r in rows])
    qd=np.array([float(r["pred_q50_demean_raw"]) for r in rows])
    o=np.argsort(ts); return mon[o],ts[o],qd[o]

def days_in_range(ts_us):
    t0=datetime.fromtimestamp(ts_us.min()/1e6,tz=timezone.utc).date()
    t1=datetime.fromtimestamp(ts_us.max()/1e6,tz=timezone.utc).date()
    out=[]; import datetime as _dt; d=t0
    while d<=t1: out.append(d.isoformat()); d=d+_dt.timedelta(days=1)
    return out

def load_perp_mid(day):
    """Return (ts_us sorted, mid) for one day, subsampled to ~1s to keep memory low."""
    f=f"{BOOK}/{day}/{VENUE}/BTCUSDT.csv.gz"
    if not os.path.exists(f): return None
    ts=[]; mid=[]; last_keep=-1
    with gzip.open(f,"rt") as fh:
        hdr=fh.readline().split(",")
        ia=hdr.index("asks[0].price"); ib=hdr.index("bids[0].price"); it=hdr.index("timestamp")
        for line in fh:
            p=line.split(",")
            try:
                t=int(p[it])
                if t-last_keep < 1_000_000: continue  # ~1s subsample
                a=float(p[ia]); b=float(p[ib])
                ts.append(t); mid.append((a+b)/2); last_keep=t
            except: continue
    if not ts: return None
    return np.array(ts,dtype=np.int64), np.array(mid,dtype=np.float64)

def build_mid_series(node_ts):
    """For the union of days, build a (ts,mid) array; then map each node_ts to real mid at-or-before (<=t)."""
    days=days_in_range(node_ts)
    TS=[];MID=[]
    for d in days:
        r=load_perp_mid(d)
        if r is not None: TS.append(r[0]); MID.append(r[1])
    if not TS: return None
    TS=np.concatenate(TS); MID=np.concatenate(MID); o=np.argsort(TS); TS=TS[o]; MID=MID[o]
    # map each node to last mid <= node_ts (causal)
    idx=np.searchsorted(TS,node_ts,side="right")-1
    valid=idx>=0
    node_mid=np.full(len(node_ts),np.nan); node_mid[valid]=MID[idx[valid]]
    # sanity: node should be within 5s of a book update
    gap=np.full(len(node_ts),1e18); gap[valid]=(node_ts[valid]-TS[idx[valid]])
    node_mid[gap>5_000_000]=np.nan
    return node_mid

def make_nodes(tm,qm):
    idx=[0]; last=tm[0]
    for i in range(1,len(tm)):
        if tm[i]-last>=(600-90)*1_000_000: idx.append(i); last=tm[i]
    idx=np.array(idx); return tm[idx],qm[idx]

def tq(sig,tn,win,ql,qh):
    n=len(sig);tl=np.full(n,np.nan);th=np.full(n,np.nan);dq=deque()
    for i in range(n):
        dq.append((tn[i],sig[i]))
        while dq and dq[0][0]<tn[i]-win: dq.popleft()
        if len(dq)>=50:
            v=np.fromiter((x for _,x in dq),float); tl[i]=np.quantile(v,ql); th[i]=np.quantile(v,qh)
    return tl,th

def backtest(tn,sig,mid,win,gate,min_hold,max_hold,side_filter=0):
    tl,th=tq(sig,tn,win,gate,1-gate); med,_=tq(sig,tn,win,0.5,0.5)
    pos=0;ep=0.0;held=0;tr=[]  # (side, gross_logret_bps, hold)
    for i in range(len(sig)):
        s=sig[i]; m=mid[i]
        if np.isnan(m):
            if pos!=0: held+=1
            continue
        if pos==0:
            if not np.isnan(th[i]):
                want=(+1 if s>=th[i] else (-1 if s<=tl[i] else 0))
                if want!=0 and (side_filter==0 or want==side_filter): pos=want; ep=m; held=0
        else:
            held+=1
            flip=(pos==+1 and not np.isnan(tl[i]) and s<=tl[i]) or (pos==-1 and not np.isnan(th[i]) and s>=th[i])
            revert=(pos==+1 and not np.isnan(med[i]) and s<med[i]) or (pos==-1 and not np.isnan(med[i]) and s>med[i])
            if (held>=min_hold and (flip or revert)) or held>=max_hold:
                gross=pos*np.log(m/ep)*1e4  # bps log-return, signed by side
                tr.append((pos,gross,held)); pos=0
    return tr

def sharpe(tr, span_days, rt_cost):
    if not tr: return None
    a=np.array([t[1] for t in tr]); n=len(a); sd=a.std()+1e-9
    tpy=n/span_days*365
    gross=a.mean(); net=gross-rt_cost
    return dict(n=n, edge=gross, net=net, sd=sd, tpy=tpy,
                Sg=gross/sd*np.sqrt(tpy), Sn=net/sd*np.sqrt(tpy),
                hold=np.mean([t[2] for t in tr]))

def main():
    ap=argparse.ArgumentParser(); ap.add_argument("--csv",default="exports/final_l01/y600_l01_alwaysEMA_walkforward.csv")
    ap.add_argument("--win",type=int,default=86400); ap.add_argument("--gate",type=float,default=0.10)
    ap.add_argument("--maker",type=float,default=2.0); ap.add_argument("--taker",type=float,default=8.0)
    a=ap.parse_args(); win_ns=a.win*1_000_000
    mon,ts,qd=load_csv(a.csv)
    span_days=(ts.max()-ts.min())/(86400*1e6)
    print(f"=== REAL-PRICE tail+holding verification (perp book-mid, {VENUE}) gate +-{a.gate*100:.1f}% ===",flush=True)
    # CACHE per-month nodes + real mid ONCE (reused for backtest + shuffle-null)
    cache=[]
    for M in sorted(set(mon)):
        m=mon==M; tn,sig=make_nodes(ts[m],qd[m]); mid=build_mid_series(tn)
        if mid is None: print(f"  {M}: no book data",flush=True); continue
        cache.append((M,tn,sig,mid)); print(f"  {M}: loaded nodes={len(tn)} midcov={np.mean(~np.isnan(mid)):.2f}",flush=True)
    ALL=[]
    for (M,tn,sig,mid) in cache:
        tr=backtest(tn,sig,mid,win_ns,a.gate,3,36,side_filter=0)
        ALL+=[(M,)+x for x in tr]
        sh=[x[1] for x in tr if x[0]==-1]; lo=[x[1] for x in tr if x[0]==+1]
        print(f"  {M}: SHORT n={len(sh)} edge={np.mean(sh) if sh else 0:+.2f}bps | LONG n={len(lo)} edge={np.mean(lo) if lo else 0:+.2f}bps",flush=True)
    # pooled SHORT vs LONG real-price
    sh=[(x[1],x[3]) for x in ALL if x[1]==-1] if False else [x for x in ALL if x[1]==-1]
    short=[(x[1],x[2],x[3]) for x in ALL if x[1]==-1]
    longs=[(x[1],x[2],x[3]) for x in ALL if x[1]==+1]
    def blk(tr3,label):
        if not tr3: print(f"  {label}: none"); return
        edges=np.array([t[1] for t in tr3]); holds=[t[2] for t in tr3]; n=len(edges); sd=edges.std()+1e-9
        tpy=n/span_days*365
        for ck,(rt,nm) in {"maker":(a.maker,"maker"),"taker":(a.taker,"taker")}.items():
            net=edges.mean()-rt
            print(f"  {label:6s} {nm:5s}: n={n} edge={edges.mean():+.2f}bps hold={np.mean(holds):.1f}nd Sgross={edges.mean()/sd*np.sqrt(tpy):+.2f} NET={net:+.2f}bps Snet={net/sd*np.sqrt(tpy):+.2f} (tpy={tpy:.0f})")
    print("\n=== POOLED REAL-PRICE (exact Sharpe = edge/sd * sqrt(n/span_days*365)) ===",flush=True)
    blk(short,"SHORT"); blk(longs,"LONG")
    # shuffle-null on SHORT side: permute yhat within month, reuse CACHED mids (no re-read)
    print("\n=== SHUFFLE-NULL (permute yhat, 50x) SHORT-side edge ===",flush=True)
    rng=np.random.default_rng(0); nulls=[]
    for k in range(50):
        tot=[]
        for (M,tn,sig,mid) in cache:
            sp=rng.permutation(sig)
            tr=backtest(tn,sp,mid,win_ns,a.gate,3,36,side_filter=-1)
            tot+=[x[1] for x in tr]
        if tot: nulls.append(np.mean(tot))
    nulls=np.array(nulls)
    real_short=np.mean([t[1] for t in short]) if short else 0
    print(f"  REAL short edge={real_short:+.2f}bps | NULL mean={nulls.mean():+.2f} sd={nulls.std():.2f} z={(real_short-nulls.mean())/(nulls.std()+1e-9):+.2f}")
    print("DONE_REALPRICE.")

if __name__=="__main__": main()
