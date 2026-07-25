"""Stop-loss watchdog — all seven §4 conditions machine-evaluated + automatic reduce-only (§9-F6).

WHY THE WATCHDOG AND NOT A HUMAN: §4 was written as rules for a person, but the rebalance anchors
land at 00:00 and 04:00 SGT, and the moment a stop-loss should fire is exactly the moment its
operator is asleep or losing money and least willing to stop. The design intent (0C) is to flip the
DEFAULT STATE from "trading" to "not trading": a trigger auto-flattens and switches the key to
reduce-only, so resuming requires a deliberate, high-friction action. Using a default to fight loss
aversion is more reliable than using discipline to fight it.

*** MOCK ONLY — THIS CONNECTS TO NOTHING. ***
    There is no account, and none may be opened or connected here. The broker interface is a
    `MockBroker` that records the actions it WOULD take. The full chain
    (condition -> trigger -> flatten order generation -> key switch) is exercised in dry-run.
    Wiring a real venue requires the user to open an account and grant explicit authorisation.

★ WHAT COUNTS AS "NOTIFIED" (name this class; it has bitten twice):
    ★ The completion marker for any NOTIFY step must be an action that LEAVES THIS MACHINE.
      Writing to a local file is not notification. A local write succeeds in almost every
      circumstance, so an alert whose success criterion is "the write returned" has fake
      reliability -- exactly the error as mirroring a report to another directory on the same box
      and calling it a second pair of eyes. `stage2_local_write_ok` therefore means RECORDED, and
      only the delivery receipt (email) may be read as DELIVERED.

★ THE GOVERNING ASYMMETRY (generalise this to EVERY check in this file):
    a redundant action is cheap; failing to act when you should have is not.
  So any optimisation of the form "check whether we already did this" must first answer "what does
  it cost if THAT check is itself wrong?" This module previously skipped acting when state already
  said reduce_only -- which meant a stale state file could silently disarm the watchdog while it
  still looked healthy in the logs. Never trade a correctness guarantee for a redundant call.

The seven conditions (§4), read from the v2 pilot log plus an injected operational stream:
  1. c > 9.0 bps for 5 consecutive trading days
  2. single-day loss worse than -6.7% of TARGET gross (§9-F12: always target, never realised)
  3. crash-day markout tail worse than -25 bps
     -- "crash day" := regime_at_anchor == "stress" (0C ruling; reuses the existing classifier,
        zero new parameters, fully machine-decidable)
  4. cumulative drawdown > 6% of target gross
  5. venue events, RE-SCOPED BY RESPONSE LATENCY rather than by detectability (0C ruling):
        5a outage              API unreachable / rejects / stale quotes        -> watchdog
        5b liquidation anomaly position changed with no order of ours          -> watchdog,
                                via position_readback. NOTE this is that field's SECOND purpose --
                                it was added to catch silent position drift, and the same
                                comparison detects an unexplained liquidation. One field, two
                                guarantees, ONE code path.
        5c account restriction behavioural fallback + error-code fast path     -> watchdog
        5d withdrawal halt     DELIBERATELY OUT of the realtime layer -> phase-boundary human check.
                                Rationale: it threatens getting money OUT, not the position, and an
                                emergency flatten does not help -- the cash is stuck either way. The
                                right response (stop adding funds, plan an exit) is a phase-boundary
                                decision, and phase boundaries have a human present (10:00 SGT).
  6. weight-fidelity corr < 0.85 for 3 consecutive days
  7. ops: rebalance failure rate > 5% for 3 days, or one un-recovered position drift

★ GENERAL RULE (0C, applies to every condition): each stop-loss must be assigned to a layer whose
  response latency matches its urgency. A condition that cannot be automatically detected has only
  two legitimate homes -- move it to a checkpoint where a human is present, or delete it. Leaving it
  in the realtime layer as "someone will notice" is an empty clause wearing the costume of a rule.

Out: exports/live/watchdog/{state.json, events.jsonl, last_eval.json}
"""
from __future__ import annotations
import argparse, json, os, sys, time
from collections import defaultdict
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from typing import Any, Dict, List

