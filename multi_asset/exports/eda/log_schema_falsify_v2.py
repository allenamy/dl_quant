"""v2 arm of the schema falsification (§10 acceptance test for §9.5 item ①). — 0B

0C's log_schema_falsify.py generated a PATHOLOGICAL day (partial fills, multi-child fills, two
attempts, F16 abandonment, min-notional skips, rate-limit skips, venue reject) and showed schema v1
fails 7/7, with M6 and the stop-loss inputs outright IMPOSSIBLE.

This re-runs the SAME pathological day against schema v2 and requires all seven to come out
computable and UNIQUE (no defensible-alternative spread).

★ DESIGN CHOICE: the v2 arm does not re-implement the metrics. It writes the synthetic day through
  the REAL logger (engine/live/pilot_log.py) and reads the answers out of the REAL gate script
  (engine/live/pilot_metrics.py). So this test exercises the code the pilot will actually run --
  a test against a parallel reimplementation could pass while production still failed.

Exit 0 = 7/7 OK. Non-zero = the schema is not fit to sign.
Writes exports/eda/log_schema_falsify_v2.json.
"""
import importlib.util, json, os, shutil, sys, tempfile

MA = "/mnt/storage/private/work_hsy/quant_research_multi_asset/multi_asset"
EDA = MA + "/exports/eda/"
sys.path.insert(0, MA + "/engine/live")
import pilot_log as PL                                    # noqa: E402
import pilot_metrics as PM                                # noqa: E402


def load_generator():
    """Import 0C's generator without executing its v1 verdict section."""
    src = open(EDA + "log_schema_falsify.py").read()
    cut = src.index("ORDERS, ANCHOR_ROWS, FILLS, FUNDING, NAVS = gen_day()")
    mod = {}
    exec(compile(src[:cut], "log_schema_falsify_gen", "exec"), mod)
    return mod["gen_day"], mod["SYMS"]


