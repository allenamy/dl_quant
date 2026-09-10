#!/usr/bin/python3
"""Round 3 (independent review 31fa3e4e A5): rebuild the FILLS rows of the 2026-09-09 16:45Z protective flatten
(rid FLATTEN-20260909T164536Z) from the venue, by ORDER IDENTITY — never by a time window.

WHY `ops/backfill_fills.py` refused: the flatten's MARKET reduce-only orders were sent WITHOUT a client id
(`flatten_all` lets the venue mint one), so the generic tool — which attributes trades through our
`<rebalance_id>-<symbol>-<n>` client ids — rebuilt 0 legs and correctly refused to write rows it could not attribute.

WHAT THIS DOES: for each of the 243 symbols in the flatten's orders rows, read `allOrders` (read-only) and select
the venue's own records that ARE the flatten: type MARKET, reduceOnly true, time inside the flatten window. Their
orderIds are the leg identities. Then `userTrades` (read-only) and keep exactly the trades whose orderId is one of
those — an exact join, the same one the anchor uses. Build schema-v2 fills rows with `venue_fills.fill_rows_from_trades`
(order_type := protective_flatten, attempt_idx := 1), validate every row, and RECONCILE before anything else:
  Σ|fill_notional| vs Σ|filled_notional| of the 243 orders rows (per symbol and total),
  n trades vs the venue's COMMISSION rows in the window, Σ commission vs the venue's income figure.
Refuses on any mismatch. Dry run writes rows to a scratch file + a receipt; `--apply` (user's word only) appends them.

Reads: ~243 allOrders + ~243 userTrades signed GETs, paced. Run OUTSIDE anchor windows only.
"""
import argparse, json, os, sys, time, collections
LIVE = os.path.expanduser("~/dl_quant_live")
for _d in ("live", "ops", "scheduler", "signal"):
    sys.path.insert(0, os.path.join(LIVE, _d))
os.chdir(LIVE)
import envfile as _envfile; _envfile.load()
os.environ.setdefault("BINANCE_LIVE_CONFIRM", "I_UNDERSTAND"); os.environ["LIVE_MODE"] = "LIVE"
import binance_broker as BB, pilot_log as PL, state_root as SR, venue_fills as VF

RID, DAY = "FLATTEN-20260909T164536Z", "20260909"
WIN_LO, WIN_HI = 1788972300000, 1788972540000          # 16:45:00Z .. 16:49:00Z (orders 16:45:36-16:47:21Z)
VENUE_N_TRADES, VENUE_COMMISSION = 3094, -116.378476    # /fapi/v1/income COMMISSION rows in [16:45, 16:50]Z, read 2026-09-10 01:21Z with
# 15-second sub-windows + (tranId, type, symbol, asset) dedupe. ★ The first figure I journaled (3,049 / -114.7707) came from a
# single-window query that advanced startTime past the last row's millisecond — the SAME saturation defect the independent
# review named (A2): 45 rows lost at page boundaries. The orderId join below found 3,095 trades / 116.378476, and the
# sub-windowed income agrees to the cent; one trade carries zero commission and has no income row (3,095 vs 3,094).
SCRATCH = os.path.expanduser("~/cc_tmp/e0909g_sim"); os.makedirs(SCRATCH, exist_ok=True)
OUT_ROWS = os.path.join(SCRATCH, "flatten_fills_20260909_DRYRUN.jsonl")
RECEIPT = os.path.expanduser("~/Desktop/quant_research/multi_asset/exports/live/pilot_journal/backfill_flatten_fills_20260909_dryrun.json")


def utc(ms): return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime(ms / 1000.0))


