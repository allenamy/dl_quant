#!/usr/bin/env python3
"""Reconstruct the frozen models' TRAINING MEMBER110 union, locally, from fapi daily klines.

> **created:** 2026-07-29 UTC | **Session:** ma-v2 universe_guard pin | **状态:** final
> **作废条件:** 若 funding_span_table.json 的 140 列集合变更, 或冻结模型换代(重训) 则重算

★ WHAT THIS SCRIPT IS FOR, AND WHY IT IS *NOT* THE PRIMARY EVIDENCE.
`live/universe_guard.py` needs `checkpoints/MANIFEST.json :: training_member_union`. Its docstring
says the union "must be computed WHERE THE PANEL LIVES ... it cannot be reconstructed from the
checkpoints". That is true of the CHECKPOINTS -- and it turned out not to be true of the REPO:
`state/fixtures/*.npz` carry real slices of the server training panel, including its symbol axis
and its actual MEMBER110 masks. Those fixtures determine the union EXACTLY (see step A below).
This reconstruction is therefore a CORROBORATING second source, not the basis of the answer. Where
the two disagree, the artifacts win: a rule replayed on re-fetched data is weaker evidence than
the mask the training panel actually carried.

★ THE RULE IS `build_wide_dl.py::MEMBER110`, NOT `panel_build.py::derive_member`.
THREE different member rules exist in this codebase and they are not interchangeable:

  (1) multi_asset/data/build_wide_panel.py   MEMBER    calendar-month refresh, elig = finite CLOSE
                                                       & dv>0, then `&= isfinite(CLOSE)`
  (2) multi_asset/data/build_wide_dl.py      MEMBER110 30-DAY-BLOCK refresh counted from panel row
                                                       0, elig = isfinite(dv) ONLY, plus a
                                                       "fewer than 110 finite -> take all finite"
                                                       fallback
  (3) dl_quant_live/signal/panel_build.py    derive_member  ROW-WISE (hourly), elig = finite CLOSE
                                                       & dv>0 & venue-TRADABLE

The frozen models consumed (2): `wide_panel_dataset.WidePanelData` reads `z["MEMBER110"]`, which
`build_wide_dl.build()` writes. (3) is the LIVE rule and answers a different question (who do we
trade at this anchor). Reconstructing the training union with (3) would silently answer the wrong
question -- and it would look fine, because the two agree on every recent anchor where the venue
list and the top-110 cut happen to coincide.

★ THE FALLBACK BRANCH IS WHY THE UNION IS SO WIDE, AND IT IS EASY TO MISREAD.
In (2), when fewer than 110 symbols have a finite DVOL30 the block takes EVERY finite symbol. For
the whole of 2021-2023 the panel had 62-97 listed coins, so "top 110" never binds and MEMBER110 is
simply "everything listed". The union is consequently the entire panel axis, not a curated 110.

CALIBER NOTE -- daily klines standing in for hourly. The panel's DVOL30 is
`pd.DataFrame(QVOL_hourly).rolling(720, min_periods=120).mean()` -- a mean over HOURS. From daily
bars we reconstruct it as  sum(daily qvol over 30d) / (24 * n_days_present), min_periods 5 days.
These agree exactly when every hour of every present day is present, and drift for a symbol on its
listing day (a partial day counted as 24 hours). The drift is a rank-boundary effect only, which
is why step B validates against 9 real server masks rather than trusting the mapping.
"""
from __future__ import annotations

import json
import os
import sys
import time
from typing import Dict, List

import numpy as np
import pandas as pd

LIVE_REPO = os.path.expanduser("~/dl_quant_live")
OUT_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path[:0] = [os.path.join(LIVE_REPO, "signal"), os.path.join(LIVE_REPO, "live")]

HOUR_MS = 3_600_000
DAY_MS = 24 * HOUR_MS
TOPN = 110
BLOCK_DAYS = 30

