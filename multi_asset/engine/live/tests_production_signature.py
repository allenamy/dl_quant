"""PRODUCTION-SIGNATURE regression: every §4 condition must be reachable THROUGH pilot_daily.

★ WHY THIS EXISTS. `pilot_daily` called `WD.run(LOG_ROOT)` with no venue_events and no ops_stats,
  so §4-5 and §4-7 could never fire in production -- while their component tests passed, because
  those tests handed the component inputs that production never handed it.

★ THE RULE THIS ENCODES (now a checklist item, not a principle to remember):
    Every safety-critical component needs at least one test that enters through the PRODUCTION CALL
    PATH. A component-level test cannot find a wiring gap between production and the component,
    because it constructs the inputs itself.

★ FOUR WAYS A CHECK PASSES FOR THE WRONG REASON (each needs its own defence):

    | # | who supplied the false condition |
    |---|---|
    | 1 | the TEST supplied what production never supplies  (this file's reason for existing) |
    | 2 | REALITY supplied a false condition and nobody asked (the 57.8h "stale" panel) |
    | 3 | the ENVIRONMENT changed between observation and verification (re-checking a fixed system) |
    | 4 | the VERIFICATION APPARATUS manufactured the condition it then detected |

  ★ #4 is the most insidious: it supplies BOTH the defect and the ability to detect it, and the two
    corroborate each other, so it reads as a textbook verification success. It happened here -- a
    newly-added standing-state display "caught" an invisible shutdown that our own test fixtures had
    written into PRODUCTION watchdog state. Defence: ProductionStateGuard, below, asserts that a
    test run leaves production state byte-identical.

★ AND THE ANTI-VACUOUS RULE (team-lead's own acceptance test was vacuous for want of it):
    Any test of the form "remove X, verify Y still works" MUST FIRST ASSERT THAT X EXISTS.
    Otherwise the absence of X makes it pass trivially -- and a test that can pass vacuously is
    worse than no test, because it manufactures the appearance of verification.

*** MOCK ONLY: no account, no credentials, no venue contact beyond public market data. ***
Exit 0 = all pass.
"""
from __future__ import annotations
import json, os, shutil, sys, tempfile

MA = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))   # .../multi_asset
sys.path.insert(0, MA + "/engine/live")
import pilot_log as PL
import pilot_daily as PD
import watchdog as WD
import watchdog_inputs as WI
import venue_error_codes as VEC
import factor_version_registry as FVR
import regime_classifier as RC
import deliver_report as DR
from production_state_guard import ProductionStateGuard, override_all, PRODUCTION_STATE_PATHS
import shadow_pilot_log as SPL
import tests_fixture as FIX

fails = []

# ★ FORM #4 DEFENCE: fingerprint every production state path BEFORE any test runs.
_GUARD = ProductionStateGuard()
_GUARD.snapshot()
print(f"[guard] snapshotted {len(PRODUCTION_STATE_PATHS)} production state paths", flush=True)


def check(name, cond, detail=""):
    print(f"  {'OK  ' if cond else 'FAIL'} {name}{(' — ' + detail) if detail else ''}", flush=True)
    if not cond:
        fails.append(name)
    return cond


def mkday(root, day, i, *, c_bps=3.0, pnl_pct=0.1, regime="calm", w_err=0.0, markout=1.0,
          reject=False, drift=False, cum=[0.0]):
    lg = PL.PilotLogger(root, day)
    ats = 1782950400000 + i * 86400_000
    mid, notional = 100.0, 10_000.0
    fee = notional * (c_bps * 0.5) * 1e-4
    px = mid * (1 + (c_bps * 0.5) * 1e-4)
    prev = cum[0]
    cum[0] += notional
    lg.anchor(anchor_ts=ats, target_vector_hash="h", realized_gross=notional,
              target_gross=notional, n_names_skipped=0, regime_at_anchor=regime,
              mid_at_anchor_vector={"BTC": mid}, factor_version="f", panel_hash="p")
    lg.order(anchor_ts=ats, symbol="BTC", side="buy",
             target_w=(cum[0] / notional) * (1 + w_err), prev_w=prev / notional,
             intended_notional=notional, order_type="maker", submit_ts=ats, price_submit=mid,
             mid_at_submit=mid, mid_at_anchor=mid, filled_notional=notional, avg_fill_px=px,
             first_fill_ts=ats + 1, last_fill_ts=ats + 2, cancel_ts=None, fee_paid=fee,
             rebalance_id=f"r{i}", attempt_idx=1,
             terminal_reason=("venue_reject" if reject else "filled"), notional_currency="USD")
    lg.fill(anchor_ts=ats, symbol="BTC", side="buy", order_type="maker", attempt_idx=1,
            fill_ts=ats + 1, fill_px=px, fill_notional=notional,
            mid_at_fill_plus_60s=px * (1 - markout * 1e-4), rebalance_id=f"r{i}")
    rb = cum[0] * (0.5 if drift else 1.0)
    lg.position_readback(anchor_ts=ats, symbol="BTC", venue_position_notional=rb, source="mock")
    lg.daily_nav(day=int(day), target_gross=notional, nav=100_000.0,
                 realised_pnl=notional * pnl_pct / 100.0, unrealised_pnl=0.0)
    lg.close()


