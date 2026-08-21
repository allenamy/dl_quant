"""Build a compact per-asset feature+label panel cache for Phase-1 A2 (per-asset
Ridge SNR) — reading each slow share day ONCE.

For a contiguous window of trading days where all 14 assets are liquid, for each
day we `load_day_panel(day, all_14_syms)` exactly once, then per symbol compute
the 47 causal features + y_600 + valid_mask, SUBSAMPLE to a stride=180 prediction
grid (dropping invalid / NaN-y windows), and append to a per-symbol cache. We
also flag a strictly non-overlap `clean600` subsample (consecutive selected
windows >=600s apart, computed greedily per day so day boundaries never create a
fake overlap).

Output (server-local, NOT on the share, NOT synced to local):
    <CACHE_DIR>/<sym>.npz  with arrays:
        X        (n, 47)  float32   causal features at the pred index
        y        (n,)     float32   forward 600s log-return of mid (RAW, not bps)
        ts       (n,)     int64     ns timestamp of the pred bar
        day      (n,)     int32     trading day YYYYMMDD of the pred bar
        clean600 (n,)     bool      non-overlap (>=600s apart) subsample flag
    plus feature_names.json and build_meta.json at the cache root.

Why stride=180 base + clean600 flag: 180s is the dense pred grid (lets us also
eval dense if ever needed); clean600 selects a >=600s non-overlap subset so the
A2 Ridge eval uses IID (non-label-overlapping) test samples — the honest measure.

Read-only over the share. Idempotent: re-run overwrites the cache.
"""
from __future__ import annotations

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

SYMBOLS = [
    "bnfbtc", "bnfeth", "bnfsol", "bnfbnb", "bnfxrp", "bnfdog", "bnfada",
    "bnflink", "bnfbch", "bnftrx", "bnfltc", "bnfdot", "bnffil", "bnfetc",
]

# Window where all 14 assets are liquid (verified: book_frac=1.0 on both ends,
# all assets trading; see A2 report). 487 trading days.
WIN_START = 20240601
WIN_END = 20250930

PRED_STRIDE = 180          # dense prediction grid (seconds == bars)
CLEAN_GAP = 600            # min seconds between consecutive clean600 windows

CACHE_DIR = ("/mnt/storage/private/work_hsy/quant_research_multi_asset/"
             "multi_asset/exports/panel_cache")


def list_days(start: int, end: int) -> list:
    days = []
    for name in os.listdir(_BAR_PATH):
        if name.isdigit() and len(name) == 8:
            di = int(name)
            if start <= di <= end:
                days.append(di)
    return sorted(days)


def _clean600_flags(pred_idx: np.ndarray, ts: np.ndarray) -> np.ndarray:
    """Greedy non-overlap flag over the day's selected pred indices: keep a window
    only if its ts is >= CLEAN_GAP ns after the last kept window's ts. pred_idx is
    sorted ascending; ts is the full-day ns grid."""
    flags = np.zeros(pred_idx.shape[0], dtype=bool)
    last_keep_ts = None
    gap_ns = CLEAN_GAP * 1_000_000_000
    for i, pi in enumerate(pred_idx):
        t = ts[pi]
        if last_keep_ts is None or (t - last_keep_ts) >= gap_ns:
            flags[i] = True
            last_keep_ts = t
    return flags


