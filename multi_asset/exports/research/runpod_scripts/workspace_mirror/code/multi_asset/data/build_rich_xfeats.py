"""RICH spot-perp feature library for the BTC PERP y_600 residual (basis change).

> **created:** 2026-06-19  | **status:** in-progress  | **supersedes shallow set:**
> the 4-basis + 6-cross-venue gate (perpY_basis_residual_gate.py /
> perp_feature_families_gate.py). This is the DEEP, mechanism-grounded set.

THE TARGET WE ARE AFTER
-----------------------
perp_y_600 = spot_y_600 + r,  corr(spot_y,perp_y)=0.9985, r_var/perp_var~0.003.
A spot-feature model gets the +0.9985 bulk for free; the *perp-specific* alpha is
the basis change ``r = perp_y - spot_y`` (~0.9 bps std). The shallow basis set
lifted perp Ridge by only ~+0.01. This module builds a RICH set whose explicit
job is to predict ``r``: the funding-carry clock that the basis mean-reverts to,
the multi-scale basis structure, deep multi-scale cross-venue divergences, and a
liquidation-cascade proxy. Each family has a mechanism (documented per builder);
the gate (rich_xfeats_gate.py) measures IC-vs-r, IC-vs-perp_y, block deltaP over
SPOT-64, and -- decisively -- whether each family adds ORTHOGONALLY over basis.

INPUTS (server, READ-ONLY)
--------------------------
  data/mid_cache/<day>.npz   : sec (unix s, 1Hz, full UTC day), spot_mid, perp_mid
                               -> families A (funding), B (basis), D (liq-proxy),
                               and the cross-venue PRICE lead-lag.
  data/lastts_cache/<day>.npz: spot_last/perp_last (N,64) last-<=t snapshots per
                               venue, timestamps (spot pred ts, us), perp_ts.
                               -> family C (cross-venue book/flow divergences).

STRICT CAUSALITY (<= t)  -- verified by the gate's +600s shift sentinel & perm-null
-----------------------------------------------------------------------------------
* Every rolling/EMA statistic on the 1Hz mid grid is SHIFT(1) (value at second i
  uses only seconds < i) or is itself a <=t level. Sampling at a prediction second
  t uses the grid value AT-OR-BEFORE floor(t) (searchsorted right-1).
* The funding clock is a deterministic function of the UTC wall-clock second, so
  every funding feature is causal BY CONSTRUCTION (no data, only the calendar).
* Cross-venue divergences are contemporaneous last-<=t snapshots (perp_ts is at or
  before the spot second), so perp_feat - spot_feat is <=t.

ALL FEATURES ARE FINITE-SANITIZED (nan/inf -> 0 after construction) and the gate
additionally drops any non-finite row, so a NaN cannot leak a fold.
"""
from __future__ import annotations

import argparse
import os.path as p
import sys

import numpy as np

_REPO = p.dirname(p.dirname(p.dirname(p.abspath(__file__))))
if _REPO not in sys.path:
    sys.path.insert(0, _REPO)

# server data root (the gate passes absolute dirs; these are the defaults)
DATA_DIR = "/mnt/storage/private/work_hsy/quant_research_multi_asset/data"
MID_DIR = p.join(DATA_DIR, "mid_cache")
LASTTS_DIR = p.join(DATA_DIR, "lastts_cache")

US = 1_000_000
SEC_PER_DAY = 86_400
FUNDING_PERIOD_S = 8 * 3600          # Binance USDT-perp funds every 8h (00/08/16 UTC)
CLIP_BPS = 50.0                      # kill cross/print glitches in the raw basis
EPS = 1e-9