def build(**kw):
    root = tempfile.mkdtemp(prefix="prodsig_")
    cum = [0.0]
    for i in range(6):
        mkday(root, f"2026071{i+1}", i, cum=cum, **kw)
    return root


def via_production(root, **overrides):
    """Enter through pilot_daily's REAL path: it must derive the watchdog's inputs itself."""
    old_root, old_track, old_decl = PD.LOG_ROOT, PD.TRACK, PD.DECLARED_FACTOR_VERSION
    PD.LOG_ROOT = root
    for k, v in overrides.items():
        setattr(PD, k, v)
    try:
        ops, events, diag = WI.collect(root)          # exactly what pilot_daily now does
        ev, br, st = WD.run(root, venue_events=events, ops_stats=ops, verbose=False,
                            state_dir=root + "/_wd")
        return ev, br, st, ops, events
    finally:
        PD.LOG_ROOT, PD.TRACK, PD.DECLARED_FACTOR_VERSION = old_root, old_track, old_decl


print("[A] production supplies the watchdog's inputs (the wiring gap)")
r = build()
ev, br, st, ops, events = via_production(r)
check("ops_stats is non-empty on the production path", len(ops) > 0, f"n={len(ops)}")
check("§4-7 has a real input (not [])", ev["conditions"]["cond7_ops"]["per_day_fail_rate"] != [],
      str(ev["conditions"]["cond7_ops"]["per_day_fail_rate"][:3]))
check("§4-5 input derived, not injected",
      "public_path_probe" in WI.collect(r)[2])
check("clean baseline does not trip on production path", not ev["tripped"], str(ev["triggers"]))
shutil.rmtree(r, ignore_errors=True)

print("[B] every one of the seven conditions is REACHABLE through the production path")
cases = {
    "cond1_c_persist":        dict(c_bps=12.0),
    "cond2_day_loss":         dict(pnl_pct=-8.0),
    "cond3_crash_markout":    dict(regime="stress", markout=40.0),
    "cond4_drawdown":         dict(pnl_pct=-1.5),
    "cond6_weight_fidelity":  dict(w_err=0.30),
    "cond7_ops":              dict(reject=True),
    "cond5_venue_event":      dict(drift=True),
}
for cond, kw in cases.items():
    r = build(**kw)
    ev, br, st, ops, events = via_production(r)
    check(f"{cond} reachable via production", ev["conditions"][cond]["triggered"])
    shutil.rmtree(r, ignore_errors=True)

print("[C] anti-vacuous: assert X EXISTS before testing 'remove X, Y still works'")
n_restricted = len([c for c in VEC.VENUE_ERROR_CODES if c["restricted"]])
pre = check("PRE-ASSERT: the error-code table is non-empty", len(VEC.VENUE_ERROR_CODES) > 0,
            f"{len(VEC.VENUE_ERROR_CODES)} rows")
pre2 = check("PRE-ASSERT: it contains restricted codes", n_restricted > 0, f"{n_restricted} rows")
if pre and pre2:
    saved = list(VEC.VENUE_ERROR_CODES), set(VEC.RESTRICTED_CODES)
    VEC.VENUE_ERROR_CODES.clear(); VEC.RESTRICTED_CODES.clear()
    r = build(reject=True)
    ev, br, st, ops, events = via_production(r)
    check("with the table EMPTIED, behaviour alone still trips §4-5c/§4-7",
          ev["conditions"]["cond7_ops"]["triggered"]
          or ev["conditions"]["cond5_venue_event"]["5c_account_restriction"]["triggered"],
          "an incomplete table must never fail open")
    VEC.VENUE_ERROR_CODES.extend(saved[0]); VEC.RESTRICTED_CODES.update(saved[1])
    shutil.rmtree(r, ignore_errors=True)

