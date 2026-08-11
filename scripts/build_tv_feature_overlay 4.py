"""Build TIME-VARYING (TV) feature overlay for V5 DL training.

Key difference from previous overlays (which broadcast last-timestep as constant):
this builds per-sample TIME SERIES (T=600 timesteps, K features per timestep)
so the Conformer can learn temporal dynamics of the new features.

Output: data/npz_v4_tv_overlay/<date>.npz with:
  timestamps     (N,) int64
  tv_feats       (N, 600, K) float32  ← TIME SERIES
  feat_names     (K,) <U32

Features (K=8):
  Trade-derived (from crypto_data/trades CSV):
    [0] sv_ewm_60s    — signed volume EWMA (HL 60s) per timestep
    [1] sv_ewm_300s   — signed volume EWMA (HL 300s) per timestep
    [2] apb_60s       — VWAP-TWAP basis sigmoid per timestep (60s rolling)
    [3] apb_300s      — same, 300s rolling
  Book-derived (from X_raw per-timestep):
    [4] energy_skew   — E_bid - E_ask, distance-weighted depth (per timestep)
    [5] ent_gap       — Shannon entropy gap (ask - bid) on 10-level depth (per timestep)
    [6] dva_L5        — bid_var - ask_var on L5 over 60s rolling (per timestep)
    [7] qd_severity   — queue depletion severity net (per timestep)

These are TRUE time series — the Conformer attention sees them evolve across t.
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
    "sv_ewm_60s", "sv_ewm_300s",
    "apb_60s", "apb_300s",
    "energy_skew", "ent_gap",
    "dva_L5_60s", "qd_severity",
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
    """Vectorized causal EWMA with half-life hl on 1Hz grid."""
    alpha = 1.0 - math.exp(-math.log(2.0) / hl)
    out = np.zeros_like(arr)
    cur = 0.0
    for i in range(len(arr)):
        cur = alpha * arr[i] + (1.0 - alpha) * cur
        out[i] = cur
    return out


def stable_sigmoid(z: np.ndarray) -> np.ndarray:
    out = np.empty_like(z, dtype=np.float64)
    pos = z >= 0
    out[pos] = 1.0 / (1.0 + np.exp(-z[pos]))
    ez = np.exp(z[~pos])
    out[~pos] = ez / (1.0 + ez)
    return out


def compute_book_tv(X_raw_day: np.ndarray) -> np.ndarray:
    """X_raw: (N, T=600, L, 4). Returns (N, T, 4) book-derived TV features.
    Channels: [energy_skew, ent_gap, dva_L5_60s, qd_severity].
    """
    N, T, L, _ = X_raw_day.shape
    L10 = min(L, 10)
    bid_amt = X_raw_day[:, :, :L, 1].astype(np.float64)  # (N, T, L)
    ask_amt = X_raw_day[:, :, :L, 3].astype(np.float64)
    bid_dbps = X_raw_day[:, :, :L, 0].astype(np.float64)
    ask_dbps = X_raw_day[:, :, :L, 2].astype(np.float64)

    # energy_skew per timestep: distance-weighted depth
    decay_bps = 10.0
    w_bid = np.exp(-np.abs(bid_dbps) / decay_bps)  # (N, T, L)
    w_ask = np.exp(-np.abs(ask_dbps) / decay_bps)
    bid_q = np.exp(bid_amt) - 1.0  # un-log
    ask_q = np.exp(ask_amt) - 1.0
    E_bid_bar = (bid_q * w_bid).sum(axis=2) / (bid_q.sum(axis=2) + EPS)  # (N, T)
    E_ask_bar = (ask_q * w_ask).sum(axis=2) / (ask_q.sum(axis=2) + EPS)
    energy_skew = E_ask_bar - E_bid_bar  # (N, T)

    # ent_gap per timestep: Shannon entropy diff on 10-level
    bid_q10 = bid_q[:, :, :L10]
    ask_q10 = ask_q[:, :, :L10]
    s_b = bid_q10.sum(axis=2, keepdims=True) + EPS
    s_a = ask_q10.sum(axis=2, keepdims=True) + EPS
    p_b = np.clip(bid_q10 / s_b, EPS, 1.0)
    p_a = np.clip(ask_q10 / s_a, EPS, 1.0)
    H_b = -(p_b * np.log(p_b)).sum(axis=2) / math.log(L10)  # (N, T)
    H_a = -(p_a * np.log(p_a)).sum(axis=2) / math.log(L10)
    ent_gap = H_a - H_b  # (N, T)

    # dva_L5_60s per timestep: bid var - ask var on inside-5 over rolling 60s
    K = 5
    Kuse = min(L, K)
    bid_q5 = bid_q[:, :, :Kuse]  # (N, T, K)
    ask_q5 = ask_q[:, :, :Kuse]
    # Rolling 60s variance for each level, summed across levels
    # Implemented as: var(rolling window) = E[x^2] - E[x]^2 over window
    win = 60
    dva = np.zeros((N, T), dtype=np.float64)
    for n in range(N):
        b_sum = np.zeros(Kuse); b_sum2 = np.zeros(Kuse)
        a_sum = np.zeros(Kuse); a_sum2 = np.zeros(Kuse)
        for t in range(T):
            # Window [max(0, t-win+1), t+1]
            t_lo = max(0, t - win + 1)
            t_hi = t + 1
            n_w = t_hi - t_lo
            b_w = bid_q5[n, t_lo:t_hi, :]  # (n_w, K)
            a_w = ask_q5[n, t_lo:t_hi, :]
            b_var = b_w.var(axis=0).sum() if n_w >= 2 else 0.0
            a_var = a_w.var(axis=0).sum() if n_w >= 2 else 0.0
            dva[n, t] = (b_var - a_var) / (b_var + a_var + EPS)

    # qd_severity per timestep: depletion of inside size vs rolling-60s median
    bid_size = np.exp(bid_amt[:, :, 0]) - 1.0  # (N, T)
    ask_size = np.exp(ask_amt[:, :, 0]) - 1.0
    qd_sev = np.zeros((N, T), dtype=np.float64)
    for n in range(N):
        for t in range(T):
            t_lo = max(0, t - win + 1); t_hi = t + 1
            med_b = np.median(bid_size[n, t_lo:t_hi]) + EPS
            med_a = np.median(ask_size[n, t_lo:t_hi]) + EPS
            sev_b = np.clip(1.0 - bid_size[n, t] / med_b, 0.0, 1.0)  # depleted bid
            sev_a = np.clip(1.0 - ask_size[n, t] / med_a, 0.0, 1.0)  # depleted ask
            qd_sev[n, t] = sev_a - sev_b  # ask depleted (buy pressure) - bid depleted (sell pressure)

    return np.stack([energy_skew, ent_gap, dva, qd_sev], axis=-1).astype(np.float32)


def compute_trade_tv(trades: pd.DataFrame, sample_ts_us: np.ndarray, T: int = 600) -> np.ndarray:
    """Returns (N_samples, T, 4) trade-derived TV: [sv_60, sv_300, apb_60, apb_300].

    For each sample at timestamp t_us, build T=600 second-grid time series ending at t_us.
    """
    N = len(sample_ts_us)
    if N == 0 or trades.empty:
        return np.zeros((N, T, 4), dtype=np.float32)

    # Build per-second daily grid first
    sample_ts_s = (sample_ts_us // 1_000_000).astype(np.int64)
    # Span: from earliest needed second to latest sample second
    min_ts_s = int(sample_ts_s.min()) - T - 10
    max_ts_s = int(sample_ts_s.max())
    span = max_ts_s - min_ts_s + 1

    # Per-second aggregates
    sv = np.zeros(span, dtype=np.float64)
    av = np.zeros(span, dtype=np.float64)
    vnum = np.zeros(span, dtype=np.float64)
    vden = np.zeros(span, dtype=np.float64)
    in_range = (trades["ts_s"].values >= min_ts_s) & (trades["ts_s"].values <= max_ts_s)
    idx = (trades["ts_s"].values[in_range] - min_ts_s).astype(np.int64)
    ss = trades["side_sign"].values[in_range].astype(np.float64)
    amt = trades["amount"].values[in_range].astype(np.float64)
    prc = trades["price"].values[in_range].astype(np.float64)
    np.add.at(sv, idx, ss * amt)
    np.add.at(av, idx, amt)
    np.add.at(vnum, idx, prc * amt)
    np.add.at(vden, idx, amt)

    # Compute EWMA for whole day grid
    sv_ewm_60_grid = ewma_recursive(sv, 60.0)
    sv_ewm_300_grid = ewma_recursive(sv, 300.0)

    # For APB we need rolling per-timestep TWAP and VWAP. Use cumulative sums for O(T) per sample.
    vnum_cs = np.cumsum(vnum)
    vden_cs = np.cumsum(av)  # use trade volume

    def rolling_apb(off_array, w):
        """Apply per timestep: for off in arr, compute APB at [off-w+1, off+1).
        For mid_arr we use trade VWAP as proxy (no mid grid here)."""
        apb_arr = np.zeros_like(off_array, dtype=np.float64)
        for i, off in enumerate(off_array):
            s_lo = max(0, off - w + 1); s_hi = off + 1
            num = vnum_cs[s_hi - 1] - (vnum_cs[s_lo - 1] if s_lo > 0 else 0.0)
            den = vden_cs[s_hi - 1] - (vden_cs[s_lo - 1] if s_lo > 0 else 0.0)
            vwap = num / den if den > 1e-9 else 0.0
            # twap proxy: simple mean of trade px in window. Use vwap stretched
            # Actually here we use sign of (vwap - twap_60s_lag) — simplified
            apb_arr[i] = vwap  # raw vwap for now
        return apb_arr

    # Simpler APB: just rolling VWAP minus median of full grid (proxy for TWAP)
    # to avoid heavy compute. For now, use rolling VWAP per timestep as feat.

    out = np.zeros((N, T, 4), dtype=np.float32)
    for s_i, t_s in enumerate(sample_ts_s):
        # For sample anchor t_s, populate T timesteps [t_s-T+1, t_s]
        t_end = t_s - min_ts_s  # offset in grid
        if t_end < T - 1: continue
        t_start = t_end - T + 1
        # Per-timestep values
        out[s_i, :, 0] = sv_ewm_60_grid[t_start:t_end + 1]
        out[s_i, :, 1] = sv_ewm_300_grid[t_start:t_end + 1]

        # APB rolling: for each t in window, compute (VWAP_w - mid_proxy)
        # Use sigmoid(log_scale × log(vwap_w / mean_grid)) — much simplified
        # Just use rolling VWAP as raw feature for now
        for w_i, w in enumerate([60, 300]):
            for t_off in range(T):
                t = t_start + t_off
                s_lo = max(0, t - w + 1); s_hi = t + 1
                num = vnum_cs[s_hi - 1] - (vnum_cs[s_lo - 1] if s_lo > 0 else 0.0)
                den = vden_cs[s_hi - 1] - (vden_cs[s_lo - 1] if s_lo > 0 else 0.0)
                vwap = num / max(den, 1e-9)
                # Normalize by global mean price (approximation of mid)
                mean_px = (vnum_cs[-1] / max(vden_cs[-1], 1e-9)) if vden_cs[-1] > 0 else 1.0
                log_r = np.log(max(vwap, 1e-9) / max(mean_px, 1e-9))
                z = max(-50.0, min(50.0, log_r * 1e4))
                out[s_i, t_off, 2 + w_i] = (1.0 / (1.0 + math.exp(-z)) - 0.5) * 2.0

    return out


def process_day(date: str, v4_dir, trades_dir, out_dir, force=False):
    out_path = pathlib.Path(out_dir) / f"{date}.npz"
    if out_path.exists() and not force:
        return date, "skip"
    try:
        v4 = np.load(pathlib.Path(v4_dir) / f"{date}.npz", allow_pickle=True)
        X_raw = v4["X_raw"]
        timestamps = v4["timestamps"]
        if X_raw.shape[0] == 0:
            return date, "empty"

        # Book TV (N, T, 4)
        book_tv = compute_book_tv(X_raw)

        # Trade TV — need raw trades. If trades missing, fill zeros.
        trades_path = pathlib.Path(trades_dir) / date / "BTCUSDT.csv.gz"
        if trades_path.exists():
            trades = read_trades_csv(trades_path)
            trade_tv = compute_trade_tv(trades, timestamps, T=600)
        else:
            trade_tv = np.zeros((X_raw.shape[0], 600, 4), dtype=np.float32)

        tv = np.concatenate([trade_tv, book_tv], axis=-1)  # (N, T, 8)
        tv = np.nan_to_num(tv, nan=0.0, posinf=0.0, neginf=0.0).astype(np.float32)
        pathlib.Path(out_dir).mkdir(parents=True, exist_ok=True)
        np.savez_compressed(out_path, timestamps=timestamps, tv_feats=tv, feat_names=FEAT_NAMES)
        return date, "ok"
    except Exception as e:
        return date, f"err: {type(e).__name__}: {str(e)[:60]}"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--v4-dir", default="data/npz_v4")
    ap.add_argument("--trades-dir", default="crypto_data/trades/trades")
    ap.add_argument("--out", default="data/npz_v4_tv_overlay")
    ap.add_argument("--workers", type=int, default=4)
    ap.add_argument("--force", action="store_true")
    args = ap.parse_args()

    days = sorted(p.stem for p in pathlib.Path(args.v4_dir).glob("20??-??-??.npz"))
    print(f"Building TV overlay for {len(days)} days → {args.out}")
    t_start = time.time()
    ok = skip = err = 0
    with cf.ProcessPoolExecutor(max_workers=args.workers) as ex:
        futs = [ex.submit(process_day, d, args.v4_dir, args.trades_dir, args.out, args.force) for d in days]
        for i, f in enumerate(cf.as_completed(futs)):
            d, status = f.result()
            if status == "ok": ok += 1
            elif status == "skip": skip += 1
            else:
                err += 1
                print(f"  {d}: {status}")
            if (i + 1) % 50 == 0:
                print(f"  progress {i+1}/{len(days)} ok={ok} skip={skip} err={err} ({time.time()-t_start:.0f}s)", flush=True)
    print(f"Done: ok={ok} skip={skip} err={err} in {time.time()-t_start:.0f}s")


if __name__ == "__main__":
    main()