def main():
    ap = argparse.ArgumentParser(); ap.add_argument("--apply", action="store_true"); a = ap.parse_args()
    root = SR.paths_for("LIVE")["pilot_log"]; day = PL.read_day(root, DAY)
    orders = [o for o in day.get("orders", []) if o.get("rebalance_id") == RID]
    have = [f for f in day.get("fills", []) if f.get("rebalance_id") == RID]
    syms = sorted({o["symbol"] for o in orders}); ats = float(orders[0]["anchor_ts"])
    want = {o["symbol"]: float(o.get("filled_notional") or 0.0) for o in orders}
    print(f"orders rows {len(orders)} on {len(syms)} symbols, anchor_ts {ats}; existing fills rows for rid: {len(have)}")
    if have:
        print("REFUSING: fills rows for this rid already exist"); return 2
    b = BB.BinanceBroker("LIVE")
    legs, by_sym_orders, missing = {}, {}, []
    for i, s in enumerate(syms):
        rows = b._request("GET", "/fapi/v1/allOrders", {"symbol": s, "startTime": WIN_LO - 120000, "limit": 200}, signed=True) or []
        mine = [r for r in rows if str(r.get("type")) == "MARKET" and bool(r.get("reduceOnly"))
                and WIN_LO <= int(r.get("time") or 0) <= WIN_HI]
        if not mine:
            missing.append(s)
        for r in mine:
            legs[int(r["orderId"])] = {"symbol": s, "leg": "protective_flatten", "client_id": r.get("clientOrderId"), "tif": "IOC",
                                       "executedQty": r.get("executedQty"), "cumQuote": r.get("cumQuote"), "status": r.get("status")}
        by_sym_orders[s] = [int(r["orderId"]) for r in mine]
        time.sleep(0.25)
        if i % 40 == 39: print(f"  allOrders {i+1}/{len(syms)} … {len(legs)} flatten orders", flush=True); time.sleep(2.0)
    print(f"flatten orders identified at the venue: {len(legs)} on {len(syms) - len(missing)} symbols; symbols with none: {missing[:8]} ({len(missing)})")
    trades_all = {}
    for k in range(0, len(syms), 40):
        chunk = syms[k:k + 40]
        trades_all.update(VF.user_trades_for(b, chunk, since_ms=WIN_LO - 120000))
        time.sleep(3.0)
    per_sym, rows_in, n_tr, n_unattr = {}, {}, 0, 0
    for s in syms:
        d = trades_all.get(s) or {"trades": []}
        mine = [dict(t, leg="protective_flatten") for t in d["trades"] if int(t.get("order_id") or 0) in set(by_sym_orders.get(s, []))]
        n_unattr += len(d["trades"]) - len(mine)
        n_tr += len(mine)
        rows_in[s] = {"trades": mine}
        per_sym[s] = {"n": len(mine), "gross": sum(abs(float(t["quote_qty"])) for t in mine),
                      "fee": sum(float(t["commission"]) for t in mine), "orders_filled": abs(want.get(s, 0.0))}
    rows = VF.fill_rows_from_trades(rows_in, ats, RID)
    for r in rows:
        r["order_type"] = "protective_flatten"; r["attempt_idx"] = 1
        r["rebuilt_from_venue"] = "orderId join: allOrders MARKET reduceOnly in the flatten window -> userTrades.orderId (round 3, review 31fa3e4e A5)"
    bad = []
    for r in rows:
        try: PL.validate("fills", r)
        except Exception as e: bad.append((r["symbol"], str(e)[:100]))
    gross = sum(abs(float(r["fill_notional"] or 0)) for r in rows); fee = sum(float(r["commission"] or 0) for r in rows)
    want_gross = sum(abs(v) for v in want.values())
    mism = [(s, round(per_sym[s]["gross"], 2), round(per_sym[s]["orders_filled"], 2)) for s in syms
            if abs(per_sym[s]["gross"] - per_sym[s]["orders_filled"]) > max(0.05, 1e-4 * per_sym[s]["orders_filled"])]
    rec = {"rid": RID, "utc": utc(time.time() * 1000), "n_symbols": len(syms), "n_flatten_orders_at_venue": len(legs),
           "symbols_without_flatten_order": missing, "n_trades_attributed": n_tr, "n_trades_in_window_not_ours": n_unattr,
           "rows_built": len(rows), "rows_invalid": bad[:5], "sum_fill_notional": round(gross, 4), "orders_sum_filled": round(want_gross, 4),
           "sum_commission": round(fee, 6), "venue_income_commission_rows": VENUE_N_TRADES, "venue_income_commission": VENUE_COMMISSION,
           "per_symbol_mismatch": mism[:20], "n_per_symbol_mismatch": len(mism), "applied": False, "rows_file": OUT_ROWS}
    with open(OUT_ROWS, "w") as f:
        for r in rows: f.write(json.dumps(r) + "\n")
    _n_fee_rows = sum(1 for r in rows if float(r.get("commission") or 0.0) != 0.0)   # income writes no row for a 0 fee
    ok = (not bad and not missing and not mism and _n_fee_rows == VENUE_N_TRADES and abs(fee + abs(VENUE_COMMISSION)) < 0.01
          and abs(gross - want_gross) < 1.0)
    rec_extra = {"n_trades_with_nonzero_commission": _n_fee_rows}
    rec["reconciled"] = ok; rec.update(rec_extra)
    json.dump(rec, open(RECEIPT, "w"), indent=1, default=str)
    print(json.dumps({k: rec[k] for k in rec if k not in ("symbols_without_flatten_order", "per_symbol_mismatch")}, default=str))
    print("mismatches:", mism[:10])
    if not ok:
        print("NOT RECONCILED — dry run only, nothing written to the ledger; fix the join before any --apply"); return 2
    if not a.apply:
        print("DRY RUN reconciled — rows in", OUT_ROWS, "; re-run with --apply on the user's word"); return 0
    lg = PL.PilotLogger(root, day=DAY)
    try:
        for r in rows: lg.fill(**r)
    finally:
        lg.close()
    rec["applied"] = True; json.dump(rec, open(RECEIPT, "w"), indent=1, default=str)
    print(f"APPLIED {len(rows)} fills rows"); return 0


if __name__ == "__main__":
    sys.exit(main())