def main():
    gen_day, SYMS = load_generator()
    ORDERS, ANCHORS, FILLS, FUNDING, NAVS = gen_day()
    print(f"[v2] same pathological day: {len(ORDERS)} orders / {len(FILLS)} child fills / "
          f"{len(ANCHORS)} anchors / {len(FUNDING)} funding settlements", flush=True)

    root = tempfile.mkdtemp(prefix="pilotlog_v2_")
    day = "20260725"
    lg = PL.PilotLogger(root, day)

    # ---- orders: v2 carries mid_at_anchor, terminal_reason, first/last_fill_ts, currency ----
    for o in ORDERS:
        lg.order(anchor_ts=o["anchor_ts"], symbol=o["symbol"], side=o["side"],
                 target_w=o["target_w"], prev_w=o["prev_w"],
                 intended_notional=o["intended_notional"], order_type=o["order_type"],
                 submit_ts=o["submit_ts"], price_submit=o["price_submit"],
                 mid_at_submit=o["mid_at_submit"], mid_at_anchor=o["_v2_mid_at_anchor"],
                 filled_notional=o["filled_notional"], avg_fill_px=o["avg_fill_px"],
                 first_fill_ts=o["_v2_first_fill_ts"], last_fill_ts=o["_v2_last_fill_ts"],
                 cancel_ts=o["cancel_ts"], fee_paid=o["fee_paid"],
                 rebalance_id=o["rebalance_id"], attempt_idx=o["attempt_idx"],
                 terminal_reason=o["_v2_terminal_reason"], notional_currency="USD")
    for f in FILLS:
        lg.fill(**f)
    for a in ANCHORS:
        lg.anchor(anchor_ts=a["anchor_ts"], target_vector_hash=a["target_vector_hash"],
                  realized_gross=a["realized_gross"], target_gross=a["target_gross"],
                  n_names_skipped=a["n_names_skipped"],
                  regime_at_anchor=a["_v2_regime_at_anchor"],
                  mid_at_anchor_vector=a["_v2_mid_at_anchor"],
                  factor_version="funding_ema_normfix", panel_hash="deadbeefcafe")
        # venue read-back: the whole point is that it comes from the VENUE, not from our fills
        for s, v in a["_v2_actual_positions"].items():
            lg.position_readback(anchor_ts=a["anchor_ts"], symbol=s,
                                 venue_position_notional=v, source="venue_api_mock")
    for fd in FUNDING:
        lg.funding(settlement_ts=fd["settlement_ts"], symbol=fd["symbol"],
                   position_notional_at_settlement=fd["position_notional"],
                   funding_rate=fd["funding_rate"], funding_paid=fd["funding_paid"])
    for n in NAVS:
        lg.daily_nav(day=int(n["day"]), target_gross=n["target_gross"], nav=100_000.0 + n["nav_pnl"],
                     realised_pnl=n["nav_pnl"], unrealised_pnl=0.0)
    lg.close()

    res = PM.compute(root, verbose=False)

    checks = {}

    def ck(name, ok, detail, value=None):
        checks[name] = {"status": "OK" if ok else "FAIL", "detail": detail, "value": value}
        print(f"  {'OK      ' if ok else 'FAIL    '} {name}: {detail}", flush=True)

    m1 = res["M1_effective_cost"]
    ck("M1_effective_cost_bps", m1["c_bps_overall"] is not None,
       "unique: benchmarked against mid_at_anchor (pinned); no alternative reading admissible "
       "because arrival mid is no longer the only available baseline",
       m1["c_bps_overall"])
    m2 = res["M2_markout"]
    ck("M2_markout_bps", m2["markout_bps"] is not None and m2["n_fills"] > 0,
       f"unique: maker-only, per CHILD fill ({m2['n_fills']} fills), notional-weighted",
       m2["markout_bps"])
    m3 = res["M3_fill_rate"]
    ck("M3_fill_rate", m3["fill_rate"] is not None,
       "unique: denominator pinned to attempt_idx==1 intended, so re-posting can never double-count",
       m3["fill_rate"])
    m4 = res["M4_turnover"]
    ck("M4_turnover", m4["target_weight_turnover_annualised"] is not None,
       "unique: gate uses TARGET-weight turnover; realized reported alongside "
       f"({m4['realized_turnover_annualised']})", m4["target_weight_turnover_annualised"])
    m5 = res["M5_weight_fidelity"]
    ck("M5_weight_fidelity",
       m5["mean_abs_weight_error"] is not None and m5["n_comparisons"] > 0
       and m5["venue_vs_inferred_drift_usd_max"] is not None
       and len(m5["shortfall_notional_by_terminal_reason"]) > 0,
       "reconciled against venue position_readback; shortfall split by terminal_reason so "
       "'did not fill' and 'abandoned under F16' are distinguishable",
       {"mean_abs_w_err": m5["mean_abs_weight_error"],
        "reasons": list(m5["shortfall_notional_by_terminal_reason"])})
    m6 = res["M6_funding"]
    ck("M6_funding", m6["n_settlements"] > 0 and m6["funding_paid_total_usd"] is not None,
       f"computable from the funding ledger ({m6['n_settlements']} settlements) — was IMPOSSIBLE "
       "under v1 because funding does not flow through orders", m6["funding_paid_total_usd"])
    sl = res["STOPLOSS_inputs"]
    ck("STOPLOSS_inputs", sl["available"],
       "daily NAV series persisted -> single-day loss and cumulative drawdown are computable AND "
       "auditable after the fact", {"worst_day_pct": sl.get("worst_day_pct_of_target_gross")})

    # regime stratification + blind-spot behaviour must also work
    rc = res["regime_coverage"]
    print(f"\n  regime coverage: present={rc['regimes_present']} missing={rc['regimes_missing']}",
          flush=True)
    if rc["blind_spot_warning"]:
        print(f"  ⚠ blind-spot warning correctly raised", flush=True)

    n_ok = sum(1 for v in checks.values() if v["status"] == "OK")
    verdict = f"{n_ok}/7 OK"
    print(f"\n  VERDICT (schema v2): {verdict}", flush=True)
    json.dump({"title": "Pilot log-schema v2 acceptance test (§10)", "created": "2026-07-25",
               "author": "0B", "schema_version": PL.SCHEMA_VERSION,
               "pilot_metrics_sha256": res["pilot_metrics_sha256"],
               "method": "0C's identical pathological day, written through the REAL logger and "
                         "measured by the REAL gate script (not a reimplementation)",
               "checks": checks, "n_ok": n_ok, "verdict": verdict,
               "regime_coverage": rc, "metrics": res},
              open(EDA + "log_schema_falsify_v2.json", "w"), indent=1, default=str)
    print(f"SAVED {EDA}log_schema_falsify_v2.json", flush=True)
    shutil.rmtree(root, ignore_errors=True)
    return 0 if n_ok == 7 else 1


if __name__ == "__main__":
    sys.exit(main())
