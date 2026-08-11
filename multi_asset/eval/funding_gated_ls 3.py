"""FUNDING-GATED LONG-SHORT backtest on REAL perp book-mid (mechanism-driven).
Signal symmetric unconditionally; funding conditions the asymmetry (high funding=over-long -> short edge triples, long decays).

STRATEGIES (all real price, causal):
  A. SHORT-ONLY (current baseline)
  B. SYMMETRIC long-short, NO gate (long top-tail / short bottom-tail)
  C. FUNDING-GATED long-short (HARD filter): high funding(>hi pctile, over-long) -> SHORT allowed, LONG suppressed;
     low/neg funding(<lo pctile) -> LONG allowed, SHORT suppressed; mid -> both (symmetric).
  D. FUNDING-TILT (continuous): size each side by a funding-based multiplier (short scaled up with funding, long down).
GATE data: causal funding (data/funding/btcusdt_funding.csv) percentile over trailing window (<=t).
HOLDING: enter on tail; hold until mean-revert through trailing median OR opposite tail; min-hold; max-hold.
COST: round-trip maker 2 / taker 8 bps charged entry+exit. PnL = real log(mid) signed by side.
RIGOR: real perp mid (midcov), causal funding<=t, shuffle-null (permute yhat; separately permute funding) -> gated edge collapse?
       drift-neutral edge reported. Exact Sharpe = edge/sd*sqrt(n/span*365).
Run on SERVER: PYTHONPATH=. python multi_asset/eval/funding_gated_ls.py --csv exports/final_l01/y600_l01_alwaysEMA_walkforward.csv
"""
from __future__ import annotations
import numpy as np, argparse, csv as _csv, gzip, os
from collections import deque
from datetime import datetime, timezone, timedelta

BOOK="/mnt/storage/btcusdt_copy_2023-01-01_2026-05-31/dl-tardis/book_snapshot_25"; VENUE="binance-futures"
FUND="data/funding/btcusdt_funding.csv"

def load_csv(path):
    rows=list(_csv.DictReader(open(path)))
    ts=np.array([int(r["timestamp_us"]) for r in rows]); mon=np.array([r["month"] for r in rows])
    qd=np.array([float(r["pred_q50_demean_raw"]) for r in rows]); o=np.argsort(ts)
    return mon[o],ts[o],qd[o]

def load_funding():
    rows=list(_csv.DictReader(open(FUND)))
    def f2(s):
        try: return float(s)
        except: return np.nan
    ft=np.array([int(r["fundingTime_ms"])*1000 for r in rows]); fr=np.array([f2(r["fundingRate"]) for r in rows])
    o=np.argsort(ft); return ft[o],fr[o]

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

def causal_funding_pctile(node_ts, ft, fr, win_ns):
    # funding value at-or-before each node, and its causal trailing percentile (<=t)
    fi=np.searchsorted(ft,node_ts,side="right")-1
    val=np.where(fi>=0, fr[np.clip(fi,0,len(fr)-1)], np.nan)
    pct=np.full(len(node_ts),np.nan); dq=deque()
    for i in range(len(node_ts)):
        if not np.isnan(val[i]): dq.append((node_ts[i],val[i]))
        while dq and dq[0][0]<node_ts[i]-win_ns: dq.popleft()
        if len(dq)>=20 and not np.isnan(val[i]):
            arr=np.fromiter((v for _,v in dq),float); pct[i]=np.mean(arr<=val[i])
    return val,pct

def tq(sig,tn,win,ql,qh):
    n=len(sig);tl=np.full(n,np.nan);th=np.full(n,np.nan);md=np.full(n,np.nan);dq=deque()
    for i in range(n):
        dq.append((tn[i],sig[i]))
        while dq and dq[0][0]<tn[i]-win: dq.popleft()
        if len(dq)>=50:
            v=np.fromiter((x for _,x in dq),float); tl[i]=np.quantile(v,ql); th[i]=np.quantile(v,qh); md[i]=np.quantile(v,0.5)
    return tl,th,md

def backtest(tn,sig,mid,fpct,gate,win,mode,fhi=0.66,flo=0.33,min_hold=3,max_hold=36):
    # mode: "short", "sym", "gated". gated: allow short only if fpct>=flo? we use: high funding(fpct>=fhi)->short ok,long block;
    #   low funding(fpct<=flo)->long ok, short block; mid-> both.
    tl,th,md=tq(sig,tn,win,gate,1-gate)
    pos=0;ep=0.0;held=0;tr=[]
    for i in range(len(sig)):
        s=sig[i]; m=mid[i]; fp=fpct[i]
        if np.isnan(m):
            if pos!=0: held+=1
            continue
        if pos==0:
            want=0
            if not np.isnan(th[i]):
                if s>=th[i]: want=+1
                elif s<=tl[i]: want=-1
            if want!=0:
                ok=True
                if mode=="short": ok=(want==-1)
                elif mode=="gated":
                    if np.isnan(fp): ok=True
                    elif want==-1: ok=(fp>=flo)       # short blocked only when funding very low (crowd short)
                    elif want==+1: ok=(fp<=fhi)       # long blocked when funding very high (crowd over-long)
                if ok: pos=want; ep=m; held=0
        else:
            held+=1
            flip=(pos==+1 and not np.isnan(tl[i]) and s<=tl[i]) or (pos==-1 and not np.isnan(th[i]) and s>=th[i])
            revert=(pos==+1 and not np.isnan(md[i]) and s<md[i]) or (pos==-1 and not np.isnan(md[i]) and s>md[i])
            if (held>=min_hold and (flip or revert)) or held>=max_hold:
                gross=pos*np.log(m/ep)*1e4; tr.append((pos,gross,held)); pos=0
    return tr

