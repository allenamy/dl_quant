"""Read-only. The SENDABLE from_partial population only, and what chasing did to the tilt."""
import json, glob, os, sys, collections, datetime as dt
sys.path.insert(0, os.path.expanduser("~/dl_quant_live/live"))
import chase_policy as CP
TREE = os.path.expanduser("~/dl_quant_live/state/live/pilot_log")
def rows(n):
    out=[]
    for f in sorted(glob.glob(os.path.join(TREE,"*",n))):
        for l in open(f):
            l=l.strip()
            if l:
                try: out.append(json.loads(l))
                except Exception: pass
    return out
O,A = rows("orders.jsonl"), rows("anchors.jsonl")
anch = {a.get("rebalance_id"): a for a in A if a.get("rebalance_id")}
SENT = {"filled","filled_amount_unknown"}
tu = collections.defaultdict(list)
for o in O:
    if o.get("order_type")=="topup_taker":
        tu[o.get("rebalance_id")].append(o)
print("terminal_reason census over ALL topup_taker rows:")
for k,v in collections.Counter(o.get("terminal_reason") for o in O if o.get("order_type")=="topup_taker").most_common():
    print(f"   {k:<26} {v}")
print()
hdr=f"{'anchor':>13} {'src':<12} {'nSend':>5} {'gross':>8} {'resid net':>10} {'book net0':>10} {'n/g0':>7} {'chase->':>8} {'n/g1':>7}"
print(hdr); print("-"*len(hdr))
for rid in sorted(tu):
    a = anch.get(rid) or {}
    vg = a.get("venue_gross_usdt"); vn = a.get("venue_net_usdt")
    ts = dt.datetime.fromtimestamp(float(a.get("anchor_ts") or 0), dt.timezone.utc).strftime("%m-%d %H:%MZ")
    for src in ("from_partial","from_reject"):
        g=[o for o in tu[rid] if o.get("topup_source")==src and o.get("terminal_reason") in SENT]
        if not g: continue
        res=[(o["symbol"], float(o.get("intended_notional") or 0)) for o in g]
        res=[(s,r) for s,r in res if r]
        fl=sum(float(o.get("filled_notional") or 0) for o in g)
        gross=sum(abs(r) for _,r in res); net=sum(r for _,r in res)
        allfl=sum(float(o.get("filled_notional") or 0) for o in tu[rid])
        n0 = (float(vn)-allfl) if vn is not None else None
        print(f"{ts:>13} {src:<12} {len(res):>5} {gross:>8.2f} {net:>+10.2f} "
              f"{(f'{n0:+10.2f}' if n0 is not None else '         ?')} "
              f"{(f'{n0/float(vg):+7.2%}' if n0 is not None and vg else '      ?')} "
              f"{fl:>+8.2f} {(f'{float(vn)/float(vg):+7.2%}' if vn is not None and vg else '      ?')}")
