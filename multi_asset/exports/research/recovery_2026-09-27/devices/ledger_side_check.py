#!/usr/bin/env python3
"""Ledger-side half of the §8 first-anchor checklist, OFFLINE (no credential, no network): K2 fill ratio, K3 ledger taker share,
K4 blocked_by_halt rows, K5 watchdog state / last ALARM line, K7 pooled fee + slippage — for the anchor whose rid lies in [A, A+4h).
Independent cross-check of the venue-side receipt. usage: /usr/bin/python3 ledger_side_check.py <A> [--out json]"""
import json, os, sys, time
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import venue_readonly as V
A = int(sys.argv[1]); out = sys.argv[sys.argv.index("--out") + 1] if "--out" in sys.argv else None
oids, cids, arow, blocked, taker, fill_n = V.local_ledger(A)
sys.path.insert(0, os.path.join(V.LIVE_REPO, "live")); import pilot_log as PL
root = os.path.join(V.LIVE_REPO, "state", "live", "pilot_log"); day = time.strftime("%Y%m%d", time.gmtime(A))
rid = arow["rebalance_id"]; D = PL.read_day(root, day); fills = [f for f in PL.read_fills(root, day) if f.get("rebalance_id") == rid]
CN = sum(abs(f.get("fill_notional") or 0) for f in fills if f.get("commission_asset") == "USDT"); C = sum(f.get("commission") or 0 for f in fills if f.get("commission_asset") == "USDT")
S = SN = 0.0
for o in D["orders"]:
    if o.get("rebalance_id") != rid: continue
    fn = abs(o.get("filled_notional") or 0); px, mid = o.get("avg_fill_px"), o.get("mid_at_submit")
    if fn and px and mid: S += fn * (1 if str(o.get("side")).upper() == "BUY" else -1) * (px - mid) / mid * 1e4; SN += fn
wd = os.path.join(V.LIVE_REPO, "state", "live", "watchdog")
st = os.path.join(wd, "state.json"); alarm_last = (open(os.path.join(wd, "ALARM.log")).read().strip().splitlines() or [""])[-1][:200]
rec = {"A": A, "rebalance_id": rid, "K2_fill_ratio": round((arow.get("realized_gross") or 0) / arow["target_gross"], 4), "target_gross": arow["target_gross"],
       "realized_gross": arow.get("realized_gross"), "K3_taker_share_ledger_pooled": taker, "K4_blocked_by_halt_rows": blocked,
       "K5_watchdog_state_json_exists": os.path.exists(st), "K5_alarm_last_line": alarm_last,
       "K7_fee_bps_usdt_fills": round(C / CN * 1e4, 2) if CN else None, "K7_slip_bps_vs_mid_at_submit": round(S / SN, 2) if SN else None,
       "ledger_fill_notional": fill_n, "n_orders_rows": sum(1 for o in D["orders"] if o.get("rebalance_id") == rid), "n_fills": len(fills),
       "utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())}
print(json.dumps(rec, indent=1, default=str))
if out:
    with open(out, "x") as f: json.dump(rec, f, indent=1, default=str)
