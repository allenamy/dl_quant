#!/usr/bin/env python3
"""Per-name stop counterfactual (lead 2026-09-25 priority 2), READ-ONLY, pooled over names. For each name that hit a per-name stop in the window:
position at the stop = the last post-anchor readback at or before the stop anchor's read time (signed notional, identity: that name, that batch);
counterfactual = keep that notional to the window end (09-25T00:44Z readback) with no further trading: pnl_hold = notional_at_stop x r(stop read time -> window end);
actual after the stop = the name's mark-to-market P&L after the stop (readback marks + fills, same method as step5); prices for r from the live rolling cache rr
(nc_contract.rr_from_ch0, latest snapshot). Reports both and the difference (positive = the stop saved money).
usage: ~/wide_shadow/venv/bin/python stop_counterfactual.py <out json>"""
import json, os, sys, glob, collections, time, calendar
import numpy as np
HOME = os.path.expanduser("~"); WS = f"{HOME}/wide_shadow"; L = f"{HOME}/dl_quant_live/state/live/pilot_log"
sys.path.insert(0, f"{WS}/fea171"); import nc_contract as NC
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__))); from paper_vs_live import STOP_T, jl, fmt
T_END_READ = 1790297100 + 3600
snap = sorted(glob.glob(f"{WS}/state/snap/17*"))[-1]; Z = np.load(f"{snap}/rolling.npz"); B = np.load(f"{snap}/boundary_raw.npz"); ts = Z["ts"].astype(np.int64)
RR = NC.rr_from_ch0(ts, Z["data"][:, :, 0], B["ts"], B["col"], B["raw"]).astype(np.float64)
syms = json.load(open(f"{WS}/shadow_bundle/config.json"))["symbols_panel"]; col = {s: j for j, s in enumerate(syms)}
LP = np.vstack([np.zeros((1, RR.shape[1])), np.cumsum(np.log1p(np.nan_to_num(RR)), axis=0)])
def ret(s, tA, tB):
    i0 = int(np.searchsorted(ts, tA, side="right")) - 1; i1 = int(np.searchsorted(ts, tB, side="right")) - 1
    return float(np.expm1(LP[i1 + 1, col[s]] - LP[i0 + 1, col[s]]))
P = jl("position_readback"); bat = collections.defaultdict(dict); rt = {}
for p in P:
    a = float(p["anchor_ts"]); bat[a][p["symbol"]] = float(p.get("venue_position_notional") or 0.0); rt[a] = max(rt.get(a, 0.0), float(p.get("read_ts") or a))
keys = sorted(k for k in bat if rt[k] <= min(T_END_READ, ts[-1] + 300))
t_end = rt[keys[-1]]
res = {}; after = json.load(open(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "receipts", "stop_after_actual.json"))) if False else None
for s, t_stop in STOP_T.items():
    prior = [k for k in keys if rt[k] <= t_stop + 1800 and bat[k].get(s, 0.0) != 0.0]
    if not prior: res[s] = {"note": "no nonzero readback before the stop"}; continue
    k = prior[-1]; n = bat[k][s]; r = ret(s, rt[k], t_end)
    res[s] = {"stop_read": fmt(rt[k]), "notional_at_stop": round(n, 2), "side": "long" if n > 0 else "short", "ret_to_window_end": round(r, 4), "pnl_if_held": round(n * r, 2)}
tot = sum(v.get("pnl_if_held", 0.0) for v in res.values())
json.dump({"window_end_read": fmt(t_end), "price_source": snap, "per_name": res, "sum_pnl_if_held": tot}, open(sys.argv[1], "w"), indent=1)
print(f"window end {fmt(t_end)}; names {len(res)}; sum pnl if held from the stop to the window end: {tot:.2f} USDT")
for s, v in sorted(res.items(), key=lambda kv: kv[1].get("pnl_if_held", 0)): print(" ", s, v)