MA = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))   # .../multi_asset
sys.path.insert(0, MA + "/engine/live")
import pilot_log as PL
import pilot_metrics as PM

OUT = MA + "/exports/live/watchdog"
C_LIMIT_BPS, C_PERSIST_DAYS = 9.0, 5          # §4-1 (persist days per §11.5 ruling: 5, all stages)
DAY_LOSS_LIMIT_PCT = -6.7                     # §4-2, of TARGET gross
MARKOUT_TAIL_LIMIT_BPS = -25.0                # §4-3
DRAWDOWN_LIMIT_PCT = -6.0                     # §4-4
WEIGHT_CORR_LIMIT, WEIGHT_PERSIST_DAYS = 0.85, 3   # §4-6
FAIL_RATE_LIMIT, FAIL_PERSIST_DAYS = 0.05, 3       # §4-7
# §4-5c behavioural fallback. N/M chosen so a transient hiccup does not trip us but a genuine
# restriction cannot persist unnoticed for long: at 6 anchors/day, M=2 anchors is <= 8 hours of
# total submission failure, and N=3 consecutive attempts is beyond any single retry storm. These
# are deliberately NOT tuned -- with no account there is nothing to tune against, and a round,
# defensible number is more honest than a precise-looking invented one.
ACCT_FAIL_ATTEMPTS_N = 3
ACCT_FAIL_ANCHORS_M = 2
REJECT_FRAC_LIMIT = 0.5      # fraction of an anchor's orders ending in venue_reject


class MockBroker:
    """Records intended actions. Places no orders, holds no credentials, contacts no venue.

    `fail_submit` simulates the case the degradation path exists for: order submission itself is
    broken. Without it the tests would keep asserting that flattening always works -- which is
    precisely the assumption §4-5/§4-7 violate by definition.
    """

    def __init__(self, fail_submit=False, fail_reduce_only=False):
        self.actions: List[Dict[str, Any]] = []
        self.reduce_only = False
        self.open_orders_halted = False
        self.fail_submit = fail_submit
        self.fail_reduce_only = fail_reduce_only

    def submit(self, order, reason=""):
        """★ The opening-halt must NEVER block a reduce-only order.
        The flatten IS reduce-only, so if the halt were applied indiscriminately, moving it to the
        front of the ladder would block our own exit -- turning an improvement into a disaster.
        The halt is therefore defined strictly over OPENING direction."""
        if self.open_orders_halted and not order.get("reduce_only"):
            self.actions.append({"action": "order_blocked_by_halt", "order": order,
                                 "reason": reason, "ts": time.time()})
            raise OpeningHalted("opening-direction order refused: open_orders_halted is set")
        return True

    def flatten_all(self, positions: Dict[str, float], reason: str):
        orders = [{"symbol": s, "side": "sell" if v > 0 else "buy", "notional": abs(v),
                   "reduce_only": True} for s, v in positions.items() if abs(v) > 1e-9]
        for o in orders:
            self.submit(o, reason)          # reduce_only -> passes even when halted
        ok = not self.fail_submit
        self.actions.append({"action": "flatten_all", "reason": reason, "n_orders": len(orders),
                             "orders": orders, "submitted_ok": ok, "ts": time.time()})
        if not ok:
            raise BrokerUnavailable("order submission failed (simulated)")
        return orders

    def set_reduce_only(self, on: bool, reason: str):
        if self.fail_reduce_only:
            self.actions.append({"action": "set_reduce_only", "value": on, "reason": reason,
                                 "submitted_ok": False, "ts": time.time()})
            raise BrokerUnavailable("reduce-only key switch failed (simulated)")
        self.reduce_only = on
        self.actions.append({"action": "set_reduce_only", "value": on, "reason": reason,
                             "submitted_ok": True, "ts": time.time()})
        return on

    def halt_opening_orders(self, reason: str):
        """★ The only protection that does NOT need the exchange to cooperate: we simply refuse to
        emit any opening-direction order. Declining to send needs no venue, no key, no fill."""
        self.open_orders_halted = True
        self.actions.append({"action": "halt_opening_orders", "reason": reason,
                             "submitted_ok": True, "ts": time.time()})
        return True


