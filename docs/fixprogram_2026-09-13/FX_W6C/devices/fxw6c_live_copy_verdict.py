"""FX-W6C pre-deployment check (READ-ONLY on a copy of live state): run the FIXED watchdog over the
real pilot_log and report the verdict it would give, beside the live `last_eval.json`'s own.

The question this answers is the only one that matters before deploying a guard change: **does the
changed code change what the watchdog says about the book we are actually holding?** It reports the
trip verdict, every blind condition, the new W6C-B13 observability block (which drives the opening
halt), and cond4's amendment record — so "no change" is a measurement, not an expectation.

usage: fxw6c_live_copy_verdict.py <code_tree> <state_copy_root>
"""
import sys, os, json

CODE, STATE = sys.argv[1], sys.argv[2]
for d in ("live", "scheduler", "ops", "signal"):
    sys.path.insert(0, os.path.join(CODE, d))
import watchdog as WD, watchdog_inputs as WI                        # noqa: E402

ROOT = os.path.join(STATE, "live", "pilot_log")
ops = WI.derive_ops_stats(ROOT)               # production's own derivation; no venue probe
ev = WD.evaluate(ROOT, venue_events=[], ops_stats=ops)
c = ev.get("conditions", {})
b = ev.get("book_observability") or {}
c4 = c.get("cond4_drawdown") or {}
ra = c4.get("realised_amendments") or {}
c5 = c.get("cond5_venue_event") or {}
live = {}
try:
    _le = json.load(open(os.path.join(STATE, "live", "watchdog", "last_eval.json")))
    live = {"evaluated_utc": _le.get("evaluated_utc"), "tripped": _le.get("tripped"),
            "conditions_blind": _le.get("conditions_blind"),
            "cond4_cum_return_from_start_pct": (_le.get("conditions", {}).get("cond4_drawdown") or {}
                                                ).get("cum_return_from_start_pct"),
            "5b_state": ((_le.get("conditions", {}).get("cond5_venue_event") or {})
                         .get("5b_liquidation_anomaly") or {}).get("state")}
except Exception as e:
    live = {"unreadable": f"{type(e).__name__}: {e}"}

print(json.dumps({
    "code_tree": CODE, "state_copy": STATE,
    "fixed_code": {
        "tripped": ev.get("tripped"), "triggers": ev.get("triggers"),
        "conditions_blind": ev.get("conditions_blind"),
        "book_observability": {k: b.get(k) for k in
                               ("state", "blind", "halt_opening", "reference",
                                "newest_scheduled_anchor_ts", "observed_at_newest_scheduled",
                                "n_readback_rows_newest_scheduled",
                                "n_readback_rows_previous_anchor", "n_readback_rows_total")},
        "5b_state": ((c5.get("5b_liquidation_anomaly") or {}).get("state")),
        "5b_blind": ((c5.get("5b_liquidation_anomaly") or {}).get("blind")),
        "5e_state": ((c5.get("5e_position_break") or {}).get("state")),
        "5e_blind": ((c5.get("5e_position_break") or {}).get("blind")),
        "cond7": {k: (c.get("cond7_ops") or {}).get(k) for k in
                  ("blind", "drift_state", "triggered",
                   "drift_newest_scheduled_ats", "drift_observed_at_newest_scheduled")},
        "cond4": {"cum_return_from_start_pct": c4.get("cum_return_from_start_pct"),
                  "limit_pct": c4.get("limit_pct"), "triggered": c4.get("triggered"),
                  "blind": c4.get("blind"),
                  "amendment_records_loaded": ra.get("n_records_loaded"),
                  "days_amended": ra.get("days_amended"),
                  "unamended_prefix_days": [d.get("day") for d in
                                            (ra.get("unamended_prefix_days") or [])]}},
    "live_last_eval": live}, indent=1, default=str))
