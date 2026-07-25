"""Watchdog dry-run: each of the seven §4 conditions must fire on demand, and the full chain
   (trigger -> flatten order generation -> reduce-only key switch) must execute.

*** MOCK ONLY: no account, no credentials, no venue contact. ***

The point is that a stop-loss which has never been observed to fire is not a stop-loss. Each
condition gets a synthetic log constructed to breach exactly that condition, plus a clean baseline
that must NOT trip (a watchdog that always fires is equally useless).

Exit 0 = all pass.
"""
import shutil, sys, tempfile

MA = "/mnt/storage/private/work_hsy/quant_research_multi_asset/multi_asset"
sys.path.insert(0, MA + "/engine/live")
import pilot_log as PL
import watchdog as WD

fails = []


def check(name, cond, detail=""):
    print(f"  {'OK  ' if cond else 'FAIL'} {name}{(' — ' + detail) if detail else ''}", flush=True)
    if not cond:
        fails.append(name)


def build(days, c_bps=3.0, day_pnl_pct=0.1, regime="calm", w_err=0.0, markout_bps=1.0,
          reject_frac=0.0, inject_anomaly=False):
    """Synthesise N days whose measured metrics land on the requested values.

    The fixture must be INTERNALLY CONSISTENT or it trips detectors for the wrong reason:
      - position_readback accumulates with the fills, else §4-5b (unexplained position change)
        fires -- correctly -- on the fixture itself;
      - target_w tracks the accumulated position, else §4-6 (weight fidelity) fires for the same
        kind of bookkeeping reason.
    So the two failure modes are injected on DIFFERENT axes: `w_err` perturbs the TARGET (fidelity
    breaks, positions still explained), `inject_anomaly` perturbs the READBACK (position becomes
    unexplained, target still tracked).
    """
    root = tempfile.mkdtemp(prefix="wd_")
    cum = 0.0
    notional = 10_000.0
    for di, day in enumerate(days):
        lg = PL.PilotLogger(root, day)
        ats = 1782950400000 + di * 86400_000
        mid = 100.0
        fee = notional * (c_bps * 0.5) * 1e-4
        px = mid * (1 + (c_bps * 0.5) * 1e-4)
        prev_cum = cum
        cum += notional
        # target tracks the accumulated position; w_err perturbs the TARGET only
        tw = (cum / notional) * (1.0 + w_err)
        pw = prev_cum / notional
        lg.anchor(anchor_ts=ats, target_vector_hash="h", realized_gross=notional,
                  target_gross=notional, n_names_skipped=0, regime_at_anchor=regime,
                  mid_at_anchor_vector={"BTC": mid}, factor_version="f", panel_hash="p")
        lg.order(anchor_ts=ats, symbol="BTC", side="buy", target_w=tw, prev_w=pw,
                 intended_notional=notional, order_type="maker", submit_ts=ats,
                 price_submit=mid, mid_at_submit=mid, mid_at_anchor=mid,
                 filled_notional=notional, avg_fill_px=px, first_fill_ts=ats + 1,
                 last_fill_ts=ats + 2, cancel_ts=None, fee_paid=fee, rebalance_id=f"r{di}",
                 attempt_idx=1,
                 terminal_reason=("venue_reject" if reject_frac >= 1.0 else "filled"),
                 notional_currency="USD")
        lg.fill(anchor_ts=ats, symbol="BTC", side="buy", order_type="maker", attempt_idx=1,
                fill_ts=ats + 1, fill_px=px, fill_notional=notional,
                mid_at_fill_plus_60s=px * (1 - markout_bps * 1e-4), rebalance_id=f"r{di}")
        # readback follows the fills; inject_anomaly perturbs the READBACK only
        rb = cum * (0.5 if (inject_anomaly and di == len(days) - 1) else 1.0)
        lg.position_readback(anchor_ts=ats, symbol="BTC",
                             venue_position_notional=rb, source="mock")
        lg.daily_nav(day=int(day), target_gross=notional, nav=100_000.0,
                     realised_pnl=notional * day_pnl_pct / 100.0, unrealised_pnl=0.0)
        lg.close()
    return root


DAYS = [f"2026071{i}" for i in range(1, 7)]