class BrokerUnavailable(RuntimeError):
    pass


class OpeningHalted(RuntimeError):
    pass


# Conditions whose very trigger implies order submission may be impaired. A flatten cannot be
# assumed to succeed for these, so they must run the degradation ladder (0C's scan; team-lead's
# first read had only 4-5 and missed the starkest one):
#   §4-5 venue event      -- impaired BY DEFINITION
#   §4-7 rebalance failure-- the trigger IS "our orders are failing"; responding with "send orders"
#                            is self-contradictory. This is the most glaring of the three.
#   §4-6 weight fidelity  -- CONDITIONALLY impaired: one cause of poor fidelity is orders not
#                            filling. The rule must not assume the benign cause (rounding).
SUBMISSION_IMPAIRED_CONDITIONS = ("§4-5", "§4-6", "§4-7")


def _degradation_ladder(broker, positions, reason, alarm_path, verbose=True, max_retries=3):
    """Three stages, ordered by RELIABILITY x PROTECTIVE POWER, descending. Each fully isolated.

    ★ ORDER MATTERS AND THIS ORDER IS DELIBERATE (it used to be flatten -> alert -> halt):

        1. HALT OPENING   a local state bit. Needs no exchange, no network, no disk; microseconds.
                          It is the least likely step to fail AND the least likely to be prevented
                          by another step's failure -- so it runs FIRST, unconditionally.
        2. FLATTEN        needs the exchange to cooperate; retried.
        3. ALERT          needs disk/network.

    Running the cheapest, most reliable protection LAST meant every fragile step upstream could
    prevent it: a bare `open()` raising on a full disk used to kill the halt entirely. Putting it
    first costs nothing (microseconds, no delay to the flatten) and removes that whole class.

    ★ GENERAL RULE: order a protection ladder by reliability x protective power, descending, and
      isolate each rung. The cheapest, most reliable layer must execute first and unconditionally --
      putting it later lets the most fragile steps gate the most dependable one.

    ★ AND: the opening-halt is defined strictly over OPENING direction, so it cannot block the
      reduce-only flatten that follows it. (Verified by test, because getting this wrong would turn
      this improvement into a disaster.)

    Every rung is independently try/except'd: any one failing must not prevent the others, and each
    failure is recorded so it can be raised into the report headline -- an alert that silently
    failed to send is itself a B3 (it fired, nobody got it, and nobody knew nobody got it).
    """
    out = {"order": ["halt_opening", "flatten", "alert"],
           "stage3_open_halted": False, "stage1_flatten_attempts": 0, "stage1_ok": False,
           "stage2_alerted": False, "stage2_local_write_ok": False,
           "stage2_delivered_offbox": None, "errors": []}

    # ---- rung 1: halt opening (zero-dependency, unconditional, first) ----
    try:
        broker.halt_opening_orders(reason)
        out["stage3_open_halted"] = True
    except Exception as e:
        out["errors"].append(f"halt_opening: {type(e).__name__}: {str(e)[:80]}")

    # ---- rung 2: flatten (needs the venue) ----
    for i in range(max_retries):
        out["stage1_flatten_attempts"] += 1
        try:
            broker.flatten_all(positions, reason)
            out["stage1_ok"] = True
            break
        except Exception as e:
            out["errors"].append(f"flatten attempt {i+1}: {type(e).__name__}: {str(e)[:80]}")

    # ---- rung 3: alert (needs disk; delivery off-box is confirmed elsewhere) ----
    sev = "CRITICAL" if not out["stage1_ok"] else "HIGH"
    msg = ("FLATTEN FAILED — positions may be stuck" if not out["stage1_ok"]
           else "STOP-LOSS TRIPPED — book flattened, reduce-only engaged")
    out["stage2_severity"] = sev
    try:
        os.makedirs(os.path.dirname(alarm_path), exist_ok=True)
        with open(alarm_path, "a") as f:
            f.write(json.dumps({"ts": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
                                "severity": sev, "msg": msg, "reason": reason,
                                "errors": out["errors"], "flatten_ok": out["stage1_ok"],
                                "open_orders_halted": out["stage3_open_halted"],
                                "human_action_required": True}) + "\n")
        out["stage2_local_write_ok"] = True
        # ★ NOT "alerted" yet. A local file append is not a notification -- see the module note.
        out["stage2_alerted"] = True     # kept for continuity; means "recorded locally"
    except Exception as e:
        out["errors"].append(f"alert_write: {type(e).__name__}: {str(e)[:80]}")
    if verbose:
        print(f"  ★★ ladder: halt={out['stage3_open_halted']} flatten={out['stage1_ok']} "
              f"alert_local={out['stage2_local_write_ok']} ({sev})", flush=True)
    return out


