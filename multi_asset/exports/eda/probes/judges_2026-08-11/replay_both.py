#!/usr/bin/python3
"""Offline replay of BOTH anchors, BEFORE vs AFTER the two producer fixes.

  A. 2026-07-28 08:01:24Z  rebalance A1785225681 — form 1: filled_notional set, avg_fill_px null.
  B. 2026-07-28 08:19:00Z  FLATTEN-20260728T081808Z — form 2: filled_notional NULL (PORTALUSDT).

No venue, no credentials. The backfill is applied by the PRODUCTION functions
(`RebalanceExecutor.apply_commission_to_rows`, `venue_fills.flatten_exec_from_trades`,
`watchdog._write_flatten_rows`) and judged by the PRODUCTION `reconcile.reconcile()`.

★ ONE HONEST LIMIT, STATED UP FRONT. The rebalance children are in our own fills.jsonl, so A is
  replayed on real recorded fills. The FLATTEN's children were never written to any table of ours
  (fill rows are collected per rebalance), so for B they are SUPPLIED here. That is not a free
  parameter: the venue's readback went -18598.7 -> 0.0 contracts, so whatever the real children
  were, their qty sums to 18598.7 — and §4-5b compares QUANTITY, so the fill PRICES cannot change
  its verdict. Demonstrated rather than asserted: B is run twice with different price splits.
"""
import json
import os
import sys
import tempfile
import time

REPO = os.path.expanduser("~/dl_quant_live")
for d in ("live", "ops", "scheduler", "signal"):
    sys.path.insert(0, os.path.join(REPO, d))

import pilot_log as PL          # noqa: E402
import reconcile as RC          # noqa: E402
import binance_executor as EX   # noqa: E402
import venue_fills as VF        # noqa: E402
import watchdog as WD           # noqa: E402

ROOT = os.path.join(REPO, "state", "testnet", "pilot_log")
DAYS = ["20260725", "20260726", "20260727", "20260728"]
ATS_A = 1785225684.348149
RID_A = "A1785225681"
RID_B = "FLATTEN-20260728T081808Z"
PORTAL_QTY = 18598.7            # the venue's own position change: -18598.7 -> 0.0
PORTAL_FILL_TS = 1785226728.403


class _NoVenue:
    mode = "TESTNET"

    def _request(self, *a, **k):
        raise AssertionError("the replay must not contact a venue")


class _TradesStub(_NoVenue):
    """Serves ONLY /fapi/v1/userTrades, with the children of the flatten order we are recovering."""

    def __init__(self, oid, splits):
        self.oid, self.splits = oid, splits

    def _request(self, method, path, params=None, signed=False):
        if path != "/fapi/v1/userTrades":
            raise AssertionError(f"unexpected request {path}")
        if (params or {}).get("symbol") != "PORTALUSDT":
            return []
        return [{"id": 1000 + i, "orderId": self.oid, "side": "BUY", "price": px,
                 "qty": q, "quoteQty": px * q, "commission": 0.0004 * px * q,
                 "commissionAsset": "USDT", "time": int(PORTAL_FILL_TS * 1000), "maker": False}
                for i, (px, q) in enumerate(self.splits)]


# ── form 1: the production stamper, over the day's REAL child fills ──────────────────────────
def backfill_rebalance(one):
    by_symbol = {}
    for f in one["fills"]:
        if f.get("rebalance_id") != RID_A:
            continue
        px, notional = f.get("fill_px"), f.get("fill_notional")
        if not px or notional is None:
            continue
        d = by_symbol.setdefault(f["symbol"], {"maker": {"commission": 0.0, "trades": []},
                                               "topup_taker": {"commission": 0.0, "trades": []}})
        d[f["order_type"]]["trades"].append({"qty": abs(float(notional)) / abs(float(px)),
                                             "quote_qty": abs(float(notional)), "price": float(px),
                                             "commission": f.get("commission") or 0.0,
                                             "commission_asset": f.get("commission_asset")})
        d[f["order_type"]]["commission"] += abs(float(f.get("commission") or 0.0))
    ex = EX.RebalanceExecutor(_NoVenue())
    ex.rows_orders = [r for r in one["orders"] if r.get("rebalance_id") == RID_A]
    sent = {(s, leg) for s in by_symbol for leg in ("maker", "topup_taker")
            if by_symbol[s][leg]["trades"]}
    rep = ex.apply_commission_to_rows(RID_A, by_symbol, set(by_symbol), sent)
    stamped = {(r["symbol"], r["order_type"]): r for r in ex.rows_orders}
    out = [stamped.get((r["symbol"], r["order_type"]), r) if r.get("rebalance_id") == RID_A else r
           for r in one["orders"]]
    return out, rep


