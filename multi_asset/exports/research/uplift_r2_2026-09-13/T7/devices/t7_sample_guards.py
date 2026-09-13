#!/usr/bin/env python3
"""t7_sample_guards.py — causal premium at 4h anchors on the sample, plus the two alignment guards (no returns anywhere).
FROZEN BEFORE RUNNING (rules and pass criteria):
ANCHORS: N in {00,04,08,12,16,20}Z with N-1h >= window start and N <= window end -> 360 anchors (2026-07-01T04Z .. 2026-08-30T00Z).
KRW BAR SELECTION (causal): for coin market i at anchor N, o_i = the largest bar open with N-4h <= o_i <= N-1h (bar closes o_i+1h <= N).
  No such bar => cell invalid. 'fresh' := o_i == N-1h.
BINANCE: futures/um index price 1h bar with open == o_i (synchronous with the KRW bar). Missing => invalid.
DEF A (FX cancels through BTC, same venue, same bar): pA = [ln Pkrw_i(o_i) - ln(Pidx_i(o_i)/mult_i)] - [ln Pkrw_BTC(o_i) - ln Pidx_BTC(o_i)].
DEF B (venue KRW-USDT market): pB = ln Pkrw_i(o_i) - ln(Pidx_i(o_i)/mult_i) - ln Pkrw_USDT(u), u = largest USDT bar open in [o_i-3h, o_i]; none => invalid.
  (Binance USDT-margined index prices are USDT-quoted, so Pidx/mult * KRW-USDT = implied KRW price.)
G1 CAUSALITY ASSERTION: every valid cell has o_i + 3600 <= N and Binance close_time_ms + 1 <= N*1000 (and u + 3600 <= N for DEF B).
  NEGATIVE CONTROL: the leaky selection o = N (bar closing at N+1h) must violate G1 on every cell where that bar exists (RED expected).
G2 HIT-RATE ASSERTION: hit = valid cells / (anchors x coin markets). DEF A cells: coin markets excluding BTC and USDT (Upbit ETH, XRP, PEPE, POL; Bithumb XRP, SHIB).
  DEF B cells: coin markets excluding USDT (BTC included). PASS iff hit >= 0.99 for each definition on each venue. Also report fresh fraction.
G3 OFFSET SPECTRUM (level alignment, not returns): series x(t) = ln KRW close of bar open t; y(t) = ln Binance index close of bar open t (BTC both venues, XRP both, ETH Upbit).
  Detrended levels x~(t) = x(t) - mean{x(s): |s-t| <= 24h}, same for y. rho(k) = Pearson corr over t of (x~(t+k), y~(t)), k = -12..+12 h, pairs with both finite.
  PASS iff argmax_k rho(k) == 0 and rho(0) > max(rho(-1), rho(+1)).
  NEGATIVE CONTROLS (must be RED at lag 0): (a) KST labels read as UTC: x_mis(t) = x(t-9h) => argmax must be +9; (b) bar labelled by close time: x_mis(t) = x(t-1h) => argmax must be +1.
  Secondary: dispersion D(k) = std_t of [x(t+k) - y(t)] minus its centred 49h median; PASS iff argmin_k D(k) == 0.
SANITY (level, not return): |pB(BTC)| < 0.15 at every valid anchor per venue; cross-venue XRP: median |pB_upbit - pB_bithumb| reported."""
import os, json, gzip, csv, math, calendar, time
import numpy as np
T7 = os.path.dirname(os.path.dirname(os.path.abspath(__file__))); S = T7 + "/sample"
MAN = json.load(open(S + "/SAMPLE_MANIFEST.json"))
W0 = calendar.timegm((2026, 7, 1, 0, 0, 0)); W1 = calendar.timegm((2026, 8, 30, 0, 0, 0)); NH = (W1 - W0) // 3600
def ep(s): return calendar.timegm(time.strptime(s[:19], "%Y-%m-%dT%H:%M:%S"))
def load_krw(v, mk):
    d = {}
    with gzip.open(f"{S}/{v}_{mk}_60m.csv.gz", "rt") as f:
        for r in csv.DictReader(f): d[ep(r["candle_date_time_utc"])] = float(r["trade_price"])
    return d
def load_bin(sym):
    d = {}; ct = {}
    with gzip.open(f"{S}/binance_indexPriceKlines_{sym}_1h.csv.gz", "rt") as f:
        for r in csv.DictReader(f): o = int(r["open_time_ms"]) // 1000; d[o] = float(r["close"]); ct[o] = int(r["close_time_ms"])
    return d, ct