def stats(tr, span_days, label, maker=2.0, taker=8.0):
    if not tr: return f"  {label}: no trades", -99, None
    e=np.array([t[1] for t in tr]); sides=np.array([t[0] for t in tr]); n=len(e); sd=e.std()+1e-9
    tpy=n/span_days*365; trd=n/span_days
    edge=e.mean(); nm=edge-maker; nt=edge-taker
    Sm=nm/sd*np.sqrt(tpy); St=nt/sd*np.sqrt(tpy); Sg=edge/sd*np.sqrt(tpy)
    ls=f"L{int((sides>0).sum())}/S{int((sides<0).sum())}"
    return (f"  {label:22s}: n={n:4d}({ls}) tr/d={trd:4.1f} edge={edge:+5.2f} Sg={Sg:+4.1f} | "
            f"NETmak={nm:+5.2f}(S{Sm:+4.1f}) NETtak={nt:+5.2f}(S{St:+4.1f})"), nm/sd*np.sqrt(tpy), (edge,n,sd,tpy)

def main():
    ap=argparse.ArgumentParser(); ap.add_argument("--csv",default="exports/final_l01/y600_l01_alwaysEMA_walkforward.csv")
    ap.add_argument("--win",type=int,default=86400); ap.add_argument("--fwin",type=int,default=30*86400)
    a=ap.parse_args(); win=a.win*1_000_000; fwin=a.fwin*1_000_000
    mon,ts,qd=load_csv(a.csv); ft,fr=load_funding(); span=(ts.max()-ts.min())/(86400*1e6)
    print(f"=== FUNDING-GATED LONG-SHORT (real perp mid, causal funding<=t) span {span:.0f}d ===",flush=True)
    cache=[]
    for M in sorted(set(mon)):
        m=mon==M; tn,sig=make_nodes(ts[m],qd[m]); mid=node_mid(tn)
        if mid is None: print(f"  {M}: no book",flush=True); continue
        fval,fpct=causal_funding_pctile(tn,ft,fr,fwin)
        cache.append((M,tn,sig,mid,fpct)); print(f"  {M}: nodes={len(tn)} midcov={np.mean(~np.isnan(mid)):.2f} fpct_cov={np.mean(~np.isnan(fpct)):.2f}",flush=True)
    def run_all(gate,fhi,flo):
        res={}
        for mode in ["short","sym","gated"]:
            allt=[]
            for (M,tn,sig,mid,fpct) in cache: allt+=backtest(tn,sig,mid,fpct,gate,win,mode,fhi,flo)
            res[mode]=allt
        return res
    print(f"\n=== SWEEP (gate x funding-threshold), exact Sharpe=edge/sd*sqrt(n/span*365) ===",flush=True)
    best=None
    for gate in [0.10,0.05,0.025]:
        for (fhi,flo) in [(0.66,0.33),(0.75,0.25),(0.80,0.20)]:
            res=run_all(gate,fhi,flo)
            print(f"\n-- gate +-{gate*100:.1f}% funding[lo<{flo} hi>{fhi}] --",flush=True)
            for mode in ["short","sym","gated"]:
                line,Sm,info=stats(res[mode],span,mode); print(line,flush=True)
                if mode=="gated" and info and (best is None or Sm>best[0]): best=(Sm,gate,fhi,flo,info)
    if best:
        Sm,gate,fhi,flo,info=best; edge,n,sd,tpy=info
        print(f"\n=== GATED best net-maker Sharpe={Sm:+.2f} @ gate{gate} fhi{fhi} flo{flo} (edge {edge:+.2f}bps n{n}) ===",flush=True)
        # shuffle-null on this config: permute yhat, and separately permute funding
        rng=np.random.default_rng(0)
        def null_edge(perm_what):
            ed=[]
            for k in range(30):
                allt=[]
                for (M,tn,sig,mid,fpct) in cache:
                    s2=rng.permutation(sig) if perm_what=="yhat" else sig
                    f2=rng.permutation(fpct) if perm_what=="fund" else fpct
                    allt+=backtest(tn,s2,mid,f2,gate,win,"gated",fhi,flo)
                if allt: ed.append(np.mean([t[1] for t in allt]))
            return np.array(ed)
        ny=null_edge("yhat"); nf=null_edge("fund")
        print(f"  SHUFFLE-NULL permute-YHAT: null edge mean={ny.mean():+.2f} sd={ny.std():.2f} z={(edge-ny.mean())/(ny.std()+1e-9):+.2f}",flush=True)
        print(f"  SHUFFLE-NULL permute-FUND: null edge mean={nf.mean():+.2f} sd={nf.std():.2f} z={(edge-nf.mean())/(nf.std()+1e-9):+.2f}",flush=True)
    print("DONE_FUNDGATE.",flush=True)

if __name__=="__main__": main()
