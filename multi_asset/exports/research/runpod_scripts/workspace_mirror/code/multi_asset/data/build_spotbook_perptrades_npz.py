"""RUN 2(b) cache — SPOT book + PERP trades features -> PERP y_600 target.

> created 2026-06-21 | status: acceptance-probe | branch: multi-asset

This is the **npz_v4 caliber** (spot book + perp trades, X std ~25) but with the
PERP target (the tradeable instrument) — to test the hypothesis that perp-TRADES
are the real signal for perp prediction.

X  = build_npz_for_day on SPOT book (binance) + PERP trades (binance-futures),
     input_len=600/stride=180, ridge+regime+quantize (the milestone contract).
y_600 = PERP forward log-return re-anchored to the SPOT prediction second t:
        log(perp_mid[t+600] / perp_mid[t]), perp_mid from the PERP book top-of-
        book on a 1s grid (read inline — no mid_cache dependency, so full history
        is available). Strictly forward (>= t), offset 0; cross-day next-day
        stitch for the t+600 leg; tail windows whose forward second is missing
        stay masked.

Source: ONLY /mnt/storage/btcusdt_copy_2023-01-01_2026-05-31 (spot book + perp
trades + perp book). Output: data/npz_spotbook_perptrades/<day>.npz with the
LOBDatasetV2 schema (X, X_raw, regime_prior, timestamps, y_600, y_mask_600).

Usage:
  python multi_asset/data/build_spotbook_perptrades_npz.py --days 2025-04-15
  python multi_asset/data/build_spotbook_perptrades_npz.py --range 2023-08-01 2025-05-08 --procs 8
"""
from __future__ import annotations

import argparse
import datetime as dt
import os
import os.path as p
import sys
import time
import warnings

import numpy as np
import pandas as pd

_REPO = p.dirname(p.dirname(p.dirname(p.abspath(__file__))))
if _REPO not in sys.path:
    sys.path.insert(0, _REPO)

from src.features.pipeline import build_npz_for_day, _save_result_npz   # noqa: E402
from src.features.resample import resample_lob_to_1s                    # noqa: E402
from multi_asset.data.build_factor_leg import EXPECTED_FEATURES         # noqa: E402
from multi_asset.data.build_unified_npz import (                        # noqa: E402
    _read_gz_csv_robust, _BOOK_COLS, BOOK_ROOT, SPOT_VENUE, PERP_VENUE,
    _mid_1s, US, INPUT_LEN, STRIDE, N_LVL,
)

OUT_DIR = p.join(_REPO, "data", "npz_spotbook_perptrades")
TRADES_ROOT = "/mnt/storage/btcusdt_copy_2023-01-01_2026-05-31/dl-tardis/trades"
HORIZON = 600


def _read_trades(date_str, venue):
    path = p.join(TRADES_ROOT, date_str, venue, "BTCUSDT.csv.gz")
    if not p.exists(path):
        raise FileNotFoundError(path)
    df = _read_gz_csv_robust(path)
    ren = {}
    if "amount" in df.columns and "size" not in df.columns:
        ren["amount"] = "size"
    if "id" in df.columns and "exec_id" not in df.columns:
        ren["id"] = "exec_id"
    if ren:
        df.rename(columns=ren, inplace=True)
    if "side" in df.columns:
        df["side"] = df["side"].astype(str).str.title()
    return df


def _spot_book_1s(date_str):
    path = p.join(BOOK_ROOT, date_str, SPOT_VENUE, "BTCUSDT.csv.gz")
    if not p.exists(path):
        raise FileNotFoundError(path)
    raw = _read_gz_csv_robust(path, usecols=_BOOK_COLS)
    df1 = resample_lob_to_1s(raw, n_levels=N_LVL)
    s = int(pd.Timestamp(date_str, tz="UTC").timestamp() * US); e = s + 86400 * US
    return df1[(df1["timestamp"] >= s) & (df1["timestamp"] < e)].reset_index(drop=True)


def _perp_mid_grid(date_str):
    """(sec, perp_mid) for date + next-day tail stitched for the t+600 forward leg."""
    sec0, mid0, _ = _mid_1s(date_str, PERP_VENUE)
    nd = (dt.date.fromisoformat(date_str) + dt.timedelta(days=1)).isoformat()
    try:
        sec1, mid1, _ = _mid_1s(nd, PERP_VENUE)
        keep = sec1 > sec0[-1]
        if keep.any():
            return np.concatenate([sec0, sec1[keep]]), np.concatenate([mid0, mid1[keep]])
    except FileNotFoundError:
        pass
    return sec0, mid0


