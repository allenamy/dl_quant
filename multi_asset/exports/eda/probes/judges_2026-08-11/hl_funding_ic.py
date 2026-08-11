"""(3c, addendum) Is HL funding as PREDICTIVE as Binance funding?

The rank correlation (0.47) says the two are different signals; it does not say which one works.
Over the shared 60d window, compare the crowding-reversion leg built from each source, on the
SAME names and SAME anchors, by rank-IC vs realized 4h return (IC is far better powered than a
60-day Sharpe, which would be noise).

Also reports the blend, since two 0.47-correlated versions of the same economic idea may add.

Out: exports/eda/hl_funding_ic.json
"""
import json, sys
import numpy as np
import pandas as pd

MA = "/mnt/storage/private/work_hsy/quant_research_multi_asset/multi_asset"
sys.path.insert(0, MA)
from engine.panel_source import PanelSource
from engine.signal_chain import _rank_centered
from engine.ic_monitor import xsec_rank_ic


def main():
    H = np.load(MA + "/exports/eda/hl_hist.npz", allow_pickle=True)
    src = PanelSource()
    W = np.load(MA + "/exports/wide_panel_full.npz", allow_pickle=True)
    FE = W["FUND_EMA"].astype(np.float64)
    ts = src.ts; syms = src.symbols
    T, N = FE.shape

    def hl2b(n):
        return ("1000" + n[1:] + "USDT") if n.startswith("k") else (n + "USDT")

    HF = np.full((T, N), np.nan)
    for c, arr in zip(H["fcoins"], H["funding"]):
        s = hl2b(str(c))
        if s not in syms:
            continue
        j = syms.index(s)
        a = arr[np.argsort(arr[:, 0])]
        ema = pd.Series(a[:, 1]).ewm(span=24, adjust=False).mean().values
        idx = np.searchsorted(a[:, 0], ts, side="right") - 1
        ok = idx >= 0
        HF[ok, j] = ema[idx[ok]]
        HF[ts < a[0, 0], j] = np.nan

    anchors = [t for t in np.where(src.CL4.any(1))[0]
               if np.isfinite(HF[t]).sum() >= 20 and src.member[t].any()]
    ics = {"binance": [], "hl": [], "blend": []}
    for t in anchors:
        m = np.where(src.member[t] & np.isfinite(HF[t]) & np.isfinite(FE[t])
                     & np.isfinite(src.Y4[t]))[0]
        if len(m) < 20:
            continue
        y = src.Y4[t, m]
        sb = -_rank_centered(FE[t, m])          # crowding-reversion sign, as the engine does
        sh = -_rank_centered(HF[t, m])
        ics["binance"].append(xsec_rank_ic(sb, y))
        ics["hl"].append(xsec_rank_ic(sh, y))
        ics["blend"].append(xsec_rank_ic(0.5 * sb + 0.5 * sh, y))

    out = {"window": "60d ending at panel end (2026-06-30)",
           "n_anchors": len(ics["binance"]),
           "caveat": ("60-day window: IC means are usable, but a t-stat this short cannot settle "
                      "whether either source is a live alpha -- it settles the COMPARISON."),
           "by_source": {}}
    for k, v in ics.items():
        a = np.array([x for x in v if np.isfinite(x)])
        out["by_source"][k] = {"mean_rank_ic": round(float(a.mean()), 5),
                               "ic_ir": round(float(a.mean() / (a.std() + 1e-12)), 4),
                               "t_stat": round(float(a.mean() / (a.std() + 1e-12)
                                                     * np.sqrt(len(a))), 2),
                               "n": int(len(a))}
        print(f"  {k:8s}: mean rank-IC {a.mean():+.5f}  IC-IR {a.mean()/(a.std()+1e-12):+.4f}  "
              f"t {a.mean()/(a.std()+1e-12)*np.sqrt(len(a)):+.2f}  (n={len(a)})", flush=True)
    json.dump(out, open(MA + "/exports/eda/hl_funding_ic.json", "w"), indent=1)
    print("-> hl_funding_ic.json")


if __name__ == "__main__":
    main()
