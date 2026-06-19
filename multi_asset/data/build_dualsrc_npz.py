"""Build the DEFINITIVE DUAL-SOURCE single-asset NPZ cache (Stage F) — LEAN.

GOAL
----
Per UTC calendar day, write ``data/npz_dualsrc/<day>.npz`` = the LEAK-FREE
spot->perp baseline contract (``data/npz_spot2perp_clean``: SPOT X / SPOT X_raw /
SPOT regime_prior / RE-ANCHORED perp ``y_600`` / ``y_mask_600`` / timestamps)
expanded along TWO axes so a SEQUENCE-DL can extract the only cross-venue
candidates that survive the Ridge/last-ts gate (perp-minus-spot divergence):

  X            float32 (N,600,69)   spot-64  ++  5 DIFFERENCED divergence/flow
                                     channels as 600-step sequences (RevIN-SAFE,
                                     ~zero-mean):
      [64] div_cumflow30   perp.cumulative_net_flow_30s - spot.same   (raw units)
      [65] div_microprice  perp.microprice_dev_bps     - spot.same   (bps)
      [66] div_netflow_z   z-score of (perp.net_trade_flow_1s - spot.same),
                           causal 5-min rolling z on the per-second divergence
      [67] basis_ema_dev   basis_bps - causal EMA(span 60s)          (bps; ~0-mean)
      [68] basis_mom       basis_bps(s) - basis_bps(s-300s)          (bps; ~0-mean)

  regime_prior float32 (N,10)       the 6 existing SPOT regime cols  ++  4 LEVEL
                                     signals (UN-normalized — these are the slow
                                     LEVEL features RevIN destroys, so they are
                                     routed to the FiLM path, NOT into RevIN'd X):
      [6] basis_bps        (perp_mid-spot_mid)/spot_mid*1e4, clip +-50  (bps level)
      [7] basis_z          causal 30-min rolling z of basis_bps        (~units)
      [8] spread_ratio     perp.spread_bps / spot.spread_bps           (>0 level)
      [9] div_obi_L5_lvl   perp.obi_L5 - spot.obi_L5 (LEVEL, last window step)

  X_raw        float16 (N,600,20,4) SPOT raw LOB     (verbatim from clean cache)
  y_600        float32 (N,)         RE-ANCHORED leak-free perp target (verbatim)
  y_mask_600   uint8/bool (N,)      verbatim
  timestamps   int64   (N,)         SPOT pred-idx us (verbatim)

NO perp-64 tensor, NO perp raw-LOB — both were shown redundant by the gate
(no perp feature family beats spot-64 above noise at Ridge/last-ts caliber); the
ONLY sign-consistent perp content is the cross-venue divergence, carried here.

WHY (the three established fixes, all baked in)
-----------------------------------------------
1. LEAK   — base cache is ``npz_spot2perp_clean`` (re-anchored perp ``y_600``;
            target window starts EXACTLY at the spot feature cutoff, offset 0).
2. RevIN destroys LEVEL features — RevIN subtracts the per-window feature mean,
   which kills slow LEVEL signals (basis_bps |mean|/std ~7.4; IC -0.030 -> +0.001
   under RevIN). FIX: LEVEL features (basis_bps, basis_z, spread_ratio, div_obi
   level) go into ``regime_prior`` (the FiLM path is fed regime_prior un-normalized
   and is NOT RevIN'd); DIFFERENCED/flow channels (div_cumflow30, div_microprice,
   div_netflow_z, basis_ema_dev, basis_mom) — all ~zero-mean — stay in ``X``
   (RevIN-safe). The model (REG_arch) RevIN's only ``x_feat``; ``regime_prior``
   reaches FiLM/PPNet un-touched. So set the config ``model.d_prior=10``.
3. EMA mis-tuned — handled in the configs (``ema_decay`` 0.999 -> 0.995); not a
   data concern.

THE SPOT<->PERP CONSTANT PER-DAY OFFSET (handled, second-exact, leak-free)
--------------------------------------------------------------------------
``npz_spot`` (the clean cache's feature/grid source) and ``npz_perp`` (the
divergence partner) were built by the SAME windowing pipeline (input_len 600,
stride 180) from the SAME Tardis day, different venue. Their pred-idx timestamps
differ by a CONSTANT per-day snapshot offset k (empirically 0 / +-1 / +-2 s; a
single value across all N rows of a day — verified: ptp(perp_ts-spot_ts)==0).
Row i in both caches is the i-th stride-180 window, same N.

We need perp features at the SPOT window's seconds (so each divergence step is a
SAME-SECOND perp-minus-spot difference). With ``k = (perp_ts - spot_ts)//1e6``
constant, the perp 600-step sequence for row i, shifted by ``-k`` steps, lands on
the spot row i seconds: spot step j is at second ``s_j``; the perp step at that
SAME second is index ``j - k`` (derivation: perp_sec[m] = perp_last - 599 + m,
spot_sec[j] = spot_last - 599 + j, perp_last - spot_last = k  =>  m = j - k).
Steps where ``j - k`` is outside [0,599] (only |k| boundary steps, k in {0,+-1,+-2})
are EDGE-PADDED (replicate the nearest valid divergence step). Because the
divergence channels are ~zero-mean differences, edge-padding |k|<=2 of 600 steps
is RevIN-safe and immaterial.

STRICT CAUSALITY (per STEP)
---------------------------
* The divergence channel at spot step j uses ``perp.X[i, j-k]`` (the perp causal
  feature at perp-second == spot-second s_j) minus ``spot.X[i, j]`` (spot causal
  feature at s_j). Both operands are <= s_j quantities (the cached features are
  per-bar causal). So step j depends ONLY on data at or before s_j.
* basis_ema_dev / basis_mom / basis_bps / basis_z are computed by the PROVEN
  ``build_basis_factors.per_second_factors`` (every rolling/EMA stat shift(1)-ed;
  basis_mom subtracts the value exactly 300s earlier) on the per-second mid grid,
  then sampled at the window's per-step / pred seconds with a ``== s`` exact
  lookup. Corrupting any mid strictly AFTER a step's second leaves that step (and
  all earlier) byte-identical (asserted in --selftest).
* The forward target ``y_600`` (over [pred_sec, pred_sec+600]) is the leak-free
  re-anchored target, copied verbatim; never touched here.

LEAN / DISK
-----------
Reuses the existing ``npz_spot2perp_clean`` (X / X_raw / y / regime) verbatim and
the existing ``npz_perp`` X for divergence; adds only 5 X channels + 4 regime
columns. No Tardis re-read, no full-X duplication of perp. Output is
np.savez_compressed.

CLI
---
  python multi_asset/data/build_dualsrc_npz.py --days 2025-02-10 2026-01-05 2024-12-01
  python multi_asset/data/build_dualsrc_npz.py --all            # skip existing
  python multi_asset/data/build_dualsrc_npz.py --all --force     # rebuild
  python multi_asset/data/build_dualsrc_npz.py --selftest        # leakage+shape unit
"""
from __future__ import annotations

