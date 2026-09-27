#!/usr/bin/env python3
"""rev 1: fills collapsed with pilot_log.collapse_supersedes before summing (run 0 double counted).
NAV closure for the Task B synthesis (READ-ONLY, pooled, no arm split). Window = NAV row at T0 .. NAV row at T1 (daily_nav nav_ts).
funding = sum funding_paid over funding.jsonl rows with settlement_ts in [T0, T1]; commission = sum fills.jsonl commission (USDT) over fills
whose anchor_ts is in [first priced anchor, last priced anchor]; price = layered_book L5 total. usage: nav_closure.py <LAYERED_BOOK.json> <out>"""
import glob, hashlib, json, os, sys, time
L = os.path.expanduser("~/dl_quant_live/state/live/pilot_log"); T0, T1 = 1789562700, 1790397960        # 09-16 12:45Z .. 09-26 04:46Z
A0, A1 = 1789560000, 1790380800                                                                          # priced anchors 09-16 12Z .. 09-26 00Z
days = sorted(d for d in glob.glob(f"{L}/2026091[5-9]") + glob.glob(f"{L}/2026092*"))
def rows(name):
    for d in days:
        p = f"{d}/{name}.jsonl"
        if os.path.exists(p):
            for l in open(p):
                if l.strip(): yield json.loads(l)
nav = {round(float(r["nav_ts"])): float(r["nav"]) for r in rows("daily_nav")}
n0 = min(nav, key=lambda t: abs(t - T0)); n1 = min(nav, key=lambda t: abs(t - T1))
flows = sum(float(r.get("external_flow_usdt") or 0) for r in rows("daily_nav") if T0 < float(r["nav_ts"]) <= T1)
fund = [float(r.get("funding_paid") or 0) for r in rows("funding") if T0 <= float(r["settlement_ts"]) <= T1]
sys.path.insert(0, os.path.expanduser("~/dl_quant_live/live")); import pilot_log as PL
# rev 1 (2026-09-27): the fills table's reader contract — collapse ORIGINAL + SUPERSEDE rows to the last row per (symbol, trade_id) BEFORE
# summing. Run 0 summed raw rows: 37,584 rows = 18,797 executions, commission and notional DOUBLE COUNTED (363.3 vs 181.7).
fl = [r for r in PL.collapse_supersedes(list(rows("fills"))) if A0 <= float(r["anchor_ts"]) < A1 + 14400]
assert {r.get("commission_asset") for r in fl} <= {"USDT"}, "non-USDT commission present"
comm = sum(float(r.get("commission") or 0) for r in fl); notl = sum(abs(float(r.get("fill_notional") or 0)) for r in fl)
LB = json.load(open(sys.argv[1])); price = LB["totals"]["pnl_L5_readback"]
out = {"device": "nav_closure.py", "self_sha256": hashlib.sha256(open(os.path.abspath(__file__), "rb").read()).hexdigest(),
       "layered_book_sha256": hashlib.sha256(open(sys.argv[1], "rb").read()).hexdigest(),
       "nav_start": [time.strftime("%m-%dT%H:%MZ", time.gmtime(n0)), round(nav[n0], 2)], "nav_end": [time.strftime("%m-%dT%H:%MZ", time.gmtime(n1)), round(nav[n1], 2)],
       "nav_change": round(nav[n1] - nav[n0], 2), "external_flows": flows, "price_L5": price, "funding_paid": round(sum(fund), 2), "n_settlements": len(fund),
       "commission": round(-abs(comm) if comm > 0 else comm, 2), "commission_raw_sum": round(comm, 2), "filled_notional": round(notl, 1), "n_fills": len(fl)}
out["closure_sum"] = round(out["price_L5"] + out["funding_paid"] + out["commission"], 2); out["residual"] = round(out["nav_change"] - out["closure_sum"], 2)
json.dump(out, open(sys.argv[2], "w"), indent=1); print(out)
