"""Build TIME-VARYING (TV v2) feature overlay — extended with 6 low-vol regime channels.

Adds to existing 8 TV channels:
  Trade-derived (3):
    [8]  ofi_60s              — order flow imbalance (signed_vol / total_vol) EWMA 60s
    [9]  trade_rate_60s       — trades per second EWMA 60s (log1p normalized)
    [10] meta_run_buy_ratio   — fraction of buy trades in 60s window (0-1)
  Book-derived (3):
    [11] l1_size_imbalance_60s — (bid_amt_L1 - ask_amt_L1) EWMA 60s — quiet-market flow asymmetry
    [12] total_depth_log_60s   — log(total book depth) EWMA 60s — liquidity state regime
    [13] l5_dbps_diff_60s      — (ask_dbps_L5 - bid_dbps_L5) EWMA 60s — book shape change

Total K=14 channels (8 v1 + 6 v2).
Note: L0 bid/ask dbps are encoded relative to current mid → constant within sample, useless.
Spread/RV at L0 not viable from X_raw alone. Use L1+ levels + size dynamics instead.

Rationale (per overnight 2026-05-13 brief):
- V5 prod high-vol regime P=+0.091, low-vol P=+0.044
- Current 8 TV channels are all aggressive-flow biased → strong in high vol, weak in low vol
- New channels target microstructure state visible in quiet markets:
  - OFI ratio = scale-invariant flow direction (works even with low volume)
  - trade_rate / meta_run = trade-timing regime indicator
  - spread state = mostly fixed in liquid markets, deviations are informative
  - RV asymmetry = jump direction predictor (especially relevant in quiet regimes)
"""
from __future__ import annotations
import argparse
import concurrent.futures as cf
import io
import math
import pathlib
import subprocess
import time
import numpy as np
import pandas as pd

FEAT_NAMES = np.array([
    # v1 channels (unchanged order)
    "sv_ewm_60s", "sv_ewm_300s",
    "apb_60s", "apb_300s",
    "energy_skew", "ent_gap",
    "dva_L5_60s", "qd_severity",
    # v2 additions
    "ofi_60s", "trade_rate_60s", "meta_run_buy_ratio_60s",
    "l1_size_imbalance_60s", "total_depth_log_60s", "l5_dbps_diff_60s",
], dtype="<U24")

EPS = 1e-12


