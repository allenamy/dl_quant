#!/usr/bin/env python3
"""Mechanism check of the reshape step (Task B, lead's estimate "reshape difference ≈ paper-vs-live difference"). READ-ONLY.
The executor's reshape re-demeans the producer's raw book: L1 = s * (L0 - net/N), so to first order the reshape P&L is -net_L0 x mean return of
the book's names. This device does NOT use layered_book's per-name reconstruction: per anchor it takes only net_L0 (the E6 identity value
recorded in LAYERED_BOOK.json) and an equal-weight market return of the live universe over [A+30 min, next A+30 min] from the latest snapshot
rr, and compares est = -net_L0 x r_mkt with layered_book's reshape step (L1 - L0). Estimated, not certified (proxy market, fixed offsets).
usage: ~/wide_shadow/venv/bin/python reshape_mechanism.py <LAYERED_BOOK.json> <out json>"""
import glob, hashlib, json, os, sys, time, calendar
import numpy as np
HOME = os.path.expanduser("~"); WS = f"{HOME}/wide_shadow"; sys.path.insert(0, f"{WS}/fea171"); import nc_contract as NC
LB = json.load(open(sys.argv[1]))
snap = sorted(d for d in glob.glob(f"{WS}/state/snap/17*") if os.path.exists(f"{d}/rolling.npz"))[-1]
Z = np.load(f"{snap}/rolling.npz"); B = np.load(f"{snap}/boundary_raw.npz"); ts = Z["ts"].astype(np.int64)
RR = NC.rr_from_ch0(ts, Z["data"][:, :, 0], B["ts"], B["col"], B["raw"]).astype(np.float64)
cfg = json.load(open(f"{WS}/shadow_bundle/config.json")); col = {s: j for j, s in enumerate(cfg["symbols_panel"])}
live = [col[s] for s in cfg["symbols_live"] if s in col]
LP = np.vstack([np.zeros((1, RR.shape[1])), np.cumsum(np.log1p(np.nan_to_num(RR)), axis=0)]); FIN = np.isfinite(RR)
def mkt(tA, tB):
    i0 = int(np.searchsorted(ts, tA, side="right")) - 1; i1 = int(np.searchsorted(ts, tB, side="right")) - 1
    if i1 <= i0 or tB > ts[-1] + 300: return None
    ok = [j for j in live if FIN[i0 + 1:i1 + 1, j].mean() >= 0.9]
    return float(np.mean(np.expm1(LP[i1 + 1, ok] - LP[i0 + 1, ok])))
rows = []
for a in LB["anchors"]:
    A = calendar.timegm(time.strptime("2026-" + a["A"], "%Y-%m-%dT%H:%MZ"))
    if not a.get("priced") or "L1_reshaped" not in (a.get("pnl_by_layer") or {}): continue
    d = a["pnl_by_layer"]["L1_reshaped"] - a["pnl_by_layer"]["L0_raw"]; n0 = a["net_by_layer"]["L0_raw"]; m = mkt(A + 1800, A + 14400 + 1800)
    if m is None: continue
    rows.append({"A": a["A"], "net_L0": round(n0, 1), "r_mkt": round(m, 6), "est": round(-n0 * m, 1), "reshape_step": round(d, 1)})
e = np.array([r["est"] for r in rows]); d = np.array([r["reshape_step"] for r in rows])
out = {"device": "reshape_mechanism.py", "self_sha256": hashlib.sha256(open(os.path.abspath(__file__), "rb").read()).hexdigest(), "layered_book_sha256": hashlib.sha256(open(sys.argv[1], "rb").read()).hexdigest(),
       "price_snapshot": snap, "n": len(rows), "sum_est": round(float(e.sum()), 1), "sum_reshape_step": round(float(d.sum()), 1), "corr": round(float(np.corrcoef(e, d)[0, 1]), 4),
       "slope_step_on_est": round(float(np.polyfit(e, d, 1)[0]), 4), "mean_net_L0": round(float(np.mean([r["net_L0"] for r in rows])), 1), "rows": rows}
json.dump(out, open(sys.argv[2], "w"), indent=1)
print({k: v for k, v in out.items() if k != "rows"})
