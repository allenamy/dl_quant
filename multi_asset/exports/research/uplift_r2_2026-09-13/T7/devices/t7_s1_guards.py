#!/usr/bin/env python3
"""t7_s1_guards.py — S1 data guards G1–G5 on the full pull (frozen PREREG_T7_S1.md §2.4 with §11 additions). Runs on the Mac against /Users/haosiyu/cc_tmp/krw_pull.
Cell rules come from t7_s1_common.py (tradability, exclusions, bar rule). Frozen criteria:
- G4 (built first, exclusions): def-B identity drift per mapped pair: hourly pB at every hour h with a coin KRW bar (volume > 0), the coin index bar at h and a KRW-USDT
  bar in [h-3h, h]; daily median over >= 6 hours; trailing 30-day median over >= 10 days; |m30| > ln 1.25 flags (venue, symbol, month). G4 list = def-B flags
  UNION the §11.10 pinned list (Upbit KAVAUSDT 2022-12..2023-06; Bithumb CRVUSDT 2023-08..09, ENJUSDT 2023-10..11, SOLVUSDT 2026-04..05, TAIKOUSDT 2026-07).
- G5 (exclusions): every venue-market-day in checks/C3_MISMATCH_DETAIL.json.
- Grid: anchors every 4h from 2021-12-01T04:00Z to 2026-08-30T20:00Z. G2 cells: mapped pair x anchor with N >= census first day + 1 d, N inside
  [first index bar + 4h, last index bar + 1h] and inside [first perp bar + 4h, last perp bar + 1h]; def A excludes the KRW-BTC/BTCUSDT pair; def B needs
  N >= KRW-USDT first day + 1 d. Cells in G4-excluded pair-months, or whose coin market has a G5-flagged venue-day containing N-1h, are removed from the
  denominator (exclusions, not misses).
- G1 PASS: every valid def A / def B cell has o + 3600 <= N and (def B) u + 3600 <= N; negative control: with the leaky bar (open == N) every cell where such a bar
  exists must violate (all red).
- G2 PASS: valid / cells >= 0.99 for every venue x calendar year x definition.
- G3 PASS: per venue, per calendar year, for KRW-BTC/BTCUSDT, KRW-ETH/ETHUSDT, KRW-XRP/XRPUSDT (hourly ln close, KRW from raw pages, index filled series):
  argmax rho == 0, rho(0) > rho(+-1), argmin dispersion == 0; negative controls (x(t-9h) => +9, x(t-1h) => +1) must be red.
  G3b (panel alignment) runs on pod2 before any IC.
Output: /Users/haosiyu/cc_tmp/krw_pull/s1/S1_GUARDS.json, S1_G4_LIST.json, S1_G5_LIST.json. Exit 0 = G1, G2, G3 all PASS; exit 2 = STOP."""
import os, sys, json, time, calendar, math, collections, hashlib
import numpy as np
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import t7_s1_common as C
DEVICE_SHA = hashlib.sha256(open(os.path.abspath(__file__), "rb").read()).hexdigest()
COMMON_SHA = hashlib.sha256(open(os.path.join(os.path.dirname(os.path.abspath(__file__)), "t7_s1_common.py"), "rb").read()).hexdigest()
OUT = C.ROOT + "/s1"; os.makedirs(OUT, exist_ok=True)
PLAN = C.plan(); L125 = math.log(1.25)
first_day = {(v, m["market"]): m["first_day_epoch"] for v in ("upbit", "bithumb") for m in PLAN["krw"][v]}
PINNED = [("upbit", "KAVAUSDT", ["2022-12", "2023-01", "2023-02", "2023-03", "2023-04", "2023-05", "2023-06"]), ("bithumb", "CRVUSDT", ["2023-08", "2023-09"]),
          ("bithumb", "ENJUSDT", ["2023-10", "2023-11"]), ("bithumb", "SOLVUSDT", ["2026-04", "2026-05"]), ("bithumb", "TAIKOUSDT", ["2026-07"])]
t0 = time.time()
KRW = {}
def krw(v, mk):
    if (v, mk) not in KRW: KRW[(v, mk)] = C.derive_krw(v, mk)
    return KRW[(v, mk)]
