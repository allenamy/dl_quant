"""Live shadow — item 3: paper P&L (dual-curve A/B, conservative maker fill).

Marks each emitted anchor's positions to the realized 4h forward return once it matures, under a
conservative maker-fill model (k=900 passive window, fill-rate 0.51, tick-corrected cost 1.9 bps calm
/ 2.9 bps stress by BTC realized vol), and accumulates a daily paper-P&L curve.

Dual curve (c2 ruling), always reported side by side:
  A = provisional 3-leg  — what THIS feed can actually trade for the open month (funding dropped).
  B = backfilled 4-leg   — what a real-time feed with live funding would get (open-month funding is a
                            premium proxy until the monthly archive backfills it).
Outputs exports/live/pnl/{pnl_daily.csv, pnl_summary.json}.
"""
import glob
import json
import os
import sys

import numpy as np
import pandas as pd

sys.path.insert(0, "/mnt/storage/private/work_hsy/quant_research_multi_asset/multi_asset")
from engine.signal_chain import _l1  # noqa (unused but keeps engine import path warm)

MA = "/mnt/storage/private/work_hsy/quant_research_multi_asset/multi_asset"
POS_DIR = MA + "/exports/live/positions"
OUT = MA + "/exports/live/pnl"
FILL = 0.51            # conservative maker fill-rate at k=900
COST_CALM, COST_STRESS = 1.9, 2.9      # bps/side, tick-corrected
RVOL_STRESS = 18.0     # BTC rvol bps/min threshold for the stress cost regime


def _src():
    from engine.panel_source import PanelSource
    return PanelSource(panel=MA + "/exports/live/wide_dl_live.npz",
                       king=MA + "/exports/live/king_pred_live.npz",
                       s2=MA + "/exports/live/s2_pred_live.npz")


def run(verbose=True):
    os.makedirs(OUT, exist_ok=True)
    src = _src()
    tj = {int(t): i for i, t in enumerate(src.ts)}
    sym2j = {s: j for j, s in enumerate(src.symbols)}
    files = sorted(glob.glob(POS_DIR + "/positions_*.json"))
    rows = {"A": [], "B": []}
    prev = {"A": np.zeros(src.N), "B": np.zeros(src.N)}
    for f in files:
        rec = json.load(open(f))
        ti = tj.get(int(rec["anchor_ts_ms"]))
        if ti is None:
            continue
        ret = src.Y4[ti]                                   # realized 4h forward return
        if not np.isfinite(ret).any():                     # not matured yet -> skip (will fill in later runs)
            continue
        rvol = src.btc_rvol_bps_min(ti)
        cost = COST_STRESS if (np.isfinite(rvol) and rvol > RVOL_STRESS) else COST_CALM
        d = pd.to_datetime(src.ts[ti], unit="ms", utc=True)
        for curve, key in (("A", "A_provisional_3leg"), ("B", "B_backfilled_4leg")):
            w = np.zeros(src.N)
            for s, wt in rec["curve"][key]["positions"].items():
                if s in sym2j:
                    w[sym2j[s]] = wt
            ok = np.isfinite(ret)
            gross = float(np.nansum(w[ok] * ret[ok]))
            turn = float(np.abs(w - prev[curve]).sum()); prev[curve] = w
            net = FILL * (gross - turn * cost * 1e-4)
            rows[curve].append({"day": d.strftime("%Y-%m-%d"), "anchor_utc": d.isoformat(),
                                "gross": gross, "turnover": turn, "cost_bps": cost,
                                "net_paper": net, "regime": "stress" if cost == COST_STRESS else "calm"})
    daily = {}
    summ = {"fill_rate": FILL, "cost_bps": {"calm": COST_CALM, "stress": COST_STRESS},
            "note": "structural-caliber paper P&L under a conservative maker-fill model; NOT a fund net return"}
    for curve in ("A", "B"):
        df = pd.DataFrame(rows[curve])
        if df.empty:
            summ[curve] = {"n_anchors": 0, "note": "no matured anchors yet"}
            continue
        dl = df.groupby("day").agg(net_paper=("net_paper", "sum"), gross=("gross", "sum"),
                                   turnover=("turnover", "sum")).reset_index()
        dl["cum_net_paper"] = dl["net_paper"].cumsum()
        daily[curve] = dl
        sh = float(dl["net_paper"].mean() / (dl["net_paper"].std() + 1e-12) * np.sqrt(365.0)) if len(dl) > 2 else np.nan
        summ[curve] = {"n_anchors": int(len(df)), "n_days": int(len(dl)),
                       "cum_net_paper": round(float(dl["cum_net_paper"].iloc[-1]), 6),
                       "daily_paper_sharpe": round(sh, 2) if np.isfinite(sh) else None,
                       "worst_day": round(float(dl["net_paper"].min()), 6),
                       "stress_anchor_frac": round(float((df["regime"] == "stress").mean()), 3)}
    # write side-by-side daily csv (A and B)
    if daily:
        out = None
        for curve in ("A", "B"):
            if curve in daily:
                dd = daily[curve][["day", "net_paper", "cum_net_paper"]].rename(
                    columns={"net_paper": f"net_paper_{curve}", "cum_net_paper": f"cum_{curve}"})
                out = dd if out is None else out.merge(dd, on="day", how="outer")
        out.sort_values("day").to_csv(OUT + "/pnl_daily.csv", index=False)
    json.dump(summ, open(OUT + "/pnl_summary.json", "w"), indent=1)
    if verbose:
        print(f"[pnl] A(3-leg): {summ['A']}  |  B(4-leg): {summ['B']}", flush=True)
        print(f"[pnl] -> {OUT}/pnl_daily.csv + pnl_summary.json", flush=True)
    return summ


if __name__ == "__main__":
    run()