print("[0] clean baseline must NOT trip")
r = build(DAYS)
ev, br, st = WD.run(r, broker=WD.MockBroker(), verbose=False, state_dir=r+'/_wd')
check("baseline does not trip", not ev["tripped"], str(ev["triggers"]))
check("baseline leaves reduce_only off", not br.reduce_only)
shutil.rmtree(r, ignore_errors=True)

print("[1] §4-1 c > 9bps for 5 consecutive days")
r = build(DAYS, c_bps=12.0)
ev, br, st = WD.run(r, broker=WD.MockBroker(), verbose=False, state_dir=r+'/_wd')
check("cond1 fires", ev["conditions"]["cond1_c_persist"]["triggered"])
check("cond1 auto reduce-only", br.reduce_only)
check("cond1 generated flatten orders",
      any(a["action"] == "flatten_all" and a["n_orders"] > 0 for a in br.actions))
shutil.rmtree(r, ignore_errors=True)

print("[2] §4-2 single-day loss worse than -6.7% of target gross")
r = build(DAYS, day_pnl_pct=-8.0)
ev, br, _ = WD.run(r, broker=WD.MockBroker(), verbose=False, state_dir=r+'/_wd')
check("cond2 fires", ev["conditions"]["cond2_day_loss"]["triggered"])
shutil.rmtree(r, ignore_errors=True)

print("[3] §4-3 crash-day markout tail worse than -25bps (stress anchors only)")
r = build(DAYS, regime="stress", markout_bps=40.0)
ev, br, _ = WD.run(r, broker=WD.MockBroker(), verbose=False, state_dir=r+'/_wd')
check("cond3 fires", ev["conditions"]["cond3_crash_markout"]["triggered"],
      f"worst={ev['conditions']['cond3_crash_markout']['worst_stress_markout_bps']}")
shutil.rmtree(r, ignore_errors=True)

print("[4] §4-4 cumulative drawdown > 6%")
r = build(DAYS, day_pnl_pct=-1.5)          # 6 days x -1.5% = -9% cumulative
ev, br, _ = WD.run(r, broker=WD.MockBroker(), verbose=False, state_dir=r+'/_wd')
check("cond4 fires", ev["conditions"]["cond4_drawdown"]["triggered"],
      f"dd={ev['conditions']['cond4_drawdown']['max_drawdown_pct']}")
shutil.rmtree(r, ignore_errors=True)

print("[5] §4-5 venue event")
r = build(DAYS)
ev, br, _ = WD.run(r, broker=WD.MockBroker(),
                   venue_events=[{"kind": "outage", "severity": "stop"}],
                   verbose=False, state_dir=r+'/_wd')
check("cond5 fires", ev["conditions"]["cond5_venue_event"]["triggered"])
check("cond5 auto reduce-only", br.reduce_only)
shutil.rmtree(r, ignore_errors=True)

print("[6] §4-6 weight fidelity < 0.85 for 3 days")
r = build(DAYS, w_err=0.30)
ev, br, _ = WD.run(r, broker=WD.MockBroker(), verbose=False, state_dir=r+'/_wd')
check("cond6 fires", ev["conditions"]["cond6_weight_fidelity"]["triggered"],
      f"per_day={ev['conditions']['cond6_weight_fidelity']['per_day'][:3]}")
shutil.rmtree(r, ignore_errors=True)

print("[7] §4-7 ops: failure rate and un-recovered drift")
r = build(DAYS)
ev, br, _ = WD.run(r, broker=WD.MockBroker(),
                   ops_stats=[{"rebalance_fail_rate": 0.12}] * 4, verbose=False,
                   state_dir=r+'/_wd1')
check("cond7 fires on failure rate", ev["conditions"]["cond7_ops"]["triggered"])
ev2, br2, _ = WD.run(r, broker=WD.MockBroker(),
                     ops_stats=[{"rebalance_fail_rate": 0.0,
                                 "unrecovered_position_drift": True}], verbose=False,
                     state_dir=r+'/_wd2')
check("cond7 fires on un-recovered drift", ev2["conditions"]["cond7_ops"]["triggered"])
shutil.rmtree(r, ignore_errors=True)

