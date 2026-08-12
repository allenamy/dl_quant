"""Control for the funding-normalisation finding.

The +0.0061 IC gain must come from the UNIT NORMALISATION, not from my rebuild pipeline differing
from the shipped one. So rebuild the factor through the SAME code path but WITHOUT normalisation:
if that reproduces the shipped npz's IC, the delta is attributable to normalisation alone.

Three arms, identical everything except the rate transform:
  shipped     : FUND_EMA straight from wide_panel_full.npz
  rebuilt_raw : my pipeline, rate as-is            <- must match `shipped`
  rebuilt_norm: my pipeline, rate x 8/interval_h   <- the fix

Out: exports/eda/fundnorm_control.json
"""
import json, os, sys
import numpy as np
import pandas as pd

MA = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))   # .../multi_asset
MA = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))   # .../multi_asset
REPO = os.path.dirname(MA)
sys.path.insert(0, MA)
from engine.panel_source import PanelSource
from engine.signal_chain import _rank_centered
from engine.ic_monitor import xsec_rank_ic

WIDE = REPO + "/data/wide"


def build(ts, syms, normalise):
    T, N = len(ts), len(syms)
    F = np.full((T, N), np.nan)
    for j, s in enumerate(syms):
        p = f"{WIDE}/{s}_funding.csv"
        if not os.path.exists(p):
            continue
        d = pd.read_csv(p)
        if "funding_interval_h" not in d or len(d) < 10:
            continue
        d = d.sort_values("fundingTime_ms")
        iv = pd.to_numeric(d["funding_interval_h"], errors="coerce").to_numpy()
        rate = pd.to_numeric(d["fundingRate"], errors="coerce").to_numpy()
        iv = np.where(np.isfinite(iv) & (iv > 0), iv, 8.0)
        r = rate * (8.0 / iv) if normalise else rate
        span = max(2, int(round(24.0 / max(float(np.median(iv)), 1.0))))
        ema = pd.Series(r).ewm(span=span, adjust=False).mean().to_numpy()
        fts = d["fundingTime_ms"].to_numpy().astype(np.int64)
        idx = np.searchsorted(fts, ts, side="right") - 1
        ok = idx >= 0
        F[ok, j] = ema[idx[ok]]
    return F


def main():
    src = PanelSource()
    ts, syms = src.ts, src.symbols
    W = np.load(MA + "/exports/wide_panel_full.npz", allow_pickle=True)
    arms = {"shipped": W["FUND_EMA"].astype(np.float64),
            "rebuilt_raw": build(ts, syms, False),
            "rebuilt_norm": build(ts, syms, True)}
    months = [f"{y}-{m:02d}" for y in range(2022, 2027) for m in range(1, 13)
              if not (y == 2026 and m > 6)]
    a = np.unique(np.concatenate([src.month_anchors(ym) for ym in months]))

    # agreement between shipped and rebuilt_raw (should be ~1.0 where both finite)
    both = np.isfinite(arms["shipped"]) & np.isfinite(arms["rebuilt_raw"])
    corr = float(np.corrcoef(arms["shipped"][both], arms["rebuilt_raw"][both])[0, 1])
    mad = float(np.abs(arms["shipped"][both] - arms["rebuilt_raw"][both]).mean())

    ics = {k: [] for k in arms}
    for t in a:
        fin = np.ones(len(syms), bool)
        for k in arms:
            fin &= np.isfinite(arms[k][t])
        m = np.where(src.member[t] & fin & np.isfinite(src.Y4[t]))[0]
        if len(m) < 20:
            continue
        y = src.Y4[t, m]
        for k in arms:
            ics[k].append(xsec_rank_ic(-_rank_centered(arms[k][t, m]), y))

    def st(v):
        v = np.array([x for x in v if np.isfinite(x)])
        return {"mean_rank_ic": round(float(v.mean()), 5),
                "t_stat": round(float(v.mean() / (v.std() + 1e-12) * np.sqrt(len(v))), 2),
                "n": int(len(v))}
    out = {"agreement_shipped_vs_rebuilt_raw": {"pearson": round(corr, 6),
                                                "mean_abs_diff": mad,
                                                "n_cells": int(both.sum())},
           "arms": {k: st(v) for k, v in ics.items()}}
    dn = np.array(ics["rebuilt_norm"], float) - np.array(ics["rebuilt_raw"], float)
    dn = dn[np.isfinite(dn)]
    out["paired_norm_minus_raw"] = {
        "mean": round(float(dn.mean()), 6),
        "t_stat": round(float(dn.mean() / (dn.std() + 1e-12) * np.sqrt(len(dn))), 2)}
    print(f"[control] shipped vs rebuilt_raw: corr {corr:.6f}, mean|diff| {mad:.3e}", flush=True)
    for k, v in out["arms"].items():
        print(f"  {k:13s} IC {v['mean_rank_ic']:+.5f}  t {v['t_stat']:+.2f}  n {v['n']}", flush=True)
    print(f"[control] paired norm-minus-raw: {out['paired_norm_minus_raw']['mean']:+.6f} "
          f"t={out['paired_norm_minus_raw']['t_stat']:+.2f}", flush=True)
    json.dump(out, open(MA + "/exports/eda/fundnorm_control.json", "w"), indent=1)
    print("-> fundnorm_control.json")


if __name__ == "__main__":
    main()