def read_trades_csv(path: pathlib.Path) -> pd.DataFrame:
    proc = subprocess.run(["gunzip", "-c", str(path)], capture_output=True, check=False)
    if proc.returncode != 0 and not proc.stdout:
        raise RuntimeError(f"gunzip failed: {path}")
    df = pd.read_csv(io.BytesIO(proc.stdout), usecols=["timestamp", "side", "price", "amount"])
    df["side_sign"] = np.where(df["side"].values == "buy", 1.0, -1.0).astype(np.float32)
    df["ts_s"] = (df["timestamp"].values // 1_000_000).astype(np.int64)
    return df.sort_values("ts_s").reset_index(drop=True)


def ewma_recursive(arr: np.ndarray, hl: float) -> np.ndarray:
    alpha = 1.0 - math.exp(-math.log(2.0) / hl)
    out = np.zeros_like(arr)
    cur = 0.0
    for i in range(len(arr)):
        cur = alpha * arr[i] + (1.0 - alpha) * cur
        out[i] = cur
    return out


def rolling_sum_1d(x: np.ndarray, w: int) -> np.ndarray:
    """Causal rolling sum window=w on 1D array. Returns same length."""
    cs = np.concatenate([[0.0], np.cumsum(x)])
    n = len(x)
    out = np.zeros(n)
    for t in range(n):
        s_lo = max(0, t - w + 1); s_hi = t + 1
        out[t] = cs[s_hi] - cs[s_lo]
    return out


def compute_book_tv_v1(X_raw_day: np.ndarray) -> np.ndarray:
    """V1 book channels: [energy_skew, ent_gap, dva_L5_60s, qd_severity]. Same as v1."""
    N, T, L, _ = X_raw_day.shape
    L10 = min(L, 10)
    bid_amt = X_raw_day[:, :, :L, 1].astype(np.float64)
    ask_amt = X_raw_day[:, :, :L, 3].astype(np.float64)
    bid_dbps = X_raw_day[:, :, :L, 0].astype(np.float64)
    ask_dbps = X_raw_day[:, :, :L, 2].astype(np.float64)

    decay_bps = 10.0
    w_bid = np.exp(-np.abs(bid_dbps) / decay_bps)
    w_ask = np.exp(-np.abs(ask_dbps) / decay_bps)
    bid_q = np.exp(bid_amt) - 1.0
    ask_q = np.exp(ask_amt) - 1.0
    E_bid_bar = (bid_q * w_bid).sum(axis=2) / (bid_q.sum(axis=2) + EPS)
    E_ask_bar = (ask_q * w_ask).sum(axis=2) / (ask_q.sum(axis=2) + EPS)
    energy_skew = E_ask_bar - E_bid_bar

    bid_q10 = bid_q[:, :, :L10]; ask_q10 = ask_q[:, :, :L10]
    s_b = bid_q10.sum(axis=2, keepdims=True) + EPS
    s_a = ask_q10.sum(axis=2, keepdims=True) + EPS
    p_b = np.clip(bid_q10 / s_b, EPS, 1.0)
    p_a = np.clip(ask_q10 / s_a, EPS, 1.0)
    H_b = -(p_b * np.log(p_b)).sum(axis=2) / math.log(L10)
    H_a = -(p_a * np.log(p_a)).sum(axis=2) / math.log(L10)
    ent_gap = H_a - H_b

    K = 5; Kuse = min(L, K)
    bid_q5 = bid_q[:, :, :Kuse]; ask_q5 = ask_q[:, :, :Kuse]
    win = 60
    dva = np.zeros((N, T))
    for n in range(N):
        for t in range(T):
            t_lo = max(0, t - win + 1); t_hi = t + 1
            n_w = t_hi - t_lo
            b_w = bid_q5[n, t_lo:t_hi, :]
            a_w = ask_q5[n, t_lo:t_hi, :]
            b_var = b_w.var(axis=0).sum() if n_w >= 2 else 0.0
            a_var = a_w.var(axis=0).sum() if n_w >= 2 else 0.0
            dva[n, t] = (b_var - a_var) / (b_var + a_var + EPS)

    bid_size = np.exp(bid_amt[:, :, 0]) - 1.0
    ask_size = np.exp(ask_amt[:, :, 0]) - 1.0
    qd_sev = np.zeros((N, T))
    for n in range(N):
        for t in range(T):
            t_lo = max(0, t - win + 1); t_hi = t + 1
            med_b = np.median(bid_size[n, t_lo:t_hi]) + EPS
            med_a = np.median(ask_size[n, t_lo:t_hi]) + EPS
            sev_b = np.clip(1.0 - bid_size[n, t] / med_b, 0.0, 1.0)
            sev_a = np.clip(1.0 - ask_size[n, t] / med_a, 0.0, 1.0)
            qd_sev[n, t] = sev_a - sev_b
    return np.stack([energy_skew, ent_gap, dva, qd_sev], axis=-1).astype(np.float32)


def compute_book_tv_v2(X_raw_day: np.ndarray) -> np.ndarray:
    """V2 book channels: [l1_size_imbalance_60s, total_depth_log_60s, l5_dbps_diff_60s].

    All EWMA HL=60s along time per sample. Returns (N, T, 3).

    Why these:
    - L1_size_imbalance: bid_amt_L1 - ask_amt_L1 varies per timestep (depth changes).
      In quiet markets, asymmetric L1 depth signals MM positioning / informed flow.
    - total_depth_log: sum of all log_amounts (bid+ask, all L). Liquidity regime indicator.
      Low total depth = thin market, high = deep market. Per-timestep variation.
    - l5_dbps_diff: ask_dbps_L5 - bid_dbps_L5. Book shape proxy — L5 prices shift as
      orders consume/refill, NOT constant per sample (vs L0 which is mid-relative const).
    """
    N, T, L, _ = X_raw_day.shape
    L1 = min(1, L - 1)
    L5_idx = min(5, L - 1)

    bid_amt = X_raw_day[:, :, :, 1].astype(np.float64)  # (N, T, L) log_amt
    ask_amt = X_raw_day[:, :, :, 3].astype(np.float64)
    bid_dbps = X_raw_day[:, :, :, 0].astype(np.float64)
    ask_dbps = X_raw_day[:, :, :, 2].astype(np.float64)

    # 1. L1 size imbalance (per timestep)
    l1_imb = bid_amt[:, :, L1] - ask_amt[:, :, L1]  # (N, T)
    # 2. total depth log (sum over levels, then log1p)
    total_depth = np.log1p(np.exp(bid_amt).sum(axis=2) + np.exp(ask_amt).sum(axis=2) - 2 * L)  # (N, T)
    # 3. l5 dbps diff (book shape at L5)
    l5_diff = ask_dbps[:, :, L5_idx] - bid_dbps[:, :, L5_idx]  # (N, T)

    # EWMA HL=60s along time axis
    alpha = 1.0 - math.exp(-math.log(2.0) / 60.0)
    out = np.zeros((N, T, 3))
    cur = np.stack([l1_imb[:, 0], total_depth[:, 0], l5_diff[:, 0]], axis=1)  # (N, 3)
    out[:, 0] = cur
    for t in range(1, T):
        cur = alpha * np.stack([l1_imb[:, t], total_depth[:, t], l5_diff[:, t]], axis=1) + (1.0 - alpha) * cur
        out[:, t] = cur
    return out.astype(np.float32)


def compute_trade_tv_v1(trades: pd.DataFrame, sample_ts_us: np.ndarray, T: int = 600) -> np.ndarray:
    """V1 trade channels: [sv_60, sv_300, apb_60, apb_300]. (N, T, 4). Same as v1."""
    N = len(sample_ts_us)
    if N == 0 or trades.empty:
        return np.zeros((N, T, 4), dtype=np.float32)

    sample_ts_s = (sample_ts_us // 1_000_000).astype(np.int64)
    min_ts_s = int(sample_ts_s.min()) - T - 10
    max_ts_s = int(sample_ts_s.max())
    span = max_ts_s - min_ts_s + 1

    sv = np.zeros(span); av = np.zeros(span)
    vnum = np.zeros(span); vden = np.zeros(span)
    in_range = (trades["ts_s"].values >= min_ts_s) & (trades["ts_s"].values <= max_ts_s)
    idx = (trades["ts_s"].values[in_range] - min_ts_s).astype(np.int64)
    ss = trades["side_sign"].values[in_range].astype(np.float64)
    amt = trades["amount"].values[in_range].astype(np.float64)
    prc = trades["price"].values[in_range].astype(np.float64)
    np.add.at(sv, idx, ss * amt)
    np.add.at(av, idx, amt)
    np.add.at(vnum, idx, prc * amt)

    sv_ewm_60_grid = ewma_recursive(sv, 60.0)
    sv_ewm_300_grid = ewma_recursive(sv, 300.0)
    vnum_cs = np.cumsum(vnum); vden_cs = np.cumsum(av)

    out = np.zeros((N, T, 4), dtype=np.float32)
    for s_i, t_s in enumerate(sample_ts_s):
        t_end = t_s - min_ts_s
        if t_end < T - 1: continue
        t_start = t_end - T + 1
        out[s_i, :, 0] = sv_ewm_60_grid[t_start:t_end + 1]
        out[s_i, :, 1] = sv_ewm_300_grid[t_start:t_end + 1]
        for w_i, w in enumerate([60, 300]):
            for t_off in range(T):
                t = t_start + t_off
                s_lo = max(0, t - w + 1); s_hi = t + 1
                num = vnum_cs[s_hi - 1] - (vnum_cs[s_lo - 1] if s_lo > 0 else 0.0)
                den = vden_cs[s_hi - 1] - (vden_cs[s_lo - 1] if s_lo > 0 else 0.0)
                vwap = num / max(den, 1e-9)
                mean_px = (vnum_cs[-1] / max(vden_cs[-1], 1e-9)) if vden_cs[-1] > 0 else 1.0
                log_r = np.log(max(vwap, 1e-9) / max(mean_px, 1e-9))
                z = max(-50.0, min(50.0, log_r * 1e4))
                out[s_i, t_off, 2 + w_i] = (1.0 / (1.0 + math.exp(-z)) - 0.5) * 2.0
    return out


def compute_trade_tv_v2(trades: pd.DataFrame, sample_ts_us: np.ndarray, T: int = 600) -> np.ndarray:
    """V2 trade channels: [ofi_60s, trade_rate_60s, meta_run_buy_ratio_60s]. (N, T, 3).

    Built on per-second grid:
    - ofi_60s: EWMA HL=60s of (signed_vol / (abs_vol + 1)) — scale-invariant flow direction
    - trade_rate_60s: log1p(EWMA HL=60s of trade count per second)
    - meta_run_buy_ratio_60s: fraction of trades same-side in 60s window
    """
    N = len(sample_ts_us)
    if N == 0:
        return np.zeros((N, T, 3), dtype=np.float32)
    sample_ts_s = (sample_ts_us // 1_000_000).astype(np.int64)
    min_ts_s = int(sample_ts_s.min()) - T - 10
    max_ts_s = int(sample_ts_s.max())
    span = max_ts_s - min_ts_s + 1

    sv = np.zeros(span); av = np.zeros(span)
    n_buy = np.zeros(span); n_total = np.zeros(span)
    if not trades.empty:
        in_range = (trades["ts_s"].values >= min_ts_s) & (trades["ts_s"].values <= max_ts_s)
        idx = (trades["ts_s"].values[in_range] - min_ts_s).astype(np.int64)
        ss = trades["side_sign"].values[in_range].astype(np.float64)
        amt = trades["amount"].values[in_range].astype(np.float64)
        np.add.at(sv, idx, ss * amt)
        np.add.at(av, idx, amt)
        np.add.at(n_buy, idx, (ss > 0).astype(np.float64))
        np.add.at(n_total, idx, 1.0)

    # OFI ratio (scale-invariant)
    ofi_ratio_per_s = sv / (av + 1.0)  # (span,) in (-1, 1)
    ofi_ewm = ewma_recursive(ofi_ratio_per_s, 60.0)

    # trade rate
    rate_ewm = ewma_recursive(n_total, 60.0)
    rate_log = np.log1p(rate_ewm)  # (span,)

    # meta-run buy ratio 60s window
    win = 60
    buy_cs = np.concatenate([[0.0], np.cumsum(n_buy)])
    tot_cs = np.concatenate([[0.0], np.cumsum(n_total)])
    buy_ratio = np.zeros(span)
    for t in range(span):
        s_lo = max(0, t - win + 1); s_hi = t + 1
        nb = buy_cs[s_hi] - buy_cs[s_lo]
        nt = tot_cs[s_hi] - tot_cs[s_lo]
        buy_ratio[t] = nb / nt if nt > 0 else 0.5  # 0.5 = neutral when no trades

    out = np.zeros((N, T, 3), dtype=np.float32)
    for s_i, t_s in enumerate(sample_ts_s):
        t_end = t_s - min_ts_s
        if t_end < T - 1: continue
        t_start = t_end - T + 1
        out[s_i, :, 0] = ofi_ewm[t_start:t_end + 1]
        out[s_i, :, 1] = rate_log[t_start:t_end + 1]
        out[s_i, :, 2] = buy_ratio[t_start:t_end + 1]
    return out


def process_day(date: str, v4_dir, trades_dir, out_dir, force=False):
    out_path = pathlib.Path(out_dir) / f"{date}.npz"
    if out_path.exists() and not force:
        return date, "skip"
    try:
        v4 = np.load(pathlib.Path(v4_dir) / f"{date}.npz", allow_pickle=True)
        X_raw = v4["X_raw"]  # (N, T, L, 4)
        ts = v4["timestamps"]  # (N,) us
        N, T, L, _ = X_raw.shape
        if N == 0:
            tv = np.zeros((0, T, 14), dtype=np.float32)
            np.savez_compressed(out_path, timestamps=ts, tv_feats=tv, feat_names=FEAT_NAMES)
            return date, "empty"

        # v1 book channels (4): [energy_skew, ent_gap, dva, qd_sev]
        book_v1 = compute_book_tv_v1(X_raw)  # (N, T, 4)
        # v2 book channels (3): [l1_imb, total_depth, l5_diff]
        book_v2 = compute_book_tv_v2(X_raw)  # (N, T, 3)

        # Trade channels: load CSV — try both layouts
        trade_csv = pathlib.Path(trades_dir) / f"BTCUSDT-trades-{date}.csv.gz"
        if not trade_csv.exists():
            trade_csv = pathlib.Path(trades_dir) / date / "BTCUSDT.csv.gz"
        if trade_csv.exists():
            trades = read_trades_csv(trade_csv)
        else:
            trades = pd.DataFrame(columns=["timestamp", "side", "price", "amount", "side_sign", "ts_s"])
        trade_v1 = compute_trade_tv_v1(trades, ts, T=T)  # (N, T, 4): sv_60, sv_300, apb_60, apb_300
        trade_v2 = compute_trade_tv_v2(trades, ts, T=T)  # (N, T, 3): ofi, rate, meta_buy

        # Stack in FEAT_NAMES order:
        # [0]sv_60 [1]sv_300 [2]apb_60 [3]apb_300 [4]energy [5]ent [6]dva [7]qd
        # [8]ofi [9]rate [10]meta_buy [11]l1_imb [12]total_depth [13]l5_diff
        tv = np.concatenate([
            trade_v1[:, :, 0:2],  # sv_60, sv_300
            trade_v1[:, :, 2:4],  # apb_60, apb_300
            book_v1,              # energy, ent, dva, qd
            trade_v2,             # ofi, rate, meta_buy
            book_v2,              # l1_imb, total_depth, l5_diff
        ], axis=-1).astype(np.float32)  # (N, T, 14)

        np.savez_compressed(out_path, timestamps=ts, tv_feats=tv, feat_names=FEAT_NAMES)
        return date, f"ok N={N}"
    except Exception as e:
        return date, f"err: {e}"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--v4-dir", default="data/npz_v4")
    ap.add_argument("--trades-dir", default="data/crypto_data/trades_btc_perp")
    ap.add_argument("--out-dir", default="data/npz_v4_tv_overlay_v2")
    ap.add_argument("--dates", nargs="*", default=None, help="If given, only process these dates")
    ap.add_argument("--workers", type=int, default=4)
    ap.add_argument("--force", action="store_true")
    args = ap.parse_args()

    out_dir = pathlib.Path(args.out_dir); out_dir.mkdir(parents=True, exist_ok=True)
    v4_dir = pathlib.Path(args.v4_dir)

    if args.dates:
        dates = args.dates
    else:
        dates = sorted([p.stem for p in v4_dir.glob("*.npz")])

    print(f"Processing {len(dates)} days → {out_dir}")
    t0 = time.time()
    if args.workers <= 1:
        for d in dates:
            r = process_day(d, args.v4_dir, args.trades_dir, args.out_dir, args.force)
            print(f"  {r[0]}: {r[1]}")
    else:
        with cf.ProcessPoolExecutor(max_workers=args.workers) as ex:
            futs = [ex.submit(process_day, d, args.v4_dir, args.trades_dir, args.out_dir, args.force) for d in dates]
            for i, f in enumerate(cf.as_completed(futs)):
                r = f.result()
                if i % 50 == 0 or "err" in r[1]:
                    print(f"  [{i+1}/{len(dates)}] {r[0]}: {r[1]} ({time.time()-t0:.0f}s)")
    print(f"Done in {time.time()-t0:.0f}s")


if __name__ == "__main__":
    main()
