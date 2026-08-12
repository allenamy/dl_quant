"""Build trade-flow overlay NPZs with signed-volume-imbalance + VWAP-drift
features computed from BTCUSDT trades gzipped CSVs.

For each V4 NPZ window at timestamp `t` (end of 600-step window), compute:
  sv_60    = sum(side * amount) over [t-60, t] seconds
  sv_300   = ...over [t-300, t]
  sv_1800  = ...over [t-1800, t]
  vwap_drift_300 = (mid[t] - vwap_300) / mid[t]
  trade_intensity_300 = trade_count / 300

Side is mapped buy→+1, sell→-1. Amount in base currency (BTC). Everything
strictly uses past+current data relative to the anchor timestamp — zero
lookahead.

Output: data/npz_v4_tradeflow/<date>.npz with:
  timestamps        (N,) int64 (pass-through for alignment verification)
  trade_feats       (N, 5) float32
  feat_names        (5,) <U20
"""
from __future__ import annotations

import argparse
import concurrent.futures as cf
import gzip
import io
import subprocess
import time
from pathlib import Path

import numpy as np
import pandas as pd


FEAT_NAMES = np.array([
    "tf_sv_60", "tf_sv_300", "tf_sv_1800", "tf_vwap_drift_300", "tf_trade_intensity_300",
], dtype="<U24")


