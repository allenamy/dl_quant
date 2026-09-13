#!/usr/bin/python3
"""Round-3 defect probe — the three §3.C defects read off ANY tree, old or new.

    /usr/bin/python3 round3_defect_probe.py /Users/haosiyu/cc_tmp/exec_w2_prev3   # pre-round-3
    /usr/bin/python3 round3_defect_probe.py /Users/haosiyu/cc_tmp/exec_w2         # fixed

★ WHY A SEPARATE DEVICE. The two suites abort with a KeyError on the pre-round-3 readers (the new
  keys do not exist there), so the red receipt cannot show what those readers SAID. This prints
  it: the same three fixtures through both trees, side by side, with no assertion of its own.
  The fixtures are the researcher's (REVIEW_code_and_research_2026-09-13 §3.C), rebuilt through
  the production writer `pilot_log.PilotLogger` rather than hand-built dicts.

*** READ-ONLY. Temp pilot_log trees only; no venue, no credentials, nothing written outside
    tempfile.mkdtemp(). ***
"""
import io
import contextlib
import os
import sys
import tempfile

REPO = sys.argv[1] if len(sys.argv) > 1 else "/Users/haosiyu/cc_tmp/exec_w2"
for _d in ("live", "ops", "scheduler", "signal"):
    sys.path.insert(0, os.path.join(REPO, _d))
import cost_buckets as CB              # noqa: E402
import daily_summary as DS             # noqa: E402
import pilot_log as PL                 # noqa: E402
import score_post_fix as SPF           # noqa: E402

DAY, T0 = "20260805", 1785931247.0


def tree(legs, sides=None, unknown_fill=False):
    d = tempfile.mkdtemp(prefix="r3probe_")
    root = os.path.join(d, "pilot_log")
    lg = PL.PilotLogger(root, DAY)
    rid = f"A{int(T0)}"
    lg.anchor(anchor_ts=T0, target_vector_hash="h", realized_gross=0, target_gross=1000.0,
              n_names_skipped=0, regime_at_anchor="calm",
              mid_at_anchor_vector={l[0]: l[2] for l in legs}, factor_version="{}", panel_hash="p",
              rebalance_id=rid, opening_halted=False,
              weights={"king": 0.5, "s2": 0.17, "funding": 0.17, "size": 0.16})
    for (s, v, mid, px, fee) in legs:
        lg.order(anchor_ts=T0, symbol=s, side=(sides or {}).get(s, "buy" if v > 0 else "sell"),
                 target_w=0.1, prev_w=0.0, intended_notional=abs(v), order_type="maker",
                 submit_ts=T0 + 1, price_submit=mid, mid_at_submit=mid, mid_at_anchor=mid,
                 filled_notional=v, avg_fill_px=px, first_fill_ts=T0 + 2, last_fill_ts=T0 + 3,
                 cancel_ts=None, fee_paid=fee, rebalance_id=rid, attempt_idx=1,
                 terminal_reason="filled", notional_currency="USDT", fee_all_usdt=True,
                 fee_conversion=None)
    if unknown_fill:
        lg.order(anchor_ts=T0, symbol="NNNUSDT", side="buy", target_w=0.1, prev_w=0.0,
                 intended_notional=100.0, order_type="maker", submit_ts=T0 + 1, price_submit=100.0,
                 mid_at_submit=100.0, mid_at_anchor=100.0, filled_notional=None, avg_fill_px=None,
                 first_fill_ts=None, last_fill_ts=None, cancel_ts=None, fee_paid=None,
                 rebalance_id=rid, attempt_idx=1, terminal_reason="filled_amount_unknown",
                 notional_currency="USDT")
    lg.daily_nav(day=DAY, target_gross=1000.0, nav=10000.0, realised_pnl=0.0, unrealised_pnl=0.0,
                 sizing_policy="constant_leverage_2.00", nav_ts=T0 + 60)
    lg.close()
    return root


NORMAL = ("SSSUSDT", 100.0, 100.0, 100.01, 0.02)          # +1bps adverse, 2bps fee -> 3.00bps
BIGSLIP = ("TTTUSDT", 100.0, 100.0, 101.0, 0.02)          # +100bps adverse