def _consecutive_tail(flags, n: int) -> bool:
    """True if the LAST n entries are all True (a run that is still active today)."""
    return len(flags) >= n and all(flags[-n:])


def evaluate(root: str, venue_events=None, ops_stats=None):
    """Evaluate all seven §4 conditions. Pure function of the logs + the injected operational
    facts that `watchdog_inputs.collect()` derives on the production path."""
    import venue_error_codes as VEC
    days = PL.available_days(root)
    triggers, detail = [], {}

    # Per-day metrics for the persistence-based conditions (1, 6, 7). Computed day-by-day rather
    # than over the pooled window: "5 CONSECUTIVE days" is a statement about the daily sequence,
    # and a pooled mean can sit under the limit while a 5-day run sits over it.
    per_day_c, per_day_loss, per_day_wcorr = [], [], []
    for d in days:
        one = PL.read_day(root, d)
        regime = {a["anchor_ts"]: a["regime_at_anchor"] for a in one["anchors"]}
        per_day_c.append(PM.m1_effective_cost(one["orders"], regime)["c_bps_overall"])
        nav = one["daily_nav"]
        if nav:
            n0 = nav[0]
            g = float(n0["target_gross"])
            pnl = float(n0["realised_pnl"]) + float(n0.get("unrealised_pnl") or 0.0)
            per_day_loss.append(pnl / g * 100.0 if g else 0.0)
        else:
            per_day_loss.append(None)
        m5 = PM.m5_weight_fidelity(one["orders"], one["anchors"], one["position_readback"])
        per_day_wcorr.append(1.0 - (m5["mean_abs_weight_error"] or 0.0) * 100.0)

    # --- 1. c > 9.0 bps for 5 consecutive days ---
    flags = [(c is not None and c > C_LIMIT_BPS) for c in per_day_c]
    hit = _consecutive_tail(flags, C_PERSIST_DAYS)
    detail["cond1_c_persist"] = {"limit_bps": C_LIMIT_BPS, "persist_days": C_PERSIST_DAYS,
                                 "per_day_c": per_day_c, "triggered": hit}
    if hit:
        triggers.append("§4-1 c > 9.0 bps for 5 consecutive days")

    # --- 2. single-day loss worse than -6.7% of TARGET gross ---
    worst = min([x for x in per_day_loss if x is not None], default=None)
    hit = worst is not None and worst < DAY_LOSS_LIMIT_PCT
    detail["cond2_day_loss"] = {"limit_pct_of_target_gross": DAY_LOSS_LIMIT_PCT,
                                "worst_day_pct": worst, "triggered": hit}
    if hit:
        triggers.append(f"§4-2 single-day loss {worst:.2f}% worse than {DAY_LOSS_LIMIT_PCT}%")

    # --- 3. crash-day markout tail worse than -25 bps ("crash day" := regime == stress) ---
    worst_mk = None
    for d in days:
        one = PL.read_day(root, d)
        stress_anchors = {a["anchor_ts"] for a in one["anchors"]
                          if a["regime_at_anchor"] == "stress"}
        f = [x for x in one["fills"] if x["anchor_ts"] in stress_anchors]
        if f:
            mk = PM.m2_markout(f)["markout_bps"]
            if mk is not None:
                worst_mk = mk if worst_mk is None else min(worst_mk, mk)
    hit = worst_mk is not None and (-worst_mk) < MARKOUT_TAIL_LIMIT_BPS
    detail["cond3_crash_markout"] = {"limit_bps": MARKOUT_TAIL_LIMIT_BPS,
                                     "worst_stress_markout_bps": worst_mk, "triggered": hit,
                                     "note": ("no stress anchors observed yet" if worst_mk is None
                                              else None)}
    if hit:
        triggers.append(f"§4-3 crash-day markout tail {worst_mk} bps")

    # --- 4. cumulative drawdown > 6% of target gross ---
    all_logs = PL.read_range(root, days)
    sl = PM.stoploss_inputs(all_logs["daily_nav"])
    dd = sl.get("max_drawdown_pct_of_target_gross") if sl.get("available") else None
    hit = dd is not None and dd < DRAWDOWN_LIMIT_PCT
    detail["cond4_drawdown"] = {"limit_pct": DRAWDOWN_LIMIT_PCT, "max_drawdown_pct": dd,
                                "triggered": hit}
    if hit:
        triggers.append(f"§4-4 cumulative drawdown {dd:.2f}%")

    # --- 5. venue events, re-scoped by response latency ---
    ve = list(venue_events or [])
    outage = [e for e in ve if e.get("kind") in ("outage", "api_unreachable", "stale_quotes")]

    # 5b: position moved with no order of ours explaining it. SECOND use of position_readback --
    # the same comparison that catches silent drift -- so it shares one code path.
    anomalies = []
    prev_rb = None
    for d in days:
        one = PL.read_day(root, d)
        rb_by_anchor = defaultdict(dict)
        for r in one["position_readback"]:
            rb_by_anchor[r["anchor_ts"]][r["symbol"]] = float(r["venue_position_notional"])
        filled_by_anchor = defaultdict(lambda: defaultdict(float))
        for o in one["orders"]:
            f = float(o["filled_notional"] or 0.0)
            if f > 0:
                filled_by_anchor[o["anchor_ts"]][o["symbol"]] += (
                    1 if o["side"] == "buy" else -1) * f
        for ats in sorted(rb_by_anchor):
            cur = rb_by_anchor[ats]
            if prev_rb is not None:
                for sym, v in cur.items():
                    expected = prev_rb.get(sym, 0.0) + filled_by_anchor[ats].get(sym, 0.0)
                    unexplained = abs(v - expected)
                    scale = max(abs(expected), abs(v), 1.0)
                    if unexplained / scale > 0.10:
                        anomalies.append({"anchor_ts": ats, "symbol": sym,
                                          "expected": round(expected, 2), "observed": round(v, 2),
                                          "unexplained_frac": round(unexplained / scale, 4)})
            prev_rb = cur

    # 5c: BEHAVIOUR is the guard; error codes are only a fast path.
    code_hits = [e for e in ve if e.get("error_code")
                 and VEC.is_restricted_code(e.get("venue", "*"), e["error_code"])]
    anchor_reject_flags = []
    for d in days:
        one = PL.read_day(root, d)
        by_anchor = defaultdict(list)
        for o in one["orders"]:
            if o["terminal_reason"] != "skipped_min_notional":
                by_anchor[o["anchor_ts"]].append(o)
        for ats in sorted(by_anchor):
            rows = by_anchor[ats]
            rej = sum(1 for o in rows if o["terminal_reason"] == "venue_reject")
            anchor_reject_flags.append(len(rows) > 0 and rej / len(rows) >= REJECT_FRAC_LIMIT)
    behav_hit = _consecutive_tail(anchor_reject_flags, ACCT_FAIL_ANCHORS_M)
    consec_attempts = max([e.get("consecutive_failed_attempts", 0) for e in ve] or [0])
    attempt_hit = consec_attempts >= ACCT_FAIL_ATTEMPTS_N
    acct_hit = bool(code_hits or behav_hit or attempt_hit)

    hit5 = bool(outage or anomalies or acct_hit)
    detail["cond5_venue_event"] = {
        "5a_outage": {"events": outage, "triggered": bool(outage)},
        "5b_liquidation_anomaly": {"n": len(anomalies), "examples": anomalies[:3],
                                   "triggered": bool(anomalies),
                                   "source": "position_readback (same path as drift detection)"},
        "5c_account_restriction": {
            "error_code_fast_path_hits": code_hits, "behavioural_anchor_hit": behav_hit,
            "behavioural_attempt_hit": attempt_hit,
            "consecutive_failed_attempts": consec_attempts,
            "thresholds": {"N_attempts": ACCT_FAIL_ATTEMPTS_N, "M_anchors": ACCT_FAIL_ANCHORS_M,
                           "reject_frac": REJECT_FRAC_LIMIT},
            "triggered": acct_hit,
            "note": ("behaviour is the guard; the code table is a fast path only and CANNOT be "
                     "complete (no account => nothing observed). Restriction and outage are NOT "
                     "distinguishable from outside, so both route to the same conservative path.")},
        "5d_withdrawal_halt": {"in_realtime_layer": False,
                               "note": ("deliberately excluded — an emergency flatten does not "
                                        "help when the cash cannot leave; handled at the phase "
                                        "boundary where a human is present")},
        "triggered": hit5}
    if outage:
        triggers.append(f"§4-5a venue outage: {outage[0].get('kind')}")
    if anomalies:
        triggers.append(f"§4-5b liquidation/position anomaly on {len(anomalies)} name-anchors")
    if code_hits:
        triggers.append(f"§4-5c account restriction (error code {code_hits[0]['error_code']})")
    if behav_hit or attempt_hit:
        triggers.append("§4-5c account anomaly by BEHAVIOUR (persistent submission failure)")

    # --- 6. weight-fidelity corr < 0.85 for 3 consecutive days ---
    flags = [(w is not None and w < WEIGHT_CORR_LIMIT) for w in per_day_wcorr]
    hit = _consecutive_tail(flags, WEIGHT_PERSIST_DAYS)
    detail["cond6_weight_fidelity"] = {"limit": WEIGHT_CORR_LIMIT,
                                       "persist_days": WEIGHT_PERSIST_DAYS,
                                       "per_day": [round(w, 4) for w in per_day_wcorr],
                                       "triggered": hit}
    if hit:
        triggers.append("§4-6 weight fidelity < 0.85 for 3 days")

    # --- 7. ops: rebalance failure rate > 5% for 3 days, or one un-recovered drift ---
    ops = ops_stats or []
    fr = [o.get("rebalance_fail_rate", 0.0) for o in ops]
    hit_rate = _consecutive_tail([x > FAIL_RATE_LIMIT for x in fr], FAIL_PERSIST_DAYS)
    drift = any(o.get("unrecovered_position_drift") for o in ops)
    detail["cond7_ops"] = {"fail_rate_limit": FAIL_RATE_LIMIT, "per_day_fail_rate": fr,
                           "unrecovered_drift": drift,
                           "triggered": bool(hit_rate or drift)}
    if hit_rate:
        triggers.append("§4-7 rebalance failure rate > 5% for 3 days")
    if drift:
        triggers.append("§4-7 un-recovered position drift")

    return {"evaluated_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            "n_days": len(days), "days": days, "triggers": triggers,
            "tripped": bool(triggers), "conditions": detail}


