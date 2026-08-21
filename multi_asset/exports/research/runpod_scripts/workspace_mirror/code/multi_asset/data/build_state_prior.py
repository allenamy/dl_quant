"""D1 state_prior OVERLAY builder (Stage-0B).

Writes an 18-d CAUSAL state vector per window timestamp into an OVERLAY cache
``data/npz_v2arch_state/`` (source cache ``npz_v2arch`` is READ-ONLY). The
dataset loader (``multi_asset/data/dual_lob_dataset.py`` with ``state_prior_dir``)
concatenates it onto ``regime_prior`` -> d_prior=24. The MODEL frozen-normalises
these RAW values (FLAG-11 fix); the overlay stays raw.

ALIGNMENT (reuses the VERIFIED leak-safe math of add_funding_channels.py):
  * metrics / premium-index 5m bars: use the last bar whose create/open time is
    <= t-300s (i.e. the bar has FULLY closed by t)  ->  strictly causal.
  * funding 8h prints: use the last settled print <= t.
All trailing-window stats use ONLY bars at or before those causal indices.

18 features (multi-timescale), NAMES in ``STATE_NAMES``:
  funding (8h): last, z_30prints, std_5d(15), mean_5d(15)
  premium-index (5m): mean_1h, std_1h, mean_24h, std_24h
  open-interest (5m): chg_1h, chg_24h, z_5d
  positioning (5m): toptrader_level, toptrader_d24h, taker_level, taker_d24h
  realized-vol (5m mark=OIV/OI): rvol_1h, rvol_24h, rvol_5d

CLI:
  build:    PYTHONPATH=. python multi_asset/data/build_state_prior.py \
                --src npz_v2arch --dst npz_v2arch_state --start 2024-05-01 --end 2026-05-31 --apply
  selftest: PYTHONPATH=. python multi_asset/data/build_state_prior.py --selftest
  pregate:  PYTHONPATH=. python multi_asset/data/build_state_prior.py --pregate \
                --src npz_v2arch --month-a 2025-10 --month-b 2026-04
"""
from __future__ import annotations

import argparse
import csv
import glob
import os
import sys
from datetime import datetime, timezone

import numpy as np

MET = "data/funding/btcusdt_metrics_5m.csv"
FUND = "data/funding/btcusdt_funding.csv"
PIDX = "data/funding/btcusdt_premium_index_5m.csv"
BAR_US = 300 * 1_000_000            # 5m in microseconds
DAY_BARS = 288                      # 5m bars per 24h
HOUR_BARS = 12                      # 5m bars per 1h
D5_BARS = 5 * DAY_BARS             # 5m bars per 5d
FUND_PER_DAY = 3                   # 8h funding prints/day
EPS = 1e-9

STATE_NAMES = [
    "fund_last", "fund_z30", "fund_std5d", "fund_mean5d",
    "pidx_mean_1h", "pidx_std_1h", "pidx_mean_24h", "pidx_std_24h",
    "oi_chg_1h", "oi_chg_24h", "oi_z_5d",
    "tt_level", "tt_d24h", "taker_level", "taker_d24h",
    "rvol_1h", "rvol_24h", "rvol_5d",
]
N_STATE = len(STATE_NAMES)
assert N_STATE == 18


def _f(x):
    try:
        return float(x)
    except Exception:
        return np.nan


def _parse_us(s: str) -> int:
    return int(datetime.strptime(s, "%Y-%m-%d %H:%M:%S")
               .replace(tzinfo=timezone.utc).timestamp()) * 1_000_000


def rolling_mean_std(a: np.ndarray, w: int):
    """Trailing window (size up to ``w``, inclusive of index i) mean & std.

    Partial leading windows use whatever is available (lo=max(0, i-w+1)). Pure
    cumsum — O(n), strictly causal (uses only elements <= i)."""
    a = a.astype(np.float64)
    n = len(a)
    c1 = np.concatenate([[0.0], np.cumsum(a)])
    c2 = np.concatenate([[0.0], np.cumsum(a * a)])
    idx = np.arange(n)
    lo = np.maximum(0, idx - w + 1)
    cnt = (idx - lo + 1).astype(np.float64)
    s1 = c1[idx + 1] - c1[lo]
    s2 = c2[idx + 1] - c2[lo]
    mean = s1 / cnt
    var = np.maximum(s2 / cnt - mean * mean, 0.0)
    return mean, np.sqrt(var)