# The panel grid, established from state/fixtures/parity_fixture_v2.npz: every one of the 10
# anchors satisfies anchor_ts == TS0 + anchor_idx*3600000 for this TS0, so the grid is hourly and
# contiguous from here. The training window ends 2026-06-30T23Z (row 48167, T=48168).
TS0 = int(pd.Timestamp("2021-01-01", tz="UTC").value // 10**6)
TS_END = int(pd.Timestamp("2026-07-01", tz="UTC").value // 10**6)      # exclusive
N_DAYS = (TS_END - TS0) // DAY_MS                                       # 2007

# ── rate discipline ──────────────────────────────────────────────────────────────────────────
# fapi_source.RateBudget is PROCESS-LOCAL, so this process cannot see what the live anchor loop is
# spending and vice versa. We therefore self-limit to a small fraction of the 2400/min cap so that
# even a fully concurrent anchor (which peaks near its own 1000/min budget) stays clear of it.
MY_WEIGHT_PER_MIN = 150
KLINE_LIMIT = 1500                                                      # weight 10 per request


def fetch_daily(src, symbol: str) -> Dict[int, float]:
    """openTime_ms -> quote volume, for [TS0, TS_END). Empty dict when the venue has no history."""
    out: Dict[int, float] = {}
    start = TS0
    while start < TS_END:
        rows = src._get("/fapi/v1/klines",
                        {"symbol": symbol, "interval": "1d",
                         "startTime": start, "endTime": TS_END - 1, "limit": KLINE_LIMIT},
                        weight=10)
        if not rows:
            break
        for r in rows:
            t = int(r[0])
            if TS0 <= t < TS_END:
                out[t] = float(r[7])                                    # quoteAssetVolume
        last = int(rows[-1][0])
        if len(rows) < KLINE_LIMIT:
            break
        start = last + DAY_MS
        time.sleep(60.0 * 10 / MY_WEIGHT_PER_MIN)
    return out


def member_blocks(DV_daily: np.ndarray) -> np.ndarray:
    """build_wide_dl.py::MEMBER110, evaluated per 30-day block. Returns (n_blocks, N) bool."""
    n_blk = int(np.ceil(N_DAYS / BLOCK_DAYS))
    N = DV_daily.shape[1]
    M = np.zeros((n_blk, N), bool)
    for b in range(n_blk):
        dv = DV_daily[b * BLOCK_DAYS]                    # DVOL30 at block start (trailing, <=t)
        fin = np.isfinite(dv)
        if fin.sum() >= TOPN:
            M[b, np.argsort(-np.where(fin, dv, -np.inf))[:TOPN]] = True
        else:
            M[b] = fin                                   # the fallback branch -- see module docstring
    return M


def main():
    import fapi_source as FS
    import live_panel as LP

    symbols: List[str] = LP.panel_symbols()              # the FROZEN 140-column axis
    print(f"[axis] {len(symbols)} frozen panel symbols from config/funding_span_table.json",
          flush=True)

    src = FS.FapiSource()
    QV = np.full((N_DAYS, len(symbols)), np.nan)
    empties = []
    t_start = time.time()
    for j, s in enumerate(symbols):
        rows = fetch_daily(src, s)
        if not rows:
            empties.append(s)
        for t, q in rows.items():
            QV[(t - TS0) // DAY_MS, j] = q
        if (j + 1) % 10 == 0:
            print(f"  [{j+1}/{len(symbols)}] {s} days={len(rows)} "
                  f"elapsed={time.time()-t_start:.0f}s", flush=True)
        time.sleep(60.0 * 10 / MY_WEIGHT_PER_MIN)
    print(f"[fetch] done in {time.time()-t_start:.0f}s; no-history symbols: {empties}", flush=True)

    # DVOL30 = trailing-30d MEAN HOURLY quote volume (see CALIBER NOTE)
    q = pd.DataFrame(QV)
    s30 = q.rolling(BLOCK_DAYS, min_periods=5).sum()
    n30 = q.notna().rolling(BLOCK_DAYS, min_periods=5).sum()
    DV = (s30 / (24.0 * n30)).values
    DV = np.asarray(np.asarray(DV, np.float32), np.float64)   # the panel stores DVOL30 as float32

    M = member_blocks(DV)
    union = np.zeros(len(symbols), bool)
    union |= M.any(0)

    per_block = []
    for b in range(M.shape[0]):
        d0 = TS0 + b * BLOCK_DAYS * DAY_MS
        per_block.append({"block": b,
                          "start": str(pd.to_datetime(d0, unit="ms", utc=True))[:10],
                          "n_members": int(M[b].sum())})

    res = {"symbols_axis": symbols, "n_axis": len(symbols),
           "union": sorted([symbols[j] for j in np.where(union)[0]]),
           "n_union": int(union.sum()),
           "no_history_from_fapi": empties,
           "per_block": per_block,
           "never_member": sorted([symbols[j] for j in np.where(~union)[0]])}
    p = os.path.join(OUT_DIR, "training_member_union_reconstructed.json")
    with open(p, "w") as f:
        json.dump(res, f, indent=1)
    print(f"[union] reconstructed n={res['n_union']}/{len(symbols)}  -> {p}", flush=True)
    np.savez(os.path.join(OUT_DIR, "training_member_union_blocks.npz"),
             symbols=np.array(symbols, dtype=object), M=M, DV=DV.astype(np.float32))
    return res


if __name__ == "__main__":
    main()