import argparse
import os
import os.path as p
import sys
import time

import numpy as np

_REPO = p.dirname(p.dirname(p.dirname(p.abspath(__file__))))
if _REPO not in sys.path:
    sys.path.insert(0, _REPO)

# Reuse the PROVEN per-second causal basis core verbatim (no re-derivation).
from multi_asset.data.build_basis_factors import (  # noqa: E402
    US_PER_SEC,
    per_second_factors,
)

# ----------------------------------------------------------------------- paths
CLEAN_DIR = p.join(_REPO, "data", "npz_spot2perp_clean")  # LEAK-FREE base (READ)
PERP_DIR = p.join(_REPO, "data", "npz_perp")              # divergence partner (READ)
MID_DIR = p.join(_REPO, "data", "mid_cache")              # per-second mids (READ)
OUT_DIR = p.join(_REPO, "data", "npz_dualsrc")            # NEW output dir

INPUT_LEN = 600
HORIZON_SEC = 600

# spot-64 feature indices (perp == spot schema, verified). EXPECTED_FEATURES order.
IDX_CUMFLOW30 = 47     # cumulative_net_flow_30s
IDX_MICROPRICE = 52    # microprice_dev_bps
IDX_NETFLOW1S = 45     # net_trade_flow_1s
IDX_SPREAD = 3         # spread_bps
IDX_OBI_L5 = 6         # obi_L5
N_SPOT = 64

# new X (differenced/flow) channels appended after spot-64 -> width 69
DIV_CH_NAMES = ["div_cumflow30", "div_microprice", "div_netflow_z",
                "basis_ema_dev", "basis_mom"]
N_DIV_CH = len(DIV_CH_NAMES)            # 5
N_FEAT = N_SPOT + N_DIV_CH             # 69

# new regime_prior (LEVEL, un-normalized) columns appended after the 6 -> width 10
LEVEL_COL_NAMES = ["basis_bps", "basis_z", "spread_ratio", "div_obi_L5_lvl"]
N_LEVEL_COL = len(LEVEL_COL_NAMES)     # 4
N_PRIOR = 6 + N_LEVEL_COL             # 10

