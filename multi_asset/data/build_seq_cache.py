"""Build a per-DAY contiguous all-asset SEQUENCE cache for the temporal-spatial
panel model.

The shallow panel_cache stores only the LAST-TOKEN feature vector at each pred
index (X(n,44)) — it threw away the temporal sequence, which is exactly the
signal that gave single-asset BTC its 0.058 per-asset Pearson. To recover that,
the temporal-spatial model needs the full 600-bar lookback window per asset. We
do NOT materialise overlapping windows (that exploded to 65 GB/asset = 910 GB
for 14 assets). Instead we store each day's CONTIGUOUS full-day arrays once and
let the panel dataset slice F[i-599:i+1] windows on the fly (no overlap
redundancy: ~110 GB hand-feats + ~50 GB raw LOB for 14 assets × 487 days).

One file per trading day, all 14 assets stacked and time-aligned on the shared
bar grid that `load_day_panel` already produces:

    <SEQ_DIR>/<day>.npz
        F     (S, T, 44)   float32  causal hand features per bar (full day)
        Xraw  (S, T, 5, 4) float32  5-level raw-LOB tensor per bar
        y     (S, T)       float32  forward-600s mid log-return (RAW)
        mask  (S, T)       bool     per-bar validity (warmup / NaN dropped)
        ts    (T,)         int64    ns timestamp of each bar (shared grid)

Plus feature_names.json + build_meta.json at the cache root. The raw-LOB key is
stored in the SAME npz but np.load is lazy per-key, so a hand-features-only model
reads only F (Xraw costs nothing until requested).

Read-only over the share. Idempotent: re-run overwrites. Skips a day file that
already exists unless --force (so an interrupted build resumes cheaply).
"""
from __future__ import annotations

import argparse
import json
import os
import os.path as p
import sys
import time

import numpy as np

sys.path.insert(0, p.dirname(p.dirname(p.dirname(p.abspath(__file__)))))
from multi_asset.data.bar_loader import load_day_panel, _BAR_PATH  # noqa: E402
from multi_asset.data.features_ma import (  # noqa: E402
    build_features, compute_y600, valid_mask, HORIZON,
)
from multi_asset.data.raw_lob_ma import build_raw_lob_tensor  # noqa: E402

SYMBOLS = [
    "bnfbtc", "bnfeth", "bnfsol", "bnfbnb", "bnfxrp", "bnfdog", "bnfada",
    "bnflink", "bnfbch", "bnftrx", "bnfltc", "bnfdot", "bnffil", "bnfetc",
]

# Same all-14-liquid window as the panel_cache (487 trading days).
WIN_START = 20220101   # extended (2026-07-09) for the M0 full-history walk-forward RETRAINING replay
WIN_END = 20250930

SEQ_DIR = ("/mnt/storage/private/work_hsy/quant_research_multi_asset/"
           "multi_asset/exports/seq_cache")


def list_days(start: int, end: int) -> list:
    days = []
    for name in os.listdir(_BAR_PATH):
        if name.isdigit() and len(name) == 8:
            di = int(name)
            if start <= di <= end:
                days.append(di)
    return sorted(days)


def build(force: bool = False):
    os.makedirs(SEQ_DIR, exist_ok=True)
    days = list_days(WIN_START, WIN_END)
    print(f"[seq] window {WIN_START}..{WIN_END}: {len(days)} days, "
          f"{len(SYMBOLS)} symbols -> {SEQ_DIR}", flush=True)

    feat_names = None
    t0 = time.time()
    n_fail = 0
    n_done = 0
    n_skip = 0

    for di, d in enumerate(days):
        out = p.join(SEQ_DIR, f"{d}.npz")
        if (not force) and p.exists(out):
            n_skip += 1
            if feat_names is None:  # still need names for meta
                try:
                    feat_names = list(np.load(out, allow_pickle=True)["feat_names"])
                except Exception:
                    pass
            continue
        try:
            dp = load_day_panel(d, SYMBOLS)
        except Exception as e:  # missing/corrupt day -> skip, keep going
            n_fail += 1
            print(f"  [warn] day {d} load failed: {e}", flush=True)
            continue
        T = dp.ts.shape[0]
        ts_day = dp.ts.astype(np.int64)

        F_all = np.zeros((len(SYMBOLS), T, 44), dtype=np.float32)
        Xraw_all = np.zeros((len(SYMBOLS), T, 5, 4), dtype=np.float32)
        y_all = np.full((len(SYMBOLS), T), np.nan, dtype=np.float32)
        mask_all = np.zeros((len(SYMBOLS), T), dtype=bool)

        for si, s in enumerate(SYMBOLS):
            F, names = build_features(dp, s)            # (T, 44)
            if feat_names is None:
                feat_names = names
            if F.shape[1] != 44:
                raise ValueError(f"{s} day {d}: expected 44 feats, got {F.shape[1]}")
            y = compute_y600(dp, s)                     # (T,)
            vm = valid_mask(dp, s)                      # (T,) bool
            xr = build_raw_lob_tensor(dp, s)            # (T, 5, 4)
            F_all[si] = F.astype(np.float32)
            Xraw_all[si] = xr
            y_all[si] = y.astype(np.float32)
            mask_all[si] = vm.astype(bool)

        np.savez(out, F=F_all, Xraw=Xraw_all, y=y_all, mask=mask_all,
                 ts=ts_day, feat_names=np.array(feat_names))
        n_done += 1

        if n_done % 10 == 0 or di == len(days) - 1:
            el = time.time() - t0
            rate = n_done / el if el > 0 else 0
            eta = (len(days) - di - 1) / rate if rate > 0 else 0
            print(f"  [{di+1:4d}/{len(days)}] day {d}  built={n_done} skip={n_skip} "
                  f"fail={n_fail}  {el/60:.1f} min, ~{rate*60:.0f} day/min, "
                  f"ETA {eta/60:.1f} min", flush=True)

    meta = {
        "window": [WIN_START, WIN_END],
        "n_days_listed": len(days),
        "n_days_built": n_done,
        "n_days_skipped": n_skip,
        "n_days_failed": n_fail,
        "horizon_s": HORIZON,
        "n_features": len(feat_names) if feat_names else 0,
        "symbols": SYMBOLS,
        "schema": {
            "F": "(S,T,44) f32 causal hand features",
            "Xraw": "(S,T,5,4) f32 raw LOB [bid_dbps,bid_logamt,ask_dbps,ask_logamt]",
            "y": "(S,T) f32 forward-600s mid logret RAW",
            "mask": "(S,T) bool per-bar validity",
            "ts": "(T,) int64 ns shared grid",
        },
    }
    with open(p.join(SEQ_DIR, "feature_names.json"), "w") as f:
        json.dump(feat_names, f, indent=2)
    with open(p.join(SEQ_DIR, "build_meta.json"), "w") as f:
        json.dump(meta, f, indent=2)
    print(f"[seq] done in {(time.time()-t0)/60:.1f} min: built={n_done} "
          f"skip={n_skip} fail={n_fail} -> {SEQ_DIR}", flush=True)


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--force", action="store_true",
                    help="rebuild day files that already exist")
    args = ap.parse_args()
    build(force=args.force)