IDX = {}; PERP = {}
def idx(s):
    if s not in IDX: IDX[s] = C.load_index(s)
    return IDX[s]
def perp(s):
    if s not in PERP: PERP[s] = C.load_perp(s)
    return PERP[s]
G5 = C.load_g5()
g5_list = sorted([[v, mk, time.strftime("%Y-%m-%d", time.gmtime(d))] for (v, mk), ds in G5.items() for d in ds])
json.dump({"rule": "every venue-market-day with hourly volume sum != day candle volume (C3_MISMATCH_DETAIL)", "n": len(g5_list), "days": g5_list}, open(OUT + "/S1_G5_LIST.json", "w"), indent=1)
# ---- G4 (def B drift) ----
g4flag = set()
for v in ("upbit", "bithumb"):
    KU = krw(v, "KRW-USDT")
    for p in [q for q in PLAN["pairs"] if q["venue"] == v]:
        K = krw(v, p["market"]); I = idx(p["symbol"])
        if I is None: continue
        h = K["open_s"]; ix = C.at(I["open_s"], h); iu = C.latest_in(KU["open_s"], h - 3 * 3600, h)
        ok = (ix >= 0) & (iu >= 0)
        if not ok.any(): continue
        pb = np.log(K["close"][ok]) - np.log(I["close"][ix[ok]] / p["mult"]) - np.log(KU["close"][iu[ok]])
        days = (h[ok] // 86400) * 86400; dm = {}
        for d in np.unique(days):
            sel = days == d
            if sel.sum() >= 6: dm[int(d)] = float(np.median(pb[sel]))
        dd = sorted(dm)
        for d in dd:
            vals = [dm[k] for k in range(d - 29 * 86400, d + 1, 86400) if k in dm]
            if len(vals) >= 10 and abs(float(np.median(vals))) > L125: g4flag.add((v, p["symbol"], C.month_of(d)))
g4set = set(g4flag) | {(v, s, m) for v, s, ms in PINNED for m in ms}
json.dump({"rule": "def-B 30d trailing median |pB| > ln 1.25 (flags) UNION §11.10 pinned five pairs", "def_B_flags": sorted([list(x) for x in g4flag]),
           "pinned": [[v, s, ms] for v, s, ms in PINNED], "union": sorted([list(x) for x in g4set]), "n_union": len(g4set)}, open(OUT + "/S1_G4_LIST.json", "w"), indent=1)
print("G4 flags", len(g4flag), "union", len(g4set), "t=%.0fs" % (time.time() - t0), flush=True)
# ---- grid, G1, G2 ----
N0, N1 = calendar.timegm((2021, 12, 1, 4, 0, 0)), calendar.timegm((2026, 8, 30, 20, 0, 0))
N = np.arange(N0, N1 + 1, 14400, dtype=np.int64); yrs = np.array([time.gmtime(int(t)).tm_year for t in N]); months = np.array([C.month_of(t) for t in N])
agg = collections.defaultdict(collections.Counter); g1 = collections.Counter()
IBTC = idx("BTCUSDT"); PBTC = perp("BTCUSDT")
for v in ("upbit", "bithumb"):
    KB = krw(v, "KRW-BTC"); KU = krw(v, "KRW-USDT"); ufirst = first_day[(v, "KRW-USDT")]
    for p in [q for q in PLAN["pairs"] if q["venue"] == v]:
        s, mk = p["symbol"], p["market"]; K = krw(v, mk); I = idx(s); Pp = perp(s)
        if I is None or Pp is None:
            agg[(v, "NO_INDEX_OR_PERP")]["pairs"] += 1; continue
        args = dict(v=v, N=N, months=months, krw=K, first_day=first_day[(v, mk)], idx=I, perp=Pp, g5days=G5.get((v, mk), set()), g4set=g4set, sym=s,
                    kbtc=KB, ibtc=IBTC, pbtc=PBTC, g5btc=G5.get((v, "KRW-BTC"), set()), kusdt=KU, g5usdt=G5.get((v, "KRW-USDT"), set()), mult=p["mult"])
        pA, pB, T24, X, dg = C.venue_leg(**args)
        _, _, _, _, dgl = C.venue_leg(**args, leaky=True)
        # G1
        vA, vB = dg["vA"], dg["vB"]
        g1[(v, "A_cells")] += int(vA.sum()); g1[(v, "A_viol")] += int((vA & ~(dg["o"] + 3600 <= N)).sum())
        g1[(v, "B_cells")] += int(vB.sum()); g1[(v, "B_viol")] += int((vB & ~((dg["o"] + 3600 <= N) & (dg["u"] + 3600 <= N))).sum())
        lk = dgl["has_bar"]; g1[(v, "leaky_cells")] += int(lk.sum()); g1[(v, "leaky_viol")] += int((lk & ~(dgl["o"] + 3600 <= N)).sum())
        # G2 cells
        win = (N >= first_day[(v, mk)] + 86400) & (N >= I["open_s"][0] + 14400) & (N <= I["open_s"][-1] + 3600) & (N >= Pp["open_s"][0] + 14400) & (N <= Pp["open_s"][-1] + 3600)
        excl = dg["g4bad"] | np.isin(C.day_keys(v, N - 3600), list(G5.get((v, mk), set())))
        cA = win & ~excl & (s != "BTCUSDT"); cB = win & ~excl & (N >= ufirst + 86400)
        for dfn, cells, valid in (("A", cA, vA), ("B", cB, vB)):
            for y in np.unique(yrs[cells]):
                cy = cells & (yrs == y); a = agg[(v, int(y), dfn)]
                a["cells"] += int(cy.sum()); a["valid"] += int((cy & valid).sum())
                a["NO_BAR"] += int((cy & ~dg["has_bar"]).sum()); a["NO_INDEX"] += int((cy & dg["has_bar"] & ~dg["idx_ok"]).sum())
                a["NO_PERP_TRADE"] += int((cy & dg["has_bar"] & dg["idx_ok"] & ~dg["perp_ok"]).sum())
                a["OTHER"] += int((cy & dg["has_bar"] & dg["idx_ok"] & dg["perp_ok"] & ~valid).sum())
        agg[(v, "excluded_cells")]["A"] += int((win & excl & (s != "BTCUSDT")).sum())
print("G1/G2 done t=%.0fs" % (time.time() - t0), flush=True)
g2rows = []
for k, a in sorted(agg.items(), key=lambda kv: str(kv[0])):
    if len(k) == 3:
        g2rows.append({"venue": k[0], "year": k[1], "def": k[2], **a, "hit_rate": round(a["valid"] / a["cells"], 6) if a["cells"] else None})
G2_PASS = all(r["hit_rate"] is not None and r["hit_rate"] >= 0.99 for r in g2rows)
G1_PASS = all(g1[(v, d + "_viol")] == 0 for v in ("upbit", "bithumb") for d in ("A", "B")) and all(g1[(v, "leaky_viol")] == g1[(v, "leaky_cells")] and g1[(v, "leaky_cells")] > 0 for v in ("upbit", "bithumb"))
# ---- G3 ----
def detrend(a):
    o = np.full_like(a, np.nan); fin = np.isfinite(a); cs = np.concatenate([[0.0], np.cumsum(np.where(fin, a, 0.0))]); cn = np.concatenate([[0], np.cumsum(fin)])
    for i in range(len(a)):
        lo, hi = max(0, i - 24), min(len(a), i + 25); nn = cn[hi] - cn[lo]
        if fin[i] and nn >= 24: o[i] = a[i] - (cs[hi] - cs[lo]) / nn
    return o
def spectrum(x, y):
    xd, yd = detrend(x), detrend(y); rho, disp = {}, {}
    for k in range(-12, 13):
        a, b = (xd[k:], yd[:len(yd) - k]) if k >= 0 else (xd[:len(xd) + k], yd[-k:])
        m = np.isfinite(a) & np.isfinite(b); rho[k] = float(np.corrcoef(a[m], b[m])[0, 1]) if m.sum() > 48 else float("nan")
        sdiff = (x[k:] - y[:len(y) - k]) if k >= 0 else (x[:len(x) + k] - y[-k:])
        med = np.array([np.nanmedian(sdiff[max(0, i - 24):i + 25]) if np.isfinite(sdiff[i]) else np.nan for i in range(len(sdiff))])
        disp[k] = float(np.nanstd(sdiff - med))
    am = max((k for k in rho if np.isfinite(rho[k])), key=lambda k: rho[k]); dm = min(disp, key=disp.get)
    return {"argmax_rho": am, "rho_m1": round(rho[-1], 5), "rho0": round(rho[0], 5), "rho_p1": round(rho[1], 5), "argmin_disp": dm}
g3 = []
BEND = calendar.timegm((2026, 9, 1, 0, 0, 0))
for v in ("upbit", "bithumb"):
    for mk, sym in (("KRW-BTC", "BTCUSDT"), ("KRW-ETH", "ETHUSDT"), ("KRW-XRP", "XRPUSDT")):
        if (v, mk) not in first_day: g3.append({"venue": v, "market": mk, "status": "NOT_MAPPED"}); continue
        K = krw(v, mk); I = idx(sym); kd = dict(zip(K["open_s"].tolist(), K["close"].tolist())); idd = dict(zip(I["open_s"].tolist(), I["close"].tolist()))
        for yr in range(2021, 2027):
            lo = max(PLAN["cutoff_epoch"], calendar.timegm((yr, 1, 1, 0, 0, 0))); hi = min(BEND, calendar.timegm((yr + 1, 1, 1, 0, 0, 0)))
            if hi - lo < 7 * 86400: continue
            hrs = np.arange(lo, hi, 3600); x = np.array([math.log(kd[t]) if t in kd else np.nan for t in hrs]); y = np.array([math.log(idd[t]) if t in idd else np.nan for t in hrs])
            sp = spectrum(x, y); nk = spectrum(np.concatenate([np.full(9, np.nan), x[:-9]]), y); nc = spectrum(np.concatenate([np.full(1, np.nan), x[:-1]]), y)
            ok = sp["argmax_rho"] == 0 and sp["rho0"] > max(sp["rho_m1"], sp["rho_p1"]) and sp["argmin_disp"] == 0
            red = nk["argmax_rho"] == 9 and nk["argmin_disp"] == 9 and nc["argmax_rho"] == 1 and nc["argmin_disp"] == 1
            g3.append({"venue": v, "market": mk, "year": yr, **sp, "neg_kst": [nk["argmax_rho"], nk["argmin_disp"]], "neg_close": [nc["argmax_rho"], nc["argmin_disp"]], "PASS": ok, "NEG_RED": red})
G3_PASS = all(c.get("PASS") and c.get("NEG_RED") for c in g3 if "PASS" in c) and not any(c.get("status") == "NOT_MAPPED" for c in g3)
out = {"device": os.path.basename(__file__), "device_sha256": DEVICE_SHA, "common_sha256": COMMON_SHA, "prereg_sha256": "62c6da526ac919304ef464389a0f5024015c37664a9721a11b70f33549f252ac",
       "run_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()), "grid": [int(N0), int(N1), int(len(N))],
       "G1": {"PASS": G1_PASS, "counts": {"%s %s" % k: v for k, v in g1.items()}}, "G2": {"PASS": G2_PASS, "rows": g2rows, "other": {"%s %s" % (k[0], k[1]): dict(a) for k, a in agg.items() if len(k) == 2}},
       "G3": {"PASS": G3_PASS, "cells": g3}, "G4": {"n_def_B_flags": len(g4flag), "n_union": len(g4set)}, "G5": {"n_days": len(g5_list)},
       "STOP": not (G1_PASS and G2_PASS and G3_PASS), "elapsed_s": round(time.time() - t0, 1)}
json.dump(out, open(OUT + "/S1_GUARDS.json", "w"), indent=1)
print(json.dumps({"G1": G1_PASS, "G2": G2_PASS, "G3": G3_PASS, "STOP": out["STOP"], "g1": out["G1"]["counts"]}, indent=1))
for r in g2rows: print("G2", r["venue"], r["year"], r["def"], r["cells"], r["hit_rate"], {k: r[k] for k in ("NO_BAR", "NO_INDEX", "NO_PERP_TRADE", "OTHER")})
for c in g3: print("G3", c)
sys.exit(2 if out["STOP"] else 0)
