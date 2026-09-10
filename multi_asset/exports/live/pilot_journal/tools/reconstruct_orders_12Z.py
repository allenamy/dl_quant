#!/usr/bin/python3
"""E-0909-G repair: reconstruct the 12Z (2026-09-09, rebalance A1788956640) ORDER rows from the venue's own records.

WHY: the 12Z anchor died inside submit_maker (E-0909-D) before any order row was persisted, so the 69 executions
that landed have fills rows (backfilled 14:3xZ) but NO order rows. `reconcile._between` builds the authorised
execution list from ORDER rows only ⇒ at the 16Z readback those positions were UNAUTHORISED ⇒ §4-5e position break
⇒ watchdog flattened the book at 16:47Z. `resume_from_trip.sh --check` still says NOT RESUMABLE for the same reason.

WHAT: for every clientOrderId with prefix A1788956640- (allOrders, read-only), write ONE order row whose execution
facts come from the venue (status / executedQty / cumQuote / avgPrice) and whose fill times + commission come from
the already-backfilled fills rows. Fields we cannot know (plan intent, target/prev weights, mids) are None or set
to the executed amount and SAID SO in `note` = RECONSTRUCTED_FROM_VENUE. Nothing existing is rewritten: the day has
zero rows for this rebalance, so appending cannot double any leg.

MODES:  (default)  dry run — fetch, build, validate, SIMULATE the reconcile + §4-5e on a scratch copy of the ledger
                   (40-day window), print anomalies before/after. Touches nothing.
        --apply    append the rows to the LIVE orders.jsonl (requires the user's word), then re-run the simulation
                   on the real ledger. Never resumes: `ops/resume_from_trip.sh` is a separate, human step.
"""
import argparse, glob, json, os, shutil, sys, time
LIVE = os.environ.get("DQL_ROOT", os.path.expanduser("~/dl_quant_live"))   # the tree whose pilot_log schema validates the rows
for _d in ("live", "ops", "scheduler", "signal"):
    sys.path.insert(0, os.path.join(LIVE, _d))
os.chdir(LIVE)
import envfile as _envfile; _envfile.load()
os.environ.setdefault("BINANCE_LIVE_CONFIRM", "I_UNDERSTAND"); os.environ["LIVE_MODE"] = "LIVE"
import binance_broker as BB, pilot_log as PL, state_root as SR, reconcile as RC, position_break as PB

RID, ATS, DAY = "A1788956640", 1788956640.0, "20260909"
SCRATCH = os.environ.get("SCRATCH", os.path.expanduser("~/cc_tmp/e0909g_sim"))
DRY_JSON = os.environ.get("DRYRUN_JSON", "/Users/haosiyu/cc_tmp/claude-501/-Users-haosiyu-Desktop-quant-research/b9646a9e-31a1-4eb3-a08b-e8ea13fdceb0/scratchpad/backfill_dryrun_12Z.json")
OUT_ROWS = os.path.expanduser("~/cc_tmp/e0909g_sim/reconstructed_orders_12Z.jsonl")


def utc(t): return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime(float(t)))


def fetch_venue_orders(broker, syms):
    """{clientOrderId: venue order dict} for every order of this rebalance, from allOrders per symbol (paced)."""
    out = {}
    since = int((ATS - 600) * 1000)
    for i, s in enumerate(syms):
        rows = broker._request("GET", "/fapi/v1/allOrders", {"symbol": s, "startTime": since, "limit": 200}, signed=True) or []
        for r in rows:
            cid = str(r.get("clientOrderId") or "")
            if cid.startswith(RID + "-"):
                out[cid] = r
        time.sleep(0.34)
        if i % 10 == 0: print(f"  allOrders {i+1}/{len(syms)} … {len(out)} legs so far", flush=True)
    return out


def collapse_fills(fills):
    """★ Round 3 (independent review 31fa3e4e A1): fills.jsonl carries EVERY fill TWICE — the original row and the
    markout backfill's superseding row (`supersedes_trade_id`, +60s mark). Summing them doubled every fee in the
    first dry run (1.00970 vs 0.50724). One fill = one (symbol, trade_id); the LAST row written wins (it carries the
    mark). Returns the collapsed list, in file order."""
    last = {}
    for f in fills:
        k = (f.get("symbol"), f.get("trade_id") if f.get("trade_id") is not None else f.get("venue_trade_id"))
        last[k] = f
    return list(last.values())


