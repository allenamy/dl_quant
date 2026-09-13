#!/usr/bin/env python3
"""t7_pull_plan.py — full-pull request budget from the census (no network). Upper bounds: pages counted as ceil(hours/200)
(bars exist only for traded hours, so real page counts are <= these). Plan date = census run date (2026-09-13).
Scopes: S-MAP = identity-verified (PASS) KRW markets + KRW-BTC + KRW-USDT per venue; S-ALL = every currently listed KRW market (turnover-share denominator).
History starts: H-REPLAY = max(first trading day, 2021-12-01) (60 d warm-up before the first replay anchor 2022-01-31); H-FULL = first trading day.
Items: 60m candles (primary), day candles (completeness identity), Binance futures/um indexPriceKlines 1h monthly zips for mapped symbols
(eligible window +/- 2 months; current month as daily zips), same count again if the perp last-price klines variant is also pulled.
Runtime = requests / rate, hosts in parallel (Upbit, Bithumb, data.binance.vision are separate hosts, each capped at 5 req/s)."""
import os, json, math, time, calendar
import numpy as np
T7 = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
C = json.load(open(T7 + "/receipts/CENSUS_krw_markets.json")); M = json.load(open(T7 + "/receipts/MAPPING_guard_r2.json"))
Z = np.load(T7 + "/receipts/pod2/T7_universe_elig.npz", allow_pickle=True); SYM = [str(s) for s in Z["symbols"]]; E = Z["E_ts"].astype(np.int64); EL = Z["elig_C0"]
def ep(s): return calendar.timegm(time.strptime(s[:19], "%Y-%m-%dT%H:%M:%S"))
PLAN_T = calendar.timegm((2026, 9, 13, 0, 0, 0)); H0 = calendar.timegm((2021, 12, 1, 0, 0, 0))
out = {"device": os.path.basename(__file__), "plan_date_utc": "2026-09-13", "venues": {}, "binance": {}}
BYTES_PER_BAR_GZCSV = 60   # measured below from the sample files
sz = []; nb = []
for f in os.listdir(T7 + "/sample"):
    if f.endswith("_60m.csv.gz"):
        sz.append(os.path.getsize(T7 + "/sample/" + f)); nb.append(sum(1 for _ in __import__("gzip").open(T7 + "/sample/" + f, "rt")) - 1)
BYTES_PER_BAR_GZCSV = sum(sz) / sum(nb); out["measured_gzcsv_bytes_per_bar"] = round(BYTES_PER_BAR_GZCSV, 1)
for v in ("upbit", "bithumb"):
    mk_map = sorted({d[v]["chosen"] for d in M["pairs"].values() if v in d and d[v]["chosen"]} | {"KRW-BTC", "KRW-USDT"})
    mk_all = sorted(C["venues"][v]["markets"])
    R = out["venues"][v] = {"n_markets_S-MAP": len(mk_map), "n_markets_S-ALL": len(mk_all)}
    for scope, mks in (("S-MAP", mk_map), ("S-ALL", mk_all)):
        for hist in ("H-REPLAY", "H-FULL"):
            hours = 0; req60 = 0; reqd = 0
            for mk in mks:
                fd = ep(C["venues"][v]["markets"][mk]["first_day_utc_label"]); st = max(fd, H0) if hist == "H-REPLAY" else fd
                h = max(0, (PLAN_T - st) // 3600); hours += h; req60 += max(1, math.ceil(h / 200)); reqd += max(1, math.ceil(h / 24 / 200))
            n = req60 + reqd
            R[f"{scope}/{hist}"] = {"bar_hours_upper": int(hours), "req_60m": req60, "req_days": reqd, "req_total": n,
                                    "hours_at_5rps": round(n / 5 / 3600, 2), "hours_at_4rps": round(n / 4 / 3600, 2),
                                    "gzcsv_MB_upper": round(hours * BYTES_PER_BAR_GZCSV / 1e6, 1)}
# Binance references: indexPriceKlines 1h monthly zips over each mapped symbol's eligible window +/- 2 months
syms = sorted(s for s, d in M["pairs"].items() if any(d.get(v, {}).get("chosen") for v in ("upbit", "bithumb"))) + ["BTCUSDT"]
months = 0
for s in syms:
    c = SYM.index(s) if s in SYM else None
    if s == "BTCUSDT" or c is None: lo, hi = calendar.timegm((2021, 10, 1, 0, 0, 0)), PLAN_T
    else:
        idx = np.where(EL[:, c])[0]; lo = int(E[idx[0]]) - 62 * 86400; hi = min(PLAN_T, int(E[idx[-1]]) + 62 * 86400)
    y0, m0 = time.gmtime(lo).tm_year, time.gmtime(lo).tm_mon; y1, m1 = time.gmtime(hi).tm_year, time.gmtime(hi).tm_mon
    months += (y1 - y0) * 12 + (m1 - m0) + 1
out["binance"] = {"n_symbols": len(syms), "monthly_zips_indexPriceKlines": months, "hours_at_5rps": round(months / 5 / 3600, 2),
                  "note": "the current partial month needs daily zips (<= 13 per symbol on 2026-09-13); doubling for the perp klines variant is optional"}
json.dump(out, open(T7 + "/receipts/PLAN_full_pull.json", "w"), indent=1)
print(json.dumps(out, indent=1))
