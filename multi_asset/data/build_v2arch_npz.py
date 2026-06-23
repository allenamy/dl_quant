"""Build the V2 dual-source ARCHITECTURE cache — ``data/npz_v2arch``.

> **created:** 2026-06-22 | **Session:** v2-dual-source-arch | **状态:** in-progress
> | **作废条件:** superseded by a re-spec'd dual-source foundation, or if the base
>   caches (npz_spot2perp_clean / npz_perp / mid_cache) are replaced.

WHAT THIS BUILDS (and WHY this is the right, cheap merge)
--------------------------------------------------------
The v2 dual-source DL model (``multi_asset/model/dual_lob_v2arch.py``) needs, per
window, FOUR things that the proven leak-free base cache does not already carry
together:

  1. the SPOT 64-feature hand sequence + SPOT raw LOB  (Path A + Path B)   ── base
  2. the PERP 25/20-level raw order book               (Path C residual)   ── perp
  3. a BOUNDED cross-venue block (relative ratios + a robustly-clipped basis
     LEVEL — NOT the toxic divergence SEQ form)        (Path A enrichment)  ── new
  4. a 60s-pooled 4h long-context series (240×10)       (ModernTCN branch)  ── new

This builder is a CHEAP file-join + light per-second derivation (no Tardis
re-read). The three populated, verified base caches are position-joined
bar-for-bar (timestamps byte-identical, perp y_600 byte-identical — see
``perpY_ridge_gate`` / ``build_duallob_npz`` join proofs):

  * ``data/npz_spot2perp_clean/<day>.npz``  (882d, 2024-01→2026-05)
        X (N,600,64) f32   SPOT 64 hand features      (Path A base)
        X_raw (N,600,20,4) f16  SPOT raw LOB          (Path B tower)
        regime_prior (N,6) f32
        y_600 (N,) f32     LEAK-FREE re-anchored PERP target
        y_mask_600 (N,) bool
        timestamps (N,) i64 us  (window cutoff t = last window second)
  * ``data/npz_perp/<day>.npz``
        X (N,600,64) f32   PERP 64 hand features      (cross block source)
        X_raw (N,600,20,4) f16  PERP raw LOB          (Path C residual source)
        features (64,) object
        timestamps (N,) i64 us  (offset 0 vs clean; CONSTANT — asserted)
  * ``data/mid_cache/<day>.npz``
        sec (86400,) i64    per-second UTC grid (full day)
        spot_mid (86400,) f64
        perp_mid (86400,) f64

OUTPUT (NEW DIR — nothing existing is touched)
----------------------------------------------
  data/npz_v2arch/<YYYY-MM-DD>.npz with keys:
      X               f32 (N,600,72)    64 SPOT hand feats + 8 BOUNDED cross chans
      X_raw           f16 (N,600,20,4)  SPOT raw LOB        (Path B — verbatim)
      X_raw_perp_deep f16 (N,600,20,4)  PERP raw LOB        (Path C residual)
      X_long          f32 (N,240,10)    60s-pooled 4h long-context (leak-safe)
      regime_prior    f32 (N,6)         milestone regime prior (FiLM)
      y_600           f32 (N,)          PERP target (verbatim from clean base)
      y_mask_600      uint8 (N,)
      timestamps      i64 (N,)          window cutoff t (us)  (verbatim)
      cross_names     (8,)  object
      long_names      (10,) object
  plus ``data/npz_v2arch/build_meta.json``.

THE 8 BOUNDED CROSS CHANNELS (no divergence SEQ — those collapse β to −3)
------------------------------------------------------------------------
Identical mechanism to the proven ``build_unified_npz`` CROSS_NAMES set. All
are ratios or BOUNDED levels (never the unbounded perp−spot divergence sequence
that anti-pattern flags as toxic):
  0 x_mid_ratio_log    log(perp_mid/spot_mid)            (≈ basis as a log-ratio)
  1 x_basis_bps        clip((perp−spot)/spot·1e4, ±50)   (the bounded basis LEVEL)
  2 x_spread_ratio_log log((perp_spr+1)/(spot_spr+1))    (rel liquidity tightness)
  3 x_depth_ratio_log  log(perp_L25_depth/spot_L25_depth)(rel depth)
  4 x_obi_diff         clip(perp_obi_L5 − spot_obi_L5,±2)(book-pressure differential)
  5 x_mpdev_diff       perp_mpdev_bps − spot_mpdev_bps   (microprice-dev differential)
  6 x_rvol_ratio_log   log((perp_rvol+e)/(spot_rvol+e))  (rel short-horizon vol)
  7 x_tradeflow_ratio  tanh(perp_ntf/(|spot_ntf|+1))     (rel trade-flow direction)
Channels 0,1,6 come from the per-second mid grid (``mid_cache``), sampled ≤t at
each window second. Channels 2,3,4,5,7 are per-step diffs/ratios of the two
already-aligned 64-feature SEQUENCES (spot = clean-base X, perp = npz_perp X);
they share windows/positions exactly so no grid reconstruction is needed.

LEAK SAFETY
-----------
* Cross channels at window position p use only quantities ≤ the second at p
  (per-second channels via ``searchsorted ≤t``; feature-diff channels inherit
  the base caches' verified ≤t windowing).
* X_long bins are STRICTLY before the bin containing t (``last_complete =
  bin_of_t − 1``), so every long-context bin ends ≤ t. Prior-day tail stitched on
  the LEFT only (never the next day) for a warm 4h lookback at day start.
* y_600 / timestamps copied VERBATIM from the leak-free clean base; this builder
  never derives a target.

CLI
---
  python multi_asset/data/build_v2arch_npz.py --days 2025-04-10 2025-04-11
  python multi_asset/data/build_v2arch_npz.py --all          # skip existing
  python multi_asset/data/build_v2arch_npz.py --all --force  # rebuild
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

_REPO = p.dirname(p.dirname(p.dirname(p.abspath(__file__))))

CLEAN_DIR = p.join(_REPO, "data", "npz_spot2perp_clean")   # base (READ)
PERP_DIR = p.join(_REPO, "data", "npz_perp")               # perp X + raw (READ)
MID_DIR = p.join(_REPO, "data", "mid_cache")               # per-sec mids (READ)
OUT_DIR = p.join(_REPO, "data", "npz_v2arch")              # NEW output dir

INPUT_LEN = 600
LONG_POOL_S = 60
LONG_STEPS = 240            # 240 * 60s = 4h
CLIP_BPS = 50.0
EPS = 1e-8
US = 1_000_000
SHIFT_TOL_US = 11 * US      # allow a small CONSTANT whole-second label offset

# 64-feature column indices (shared spot/perp spot2perp schema; verified present)
J_SPREAD = 3
J_OBI_L5 = 6
J_BID_DEPTH_L25 = 12
J_ASK_DEPTH_L25 = 13
J_NTF = 45
J_MPDEV = 52

# PERP-TRADE feature block (the 16/64 channels computed FROM PERP TRADES — these
# are what drove the milestone npz_v4 to 0.082 raw: spot BOOK + PERP TRADES. The
# clean base X carries spot book + SPOT trades, so we ENRICH Path A with the perp
# venue's trade-flow features here so the DL has the milestone's actual signal
# source. Indices into the shared 64-feature schema (verified by name).
PERP_TRADE_IDX = [43, 44, 45, 46, 47, 48, 49, 50, 51, 54, 55, 57, 58, 59, 61, 62]
PERP_TRADE_NAMES = [
    "pt_buy_volume_1s", "pt_sell_volume_1s", "pt_net_trade_flow_1s",
    "pt_trade_imbalance_1s", "pt_cumulative_net_flow_30s", "pt_cumulative_net_flow_300s",
    "pt_trade_intensity_30s", "pt_vwap_return_1s", "pt_kyle_lambda_30s",
    "pt_vpin_60s", "pt_vpin_300s", "pt_price_impact_30s", "pt_net_flow_x_spread",
    "pt_net_flow_x_vol", "pt_net_flow_rank_1h", "pt_large_trade_arrival_60s",
]

CROSS_NAMES = [
    "x_mid_ratio_log", "x_basis_bps", "x_spread_ratio_log", "x_depth_ratio_log",
    "x_obi_diff", "x_mpdev_diff", "x_rvol_ratio_log", "x_tradeflow_ratio",
]
LONG_NAMES = [
    "l_spot_ret", "l_spot_rvol", "l_spot_obi", "l_spot_spread", "l_spot_vol",
    "l_perp_ret", "l_perp_rvol", "l_perp_obi", "l_perp_spread", "l_basis_bps",
]


# --------------------------------------------------------------------------- #
# per-second helpers (replicated leak-safe primitives from build_unified_npz)  #
# --------------------------------------------------------------------------- #
def _causal_roll_std(x, win):
    """Trailing rolling std over `win` samples, SHIFT(1): value at i uses only
    x[i-win..i-1].  O(T) prefix sums.  <2 obs -> NaN."""
    x = np.asarray(x, np.float64)
    T = x.size
    xs = np.concatenate([[0.0], np.cumsum(x)])
    xs2 = np.concatenate([[0.0], np.cumsum(x * x)])
    i = np.arange(T)
    hi = i
    lo = np.maximum(0, i - win)
    cnt = (hi - lo).astype(np.float64)
    valid = cnt >= 2
    s1 = xs[hi] - xs[lo]
    s2 = xs2[hi] - xs2[lo]
    out_s = np.full(T, np.nan)
    with np.errstate(invalid="ignore", divide="ignore"):
        mean = s1 / np.where(cnt > 0, cnt, 1.0)
        var = s2 / np.where(cnt > 0, cnt, 1.0) - mean * mean
        var = np.where(var < 0, 0.0, var)
        std = np.sqrt(var)
    out_s[valid] = std[valid]
    return out_s


def _sample_le_t(sec, arr, pred_sec):
    """Sample arr (on `sec` grid) at each pred second via ≤t lookup
    (searchsorted right-1). pred before grid -> NaN."""
    sec = np.asarray(sec, np.int64)
    pred_sec = np.asarray(pred_sec, np.int64)
    j = np.searchsorted(sec, pred_sec, side="right") - 1
    valid = j >= 0
    jj = np.clip(j, 0, sec.size - 1)
    v = np.asarray(arr, np.float64)[jj]
    v[~valid] = np.nan
    return v


def _window_secs(pred_secs):
    """(N,600) int64 array of the actual UTC second at every window position.
    Window p ends at pred_sec (the cutoff t); positions are t-599 .. t."""
    pred_secs = np.asarray(pred_secs, np.int64)
    offs = np.arange(-(INPUT_LEN - 1), 1, dtype=np.int64)   # (600,)  [-599..0]
    return pred_secs[:, None] + offs[None, :]               # (N,600)


# --------------------------------------------------------------------------- #
# cross-venue bounded block                                                    #
# --------------------------------------------------------------------------- #
def _build_cross(xs_spot, xp_perp, sec_m, spot_mid, perp_mid, pred_secs):
    """X_cross (N,600,8): 3 per-second-grid channels (mid-ratio/basis/rvol-ratio)
    sampled ≤t at each window second, + 5 per-step feature-diff channels from the
    two aligned 64-feature SEQUENCES. All bounded / ratios (no divergence SEQ)."""
    # per-second common channels from the mid grid (≤t)
    lsm = np.log(np.clip(spot_mid, EPS, None))
    lpm = np.log(np.clip(perp_mid, EPS, None))
    sret = np.zeros_like(lsm); sret[1:] = np.diff(lsm)
    pret = np.zeros_like(lpm); pret[1:] = np.diff(lpm)
    s_rv = _causal_roll_std(sret, 30)
    p_rv = _causal_roll_std(pret, 30)

    # all log-ratios CLIPPED — perp≈spot so these are ~0; a bad bar with mid≈0
    # makes log() blow up (saw max 838), so bound every cross channel.
    mid_ratio_log = np.clip(lpm - lsm, -0.05, 0.05)
    basis_bps = np.clip((perp_mid - spot_mid)
                        / np.where(spot_mid > 0, spot_mid, 1.0) * 1e4,
                        -CLIP_BPS, CLIP_BPS)
    rvol_ratio_log = np.clip(np.log((p_rv + EPS) / (s_rv + EPS)), -4.0, 4.0)

    win_secs = _window_secs(pred_secs)              # (N,600)
    N = win_secs.shape[0]
    flat = win_secs.reshape(-1)

    def _samp(arr):
        return _sample_le_t(sec_m, arr, flat).reshape(N, INPUT_LEN)

    Xc = np.empty((N, INPUT_LEN, 8), dtype=np.float64)
    Xc[:, :, 0] = _samp(mid_ratio_log)
    Xc[:, :, 1] = _samp(basis_bps)
    Xc[:, :, 6] = _samp(rvol_ratio_log)

    # per-step diffs/ratios from the two aligned 64-feature sequences
    Xs = xs_spot.astype(np.float64); Xp = xp_perp.astype(np.float64)   # (N,600,64)
    s_spr = Xs[:, :, J_SPREAD]; p_spr = Xp[:, :, J_SPREAD]
    Xc[:, :, 2] = np.clip(np.log((np.clip(p_spr, 0, None) + 1.0) /
                                 (np.clip(s_spr, 0, None) + 1.0)), -4.0, 4.0)
    sd = np.abs(Xs[:, :, J_BID_DEPTH_L25]) + np.abs(Xs[:, :, J_ASK_DEPTH_L25])
    pd = np.abs(Xp[:, :, J_BID_DEPTH_L25]) + np.abs(Xp[:, :, J_ASK_DEPTH_L25])
    Xc[:, :, 3] = np.clip(np.log((pd + EPS) / (sd + EPS)), -4.0, 4.0)
    Xc[:, :, 4] = np.clip(Xp[:, :, J_OBI_L5] - Xs[:, :, J_OBI_L5], -2.0, 2.0)
    Xc[:, :, 5] = np.clip(Xp[:, :, J_MPDEV] - Xs[:, :, J_MPDEV], -3.0, 3.0)
    Xc[:, :, 7] = np.tanh(Xp[:, :, J_NTF] / (np.abs(Xs[:, :, J_NTF]) + 1.0))

    return np.nan_to_num(Xc, nan=0.0, posinf=0.0, neginf=0.0).astype(np.float32)


# --------------------------------------------------------------------------- #
# long-context 60s-pooled 4h block (leak-safe, cross-day stitched)             #
# --------------------------------------------------------------------------- #
def _build_long(sec_m, spot_mid, perp_mid, pred_secs, prev_tail):
    """X_long (N,240,10): 60s-pooled 4h summary; bins STRICTLY before t's bin.

    Replicates ``build_unified_npz._build_long`` from the mid grid (the only
    per-second source mid_cache provides). Spread channels (3,8) are filled with
    a bounded activity proxy from |ret| (mid_cache carries no per-second spread);
    obi channels (2,7) and vol channel (4) are the same momentum/activity proxies
    the unified builder uses. Returns/basis are the real signal-bearing content
    (the Ridge-confirmed long block = spot/perp ret + rvol + basis)."""
    if prev_tail is not None:
        psec, pmid_s, pmid_p = prev_tail
        keep = psec < sec_m[0]
        if keep.any():
            sec_all = np.concatenate([psec[keep], sec_m])
            sm_all = np.concatenate([pmid_s[keep], spot_mid])
            pm_all = np.concatenate([pmid_p[keep], perp_mid])
        else:
            sec_all, sm_all, pm_all = sec_m, spot_mid, perp_mid
    else:
        sec_all, sm_all, pm_all = sec_m, spot_mid, perp_mid

    lsm = np.log(np.clip(sm_all, EPS, None)); lpm = np.log(np.clip(pm_all, EPS, None))
    sret = np.zeros_like(lsm); sret[1:] = np.diff(lsm)
    pret = np.zeros_like(lpm); pret[1:] = np.diff(lpm)
    basis_all = np.clip((pm_all - sm_all) / np.where(sm_all > 0, sm_all, 1.0) * 1e4,
                        -CLIP_BPS, CLIP_BPS)

    binid = sec_all // LONG_POOL_S
    uniq_bins, inv = np.unique(binid, return_inverse=True)
    nb = uniq_bins.size

    def _binagg(x, how):
        out = np.zeros(nb)
        if how == "sum":
            np.add.at(out, inv, x)
        elif how == "mean":
            cnt = np.zeros(nb); np.add.at(cnt, inv, 1.0)
            np.add.at(out, inv, x); out = out / np.where(cnt > 0, cnt, 1.0)
        elif how == "std":
            m = np.zeros(nb); cnt = np.zeros(nb)
            np.add.at(cnt, inv, 1.0); np.add.at(m, inv, x); m = m / np.where(cnt > 0, cnt, 1.0)
            v = np.zeros(nb); np.add.at(v, inv, (x - m[inv]) ** 2)
            out = np.sqrt(v / np.where(cnt > 0, cnt, 1.0))
        return out

    sret = np.clip(sret, -0.02, 0.02)
    pret = np.clip(pret, -0.02, 0.02)

    bin_spot_ret = np.clip(_binagg(sret, "sum"), -0.05, 0.05)
    bin_spot_rvol = _binagg(sret, "std")
    bin_perp_ret = np.clip(_binagg(pret, "sum"), -0.05, 0.05)
    bin_perp_rvol = _binagg(pret, "std")
    bin_basis = _binagg(basis_all, "mean")
    bin_spot_obi = np.tanh(bin_spot_ret / (bin_spot_rvol + EPS))
    bin_perp_obi = np.tanh(bin_perp_ret / (bin_perp_rvol + EPS))
    bin_spot_vol = np.log1p(_binagg(np.abs(sret), "sum") * 1e4)
    bin_perp_vol = np.log1p(_binagg(np.abs(pret), "sum") * 1e4)
    # spread channels: mid_cache has no per-second spread -> use the bounded
    # per-venue activity proxy (same family as obi/vol proxies above).
    bin_spot_spr = bin_spot_vol
    bin_perp_spr = bin_perp_vol

    bin_feats = np.column_stack([
        bin_spot_ret, bin_spot_rvol, bin_spot_obi, bin_spot_spr, bin_spot_vol,
        bin_perp_ret, bin_perp_rvol, bin_perp_obi, bin_perp_spr, bin_basis,
    ])  # (nb, 10)
    bin_feats = np.nan_to_num(bin_feats, nan=0.0, posinf=0.0, neginf=0.0)

    N = pred_secs.size
    Xlong = np.zeros((N, LONG_STEPS, 10), dtype=np.float32)
    bin_of_pred = pred_secs // LONG_POOL_S
    binpos = {int(b): i for i, b in enumerate(uniq_bins)}
    for wi in range(N):
        last_complete = int(bin_of_pred[wi]) - 1     # strictly before t's bin (≤ t)
        idxs = np.empty(LONG_STEPS, dtype=np.int64)
        for k in range(LONG_STEPS):
            b = last_complete - (LONG_STEPS - 1 - k)
            idxs[k] = binpos.get(b, -1)
        ok = idxs >= 0
        seg = np.zeros((LONG_STEPS, 10), dtype=np.float32)
        seg[ok] = bin_feats[idxs[ok]]
        Xlong[wi] = seg
    return Xlong


# --------------------------------------------------------------------------- #
# day driver                                                                   #
# --------------------------------------------------------------------------- #
def _prev_day(day_str):
    d = dt.date.fromisoformat(day_str) - dt.timedelta(days=1)
    return d.isoformat()


def _load_mid(day_str):
    fp = p.join(MID_DIR, f"{day_str}.npz")
    if not p.exists(fp):
        return None
    d = np.load(fp)
    return d["sec"].astype(np.int64), d["spot_mid"].astype(np.float64), d["perp_mid"].astype(np.float64)


def build_day(day_str: str, force: bool = False) -> str:
    out_fp = p.join(OUT_DIR, f"{day_str}.npz")
    if p.exists(out_fp) and not force:
        return "skip"

    clean_fp = p.join(CLEAN_DIR, f"{day_str}.npz")
    perp_fp = p.join(PERP_DIR, f"{day_str}.npz")
    if not (p.exists(clean_fp) and p.exists(perp_fp)):
        return "missing-base"

    dc = np.load(clean_fp, allow_pickle=True)
    dp = np.load(perp_fp, allow_pickle=True)

    Xc = dc["X"]                       # (N,600,64) spot hand feats
    Xp = dp["X"]                       # (N,600,64) perp hand feats
    if Xc.shape[0] != Xp.shape[0]:
        return f"len-mismatch {Xc.shape[0]} vs {Xp.shape[0]}"
    ts_c = dc["timestamps"].astype(np.int64)
    ts_p = dp["timestamps"].astype(np.int64)
    off = np.unique(ts_p - ts_c)
    if off.size != 1 or abs(int(off[0])) > SHIFT_TOL_US:
        return f"nonconstant-or-large-shift {off[:3]}"

    # Path B (spot) and Path C (perp) raw books
    Xraw_spot = np.asarray(dc["X_raw"], dtype=np.float16)
    Xraw_perp = np.asarray(dp["X_raw"], dtype=np.float16)
    if Xraw_spot.shape != Xraw_perp.shape:
        return f"raw-shape-mismatch {Xraw_spot.shape} vs {Xraw_perp.shape}"

    pred_secs = ts_c // US             # window cutoff t in whole seconds

    mid = _load_mid(day_str)
    if mid is None:
        return "missing-mid"
    sec_m, spot_mid, perp_mid = mid

    # PERP-TRADE block (16 channels from the perp 64-feat at PERP_TRADE_IDX) — the
    # milestone signal source (spot BOOK + PERP TRADES). Sanitised; left RAW for
    # the dataset's per-channel RevIN/normalize (same treatment as spot-64).
    Xptrade = np.nan_to_num(Xp[:, :, PERP_TRADE_IDX].astype(np.float32),
                            nan=0.0, posinf=0.0, neginf=0.0)        # (N,600,16)

    # cross block (8 bounded channels)
    Xcross = _build_cross(Xc, Xp, sec_m, spot_mid, perp_mid, pred_secs)

    # Path A input = [64 spot | 16 perp-trade | 8 cross] = 88 channels.
    # Order matters: spot-64 FIRST so the matched-BASE arm (slice x_channels=64)
    # recovers the exact milestone spot-only Path A.
    X88 = np.concatenate([Xc.astype(np.float32), Xptrade, Xcross], axis=-1)  # (N,600,88)

    # long-context (240×10), with prior-day tail stitched LEFT for warm lookback
    prev = _load_mid(_prev_day(day_str))
    prev_tail = None
    if prev is not None:
        prev_tail = (prev[0], prev[1], prev[2])
    Xlong = _build_long(sec_m, spot_mid, perp_mid, pred_secs, prev_tail)

    # SPOT forward-600s return target (for multi-task spot-primary + perp-aux, and
    # to root-cause the spot-vs-perp gap). Leakage-safe: spot_mid at t and t+600;
    # masked where t+600 exceeds the day (no cross-day return). The perp y_600 from
    # the clean cache is kept as-is; this adds the matched SPOT label.
    sec_max = int(sec_m[-1])
    m_t = _sample_le_t(sec_m, spot_mid, pred_secs)
    m_th = _sample_le_t(sec_m, spot_mid, pred_secs + 600)
    with np.errstate(invalid="ignore", divide="ignore"):
        y_spot_600 = np.log(np.clip(m_th, EPS, None) / np.clip(m_t, EPS, None)).astype(np.float32)
    y_mask_spot_600 = (np.isfinite(y_spot_600) & (m_t > 0) & (m_th > 0)
                       & (pred_secs + 600 <= sec_max)).astype(np.uint8)
    y_spot_600 = np.nan_to_num(y_spot_600, nan=0.0, posinf=0.0, neginf=0.0)

    os.makedirs(OUT_DIR, exist_ok=True)
    np.savez(
        out_fp,
        X=X88.astype(np.float32),
        X_raw=Xraw_spot,
        X_raw_perp_deep=Xraw_perp,
        X_long=Xlong.astype(np.float32),
        regime_prior=np.asarray(dc["regime_prior"], dtype=np.float32),
        y_600=np.asarray(dc["y_600"], dtype=np.float32),
        y_mask_600=np.asarray(dc["y_mask_600"]).astype(np.uint8),
        y_spot_600=y_spot_600,
        y_mask_spot_600=y_mask_spot_600,
        timestamps=ts_c,
        ptrade_names=np.array(PERP_TRADE_NAMES, dtype=object),
        cross_names=np.array(CROSS_NAMES, dtype=object),
        long_names=np.array(LONG_NAMES, dtype=object),
    )
    return "built"


def _all_days() -> list[str]:
    clean = {f[:-4] for f in os.listdir(CLEAN_DIR) if f.endswith(".npz") and f[0].isdigit()}
    perp = {f[:-4] for f in os.listdir(PERP_DIR) if f.endswith(".npz") and f[0].isdigit()}
    mid = {f[:-4] for f in os.listdir(MID_DIR) if f.endswith(".npz") and f[0].isdigit()}
    return sorted(clean & perp & mid)


def main() -> None:
    ap = argparse.ArgumentParser(description="Build npz_v2arch dual-source cache")
    ap.add_argument("--days", nargs="*", default=None)
    ap.add_argument("--all", action="store_true")
    ap.add_argument("--force", action="store_true")
    args = ap.parse_args()

    if args.all:
        days = _all_days()
    elif args.days:
        days = args.days
    else:
        ap.error("pass --days <d...> or --all")

    print(f"[build_v2arch] {len(days)} day(s); out={OUT_DIR}", flush=True)
    t0 = time.time()
    counts: dict[str, int] = {}
    for i, day in enumerate(days):
        try:
            r = build_day(day, force=args.force)
        except Exception as e:           # noqa: BLE001
            r = f"error:{type(e).__name__}:{e}"
        key = r if r in ("built", "skip") else (r.split()[0] if r else "unknown")
        counts[key] = counts.get(key, 0) + 1
        if r not in ("built", "skip"):
            print(f"  {day}: {r}", flush=True)
        if (i + 1) % 50 == 0 or i + 1 == len(days):
            print(f"  [{i+1}/{len(days)}] {counts} ({time.time()-t0:.0f}s)", flush=True)

    meta = {
        "created": dt.datetime.utcnow().isoformat() + "Z",
        "sources": {"clean": CLEAN_DIR, "perp": PERP_DIR, "mid": MID_DIR},
        "keys": {
            "X": "(N,600,88) f32  64 SPOT hand + 16 PERP-trade + 8 bounded cross",
            "X_raw": "(N,600,20,4) f16 SPOT raw LOB (Path B)",
            "X_raw_perp_deep": "(N,600,20,4) f16 PERP raw LOB (Path C)",
            "X_long": "(N,240,10) f32 60s-pooled 4h long-context (leak-safe)",
            "regime_prior": "(N,6) f32",
            "y_600": "(N,) f32 PERP target (verbatim leak-free)",
        },
        "x_layout": "X[:, :, 0:64]=spot64; [64:80]=perp-trade; [80:88]=cross",
        "ptrade_names": PERP_TRADE_NAMES,
        "cross_names": CROSS_NAMES,
        "long_names": LONG_NAMES,
        "counts": counts,
    }
    os.makedirs(OUT_DIR, exist_ok=True)
    with open(p.join(OUT_DIR, "build_meta.json"), "w") as f:
        json.dump(meta, f, indent=2)
    print(f"[build_v2arch] DONE {counts} in {time.time()-t0:.0f}s", flush=True)


if __name__ == "__main__":
    main()
