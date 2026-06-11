"""Build per-day BTC 25-level LOB STATE scalars (z_btc) aligned to the panel grid.

S5 prerequisite for the FiLM-conditioning kill-test: the temporal-spatial panel
model gets a tiny side-array z_btc (T, 8) of *causal* BTC deep-book state scalars
at each panel prediction timestamp, and FiLM layers modulate the backbone with it.
The kill-test asks: does deep-book (25-level) BTC state carry conditioning info
beyond the 5-level + 9-bucket bar features the panel already sees?

Source data (READ-ONLY, discovered schema)
------------------------------------------
    /mnt/storage/share/23-25-BTCUSDT/book_snapshot_25/YYYY-MM-DD/BTCUSDT.csv.gz

Tardis-style tick-level book snapshots, FULL 25 explicit levels per side
(``asks[i].price/.amount``, ``bids[i].price/.amount``, i in 0..24), ``timestamp``
in MICROSECONDS (exchange event time). Calendar-UTC date folders, 2023-01-01 ..
2025-09-30 — fully covers the panel window 20240601..20250930. No schema
substitution was needed: all 8 scalars are computed exactly as specified from
explicit per-level prices/sizes (NOT the 9-bucket cumulative-depth fallback).

Alignment / causality
---------------------
The panel trading "day" d (seq_cache/<d>.npz) spans UTC ~14:05 of d-1 to
~13:54:59 of d (85800 1s bars), so each build reads ticks from TWO calendar-date
folders. Ticks are floored (never rounded) to the second, last-tick-per-second
kept, forward-filled — the exact causal convention of the single-asset
``src/features/resample.py`` and of the share bar loader (book state at bar ts =
last tick inside that second). The 1s series is extended 300 s BEFORE the day's
first bar (plus a 600 s ffill seed margin) so rolling-300s features are fully
formed at every grid row — no in-day warmup loss.

Output rows sit on the panel's stride-180 prediction-candidate grid
(``np.arange(0, T - HORIZON, PRED_STRIDE)`` over the seq_cache ts — identical to
``build_feature_cache.py``; the actual panel ts is always a subset). Rows where
any of the 8 scalars is non-finite are dropped, so ``ts`` is an aligned SUBSET
of the seq_cache ts and downstream joins by exact ts match.

The 8 scalars (raw — standardize NOTHING here; downstream normalizes; clips are
generous, against pathological values only)
-------------------------------------------
    0 deep_imb_l25       (sum bid sz L1-25 - sum ask sz L1-25) / (sum + sum).
                         Mechanism: persistent deep-book pressure = patient
                         institutional interest, slower-moving than top-of-book.
    1 near_imb_l5        same over L1-5 only — lets FiLM see near-vs-deep
                         divergence (spoof-like near pressure vs real depth).
    2 slope_asym_l25     OLS slope of cumulative bid depth vs price-distance
                         minus same for asks, 25 levels. Distance is in BPS of
                         mid (documented choice: bps keeps the slope comparable
                         across the 2024-2025 BTC price range; mechanism is the
                         book's resistance profile asymmetry). Units: size/bps.
    3 micro_dev_bps      (microprice - mid)/mid in bps,
                         micro = (ask0*bidsz0 + bid0*asksz0)/(bidsz0+asksz0).
                         Mechanism: size-weighted fair price vs mid = imminent
                         tick direction pressure.
    4 dw_spread_bps      sum_l (ask_l - bid_l) * w_l / mid * 1e4, w_l prop. to
                         (bidsz_l + asksz_l). Mechanism: liquidity-weighted
                         effective spread across the whole visible book.
    5 deep_imb_d300      300 s change in (0): deep-imbalance momentum.
    6 rv_mid_300         rolling std of per-second log mid returns over 300 s
                         (raw, no annualization). Mechanism: realized-vol regime.
    7 depth_delta_log300 log(total 25-level depth_t / depth_{t-300}): net
                         deep-book add/pull — liquidity provision regime shift.

Output
------
    <OUT_DIR>/<day>.npz
        ts       (n,)   int64    ns, exact subset of seq_cache/<day>.npz ts
        Z        (n, 8) float32  raw state scalars (column order above)
        z_names  (8,)   str
    plus build_meta.json at the cache root.

Read-only over the share. Idempotent: skips existing day files unless --force.
CPU-only (pure numpy/pandas; safe to run while GPU training is up).

Usage
-----
    # validate 3 sample days (prints stats + alignment + ETA):
    python multi_asset/data/btc25_state.py --days 20250203 20250512 20250811 --force
    # full batch build (later):
    nohup python multi_asset/data/btc25_state.py --all > btc25_state_build.log 2>&1 &
"""
from __future__ import annotations

