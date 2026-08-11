"""Production inputs for the watchdog — derived BY THE DAILY RUN, not injected by a caller.

★ WHY THIS MODULE EXISTS (0C found it, and it is the same failure I avoided on the logger):
  `pilot_daily` called `WD.run(LOG_ROOT)` with no venue_events and no ops_stats. §4-5 read only
  externally-injected events and §4-7 read only an externally-injected list -- and production
  injected neither. Two of the seven stop-losses were structurally dead on the production path
  while every component test passed, because the tests supplied inputs production never supplies.

  The general rule, now a checklist item rather than a principle to remember:
  ★ EVERY SAFETY-CRITICAL COMPONENT NEEDS AT LEAST ONE TEST THAT ENTERS THROUGH THE PRODUCTION
    CALL PATH. Component-level tests cannot find a wiring gap between production and the
    component, because they construct the inputs themselves.

Two derivations, both from things the daily run already has:

  ops_stats     from the v2 log: per-day rebalance failure rate (orders that did not reach their
                intended notional for a venue-side reason) + unexplained position drift.
  venue_events  from a PUBLIC-PATH PROBE. No account and no error codes needed:
                    public market data ALIVE  + our submissions failing -> ACCOUNT side
                    public market data DEAD   + our submissions failing -> VENUE side
                Misclassification is biased safe: both roads lead to flatten + reduce-only, and
                the distinction only changes the alert text, never whether we stop.

*** READ-ONLY public endpoints. No account, no credentials, no venue contact beyond public data. ***
"""
from __future__ import annotations
import json, time, urllib.request
from collections import defaultdict

import pilot_log as PL

HL_INFO = "https://api.hyperliquid.xyz/info"
UA = "Mozilla/5.0 (research-probe; read-only public market data)"

# ★ WHAT COUNTS AS A "REBALANCE FAILURE" (§4-7). Only the venue refusing the order.
# A `partial_expired` maker order is NORMAL: the passive leg is expected to fill partially inside
# the k=900 window and the taker top-up completes it. Counting it as a failure made the watchdog
# trip on every ordinary shadow day -- and a stop-loss that fires daily is one that gets ignored,
# which is a worse failure than not having it. `abandoned_*` are OUR OWN rules (F16) firing
# correctly, not the venue failing us; they are already measured as M5 shortfall.
VENUE_SIDE_FAILURES = {"venue_reject"}
NORMAL_EXECUTION_OUTCOMES = {"filled", "partial_expired"}
OUR_OWN_RULES = {"skipped_min_notional", "abandoned_spread_gt_25bps", "abandoned_max_attempts"}


def public_path_alive(timeout=10):
    """Is the venue's PUBLIC market data reachable? Distinguishes venue-side from account-side."""
    t0 = time.time()
    try:
        req = urllib.request.Request(HL_INFO, data=json.dumps({"type": "meta"}).encode(),
                                     method="POST",
                                     headers={"User-Agent": UA, "Content-Type": "application/json"})
        with urllib.request.urlopen(req, timeout=timeout) as r:
            j = json.loads(r.read())
        ok = bool(j.get("universe"))
        return {"alive": ok, "ms": round((time.time() - t0) * 1000),
                "n_markets": len(j.get("universe", []))}
    except Exception as e:
        return {"alive": False, "ms": round((time.time() - t0) * 1000),
                "error": type(e).__name__ + ": " + str(e)[:120]}


def derive_ops_stats(root, days=None):
    """Per-day ops facts from the v2 log. This is what §4-7 must read in production."""
    days = days or PL.available_days(root)
    out = []
    prev_rb = None
    for d in days:
        one = PL.read_day(root, d)
        orders = [o for o in one["orders"] if o["terminal_reason"] not in ("skipped_min_notional",)]
        n = len(orders)
        # a "failed rebalance" = the venue would not take it, NOT our own abandonment rules
        n_fail = sum(1 for o in orders if o["terminal_reason"] in VENUE_SIDE_FAILURES)
        # unexplained position drift, same comparison §4-5b uses (one path, two guarantees)
        rb = defaultdict(dict)
        for r in one["position_readback"]:
            rb[r["anchor_ts"]][r["symbol"]] = float(r["venue_position_notional"])
        fills = defaultdict(lambda: defaultdict(float))
        for o in one["orders"]:
            f = float(o["filled_notional"] or 0.0)
            if f > 0:
                fills[o["anchor_ts"]][o["symbol"]] += (1 if o["side"] == "buy" else -1) * f
        drift = False
        for ats in sorted(rb):
            cur = rb[ats]
            if prev_rb is not None:
                for sym, v in cur.items():
                    exp = prev_rb.get(sym, 0.0) + fills[ats].get(sym, 0.0)
                    scale = max(abs(exp), abs(v), 1.0)
                    if abs(v - exp) / scale > 0.10:
                        drift = True
                        break
            prev_rb = cur
            if drift:
                break
        out.append({"day": d, "n_orders": n, "n_venue_side_failures": n_fail,
                    "rebalance_fail_rate": (n_fail / n) if n else 0.0,
                    "unrecovered_position_drift": drift})
    return out


def derive_venue_events(root, ops_stats, days=None):
    """§4-5 inputs, derived. Public-path probe + our own submission health from the log."""
    probe = public_path_alive()
    recent = ops_stats[-2:] if ops_stats else []
    our_orders_failing = bool(recent) and all(o["rebalance_fail_rate"] > 0.5 for o in recent)
    events = []
    if our_orders_failing and probe["alive"]:
        events.append({"kind": "account_side_anomaly", "severity": "stop",
                       "evidence": {"public_path": probe, "recent_ops": recent},
                       "reasoning": ("public market data is reachable while OUR submissions are "
                                     "failing -> the problem is on our account, not the venue")})
    elif our_orders_failing and not probe["alive"]:
        events.append({"kind": "outage", "severity": "stop",
                       "evidence": {"public_path": probe, "recent_ops": recent},
                       "reasoning": "public market data is also unreachable -> venue-side outage"})
    elif not probe["alive"]:
        events.append({"kind": "public_path_unreachable", "severity": "warn",
                       "evidence": {"public_path": probe},
                       "reasoning": ("public data unreachable but our submissions are not failing "
                                     "— could be our egress; warn, do not stop")})
    return events, probe


def collect(root, days=None):
    """The single call production uses. Returns (ops_stats, venue_events, diagnostics)."""
    ops = derive_ops_stats(root, days)
    events, probe = derive_venue_events(root, ops, days)
    return ops, events, {"public_path_probe": probe, "n_days": len(ops),
                         "derived_by": "watchdog_inputs.collect (production path)"}