def build_one_day(date_str, out_path):
    t0 = time.time()
    df1 = _spot_book_1s(date_str)
    if len(df1) < INPUT_LEN:
        raise ValueError(f"{date_str}: {len(df1)} spot-book 1s rows")
    perp_trades = _read_trades(date_str, PERP_VENUE)
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        res = build_npz_for_day(
            df1, trades_df=perp_trades, horizons_sec=[HORIZON],
            input_len=INPUT_LEN, stride=STRIDE, n_levels=N_LVL,
            include_ridge_features=True, include_regime_prior=True,
            quantize_features=True)
    feats = [str(f) for f in res["features"]]
    if feats != EXPECTED_FEATURES:
        raise RuntimeError(f"{date_str}: feature schema drift")

    # PERP target re-anchored to the spot pred second t (offset 0, forward only)
    sec, perp_mid = _perp_mid_grid(date_str)
    ts = res["timestamps"].astype(np.int64)
    s = ts // US

    def lk(target):
        pos = np.searchsorted(sec, target, side="left")
        posc = np.clip(pos, 0, sec.size - 1)
        hit = (pos < sec.size) & (sec[posc] == target)
        v = np.full(target.shape, np.nan); v[hit] = perp_mid[posc[hit]]
        return v
    m_t = lk(s); m_f = lk(s + HORIZON)
    with np.errstate(invalid="ignore", divide="ignore"):
        good = np.isfinite(m_t) & np.isfinite(m_f) & (m_t > 0) & (m_f > 0)
        y = np.full(s.shape, np.nan); y[good] = np.log(m_f[good] / m_t[good])
    res["y_600"] = y.astype(np.float32)
    res["y_mask_600"] = good.astype(np.uint8)
    # drop the spot-book-mid labels that build_npz_for_day created (keep perp y)
    res["y"] = res["y_600"]; res["y_mask"] = res["y_mask_600"]

    os.makedirs(OUT_DIR, exist_ok=True)
    tmp = f"{out_path}.tmp.{os.getpid()}.npz"
    _save_result_npz(tmp, res)
    os.replace(tmp, out_path)
    yv = y[good]
    return {"N": int(ts.size), "valid": int(good.sum()),
            "Xstd": float(np.nanstd(res["X"].reshape(-1, 64))),
            "y_std_bps": float(yv.std() * 1e4) if yv.size else float("nan"),
            "secs": time.time() - t0, "mb": os.path.getsize(out_path) / 1e6}


def _daterange(a, b):
    d0 = dt.date.fromisoformat(a); d1 = dt.date.fromisoformat(b)
    out = []
    while d0 <= d1:
        out.append(d0.isoformat()); d0 += dt.timedelta(days=1)
    return out


def _worker(args):
    d, force = args
    out = p.join(OUT_DIR, f"{d}.npz")
    if (not force) and p.exists(out):
        return (d, "skip", None)
    try:
        return (d, "ok", build_one_day(d, out))
    except Exception as e:
        return (d, "fail", f"{type(e).__name__}: {e}")


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    g = ap.add_mutually_exclusive_group(required=True)
    g.add_argument("--days", nargs="+")
    g.add_argument("--range", nargs=2, metavar=("START", "END"))
    ap.add_argument("--force", action="store_true")
    ap.add_argument("--procs", type=int, default=8)
    args = ap.parse_args()
    os.makedirs(OUT_DIR, exist_ok=True)
    days = args.days if args.days else _daterange(*args.range)
    print(f"[spotbook_perptrades] {len(days)} days -> {OUT_DIR} (procs={args.procs})", flush=True)
    t0 = time.time(); nok = nsk = nf = 0; fails = []
    tasks = [(d, args.force) for d in days]
    if args.procs <= 1:
        it = (_worker(t) for t in tasks)
    else:
        import multiprocessing as mp
        pool = mp.Pool(args.procs)
        it = pool.imap_unordered(_worker, tasks, chunksize=2)
    for i, (d, st, info) in enumerate(it):
        if st == "ok":
            nok += 1
            if nok % 20 == 0:
                print(f"  [{i+1}/{len(days)}] {d} N={info['N']} Xstd={info['Xstd']:.1f} "
                      f"y_std={info['y_std_bps']:.1f}bps {info['secs']:.1f}s ({(time.time()-t0)/60:.1f}min)",
                      flush=True)
        elif st == "skip":
            nsk += 1
        else:
            nf += 1; fails.append((d, info)); print(f"  [warn] {d}: {info}", flush=True)
    print(f"[spotbook_perptrades] DONE ok={nok} skip={nsk} fail={nf} in {(time.time()-t0)/60:.1f}min", flush=True)
    if fails:
        print("  fails:", fails[:10], flush=True)