# 64-feature column map (identical for spot & perp; == build_factor_leg EXPECTED)
FEAT = {
    "log_return_1s": 0, "log_return_5s": 1, "log_return_30s": 2, "spread_bps": 3,
    "spread_change": 4, "obi_L1": 5, "obi_L5": 6, "obi_L10": 7, "obi_L25": 8,
    "obi_L1_delta": 9, "bid_depth_L5": 10, "ask_depth_L5": 11, "bid_depth_L25": 12,
    "ask_depth_L25": 13, "depth_ratio_L5": 14, "weighted_price_bid_L10": 15,
    "weighted_price_ask_L10": 16, "price_pressure": 17, "realized_vol_30s": 18,
    "realized_vol_60s": 19, "realized_vol_300s": 20, "depth_flow_ratio_30s": 21,
    "bid_slope_L10": 22, "ask_slope_L10": 23, "bid_concentration": 24,
    "ask_concentration": 25, "bid_amt_ratio_L0": 26, "ask_amt_ratio_L0": 27,
    "bid_amt_ratio_L1": 28, "ask_amt_ratio_L1": 29, "bid_amt_ratio_L2": 30,
    "ask_amt_ratio_L2": 31, "bid_amt_ratio_L3": 32, "ask_amt_ratio_L3": 33,
    "bid_amt_ratio_L4": 34, "ask_amt_ratio_L4": 35, "second_of_day_sin": 36,
    "second_of_day_cos": 37, "delta_bid_depth_L5": 38, "delta_ask_depth_L5": 39,
    "net_order_flow_L5": 40, "delta_obi_L5_5s": 41, "delta_pressure_5s": 42,
    "buy_volume_1s": 43, "sell_volume_1s": 44, "net_trade_flow_1s": 45,
    "trade_imbalance_1s": 46, "cumulative_net_flow_30s": 47,
    "cumulative_net_flow_300s": 48, "trade_intensity_30s": 49, "vwap_return_1s": 50,
    "kyle_lambda_30s": 51, "microprice_dev_bps": 52, "roll_spread_60s": 53,
    "vpin_60s": 54, "vpin_300s": 55, "book_pressure_imbalance": 56,
    "price_impact_30s": 57, "net_flow_x_spread": 58, "net_flow_x_vol": 59,
    "obi_L5_rank_1h": 60, "net_flow_rank_1h": 61, "large_trade_arrival_60s": 62,
    "book_pressure_delta_60s": 63,
}


# =========================================================================== #
# causal 1Hz-grid helpers (shift(1) baked in: value at i uses only j < i)
# =========================================================================== #
def _causal_roll_mean_std(x, win):
    """Trailing rolling mean & std over `win` samples, SHIFTED by 1 so index i
    uses x[i-win .. i-1] (strictly < i). >=2 obs else NaN. O(T) prefix sums."""
    x = np.asarray(x, np.float64)
    T = x.size
    xs = np.concatenate([[0.0], np.cumsum(x)])
    xs2 = np.concatenate([[0.0], np.cumsum(x * x)])
    i = np.arange(T)
    hi = i                                   # exclusive upper = i -> up to i-1
    lo = np.maximum(0, i - win)
    cnt = (hi - lo).astype(np.float64)
    s1 = xs[hi] - xs[lo]
    s2 = xs2[hi] - xs2[lo]
    out_m = np.full(T, np.nan); out_s = np.full(T, np.nan)
    valid = cnt >= 2
    with np.errstate(invalid="ignore", divide="ignore"):
        mean = s1 / np.where(cnt > 0, cnt, 1.0)
        var = np.maximum(s2 / np.where(cnt > 0, cnt, 1.0) - mean * mean, 0.0)
        std = np.sqrt(var)
    out_m[valid] = mean[valid]; out_s[valid] = std[valid]
    return out_m, out_s


def _causal_roll_sum(x, win):
    """Trailing rolling sum over `win` samples, SHIFT(1) (index i uses i-win..i-1)."""
    x = np.asarray(x, np.float64)
    T = x.size
    xs = np.concatenate([[0.0], np.cumsum(x)])
    i = np.arange(T)
    hi = i; lo = np.maximum(0, i - win)
    return xs[hi] - xs[lo]


def _causal_roll_max(x, win):
    """Trailing rolling max over `win` samples, SHIFT(1). O(T) via deque."""
    x = np.asarray(x, np.float64)
    T = x.size
    out = np.full(T, np.nan)
    from collections import deque
    dq = deque()                              # holds indices, decreasing x
    for i in range(T):
        # window for index i is [i-win, i-1]; evict out-of-window from front
        while dq and dq[0] < i - win:
            dq.popleft()
        out[i] = x[dq[0]] if dq else np.nan   # max over strictly-earlier samples
        # now push i (so it's available for i+1..)
        while dq and x[dq[-1]] <= x[i]:
            dq.pop()
        dq.append(i)
    return out