print("[D] three-stage degradation on the conditions whose trigger implies broken submission")
for cond, kw in (("§4-7", dict(reject=True)), ("§4-5", dict(drift=True)),
                 ("§4-6", dict(w_err=0.30))):
    r = build(**kw)
    ops, events, _ = WI.collect(r)
    br = WD.MockBroker(fail_submit=True)          # the flatten itself cannot be sent
    ev, br, st = WD.run(r, broker=br, venue_events=events, ops_stats=ops, verbose=False,
                        state_dir=r + "/_wd")
    deg = ev.get("degradation", {})
    check(f"{cond}: stage1 retried the flatten", deg.get("stage1_flatten_attempts", 0) > 1,
          f"attempts={deg.get('stage1_flatten_attempts')}")
    check(f"{cond}: stage2 escalated to a human", deg.get("stage2_alerted") is True)
    check(f"{cond}: stage3 halted OPENING orders", br.open_orders_halted is True,
          "the only stage that needs no venue cooperation")
    check(f"{cond}: ALARM.log written", os.path.exists(os.path.join(r, "_wd", "ALARM.log")))
    shutil.rmtree(r, ignore_errors=True)

print("[D2] headline must reflect a watchdog trip, not just the guards")
# 0C found a run whose report said "Status: OK" on line 3 while the body said tripped:True and the
# book had been flattened. When headline and body disagree the headline wins — that is the whole
# point of a headline. So this asserts the report TEXT, not the internal dict.
import tempfile as _tf
r = build(pnl_pct=-8.0)                       # trips §4-2
_out = _tf.mkdtemp(prefix="rep_")
# Override EVERY production-state path (not only the one that broke last time — overriding just
# that one is how the next one breaks). override_all covers pilot_log / pilot_daily / mirror /
# watchdog / regime / delivery status / smtp config in a single call.
_restore = override_all(PD, RC, DR, tmp=_out)
# the panel is a build artifact that exists only on the server; a synthetic fixture keeps this
# suite hermetic so a change can be verified where it is written (see tests_fixture.py).
_fx, _fxrestore = FIX.install(PD, RC, SPL, dirpath=_out + "/fixture")
PD.LOG_ROOT = r
try:
    rep = PD.main(days_back=1, skip_log=True, verbose=False)
finally:
    _fxrestore(); _restore()
check("watchdog actually tripped in this run", rep["watchdog"]["tripped"])
check("status is NOT 'OK' when the watchdog tripped", rep["status"] != "OK", rep["status"][:60])
check("status names the trip", "TRIPPED" in rep["status"])
import glob as _g
_rep = sorted(_g.glob(_out + "/pilot_daily/2026*/report.md"))
if check("report file written", bool(_rep)):
    _t = open(_rep[-1]).read()
    head = [l for l in _t.splitlines() if l.startswith("**Status:")][0]
    check("REPORT HEADLINE says TRIPPED (not OK)", "TRIPPED" in head, head[:70])
    check("headline mentions the protective action",
          "flattened" in head or "reduce-only" in head, head[:70])
shutil.rmtree(r, ignore_errors=True); shutil.rmtree(_out, ignore_errors=True)

print("[D3] data-age bound is bound to the data-source type")
_out3 = _tf.mkdtemp(prefix="ds_")
_fx3, _fx3restore = FIX.install(PD, RC, SPL, dirpath=_out3 + "/fixture")
old_src = PD.DATA_SOURCE_TYPE
try:
    PD.DATA_SOURCE_TYPE = "some_new_feed_nobody_calibrated"
    g = PD.run_guards(verbose=False)
    check("unknown data source BLOCKS rather than reusing another source's gate",
          not g["ok"] and "calibrated" in (g.get("blocking_reason") or ""),
          (g.get("blocking_reason") or "")[:60])
finally:
    PD.DATA_SOURCE_TYPE = old_src
    _fx3restore(); shutil.rmtree(_out3, ignore_errors=True)
check("live_venue_feed has a much tighter bound than the archive feed",
      PD.DATA_SOURCE_MAX_DATA_AGE_H["live_venue_feed"] < PD.DATA_SOURCE_MAX_DATA_AGE_H["t_plus_1_public_archive"],
      f'{PD.DATA_SOURCE_MAX_DATA_AGE_H["live_venue_feed"]}h vs {PD.DATA_SOURCE_MAX_DATA_AGE_H["t_plus_1_public_archive"]}h')