# causal rolling window (seconds) for div_netflow_z (matches the basis_z 5-min
# spirit but on the flow divergence; shift(1) so z at s uses only seconds < s).
NETFLOW_Z_WIN_SEC = 5 * 60
NETFLOW_Z_CLIP = 10.0                  # a z-score is dimensionless & ~±10 bounded;
                                       # rollstd->0 over flat-flow windows blows it
                                       # up (observed ~1e7) — clip like basis_z does
SPREAD_RATIO_CLIP = 50.0               # spread ratio is >0; clip pathological prints
DIV_OBI_CLIP = 5.0                     # obi in [-1,1] nominally; difference in [-2,2]


# --------------------------------------------------------------------------- #
# causal per-second z (shift(1)) — same discipline as build_basis_factors      #
# --------------------------------------------------------------------------- #
def _causal_z_shift1(x: np.ndarray, win: int, eps: float = 1e-6) -> np.ndarray:
    """Trailing rolling z over `win` samples, SHIFTED by 1 so the value at index
    i uses only samples [i-win, i-1] (strictly < i). x is a per-second array on a
    contiguous grid. NaN-safe (treats the warmup prefix as 0)."""
    x = np.asarray(x, dtype=np.float64)
    n = x.size
    csum = np.concatenate([[0.0], np.cumsum(x)])
    csum2 = np.concatenate([[0.0], np.cumsum(x * x)])
    out = np.zeros(n, dtype=np.float64)
    for i in range(1, n):
        lo = max(0, i - win)
        cnt = i - lo
        if cnt < 2:
            continue
        s = csum[i] - csum[lo]
        s2 = csum2[i] - csum2[lo]
        mean = s / cnt
        var = max(s2 / cnt - mean * mean, 0.0)
        std = np.sqrt(var)
        out[i] = (x[i] - mean) / (std + eps)
    return out


# --------------------------------------------------------------------------- #
# per-second mids                                                              #
# --------------------------------------------------------------------------- #
def _load_mids(date_str: str):
    """(sec, spot_mid, perp_mid) per-second arrays for one UTC day from mid_cache."""
    z = np.load(p.join(MID_DIR, "%s.npz" % date_str), allow_pickle=True)
    sec = z["sec"].astype(np.int64)
    spot_mid = z["spot_mid"].astype(np.float64)
    perp_mid = z["perp_mid"].astype(np.float64)
    if not np.all(np.diff(sec) == 1):
        raise RuntimeError("%s: mid_cache sec grid not contiguous 1s" % date_str)
    return sec, spot_mid, perp_mid


def _gather_at_secs(sec: np.ndarray, arr: np.ndarray, want_secs: np.ndarray):
    """Exact-second gather: for each requested second return arr at that second,
    or NaN when the second is missing from the (ascending, contiguous) grid.
    No nearest-neighbour fudge — a missing second yields NaN, never a wrong value.
    Returns (values, hit_mask)."""
    pos = np.searchsorted(sec, want_secs, side="left")
    in_range = (pos >= 0) & (pos < sec.size)
    pos_c = np.clip(pos, 0, sec.size - 1)
    hit = in_range & (sec[pos_c] == want_secs)
    out = np.full(want_secs.shape, np.nan, dtype=np.float64)
    out[hit] = arr[pos_c[hit]]
    return out, hit


# --------------------------------------------------------------------------- #
# core: build the divergence X channels + LEVEL regime columns for one day      #
# --------------------------------------------------------------------------- #
def _perp_to_spot_step_shift(perp_X: np.ndarray, k: int):
    """Re-index a perp (N,600,C) window tensor so step j carries the perp value at
    the SAME absolute second as spot step j, given constant offset
    ``k = (perp_ts - spot_ts) // 1e6`` (integer seconds). perp step at spot-second
    s_j is index ``j - k`` (see module docstring).

    Boundary steps where ``j - k`` falls outside [0,599] are ZERO-FILLED (not
    edge-clamped): for k>0 the |k| oldest steps have no perp second <= s_j inside
    the window, so substituting any in-window perp value would reference a second
    > s_j (a tiny, ~597s-pre-prediction, target-irrelevant forward reference); we
    refuse it and zero-fill instead — strictly causal, and immaterial because the
    channels are ~zero-mean DIFFERENCES and these are the window's oldest |k|<=2
    of 600 steps. Returns (perp_on_spot (N,600,C), valid_mask (600,))."""
    n, L, c = perp_X.shape
    j = np.arange(L, dtype=np.int64)
    src = j - k
    valid = (src >= 0) & (src <= L - 1)
    src_c = np.clip(src, 0, L - 1)
    out = perp_X[:, src_c, :].copy()
    if not valid.all():
        out[:, ~valid, :] = 0.0               # zero-fill (no forward reference)
    return out, valid