def _causal_ema_shift1(x, span):
    """EMA(x, span) then SHIFT(1): value at i is the EMA through i-1. alpha=2/(s+1).

    Recurrence ema[i] = alpha*x[i] + (1-alpha)*ema[i-1], ema[0]=x[0]. Vectorized
    via lfilter (the IIR form of the exact same recurrence) so it is O(T) in C
    rather than a Python loop. Falls back to the explicit loop if scipy is absent.
    """
    x = np.asarray(x, np.float64)
    T = x.size
    if T == 0:
        return x.copy()
    alpha = 2.0 / (span + 1.0)
    try:
        from scipy.signal import lfilter
        # y[i] = alpha*x[i] + (1-alpha)*y[i-1]; seed y[-1]=x[0] so y[0]=x[0].
        zi = np.array([(1.0 - alpha) * x[0]])
        ema, _ = lfilter([alpha], [1.0, -(1.0 - alpha)], x, zi=zi)
    except Exception:
        ema = np.empty(T)
        ema[0] = x[0]
        for i in range(1, T):
            ema[i] = alpha * x[i] + (1.0 - alpha) * ema[i - 1]
    out = np.full(T, np.nan)
    out[1:] = ema[:-1]
    return out


def _lag_on_grid(sec, x, lag_s):
    """x at second (t - lag_s), aligned on the SECOND index (gaps don't shorten
    the lag). Returns (val, ok). Missing -> NaN/False."""
    sec = np.asarray(sec, np.int64)
    target = sec - lag_s
    pos = np.searchsorted(sec, target, side="left")
    ok = (pos < sec.size) & (sec[np.minimum(pos, sec.size - 1)] == target)
    out = np.full(sec.size, np.nan)
    out[ok] = np.asarray(x, np.float64)[pos[ok]]
    return out, ok


def _pctrank_at(sec, x, win, pred_sec):
    """Causal percentile-rank of x AT each prediction second, within the trailing
    `win` seconds (strictly < that second). Computed ONLY at the N pred seconds
    (not the full grid) -> O(N*win), cheap. Returns 0.5 where <2 history obs or
    the pred second is off-grid."""
    sec = np.asarray(sec, np.int64)
    x = np.asarray(x, np.float64)
    pred_sec = np.asarray(pred_sec, np.int64)
    pos = np.searchsorted(sec, pred_sec, side="right") - 1   # last grid idx <= t
    out = np.full(pred_sec.size, 0.5)
    for j in range(pred_sec.size):
        i = pos[j]
        if i < 1:
            continue
        lo = max(0, i - win + 1)
        w = x[lo:i]                                          # strictly earlier
        if w.size >= 2:
            out[j] = float(np.mean(w < x[i]))
    return out


# =========================================================================== #
# per-second SOURCE series from mid_cache (basis level + 1s returns + clock)
# =========================================================================== #
def per_second_source(sec, spot_mid, perp_mid):
    """Return causal per-second source arrays used by families A/B/D and the
    price lead-lag. All are <=t levels or shift(1) stats.

    keys: sec, basis_bps, spot_ret_1s, perp_ret_1s, resid_ret_1s (perp-spot 1s
    return, the per-second analogue of r), sod (sec-of-day)."""
    sec = np.asarray(sec, np.int64)
    spot_mid = np.asarray(spot_mid, np.float64)
    perp_mid = np.asarray(perp_mid, np.float64)
    basis_bps = np.clip((perp_mid - spot_mid) / spot_mid * 1e4, -CLIP_BPS, CLIP_BPS)

    lsm = np.log(np.clip(spot_mid, 1e-12, None))
    lpm = np.log(np.clip(perp_mid, 1e-12, None))
    spot_ret = np.zeros_like(lsm); spot_ret[1:] = np.diff(lsm)
    perp_ret = np.zeros_like(lpm); perp_ret[1:] = np.diff(lpm)
    resid_ret = perp_ret - spot_ret                       # per-second basis change
    sod = (sec % SEC_PER_DAY).astype(np.float64)
    return dict(sec=sec, basis_bps=basis_bps, spot_ret_1s=spot_ret,
                perp_ret_1s=perp_ret, resid_ret_1s=resid_ret, sod=sod)