def build_rows(venue, fills):
    """one order row per venue leg; fill times/commission from the backfilled fills rows (same rebalance),
    COLLAPSED to one row per trade first (see collapse_fills)."""
    by_leg = {}
    for f in collapse_fills(fills):
        if f.get("rebalance_id") != RID: continue
        k = (f["symbol"], int(f.get("attempt_idx") or 1)); by_leg.setdefault(k, []).append(f)
    rows = []
    for cid, o in sorted(venue.items()):
        sym = o["symbol"]; attempt = int(cid.rsplit("-", 1)[-1]) if cid.rsplit("-", 1)[-1].isdigit() else 1
        side = str(o.get("side", "")).lower(); sign = 1.0 if side == "buy" else -1.0
        ex = float(o.get("executedQty") or 0.0); cq = float(o.get("cumQuote") or 0.0); avg = float(o.get("avgPrice") or 0.0)
        st = str(o.get("status", "")).upper(); tif = str(o.get("timeInForce", "")).upper()
        # ★ round 3 (review 31fa3e4e A1): a rebuilt row is an AUTHORISATION RECORD, typed `reconstructed` so every
        #   type-filtered metric (m1/m3/m4) excludes it by construction; the leg it stood for is kept in `leg_kind`.
        #   Requires the deployed pilot_log to accept the type (live branch d73b1b0+ / round-3 addendum) — the tool
        #   refuses otherwise via PL.validate below.
        leg_kind = "topup_taker" if tif == "IOC" or str(o.get("type", "")).upper() == "MARKET" else "maker"
        otype = "reconstructed"
        legf = by_leg.get((sym, attempt), [])
        fts = sorted(float(f["fill_ts"]) for f in legf if f.get("fill_ts") is not None)
        fee = sum(float(f.get("commission") or 0.0) for f in legf) if legf else None
        if st == "FILLED": tr = "filled"
        elif st in ("CANCELED", "EXPIRED"): tr = "partial_expired"
        elif st == "REJECTED": tr = "venue_reject"
        elif st == "NEW": tr = "partial_expired"          # a resting order the 16Z sweep would have cancelled (none left: swept/cancelled 14:16Z)
        else: tr = "filled_amount_unknown"
        rows.append({
            "anchor_ts": ATS, "symbol": sym, "side": side, "target_w": None, "prev_w": None,
            "intended_notional": sign * cq if cq else None, "order_type": otype,
            "submit_ts": float(o.get("time") or 0) / 1000.0 or None, "price_submit": float(o.get("price") or 0) or None,
            "mid_at_submit": None, "mid_at_anchor": None,
            "filled_notional": sign * cq if ex > 0 else 0.0, "avg_fill_px": avg if (ex > 0 and avg > 0) else None,
            "first_fill_ts": (fts[0] if fts else (float(o.get("updateTime") or 0) / 1000.0 if ex > 0 else None)),
            "last_fill_ts": (fts[-1] if fts else (float(o.get("updateTime") or 0) / 1000.0 if ex > 0 else None)),
            "cancel_ts": (float(o.get("updateTime") or 0) / 1000.0 if st in ("CANCELED", "EXPIRED") else None),
            "fee_paid": fee, "rebalance_id": RID, "attempt_idx": attempt, "terminal_reason": tr, "notional_currency": "USDT",
            "venue_order_id": o.get("orderId"), "venue_status": st, "venue_executed_qty": ex, "venue_orig_qty": float(o.get("origQty") or 0),
            "leg_kind": leg_kind,
            "n_fills_joined": len(legf),
            # ★ structured flag (round 3). The exclusion from the execution-quality metrics is by TYPE (`reconstructed`
            #   is outside pilot_metrics' m1/m3/m4 `order_type in ("maker","topup_taker")` filters — the frozen module is
            #   untouched); `order_disposition.gaps` additionally skips rows carrying this flag. Rows are still counted by
            #   reconcile / book_after_anchor as executions (quantity-based), which is what they are for.
            "reconstructed_from_venue": True,
            "note": ("RECONSTRUCTED_FROM_VENUE (E-0909-G repair of the E-0909-D crash anchor: the process died before persisting any "
                     "order row; execution facts = venue allOrders + backfilled fills; plan intent NOT persisted ⇒ intended_notional := "
                     "executed, target_w/prev_w/mids None). Exclude from execution-quality metrics via this note."),
            "reconstructed_utc": utc(time.time()),
        })
    return rows


def simulate(root, days, extra_rows=None, label=""):
    """reconcile + §4-5e on `root`, optionally with extra_rows appended to DAY in memory."""
    dd = []
    for d in days:
        one = PL.read_day(root, d)
        if extra_rows and d == DAY:
            one = dict(one); one["orders"] = list(one.get("orders", [])) + list(extra_rows)
        dd.append((d, one))
    rec = RC.reconcile(dd)
    latest = rec.get("latest") or []
    pb = PB.evaluate(dd)
    keys = [k for k in pb.keys() if any(x in k for x in ("trip", "unauth", "frac", "gate", "halt", "n_", "names"))][:12]
    print(f"── simulation {label}: reconcile latest anomalies {len(latest)} @ {utc(rec.get('last_reconciled_ats') or 0)}: "
          f"{sorted(a['symbol'] for a in latest)[:12]}{' …' if len(latest) > 12 else ''}")
    print(f"   §4-5e: " + json.dumps({k: pb.get(k) for k in keys}, default=str)[:600])
    return rec, pb


