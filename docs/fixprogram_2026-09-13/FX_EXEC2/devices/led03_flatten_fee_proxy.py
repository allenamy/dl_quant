#!/usr/bin/python3
"""LED-03 offline PROXY of the protective-flatten fees that were never measured (read-only, no venue, no credentials).

For every FLATTEN-<trip> batch in a ledger COPY: each filled leg's commission = Σ guard_twin income COMMISSION rows of
that symbol whose time lies in the BATCH WINDOW [trip time from the rebalance id, the batch rows' write time + 5 s]
(both read from the ledger, not tuned). A leg is AMBIGUOUS when another order row of the same symbol (not this batch)
has a fill time inside the window. Amounts stay per asset (BNB is never converted here).
POSITIVE CONTROL: the same rule on the two batches whose exact commissions exist in fills rows (09-09, 09-12), compared
leg by leg (collapsed on (symbol, trade_id)). The proxy is reported for the eight older batches only if the control
matches on every unambiguous leg within 1e-8 per asset. Output: receipt JSON (argv[3]); nothing else is written.
Usage: /usr/bin/python3 led03_flatten_fee_proxy.py <pilot_log_root_copy> <guard_twin_income.jsonl> <receipt.json>"""
import bisect, calendar, collections, hashlib, json, os, sys, time
ROOT, INCOME, OUT = sys.argv[1:4]
TOL, SLACK_S = 1e-8, 5.0
raw = open(INCOME, "rb").read(); assert len(raw) == os.stat(INCOME).st_size
inc = sorted((json.loads(l) for l in raw.splitlines() if l.strip()), key=lambda r: r["time"])
comm = collections.defaultdict(list)
for r in inc:
    if r["type"] == "COMMISSION":
        comm[r["symbol"]].append((r["time"], r["asset"], float(r["income"])))
def rd(p): return [json.loads(l) for l in open(p) if l.strip()] if os.path.exists(p) else []
orders_by_day = {d: rd(os.path.join(ROOT, d, "orders.jsonl")) for d in sorted(os.listdir(ROOT)) if d.isdigit() and len(d) == 8}
batches = collections.defaultdict(list)
for d, rows in orders_by_day.items():
    for o in rows:
        if str(o.get("rebalance_id", "")).startswith("FLATTEN-"):
            batches[o["rebalance_id"]].append((d, o))
def other_fill_ts(sym, rid, t0, t1):
    hits = []
    for d, rows in orders_by_day.items():
        for o in rows:
            if o.get("symbol") != sym or o.get("rebalance_id") == rid: continue
            for k in ("first_fill_ts", "last_fill_ts"):
                v = o.get(k)
                if v is not None and t0 <= float(v) <= t1: hits.append(o.get("rebalance_id"))
    return hits
res = {"utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()), "income_sha256": hashlib.sha256(raw).hexdigest(),
       "income_rows": len(inc), "rule": "COMMISSION rows of the leg's symbol in [trip time, batch write time + 5 s]", "batches": {}}
for rid, items in sorted(batches.items()):
    trip = calendar.timegm(time.strptime(rid.split("-", 1)[1], "%Y%m%dT%H%M%SZ"))
    t_end = max(float(o["anchor_ts"]) for _, o in items) + SLACK_S
    day = items[0][0]
    fills = rd(os.path.join(ROOT, day, "fills.jsonl"))
    last = {}
    for i, f in enumerate(fills):
        if f.get("rebalance_id") == rid and f.get("trade_id") is not None: last[(f["symbol"], f["trade_id"])] = f
    exact = collections.defaultdict(lambda: collections.defaultdict(float))
    for (s, _), f in last.items(): exact[s][f.get("commission_asset")] += float(f.get("commission") or 0.0)
    legs = []
    for _, o in items:
        if not o.get("filled_notional"): continue
        s = o["symbol"]; ts = [t for t, _, _ in comm.get(s, [])]
        i, j = bisect.bisect_left(ts, int(trip * 1000)), bisect.bisect_right(ts, int(t_end * 1000))
        proxy = collections.defaultdict(float)
        for t, asset, v in comm.get(s, [])[i:j]: proxy[asset] += -v          # income is negative; fee is positive
        amb = other_fill_ts(s, rid, trip, t_end)
        leg = {"symbol": s, "notional": abs(float(o["filled_notional"])), "proxy_fee_by_asset": {k: round(v, 10) for k, v in proxy.items()},
               "ambiguous_other_fills": sorted(set(amb))}
        if last:
            leg["exact_fee_by_asset"] = {k: round(v, 10) for k, v in exact.get(s, {}).items()}
            ks = set(leg["proxy_fee_by_asset"]) | set(leg["exact_fee_by_asset"])
            leg["control_equal"] = all(abs(leg["proxy_fee_by_asset"].get(k, 0.0) - leg["exact_fee_by_asset"].get(k, 0.0)) <= TOL for k in ks)
        legs.append(leg)
    tot = collections.defaultdict(float)
    for l in legs:
        if not l["ambiguous_other_fills"]:
            for k, v in l["proxy_fee_by_asset"].items(): tot[k] += v
    b = {"day": day, "trip_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime(trip)), "window_s": round(t_end - trip, 3),
         "n_legs": len(legs), "notional": round(sum(l["notional"] for l in legs), 2),
         "n_ambiguous": sum(1 for l in legs if l["ambiguous_other_fills"]), "n_legs_without_proxy": sum(1 for l in legs if not l["proxy_fee_by_asset"]),
         "proxy_fee_by_asset_unambiguous": {k: round(v, 8) for k, v in tot.items()}, "has_exact": bool(last)}
    if last:
        un = [l for l in legs if not l["ambiguous_other_fills"]]
        b["control_equal_legs"] = sum(1 for l in un if l["control_equal"]); b["control_unambiguous_legs"] = len(un)
    b["legs"] = legs
    res["batches"][rid] = b
ctrl = [b for b in res["batches"].values() if b["has_exact"]]
res["control_pass"] = bool(ctrl) and all(b["control_equal_legs"] == b["control_unambiguous_legs"] for b in ctrl)
json.dump(res, open(OUT, "w"), indent=1)
for rid, b in res["batches"].items():
    print(rid, b["n_legs"], "amb", b["n_ambiguous"], "noproxy", b["n_legs_without_proxy"], "fee", b["proxy_fee_by_asset_unambiguous"],
          ("control %d/%d" % (b["control_equal_legs"], b["control_unambiguous_legs"])) if b["has_exact"] else "")
print("LED03_PROXY control_pass", res["control_pass"])