# =========================================================================== #
# FAMILY A -- FUNDING-CYCLE / CARRY  (headline, untested)
# =========================================================================== #
# MECHANISM: Binance USDT-perp pays funding every 8h at 00:00/08:00/16:00 UTC.
# Funding ~ basis, so the basis is mean-pulled toward each settlement: as a
# settlement approaches, holders of a rich/cheap perp face an imminent
# carry payment/receipt and arbitrage tightens, so the basis tends to revert.
# The 10-min forward perp return therefore depends on (i) where we are in the
# 8h cycle and (ii) the basis x phase interaction (a rich basis late in the
# cycle reverts harder than the same basis early). basis_decay = how far the
# basis has drifted since the last settlement (the reversion is *toward* the
# settlement-time anchor). The clock is pure UTC calendar -> causal by
# construction (no future data, only wall-clock).
def family_funding(src):
    sod = src["sod"]; basis = src["basis_bps"]
    phase = (sod % FUNDING_PERIOD_S) / FUNDING_PERIOD_S          # 0..1 within 8h
    t_since = sod % FUNDING_PERIOD_S                             # s since last settle
    t_to_next = FUNDING_PERIOD_S - t_since                       # s to next settle
    sin = np.sin(2 * np.pi * phase)
    cos = np.cos(2 * np.pi * phase)
    # implied annualised carry from the basis (3 settlements/day * 365)
    basis_annualized = basis * 3.0 * 365.0 / 1e4                 # as a fraction/yr
    # basis decay since the last settlement: basis(t) - basis at the most recent
    # settlement second (<=t). Find last settle second on the grid.
    sec = src["sec"]
    # second-of-day of the last settlement at-or-before each t:
    last_settle_sod = (sod // FUNDING_PERIOD_S) * FUNDING_PERIOD_S
    settle_sec = sec - (sod - last_settle_sod)                   # unix sec of that settle
    # look up basis at settle_sec via searchsorted (<=t, exact second)
    pos = np.searchsorted(sec, settle_sec, side="left")
    okp = (pos < sec.size) & (sec[np.minimum(pos, sec.size - 1)] == settle_sec)
    basis_at_settle = np.full(sec.size, np.nan)
    basis_at_settle[okp] = basis[pos[okp]]
    basis_decay = basis - basis_at_settle                       # drift since settle

    cols = {
        "fund_t_to_next": t_to_next / FUNDING_PERIOD_S,         # 0..1, 0 at settle
        "fund_t_since": t_since / FUNDING_PERIOD_S,             # 0..1
        "fund_phase_sin": sin,
        "fund_phase_cos": cos,
        "fund_basis_x_phase": basis * (phase - 0.5) * 2.0,     # basis x signed cycle pos
        "fund_basis_x_ttn": basis * (t_to_next / FUNDING_PERIOD_S),
        "fund_basis_annualized": basis_annualized,
        "fund_basis_decay": basis_decay,
    }
    return cols


# =========================================================================== #
# FAMILY B -- MULTI-SCALE BASIS STRUCTURE
# =========================================================================== #
# MECHANISM: the shallow set used ONE window each (z@30min, mom@300s, ema@60s).
# The basis lives on multiple timescales: a 5-min dislocation reverts fast, a 2h
# dislocation is a slower carry regime. We expose level, z-score, momentum,
# ema-deviation, realized-vol, and percentile-rank of the basis at {5min, 30min,
# 2h}, plus the basis acceleration (2nd difference). Richer scale coverage lets
# the Ridge separate fast micro-reversion from slow carry drift -- the single-
# window set conflates them.
BASIS_WINDOWS = {"5m": 300, "30m": 1800, "2h": 7200}


def family_basis(src):
    sec = src["sec"]; basis = src["basis_bps"]
    cols = {"basis_bps": basis}
    for tag, win in BASIS_WINDOWS.items():
        m, s = _causal_roll_mean_std(basis, win)
        z = (basis - m) / (s + EPS)
        cols[f"basis_z_{tag}"] = z
        cols[f"basis_emadev_{tag}"] = basis - _causal_ema_shift1(basis, win)
        lag, ok = _lag_on_grid(sec, basis, win)
        mom = np.full(sec.size, np.nan); mom[ok] = basis[ok] - lag[ok]
        cols[f"basis_mom_{tag}"] = mom
        # realized vol of the basis = rolling std of its 1s change
        dbasis = np.zeros_like(basis); dbasis[1:] = np.diff(basis)
        _, rvs = _causal_roll_mean_std(dbasis, win)
        cols[f"basis_rvol_{tag}"] = rvs
    # acceleration: (basis_t - basis_{t-60}) - (basis_{t-60} - basis_{t-120})
    l60, o60 = _lag_on_grid(sec, basis, 60)
    l120, o120 = _lag_on_grid(sec, basis, 120)
    acc = np.full(sec.size, np.nan)
    good = o60 & o120
    acc[good] = (basis[good] - l60[good]) - (l60[good] - l120[good])
    cols["basis_accel_60s"] = acc
    return cols


# =========================================================================== #
# FAMILY C -- CROSS-VENUE DIVERGENCE (deep, multi-scale)
# =========================================================================== #
# MECHANISM: when perp order-flow / book pressure differs from spot at the SAME
# instant, perp is being pushed by perp-only forces (leverage, liquidations,
# funding positioning) that spot does not see -> a perp-specific forward move
# (i.e. predicts r). The shallow set took a single OBI/microprice/flow diff; we
# take the divergence across the book's MULTI-SCALE channels already in the 64-
# feat snapshot (obi L1/L5/L10/L25; net flow 1s/30s/300s; rvol 30/60/300s; vpin
# 60/300; kyle; microprice; depth; spread) PLUS perp/spot ratios for the
# strictly-positive quantities (vol, spread, depth, volume), where a ratio is the
# right scale-free contrast. Flow diffs are emitted RAW (perp flow >> spot flow
# in absolute size) and the gate MAD-standardizes per-fold so the diff is a
# pressure-sign, not a scale artifact.
DIV_DIRECTIONAL = [        # comparable in sign+units across venues -> raw diff
    "obi_L1", "obi_L5", "obi_L10", "obi_L25",
    "microprice_dev_bps", "book_pressure_imbalance",
    "trade_imbalance_1s", "vpin_60s", "vpin_300s",
    "price_pressure", "weighted_price_bid_L10", "weighted_price_ask_L10",
]
DIV_FLOW_RAW = [           # signed flow, perp>>spot in scale -> raw diff (gate z's)
    "net_trade_flow_1s", "cumulative_net_flow_30s", "cumulative_net_flow_300s",
    "net_order_flow_L5",
]
DIV_RATIO_POS = [          # strictly >=0 -> log-ratio is the scale-free contrast
    "realized_vol_30s", "realized_vol_60s", "realized_vol_300s",
    "spread_bps", "kyle_lambda_30s", "trade_intensity_30s",
    "bid_depth_L5", "ask_depth_L5", "bid_depth_L25", "ask_depth_L25",
]


def _logratio(a, b):
    r = (np.abs(a) + EPS) / (np.abs(b) + EPS)
    return np.log(np.clip(r, 1e-3, 1e3))


def family_xvenue(spot_last, perp_last):
    cols = {}
    for f in DIV_DIRECTIONAL:
        cols[f"div_{f}"] = perp_last[:, FEAT[f]] - spot_last[:, FEAT[f]]
    for f in DIV_FLOW_RAW:
        cols[f"divflow_{f}"] = perp_last[:, FEAT[f]] - spot_last[:, FEAT[f]]
    for f in DIV_RATIO_POS:
        cols[f"ratio_{f}"] = _logratio(perp_last[:, FEAT[f]], spot_last[:, FEAT[f]])
    # perp/spot total trade volume ratio (buy+sell)
    pvol = perp_last[:, FEAT["buy_volume_1s"]] + perp_last[:, FEAT["sell_volume_1s"]]
    svol = spot_last[:, FEAT["buy_volume_1s"]] + spot_last[:, FEAT["sell_volume_1s"]]
    cols["ratio_volume_1s"] = _logratio(pvol, svol)
    return cols


def family_xvenue_price_leadlag(src, pred_sec):
    """Causal spot->perp PRICE lead-lag at the prediction second, from the 1Hz
    mids. MECHANISM: spot price is measured ~2x cleaner / can lead perp; if spot
    has already moved over the last k seconds and perp has not fully matched, perp
    tends to catch up -> predicts a perp-specific move (a component of r). We
    expose the spot-minus-perp cumulative return over {5s,30s,60s} (lagged so it
    is <=t) -- a positive value = spot ran ahead of perp -> perp should follow."""
    sec = src["sec"]
    lsm_ret = src["spot_ret_1s"]; lpm_ret = src["perp_ret_1s"]
    cols = {}
    for k in (5, 30, 60):
        s_cum = _causal_roll_sum(lsm_ret, k)        # sum of last k 1s spot returns (<=t)
        p_cum = _causal_roll_sum(lpm_ret, k)
        gap = s_cum - p_cum                          # spot ahead of perp by this much
        cols[f"px_spotlead_{k}s"] = _sample_grid(sec, gap, pred_sec)
    return cols


# =========================================================================== #
# FAMILY D -- LIQUIDATION-CASCADE PROXY
# =========================================================================== #
# MECHANISM: a perp liquidation cascade moves the PERP price violently while spot
# barely moves (forced perp-side market orders). So a large |perp 1s return -
# spot 1s return| spike, and a perp/spot realized-vol ratio spike, are proxies for
# liquidation pressure that is PERP-SPECIFIC -> a perp forward move (component of
# r), typically with short-term continuation then reversion. We expose: rolling
# max & mean of the per-second residual return magnitude {60s,300s}, the perp/spot
# 1s-realized-vol ratio {60s,300s}, a count of "large perp move unmatched by spot"
# events {300s}, and the SIGNED recent residual return sum {60s} (cascade
# direction). Liquidations are absent on disk (no Tardis liq feed) so this is the
# best causal proxy from mids alone.
def family_liq(src, pred_sec):
    sec = src["sec"]
    resid = src["resid_ret_1s"]
    aresid = np.abs(resid)
    spot_ret = src["spot_ret_1s"]; perp_ret = src["perp_ret_1s"]
    cols = {}
    for k in (60, 300):
        cols[f"liq_absresid_max_{k}s"] = _sample_grid(sec, _causal_roll_max(aresid, k), pred_sec)
        cols[f"liq_absresid_mean_{k}s"] = _sample_grid(sec, _causal_roll_sum(aresid, k) / k, pred_sec)
        # perp/spot realized-vol ratio: sqrt(sum perp_ret^2)/sqrt(sum spot_ret^2)
        pv = np.sqrt(np.maximum(_causal_roll_sum(perp_ret ** 2, k), 0.0))
        sv = np.sqrt(np.maximum(_causal_roll_sum(spot_ret ** 2, k), 0.0))
        cols[f"liq_perpspot_rvol_{k}s"] = _sample_grid(sec, np.log((pv + EPS) / (sv + EPS)), pred_sec)
    # "large perp move unmatched by spot": |perp_ret|>3*rolling_std(perp_ret,300)
    # AND |spot_ret| small. count over trailing 300s.
    _, pstd = _causal_roll_mean_std(perp_ret, 300)
    big_unmatched = ((np.abs(perp_ret) > 3.0 * (pstd + EPS)) &
                     (np.abs(spot_ret) < 1.0 * (pstd + EPS))).astype(np.float64)
    cols["liq_unmatched_cnt_300s"] = _sample_grid(sec, _causal_roll_sum(big_unmatched, 300), pred_sec)
    # signed recent residual-return sum (cascade direction) over 60s
    cols["liq_resid_sum_60s"] = _sample_grid(sec, _causal_roll_sum(resid, 60), pred_sec)
    return cols


# =========================================================================== #
# sampling at prediction seconds (<=t lookup on the 1Hz grid)
# =========================================================================== #
def _sample_grid(sec, grid_vals, pred_sec):
    """grid_vals[ floor(pred_ts) ] via searchsorted right-1 (value at-or-before)."""
    sec = np.asarray(sec, np.int64)
    pred_sec = np.asarray(pred_sec, np.int64)
    pos = np.searchsorted(sec, pred_sec, side="right") - 1
    ok = pos >= 0
    pos = np.clip(pos, 0, sec.size - 1)
    out = np.asarray(grid_vals, np.float64)[pos]
    out[~ok] = np.nan
    return out


# =========================================================================== #
# top-level per-day assembly
# =========================================================================== #
FAMILIES = ("funding", "basis", "xvenue", "liq")


def build_day(day, mid_dir=MID_DIR, lastts_dir=LASTTS_DIR):
    """Build all rich families for one UTC day, sampled at the spot prediction
    grid. Returns dict:
        ts        (N,) int64  spot pred ts (us)  -- joins to npz_spot / clean
        perp_ts   (N,) int64
        fam       {family_name: (names list, X (N,k) float64)}
        all_names list, all_X (N,K)
    NaN/inf in features -> 0 (sanitized); the gate also drops non-finite rows.
    """
    lc = np.load(p.join(lastts_dir, f"{day}.npz"))
    ts = lc["timestamps"].astype(np.int64)
    perp_ts = lc["perp_ts"].astype(np.int64)
    spot_last = lc["spot_last"].astype(np.float64)
    perp_last = lc["perp_last"].astype(np.float64)
    pred_sec = ts // US

    zm = np.load(p.join(mid_dir, f"{day}.npz"))
    src = per_second_source(zm["sec"], zm["spot_mid"], zm["perp_mid"])

    fam = {}
    # A funding (grid cols -> sample at pred_sec)
    fcols = family_funding(src)
    fam["funding"] = _finalize({k: _sample_grid(src["sec"], v, pred_sec)
                                for k, v in fcols.items()})
    # B basis (grid cols -> sample) + pctrank computed directly at pred seconds
    bcols = family_basis(src)
    bsamp = {k: _sample_grid(src["sec"], v, pred_sec) for k, v in bcols.items()}
    bsamp["basis_pctrank_30m"] = _pctrank_at(src["sec"], src["basis_bps"], 1800, pred_sec)
    bsamp["basis_pctrank_2h"] = _pctrank_at(src["sec"], src["basis_bps"], 7200, pred_sec)
    fam["basis"] = _finalize(bsamp)
    # C cross-venue: book/flow diffs at last-step + price lead-lag from grid
    xcols = family_xvenue(spot_last, perp_last)
    xcols.update(family_xvenue_price_leadlag(src, pred_sec))
    fam["xvenue"] = _finalize(xcols)
    # D liquidation proxy (grid)
    fam["liq"] = _finalize(family_liq(src, pred_sec))

    all_names, all_blocks = [], []
    for f in FAMILIES:
        names, X = fam[f]
        all_names += names
        all_blocks.append(X)
    all_X = np.concatenate(all_blocks, axis=1)
    return dict(ts=ts, perp_ts=perp_ts, fam=fam, all_names=all_names, all_X=all_X)


def _finalize(cols: dict):
    """dict name->array -> (sorted names, X) with nan/inf -> 0."""
    names = list(cols.keys())
    X = np.column_stack([cols[n] for n in names]).astype(np.float64)
    X = np.nan_to_num(X, nan=0.0, posinf=0.0, neginf=0.0)
    return names, X


# =========================================================================== #
# self-test
# =========================================================================== #
def _probe(days):
    for day in days:
        try:
            d = build_day(day)
        except Exception as e:
            print(f"{day}: ERR {type(e).__name__}: {e}")
            continue
        print(f"\n=== {day}  N={d['ts'].size}  total_feats={d['all_X'].shape[1]} ===")
        for f in FAMILIES:
            names, X = d["fam"][f]
            finite = np.isfinite(X).all(axis=1).mean()
            print(f"  {f:8s} k={len(names):2d}  finite_rows={finite:.3f}  "
                  f"std_range=[{X.std(0).min():.2e},{X.std(0).max():.2e}]")
            print(f"           {names}")


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--probe", nargs="*", default=["2025-02-10", "2026-03-15"])
    args = ap.parse_args()
    _probe(args.probe)
