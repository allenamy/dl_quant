#!/usr/bin/env python3
"""Per-name stop contribution PER HOLDING INTERVAL (Task B synthesis 2026-09-26; extends stop_counterfactual.py, whose stop list was hand-typed
and whose comparison was a single end-aligned number). READ-ONLY, pooled over names and arms (blind-state rule: no arm split).
Stops   = every "★ per_name_stop 触发: <SYM>" event in state/notify_audit.jsonl inside the window (not a hand list).
Held counterfactual  the stopped name keeps the QUANTITY it had at the last nonzero post-anchor readback at/before the fire time, no further trading.
Actual               the name's readback position of each interval (whatever the executor still held while exiting, then 0).
Per interval k (readback t_k -> t_{k+1}), per stopped name: actual_k = n_read_k * r_k ;  held_k = n_stop * (P_k / P_stop) * r_k ;
contribution_k = actual_k - held_k  (positive = the stop saved money in that interval). r from the latest snapshot rr (nc_contract.rr_from_ch0);
a name/interval without a price is UNPRICED (listed, never 0). Intervals after the last readback covered by the price data are not evaluated.
usage: ~/wide_shadow/venv/bin/python stop_per_anchor.py <out json> [--from 2026-09-16T12] [--snap <anchor>]"""
import argparse, calendar, collections, glob, hashlib, json, os, re, sys, time
import numpy as np
HOME = os.path.expanduser("~"); WS = f"{HOME}/wide_shadow"; LIVE = f"{HOME}/dl_quant_live"; L = f"{LIVE}/state/live/pilot_log"
sys.path.insert(0, f"{WS}/fea171"); import nc_contract as NC
fmt = lambda t: time.strftime("%m-%dT%H:%MZ", time.gmtime(t))
ap = argparse.ArgumentParser(); ap.add_argument("out"); ap.add_argument("--from", dest="t0", default="2026-09-16T12"); ap.add_argument("--snap", default=None)
a = ap.parse_args()
T0 = calendar.timegm(time.strptime(a.t0, "%Y-%m-%dT%H"))
snap = f"{WS}/state/snap/{a.snap}" if a.snap else sorted(d for d in glob.glob(f"{WS}/state/snap/17*") if os.path.exists(f"{d}/rolling.npz"))[-1]
Z = np.load(f"{snap}/rolling.npz"); B = np.load(f"{snap}/boundary_raw.npz"); ts = Z["ts"].astype(np.int64)
RR = NC.rr_from_ch0(ts, Z["data"][:, :, 0], B["ts"], B["col"], B["raw"]).astype(np.float64)
syms = json.load(open(f"{WS}/shadow_bundle/config.json"))["symbols_panel"]; col = {s: j for j, s in enumerate(syms)}
fin = np.isfinite(RR)
LP = np.vstack([np.zeros((1, RR.shape[1])), np.cumsum(np.log1p(np.where(fin, RR, 0.0)), axis=0)])
NF = np.vstack([np.zeros((1, RR.shape[1]), int), np.cumsum(~fin, axis=0)])
T_DATA = int(ts[-1]) + 300


def logp(s, t):
    """cumulative log price at time t (bar closing at or before t); None if unpriced."""
    if s not in col: return None
    i = int(np.searchsorted(ts, t, side="right")) - 1
    return (i, LP[i + 1, col[s]]) if i >= 0 else None


def ret(s, tA, tB):
    x, y = logp(s, tA), logp(s, tB)
    if x is None or y is None: return None
    if NF[y[0] + 1, col[s]] - NF[x[0] + 1, col[s]] > 0: return None      # any missing bar inside the interval => unpriced
    return float(np.expm1(y[1] - x[1]))


# stops from the audit (not a hand list)
stops = []
for l in open(f"{LIVE}/state/notify_audit.jsonl"):
    try: d = json.loads(l)
    except ValueError: continue
    m = str(d.get("message", "")); t = float(d.get("ts") or 0)
    for sy in re.findall(r"per_name_stop 触发: ([A-Z0-9]+USDT)", m):
        if t >= T0: stops.append((t, sy))