import argparse
import datetime as dt
import json
import os
import os.path as p
import sys
import time

import numpy as np
import pandas as pd

sys.path.insert(0, p.dirname(p.dirname(p.dirname(p.abspath(__file__)))))
from multi_asset.data.seq_panel_dataset import HORIZON, PRED_STRIDE  # noqa: E402

BOOK25_ROOT = "/mnt/storage/share/23-25-BTCUSDT/book_snapshot_25"  # READ-ONLY
SEQ_DIR = ("/mnt/storage/private/work_hsy/quant_research_multi_asset/"
           "multi_asset/exports/seq_cache")
OUT_DIR = ("/mnt/storage/private/work_hsy/quant_research_multi_asset/"
           "multi_asset/exports/btc25_state")

N_LVL = 25
ROLL_S = 300          # rolling window for features 5/6/7 (seconds)
SEED_S = 600          # extra ffill seed margin before the extended grid start

Z_NAMES = ["deep_imb_l25", "near_imb_l5", "slope_asym_l25", "micro_dev_bps",
           "dw_spread_bps", "deep_imb_d300", "rv_mid_300", "depth_delta_log300"]
# generous clips against pathological values ONLY (no standardization here)
Z_CLIPS = [(-1.0, 1.0), (-1.0, 1.0), (-1e4, 1e4), (-50.0, 50.0),
           (0.0, 500.0), (-2.0, 2.0), (0.0, 0.05), (-5.0, 5.0)]

_TICK_COLS = ["timestamp"]
for _i in range(N_LVL):
    _TICK_COLS += [f"bids[{_i}].price", f"bids[{_i}].amount",
                   f"asks[{_i}].price", f"asks[{_i}].amount"]


# --------------------------------------------------------------------- ticks
def _calendar_dates(t0_s: int, t1_s: int) -> list:
    """Calendar-UTC 'YYYY-MM-DD' folder names covering [t0_s, t1_s] (epoch s)."""
    d0 = dt.datetime.fromtimestamp(t0_s, dt.timezone.utc).date()
    d1 = dt.datetime.fromtimestamp(t1_s, dt.timezone.utc).date()
    out, d = [], d0
    while d <= d1:
        out.append(d.isoformat())
        d += dt.timedelta(days=1)
    return out


def _read_day_file(date_str: str) -> pd.DataFrame:
    path = p.join(BOOK25_ROOT, date_str, "BTCUSDT.csv.gz")
    if not p.exists(path):
        raise FileNotFoundError(path)
    try:
        return pd.read_csv(path, usecols=_TICK_COLS, engine="pyarrow")
    except Exception:  # pyarrow unavailable / parse quirk -> C engine fallback
        return pd.read_csv(path, usecols=_TICK_COLS, engine="c")


def _last_per_second(df: pd.DataFrame, t0_us: int, t1_us: int):
    """Causal 1s resample of one calendar file: floor ts to second (never
    round), keep the LAST tick per second, restricted to [t0_us, t1_us).
    Returns (secs (n,) int64 epoch-s ascending, mats dict of (n, 25) f64)."""
    t = df["timestamp"].to_numpy(np.int64)
    m = (t >= t0_us) & (t < t1_us)
    if not m.any():
        return None
    t = t[m]
    if not np.all(t[:-1] <= t[1:]):           # defensive: keep time order
        order = np.argsort(t, kind="stable")
        df = df.loc[m].iloc[order]
        t = t[order]
    else:
        df = df.loc[m]
    sec = t // 1_000_000
    last = np.flatnonzero(np.r_[sec[1:] != sec[:-1], True])
    sub = df.iloc[last]
    mats = {}
    for side, field, key in (("bids", "price", "bp"), ("bids", "amount", "bq"),
                             ("asks", "price", "ap"), ("asks", "amount", "aq")):
        cols = [f"{side}[{i}].{field}" for i in range(N_LVL)]
        mats[key] = sub[cols].to_numpy(np.float64)
    return sec[last], mats


