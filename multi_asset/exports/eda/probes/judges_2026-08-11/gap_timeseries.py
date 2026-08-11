"""Monthly funding-dimension gap on both live panels (server, /tmp only).

The band 0C specified (-0.45..-0.30 as-trained, +0.05..+0.25 normfix) is a FULL-HISTORY mean. A
live panel is ~37-45 days. If the gap is time-varying, a full-history band cannot gate a live
window. This measures the gap in 30-day blocks so the band can be re-derived on the right scale.
"""
import json
import sys

import numpy as np
import pandas as pd
from scipy.stats import rankdata

REPO = "/mnt/storage/private/work_hsy/quant_research_multi_asset"
MA = REPO + "/multi_asset"
WIDE = REPO + "/data/wide"


def rank_centred(x):
    r = rankdata(x); k = len(r)
    return 2.0 * (r - 1) / (k - 1) - 1.0 if k > 1 else np.zeros_like(x)


def ih_grid(ts, symbols):
    IH = np.full((len(ts), len(symbols)), np.nan)
    for j, s in enumerate(symbols):
        try:
            d = pd.read_csv(f"{WIDE}/{s}_funding.csv").sort_values("fundingTime_ms")
        except Exception:
            continue
        iv = pd.to_numeric(d["funding_interval_h"], errors="coerce").to_numpy()
        fts = d["fundingTime_ms"].to_numpy().astype(np.int64)
        ok = np.isfinite(iv) & (iv > 0)
        if ok.sum() < 3:
            continue
        idx = np.searchsorted(fts[ok], ts, side="right") - 1
        g = idx >= 0
        IH[g, j] = iv[ok][idx[g]]
    return IH


out = {}
for name, path in (("as_trained", MA + "/exports/live/wide_dl_live.npz"),
                   ("normfix", MA + "/exports/live/wide_dl_live_fundfix.npz")):
    z = np.load(path, allow_pickle=True)
    ts = z["ts"].astype(np.int64); syms = [str(s) for s in z["symbols"]]
    ch = [str(c) for c in z["ch_names"]]; mem = z["MEMBER110"]
    IH = ih_grid(ts, syms)
    X = z["CH"][:, :, ch.index("funding_ema")].astype(np.float64)
    cal = pd.to_datetime(ts, unit="ms", utc=True)
    ym = (cal.year * 100 + cal.month).to_numpy()
    series = {}
    for m in np.unique(ym):
        rr = np.where(ym == m)[0]
        acc = []
        for t in rr[::4]:
            if not mem[t].any():
                continue
            v = np.where(mem[t] & np.isfinite(IH[t]))[0]
            if v.size < 20:
                continue
            is4 = IH[t, v] <= 4.0
            x = X[t, v]; f = np.isfinite(x)
            if (f & is4).sum() < 3 or (f & ~is4).sum() < 3:
                continue
            zc = np.full(len(x), np.nan); zc[f] = rank_centred(x[f])
            acc.append(float(np.nanmean(zc[is4]) - np.nanmean(zc[~is4])))
        if acc:
            series[int(m)] = dict(gap=round(float(np.mean(acc)), 4), n=len(acc),
                                  n4=int((mem[rr[0]] & (IH[rr[0]] <= 4)).sum()))
    out[name] = series
    print(f"[{name}] " + " ".join(f"{m}:{v['gap']:+.3f}" for m, v in sorted(series.items())),
          flush=True)
    del z, X

with open("/tmp/funding_gap_monthly.json", "w") as f:
    json.dump(out, f, indent=1)
print("[done] /tmp/funding_gap_monthly.json", flush=True)
