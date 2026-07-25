"""Acceptance for RebalanceExecutor. All DRY_RUN: no credentials, no venue contacted.

What is under test is not the wire format — it is the set of properties the pilot's measurements
depend on. Two in particular:
  * every row carries mid_at_anchor (M1's baseline; the alternative baseline differs by more than
    the entire distance between PASS and FAIL);
  * every dropped name is LABELLED with a terminal_reason (a silently-lagging book is
    indistinguishable from a correctly-tracking one).
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import binance_broker as BB          # noqa: E402
import binance_executor as EX        # noqa: E402
import pilot_log as PL               # noqa: E402

FAILS = 0


def check(name, cond, extra=""):
    global FAILS
    print(f"  {'OK  ' if cond else 'FAIL'}  {name}{('  — ' + str(extra)) if extra else ''}")
    if not cond:
        FAILS += 1
    return cond


def mk(band=0.0, halted=False):
    b = BB.BinanceBroker(); b.arm()
    if halted:
        b.halt_opening_orders("test")
    e = EX.RebalanceExecutor(b, band_bps=band)
    e.filters.f = {"BTCUSDT": {"tick": 0.1, "step": 0.001, "min_notional": 100.0},
                   "ETHUSDT": {"tick": 0.01, "step": 0.001, "min_notional": 20.0},
                   "TINYUSDT": {"tick": 0.0001, "step": 1.0, "min_notional": 5.0}}
    return b, e


MIDS = {"BTCUSDT": 60000.0, "ETHUSDT": 3000.0, "TINYUSDT": 0.5}

print("[A] the anchor is captured before anything else exists")
b, e = mk()
ts, mids = e.capture_anchor(list(MIDS))
check("anchor_ts is a real timestamp", ts > 1.7e9, ts)
check("a mid exists for every requested symbol", set(mids) == set(MIDS))

print("\n[B] ★ every emitted row carries mid_at_anchor, including the DROPPED ones")
b, e = mk()
# ETH target is deliberately BELOW its 20 USDT min-notional: that is the case under test.
plans = e.plan({"BTCUSDT": 50_000, "ETHUSDT": 10, "TINYUSDT": 1_000},
               {"BTCUSDT": 0, "ETHUSDT": 0, "TINYUSDT": 0}, MIDS)
live = e.submit_maker(plans, ts, "RB1")
e.topup(live, {"BTCUSDT": 25_000}, ts, "RB1")
check("rows were emitted", len(e.rows_orders) > 0, len(e.rows_orders))
check("mid_at_anchor present and non-null on EVERY row",
      all(r["mid_at_anchor"] is not None for r in e.rows_orders))
check("notional_currency stamped on every row",
      all(r["notional_currency"] == "USDT" for r in e.rows_orders))

print("\n[C] ★ every drop is labelled — nothing vanishes silently")
reasons = {r["terminal_reason"] for r in e.rows_orders}
check("all terminal_reasons are in the schema's enum",
      reasons <= PL.TERMINAL_REASONS, sorted(reasons))
eth = [r for r in e.rows_orders if r["symbol"] == "ETHUSDT"]
check("the sub-min-notional name is labelled skipped_min_notional, not dropped",
      any(r["terminal_reason"] == "skipped_min_notional" for r in eth), [r["terminal_reason"] for r in eth])

print("\n[D] ★ the top-up is emitted for a partial fill — it is mandatory, not optional")
btc = [r for r in e.rows_orders if r["symbol"] == "BTCUSDT"]
check("maker leg recorded as partial_expired",
      any(r["order_type"] == "maker" and r["terminal_reason"] == "partial_expired" for r in btc))
check("a topup_taker attempt WAS emitted for the residual",
      any(r["order_type"] == "topup_taker" for r in btc),
      [(r["order_type"], r["terminal_reason"]) for r in btc])
check("top-up carries attempt_idx=2 (M3's denominator is attempt 1 only)",
      all(r["attempt_idx"] == 2 for r in btc if r["order_type"] == "topup_taker"))

print("\n[E] a spread wider than 25bps is ABANDONED and RECORDED, never chased")
b, e = mk()
plans = e.plan({"BTCUSDT": 50_000}, {"BTCUSDT": 0}, MIDS)
live = e.submit_maker(plans, ts, "RB2")
e.topup(live, {"BTCUSDT": 10_000}, ts, "RB2", spreads_bps={"BTCUSDT": 40.0})
tu = [r for r in e.rows_orders if r["order_type"] == "topup_taker"]
check("abandoned_spread_gt_25bps recorded", any(r["terminal_reason"] == "abandoned_spread_gt_25bps" for r in tu))
check("the abandoned gap keeps its intended_notional (so M5 can see it)",
      all(r["intended_notional"] not in (None, 0) for r in tu))

print("\n[F] ★ when the halt is engaged, NEW exposure is refused but the row still appears")
b, e = mk(halted=True)
plans = e.plan({"BTCUSDT": 50_000}, {"BTCUSDT": 0}, MIDS)
live = e.submit_maker(plans, ts, "RB3")
check("no order went live while halted", len(live) == 0, len(live))
check("the refusal is still recorded as a row", len(e.rows_orders) == 1)
check("mid_at_anchor survives even on the refused row",
      e.rows_orders[0]["mid_at_anchor"] == 60000.0)

print("\n[G] no-trade band suppresses trading WITHOUT fabricating a failure reason")
b, e = mk(band=50.0)
# a 1 USDT tweak on a 50k book = 0.2bps of gross, i.e. genuinely inside a 50bps band
plans = e.plan({"BTCUSDT": 50_001}, {"BTCUSDT": 50_000}, MIDS)
inside = [p for p in plans if p.get("skip", "MISSING") is None]
check("a within-band delta is marked skip=None (no trade, no error)", len(inside) == 1)
e.submit_maker(plans, ts, "RB4")
check("a within-band name emits NO order row at all", len(e.rows_orders) == 0, len(e.rows_orders))

print("\n[H] rounding respects venue filters (wrong rounding => rejection => unusable data)")
b, e = mk()
check("qty floors to step size", e.filters.round_qty("BTCUSDT", 0.0019) == 0.001,
      e.filters.round_qty("BTCUSDT", 0.0019))
check("price floors to tick size", e.filters.round_px("ETHUSDT", 3000.017) == 3000.01,
      e.filters.round_px("ETHUSDT", 3000.017))

print("\n[I] anchor row is schema-shaped and hashes the target vector")
b, e = mk()
row = e.anchor_row(ts, MIDS, {"BTCUSDT": 50_000}, 50_000, 2, "calm", "normfix", "abc123")
missing = set(PL.SCHEMA["anchors"]["required"]) - set(row)
check("anchor row has every required field", not missing, sorted(missing) or "complete")
check("regime is stamped at the anchor (auditable before markout is knowable)",
      row["regime_at_anchor"] == "calm")
row2 = e.anchor_row(ts, MIDS, {"BTCUSDT": 50_001}, 50_000, 2, "calm", "normfix", "abc123")
check("a different target vector hashes differently",
      row["target_vector_hash"] != row2["target_vector_hash"])

print(f"\n{'ALL PASS' if FAILS == 0 else str(FAILS) + ' FAIL'}")
sys.exit(1 if FAILS else 0)