def run(root, broker=None, venue_events=None, ops_stats=None, verbose=True, state_dir=None):
    """state_dir defaults to OUT but is SCOPED so one watcher's state cannot govern another's.

    ★ Two safety properties, both learned from a failing dry-run:
      1. state is scoped to the run being watched -- a leftover state.json from a previous phase
         must never speak for the current one;
      2. a trip ALWAYS acts. The earlier version skipped acting when state already said
         reduce_only, which meant a stale True could silently suppress the watchdog on a genuine
         new trigger -- e.g. after an operator manually resumed trading without clearing state.
         Flattening is idempotent (an already-flat book yields zero orders), so acting redundantly
         is cheap and failing to act is not.
    """
    sdir = state_dir or OUT
    os.makedirs(sdir, exist_ok=True)
    broker = broker or MockBroker()
    ev = evaluate(root, venue_events, ops_stats)
    state_p = os.path.join(sdir, "state.json")
    state = json.load(open(state_p)) if os.path.exists(state_p) else {"reduce_only": False,
                                                                      "tripped_at": None}
    if ev["tripped"]:
        last = PL.read_day(root, ev["days"][-1]) if ev["days"] else {"position_readback": []}
        pos = {r["symbol"]: float(r["venue_position_notional"])
               for r in last.get("position_readback", [])}
        reason = "; ".join(ev["triggers"])
        impaired = any(c in reason for c in SUBMISSION_IMPAIRED_CONDITIONS)
        alarm = os.path.join(sdir, "ALARM.log")
        if impaired:
            # the trigger itself implies submission may be broken -> ladder, never a bare flatten
            ladder = _degradation_ladder(broker, pos, reason, alarm, verbose=verbose)
        else:
            # submission is not implicated, but a trip STILL has to reach a human -> same ladder.
            # (Routing the "healthy" case around the ladder is exactly how stage 2 got skipped.)
            ladder = _degradation_ladder(broker, pos, reason, alarm, verbose=verbose)
        try:
            broker.set_reduce_only(True, reason)
        except Exception as e:
            # the halt already ran first, so a failed key switch can no longer take it down with it
            ladder["errors"].append(f"reduce_only: {type(e).__name__}: {str(e)[:80]}")
        ev["degradation"] = ladder
        state = {"reduce_only": True, "degradation": ladder,
                 "open_orders_halted": getattr(broker, "open_orders_halted", False),
                 "tripped_at": state.get("tripped_at") or ev["evaluated_utc"],
                 "last_action_utc": ev["evaluated_utc"], "reason": reason,
                 "flatten_ok": ladder["stage1_ok"],
                 "resume_requires": ("a deliberate manual action — the default is now NOT TRADING. "
                                     "Per §9-F7 no protocol v2 may be drafted for >=72h.")}
        with open(os.path.join(sdir, "events.jsonl"), "a") as f:
            f.write(json.dumps({"ts": ev["evaluated_utc"], "triggers": ev["triggers"],
                                "actions": broker.actions}, default=str) + "\n")
    json.dump(state, open(state_p, "w"), indent=1)
    # sdir, NOT OUT: this line was the one remaining hardcoded production path, so every
    # scoped call still wrote its evaluation into production state. Found by
    # ProductionStateGuard on its first run — which is precisely the leak class it exists for.
    json.dump(ev, open(os.path.join(sdir, "last_eval.json"), "w"), indent=1, default=str)
    if verbose:
        print(f"[watchdog] days={ev['n_days']} tripped={ev['tripped']}", flush=True)
        for k, v in ev["conditions"].items():
            print(f"    {k:24s} triggered={v['triggered']}", flush=True)
        if ev["tripped"]:
            print(f"  ★ TRIPPED: {ev['triggers']}", flush=True)
            print(f"  ★ MOCK actions: flatten + reduce_only={broker.reduce_only}", flush=True)
    return ev, broker, state


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--root", default=MA + "/exports/live/pilot_log")
    a = ap.parse_args()
    run(a.root)
