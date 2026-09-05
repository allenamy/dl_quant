import json, os, time, collections
import numpy as np
PL=os.path.expanduser("~/dl_quant_live/state/live/pilot_log"); H4=14400
days=[d for d in sorted(os.listdir(PL)) if d.isdigit() and "20260826"<=d<="20260905"]
def jl(d,n):
    p=f"{PL}/{d}/{n}.jsonl"; return [json.loads(l) for l in open(p) if l.strip()] if os.path.exists(p) else []
O=[r for d in days for r in jl(d,"orders")]; F=[r for d in days for r in jl(d,"fills")]; A=[r for d in days for r in jl(d,"anchors")]
rid2N={r["rebalance_id"]:int(float(r["anchor_ts"])//H4*H4) for r in A}; ANCT={r["rebalance_id"]:float(r["anchor_ts"]) for r in A}
byid={}
for r in F:
    if r["trade_id"] not in byid or r.get("supersedes_trade_id") is not None: byid[r["trade_id"]]=r
FD=list(byid.values())
MID={}; SPR={}
for r in O:
    MID[(r["rebalance_id"],r["symbol"])]=r.get("mid_at_anchor")
    if r.get("spread_at_submit_bps") is not None: SPR[(r["rebalance_id"],r["symbol"],r["order_type"],int(r["attempt_idx"]))]=r["spread_at_submit_bps"]
rows=[]
for r in FD:
    px=float(r["fill_px"]); m60=r.get("mid_at_fill_plus_60s"); sgn=1 if r["side"]=="buy" else -1
    m0=MID.get((r["rebalance_id"],r["symbol"])); at=ANCT.get(r["rebalance_id"])
    rows.append(dict(sym=r["symbol"], typ=r["order_type"], side=r["side"], notl=float(r["fill_notional"]), N=rid2N.get(r["rebalance_id"]),
        mo=(sgn*(float(m60)-px)/px*1e4) if m60 is not None else np.nan, lag=r.get("mark_lag_s"),
        vam=(sgn*(m0-px)/m0*1e4) if m0 else np.nan, delay=(float(r["fill_ts"])-at) if at else np.nan,
        spr=SPR.get((r["rebalance_id"],r["symbol"],r["order_type"],int(r["attempt_idx"]))), bf=m60 is not None))
B=[x for x in rows if x["bf"]]; P=rows
print("backfilled n", len(B), "population n", len(P))
def desc(v, w=None):
    v=np.array(v,float); ok=np.isfinite(v); v=v[ok]
    if w is not None: w=np.array(w,float)[ok]
    if not len(v): return "n=0"
    s=f"n={len(v)} mean={v.mean():+.2f} wmean={((v*w).sum()/w.sum()) if w is not None else float('nan'):+.2f} med={np.median(v):+.2f} p5={np.percentile(v,5):+.1f} p25={np.percentile(v,25):+.1f} p75={np.percentile(v,75):+.1f} p95={np.percentile(v,95):+.1f} min={v.min():+.1f} max={v.max():+.1f}"
    return s
print("\n== +60s markout (bps, >0 favourable) by type, backfilled only")
for t in ("maker","topup_taker"):
    b=[x for x in B if x["typ"]==t]; print(f"  {t}: {desc([x['mo'] for x in b],[x['notl'] for x in b])}")
print("  maker excl |mo|>100:", desc([x['mo'] for x in B if x['typ']=='maker' and abs(x['mo'])<=100],[x['notl'] for x in B if x['typ']=='maker' and abs(x['mo'])<=100]))
print("\n== largest |markout| rows")
for x in sorted(B, key=lambda x:-abs(x["mo"]))[:12]: print("  ", x["sym"], x["typ"], x["side"], f"notl={x['notl']:.1f} mo={x['mo']:+.1f} vam={x['vam']:+.1f} lag={x['lag']} spr={x['spr']}", time.strftime("%m-%d %HZ",time.gmtime(x["N"])))
print("\n== mark_lag_s:", desc([x["lag"] for x in B]))
print("\n== representativeness: backfilled subset vs population on 100%-covered fields")
for t in ("maker","topup_taker"):
    b=[x for x in B if x["typ"]==t]; p=[x for x in P if x["typ"]==t]
    print(f"  {t}: vs_anchor_mid  subset {desc([x['vam'] for x in b],[x['notl'] for x in b])}")
    print(f"  {t}: vs_anchor_mid  popul. {desc([x['vam'] for x in p],[x['notl'] for x in p])}")
    print(f"  {t}: notional       subset {desc([x['notl'] for x in b])}")
    print(f"  {t}: notional       popul. {desc([x['notl'] for x in p])}")
    print(f"  {t}: fill delay s   subset {desc([x['delay'] for x in b])}")
    print(f"  {t}: fill delay s   popul. {desc([x['delay'] for x in p])}")
    print(f"  {t}: spread bps     subset {desc([x['spr'] for x in b])}")
    print(f"  {t}: spread bps     popul. {desc([x['spr'] for x in p])}")
    print(f"  {t}: side buy share subset {np.mean([x['side']=='buy' for x in b]):.3f} popul. {np.mean([x['side']=='buy' for x in p]):.3f}")
# symbol concentration of backfill
cs=collections.Counter(x["sym"] for x in B); print("\n== backfilled symbol concentration: distinct", len(cs), "top", cs.most_common(8))
cp=collections.Counter(x["sym"] for x in P); print("   population distinct symbols", len(cp))
# per-anchor: is the subset the first fills of the anchor?
first=collections.defaultdict(list)
for x in P: first[x["N"]].append(x)
rk=[]
for N,xs in first.items():
    xs=sorted(xs,key=lambda x:x["delay"] if np.isfinite(x["delay"]) else 1e9)
    for i,x in enumerate(xs):
        if x["bf"]: rk.append(i/len(xs))
print("== backfilled fills' rank-within-anchor by fill time (0=first):", desc(rk))
# markout vs anchor-mid relation on subset: is markout mostly spread capture reversal?
b=[x for x in B if x["typ"]=="maker" and np.isfinite(x["vam"])]
print("\n== maker subset corr(markout, vs_anchor_mid) =", np.corrcoef([x["mo"] for x in b],[x["vam"] for x in b])[0,1], "; mean(mo+vam) =", np.mean([x["mo"]+x["vam"] for x in b]))
# taker vs anchor mid by anchor (which anchors drive the -40 bps in tier1?)
tk=[x for x in P if x["typ"]=="topup_taker" and np.isfinite(x["vam"])]
byN=collections.defaultdict(list)
for x in tk: byN[x["N"]].append(x)
print("\n== taker vs_anchor_mid by anchor (notional-weighted), worst 8:")
agg=[(N, sum(x["vam"]*x["notl"] for x in xs)/sum(x["notl"] for x in xs), sum(x["notl"] for x in xs), len(xs)) for N,xs in byN.items()]
for N,v,n,c in sorted(agg,key=lambda t:t[1])[:8]: print("  ", time.strftime("%m-%d %HZ",time.gmtime(N)), f"{v:+.1f} bps on {n:.0f} USDT, {c} fills")
print("== taker vs_anchor_mid overall wmean", sum(x["vam"]*x["notl"] for x in tk)/sum(x["notl"] for x in tk), "median", np.median([x["vam"] for x in tk]), "; by delay bucket:")
for lo,hi in ((0,300),(300,600),(600,900),(900,2000)):
    xs=[x for x in tk if lo<=x["delay"]<hi]
    if xs: print(f"   delay {lo}-{hi}s: n={len(xs)} wmean={sum(x['vam']*x['notl'] for x in xs)/sum(x['notl'] for x in xs):+.1f} med={np.median([x['vam'] for x in xs]):+.1f}")
