"""Causal trailing rolling-RANK overlay for the drift-OOD X channels (feature-drift audit, gap #7).

Replaces each selected channel's value by its causal trailing-3d PERCENTILE in [-1,1] (stationary by
construction, regardless of level/scale drift). The reference for a window ending at ts_n is the
channel's recent marginal — the last-timestep values of all windows with ts in [ts_n-3d, ts_n]
(strictly <=t => causal). All 600 timesteps of the window are ranked against that reference.

MODES:
  full_x : write a full npz_v2arch_rank/<day>.npz (all keys copied; X[:,:,SEL] rank-transformed) —
           config-only apples-to-apples training (requires the RevIN-bypass model flag for SEL, else
           RevIN washes the rank out: within-window corr(RevIN(raw),RevIN(rank))=0.85-0.98).
  prior  : write a small sidecar npz_v2arch_rank_prior/<day>.npz with X_rank_last (N,len(SEL)) =
           the last-timestep rank per selected channel (a regime-state descriptor; feed via the
           state_prior/FiLM path which already bypasses RevIN).

DISK-SAFE: reads --src mode implicit r; writes --dst. Processes days in time order with a trailing
buffer so each day only needs a 3d warmup. --self-test runs causality + truncation-invariance checks.

Run on SERVER:
  conda run -n hsy_v5push python multi_asset/data/build_rank_overlay.py \
    --src npz_v2arch --dst npz_v2arch_rank --mode full_x \
    --start 2024-08-25 --end 2026-05-07 --window-days 3
"""
from __future__ import annotations
import numpy as np, glob, os, argparse, json
from datetime import datetime, timezone, timedelta

# 34 drift-PSI>0.1 channels (x_mid_ratio_log dropped as redundant with x_basis_bps). Frozen from
# exports/feature_drift_audit.csv (2026-07-03).
SEL_DEFAULT = [3,10,11,12,13,15,16,19,20,21,22,23,26,27,28,29,30,31,32,33,34,35,49,50,51,52,57,
               70,71,72,75,81,82,83]
DAY_US = 86_400_000_000
MIN_REF = 300                    # min reference size to rank; else leave raw (warmup fallback)


def _daterange(s, e):
    d0 = datetime.strptime(s, "%Y-%m-%d").replace(tzinfo=timezone.utc)
    d1 = datetime.strptime(e, "%Y-%m-%d").replace(tzinfo=timezone.utc)
    d = d0
    while d <= d1:
        yield d.strftime("%Y-%m-%d"); d += timedelta(days=1)


def rank_day(X, ts_us, sel, buf_ts, buf_vals, win_us):
    """Rank the selected channels of one day's X (N,600,C) against the trailing buffer.
    buf_ts (M,), buf_vals (M,len(sel)) are time-ordered last-ts values of PRIOR windows (<= each ts).
    Returns rank_X (N,600,len(sel)) in [-1,1], and the day's own last-ts values to append to the buffer.
    Causal: window n uses only buffer entries with ts <= ts_n."""
    N, L, _ = X.shape
    Xsel = X[:, :, sel].astype(np.float64)                  # (N,600,S)
    last_vals = Xsel[:, -1, :]                               # (N,S) current-state values
    out = np.empty((N, L, len(sel)), np.float32)
    # merge prior buffer with same-day earlier windows incrementally (time order within day assumed)
    order = np.argsort(ts_us)
    cur_ts = list(buf_ts); cur_vals = [buf_vals] if len(buf_vals) else []
    all_ts = np.array(buf_ts, np.int64)
    all_vals = buf_vals if len(buf_vals) else np.zeros((0, len(sel)))
    for oi in order:
        t_n = ts_us[oi]
        lo = np.searchsorted(all_ts, t_n - win_us, side="left")
        ref = all_vals[lo:]                                 # (K,S) trailing-3d, ts<=t_n by construction
        if len(ref) >= MIN_REF:
            rs = np.sort(ref, axis=0)                       # (K,S)
            for j in range(len(sel)):
                pos = np.searchsorted(rs[:, j], Xsel[oi, :, j])
                out[oi, :, j] = (pos / len(rs) * 2.0 - 1.0)
        else:
            out[oi] = np.nan                                 # warmup (ref<MIN_REF) -> caller keeps raw / sets 0
        # append this window's last-ts value to the running buffer (so later same-day windows see it)
        all_ts = np.append(all_ts, t_n)
        all_vals = np.vstack([all_vals, last_vals[oi:oi+1]])
    return out, ts_us, last_vals