def read_trades_csv(path: Path) -> pd.DataFrame:
    """Read gzipped trades CSV via subprocess gunzip to tolerate truncated CRC.

    Returns DataFrame with columns ts_us (int64), side (+1 buy / -1 sell),
    price (float64), amount (float64).
    """
    proc = subprocess.run(
        ["gunzip", "-c", str(path)],
        capture_output=True, check=False,
    )
    if proc.returncode != 0 and not proc.stdout:
        raise RuntimeError(f"gunzip failed for {path}: {proc.stderr[:200]}")
    df = pd.read_csv(io.BytesIO(proc.stdout), usecols=["timestamp", "side", "price", "amount"])
    df["side_sign"] = np.where(df["side"].values == "buy", 1.0, -1.0).astype(np.float32)
    df = df.rename(columns={"timestamp": "ts_us"})
    df["ts_s"] = (df["ts_us"].values // 1_000_000).astype(np.int64)
    df["amount"] = df["amount"].astype(np.float32)
    df["price"] = df["price"].astype(np.float64)
    return df[["ts_s", "side_sign", "price", "amount"]].sort_values("ts_s").reset_index(drop=True)


def compute_trade_features(
    v4_npz: dict,
    trades: pd.DataFrame,
    mid_ts: np.ndarray,
    mid_grid: np.ndarray,
) -> np.ndarray:
    """Vectorized per-second-bucket trade flow computation, then per-sample
    windowed sums via cumsum.

    Returns (N, 5) float32 feature matrix.
    """
    timestamps_us = v4_npz["timestamps"].astype(np.int64)
    N = len(timestamps_us)
    if N == 0:
        return np.zeros((0, 5), dtype=np.float32)

    # Per-second bucket aggregates
    t0 = int(trades["ts_s"].min()) if len(trades) else 0
    t1 = int(trades["ts_s"].max()) + 1 if len(trades) else 1
    # Anchor grid to midprice grid for alignment
    grid_start = int(mid_ts[0]) if len(mid_ts) else t0
    grid_end = int(mid_ts[-1]) + 1 if len(mid_ts) else t1
    span = grid_end - grid_start
    if span <= 0 or span > 3 * 86400:
        return np.zeros((N, 5), dtype=np.float32)

    signed_vol = np.zeros(span, dtype=np.float64)
    vwap_num = np.zeros(span, dtype=np.float64)
    vwap_den = np.zeros(span, dtype=np.float64)
    trade_count = np.zeros(span, dtype=np.int32)

    if len(trades) > 0:
        idx = trades["ts_s"].values - grid_start
        in_range = (idx >= 0) & (idx < span)
        if in_range.any():
            idx = idx[in_range]
            ss = trades["side_sign"].values[in_range]
            amt = trades["amount"].values[in_range]
            prc = trades["price"].values[in_range]
            np.add.at(signed_vol, idx, ss * amt)
            np.add.at(vwap_num, idx, prc * amt)
            np.add.at(vwap_den, idx, amt)
            np.add.at(trade_count, idx, 1)

    # Cumulative sums for O(1) rolling window
    sv_cs = np.cumsum(signed_vol)
    vnum_cs = np.cumsum(vwap_num)
    vden_cs = np.cumsum(vwap_den)
    tc_cs = np.cumsum(trade_count, dtype=np.int64)

    def _rs(cs, s, e):  # rolling sum on [s, e)
        sc = cs[s - 1] if s > 0 else 0
        return float(cs[e - 1] - sc) if e > s else 0.0

    sample_ts_s = timestamps_us // 1_000_000
    offsets = sample_ts_s - grid_start  # (N,)

    feats = np.zeros((N, 5), dtype=np.float64)
    for i in range(N):
        off = int(offsets[i])
        if off < 0 or off >= span:
            continue
        # Windows use [off - S, off] inclusive => slice [off-S, off+1)
        for j, S in enumerate((60, 300, 1800)):
            s_lo = max(0, off - S)
            s_hi = off + 1
            feats[i, j] = _rs(sv_cs, s_lo, s_hi)

        s_lo = max(0, off - 300)
        s_hi = off + 1
        num = _rs(vnum_cs, s_lo, s_hi)
        den = _rs(vden_cs, s_lo, s_hi)
        cnt = tc_cs[s_hi - 1] - (tc_cs[s_lo - 1] if s_lo > 0 else 0) if s_hi > s_lo else 0
        vwap_300 = num / den if den > 1e-9 else 0.0
        mid_now = float(mid_grid[off]) if off < len(mid_grid) and np.isfinite(mid_grid[off]) else 0.0
        if vwap_300 > 0 and mid_now > 0:
            feats[i, 3] = (mid_now - vwap_300) / mid_now
        feats[i, 4] = cnt / 300.0

    return np.nan_to_num(feats.astype(np.float32), nan=0.0, posinf=10.0, neginf=-10.0)


def process_day(
    date_name: str,
    v4_dir: Path,
    trades_dir: Path,
    midprice_dir: Path,
    out_dir: Path,
) -> tuple[str, float, str]:
    t0 = time.time()
    try:
        v4_path = v4_dir / f"{date_name}.npz"
        trades_path = trades_dir / date_name / "BTCUSDT.csv.gz"
        mid_path = midprice_dir / f"{date_name}.npz"
        out_path = out_dir / f"{date_name}.npz"

        if not v4_path.exists() or not trades_path.exists() or not mid_path.exists():
            return (date_name, 0.0, "MISSING")
        if out_path.exists():
            return (date_name, 0.0, "SKIP")

        v4 = np.load(str(v4_path), allow_pickle=True)
        mid = np.load(str(mid_path), allow_pickle=True)

        # Build midprice grid same way as long_context overlay
        mid_ts_all = mid["timestamps_s"].astype(np.int64)
        mid_prc = mid["mid_price"].astype(np.float64)
        order_valid = np.zeros(len(mid_ts_all), dtype=bool)
        cur_max = -1
        for i, t in enumerate(mid_ts_all):
            if t >= cur_max:
                order_valid[i] = True
                cur_max = t
        mid_ts_all = mid_ts_all[order_valid]
        mid_prc = mid_prc[order_valid]
        if len(mid_ts_all) < 2:
            return (date_name, time.time() - t0, "NO_MID")
        t_start = int(mid_ts_all[0])
        t_end = int(mid_ts_all[-1]) + 1
        span = t_end - t_start
        if span <= 0 or span > 3 * 86400:
            return (date_name, time.time() - t0, "BAD_SPAN")
        mid_grid = np.full(span, np.nan, dtype=np.float64)
        offs = mid_ts_all - t_start
        in_range = (offs >= 0) & (offs < span)
        mid_grid[offs[in_range]] = mid_prc[in_range]
        mid_grid = pd.Series(mid_grid).ffill(limit=60).to_numpy()
        mid_ts = np.arange(t_start, t_end, dtype=np.int64)

        trades = read_trades_csv(trades_path)
        feats = compute_trade_features(v4, trades, mid_ts, mid_grid)

        out_dir.mkdir(parents=True, exist_ok=True)
        np.savez_compressed(
            str(out_path),
            timestamps=v4["timestamps"],
            trade_feats=feats,
            feat_names=FEAT_NAMES,
        )
        n_nonzero = int((np.abs(feats).sum(axis=1) > 0).sum())
        return (date_name, time.time() - t0, f"OK valid={n_nonzero}/{len(feats)}")
    except Exception as e:
        return (date_name, time.time() - t0, f"ERR: {type(e).__name__}: {str(e)[:100]}")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--v4-dir", default="data/npz_v4")
    ap.add_argument("--trades-dir", default="crypto_data/trades/trades")
    ap.add_argument("--midprice-dir", default="data/midprice_per_day")
    ap.add_argument("--out-dir", default="data/npz_v4_tradeflow")
    ap.add_argument("--workers", type=int, default=6)
    ap.add_argument("--dates", nargs="*", default=None, help="specific dates (YYYY-MM-DD); default: all from midprice_dir")
    args = ap.parse_args()

    v4_dir = Path(args.v4_dir)
    trades_dir = Path(args.trades_dir)
    mid_dir = Path(args.midprice_dir)
    out_dir = Path(args.out_dir)

    dates = args.dates or sorted(p.stem for p in mid_dir.glob("*.npz"))
    print(f"Processing {len(dates)} days from {v4_dir} + {trades_dir} + {mid_dir} → {out_dir}")

    def _wrap(d):
        return process_day(d, v4_dir, trades_dir, mid_dir, out_dir)

    with cf.ThreadPoolExecutor(max_workers=args.workers) as ex:
        results = list(ex.map(_wrap, dates))

    ok = [r for r in results if r[2].startswith("OK")]
    skip = [r for r in results if r[2] == "SKIP"]
    err = [r for r in results if not r[2].startswith("OK") and r[2] != "SKIP"]
    total = sum(r[1] for r in results)
    print(f"OK={len(ok)} SKIP={len(skip)} ERR={len(err)} wall_s={total:.1f}")
    for n, _, s in err[:15]:
        print(f"  {n}: {s}")


if __name__ == "__main__":
    main()