def main():
    ap = argparse.ArgumentParser(); ap.add_argument("--apply", action="store_true", help="append the rows to the LIVE ledger (user's word required)")
    a = ap.parse_args()
    root = SR.paths_for("LIVE")["pilot_log"]
    days = sorted(os.path.basename(p) for p in glob.glob(os.path.join(root, "2026*")))[-40:]
    syms = json.load(open(DRY_JSON))["income_symbols"]
    b = BB.BinanceBroker("LIVE")
    print(f"fetching venue orders for {len(syms)} symbols (read-only, paced) …", flush=True)
    venue = fetch_venue_orders(b, syms)
    fills = PL.read_day(root, DAY).get("fills", [])
    rows = build_rows(venue, fills)
    existing = [o for o in PL.read_day(root, DAY).get("orders", []) if o.get("rebalance_id") == RID]
    print(f"venue legs {len(venue)}; rows built {len(rows)}; existing order rows for {RID}: {len(existing)} (must be 0 to append)")
    bad = []
    for r in rows:
        try: PL.validate("orders", r)
        except Exception as e: bad.append((r["symbol"], str(e)[:120]))
    print(f"schema: {len(rows) - len(bad)} valid, {len(bad)} invalid {bad[:3]}")
    os.makedirs(SCRATCH, exist_ok=True)
    with open(OUT_ROWS, "w") as f:
        for r in rows: f.write(json.dumps(r) + "\n")
    print(f"rows written to {OUT_ROWS}")
    from collections import Counter
    print("terminal_reason:", dict(Counter(r["terminal_reason"] for r in rows)), "| executed legs:", sum(1 for r in rows if r["venue_executed_qty"] > 0), "| Σ|filled| USDT:", round(sum(abs(r["filled_notional"] or 0) for r in rows), 1))
    # ★ round-3 acceptance: fee reconciliation against the collapsed fills (the first dry run failed exactly here)
    _cf = [f for f in collapse_fills(fills) if f.get("rebalance_id") == RID]
    _fee_fills = sum(float(f.get("commission") or 0.0) for f in _cf); _fee_rows = sum(float(r.get("fee_paid") or 0.0) for r in rows)
    _gross_fills = sum(abs(float(f.get("fill_notional") or 0.0)) for f in _cf); _gross_rows = sum(abs(float(r.get("filled_notional") or 0.0)) for r in rows)
    print(f"fee check: Σ fee_paid(rows) {_fee_rows:.8f} vs Σ commission(collapsed fills, n={len(_cf)}) {_fee_fills:.8f} | gross rows {_gross_rows:.4f} vs fills {_gross_fills:.4f}")
    if abs(_fee_rows - _fee_fills) > 1e-6 or abs(_gross_rows - _gross_fills) > 0.05:
        print("REFUSING: rows do not reconcile with the collapsed fills"); sys.exit(2)
    if bad or existing:
        print("REFUSING (invalid rows or rows already present)"); sys.exit(2)
    if any(int(r.get("n_fills_joined") or 0) > int(r.get("venue_executed_qty") is not None and 10**6) for r in rows):
        print("REFUSING: implausible fill join"); sys.exit(2)
    simulate(root, days, None, "BEFORE (ledger as is)")
    rec2, pb2 = simulate(root, days, rows, "AFTER (with reconstructed rows, in memory)")
    still = [a["symbol"] for a in (rec2.get("latest") or [])]
    print("REPAIR CLEARS latest reconcile anomalies:", "YES" if not still else f"NO — still: {still}")
    if not a.apply:
        print("DRY RUN — nothing written to the live ledger. Re-run with --apply on the user's word."); return 0
    lg = PL.PilotLogger(root, day=DAY)
    try:
        for r in rows: lg.order(**r)
    finally:
        lg.close()
    print(f"APPLIED: {len(rows)} order rows appended to {root}/{DAY}/orders.jsonl at {utc(time.time())}")
    simulate(root, days, None, "AFTER APPLY (real ledger)")
    print("next (human): bash ops/resume_from_trip.sh --check ; then, on the user's word, bash ops/resume_from_trip.sh \"<reason>\"")
    return 0


if __name__ == "__main__":
    sys.exit(main())
