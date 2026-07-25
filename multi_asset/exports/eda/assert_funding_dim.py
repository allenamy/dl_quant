"""0C — REGRESSION ASSERTION for the funding settlement-interval dimension bug. RUN AT EVERY PANEL REBUILD.

> created 2026-07-25 | Session: 0C | 状态: permanent guard | 作废条件: 从不 (面板重建流程的常驻检查)

WHY THIS EXISTS
---------------
`FUND_EMA` / `funding_ema` stored the EMA of the PER-SETTLEMENT-PERIOD funding rate, while 4h-settled
and 8h-settled coins coexist in the panel. A 4h coin with identical annualised carry shows HALF the
per-period rate. Cross-sectional rank-centring -- which the engine's funding leg uses -- removes
INDIVIDUAL scale but NOT a GROUP-level location shift, so the 4h cohort was pushed systematically to
one side (measured: -0.3745 rank units on a [-1,1] scale, ~19% of full range).

TWO CHANNELS CARRY IT, NOT ONE
------------------------------
  ch  0  funding_ema   -- the raw factor
  ch 28  xsr_fund      -- centered pct-rank OF funding_ema (build_wide_dl.py L80-91)
A rank transform is EXACTLY the operation that preserves a group shift, so xsr_fund carries the same
artifact in a purer form. xsr_fund is derived from funding_ema in the same script, so fixing the
source fixes both -- but that is an assumption about the build graph, and assumptions rot. This
script VERIFIES it instead of trusting it.

WHAT IT CHECKS
--------------
For each channel, per anchor, over the member cross-section:
    gap = mean(rank_centred(x) | 4h-settled) - mean(rank_centred(x) | 8h-settled)
A correctly-dimensioned factor has |mean gap| small. The control is gap(Y4): the 4h cohort genuinely
underperforms (measured -0.033), so a SMALL residual gap is expected and legitimate -- the fail
threshold is set well above it and well below the broken value.

  PASS  |mean gap| <= 0.20 for BOTH channels
  FAIL  otherwise   (broken shipped value was -0.3745; corrected value +0.1463)

Usage:  python multi_asset/exports/eda/assert_funding_dim.py [--panel <wide_dl_full.npz>]
Exit code 0 = pass, 1 = fail (wire into the panel-rebuild pipeline so a regression breaks the build).
"""
import os
import sys, json, argparse
import numpy as np, pandas as pd
from scipy.stats import rankdata

MA = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))   # .../multi_asset
EDA = MA + "/exports/eda/"
WIDE = os.path.join(os.path.dirname(MA), "data", "wide")
FAIL_ABS = 0.20            # broken = 0.3745, corrected = 0.1463, legitimate return-driven gap = 0.033
CHANNELS = ["funding_ema", "xsr_fund"]


def rank_centred(x):
    r = rankdata(x); k = len(r)
    return 2.0 * (r - 1) / (k - 1) - 1.0 if k > 1 else np.zeros_like(x)


def main(panel):
    W = np.load(panel, allow_pickle=True)
    ts = W["ts"].astype(np.int64); symbols = [str(s) for s in W["symbols"]]
    ch = [str(c) for c in W["ch_names"]]; CH = W["CH"]; mem = W["MEMBER110"]
    Y4 = W["Y4"].astype(np.float64)
    T, N = mem.shape

    # settlement interval in force, from the raw archive
    IH = np.full((T, N), np.nan)
    for j, s in enumerate(symbols):
        try:
            d = pd.read_csv(f"{WIDE}/{s}_funding.csv").sort_values("fundingTime_ms")
        except FileNotFoundError:
            continue
        iv = pd.to_numeric(d["funding_interval_h"], errors="coerce").to_numpy()
        fts = d["fundingTime_ms"].to_numpy().astype(np.int64)
        ok = np.isfinite(iv) & (iv > 0)
        if ok.sum() < 3:
            continue
        idx = np.searchsorted(fts[ok], ts, side="right") - 1
        g = idx >= 0
        IH[g, j] = iv[ok][idx[g]]

    missing = [c for c in CHANNELS if c not in ch]
    if missing:
        print(f"FAIL: channels not present in panel: {missing}", flush=True)
        return 1

    acc = {c: [] for c in CHANNELS}; acc["Y4"] = []
    rows = np.where(mem.any(1))[0]
    for t in rows[::4]:
        v = np.where(mem[t] & np.isfinite(IH[t]))[0]
        if v.size < 20:
            continue
        is4 = IH[t, v] <= 4.0
        if is4.sum() < 3 or (~is4).sum() < 3:
            continue
        for c in CHANNELS + ["Y4"]:
            x = Y4[t, v] if c == "Y4" else CH[t, v, ch.index(c)].astype(np.float64)
            f = np.isfinite(x)
            if (f & is4).sum() < 3 or (f & ~is4).sum() < 3:
                continue
            z = np.full(len(x), np.nan); z[f] = rank_centred(x[f])
            acc[c].append(float(np.nanmean(z[is4]) - np.nanmean(z[~is4])))

    print(f"panel: {panel}\nanchors sampled: {len(acc['Y4'])}\n", flush=True)
    res = {}; failed = []
    for c in CHANNELS + ["Y4"]:
        a = np.array(acc[c], float); a = a[np.isfinite(a)]
        if a.size == 0:
            print(f"  {c:14s}  NO DATA -> FAIL"); failed.append(c); continue
        mg = float(a.mean())
        res[c] = dict(mean_gap=round(mg, 4), n=int(a.size))
        if c == "Y4":
            print(f"  {c:14s}  mean gap {mg:+.4f}   (CONTROL: real 4h-cohort return gap, "
                  f"a small factor gap of this order is legitimate)", flush=True)
        else:
            ok = abs(mg) <= FAIL_ABS
            print(f"  {c:14s}  mean gap {mg:+.4f}   {'PASS' if ok else 'FAIL'} "
                  f"(|gap| <= {FAIL_ABS}; broken -0.3745 / corrected +0.1463)", flush=True)
            if not ok:
                failed.append(c)

    verdict = "PASS" if not failed else f"FAIL: {failed}"
    print(f"\nVERDICT: {verdict}", flush=True)
    if failed:
        print("\n  The funding dimension bug (or a regression of it) is present. Fix: normalise each\n"
              "  settlement rate to an 8h equivalent BEFORE the EMA:  rate * (8 / interval_h_of_that_row).\n"
              "  Applying it after the EMA is wrong for the ~29 coins that migrated 8h<->4h mid-history.\n"
              "  Reference implementation: exports/eda/funding_dim_fix.py", flush=True)
    json.dump(dict(panel=panel, created="2026-07-25", auditor="0C", fail_threshold=FAIL_ABS,
                   channels=res, verdict=verdict),
              open(EDA + "assert_funding_dim_result.json", "w"), indent=1, default=str)
    return 0 if not failed else 1


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--panel", default=MA + "/exports/wide_dl_full.npz")
    sys.exit(main(ap.parse_args().panel))
