"""After a LOCAL response (production rows_root), the NEXT anchor is halted: blocked opening rows, no submission. Does §4-5e
judge the held book against intent ZERO (flat_intent_legacy) and trip the whole-book ladder?"""
import sys, os, json, shutil, tempfile
SUITE = "/Users/haosiyu/cc_tmp/fx_w6c/live/tests_proportional_response.py"
src = open(SUITE).read()
cut = src.index('print("[A0] control')
g = {"__file__": SUITE, "__name__": "probe"}
exec(compile(src[:cut], SUITE, "exec"), g)
WD, WI, PL, build, NAMES, EACH, T2 = g["WD"], g["WI"], g["PL"], g["build"], g["NAMES"], g["EACH"], g["T2"]

class TrueMock(WD.MockBroker):
    def account_snapshot(self):
        c = dict(self._contracts)
        return {"positions_notional": dict(c), "positions_contracts": dict(c), "contracts_caliber": "mark 1", "read_ts": 0}

R1 = {"S007USDT": 300.0}
root = build(R1)
b = TrueMock(positions={s: EACH + R1.get(s, 0.0) for s in NAMES})
ops = WI.derive_ops_stats(root)
sd = tempfile.mkdtemp(prefix="probe3_")
ev, brk, st = WD.run(root, broker=b, venue_events=[], ops_stats=ops, verbose=False, state_dir=sd, rows_root=root)
print("eval1 tripped", ev["tripped"], "local", [lr["names"] for lr in ev.get("local_responses") or []])
# next anchor T3 (halted): every name's order blocked (no submit), readback = venue (S007 gone), anchors row
T3 = 1789330000.0
day = "20260914"
lg = PL.PilotLogger(root, day)
lg.anchor(anchor_ts=T3, target_vector_hash="h", realized_gross=99000.0, target_gross=100000.0, n_names_skipped=0,
          regime_at_anchor="calm", mid_at_anchor_vector={s: 1.0 for s in NAMES}, factor_version="f", panel_hash="p")
for s in NAMES:
    lg.order(anchor_ts=T3, symbol=s, side="buy", target_w=0.01, prev_w=0.01, intended_notional=(1000.0 if s == "S007USDT" else 0.0),
             order_type="maker", submit_ts=None, price_submit=None, mid_at_submit=1.0, mid_at_anchor=1.0, filled_notional=None,
             avg_fill_px=None, first_fill_ts=None, last_fill_ts=None, cancel_ts=None, fee_paid=None, rebalance_id=f"A{int(T3)}",
             attempt_idx=1, terminal_reason=("blocked_by_halt" if s == "S007USDT" else "skipped_min_notional"), notional_currency="USDT")
    q = float(b._contracts.get(s, 0.0))
    lg.position_readback(anchor_ts=T3, symbol=s, venue_position_notional=q, venue_position_qty=q, source="mock", read_ts=T3 + 10)
lg.daily_nav(day=int(day), target_gross=100000.0, nav=50000.0, sizing_policy="constant_leverage_2.00", realised_pnl=0.0, unrealised_pnl=0.0)
lg.close()
ops3 = WI.derive_ops_stats(root)
ev3 = WD.evaluate(root, venue_events=[], ops_stats=ops3)
c5 = ev3["conditions"]["cond5_venue_event"]; pb = c5.get("5e_position_break") or {}
print("eval3 tripped", ev3["tripped"], [t[:140] for t in ev3["triggers"]])
print("eval3 local", [lr["names"] for lr in ev3.get("local_responses") or []], "route", (ev3.get("proportional_response") or {}).get("route"), (ev3.get("proportional_response") or {}).get("why"))
print("5b", c5["5b_liquidation_anomaly"]["state"], "5e", pb.get("state"), pb.get("trip_gate"), (pb.get("latest") or {}).get("anchor_kind"), (pb.get("latest") or {}).get("portfolio_dev_frac"))