def _load_book_1s(grid_secs: np.ndarray):
    """Causal 1s book series on grid_secs (epoch s, ascending): read the needed
    calendar folders, last-tick-per-second, forward-fill onto the grid (NaN
    before the first available tick). Returns dict bp/bq/ap/aq (T, 25) f64."""
    t0_us = int((grid_secs[0] - SEED_S)) * 1_000_000
    t1_us = int(grid_secs[-1] + 1) * 1_000_000
    secs_l, mats_l = [], []
    for ds in _calendar_dates(grid_secs[0] - SEED_S, grid_secs[-1]):
        got = _last_per_second(_read_day_file(ds), t0_us, t1_us)
        if got is not None:
            secs_l.append(got[0]); mats_l.append(got[1])
    if not secs_l:
        raise RuntimeError("no ticks in range")
    secs = np.concatenate(secs_l)                    # calendar files don't overlap
    if not np.all(secs[:-1] < secs[1:]):
        raise RuntimeError("tick seconds not strictly increasing across files")
    # causal ffill: index of the last available second at-or-before each grid sec
    pos = np.searchsorted(secs, grid_secs, side="right") - 1
    have = pos >= 0
    out = {}
    for k in ("bp", "bq", "ap", "aq"):
        v = np.concatenate([m[k] for m in mats_l], axis=0)
        g = np.full((grid_secs.shape[0], N_LVL), np.nan)
        g[have] = v[pos[have]]
        out[k] = g
    return out


# ------------------------------------------------------------------ features
def _masked_ols_slope(x: np.ndarray, y: np.ndarray, m: np.ndarray) -> np.ndarray:
    """Per-row OLS slope of y on x over masked level points. x,y,m: (T, L)."""
    n = m.sum(axis=1).astype(np.float64)
    xm = np.where(m, x, 0.0)
    ym = np.where(m, y, 0.0)
    sx, sy = xm.sum(1), ym.sum(1)
    sxx, sxy = (xm * xm).sum(1), (xm * ym).sum(1)
    den = n * sxx - sx * sx
    out = np.full(x.shape[0], np.nan)
    ok = (n >= 3) & (den > 1e-12)
    out[ok] = (n * sxy - sx * sy)[ok] / den[ok]
    return out