VEN = {"upbit": {"coins": {"KRW-ETH": ("ETHUSDT", 1), "KRW-XRP": ("XRPUSDT", 1), "KRW-PEPE": ("1000PEPEUSDT", 1000), "KRW-POL": ("POLUSDT", 1)}},
       "bithumb": {"coins": {"KRW-XRP": ("XRPUSDT", 1), "KRW-SHIB": ("1000SHIBUSDT", 1000)}}}
BIN = {s: load_bin(s) for s in ("BTCUSDT", "ETHUSDT", "XRPUSDT", "1000PEPEUSDT", "POLUSDT", "1000SHIBUSDT")}
anchors = [t for t in range(W0 + 4 * 3600, W1 + 1, 4 * 3600) if t - 3600 >= W0]
assert len(anchors) == 360, len(anchors)
out = {"device": os.path.basename(__file__), "n_anchors": len(anchors), "venues": {}}
def select(bars, N, leaky=False):
    if leaky: return N if N in bars else None
    for o in (N - 3600, N - 7200, N - 10800, N - 14400):
        if o in bars: return o
    return None
PB = {}
for v, cfg in VEN.items():
    K = {mk: load_krw(v, mk) for mk in ["KRW-BTC", "KRW-USDT"] + list(cfg["coins"])}
    coins = dict(cfg["coins"]); coins_B = {"KRW-BTC": ("BTCUSDT", 1), **coins}
    R = out["venues"][v] = {}
    g1_viol = 0; g1_cells = 0; leaky_cells = 0; leaky_viol = 0
    hitA = {"valid": 0, "cells": 0, "fresh": 0}; hitB = {"valid": 0, "cells": 0, "fresh": 0}
    usdt_stale = []
    for N in anchors:
        for mk, (sym, mult) in coins_B.items():
            bars = K[mk]; bi, bct = BIN[sym]; bb, bbct = BIN["BTCUSDT"]
            o = select(bars, N)
            # leaky negative control
            ol = select(bars, N, leaky=True)
            if ol is not None:
                leaky_cells += 1
                if not (ol + 3600 <= N): leaky_viol += 1
            isA = mk in coins
            if isA: hitA["cells"] += 1
            hitB["cells"] += 1
            if o is None or o not in bi: continue
            fresh = (o == N - 3600)
            g1_cells += 1
            if not (o + 3600 <= N and bct[o] + 1 <= N * 1000): g1_viol += 1
            base = math.log(bars[o]) - math.log(bi[o] / mult)
            if isA and o in K["KRW-BTC"] and o in bb:
                pA = base - (math.log(K["KRW-BTC"][o]) - math.log(bb[o]))
                hitA["valid"] += 1; hitA["fresh"] += fresh
            u = next((x for x in (o, o - 3600, o - 7200, o - 10800) if x in K["KRW-USDT"]), None)
            if u is not None:
                if not (u + 3600 <= N): g1_viol += 1
                pB = base - math.log(K["KRW-USDT"][u]); usdt_stale.append(o - u)
                hitB["valid"] += 1; hitB["fresh"] += fresh
                PB[(v, mk, N)] = pB
    R["G1_causality"] = {"cells_checked": g1_cells, "violations": g1_viol, "PASS": g1_viol == 0,
                         "negative_control_leaky": {"cells_with_bar_open_eq_N": leaky_cells, "violations": leaky_viol, "RED_as_expected": leaky_cells > 0 and leaky_viol == leaky_cells}}
    for nm, h in (("A", hitA), ("B", hitB)):
        h["hit_rate"] = round(h["valid"] / h["cells"], 6); h["fresh_frac_of_valid"] = round(h["fresh"] / max(1, h["valid"]), 6); h["PASS"] = h["hit_rate"] >= 0.99
        R["G2_hit_rate_def" + nm] = h
    R["defB_usdt_bar_staleness_hours_hist"] = {str(k // 3600): usdt_stale.count(k) for k in sorted(set(usdt_stale))}
    btc = [PB[(v, "KRW-BTC", N)] for N in anchors if (v, "KRW-BTC", N) in PB]
    R["SANITY_btc_pB"] = {"n": len(btc), "min": round(min(btc), 5), "median": round(float(np.median(btc)), 5), "max": round(max(btc), 5), "PASS": all(abs(x) < 0.15 for x in btc)}
    # G3 offset spectrum
    hours = np.arange(W0, W1, 3600)
    def arr(dct): return np.array([math.log(dct[t]) if t in dct else np.nan for t in hours])
    def detrend(a):
        o = np.full_like(a, np.nan)
        for i in range(len(a)):
            lo, hi = max(0, i - 24), min(len(a), i + 25); w = a[lo:hi]; w = w[np.isfinite(w)]
            if np.isfinite(a[i]) and len(w) >= 24: o[i] = a[i] - w.mean()
        return o
    def spectrum(x, y):
        xd, yd = detrend(x), detrend(y); rho = {}
        for k in range(-12, 13):
            if k >= 0: a, b = xd[k:], yd[:len(yd) - k]
            else: a, b = xd[:len(xd) + k], yd[-k:]
            m = np.isfinite(a) & np.isfinite(b); rho[k] = float(np.corrcoef(a[m], b[m])[0, 1])
        disp = {}
        for k in range(-12, 13):
            if k >= 0: s = x[k:] - y[:len(y) - k]
            else: s = x[:len(x) + k] - y[-k:]
            med = np.array([np.nanmedian(s[max(0, i - 24):i + 25]) if np.isfinite(s[i]) else np.nan for i in range(len(s))])
            r = s - med; disp[k] = float(np.nanstd(r))
        am = max(rho, key=rho.get); dm = min(disp, key=disp.get)
        return {"argmax_rho": am, "rho0": round(rho[0], 6), "rho_m1": round(rho[-1], 6), "rho_p1": round(rho[1], 6), "rho_at_argmax": round(rho[am], 6),
                "argmin_dispersion": dm, "disp0_over_disp1_min": round(disp[0] / min(disp[-1], disp[1]), 4), "rho_all": {str(k): round(r, 5) for k, r in rho.items()}}
    G3 = R["G3_offset_spectrum"] = {}
    for mk, sym in [("KRW-BTC", "BTCUSDT")] + [(m, s) for m, (s, _) in coins.items() if m in ("KRW-XRP", "KRW-ETH")]:
        x = arr(K[mk]); y = arr(BIN[sym][0])
        sp = spectrum(x, y); sp["PASS"] = sp["argmax_rho"] == 0 and sp["rho0"] > max(sp["rho_m1"], sp["rho_p1"]) and sp["argmin_dispersion"] == 0
        xk = np.concatenate([np.full(9, np.nan), x[:-9]]); nk = spectrum(xk, y)
        xc = np.concatenate([np.full(1, np.nan), x[:-1]]); nc = spectrum(xc, y)
        sp["NEG_kst_as_utc"] = {"argmax_rho": nk["argmax_rho"], "argmin_dispersion": nk["argmin_dispersion"], "RED_as_expected": nk["argmax_rho"] == 9 and nk["argmin_dispersion"] == 9}
        sp["NEG_close_time_label"] = {"argmax_rho": nc["argmax_rho"], "argmin_dispersion": nc["argmin_dispersion"], "RED_as_expected": nc["argmax_rho"] == 1 and nc["argmin_dispersion"] == 1}
        G3[mk] = sp
xr = [abs(PB[("upbit", "KRW-XRP", N)] - PB[("bithumb", "KRW-XRP", N)]) for N in anchors if ("upbit", "KRW-XRP", N) in PB and ("bithumb", "KRW-XRP", N) in PB]
out["SANITY_cross_venue_XRP_pB_abs_diff"] = {"n": len(xr), "median": round(float(np.median(xr)), 5), "p95": round(float(np.percentile(xr, 95)), 5)}
json.dump(out, open(T7 + "/receipts/GUARDS_sample.json", "w"), indent=1)
for v, R in out["venues"].items():
    print("==", v)
    print(" G1", R["G1_causality"])
    print(" G2A", R["G2_hit_rate_defA"]); print(" G2B", R["G2_hit_rate_defB"]); print(" usdt staleness", R["defB_usdt_bar_staleness_hours_hist"])
    print(" SANITY BTC pB", R["SANITY_btc_pB"])
    for mk, sp in R["G3_offset_spectrum"].items():
        print(" G3", mk, {k: sp[k] for k in ("argmax_rho", "rho0", "rho_m1", "rho_p1", "argmin_dispersion", "disp0_over_disp1_min", "PASS")}, "NEG_KST", sp["NEG_kst_as_utc"], "NEG_close", sp["NEG_close_time_label"])
print("XRP cross-venue", out["SANITY_cross_venue_XRP_pB_abs_diff"])