def process_range(src, dst, sel, start, end, mode, win_days):
    win_us = win_days * DAY_US
    os.makedirs(dst, exist_ok=True)
    days = [d for d in _daterange(start, end) if os.path.exists(f"data/{src}/{d}.npz")]
    print(f"build_rank_overlay: {len(days)} days {start}..{end} mode={mode} win={win_days}d "
          f"sel={len(sel)}ch -> data/{dst}", flush=True)
    buf_ts = np.zeros(0, np.int64); buf_vals = np.zeros((0, len(sel)))
    for di, d in enumerate(days):
        z = dict(np.load(f"data/{src}/{d}.npz", allow_pickle=True))
        X = z["X"]; ts = z["timestamps"].astype(np.int64)
        rank, day_ts, day_last = rank_day(X, ts, sel, buf_ts, buf_vals, win_us)
        warm = np.isnan(rank).any(axis=(1, 2))               # windows without enough reference
        if mode == "full_x":
            Xnew = X.astype(np.float32).copy()
            good = ~warm
            for c_i, c in enumerate(sel):
                Xnew[good, :, c] = rank[good, :, c_i].astype(np.float32)   # warmup windows keep raw
            z["X"] = Xnew
            z["rank_channels"] = np.array(sel)
            _save(f"data/{dst}/{d}.npz", z)
        else:  # prior sidecar: last-ts rank per selected channel (regime-state descriptor)
            last_rank = rank[:, -1, :]                        # (N,S)
            last_rank[warm] = 0.0
            _save(f"data/{dst}/{d}.npz", {"X_rank_last": last_rank.astype(np.float32),
                                          "timestamps": day_ts.astype(np.int64),
                                          "rank_channels": np.array(sel)})
        # update buffer, prune to trailing win + a margin
        buf_ts = np.append(buf_ts, day_ts); buf_vals = np.vstack([buf_vals, day_last])
        keep = buf_ts >= buf_ts.max() - win_us - DAY_US
        buf_ts, buf_vals = buf_ts[keep], buf_vals[keep]
        if (di + 1) % 20 == 0:
            print(f"  {di+1}/{len(days)} ({d}) warm-windows={int(warm.sum())} buf={len(buf_ts)}", flush=True)
    print("DONE_RANK_OVERLAY.")


def _save(path, d):
    tmp = path + ".tmp.npz"; np.savez(tmp, **d); os.replace(tmp, path)


def self_test(src, sel):
    """Causality + truncation-invariance on real data (a handful of days)."""
    win_us = 3 * DAY_US
    days = sorted(os.path.basename(f)[:-4] for f in glob.glob(f"data/{src}/*.npz")
                  if os.path.basename(f)[0].isdigit())[:12]
    def build_slice(day_list):
        buf_ts = np.zeros(0, np.int64); buf_vals = np.zeros((0, len(sel))); res = {}
        for d in day_list:
            z = np.load(f"data/{src}/{d}.npz", allow_pickle=True)
            r, dts, dl = rank_day(z["X"], z["timestamps"].astype(np.int64), sel, buf_ts, buf_vals, win_us)
            res[d] = r
            buf_ts = np.append(buf_ts, dts); buf_vals = np.vstack([buf_vals, dl])
        return res
    full = build_slice(days)
    tgt = days[-1]
    # CAUSALITY: dropping days AFTER tgt must not change tgt's rank
    trunc_future = build_slice(days[:days.index(tgt) + 1])
    a = np.nan_to_num(full[tgt]); b = np.nan_to_num(trunc_future[tgt])
    print(f"CAUSALITY (future-drop): max|Δ|={np.max(np.abs(a-b)):.2e} (must be 0)")
    # TRUNCATION-INVARIANCE: building from only the trailing 3d+1 warmup gives identical tgt
    ti = days.index(tgt); warm_start = max(0, ti - 4)         # >=3d warmup
    trunc_past = build_slice(days[warm_start:ti + 1])
    c = np.nan_to_num(trunc_past[tgt])
    print(f"TRUNCATION-INVARIANCE (trailing-only): max|Δ|={np.max(np.abs(a-c)):.2e} (must be ~0)")
    r = full[tgt][~np.isnan(full[tgt]).any(axis=(1,2))]
    print(f"rank range=[{np.nanmin(full[tgt]):.3f},{np.nanmax(full[tgt]):.3f}] (must be within [-1,1])")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--src", default="npz_v2arch"); ap.add_argument("--dst", default="npz_v2arch_rank")
    ap.add_argument("--mode", choices=["full_x", "prior"], default="full_x")
    ap.add_argument("--start"); ap.add_argument("--end"); ap.add_argument("--window-days", type=int, default=3)
    ap.add_argument("--sel", default=None, help="json list of channel indices; default = frozen 34")
    ap.add_argument("--self-test", action="store_true")
    a = ap.parse_args()
    sel = json.loads(a.sel) if a.sel else SEL_DEFAULT
    if a.self_test:
        self_test(a.src, sel); return
    process_range(a.src, a.dst, sel, a.start, a.end, a.mode, a.window_days)


if __name__ == "__main__":
    main()
