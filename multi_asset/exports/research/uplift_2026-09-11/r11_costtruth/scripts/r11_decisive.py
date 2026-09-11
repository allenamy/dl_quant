#!/usr/bin/env python3
"""r11 STEP 4 — THE DECISIVE READING: does the adverse markout REVERT by +4h, or PERSIST?

The level at +4h is a badly-powered statistic (4h price variance swamps the impact). The PAIRED
difference markout(D) - markout(60s) on the SAME fills is the right test and is far tighter:
    REVERSION  predicts  D - 60s  ->  +3.2 bps (the 60s adverse move is handed back)
    PERSISTENCE predicts D - 60s  ->   0 bps   (the move stays)
    CONTINUATION predicts D - 60s <    0 bps

Also runs the critic's confound test (is this just the book's directional view?) at EVERY lag.

UTC-day block bootstrap, 2000 resamples, numpy.default_rng([20260905,k]).
ENV WHITELIST: {} (empty) — asserted (E-0826-D).
"""
import json, os, hashlib, datetime as dt
import numpy as np
from collections import defaultdict

_FORBID = ("CAL","JUDGE","PANEL","EXPORT_PANEL","EMA_STATE_JSON","W10_","POD_","DLW_","KING_","SEAT_","UMASK")
_h = sorted(k for k in os.environ if any(k.startswith(p) for p in _FORBID))
assert not _h, f"ENV WHITELIST VIOLATION: {_h}"

OUT = "/Users/haosiyu/Desktop/quant_research/multi_asset/exports/research/uplift_2026-09-11/r11_costtruth/out"
LAGS = ["60", "300", "900", "3600", "14400"]
LAGLBL = {"60": "+60s", "300": "+5m", "900": "+15m", "3600": "+1h", "14400": "+4h"}
LAGSEC = {"60": 60, "300": 300, "900": 900, "3600": 3600, "14400": 14400}
NBOOT, SEED = 2000, 20260905
A0_G = 0.6342          # A0 mean g, bps per 4h anchor per unit gross (pinned planning number)

inp = json.load(open(f"{OUT}/r11_fills_input.json")); rows = {str(r["trade_id"]): r for r in inp["rows"]}
marks = json.load(open(f"{OUT}/full/marks_multilag.json"))

recs = []
for tid, lr in marks.items():
    r = rows.get(tid)
    if r is None or r["fill_px"] <= 0: continue
    mo = {}
    okall = True
    for L in LAGS:
        rc = lr.get(L)
        if rc and rc["status"] == "ok":
            mo[L] = r["sign"] * (float(rc["mark_px"]) - r["fill_px"]) / r["fill_px"] * 1e4
        else:
            mo[L] = np.nan; okall = False
    if not okall: continue
    recs.append(dict(day=dt.datetime.fromtimestamp(r["fill_ts"], tz=dt.timezone.utc).strftime("%Y-%m-%d"),
                     nz=r["notional"], ot=r["order_type"], **{f"mo{L}": mo[L] for L in LAGS}))
print(f"balanced panel n={len(recs)}  notional=${sum(x['nz'] for x in recs):,.0f}\n")

def boot(sub, fn, k):
    """day-block bootstrap of a notional-weighted linear statistic given per-fill values fn(x)."""
    byday = defaultdict(lambda: [0.0, 0.0])
    for x in sub:
        v = fn(x)
        if np.isfinite(v):
            byday[x["day"]][0] += x["nz"] * v; byday[x["day"]][1] += x["nz"]
    days = sorted(byday)
    V = np.array([byday[d][0] for d in days]); W = np.array([byday[d][1] for d in days])
    pt = V.sum() / W.sum()
    if len(days) < 2: return pt, np.nan, np.nan, len(days)
    rng = np.random.default_rng([SEED, k])
    idx = rng.integers(0, len(days), size=(NBOOT, len(days)))
    b = V[idx].sum(1) / W[idx].sum(1)
    return pt, float(np.percentile(b, 2.5)), float(np.percentile(b, 97.5)), len(days)