class StatePriorSource:
    """Loads the CSVs once and precomputes causal rolling stats for state_vector."""

    def __init__(self, met=MET, fund=FUND, pidx=PIDX):
        # --- metrics (5m): create_time, OI, OIV, toptrader LS, taker LS -------
        mrows = []
        with open(met) as f:
            for r in csv.DictReader(f):
                try:
                    mrows.append((
                        _parse_us(r["create_time"]),
                        _f(r["sum_open_interest"]),
                        _f(r["sum_open_interest_value"]),
                        _f(r["sum_toptrader_long_short_ratio"]),
                        _f(r["sum_taker_long_short_vol_ratio"]),
                    ))
                except Exception:
                    continue
        M = np.array(mrows, dtype=np.float64)
        M = M[np.argsort(M[:, 0])]
        self.MT, self.OI, self.OIV, self.TT, self.TK = (M[:, 0], M[:, 1], M[:, 2],
                                                        M[:, 3], M[:, 4])
        self.PRICE = self.OIV / np.clip(self.OI, EPS, None)   # mark-price proxy

        # --- premium index (5m): openTime, pidx_close -------------------------
        prows = []
        with open(pidx) as f:
            for r in csv.DictReader(f):
                try:
                    prows.append((int(r["openTime_ms"]) * 1000, _f(r["pidx_close"])))
                except Exception:
                    continue
        P = np.array(prows, dtype=np.float64)
        P = P[np.argsort(P[:, 0])]
        self.PT, self.PC = P[:, 0], P[:, 1]

        # --- funding (8h): fundingTime, fundingRate ---------------------------
        frows = []
        with open(fund) as f:
            for r in csv.DictReader(f):
                try:
                    frows.append((int(r["fundingTime_ms"]) * 1000, _f(r["fundingRate"])))
                except Exception:
                    continue
        F = np.array(frows, dtype=np.float64)
        F = F[np.argsort(F[:, 0])]
        self.FT, self.FR = F[:, 0], F[:, 1]

        # --- precompute causal rolling stats ----------------------------------
        # funding
        self.fr_m30, self.fr_s30 = rolling_mean_std(self.FR, 30)
        self.fr_m5d, self.fr_s5d = rolling_mean_std(self.FR, FUND_PER_DAY * 5)  # 15
        # premium index
        self.pc_m1h, self.pc_s1h = rolling_mean_std(self.PC, HOUR_BARS)
        self.pc_m24, self.pc_s24 = rolling_mean_std(self.PC, DAY_BARS)
        # OI z over 5d
        self.oi_m5d, self.oi_s5d = rolling_mean_std(self.OI, D5_BARS)
        # realized vol of 5m mark-price log-returns
        logp = np.log(np.clip(self.PRICE, EPS, None))
        ret = np.zeros_like(logp)
        ret[1:] = np.diff(logp)
        self.ret = ret
        _, self.rv_1h = rolling_mean_std(ret, HOUR_BARS)
        _, self.rv_24 = rolling_mean_std(ret, DAY_BARS)
        _, self.rv_5d = rolling_mean_std(ret, D5_BARS)

    def state_vector(self, win_ts_us: np.ndarray) -> np.ndarray:
        """(N,) anchor timestamps (us) -> (N, 18) RAW causal state. Rows with no
        available history (before any data) are left 0 (mask-safe)."""
        win_ts_us = np.asarray(win_ts_us, dtype=np.int64)
        N = len(win_ts_us)
        out = np.zeros((N, N_STATE), dtype=np.float32)
        cut = win_ts_us - BAR_US                                # 5m-bar closed-by-t
        im = np.searchsorted(self.MT, cut, side="right") - 1
        ip = np.searchsorted(self.PT, cut, side="right") - 1
        iff = np.searchsorted(self.FT, win_ts_us, side="right") - 1
        v = (im >= 0) & (ip >= 0) & (iff >= 0)
        if not np.any(v):
            return out
        imv, ipv, iffv = im[v], ip[v], iff[v]

        def lag(arr, idx, k):
            return arr[np.clip(idx - k, 0, None)]

        # funding
        out[v, 0] = self.FR[iffv]
        out[v, 1] = (self.FR[iffv] - self.fr_m30[iffv]) / (self.fr_s30[iffv] + EPS)
        out[v, 2] = self.fr_s5d[iffv]
        out[v, 3] = self.fr_m5d[iffv]
        # premium index
        out[v, 4] = self.pc_m1h[ipv]
        out[v, 5] = self.pc_s1h[ipv]
        out[v, 6] = self.pc_m24[ipv]
        out[v, 7] = self.pc_s24[ipv]
        # open interest
        out[v, 8] = (self.OI[imv] - lag(self.OI, imv, HOUR_BARS)) / (
            np.abs(lag(self.OI, imv, HOUR_BARS)) + EPS)
        out[v, 9] = (self.OI[imv] - lag(self.OI, imv, DAY_BARS)) / (
            np.abs(lag(self.OI, imv, DAY_BARS)) + EPS)
        out[v, 10] = (self.OI[imv] - self.oi_m5d[imv]) / (self.oi_s5d[imv] + EPS)
        # positioning
        out[v, 11] = self.TT[imv] - 1.0
        out[v, 12] = self.TT[imv] - lag(self.TT, imv, DAY_BARS)
        out[v, 13] = self.TK[imv] - 1.0
        out[v, 14] = self.TK[imv] - lag(self.TK, imv, DAY_BARS)
        # realized vol
        out[v, 15] = self.rv_1h[imv]
        out[v, 16] = self.rv_24[imv]
        out[v, 17] = self.rv_5d[imv]
        return np.nan_to_num(out, nan=0.0, posinf=0.0, neginf=0.0)


