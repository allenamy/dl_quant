#!/usr/bin/env python3
"""t7_pull_offset_spectrum.py — timestamp offset-spectrum guard once per calendar year, per venue, on KRW-BTC/BTCUSDT and KRW-XRP/XRPUSDT (rules frozen in plan 'offset_spectrum').
Level alignment on detrended hourly log closes (not returns). Negative controls: KST-as-UTC relabel (+9) and close-time relabel (+1) must move the peak.
Reads <root>/derived. Output <root>/checks/OFFSET_SPECTRUM_T7_pull.json."""
import os, json, math, hashlib, argparse, time, calendar
import numpy as np
ap = argparse.ArgumentParser(); ap.add_argument("--root", required=True); A = ap.parse_args(); ROOT = A.root
_pb = open(ROOT + "/plan/PULL_PLAN_FROZEN.json", "rb").read(); assert hashlib.sha256(_pb).hexdigest() == open(ROOT + "/plan/PULL_PLAN_FROZEN.json.sha256").read().split()[0]
PLAN = json.loads(_pb); CUTOFF, PULL_END = PLAN["cutoff_epoch"], PLAN["pull_end_epoch"]
def load(p):
    z = np.load(p); return dict(zip(z["open_s"].tolist(), z["close"].tolist()))
def detrend(a):
    o = np.full_like(a, np.nan); fin = np.isfinite(a); cs = np.concatenate([[0.0], np.cumsum(np.where(fin, a, 0.0))]); cn = np.concatenate([[0], np.cumsum(fin)])
    for i in range(len(a)):
        lo, hi = max(0, i - 24), min(len(a), i + 25); n = cn[hi] - cn[lo]
        if fin[i] and n >= 24: o[i] = a[i] - (cs[hi] - cs[lo]) / n
    return o
def spectrum(x, y):
    xd, yd = detrend(x), detrend(y); rho, disp = {}, {}
    for k in range(-12, 13):
        a, b = (xd[k:], yd[:len(yd) - k]) if k >= 0 else (xd[:len(xd) + k], yd[-k:])
        m = np.isfinite(a) & np.isfinite(b); rho[k] = float(np.corrcoef(a[m], b[m])[0, 1]) if m.sum() > 48 else float("nan")
        s = (x[k:] - y[:len(y) - k]) if k >= 0 else (x[:len(x) + k] - y[-k:])
        med = np.array([np.nanmedian(s[max(0, i - 24):i + 25]) if np.isfinite(s[i]) else np.nan for i in range(len(s))])
        disp[k] = float(np.nanstd(s - med))
    am = max((k for k in rho if np.isfinite(rho[k])), key=lambda k: rho[k]); dm = min(disp, key=disp.get)
    return {"argmax_rho": am, "rho_m1": round(rho[-1], 5), "rho0": round(rho[0], 5), "rho_p1": round(rho[1], 5), "argmin_disp": dm}
out = {"device": os.path.basename(__file__), "run_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()), "plan_sha256": hashlib.sha256(_pb).hexdigest(), "cells": []}
BEND = calendar.timegm((2026, 9, 1, 0, 0, 0))   # last Binance monthly zip is 2026-08
for v in ("upbit", "bithumb"):
    for mk, sym in (("KRW-BTC", "BTCUSDT"), ("KRW-XRP", "XRPUSDT")):
        kp, bp = ROOT + "/derived/%s/%s_60m.npz" % (v, mk), ROOT + "/derived/binance/%s.npz" % sym
        if not (os.path.exists(kp) and os.path.exists(bp)): out["cells"].append({"venue": v, "market": mk, "status": "NO_DATA"}); continue
        K, B = load(kp), load(bp)
        for yr in range(time.gmtime(CUTOFF).tm_year, time.gmtime(PULL_END).tm_year + 1):
            lo = max(CUTOFF, calendar.timegm((yr, 1, 1, 0, 0, 0))); hi = min(PULL_END, BEND, calendar.timegm((yr + 1, 1, 1, 0, 0, 0)))
            if hi - lo < 7 * 86400: continue
            hours = np.arange(lo, hi, 3600)
            x = np.array([math.log(K[t]) if t in K else np.nan for t in hours]); y = np.array([math.log(B[t]) if t in B else np.nan for t in hours])
            c = {"venue": v, "market": mk, "year": yr, "hours": len(hours), "krw_bars": int(np.isfinite(x).sum()), "index_bars": int(np.isfinite(y).sum())}
            sp = spectrum(x, y); c.update(sp)
            c["PASS"] = sp["argmax_rho"] == 0 and sp["rho0"] > max(sp["rho_m1"], sp["rho_p1"]) and sp["argmin_disp"] == 0
            nk = spectrum(np.concatenate([np.full(9, np.nan), x[:-9]]), y); nc = spectrum(np.concatenate([np.full(1, np.nan), x[:-1]]), y)
            c["NEG_kst"] = {"argmax_rho": nk["argmax_rho"], "argmin_disp": nk["argmin_disp"], "RED": nk["argmax_rho"] == 9 and nk["argmin_disp"] == 9}
            c["NEG_close"] = {"argmax_rho": nc["argmax_rho"], "argmin_disp": nc["argmin_disp"], "RED": nc["argmax_rho"] == 1 and nc["argmin_disp"] == 1}
            out["cells"].append(c); print(v, mk, yr, c["PASS"], sp, "negKST", c["NEG_kst"]["RED"], "negClose", c["NEG_close"]["RED"], flush=True)
cells = [c for c in out["cells"] if "PASS" in c]
out["summary"] = {"n_cells": len(cells), "n_pass": sum(c["PASS"] for c in cells), "n_neg_kst_red": sum(c["NEG_kst"]["RED"] for c in cells), "n_neg_close_red": sum(c["NEG_close"]["RED"] for c in cells),
                  "non_pass": [(c["venue"], c["market"], c["year"]) for c in cells if not c["PASS"]], "no_data": [(c["venue"], c["market"]) for c in out["cells"] if c.get("status") == "NO_DATA"]}
json.dump(out, open(ROOT + "/checks/OFFSET_SPECTRUM_T7_pull.json", "w"), indent=1)
print(json.dumps(out["summary"]))