def compute_state(bp, bq, ap, aq) -> np.ndarray:
    """The 8 causal state scalars from a contiguous 1s book series.

    Inputs (T, 25) f64 (NaN rows allowed -> NaN features). Features 5/6/7 use
    trailing ROLL_S-second windows, so the first ROLL_S rows are NaN — callers
    prepend ROLL_S seconds of history before the rows they keep.
    """
    T = bp.shape[0]
    mid = 0.5 * (bp[:, 0] + ap[:, 0])
    mid = np.where(mid > 0, mid, np.nan)
    bqz = np.where(np.isfinite(bq), bq, 0.0)
    aqz = np.where(np.isfinite(aq), aq, 0.0)
    bsum, asum = bqz.sum(1), aqz.sum(1)
    tot = bsum + asum

    f = np.full((T, 8), np.nan)
    # 0/1: deep + near imbalance
    with np.errstate(invalid="ignore", divide="ignore"):
        f[:, 0] = np.where(tot > 0, (bsum - asum) / tot, np.nan)
        b5, a5 = bqz[:, :5].sum(1), aqz[:, :5].sum(1)
        t5 = b5 + a5
        f[:, 1] = np.where(t5 > 0, (b5 - a5) / t5, np.nan)
        # 2: book slope asymmetry (cumulative depth vs distance-in-bps OLS)
        xb = (mid[:, None] - bp) / mid[:, None] * 1e4
        xa = (ap - mid[:, None]) / mid[:, None] * 1e4
        mb = np.isfinite(xb) & np.isfinite(bq)
        ma = np.isfinite(xa) & np.isfinite(aq)
        f[:, 2] = (_masked_ols_slope(xb, np.cumsum(bqz, 1), mb)
                   - _masked_ols_slope(xa, np.cumsum(aqz, 1), ma))
        # 3: microprice deviation (bps)
        q0 = bq[:, 0] + aq[:, 0]
        micro = (ap[:, 0] * bq[:, 0] + bp[:, 0] * aq[:, 0]) / np.where(q0 > 0, q0, np.nan)
        f[:, 3] = (micro - mid) / mid * 1e4
        # 4: depth-weighted spread (bps)
        sp = ap - bp
        wl = np.where(np.isfinite(sp), bqz + aqz, 0.0)
        wsum = wl.sum(1)
        f[:, 4] = (np.where(np.isfinite(sp), sp, 0.0) * wl).sum(1) \
            / np.where(wsum > 0, wsum, np.nan) / mid * 1e4
        # 5: 300s deep-imbalance momentum
        f[ROLL_S:, 5] = f[ROLL_S:, 0] - f[:-ROLL_S, 0]
        # 6: 300s realized vol of mid (per-second log-rets, trailing std, raw)
        r = np.diff(np.log(mid), prepend=np.nan)
        f[:, 6] = pd.Series(r).rolling(ROLL_S, min_periods=ROLL_S).std().to_numpy()
        # 7: 300s net deep-book delta (log-ratio of total 25-level depth)
        d = np.where(tot > 0, tot, np.nan)
        f[ROLL_S:, 7] = np.log(d[ROLL_S:] / d[:-ROLL_S])
    return f


# --------------------------------------------------------------------- build
def build_day(d: int, seq_dir: str = SEQ_DIR, out_dir: str = OUT_DIR,
              force: bool = False, verbose: bool = True):
    """Build <out_dir>/<d>.npz. Returns a stats dict (None if skipped)."""
    out = p.join(out_dir, f"{d}.npz")
    if (not force) and p.exists(out):
        return None
    t0 = time.time()
    seq = np.load(p.join(seq_dir, f"{d}.npz"))
    ts = seq["ts"].astype(np.int64)                       # (T,) ns, 1s grid
    grid_secs = ts // 1_000_000_000
    if not np.all(np.diff(grid_secs) == 1):
        raise ValueError(f"day {d}: seq_cache ts grid is not contiguous 1s")
    # extend ROLL_S seconds back so rolling features are formed at row 0
    ext_secs = np.arange(grid_secs[0] - ROLL_S, grid_secs[-1] + 1, dtype=np.int64)
    book = _load_book_1s(ext_secs)
    Z_ext = compute_state(book["bp"], book["bq"], book["ap"], book["aq"])
    Z_day = Z_ext[ROLL_S:]                                # back on the seq grid

    # panel pred-candidate grid — identical to build_feature_cache.py
    base = np.arange(0, ts.shape[0] - HORIZON, PRED_STRIDE)
    Zg = Z_day[base]
    finite_frac = np.isfinite(Zg).mean(axis=0)
    keep = np.isfinite(Zg).all(axis=1)
    Zo = Zg[keep]
    for j, (lo, hi) in enumerate(Z_CLIPS):
        Zo[:, j] = np.clip(Zo[:, j], lo, hi)
    ts_out = ts[base][keep]
    np.savez(out, ts=ts_out, Z=Zo.astype(np.float32), z_names=np.array(Z_NAMES))

    stats = {
        "day": d, "secs": time.time() - t0, "n_grid": int(base.shape[0]),
        "n_out": int(keep.sum()), "coverage": float(keep.mean()),
        "finite_frac": finite_frac, "Z": Zo,
        "ts_subset_ok": bool(np.isin(ts_out, ts).all()),
    }
    if verbose:
        print(f"  [day {d}] {stats['n_out']}/{stats['n_grid']} grid rows "
              f"({100*stats['coverage']:.2f}% coverage), "
              f"{stats['secs']:.1f}s", flush=True)
    return stats


