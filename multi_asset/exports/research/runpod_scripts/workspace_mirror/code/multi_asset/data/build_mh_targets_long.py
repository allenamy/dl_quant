"""Long-horizon (>600s) AUX-targets cache for multi-asset v2 Phase-0a.

> **created:** 2026-07-07 | **Session:** multi-asset-v2 phase-0a (0B) | **状态:** in-progress

Thin re-target of build_multihorizon_targets.py: SAME 14-asset panel, SAME within-day
forward-logret + finite-mask logic, ONLY the horizon changes to 3600s (1h). Writes into
mh_targets_long/ — the dir seq_panel_dataset already routes h>600 to
(_mh_dir_for = root+'/mh_targets_long' if h>600). Enables the 1h cross-sectional GO/NO-GO
without rebuilding features. Read-only over the share; idempotent (skip existing unless --force).

Output: <mh_targets_long>/<day>.npz with y_3600 (S,T) f32 + m_3600 (S,T) bool + ts.
"""
from __future__ import annotations
import argparse, os, os.path as p, sys, time
import numpy as np

sys.path.insert(0, p.dirname(p.dirname(p.dirname(p.abspath(__file__)))))
from multi_asset.data.bar_loader import load_day_panel, _BAR_PATH  # noqa: E402
from multi_asset.data.build_multihorizon_targets import SYMBOLS, list_days, WIN_START, WIN_END  # noqa: E402

WIN_START = 20220101   # extended (2026-07-09) for the M0 full-history walk-forward RETRAINING replay
WIN_END = 20251130     # DL ceiling = bar_data end (2025-11) per 0C's pre-reg (test 2025 Jan-Nov)
HORIZONS = [3600, 7200]   # 1h primary + 2h robustness (funding GO → confirm not a 1h artifact)
OUT_DIR = ("/mnt/storage/private/work_hsy/quant_research_multi_asset/"
           "multi_asset/exports/mh_targets_long")


def build(force=False):
    os.makedirs(OUT_DIR, exist_ok=True)
    days = list_days(WIN_START, WIN_END)
    print(f"[mh_long] {len(days)} days, horizons={HORIZONS} -> {OUT_DIR}", flush=True)
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
                if T > h:
                    y[:T - h] = logm[h:] - logm[:T - h]
                ys[h][si] = y.astype(np.float32)
                ms[h][si] = np.isfinite(y)
        np.savez(out, ts=dp.ts.astype(np.int64),
                 **{f"y_{h}": ys[h] for h in HORIZONS},
                 **{f"m_{h}": ms[h] for h in HORIZONS})
        n_done += 1
        if n_done % 25 == 0 or di == len(days) - 1:
            print(f"  [{di+1}/{len(days)}] {d} done={n_done} skip={n_skip} fail={n_fail} "
                  f"{(time.time()-t0)/60:.1f}min", flush=True)
    print(f"[mh_long] done in {(time.time()-t0)/60:.1f}min: {n_done} built {n_skip} skip "
          f"{n_fail} fail -> {OUT_DIR}", flush=True)


if __name__ == "__main__":
    ap = argparse.ArgumentParser(); ap.add_argument("--force", action="store_true")
    build(force=ap.parse_args().force)