stops = sorted(set(stops))
# readbacks (post-anchor batches)
pos = collections.defaultdict(dict); rt = {}
for dd in sorted(glob.glob(f"{L}/2026*")):
    p = f"{dd}/position_readback.jsonl"
    if not os.path.exists(p) or os.path.basename(dd) < time.strftime("%Y%m%d", time.gmtime(T0 - 86400)): continue
    for ln in open(p):
        if not ln.strip(): continue
        r = json.loads(ln); A = float(r["anchor_ts"])
        pos[A][r["symbol"]] = float(r.get("venue_position_notional") or 0.0); rt[A] = max(rt.get(A, 0.0), float(r.get("read_ts") or A))
keys = sorted(k for k in pos if rt[k] <= T_DATA)
per_int = collections.OrderedDict(); per_stop = []; unpriced = []
for (tf, s) in stops:
    prior = [k for k in keys if rt[k] <= tf + 1800 and abs(pos[k].get(s, 0.0)) > 0]
    if not prior: per_stop.append({"sym": s, "fire": fmt(tf), "note": "no nonzero readback at/before the stop"}); continue
    k0 = prior[-1]; n0 = pos[k0][s]; t_stop = rt[k0]
    tot_a = tot_h = 0.0; n_int = 0
    after = [k for k in keys if rt[k] >= t_stop]
    for kA, kB in zip(after, after[1:]):
        tA, tB = rt[kA], rt[kB]
        r = ret(s, tA, tB); grow = ret(s, t_stop, tA)
        if r is None or grow is None:
            unpriced.append({"sym": s, "interval": [fmt(tA), fmt(tB)]}); continue
        act = pos[kA].get(s, 0.0) * r
        held = n0 * (1.0 + grow) * r
        c = per_int.setdefault(kB, {"interval_end_anchor": fmt(kB), "interval": [fmt(tA), fmt(tB)], "actual": 0.0, "held": 0.0, "contribution": 0.0, "names": []})
        c["actual"] += act; c["held"] += held; c["contribution"] += act - held; c["names"].append(s)
        tot_a += act; tot_h += held; n_int += 1
    per_stop.append({"sym": s, "fire": fmt(tf), "stop_readback": fmt(t_stop), "notional_at_stop": round(n0, 2), "side": "long" if n0 > 0 else "short",
                     "intervals": n_int, "actual_after_stop": round(tot_a, 2), "held_counterfactual": round(tot_h, 2), "saved": round(tot_a - tot_h, 2)})
rows = [{**v, "actual": round(v["actual"], 2), "held": round(v["held"], 2), "contribution": round(v["contribution"], 2)} for v in per_int.values()]
out = {"device": "stop_per_anchor.py", "self_sha256": hashlib.sha256(open(os.path.abspath(__file__), "rb").read()).hexdigest(),
       "utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()), "window_from": fmt(T0), "price_snapshot": snap, "price_data_end": fmt(T_DATA),
       "last_readback_evaluated": fmt(rt[keys[-1]]), "n_stops": len(stops), "stops": per_stop, "per_interval": rows, "unpriced": unpriced,
       "total": {"actual_after_stop": round(sum(r["actual"] for r in rows), 2), "held": round(sum(r["held"] for r in rows), 2),
                 "saved": round(sum(r["contribution"] for r in rows), 2)}}
with open(a.out, "w") as f: json.dump(out, f, indent=1)
print(f"stops {len(stops)} window {fmt(T0)}..{out['last_readback_evaluated']} (price data to {fmt(T_DATA)}); total saved {out['total']['saved']:+.2f} "
      f"(actual {out['total']['actual_after_stop']:+.2f} vs held {out['total']['held']:+.2f}); intervals {len(rows)}; unpriced {len(unpriced)}")
for r in per_stop: print(" ", r)