def build(win_start=WIN_START, win_end=WIN_END, cache_dir=CACHE_DIR):
    os.makedirs(cache_dir, exist_ok=True)
    days = list_days(win_start, win_end)
    print(f"[cache] window {win_start}..{win_end}: {len(days)} trading days, "
          f"{len(SYMBOLS)} symbols, pred_stride={PRED_STRIDE}s, clean_gap={CLEAN_GAP}s")

    # per-symbol accumulators
    acc = {s: {"X": [], "y": [], "ts": [], "day": [], "clean600": []} for s in SYMBOLS}
    feat_names = None
    t0 = time.time()
    n_fail = 0

    for di, d in enumerate(days):
        try:
            dp = load_day_panel(d, SYMBOLS)
        except Exception as e:  # missing/corrupt day -> skip, keep going
            n_fail += 1
            print(f"  [warn] day {d} load failed: {e}")
            continue
        T = dp.ts.shape[0]
        ts_day = dp.ts
        # candidate pred indices on the dense grid, leaving the forward y window
        base_idx = np.arange(0, T - HORIZON, PRED_STRIDE)

        for s in SYMBOLS:
            F, names = build_features(dp, s)
            if feat_names is None:
                feat_names = names
            y = compute_y600(dp, s)
            vm = valid_mask(dp, s)
            # keep pred indices that are valid AND have a finite y
            sel = base_idx[vm[base_idx] & np.isfinite(y[base_idx])]
            if sel.size == 0:
                continue
            clean = _clean600_flags(sel, ts_day)
            acc[s]["X"].append(F[sel])
            acc[s]["y"].append(y[sel].astype(np.float32))
            acc[s]["ts"].append(ts_day[sel].astype(np.int64))
            acc[s]["day"].append(np.full(sel.shape[0], d, dtype=np.int32))
            acc[s]["clean600"].append(clean)

        if (di + 1) % 25 == 0 or di == len(days) - 1:
            el = time.time() - t0
            rate = (di + 1) / el
            eta = (len(days) - di - 1) / rate if rate > 0 else 0
            print(f"  [{di+1:4d}/{len(days)}] day {d}  "
                  f"{el/60:.1f} min elapsed, ETA {eta/60:.1f} min", flush=True)

    # write per-symbol npz
    meta = {
        "window": [win_start, win_end],
        "n_days_listed": len(days),
        "n_days_failed": n_fail,
        "pred_stride_s": PRED_STRIDE,
        "clean_gap_s": CLEAN_GAP,
        "horizon_s": HORIZON,
        "n_features": len(feat_names) if feat_names else 0,
        "per_symbol_counts": {},
    }
    for s in SYMBOLS:
        if not acc[s]["X"]:
            print(f"  [warn] {s}: no windows collected")
            meta["per_symbol_counts"][s] = {"n": 0, "n_clean": 0}
            continue
        X = np.concatenate(acc[s]["X"]).astype(np.float32)
        y = np.concatenate(acc[s]["y"]).astype(np.float32)
        ts = np.concatenate(acc[s]["ts"]).astype(np.int64)
        day = np.concatenate(acc[s]["day"]).astype(np.int32)
        clean600 = np.concatenate(acc[s]["clean600"]).astype(bool)
        # rows are appended in day order; ts already sorted within and across days
        np.savez(p.join(cache_dir, f"{s}.npz"),
                 X=X, y=y, ts=ts, day=day, clean600=clean600)
        meta["per_symbol_counts"][s] = {"n": int(X.shape[0]),
                                        "n_clean": int(clean600.sum())}
        print(f"  saved {s}: n={X.shape[0]:7d} n_clean={int(clean600.sum()):6d}")

    with open(p.join(cache_dir, "feature_names.json"), "w") as f:
        json.dump(feat_names, f, indent=2)
    with open(p.join(cache_dir, "build_meta.json"), "w") as f:
        json.dump(meta, f, indent=2)
    print(f"[cache] done in {(time.time()-t0)/60:.1f} min -> {cache_dir}")


if __name__ == "__main__":
    import argparse
    ap = argparse.ArgumentParser()
    ap.add_argument("--win_start", type=int, default=WIN_START,
                    help="first day YYYYMMDD (default 20240601 = production window)")
    ap.add_argument("--win_end", type=int, default=WIN_END,
                    help="last day YYYYMMDD (default 20250930)")
    ap.add_argument("--out_dir", default=CACHE_DIR,
                    help="output cache dir (default the production panel_cache)")
    args = ap.parse_args()
    build(win_start=args.win_start, win_end=args.win_end, cache_dir=args.out_dir)