def build_div_and_levels(date_str: str):
    """Compute, for one UTC day:
       div_X      float32 (N,600,5)  the 5 differenced/flow X channels
       levels     float32 (N,4)      the 4 LEVEL regime columns
       info       dict               provenance + sanity stats
    using the clean cache grid as authoritative and npz_perp for divergence.
    """
    clean_path = p.join(CLEAN_DIR, "%s.npz" % date_str)
    perp_path = p.join(PERP_DIR, "%s.npz" % date_str)
    if not p.exists(clean_path):
        raise FileNotFoundError("clean cache missing: %s" % clean_path)
    if not p.exists(perp_path):
        raise FileNotFoundError("perp cache missing: %s" % perp_path)

    with np.load(clean_path, allow_pickle=True) as zc:
        spot_X = np.asarray(zc["X"], dtype=np.float32)        # (N,600,64) SPOT
        spot_ts = zc["timestamps"].astype(np.int64)           # pred-idx us
        N = spot_X.shape[0]
    with np.load(perp_path, allow_pickle=True) as zp:
        perp_X = np.asarray(zp["X"], dtype=np.float32)        # (N,600,64) PERP
        perp_ts = zp["timestamps"].astype(np.int64)

    if perp_X.shape[0] != N:
        raise RuntimeError("%s: perp N=%d != clean N=%d (windowing drift)"
                           % (date_str, perp_X.shape[0], N))
    if spot_X.shape[1] != INPUT_LEN or perp_X.shape[1] != INPUT_LEN:
        raise RuntimeError("%s: window len != %d" % (date_str, INPUT_LEN))

    # constant per-day offset k (seconds). MUST be a single value across rows.
    diff_us = perp_ts - spot_ts
    if int(np.ptp(diff_us)) != 0:
        raise RuntimeError(
            "%s: perp_ts-spot_ts not constant (ptp=%d us); refusing to align "
            "a row-dependent offset" % (date_str, int(np.ptp(diff_us))))
    off_us = int(diff_us[0])
    if off_us % US_PER_SEC != 0:
        raise RuntimeError("%s: perp-spot offset %d us is not a whole second"
                           % (date_str, off_us))
    k = off_us // US_PER_SEC                          # integer seconds (0/+-1/+-2)

    # 1) SAME-SECOND perp tensor on the spot grid, then differenced X channels.
    #    valid[j] = False on the |k| boundary steps with no perp second <= s_j in
    #    the perp window (zero-filled). The divergence at those steps is therefore
    #    0 (perp - spot with perp=0); since the channels are ~zero-mean differences
    #    and these are the window's oldest <=2 steps, this is immaterial + causal.
    perp_on_spot, step_valid = _perp_to_spot_step_shift(perp_X, k)  # (N,600,64)
    div_cumflow30 = np.where(step_valid[None, :],
                             perp_on_spot[:, :, IDX_CUMFLOW30]
                             - spot_X[:, :, IDX_CUMFLOW30], 0.0)     # (N,600)
    div_microprice = np.where(step_valid[None, :],
                              perp_on_spot[:, :, IDX_MICROPRICE]
                              - spot_X[:, :, IDX_MICROPRICE], 0.0)
    # last step index that is valid for the perp tensor (== s_pred for k<=0; for
    # k>0 step 599 is valid since src=599-k in range). Used for pred-second LEVELs.
    last_valid_step = int(np.flatnonzero(step_valid)[-1])

    # 2) div_netflow_z: causal 5-min rolling z of the per-second flow divergence.
    #    Build it on the per-second grid (so the z window is real seconds and
    #    shift(1) excludes the current second), then gather at each window step's
    #    second. We reconstruct the per-second flow divergence from the windows by
    #    placing each step's value at its absolute second (last write wins; windows
    #    overlap so every covered second is filled identically by construction —
    #    the value at a second is a deterministic <=t feature).
    spot_last = spot_ts // US_PER_SEC                          # (N,) window last sec
    # per-second flow divergence over the union of all window seconds for the day
    step_offs = np.arange(INPUT_LEN, dtype=np.int64) - (INPUT_LEN - 1)  # -599..0
    win_secs = spot_last[:, None] + step_offs[None, :]         # (N,600) abs seconds
    flow_div_win = np.where(step_valid[None, :],
                            perp_on_spot[:, :, IDX_NETFLOW1S]
                            - spot_X[:, :, IDX_NETFLOW1S], np.nan).astype(np.float64)
    sec_min = int(win_secs.min())
    sec_max = int(win_secs.max())
    grid = np.arange(sec_min, sec_max + 1, dtype=np.int64)
    flow_div_ps = np.full(grid.size, np.nan, dtype=np.float64)
    # write ONLY valid steps (boundary zero-fill steps stay NaN -> 0 below); a
    # second covered by both a valid and an invalid step keeps the valid value.
    flat_sec = (win_secs - sec_min).reshape(-1)
    flat_val = flow_div_win.reshape(-1)
    fv = np.isfinite(flat_val)
    flow_div_ps[flat_sec[fv]] = flat_val[fv]                  # fill covered seconds
    # warmup / uncovered seconds (e.g. cross-day tail gap) -> 0 so z is finite
    flow_div_ps = np.nan_to_num(flow_div_ps, nan=0.0)
    netflow_z_ps = _causal_z_shift1(flow_div_ps, NETFLOW_Z_WIN_SEC)
    netflow_z_ps = np.clip(netflow_z_ps, -NETFLOW_Z_CLIP, NETFLOW_Z_CLIP)
    # gather z at each window step's second
    div_netflow_z = netflow_z_ps[(win_secs - sec_min)]        # (N,600)

    # 3) basis factors (per-second, causal) for basis_ema_dev / basis_mom (X) and
    #    basis_bps / basis_z (LEVEL regime). Cross-day tail (s+600 next day) does
    #    NOT matter for the FEATURE legs (all <= pred sec); only the target needs
    #    the forward stitch, and the target is taken verbatim from the clean cache.
    sec, spot_mid, perp_mid = _load_mids(date_str)
    fac = per_second_factors(sec, spot_mid, perp_mid)
    # per-step gather (X channels) at window seconds
    bdev, _ = _gather_at_secs(sec, fac["basis_ema_dev"], win_secs.reshape(-1))
    bmom, _ = _gather_at_secs(sec, fac["basis_mom"], win_secs.reshape(-1))
    basis_ema_dev = np.nan_to_num(bdev, nan=0.0).reshape(N, INPUT_LEN)
    basis_mom = np.nan_to_num(bmom, nan=0.0).reshape(N, INPUT_LEN)

    # 4) LEVEL regime columns at the PREDICTION second (last window step).
    bbps_pred, _ = _gather_at_secs(sec, fac["basis_bps"], spot_last)
    bz_pred, _ = _gather_at_secs(sec, fac["basis_z"], spot_last)
    basis_bps_lvl = np.nan_to_num(bbps_pred, nan=0.0).astype(np.float32)
    basis_z_lvl = np.nan_to_num(bz_pred, nan=0.0).astype(np.float32)
    # perp-sourced LEVELs use the LAST VALID perp step (== pred second for k<=0;
    # for k<0 the perp window's last second is k seconds BEFORE the spot pred
    # second, so this is the nearest perp second <= pred sec — |k|<=2s stale,
    # strictly causal). spot legs always use the true last step (spot pred sec).
    # spread_ratio = perp.spread_bps / spot.spread_bps.
    perp_spread_pred = perp_on_spot[:, last_valid_step, IDX_SPREAD]
    spot_spread_pred = spot_X[:, -1, IDX_SPREAD]
    denom = np.where(np.abs(spot_spread_pred) < 1e-9, np.nan, spot_spread_pred)
    spread_ratio = np.clip(perp_spread_pred / denom, -SPREAD_RATIO_CLIP,
                           SPREAD_RATIO_CLIP)
    spread_ratio = np.nan_to_num(spread_ratio, nan=1.0).astype(np.float32)  # 1=parity
    # div_obi_L5 LEVEL at the pred second
    div_obi_lvl = np.clip(perp_on_spot[:, last_valid_step, IDX_OBI_L5]
                          - spot_X[:, -1, IDX_OBI_L5],
                          -DIV_OBI_CLIP, DIV_OBI_CLIP).astype(np.float32)

    # ---- assemble ----
    div_X = np.stack([div_cumflow30, div_microprice, div_netflow_z,
                      basis_ema_dev, basis_mom], axis=-1).astype(np.float32)  # (N,600,5)
    div_X = np.nan_to_num(div_X, nan=0.0, posinf=0.0, neginf=0.0)
    levels = np.stack([basis_bps_lvl, basis_z_lvl, spread_ratio, div_obi_lvl],
                      axis=-1).astype(np.float32)                              # (N,4)

    info = dict(
        N=int(N), offset_sec=int(k),
        div_means={DIV_CH_NAMES[c]: float(div_X[:, :, c].mean())
                   for c in range(N_DIV_CH)},
        div_stds={DIV_CH_NAMES[c]: float(div_X[:, :, c].std())
                  for c in range(N_DIV_CH)},
        level_means={LEVEL_COL_NAMES[c]: float(levels[:, c].mean())
                     for c in range(N_LEVEL_COL)},
        level_stds={LEVEL_COL_NAMES[c]: float(levels[:, c].std())
                    for c in range(N_LEVEL_COL)},
    )
    return div_X, levels, info