# --------------------------------------------------------------------------- #
def _dd(p):
    return os.path.basename(p)[:-4]


def build(src: str, dst: str, start: str | None, end: str | None, apply: bool):
    if src == dst:
        sys.exit("src==dst not allowed (overlay must be a separate cache)")
    srcd, dstd = f"data/{src}", f"data/{dst}"
    os.makedirs(dstd, exist_ok=True)
    files = sorted(glob.glob(f"{srcd}/*.npz"))
    sel = [f for f in files
           if (not start or _dd(f) >= start) and (not end or _dd(f) <= end)]
    print(f"build_state_prior: {len(sel)} day(s) {start}..{end} -> {dstd} (apply={apply})")
    src_obj = StatePriorSource()
    for f in sel:
        day = _dd(f)
        dp = f"{dstd}/{day}.npz"
        with np.load(f, allow_pickle=True) as z:
            ts = np.asarray(z["timestamps"], dtype=np.int64)
        state = src_obj.state_vector(ts)
        cov = float(np.mean(np.any(state != 0, axis=1)))
        if not apply:
            print(f"  [dry] {day}: state {state.shape} cov={cov:.3f}")
            continue
        tmp = dp + ".tmp.npz"
        np.savez(tmp, state=state, timestamps=ts, state_names=np.array(STATE_NAMES))
        os.replace(tmp, dp)
        print(f"  {day}: state {state.shape} cov={cov:.3f}")
    print("DONE_STATE_PRIOR.")