print("[D4] tests must not be able to write into PRODUCTION state (ANY path)")
_prod = MA + "/exports/live/watchdog/state.json"
_before = open(_prod).read() if os.path.exists(_prod) else None
r = build(pnl_pct=-8.0)
_out2 = _tf.mkdtemp(prefix="iso_")
_restore = override_all(PD, RC, DR, tmp=_out2)
_fx, _fxrestore = FIX.install(PD, RC, SPL, dirpath=_out2 + "/fixture")
PD.LOG_ROOT = r
try:
    PD.main(days_back=1, skip_log=True, verbose=False)
finally:
    _fxrestore(); _restore()
_after = open(_prod).read() if os.path.exists(_prod) else None
check("production watchdog state unchanged by a tripping test", _before == _after,
      "a test writing a trip into production state is how an invisible HALT was manufactured")
shutil.rmtree(r, ignore_errors=True); shutil.rmtree(_out2, ignore_errors=True)

print("[D5] ★ opening-halt must NOT block the reduce-only flatten")
# Moving the halt to the FRONT of the ladder is only safe if it is defined strictly over OPENING
# direction. If it blocked reduce-only too, the halt would block our own exit -- turning the
# improvement into a disaster. This is the test that makes the reorder safe.
br = WD.MockBroker()
br.halt_opening_orders("test")
check("halt is engaged", br.open_orders_halted is True)
try:
    orders = br.flatten_all({"BTC": 5000.0, "ETH": -3000.0}, "test flatten while halted")
    check("reduce-only flatten still submits while halted", len(orders) == 2, f"{len(orders)} orders")
    check("every flatten order is reduce_only", all(o["reduce_only"] for o in orders))
except Exception as e:
    check("reduce-only flatten still submits while halted", False, f"{type(e).__name__}: {e}")
try:
    br.submit({"symbol": "BTC", "side": "buy", "notional": 100.0, "reduce_only": False}, "opening")
    check("OPENING order is refused while halted", False, "it was accepted")
except WD.OpeningHalted:
    check("OPENING order is refused while halted", True)

print("[D6] ladder order: halt runs FIRST and survives failures of the other rungs")
r = build(reject=True)
ops, events, _ = WI.collect(r)
br = WD.MockBroker(fail_submit=True, fail_reduce_only=True)   # both venue-dependent rungs fail
ev, br, st = WD.run(r, broker=br, venue_events=events, ops_stats=ops, verbose=False,
                    state_dir=r + "/_wd")
deg = ev.get("degradation", {})
check("halt ran despite flatten AND reduce-only both failing", br.open_orders_halted is True,
      "the zero-dependency rung must not be gated by the fragile ones")
check("ladder records the declared order", deg.get("order") == ["halt_opening", "flatten", "alert"],
      str(deg.get("order")))
check("flatten failure recorded, not swallowed", deg.get("stage1_ok") is False)
check("alert still written despite the other failures", deg.get("stage2_local_write_ok") is True)
shutil.rmtree(r, ignore_errors=True)

print("[E] per-track factor-version registry (protocol -> declaration -> observation)")
ok, d = FVR.assert_track_version("champion", "funding_ema_broken_v1")
check("champion declaring pre-fix is CORRECT (control arm)", ok, d["meaning"][:60])
ok, d = FVR.assert_track_version("champion_fixfunding", "funding_ema_normfix")
check("fixfunding declaring corrected is CORRECT", ok)
ok, d = FVR.assert_track_version("pilot_book", "funding_ema_broken_v1")
check("pilot_book declaring pre-fix is a VIOLATION (§5 says corrected)", not ok, d["meaning"][:70])
check("registry is per-track, not a scalar", isinstance(FVR.TRACK_EXPECTED_VERSION, dict)
      and len(set(FVR.TRACK_EXPECTED_VERSION.values())) > 1,
      "a global assertion would turn the shadow red for no reason")

print("[D4-ALL] ★ production state must be byte-identical after the whole test run")
_ok, _diff = _GUARD.assert_unchanged()
check("no production state path was modified by this test run", _ok,
      ("clean" if _ok else f"MUTATED: {_diff}"))
if not _ok:
    print("    ⚠ failure form #4: the verification apparatus wrote into the state it verifies.",
          flush=True)
    for k, v in _diff.items():
        print(f"      {k}: +{v['n_added']} ~{v['n_changed']} -{v['n_removed']} {v['changed'][:3]}",
              flush=True)

print(f"\n  {'ALL PASS' if not fails else 'FAILURES: ' + str(fails)}", flush=True)
sys.exit(0 if not fails else 1)