print("=" * 92)
print("THE DECISIVE TEST — PAIRED difference  markout(D) - markout(+60s), same fills")
print("  REVERSION would give  ~ +3.20 bps   |   PERSISTENCE gives ~ 0   |   CONTINUATION gives < 0")
print("=" * 92)
print(f"  {'lag D':>7} {'paired D-60s':>14} {'95% CI (day-block)':>28}   reading")
DEC = {}
for i, L in enumerate(LAGS[1:], 1):
    pt, lo, hi, nd = boot(recs, lambda x, L=L: x[f"mo{L}"] - x["mo60"], 400 + i)
    rd = "REVERTS" if lo > 0 else ("CONTINUES (worse)" if hi < 0 else "no reversion detected")
    print(f"  {LAGLBL[L]:>7} {pt:>+14.4f}   [{lo:>+8.4f}, {hi:>+8.4f}]   {rd}")
    DEC[L] = dict(paired_diff=pt, lo=lo, hi=hi, days=nd)
print()
full_rev = 3.2026
pt4, lo4, hi4, _ = boot(recs, lambda x: x["mo14400"] - x["mo60"], 499)
print(f"  Full reversion by +4h would require the paired difference to be +{full_rev:.4f} bps.")
print(f"  Measured: {pt4:+.4f} [{lo4:+.4f}, {hi4:+.4f}]  ->  full reversion is "
      f"{'EXCLUDED' if hi4 < full_rev else 'NOT excluded'} at 95%.")
print()

print("=" * 92)
print("CONFOUND TEST at every lag — is the markout just the book's own directional view?")
print("  A0 expected alpha over D = 0.6342 bps/anchor x (D / 14400 s), per unit position.")
print("=" * 92)
print(f"  {'lag':>7} {'|markout| bps':>14} {'book alpha bps':>16} {'ratio':>9}")
CONF = {}
for L in LAGS:
    pt, lo, hi, _ = boot(recs, lambda x, L=L: x[f"mo{L}"], 500 + LAGSEC[L])
    alpha = A0_G * LAGSEC[L] / 14400.0
    print(f"  {LAGLBL[L]:>7} {abs(pt):>14.4f} {alpha:>16.5f} {abs(pt)/alpha:>8.1f}x")
    CONF[L] = dict(markout=pt, lo=lo, hi=hi, book_alpha=alpha, ratio=abs(pt) / alpha)
print()

print("=" * 92)
print("protective_flatten (2026-09-09 watchdog trip) — ONE UTC day, so NO day-block CI is possible")
print("=" * 92)
pf = [x for x in recs if x["ot"] == "protective_flatten"]
print(f"  n={len(pf)}  notional=${sum(x['nz'] for x in pf):,.0f}   (point estimates only)")
PF = {}
for L in LAGS:
    w = np.array([x["nz"] for x in pf]); v = np.array([x[f"mo{L}"] for x in pf])
    m = float((v * w).sum() / w.sum())
    print(f"    {LAGLBL[L]:>6} {m:>+10.4f} bps")
    PF[L] = m
print()

# steady-state adverse cost = the plateau the curve settles on, 5m..4h, notional-weighted across lags
plat = [CONF[L]["markout"] for L in ["300", "900", "3600", "14400"]]
print("=" * 92)
print("STEADY-STATE ADVERSE SELECTION (the number that should enter a cost model)")
print("=" * 92)
print(f"  plateau across +5m/+15m/+1h/+4h : mean {np.mean(plat):+.4f} bps   (min {min(plat):+.4f}, max {max(plat):+.4f})")
print(f"  recorded 60s value the desk used: {CONF['60']['markout']:+.4f} bps")
print(f"  UNDERSTATEMENT of the 60s proxy : {abs(np.mean(plat))/abs(CONF['60']['markout']):.3f} x")
json.dump(dict(paired=DEC, confound=CONF, protective_flatten=PF,
               plateau_mean=float(np.mean(plat)), n=len(recs)),
          open(f"{OUT}/r11_decisive.json", "w"), indent=1, default=float)
print(f"\nwrote {OUT}/r11_decisive.json")