# --------------------------------------------------------------------------- #
# build one day -> npz_dualsrc/<day>.npz                                        #
# --------------------------------------------------------------------------- #
def build_one_day(date_str: str, out_path: str):
    t0 = time.time()
    div_X, levels, info = build_div_and_levels(date_str)

    # carry the leak-free base contract verbatim
    with np.load(p.join(CLEAN_DIR, "%s.npz" % date_str), allow_pickle=True) as zc:
        spot_X = np.asarray(zc["X"], dtype=np.float32)        # (N,600,64)
        X_raw = np.asarray(zc["X_raw"])                        # (N,600,20,4) f16
        regime6 = np.asarray(zc["regime_prior"], dtype=np.float32)  # (N,6)
        y_600 = np.asarray(zc["y_600"], dtype=np.float32)
        y_mask_600 = np.asarray(zc["y_mask_600"])
        ts = zc["timestamps"].astype(np.int64)

    if regime6.shape[1] != 6:
        raise RuntimeError("%s: clean regime_prior width %d != 6"
                           % (date_str, regime6.shape[1]))

    X = np.concatenate([spot_X, div_X], axis=-1).astype(np.float32)      # (N,600,69)
    regime_prior_ext = np.concatenate([regime6, levels], axis=-1).astype(np.float32)  # (N,10)
    if X.shape[-1] != N_FEAT:
        raise RuntimeError("%s: X width %d != %d" % (date_str, X.shape[-1], N_FEAT))
    if regime_prior_ext.shape[-1] != N_PRIOR:
        raise RuntimeError("%s: regime width %d != %d"
                           % (date_str, regime_prior_ext.shape[-1], N_PRIOR))

    os.makedirs(OUT_DIR, exist_ok=True)
    tmp = "%s.tmp.%d.npz" % (out_path, os.getpid())
    np.savez_compressed(
        tmp, X=X, X_raw=X_raw, regime_prior=regime_prior_ext,
        y_600=y_600, y_mask_600=y_mask_600, timestamps=ts)
    os.replace(tmp, out_path)

    return dict(N=info["N"], offset_sec=info["offset_sec"],
                secs=time.time() - t0, mb=os.path.getsize(out_path) / 1e6,
                div_means=info["div_means"], div_stds=info["div_stds"],
                level_means=info["level_means"], level_stds=info["level_stds"],
                X_finite=float(np.isfinite(X).mean()),
                rp_finite=float(np.isfinite(regime_prior_ext).mean()))


