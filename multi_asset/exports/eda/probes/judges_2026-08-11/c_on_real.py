"""Read-only: run the neutral_only rule on the REAL per-name residuals in the production ledger.

Nothing is written. The residual is the top-up leg's own `intended_notional`; the book net at
top-up time is the anchor's measured venue net MINUS the top-up notional that actually filled.
"""
import json, glob, os, sys, collections, datetime as dt
sys.path.insert(0, os.path.expanduser("~/dl_quant_live/live"))
import chase_policy as CP

TREE = os.path.expanduser("~/dl_quant_live/state/live/pilot_log")
def rows(name):
    out=[]
    for f in sorted(glob.glob(os.path.join(TREE,"*",name))):
        for line in open(f):
            line=line.strip()
            if line:
                try: out.append(json.loads(line))
                except Exception: pass
    return out

O, A = rows("orders.jsonl"), rows("anchors.jsonl")
anch = {a.get("rebalance_id"): a for a in A if a.get("rebalance_id")}
by_rid = collections.defaultdict(list)
for o in O:
    if o.get("order_type")=="topup_taker" and o.get("topup_source")=="from_partial":
        by_rid[o.get("rebalance_id")].append(o)

print(f"{'anchor':>22} {'n':>3} {'gross':>9} {'net':>9} {'book net':>10} {'fill':>3} {'skip$':>9} {'saved':>7} {'left tilt':>10}")
tot_g=tot_s=0.0
for rid in sorted(by_rid):
    g = by_rid[rid]; a = anch.get(rid) or {}
    res = [(o["symbol"], float(o.get("intended_notional") or 0.0)) for o in g]
    res = [(s,r) for s,r in res if r]
    if not res: continue
    filled_topup = sum(float(o.get("filled_notional") or 0.0) for o in O
                       if o.get("rebalance_id")==rid and o.get("order_type")=="topup_taker")
    vn, vg = a.get("venue_net_usdt"), a.get("venue_gross_usdt")
    if vn is None or not vg:
        print(f"{rid:>22} {len(res):>3}  (no venue snapshot on this anchor — skipped)"); continue
    net_before = float(vn) - filled_topup
    d = CP.neutral_only_decision(res, net_before, float(vg))
    gr = d["residual_gross_usdt"]; sk = d["skipped_notional_usdt"]
    tot_g += gr; tot_s += sk
    ts = dt.datetime.fromtimestamp(float(a.get("anchor_ts") or 0), dt.timezone.utc).strftime("%m-%d %H:%MZ")
    print(f"{ts:>22} {len(res):>3} {gr:>9.2f} {sum(r for _,r in res):>+9.2f} {net_before:>+10.2f} "
          f"{len(d['fill']):>3} {sk:>9.2f} {sk/gr if gr else 0:>6.1%} {d['projected_net_over_gross']:>+9.3%}"
          f"{'' if d['band_reached'] else '  band NOT reached'}")
print(f"{'TOTAL':>22} {'':>3} {tot_g:>9.2f} {'':>9} {'':>10} {'':>3} {tot_s:>9.2f} {tot_s/tot_g if tot_g else 0:>6.1%}")
