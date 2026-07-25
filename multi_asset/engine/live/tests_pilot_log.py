"""Negative tests for the pilot v2 log schema + metrics — the paths that only matter when they fire.

Two behaviours cannot be verified by the happy-path acceptance run:
  1. write-time validation must REJECT a row missing a required field (the entire point of the
     logger is that day 1 fails loudly rather than analysis day failing silently);
  2. the stress blind-spot warning must fire when the window has no stress anchors -- 0C's
     synthetic day happened to contain all three regimes, so the acceptance run never exercised it.

Exit 0 = all pass.
"""
import os
import shutil, sys, tempfile

MA = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))   # .../multi_asset
sys.path.insert(0, MA + "/engine/live")
import pilot_log as PL
import pilot_metrics as PM

fails = []


def check(name, cond, detail=""):
    print(f"  {'OK  ' if cond else 'FAIL'} {name}{(' — ' + detail) if detail else ''}", flush=True)
    if not cond:
        fails.append(name)


def order_row(**over):
    row = dict(anchor_ts=1782950400000, symbol="BTC", side="buy", target_w=0.01, prev_w=0.0,
               intended_notional=500.0, order_type="maker", submit_ts=1782950400000,
               price_submit=100.0, mid_at_submit=100.0, mid_at_anchor=100.0,
               filled_notional=500.0, avg_fill_px=100.01, first_fill_ts=1782950401000,
               last_fill_ts=1782950402000, cancel_ts=None, fee_paid=0.09,
               rebalance_id="r0", attempt_idx=1, terminal_reason="filled", notional_currency="USD")
    row.update(over)
    return row


print("[1] write-time validation")
root = tempfile.mkdtemp(prefix="pl_neg_")
lg = PL.PilotLogger(root, "20260725")

# 1a. missing mid_at_anchor -> must raise (this is the field that fixes M1)
bad = order_row(); bad.pop("mid_at_anchor")
try:
    lg.order(**bad); check("rejects missing mid_at_anchor", False, "accepted a row without it")
except PL.SchemaError as e:
    check("rejects missing mid_at_anchor", "mid_at_anchor" in str(e))

# 1b. missing terminal_reason -> must raise (fixes M5)
bad = order_row(); bad.pop("terminal_reason")
try:
    lg.order(**bad); check("rejects missing terminal_reason", False)
except PL.SchemaError as e:
    check("rejects missing terminal_reason", "terminal_reason" in str(e))

# 1c. bogus terminal_reason -> must raise (enum is closed)
try:
    lg.order(**order_row(terminal_reason="whatever")); check("rejects unknown terminal_reason", False)
except PL.SchemaError:
    check("rejects unknown terminal_reason", True)

# 1d. bogus regime -> must raise
try:
    lg.anchor(anchor_ts=1, target_vector_hash="x", realized_gross=1.0, target_gross=1.0,
              n_names_skipped=0, regime_at_anchor="choppy", mid_at_anchor_vector={"BTC": 1.0},
              factor_version="v", panel_hash="h")
    check("rejects unknown regime label", False)
except PL.SchemaError:
    check("rejects unknown regime label", True)

# 1e. null in a not_null field -> must raise
try:
    lg.order(**order_row(mid_at_anchor=None)); check("rejects null mid_at_anchor", False)
except PL.SchemaError:
    check("rejects null mid_at_anchor", True)

# 1f. a valid row still writes
try:
    lg.order(**order_row()); check("accepts a valid order row", True)
except Exception as e:
    check("accepts a valid order row", False, str(e)[:80])
lg.close()
shutil.rmtree(root, ignore_errors=True)

print("[2] stress blind-spot warning")
root = tempfile.mkdtemp(prefix="pl_reg_")
lg = PL.PilotLogger(root, "20260725")
for i, reg in enumerate(["calm", "normal", "calm", "normal"]):        # deliberately NO stress
    ats = 1782950400000 + i * 4 * 3600_000
    lg.anchor(anchor_ts=ats, target_vector_hash="h", realized_gross=1000.0, target_gross=1000.0,
              n_names_skipped=0, regime_at_anchor=reg, mid_at_anchor_vector={"BTC": 100.0},
              factor_version="funding_ema_normfix", panel_hash="abc")
    lg.order(**order_row(anchor_ts=ats))
    lg.fill(anchor_ts=ats, symbol="BTC", side="buy", order_type="maker", attempt_idx=1,
            fill_ts=ats + 1000, fill_px=100.01, fill_notional=500.0,
            mid_at_fill_plus_60s=100.03, rebalance_id="r0")
    lg.position_readback(anchor_ts=ats, symbol="BTC", venue_position_notional=500.0,
                         source="venue_api_mock")
lg.daily_nav(day=20629, target_gross=1000.0, nav=100000.0, realised_pnl=5.0, unrealised_pnl=0.0)
lg.close()
res = PM.compute(root, verbose=False)
rc = res["regime_coverage"]
check("stress correctly reported absent", rc["stress_present"] is False)
check("blind-spot warning fires", bool(rc["blind_spot_warning"]),
      (rc["blind_spot_warning"] or "")[:60] + "…")
check("c still stratified by the regimes present",
      set(res["M1_effective_cost"]["by_regime"]) == {"calm", "normal"})
check("regimes_missing lists stress", rc["regimes_missing"] == ["stress"])
shutil.rmtree(root, ignore_errors=True)

print(f"\n  {'ALL PASS' if not fails else 'FAILURES: ' + str(fails)}", flush=True)
sys.exit(0 if not fails else 1)