print(f"REPO = {REPO}\n")
print("=" * 100)
print("DEFECT 1 — score_post_fix E6: the verdict's population vs the published number's population")
print("=" * 100)
for label, legs, sides in (("single row, side=None", [NORMAL], {"SSSUSDT": None}),
                           ("normal + side=None (bigger slip)", [NORMAL, BIGSLIP],
                            {"TTTUSDT": None}),
                           ("clean control (all sides readable)", [NORMAL, BIGSLIP], None)):
    e6 = SPF.score(root=tree(legs, sides), day=DAY)["E6_cost_comparable"]
    cc = e6.get("carrier_consistency") or {}
    print(f"\n  {label}")
    print(f"    verdict                {e6['verdict']}")
    print(f"    measurement_complete   {e6['measurement_complete']} (bucket-derived) "
          f"| m1 bit {e6.get('m1_measurement_complete')}")
    print(f"    c_bps_overall (m1)     {e6['c_bps_overall']}")
    print(f"    cost_bps_displayed     {e6.get('cost_bps_displayed', '<key absent: pre-round-3>')}")
    print(f"    carrier consistent     {cc.get('consistent', '<key absent: pre-round-3>')}")
    for w in cc.get("why_not") or []:
        print(f"      why_not: {w[:120]}")

print("\n" + "=" * 100)
print("DEFECT 2 — first_anchor_review §3c: completeness computed after the unknown rows are dropped")
print("=" * 100)
rows = PL.read_day(tree([NORMAL, ("UUUUSDT", -100.0, 100.0, 99.99, 0.02)], unknown_fill=True),
                   DAY)["orders"]
print(f"  rows in the anchor: {len(rows)} "
      f"({sum(1 for r in rows if CB.filled_abs(r) is None)} with an UNKNOWN fill amount)")
print(f"  bucket completeness over the FULL population : "
      f"{CB.bucket_fills(rows)['measurement_complete']}")
print(f"  bucket completeness after the `ex` filter    : "
      f"{CB.bucket_fills([r for r in rows if CB.filled_abs(r)])['measurement_complete']}")
print("  what the screen PRINTS:")
_src = open(os.path.join(REPO, "ops", "first_anchor_review.py")).read()
_ns = {"CB": CB, "mine": rows, "print": print}
_leg_src = _src[_src.index("        def _leg(rows, label):"):_src.index("        _leg([r for r in")]
exec(compile("import cost_buckets as CB\n"
             + "\n".join(l[8:] for l in _leg_src.splitlines()), "leg", "exec"), _ns)
cap = io.StringIO()
with contextlib.redirect_stdout(cap):
    _ns["_leg"]([r for r in rows if CB.filled_abs(r)], "ex-filtered")   # the pre-round-3 call
    _ns["_leg"](rows, "full rows")                                       # the round-3 call
print("\n".join("    " + l for l in cap.getvalue().splitlines()))

print("\n" + "=" * 100)
print("DEFECT 3 — daily_summary: a DAY-CUMULATIVE flow subtracted from an INTERVAL equity change")
print("=" * 100)
nav = {"day": "20260912", "wallet_balance": 1000.0, "unrealised_pnl": 0.0, "nav": 1000.0,
       "realised_pnl": 0.0, "realised_by_type_asset": {}, "realised_truncated": False,
       "realised_pnl_source": "/fapi/v1/income since 00:00Z", "external_flow_usdt": 1000.0}
for label, pair in (("transfer landed BEFORE the window (both ends 1000)", [nav, dict(nav)]),
                    ("transfer landed INSIDE the window (0 -> 1000, equity +1000)",
                     [dict(nav, external_flow_usdt=0.0),
                      dict(nav, nav=2000.0, wallet_balance=2000.0)])):
    f = DS.account_facts(pair)
    print(f"\n  {label}")
    print(f"    equity_change            {f['equity_change']}")
    print(f"    external_flow_usdt (day) {f['external_flow_usdt']}")
    print(f"    interval flow            "
          f"{f.get('external_flow_interval_usdt', '<key absent: pre-round-3>')}")
    print(f"    unexplained_equity_change {f['unexplained_equity_change']}"
          f"   [computable: {f['unexplained_computable']}]")
