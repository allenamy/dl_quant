"""Small AUX-targets cache: per-day forward returns at multiple horizons (y_60/y_180/
y_600) for all 14 assets, from mid. Enables MULTI-HORIZON MTL — the short-horizon heads
harvest the strong BTC->alt lead-lag and route it (via the shared backbone) into y_600.

Cheap: reads only `mid` per asset per day; output is tiny ((S,T) float32 per horizon,
~5 MB/day -> ~2.4 GB for 487 days), keyed by day to merge with the heavy seq_cache.

Output: <DIR>/<day>.npz with y_{60,180,600} (S,T) f32 + m_{60,180,600} (S,T) bool + ts.
Read-only over the share. Idempotent (skips existing day files unless --force).
"""
from __future__ import annotations

import argparse
import os
import os.path as p
import sys
import time

import numpy as np

sys.path.insert(0, p.dirname(p.dirname(p.dirname(p.abspath(__file__)))))
from multi_asset.data.bar_loader import load_day_panel, _BAR_PATH  # noqa: E402

SYMBOLS = ["bnfbtc", "bnfeth", "bnfsol", "bnfbnb", "bnfxrp", "bnfdog", "bnfada",
           "bnflink", "bnfbch", "bnftrx", "bnfltc", "bnfdot", "bnffil", "bnfetc"]
HORIZONS = [60, 180, 600]
WIN_START, WIN_END = 20240601, 20250930
OUT_DIR = ("/mnt/storage/private/work_hsy/quant_research_multi_asset/"
           "multi_asset/exports/mh_targets")


def list_days(a, b):
    return sorted(int(n) for n in os.listdir(_BAR_PATH)
                  if n.isdigit() and len(n) == 8 and a <= int(n) <= b)


def build(force=False):
    os.makedirs(OUT_DIR, exist_ok=True)
    days = list_days(WIN_START, WIN_END)
    print(f"[mh] {len(days)} days, horizons={HORIZONS}", flush=True)
    t0 = time.time(); n_done = n_skip = n_fail = 0
    for di, d in enumerate(days):
        out = p.join(OUT_DIR, f"{d}.npz")
        if (not force) and p.exists(out):
            n_skip += 1; continue
        try:
            dp = load_day_panel(d, SYMBOLS)
        except Exception as e:
            n_fail += 1; print(f"  [warn] {d}: {e}", flush=True); continue
        T = dp.ts.shape[0]; S = len(SYMBOLS)
        mid_i = dp.cols.index("mid")
        ys = {h: np.full((S, T), np.nan, np.float32) for h in HORIZONS}
        ms = {h: np.zeros((S, T), bool) for h in HORIZONS}
        for si, s in enumerate(SYMBOLS):
            mid = dp.data[s][:, mid_i].astype(np.float64)
            logm = np.log(np.where(mid > 0, mid, np.nan))
            for h in HORIZONS:
                y = np.full(T, np.nan, np.float64)
                y[:T - h] = logm[h:] - logm[:T - h]
                ys[h][si] = y.astype(np.float32)
                ms[h][si] = np.isfinite(y)
        np.savez(out, ts=dp.ts.astype(np.int64),
                 **{f"y_{h}": ys[h] for h in HORIZONS},
                 **{f"m_{h}": ms[h] for h in HORIZONS})
        n_done += 1
        if n_done % 25 == 0 or di == len(days) - 1:
            el = time.time() - t0
            print(f"  [{di+1}/{len(days)}] {d} done={n_done} skip={n_skip} fail={n_fail} "
                  f"{el/60:.1f}min", flush=True)
    print(f"[mh] done in {(time.time()-t0)/60:.1f}min: {n_done} built {n_skip} skip "
          f"{n_fail} fail -> {OUT_DIR}", flush=True)


if __name__ == "__main__":
    ap = argparse.ArgumentParser(); ap.add_argument("--force", action="store_true")
    build(force=ap.parse_args().force)