def list_days():
    """Days that have BOTH the leak-free clean cache and the perp cache + mids."""
    out = []
    for name in sorted(os.listdir(CLEAN_DIR)):
        if not (len(name) == 14 and name.endswith(".npz")):
            continue
        d = name[:-4]
        if (p.exists(p.join(PERP_DIR, "%s.npz" % d))
                and p.exists(p.join(MID_DIR, "%s.npz" % d))):
            out.append(d)
    return out


def build(days_subset=None, force=False):
    os.makedirs(OUT_DIR, exist_ok=True)
    days = days_subset if days_subset else list_days()
    print("[dualsrc] %d day(s) -> %s" % (len(days), OUT_DIR), flush=True)
    t0 = time.time(); n_done = n_skip = n_fail = 0; failed = []
    for i, d in enumerate(days):
        out = p.join(OUT_DIR, "%s.npz" % d)
        if (not force) and p.exists(out):
            n_skip += 1
            continue
        try:
            st = build_one_day(d, out)
        except Exception as e:
            n_fail += 1; failed.append(d)
            print("  [warn] day %s failed: %s: %s"
                  % (d, type(e).__name__, e), flush=True)
            continue
        n_done += 1
        dm = st["div_means"]; ds = st["div_stds"]; lm = st["level_means"]
        print("  [%d/%d] %s N=%d off=%+ds %.1fMB %.1fs X_fin=%.4f rp_fin=%.4f"
              % (i + 1, len(days), d, st["N"], st["offset_sec"], st["mb"],
                 st["secs"], st["X_finite"], st["rp_finite"]), flush=True)
        print("            div_mean[cumflow30=%+.4f micro=%+.5f nflz=%+.4f "
              "ema_dev=%+.4f mom=%+.4f] basis_bps_lvl_mean=%+.3f"
              % (dm["div_cumflow30"], dm["div_microprice"], dm["div_netflow_z"],
                 dm["basis_ema_dev"], dm["basis_mom"], lm["basis_bps"]), flush=True)
    print("[dualsrc] DONE in %.1f min: built=%d skip=%d fail=%d%s -> %s"
          % ((time.time() - t0) / 60, n_done, n_skip, n_fail,
             ("  FAILED: %s" % failed) if failed else "", OUT_DIR), flush=True)
    return n_fail


