import json, glob, os, sys, collections, datetime as dt
sys.path.insert(0, os.path.expanduser("~/dl_quant_live/live"))
import chase_policy as CP
TREE=os.path.expanduser("~/dl_quant_live/state/live/pilot_log")
def rows(n):
    out=[]
    for f in sorted(glob.glob(os.path.join(TREE,"*",n))):
        for l in open(f):
            l=l.strip()
            if l:
                try: out.append(json.loads(l))
                except Exception: pass
    return out
O,A=rows("orders.jsonl"),rows("anchors.jsonl")
anch={a.get("rebalance_id"):a for a in A if a.get("rebalance_id")}
SENT={"filled","filled_amount_unknown"}
tu=collections.defaultdict(list)
for o in O:
    if o.get("order_type")=="topup_taker": tu[o.get("rebalance_id")].append(o)
print(f"{'anchor':>13} {'n':>2} {'gross':>8} {'net0':>8} {'n/g0':>7} | "
      f"{'A: n/g':>8} {'A: $':>7} | {'C fill':>6} {'C skip$':>8} {'saved':>6} {'C: n/g':>8} {'band':>5}")
print("-"*104)
for rid in sorted(tu, key=lambda r: (anch.get(r) or {}).get("anchor_ts") or 0):
    a=anch.get(rid) or {}
    vg,vn=a.get("venue_gross_usdt"),a.get("venue_net_usdt")
    if vn is None or not vg: continue
    g=[o for o in tu[rid] if o.get("topup_source")=="from_partial" and o.get("terminal_reason") in SENT]
    res=[(o["symbol"],float(o.get("intended_notional") or 0)) for o in g]
    res=[(s,r) for s,r in res if r]
    if not res: continue
    allfl=sum(float(o.get("filled_notional") or 0) for o in tu[rid])
    pfl=sum(float(o.get("filled_notional") or 0) for o in g)
    n0=float(vn)-allfl                      # book net before ANY top-up
    G=float(vg)
    d=CP.neutral_only_decision(res,n0,G)
    ts=dt.datetime.fromtimestamp(float(a.get("anchor_ts") or 0),dt.timezone.utc).strftime("%m-%d %H:%MZ")
    a_net=n0+pfl                            # what chasing ALL of from_partial does, other legs held
    print(f"{ts:>13} {len(res):>2} {d['residual_gross_usdt']:>8.2f} {n0:>+8.2f} {n0/G:>+7.2%} | "
          f"{a_net/G:>+8.2%} {abs(pfl)*40/1e4:>7.2f} | {len(d['fill']):>6} {d['skipped_notional_usdt']:>8.2f} "
          f"{d['skipped_notional_usdt']/d['residual_gross_usdt']:>5.0%} "
          f"{d['projected_net_over_gross']:>+8.2%} {'yes' if d['band_reached'] else 'NO':>5}")
print("\nA: $ = the chase cost at the measured ~40bps blended from_partial rate (indicative).")
