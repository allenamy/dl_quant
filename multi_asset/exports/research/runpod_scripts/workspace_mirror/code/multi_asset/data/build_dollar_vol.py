"""Precompute per-asset dollar-volume cap weights for the Phase-1 market token.

The cross-asset panel cache stores only standardized/relative features (no raw
size LEVEL), so the market token's cap-weighted pool needs a separate, FIXED
per-asset dollar-volume vector. We read the raw 1s bars for a sample of days in
the *training* window and take, per asset, the median of the per-day total taker
notional (tdQtyPxBuy + tdQtyPxSell summed over the day).

These weights are TRAIN-FIXED and asset-level constants: they are computed once
(over an early-window day sample that sits inside every fold's train span) and
never recomputed on test. The trainer renormalizes them over the assets present
in a given fold's train block — that is just a restriction of a fixed vector, so
the train-fixed property holds (no test-time leakage).

Output (server-local, next to the panel cache):
    <CACHE_DIR>/dollar_vol.npz  with arrays:
        sym       (S,)  object  symbol order (matches panel SYMBOLS)
        dvol_med  (S,)  float64 per-asset median daily total taker notional
        log_dvol  (S,)  float64 log1p(dvol_med) (the model-side scale)
        days_used (k,)  int32   sampled day list

Read-only over the share. Idempotent: re-run overwrites.
"""
from __future__ import annotations

import json
import os
import os.path as p
import sys

import numpy as np

sys.path.insert(0, p.dirname(p.dirname(p.dirname(p.abspath(__file__)))))
from multi_asset.data.bar_loader import load_day_panel  # noqa: E402
from multi_asset.data.features_ma import _col  # noqa: E402
from multi_asset.data.build_feature_cache import SYMBOLS, list_days, WIN_START, WIN_END  # noqa: E402

CACHE_DIR = ("/mnt/storage/private/work_hsy/quant_research_multi_asset/"
             "multi_asset/exports/panel_cache")

# Sample N days from the EARLY part of the window so the estimate sits inside
# every fold's train span (fold train spans start at day-idx 0/80/160; sampling
# the first ~200 days keeps the weights train-fixed for all three folds).
N_SAMPLE_DAYS = 40
EARLY_FRACTION = 0.45     # sample within the first 45% of the window's days


def build():
    days = list_days(WIN_START, WIN_END)
    n_early = max(N_SAMPLE_DAYS, int(len(days) * EARLY_FRACTION))
    early = days[:n_early]
    # evenly spaced sample across the early span
    idx = np.linspace(0, len(early) - 1, N_SAMPLE_DAYS).round().astype(int)
    sample_days = sorted(set(early[i] for i in idx))
    print(f"[dvol] window {WIN_START}..{WIN_END}: {len(days)} days, "
          f"sampling {len(sample_days)} early days for cap weights", flush=True)

    # per-asset list of per-day total taker notional
    per_day_notional = {s: [] for s in SYMBOLS}
    n_fail = 0
    for d in sample_days:
        try:
            dp = load_day_panel(d, SYMBOLS)
        except Exception as e:
            n_fail += 1
            print(f"  [warn] day {d} load failed: {e}", flush=True)
            continue
        for s in SYMBOLS:
            buy = _col(dp, s, "tdQtyPxBuy")
            sell = _col(dp, s, "tdQtyPxSell")
            tot = np.asarray(buy, dtype=np.float64) + np.asarray(sell, dtype=np.float64)
            tot = tot[np.isfinite(tot)]
            if tot.size:
                per_day_notional[s].append(float(tot.sum()))
        print(f"  day {d}: ok", flush=True)

    dvol_med = np.zeros(len(SYMBOLS), np.float64)
    for si, s in enumerate(SYMBOLS):
        vals = np.array(per_day_notional[s], dtype=np.float64)
        dvol_med[si] = float(np.median(vals)) if vals.size else 0.0
    log_dvol = np.log1p(dvol_med)

    os.makedirs(CACHE_DIR, exist_ok=True)
    out = p.join(CACHE_DIR, "dollar_vol.npz")
    np.savez(out,
             sym=np.array(SYMBOLS, dtype=object),
             dvol_med=dvol_med,
             log_dvol=log_dvol,
             days_used=np.array(sample_days, dtype=np.int32))
    # human-readable companion
    summary = {s: {"dvol_med": dvol_med[i], "log_dvol": round(log_dvol[i], 3)}
               for i, s in enumerate(SYMBOLS)}
    with open(p.join(CACHE_DIR, "dollar_vol.json"), "w") as f:
        json.dump({"days_used": [int(x) for x in sample_days],
                   "n_fail": n_fail, "per_asset": summary}, f, indent=2)

    print(f"\n[dvol] per-asset median daily taker notional (cap-weight basis):", flush=True)
    order = np.argsort(-dvol_med)
    for si in order:
        print(f"  {SYMBOLS[si]:10s} dvol_med={dvol_med[si]:.3e}  log={log_dvol[si]:.3f}", flush=True)
    print(f"\nsaved -> {out}", flush=True)


if __name__ == "__main__":
    build()