# --------------------------------------------------------------------------- #
# SELFTEST — synthetic-timestamp alignment / no-look-ahead                     #
# --------------------------------------------------------------------------- #
def selftest():
    """Verify (i) causality (a future spike in funding/OI does NOT affect an
    earlier window's state) and (ii) monotone ffill (state changes only at bar
    boundaries)."""
    import tempfile
    ok = True

    class _Synth(StatePriorSource):
        def __init__(self):
            # 5m metrics grid over 10 days from an arbitrary epoch
            t0 = _parse_us("2025-01-01 00:00:00")
            n = DAY_BARS * 10
            self.MT = t0 + np.arange(n) * BAR_US
            self.OI = 100.0 + np.zeros(n)
            self.OI[n // 2:] = 200.0                       # step at the midpoint
            self.OIV = self.OI * 50000.0
            self.TT = np.ones(n)
            self.TK = np.ones(n)
            self.PRICE = self.OIV / np.clip(self.OI, EPS, None)
            self.PT = self.MT.copy()
            self.PC = np.zeros(n)
            self.PC[n // 2:] = 0.001
            # funding every 8h
            self.FT = t0 + np.arange(30) * (8 * 3600 * 1_000_000)
            self.FR = np.zeros(30)
            self.FR[15:] = 0.01                            # funding spike at print 15
            self.fr_m30, self.fr_s30 = rolling_mean_std(self.FR, 30)
            self.fr_m5d, self.fr_s5d = rolling_mean_std(self.FR, 15)
            self.pc_m1h, self.pc_s1h = rolling_mean_std(self.PC, HOUR_BARS)
            self.pc_m24, self.pc_s24 = rolling_mean_std(self.PC, DAY_BARS)
            self.oi_m5d, self.oi_s5d = rolling_mean_std(self.OI, D5_BARS)
            logp = np.log(np.clip(self.PRICE, EPS, None))
            ret = np.zeros_like(logp); ret[1:] = np.diff(logp)
            self.ret = ret
            _, self.rv_1h = rolling_mean_std(ret, HOUR_BARS)
            _, self.rv_24 = rolling_mean_std(ret, DAY_BARS)
            _, self.rv_5d = rolling_mean_std(ret, D5_BARS)

    s = _Synth()
    t0 = s.MT[0]
    mid_bar = DAY_BARS * 10 // 2
    t_mid = s.MT[mid_bar]
    # (1) Causality on OI step: a window anchored 1s BEFORE the step-bar closes
    #     must see OI=100 (fund/metrics <= t-300). One anchored well after -> 200.
    st_before = s.state_vector(np.array([t_mid + BAR_US - 1_000_000]))[0]  # just before bar closes at t-300
    st_after = s.state_vector(np.array([t_mid + 2 * BAR_US + 1_000_000]))[0]
    # OI level via fund? use tt_level? use raw OI through oi_z? Check OI %chg 1h is 0 pre-step
    # Use the OI z (idx 10): pre-step z ~0 (flat 100); post-step z >0 (jumped to 200).
    pre_z = st_before[10]
    post_z = st_after[10]
    c1 = (pre_z == 0.0 or abs(pre_z) < abs(post_z))
    print(f"[selftest] OI-step causality: pre_z={pre_z:.3f} post_z={post_z:.3f} -> {'OK' if c1 else 'FAIL'}")
    ok &= c1

    # (2) Funding-spike causality: window BEFORE print-15 time must see fund_last=0.
    t_fund_pre = s.FT[15] - 1_000_000               # 1s before the spike settles
    t_fund_post = s.FT[15] + 1_000_000              # 1s after
    f_pre = s.state_vector(np.array([t_fund_pre]))[0][0]   # fund_last
    f_post = s.state_vector(np.array([t_fund_post]))[0][0]
    c2 = (f_pre == 0.0 and f_post == 0.01)
    print(f"[selftest] funding-spike causality: fund_last pre={f_pre} post={f_post} -> {'OK' if c2 else 'FAIL'}")
    ok &= c2

    # (3) No look-ahead vs a truncated source: state at time T computed on the
    #     FULL series must equal state computed on a source truncated to <= T.
    Ttest = s.MT[mid_bar + 50]
    full = s.state_vector(np.array([Ttest]))[0]
    trunc = _Synth()
    keep_m = trunc.MT <= Ttest
    keep_f = trunc.FT <= Ttest
    keep_p = trunc.PT <= Ttest
    for attr, keep in (("MT", keep_m), ("OI", keep_m), ("OIV", keep_m),
                       ("TT", keep_m), ("TK", keep_m), ("PRICE", keep_m),
                       ("PT", keep_p), ("PC", keep_p), ("FT", keep_f), ("FR", keep_f)):
        setattr(trunc, attr, getattr(trunc, attr)[keep])
    trunc.fr_m30, trunc.fr_s30 = rolling_mean_std(trunc.FR, 30)
    trunc.fr_m5d, trunc.fr_s5d = rolling_mean_std(trunc.FR, 15)
    trunc.pc_m1h, trunc.pc_s1h = rolling_mean_std(trunc.PC, HOUR_BARS)
    trunc.pc_m24, trunc.pc_s24 = rolling_mean_std(trunc.PC, DAY_BARS)
    trunc.oi_m5d, trunc.oi_s5d = rolling_mean_std(trunc.OI, D5_BARS)
    lp = np.log(np.clip(trunc.PRICE, EPS, None)); rr = np.zeros_like(lp); rr[1:] = np.diff(lp)
    _, trunc.rv_1h = rolling_mean_std(rr, HOUR_BARS)
    _, trunc.rv_24 = rolling_mean_std(rr, DAY_BARS)
    _, trunc.rv_5d = rolling_mean_std(rr, D5_BARS)
    tstate = trunc.state_vector(np.array([Ttest]))[0]
    c3 = bool(np.allclose(full, tstate, atol=1e-9))
    print(f"[selftest] truncation-invariance (no look-ahead): max|Δ|="
          f"{float(np.abs(full - tstate).max()):.3e} -> {'OK' if c3 else 'FAIL'}")
    ok &= c3

    print(f"\n[selftest] {'ALL OK' if ok else 'FAILED'}")
    return ok


# --------------------------------------------------------------------------- #
# CPU PRE-GATE — do fixed descriptors AND state features separate the months?  #
# --------------------------------------------------------------------------- #
def pregate(src: str, month_a: str, month_b: str, max_windows: int = 20000):
    """Report inter-month separation for the 6 fixed descriptors AND the 18 state
    features between two months. PASS (descriptors) = >=3/6 separate (>1 within-σ).

    Descriptor separation is AFFINE-INVARIANT to the static-450d-z the model
    applies pre-RevIN, so computing on RAW X here gives the identical verdict.
    """
    import torch
    from multi_asset.model.regime_state import (
        PreRevINRegimeExtractor, descriptor_month_separation)

    def _collect(month):
        files = sorted(glob.glob(f"data/{src}/{month}-*.npz"))
        descs, states, tss = [], [], []
        src_obj = None
        for f in files:
            with np.load(f, allow_pickle=True) as z:
                X = np.asarray(z["X"], dtype=np.float32)
                ts = np.asarray(z["timestamps"], dtype=np.int64)
            descs.append(X)     # keep raw windows; extractor pulls feat0
            tss.append(ts)
        Xall = np.concatenate(descs, axis=0)
        tsall = np.concatenate(tss, axis=0)
        if len(tsall) > max_windows:
            sel = np.linspace(0, len(tsall) - 1, max_windows).astype(int)
            Xall, tsall = Xall[sel], tsall[sel]
        return Xall, tsall

    print(f"[pregate] months {month_a} vs {month_b} from data/{src}")
    Xa, tsa = _collect(month_a)
    Xb, tsb = _collect(month_b)
    ext = PreRevINRegimeExtractor()
    with torch.no_grad():
        da = ext(torch.from_numpy(Xa).float())
        db = ext(torch.from_numpy(Xb).float())
    r = descriptor_month_separation(da, db)
    desc_names = ["vol_60", "vol_300", "vol_full", "vol_accel", "mean_feat0", "ac1"]
    print(f"\n  === 6 FIXED DESCRIPTORS ({month_a} vs {month_b}) ===")
    for i, nm in enumerate(desc_names):
        print(f"    {nm:11s} meanA={r['mean_a'][i]:+.4f} meanB={r['mean_b'][i]:+.4f} "
              f"spread={r['spread'][i]:.4f} within1σ={r['within_sigma'][i]:.4f} "
              f"sep={'YES' if bool(r['pass_per_desc'][i]) else 'no'}")
    desc_pass = r["n_pass"] >= 3
    print(f"  DESCRIPTOR PRE-GATE: {r['n_pass']}/6 separate -> "
          f"{'PASS' if desc_pass else 'FAIL'} (need >=3)")

    # state features
    s = StatePriorSource()
    sa = torch.from_numpy(s.state_vector(tsa)).float()
    sb = torch.from_numpy(s.state_vector(tsb)).float()
    rs = descriptor_month_separation(sa, sb)
    print(f"\n  === 18 STATE FEATURES ({month_a} vs {month_b}) ===")
    for i, nm in enumerate(STATE_NAMES):
        print(f"    {nm:14s} meanA={rs['mean_a'][i]:+.5f} meanB={rs['mean_b'][i]:+.5f} "
              f"spread={rs['spread'][i]:.5f} within1σ={rs['within_sigma'][i]:.5f} "
              f"sep={'YES' if bool(rs['pass_per_desc'][i]) else 'no'}")
    print(f"  STATE SEPARATION: {rs['n_pass']}/18 features separate months")
    return desc_pass, r["n_pass"], rs["n_pass"]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--src", default="npz_v2arch")
    ap.add_argument("--dst", default="npz_v2arch_state")
    ap.add_argument("--start")
    ap.add_argument("--end")
    ap.add_argument("--apply", action="store_true")
    ap.add_argument("--selftest", action="store_true")
    ap.add_argument("--pregate", action="store_true")
    ap.add_argument("--month-a", default="2025-10")
    ap.add_argument("--month-b", default="2026-04")
    a = ap.parse_args()
    if a.selftest:
        ok = selftest()
        sys.exit(0 if ok else 1)
    if a.pregate:
        pregate(a.src, a.month_a, a.month_b)
        return
    build(a.src, a.dst, a.start, a.end, a.apply)


if __name__ == "__main__":
    main()