def _print_validation(stats: dict):
    Z = stats["Z"]
    print(f"\n[validate] day {stats['day']}: n={stats['n_out']} "
          f"coverage={100*stats['coverage']:.2f}% "
          f"ts-subset-of-seq-grid={'OK' if stats['ts_subset_ok'] else 'FAIL'}")
    print(f"  {'feature':<20} {'finite%':>8} {'mean':>12} {'std':>12} "
          f"{'min':>12} {'max':>12}")
    for j, name in enumerate(Z_NAMES):
        col = Z[:, j]
        print(f"  {name:<20} {100*stats['finite_frac'][j]:>7.2f}% "
              f"{col.mean():>12.5g} {col.std():>12.5g} "
              f"{col.min():>12.5g} {col.max():>12.5g}")


def list_days(seq_dir: str = SEQ_DIR) -> list:
    return sorted(int(n[:-4]) for n in os.listdir(seq_dir)
                  if n.endswith(".npz") and n[:-4].isdigit())


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    g = ap.add_mutually_exclusive_group(required=True)
    g.add_argument("--days", type=int, nargs="+",
                   help="explicit YYYYMMDD trading days (validation mode: "
                        "prints per-feature stats + alignment + ETA)")
    g.add_argument("--all", action="store_true",
                   help="build every seq_cache day (batch mode)")
    ap.add_argument("--force", action="store_true",
                    help="rebuild day files that already exist")
    args = ap.parse_args()

    os.makedirs(OUT_DIR, exist_ok=True)
    all_days = list_days()
    days = args.days if args.days else all_days
    print(f"[btc25] {len(days)} day(s) -> {OUT_DIR}  "
          f"(grid: stride={PRED_STRIDE}s, horizon={HORIZON}s, roll={ROLL_S}s)",
          flush=True)

    t0 = time.time()
    n_done = n_skip = n_fail = 0
    per_day_secs = []
    for di, d in enumerate(days):
        try:
            st = build_day(d, force=args.force)
        except Exception as e:                       # missing/corrupt -> keep going
            n_fail += 1
            print(f"  [warn] day {d} failed: {e}", flush=True)
            continue
        if st is None:
            n_skip += 1
            continue
        n_done += 1
        per_day_secs.append(st["secs"])
        if args.days:
            _print_validation(st)
        elif n_done % 10 == 0 or di == len(days) - 1:
            el = time.time() - t0
            rate = n_done / el
            eta = (len(days) - di - 1) / rate if rate > 0 else 0
            print(f"  [{di+1:4d}/{len(days)}] built={n_done} skip={n_skip} "
                  f"fail={n_fail}  {el/60:.1f} min, ETA {eta/60:.1f} min",
                  flush=True)

    meta = {
        "source": BOOK25_ROOT,
        "n_days_built": n_done, "n_days_skipped": n_skip, "n_days_failed": n_fail,
        "pred_stride_s": PRED_STRIDE, "horizon_s": HORIZON, "roll_s": ROLL_S,
        "z_names": Z_NAMES, "z_clips": Z_CLIPS,
        "schema": {"ts": "(n,) int64 ns, exact subset of seq_cache ts",
                   "Z": "(n,8) f32 raw causal BTC 25-level state scalars"},
    }
    with open(p.join(OUT_DIR, "build_meta.json"), "w") as f:
        json.dump(meta, f, indent=2)

    el = time.time() - t0
    print(f"\n[btc25] done in {el/60:.1f} min: built={n_done} skip={n_skip} "
          f"fail={n_fail} -> {OUT_DIR}", flush=True)
    if per_day_secs:
        sec_day = float(np.mean(per_day_secs))
        print(f"[btc25] {sec_day:.1f} s/day -> estimated full build "
              f"({len(all_days)} days): {sec_day*len(all_days)/3600:.1f} h "
              f"(single process)", flush=True)


if __name__ == "__main__":
    main()