# ── form 2: the production ladder recovery + the production row writer ───────────────────────
def rebuild_flatten(one, splits):
    old = [r for r in one["orders"]
           if r.get("rebalance_id") == RID_B and r["symbol"] == "PORTALUSDT"][0]
    oid = 777001
    order = {"symbol": "PORTALUSDT", "side": old["side"], "quantity": PORTAL_QTY,
             "reduce_only": True, "attempt_idx": old["attempt_idx"],
             "_exec": {"submitted": True, "error": None, "filled_notional": None,
                       "avg_fill_px": None, "fill_ts": PORTAL_FILL_TS, "order_id": oid,
                       "mid_at_submit": old["mid_at_submit"]}}
    rep = VF.flatten_exec_from_trades(_TradesStub(oid, splits), [order],
                                      since_ms=int((PORTAL_FILL_TS - 300) * 1000))
    tmp = tempfile.mkdtemp()
    n = WD._write_flatten_rows(tmp, [order], "2026-07-28T08:18:08Z", "replay")
    assert n == 1, n
    day = time.strftime("%Y%m%d", time.gmtime())
    new = PL.read_day(tmp, day)["orders"][0]
    new["rebalance_id"] = RID_B
    return [new if r is old else r for r in one["orders"]], rep, new


def load(fix_a=False, fix_b=False, truncate_to=None, splits=None):
    days, reports = [], {}
    for d in DAYS:
        one = PL.read_day(ROOT, d)
        one = {k: [dict(r) for r in v] for k, v in one.items()}
        if truncate_to is not None:
            one["position_readback"] = [r for r in one["position_readback"]
                                        if float(r["anchor_ts"]) <= truncate_to]
        if d == "20260728" and fix_a:
            one["orders"], reports["A"] = backfill_rebalance(one)
        if d == "20260728" and fix_b:
            one["orders"], reports["B"], reports["row"] = rebuild_flatten(one, splits)
        days.append((d, one))
    return days, reports


def judge(tag, days_data):
    rec = RC.reconcile(days_data)
    latest, unrec = rec["latest"], rec.get("latest_unreconcilable") or []
    state = ("UNKNOWN" if rec["last_reconciled_ats"] is None else
             ("ANOMALOUS" if latest else "PARTIAL" if unrec else "CLEAN"))
    drift = "UNKNOWN" if rec["last_reconciled_ats"] is None else ("DRIFT" if latest else "CLEAN")
    print(f"\n== {tag} ==")
    print(f"  last_reconciled_ats = {rec['last_reconciled_ats']}")
    print(f"  §4-5b = {state}  (n_latest={len(latest)}, n_history={len(rec['anomalies'])})   "
          f"§4-7 drift = {drift}")
    for a in latest[:4]:
        print(f"    - {a['symbol']:10s} {a['kind']:26s} {a.get('order_type')}/"
              f"{a.get('terminal_reason')}")
    return state, drift


def main():
    print("###### A. 08:01:24Z rebalance anchor (readbacks truncated to the trip's evaluation) ##")
    a_before = judge("BEFORE", load(truncate_to=ATS_A)[0])
    d, rep = load(fix_a=True, truncate_to=ATS_A)
    print(f"  form-1 stamper: px_backfilled={rep['A']['px_backfilled']} "
          f"px_unavailable={rep['A']['px_unavailable']}")
    a_after = judge("AFTER (form 1 applied)", d)

    print("\n###### B. 08:19:00Z flatten anchor (all readbacks; this is the CURRENT red) ########")
    b_before = judge("BEFORE", load()[0])
    outs = []
    for label, splits in (("one child @0.00944", [(0.00944, PORTAL_QTY)]),
                          ("three children, 0.00940/0.00944/0.00951",
                           [(0.00940, 9000.0), (0.00944, 5000.0), (0.00951, 4598.7)])):
        d, rep = load(fix_a=True, fix_b=True, splits=splits)
        r = rep["row"]
        print(f"\n  -- price split: {label}")
        print(f"     recovery: {json.dumps({k: v for k, v in rep['B'].items() if v})}")
        print(f"     row: filled_notional={r['filled_notional']} avg_fill_px={r['avg_fill_px']} "
              f"terminal_reason={r['terminal_reason']!r} fee_paid={r['fee_paid']}")
        print(f"     -> derived qty = {r['filled_notional'] / r['avg_fill_px']:.4f} "
              f"(venue's own change: +{PORTAL_QTY})")
        outs.append(judge(f"AFTER (form 1 + form 2, {label})", d))

    print("\n########## SUMMARY ##########")
    print(f"  A  {a_before} -> {a_after}")
    print(f"  B  {b_before} -> {outs[0]} and {outs[1]} (price-independent, as claimed)")
    ok = (a_after == ("CLEAN", "CLEAN") and all(o == ("CLEAN", "CLEAN") for o in outs))
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
