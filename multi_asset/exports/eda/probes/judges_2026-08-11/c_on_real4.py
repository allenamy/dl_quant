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
print("baseline = the ACTUAL book with every other leg at its realised value; only the")
print("from_partial chase is varied.  decision net for C = book net projected AFTER the")
print("from_reject leg, which is known before anything is sent.\n")
print(f"{'anchor':>13} {'n':>2} {'gross':>7} | {'B (no chase)':>12} {'A (chase all)':>13} "
      f"{'C':>8} | {'C fill':>6} {'C skip$':>8} {'saved':>6} {'C cost$':>7} {'A cost$':>7}")
print("-"*106)
T={}
for rid in sorted(tu, key=lambda r:(anch.get(r) or {}).get("anchor_ts") or 0):
    a=anch.get(rid) or {}
    vg,vn=a.get("venue_gross_usdt"),a.get("venue_net_usdt")
    if vn is None or not vg: continue
    G=float(vg)
    fp=[o for o in tu[rid] if o.get("topup_source")=="from_partial" and o.get("terminal_reason") in SENT]
    fr=[o for o in tu[rid] if o.get("topup_source")=="from_reject" and o.get("terminal_reason") in SENT]
    res=[(o["symbol"],float(o.get("intended_notional") or 0)) for o in fp]
    res=[(s,r) for s,r in res if r]
    if not res: continue
    pfl=sum(float(o.get("filled_notional") or 0) for o in fp)
    allfl=sum(float(o.get("filled_notional") or 0) for o in tu[rid])
    n0=float(vn)-allfl                       # before ANY top-up
    n_after_reject=n0+sum(float(o.get("filled_notional") or 0) for o in fr)
    d=CP.neutral_only_decision(res,n_after_reject,G)
    fills={s for s in d["fill"]}
    c_delta=sum(r for s,r in res if s in fills)
    net_B=float(vn)-pfl; net_A=float(vn); net_C=n_after_reject+c_delta
    # per-anchor measured from_partial cost, in bps and dollars
    fee=sum(float(o.get("fee_paid") or 0) for o in fp); adv=0.0; notl=0.0
    for o in fp:
        px,mid=o.get("avg_fill_px"),o.get("mid_at_anchor")
        f_=abs(float(o.get("filled_notional") or 0)); notl+=f_
        if px and mid and f_:
            sg=1.0 if float(o["filled_notional"])>0 else -1.0
            adv+=sg*(float(px)-float(mid))/float(mid)*f_
    bps=1e4*(fee+adv)/notl if notl else 0.0
    cost_A=notl*bps/1e4; cost_C=(notl-d["skipped_notional_usdt"])*bps/1e4
    ts=dt.datetime.fromtimestamp(float(a.get("anchor_ts") or 0),dt.timezone.utc).strftime("%m-%d %H:%MZ")
    print(f"{ts:>13} {len(res):>2} {d['residual_gross_usdt']:>7.2f} | {net_B/G:>+12.2%} {net_A/G:>+13.2%} "
          f"{net_C/G:>+8.2%} | {len(d['fill']):>6} {d['skipped_notional_usdt']:>8.2f} "
          f"{d['skipped_notional_usdt']/d['residual_gross_usdt']:>5.0%} {cost_C:>7.2f} {cost_A:>7.2f}"
          f"   [{bps:+.1f}bps]")
    for k,v in (("B",abs(net_B/G)),("A",abs(net_A/G)),("C",abs(net_C/G)),
                ("cA",cost_A),("cC",cost_C),("g",d["residual_gross_usdt"]),
                ("s",d["skipped_notional_usdt"])):
        T[k]=T.get(k,0.0)+v
print("-"*106)
print(f"{'mean |n/g|':>13}    {'':>7} | {T['B']/3:>+12.2%} {T['A']/3:>+13.2%} {T['C']/3:>+8.2%} | "
      f"{'':>6} {T['s']:>8.2f} {T['s']/T['g']:>5.0%} {T['cC']:>7.2f} {T['cA']:>7.2f}")