print("[8] default-state semantics")
r = build(DAYS, c_bps=12.0)
br = WD.MockBroker()
ev, br, st = WD.run(r, broker=br, verbose=False, state_dir=r+'/_wd')
check("state persists reduce_only=True", st["reduce_only"] is True)
check("state records resume friction", "deliberate" in st.get("resume_requires", ""))
order_actions = [a for a in br.actions if a["action"] == "flatten_all"]
ro_actions = [a for a in br.actions if a["action"] == "set_reduce_only"]
check("flatten precedes reduce-only switch",
      bool(order_actions) and bool(ro_actions)
      and br.actions.index(order_actions[0]) < br.actions.index(ro_actions[0]))
check("flatten orders are reduce_only",
      all(o["reduce_only"] for a in order_actions for o in a["orders"]))
shutil.rmtree(r, ignore_errors=True)

print("[5b] §4-5b liquidation/position anomaly via position_readback")
r = build(DAYS, inject_anomaly=True)
ev, br, _ = WD.run(r, broker=WD.MockBroker(), verbose=False, state_dir=r+'/_wd')
c5 = ev["conditions"]["cond5_venue_event"]
check("5b fires on unexplained position change", c5["5b_liquidation_anomaly"]["triggered"],
      f"n={c5['5b_liquidation_anomaly']['n']}")
check("5b reuses position_readback path",
      "position_readback" in c5["5b_liquidation_anomaly"]["source"])
shutil.rmtree(r, ignore_errors=True)

print("[5c] §4-5c account restriction — behaviour is the guard, codes are a fast path")
r = build(DAYS, reject_frac=1.0)
ev, br, _ = WD.run(r, broker=WD.MockBroker(), verbose=False, state_dir=r+'/_wd')
c5 = ev["conditions"]["cond5_venue_event"]
check("5c fires on BEHAVIOUR alone (no error code supplied)",
      c5["5c_account_restriction"]["behavioural_anchor_hit"])
check("5c fired without any code hit",
      not c5["5c_account_restriction"]["error_code_fast_path_hits"])
shutil.rmtree(r, ignore_errors=True)

r = build(DAYS)
ev, br, _ = WD.run(r, broker=WD.MockBroker(),
                   venue_events=[{"venue": "hyperliquid", "error_code": "HTTP 403"}],
                   verbose=False, state_dir=r+'/_wd')
c5 = ev["conditions"]["cond5_venue_event"]
check("5c error-code fast path fires immediately",
      bool(c5["5c_account_restriction"]["error_code_fast_path_hits"]))
shutil.rmtree(r, ignore_errors=True)

r = build(DAYS)
ev, br, _ = WD.run(r, broker=WD.MockBroker(),
                   venue_events=[{"venue": "hyperliquid", "error_code": "SOME_UNDOCUMENTED_CODE",
                                  "consecutive_failed_attempts": 5}],
                   verbose=False, state_dir=r+'/_wd')
c5 = ev["conditions"]["cond5_venue_event"]
check("unknown code still trips via behavioural fallback",
      c5["5c_account_restriction"]["behavioural_attempt_hit"],
      "an incomplete table must never fail open")
shutil.rmtree(r, ignore_errors=True)

print("[5d] withdrawal halt is NOT in the realtime layer")
r = build(DAYS)
ev, br, _ = WD.run(r, broker=WD.MockBroker(), verbose=False, state_dir=r+'/_wd')
check("5d documented as out of realtime layer",
      ev["conditions"]["cond5_venue_event"]["5d_withdrawal_halt"]["in_realtime_layer"] is False)
shutil.rmtree(r, ignore_errors=True)

print("[9] stale state must NOT suppress action on a new trip (regression)")
r = build(DAYS, c_bps=12.0)
sd = r + "/_wd"
WD.run(r, broker=WD.MockBroker(), verbose=False, state_dir=sd)      # first trip writes state
br3 = WD.MockBroker()
ev3, br3, st3 = WD.run(r, broker=br3, verbose=False, state_dir=sd)  # state already reduce_only
check("acts again despite stale reduce_only state",
      any(a["action"] == "set_reduce_only" for a in br3.actions),
      "a leftover True must never silence a genuine trigger")
shutil.rmtree(r, ignore_errors=True)

print(f"\n  {'ALL PASS' if not fails else 'FAILURES: ' + str(fails)}", flush=True)
sys.exit(0 if not fails else 1)
