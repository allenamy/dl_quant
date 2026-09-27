# Pooled (blind state: no arm split) rebuild and cost statistics from the LIVE ledger, read through the owner's readers
# (pilot_log.read_fills = collapse_supersedes; read_day for orders/anchors). Read-only. usage: /usr/bin/python3 rebuild_stats.py <executor repo>
import sys, time, collections
REPO = sys.argv[1]; sys.path.insert(0, f"{REPO}/live"); import pilot_log as PL
root = f"{REPO}/state/live/pilot_log"; days = [d for d in PL.available_days(root) if d >= "20260901"]
fills = collections.defaultdict(list); orders = collections.defaultdict(list); anchors = {}
for d in days:
    for f in PL.read_fills(root, d): fills[f.get("rebalance_id")].append(f)
    D = PL.read_day(root, d)
    for o in D["orders"]: orders[o.get("rebalance_id")].append(o)
    for a in D["anchors"]: anchors[a["rebalance_id"]] = a
def stats(rids):
    N = T = 0.0; CN = C = 0.0; S = SN = 0.0
    for rid in rids:
        for f in fills.get(rid, []):
            n = abs(f.get("fill_notional") or 0); N += n
            if f.get("venue_maker_flag") is False: T += n
            if f.get("commission_asset") == "USDT": CN += n; C += f.get("commission") or 0
        for o in orders.get(rid, []):
            fn = abs(o.get("filled_notional") or 0); px, mid = o.get("avg_fill_px"), o.get("mid_at_submit")
            if fn and px and mid:
                S += fn * (1 if str(o.get("side")).upper() == "BUY" else -1) * (px - mid) / mid * 1e4; SN += fn
    return {"fill_notional": round(N), "taker_share": round(T / N, 3) if N else None, "fee_bps": round(C / CN * 1e4, 2) if CN else None,
            "slip_bps_vs_mid_at_submit": round(S / SN, 2) if SN else None}
order = sorted(anchors, key=lambda r: anchors[r]["anchor_ts"])
traded = [r for r in order if r.startswith("A") and (anchors[r].get("realized_gross") or 0) > 1000 and anchors[r]["anchor_ts"] < 1790496000]
l42 = traded[-42:]
u = lambda r: time.strftime("%m-%dT%HZ", time.gmtime(anchors[r]["anchor_ts"] - 1440))
print(f"LAST42 {u(l42[0])}..{u(l42[-1])} pooled {stats(l42)}")
prev = None
for r in order:
    a = anchors[r]
    if prev is not None and (anchors[prev].get("realized_gross") or 0) < 1000 and (a.get("realized_gross") or 0) > 1000:
        nxt = order[order.index(r) + 1] if order.index(r) + 1 < len(order) else None
        f1 = a["realized_gross"] / a["target_gross"]; f2 = (anchors[nxt]["realized_gross"] / anchors[nxt]["target_gross"]) if nxt else None
        print(f"REBUILD first={u(r)} target {a['target_gross']:.0f} realized {a['realized_gross']:.0f} ({f1:.1%}) {stats([r])}"
              + (f" | second={u(nxt)} ({f2:.1%}) {stats([nxt])}" if nxt else ""))
    prev = r
