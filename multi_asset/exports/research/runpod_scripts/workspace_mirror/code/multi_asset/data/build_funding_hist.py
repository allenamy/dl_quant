#!/usr/bin/env python3
"""Full-history funding_ema cache (2022+) for the M0 walk-forward RETRAINING replay's residual target.

> **created:** 2026-07-09 | **Session:** multi-asset-v2 M0-fullhist (0B) | **状态:** in-progress

The trainer's load_funding reads funding_factor_cache/<bnf-sym>.npz {ts, X[:,funding_ema], factor_names}
and ffills≤t to the panel grid. The current cache is 2024-2025; the full-history retraining needs
funding_ema back to 2022. Builds it from the megacap_hist funding CSVs (24h-equiv EMA of the 8h rate,
per coin) at the settlement grid (ns) — load_funding ffills from there. Output: funding_ema_hist/<bnf>.npz.
Usage: PYTHONPATH=. python multi_asset/data/build_funding_hist.py
"""
from __future__ import annotations
import os, os.path as p
import numpy as np, pandas as pd

HIST = "/mnt/storage/private/work_hsy/quant_research_multi_asset/data/megacap_hist"
OUT = "/mnt/storage/private/work_hsy/quant_research_multi_asset/multi_asset/exports/funding_ema_hist"
PANEL = {"bnfbtc": "BTCUSDT", "bnfeth": "ETHUSDT", "bnfsol": "SOLUSDT", "bnfbnb": "BNBUSDT",
         "bnfxrp": "XRPUSDT", "bnfdog": "DOGEUSDT", "bnfada": "ADAUSDT", "bnflink": "LINKUSDT",
         "bnfbch": "BCHUSDT", "bnftrx": "TRXUSDT", "bnfltc": "LTCUSDT", "bnfdot": "DOTUSDT",
         "bnffil": "FILUSDT", "bnfetc": "ETCUSDT"}


def main():
    os.makedirs(OUT, exist_ok=True)
    for bnf, SYM in PANEL.items():
        ff = p.join(HIST, f"{SYM}_funding.csv")
        if not p.exists(ff):
            print(f"  [warn] {SYM}: no funding csv"); continue
        fd = pd.read_csv(ff).sort_values("fundingTime_ms")
        ih = float(np.median(fd["funding_interval_h"].values)) if len(fd) else 8.0
        span = max(2, int(round(24.0 / max(ih, 1.0))))
        rate = pd.to_numeric(fd["fundingRate"], errors="coerce").values.astype(np.float64)
        ema = pd.Series(rate).ewm(span=span, adjust=False).mean().values
        ts_ns = fd["fundingTime_ms"].values.astype(np.int64) * 1_000_000   # ms -> ns (panel ts is ns)
        X = ema.reshape(-1, 1).astype(np.float32)
        np.savez(p.join(OUT, f"{bnf}.npz"), ts=ts_ns, X=X,
                 factor_names=np.array(["funding_ema"], dtype=object))
        print(f"  {bnf} ({SYM}): {len(ts_ns)} settlements, span={span}, "
              f"{pd.to_datetime(ts_ns[0], unit='ns').date()}→{pd.to_datetime(ts_ns[-1], unit='ns').date()}", flush=True)
    print(f"[funding_hist] -> {OUT}", flush=True)


if __name__ == "__main__":
    main()