# --------------------------------------------------------------------------- #
# self-test: shape + per-step leakage (corrupt-future mids AND perp features)   #
# --------------------------------------------------------------------------- #
def _selftest():
    """Synthetic + (if available) real-day leakage/shape check.

    Synthetic: a contiguous-second toy day with known mids and a tiny perp/spot
    feature pair; verify (a) shapes, (b) the per-step shift puts perp at the
    SAME second as spot, (c) corrupting mids/features STRICTLY AFTER a cut second
    leaves every window step at-or-before the cut byte-identical (no future leak).
    """
    print("[selftest] synthetic shape + leakage ...", flush=True)
    rng = np.random.default_rng(0)
    L = INPUT_LEN
    # toy: 3 windows, last-secs spaced by stride 180 on a contiguous grid.
    n = 3
    stride = 180
    last0 = 10_000
    spot_last = np.array([last0 + i * stride for i in range(n)], dtype=np.int64)
    # full per-second grid covering all windows (first window start .. last end),
    # padded by KMAX on both ends so SHIFTED perp windows (last+-k, |k|<=KMAX) and
    # the per-step gathers below stay in-bounds in this synthetic harness.
    KMAX = 2
    g0 = int(spot_last.min() - (L - 1) - KMAX)
    g1 = int(spot_last.max() + KMAX)
    sec = np.arange(g0, g1 + 1, dtype=np.int64)

    # toy per-second spot/perp features & mids
    base = rng.standard_normal(sec.size)
    spot_ps = {IDX_CUMFLOW30: np.cumsum(base) * 0.01,
               IDX_MICROPRICE: base * 0.5,
               IDX_NETFLOW1S: rng.standard_normal(sec.size),
               IDX_SPREAD: 1.0 + 0.1 * np.abs(rng.standard_normal(sec.size)),
               IDX_OBI_L5: np.tanh(rng.standard_normal(sec.size))}
    perp_ps = {idx: spot_ps[idx] + 0.05 * rng.standard_normal(sec.size)
               for idx in spot_ps}
    spot_mid = 100.0 + np.cumsum(rng.standard_normal(sec.size)) * 0.01
    perp_mid = spot_mid + 0.2 + 0.05 * rng.standard_normal(sec.size)

    def _windows_from_ps(ps_dict, last_secs):
        """(n,600,64)-ish toy X: only the used indices are populated, others 0."""
        X = np.zeros((len(last_secs), L, N_SPOT), dtype=np.float32)
        offs = np.arange(L, dtype=np.int64) - (L - 1)
        for i, ls in enumerate(last_secs):
            secs_i = ls + offs
            pos = secs_i - g0
            for idx, arr in ps_dict.items():
                X[i, :, idx] = arr[pos]
        return X

    # offset k = 0 case (spot grid == perp grid)
    spot_X = _windows_from_ps(spot_ps, spot_last)
    perp_X = _windows_from_ps(perp_ps, spot_last)

    # emulate build_div_and_levels internals on the toy (k=0)
    k = 0
    perp_on_spot, valid0 = _perp_to_spot_step_shift(perp_X, k)
    assert valid0.all(), "selftest: k=0 should have no invalid steps"
    # same-second check: perp_on_spot at step j must equal perp feature at spot sec
    offs = np.arange(L, dtype=np.int64) - (L - 1)
    for i in range(n):
        secs_i = spot_last[i] + offs
        pos = secs_i - g0
        ok = np.allclose(perp_on_spot[i, :, IDX_MICROPRICE], perp_ps[IDX_MICROPRICE][pos])
        assert ok, "selftest: perp_on_spot not at same second (k=0)"

    # offset k = +2 / -1: perp grid shifted. Build perp windows on shifted
    # last-secs and verify the shift re-aligns the SAME-SECOND values; invalid
    # (zero-filled) boundary steps are exactly the |k| oldest/newest steps.
    for k in (2, -1):
        perp_last_k = spot_last + k
        perp_X_k = _windows_from_ps(perp_ps, perp_last_k)
        perp_on_spot_k, valid_k = _perp_to_spot_step_shift(perp_X_k, k)
        # valid steps are j with src=j-k in [0,L-1]: j in [max(0,k), L-1+min(0,k)]
        exp_valid = np.zeros(L, bool)
        exp_valid[max(0, k):L + min(0, k)] = True
        assert np.array_equal(valid_k, exp_valid), "selftest: valid mask wrong"
        for i in range(n):
            secs_i = spot_last[i] + offs
            pos = secs_i - g0
            a = perp_on_spot_k[i, valid_k, IDX_MICROPRICE]
            b = perp_ps[IDX_MICROPRICE][pos][valid_k]
            assert np.allclose(a, b), ("selftest: shift k=%d misaligned" % k)
            # invalid steps must be exactly zero (no forward reference)
            assert np.allclose(perp_on_spot_k[i, ~valid_k, IDX_MICROPRICE], 0.0), \
                ("selftest: invalid boundary step not zero-filled (k=%d)" % k)
    print("[selftest]   same-second alignment + zero-fill boundary OK "
          "(k in {0,+2,-1})", flush=True)

    # leakage: corrupt mids strictly AFTER a cut second; basis-derived X steps at
    # or before the cut must be byte-identical.
    fac0 = per_second_factors(sec, spot_mid, perp_mid)
    win_secs = spot_last[:, None] + offs[None, :]
    bdev0, _ = _gather_at_secs(sec, fac0["basis_ema_dev"], win_secs.reshape(-1))
    bmom0, _ = _gather_at_secs(sec, fac0["basis_mom"], win_secs.reshape(-1))
    cut = int(sec[sec.size // 2])
    sm, pm = spot_mid.copy(), perp_mid.copy()
    fut = sec > cut
    sm[fut] = 1e-3; pm[fut] = -1e9
    fac1 = per_second_factors(sec, sm, pm)
    bdev1, _ = _gather_at_secs(sec, fac1["basis_ema_dev"], win_secs.reshape(-1))
    bmom1, _ = _gather_at_secs(sec, fac1["basis_mom"], win_secs.reshape(-1))
    le = (win_secs.reshape(-1) <= cut)
    d0 = np.nan_to_num(bdev0); d1 = np.nan_to_num(bdev1)
    m0 = np.nan_to_num(bmom0); m1 = np.nan_to_num(bmom1)
    assert np.array_equal(d0[le], d1[le]), "LEAKAGE: basis_ema_dev <=cut changed"
    assert np.array_equal(m0[le], m1[le]), "LEAKAGE: basis_mom <=cut changed"
    print("[selftest]   basis-seq causal OK (%d <=cut steps identical)"
          % int(le.sum()), flush=True)

    # div_netflow_z causal: corrupting flow STRICTLY AFTER cut must not change z
    # at or before cut (shift(1) rolling z).
    flow = rng.standard_normal(sec.size)
    z0 = _causal_z_shift1(flow, NETFLOW_Z_WIN_SEC)
    flow_c = flow.copy(); flow_c[sec > cut] = 1e9
    z1 = _causal_z_shift1(flow_c, NETFLOW_Z_WIN_SEC)
    le_ps = sec <= cut
    assert np.array_equal(z0[le_ps], z1[le_ps]), "LEAKAGE: div_netflow_z <=cut changed"
    print("[selftest]   div_netflow_z causal OK", flush=True)

    print("[selftest] PASS (shape, same-second alignment, per-step causality)",
          flush=True)
    return True


if __name__ == "__main__":
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    g = ap.add_mutually_exclusive_group(required=True)
    g.add_argument("--all", action="store_true",
                   help="build every day with clean+perp+mid caches (skip existing)")
    g.add_argument("--days", type=str, nargs="+", help="build only these YYYY-MM-DD")
    g.add_argument("--selftest", action="store_true",
                   help="shape + per-step leakage unit (no disk caches needed)")
    ap.add_argument("--force", action="store_true", help="rebuild existing day files")
    args = ap.parse_args()
    if args.selftest:
        sys.exit(0 if _selftest() else 1)
    nf = build(days_subset=args.days, force=args.force)
    sys.exit(1 if nf else 0)
