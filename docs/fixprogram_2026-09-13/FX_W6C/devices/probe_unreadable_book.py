"""Probe (scratch, MockBroker only): what does the watchdog do when the venue's positions are UNREADABLE across the book?
Three shapes, on the code tree given as argv[1]:
  U1  the newest anchor wrote NO position_readback rows (account snapshot failed ⇒ the loop writes none, anchor_loop ~L1197)
  U2  NO readback rows in the whole window (every anchor unreadable) while orders were sent
  U3  the newest anchor's readback rows exist but carry non-finite notionals (NaN) — written raw, bypassing the logger
"""
import json, os, sys, tempfile, shutil, math
code = sys.argv[1]
for d in ("live", "scheduler", "ops", "signal"):
    sys.path.insert(0, os.path.join(code, d))
import pilot_log as PL, watchdog as WD, watchdog_inputs as WI

NAMES = ["AAAUSDT", "BBBUSDT", "CCCUSDT", "DDDUSDT", "EEEUSDT", "FFFUSDT", "GGGUSDT", "HHHUSDT"]

def build(shape):
    root = tempfile.mkdtemp(prefix="probe_unreadable_")
    days = ["20260910", "20260911", "20260912"]
    for di, day in enumerate(days):
        lg = PL.PilotLogger(root, day)
        ats = 1789000000.0 + di * 86400
        lg.anchor(anchor_ts=ats, target_vector_hash="h", realized_gross=8000.0, target_gross=8000.0, n_names_skipped=0,
                  regime_at_anchor="calm", mid_at_anchor_vector={s: 1.0 for s in NAMES}, factor_version="f", panel_hash="p")
        for s in NAMES:
            lg.order(anchor_ts=ats, symbol=s, side="buy", target_w=0.125, prev_w=(0.125 if di else 0.0),
                     intended_notional=(1000.0 if di == 0 else 0.0), order_type="maker", submit_ts=ats, price_submit=1.0,
                     mid_at_submit=1.0, mid_at_anchor=1.0, filled_notional=(1000.0 if di == 0 else 0.0), avg_fill_px=1.0,
                     first_fill_ts=ats + 1, last_fill_ts=ats + 2, cancel_ts=None, fee_paid=0.2, rebalance_id=f"r{di}",
                     attempt_idx=1, terminal_reason="filled", notional_currency="USDT")
            write_rb = not ((shape == "U1" and di == len(days) - 1) or shape == "U2")
            if write_rb:
                lg.position_readback(anchor_ts=ats, symbol=s, venue_position_notional=1000.0, venue_position_qty=1000.0, source="mock", read_ts=ats + 10)
        lg.daily_nav(day=int(day), target_gross=8000.0, nav=4000.0, sizing_policy="constant_leverage_2.00", realised_pnl=0.0, unrealised_pnl=0.0)
        lg.close()
    if shape == "U3":
        p = os.path.join(root, days[-1], "position_readback.jsonl")
        rows = [json.loads(l) for l in open(p) if l.strip()]
        for r in rows:
            r["venue_position_notional"] = float("nan")
        open(p, "w").write("".join(json.dumps(r) + "\n" for r in rows))
    return root

out = {}
for shape in ("U1", "U2", "U3"):
    root = build(shape)
    try:
        ops = WI.derive_ops_stats(root)
        b = WD.MockBroker(positions={s: 1000.0 for s in NAMES}); b._notional = {s: 1000.0 for s in NAMES}
        sd = tempfile.mkdtemp(prefix="probe_unreadable_state_")
        ev, br, st = WD.run(root, broker=b, venue_events=[], ops_stats=ops, verbose=False, state_dir=sd)
        c5 = ev["conditions"]["cond5_venue_event"]
        out[shape] = {"tripped": ev["tripped"], "triggers": [t[:90] for t in ev["triggers"]], "blind": ev["conditions_blind"],
                      "5b_state": c5["5b_liquidation_anomaly"]["state"], "5b_last_ats": c5["5b_liquidation_anomaly"]["last_reconciled_anchor_ts"],
                      "5e_state": (c5.get("5e_position_break") or {}).get("state"), "5e_blind": (c5.get("5e_position_break") or {}).get("blind"),
                      "cond7_drift": ev["conditions"]["cond7_ops"].get("drift_state"),
                      "flatten_all": [a.get("n_orders") for a in br.actions if a.get("action") == "flatten_all"],
                      "local_responses": ev.get("local_responses")}
    except Exception as e:
        out[shape] = {"raised": f"{type(e).__name__}: {str(e)[:200]}"}
    shutil.rmtree(root, ignore_errors=True)
print(json.dumps({"code": code, "probe": out}, indent=1, default=str))
