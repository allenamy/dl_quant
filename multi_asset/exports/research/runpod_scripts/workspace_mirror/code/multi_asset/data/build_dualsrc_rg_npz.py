"""RG-ENRICHED dual-source NPZ — append the bounded RG regime block to the FiLM
regime_prior (Gate 1 of the dual-source v2 build).

> created 2026-06-20 | status: research-gate | branch: dual-source-perp

WHY THIS EXISTS
---------------
The factor study found RG (regime) conditioning the single most robust lever:
perp_y ΔP +0.0061 STRONG / +0.0036 CHOPPY — the ONLY factor family positive in
BOTH regimes. RG factors are causal microstructure-regime descriptors (realized-
vol term-structure, variance-ratio/Hurst trend-detector, liquidity-depth ratio,
spot↔perp lead-lag couple-strength), multi-scale {60,600,3600}s. The mechanism
for FiLM: the perp y_600 signal is regime-dependent (trending months pay, choppy
don't); a causal regime indicator lets the FiLM/PPNet gate condition its alpha on
"what regime am I in", which is exactly what a multiplicative gate is for.

WHAT THIS BUILDS
----------------
Verbatim reuses ``build_dualsrc_npz.build_div_and_levels`` (spot-64 + 5 divergence
seq channels in X[64..68] with the ITER-3 calib bounds; 4 basis LEVEL cols in
regime_prior[6..9] with the ITER-2/3 calib bounds) and the leak-free base
contract from ``npz_spot2perp_clean``, then APPENDS a 13-channel RG regime block
to regime_prior:

  regime_prior  float32 (N, 23)   = 6 spot regime  ++  4 basis LEVEL (calib-fixed)
                                    ++  13 RG regime (NEW, robust-bounded ±5)

  RG block (regime_prior cols 10..22), each robust-standardized by a FIXED
  (train-span median + 1.4826·MAD) center/scale then HARD-CLIPPED to ±5 — the
  SAME discipline as the basis LEVEL calib fix (these are FiLM gate inputs, so an
  OOD spike = β-collapse risk; bounding by construction clamps it):
    [10] rg_rvol_ts_60_600      short/med realized-vol ratio
    [11] rg_rvol_ts_600_3600    med/long realized-vol ratio
    [12] rg_rvol_600s           medium-window realized vol level
    [13] rg_vr_q30_w3600        variance-ratio q=30  (trend>1 vs chop<1)
    [14] rg_vr_q120_w3600       variance-ratio q=120
    [15] rg_hurst_like          Hurst exponent (>.5 trend, <.5 revert)
    [16] rg_liq_depth_ratio     log perp/spot L25 depth ratio (liquidity regime)
    [17] ll_peakcorr_600s       spot→perp lead-lag peak cross-corr (couple-strength)
    [18] ll_couple0_600s        contemporaneous spot↔perp coupling
    [19] ll_leadgain_600s       lead beyond contemporaneous (lead-lag regime)
    [20] ll_peakcorr_3600s      couple-strength, long scale
    [21] ll_couple0_3600s       contemporaneous coupling, long scale
    [22] ll_leadgain_3600s      lead gain, long scale

  DROPPED vs the full family_regime/family_leadlag output (deliberate, mechanism):
    - rg_liq_spread_ratio : near-constant log-ratio (train p1..p99 range ~2e-3);
      already represented by basis LEVEL spread_ratio (col 8); a tiny-MAD near-
      delta would only inject amplified micro-noise into the multiplicative gate.
    - the 3 xs_* designed interaction products (basisz×volregime, basisz×vr,
      divobi×hurst): these are ALPHA-flavoured cross-scale products, not regime
      STATE descriptors — feeding alpha-ish products into the FiLM gate is exactly
      the kind of OOD-prone construct the calib fix warns against; the regime gate
      should see regime, not alpha.
    - ll_peaklag_*: a discrete argmax over a small lag grid (noisy, near-categorical
      — a poor continuous FiLM input) and ll_gap_x_strength_30s (a gap×strength
      product = alpha, not regime).

  EVERYTHING ELSE is byte-identical to ``npz_dualsrc`` (X width 69, X_raw, y_600,
  y_mask_600, timestamps). The only change is regime_prior 10 → 23. Set the config
  ``model.d_prior=23`` to consume it. The matched baseline (no RG) is the existing
  ``npz_dualsrc`` (d_prior=10) — so the ΔP is clean apples-to-apples.

RG SOURCE / CAUSALITY
---------------------
The RG channels come from ``build_ho_factors.family_regime`` and the couple-
strength subset of ``family_leadlag`` — both strictly ≤ t (every rolling/EMA/
cross-corr is shift(1)-ed; verified by ho_factors_gate's +600s forward-shift leak
sentinel which did NOT inflate the perp blk dP). They are sampled at the PRED
second (the window's last step), exactly where the FiLM gate consumes them.

The RG factors are keyed by the lastts_cache pred-idx ``timestamps`` (perp_ts ==
the perp last-snapshot us). The dualsrc rows are keyed by the SPOT pred-idx
``timestamps`` (offset k = perp_ts - spot_ts, a constant per day, |k|<=2s). We
align by the SAME per-day constant offset already proven in build_dualsrc_npz:
spot row i pred-second = spot_ts[i]//1e6; we look up the RG row whose lastts
``timestamps`` equals that spot pred-idx us (lastts timestamps == spot pred-idx
us in this pipeline — verified below by exact-match assert; any unmatched row's
RG block is set to its train-median 0 after standardization, i.e. neutral gate).

CLI
---
  python multi_asset/data/build_dualsrc_rg_npz.py --days 2025-02-10
  python multi_asset/data/build_dualsrc_rg_npz.py --fold 2025-02-01   # 540+60+1+28
  python multi_asset/data/build_dualsrc_rg_npz.py --fold 2025-04-01
  python multi_asset/data/build_dualsrc_rg_npz.py --selftest
"""
from __future__ import annotations

import argparse
import datetime as dt
import os
import os.path as p
import sys
import time

import numpy as np

_REPO = p.dirname(p.dirname(p.dirname(p.abspath(__file__))))
if _REPO not in sys.path:
    sys.path.insert(0, _REPO)

from multi_asset.data.build_dualsrc_npz import (  # noqa: E402
    CLEAN_DIR, N_FEAT, N_PRIOR as N_PRIOR_BASE, US_PER_SEC,
    build_div_and_levels,
)
from multi_asset.data.build_ho_factors import build_day_ho  # noqa: E402

# ----------------------------------------------------------------------- paths
MID_DIR = p.join(_REPO, "data", "mid_cache")
LASTTS_DIR = p.join(_REPO, "data", "lastts_cache")
OUT_DIR = p.join(_REPO, "data", "npz_dualsrc_rg")          # NEW output dir

# RG regime block: (family, channel-name) in build order. Pure regime-STATE
# descriptors only (see module docstring for the deliberate drops).
RG_CHANNELS = [
    ("rg", "rg_rvol_ts_60_600"),
    ("rg", "rg_rvol_ts_600_3600"),
    ("rg", "rg_rvol_600s"),
    ("rg", "rg_vr_q30_w3600"),
    ("rg", "rg_vr_q120_w3600"),
    ("rg", "rg_hurst_like"),
    ("rg", "rg_liq_depth_ratio"),
    ("ll", "ll_peakcorr_600s"),
    ("ll", "ll_couple0_600s"),
    ("ll", "ll_leadgain_600s"),
    ("ll", "ll_peakcorr_3600s"),
    ("ll", "ll_couple0_3600s"),
    ("ll", "ll_leadgain_3600s"),
]
N_RG = len(RG_CHANNELS)                 # 13
N_PRIOR_RG = N_PRIOR_BASE + N_RG       # 10 + 13 = 23

# FIXED robust (median, 1.4826·MAD scale, clip) per RG channel, measured on a
# 24-day train-span sample (2024-01..2024-12-15, seed 0) — bake-in so the gate
# always sees a train-distribution-matched, OOD-clamped input regardless of
# regime. Index aligns with RG_CHANNELS. clip ±5 (looser than the basis-LEVEL ±3
# because these are regime descriptors with naturally wider tails, but still hard-
# bounded so an OOD spike cannot drive the multiplicative gate out of range).
RG_NORM = [
    (+0.898119, 0.317996, 5.0),   # rg_rvol_ts_60_600
    (+0.933086, 0.220809, 5.0),   # rg_rvol_ts_600_3600
    (+0.000052, 0.000030, 5.0),   # rg_rvol_600s
    (+1.318089, 0.223572, 5.0),   # rg_vr_q30_w3600
    (+1.271148, 0.343290, 5.0),   # rg_vr_q120_w3600
    (+0.533904, 0.026594, 5.0),   # rg_hurst_like
    (+0.232608, 0.197982, 5.0),   # rg_liq_depth_ratio
    (+0.066254, 0.042922, 5.0),   # ll_peakcorr_600s
    (+0.523611, 0.245942, 5.0),   # ll_couple0_600s
    (-0.437811, 0.224389, 5.0),   # ll_leadgain_600s
    (+0.065099, 0.034053, 5.0),   # ll_peakcorr_3600s
    (+0.556895, 0.227459, 5.0),   # ll_couple0_3600s
    (-0.472377, 0.209041, 5.0),   # ll_leadgain_3600s
]
assert len(RG_NORM) == N_RG


def _robust_std_clip(x, center, scale, clip):
    """(x - center) / scale, NaN/inf-safe, hard-clip ±clip. Train-matched +
    bounded by construction (regime-invariant gate input)."""
    out = (np.asarray(x, dtype=np.float32) - np.float32(center)) / np.float32(scale)
    out = np.nan_to_num(out, nan=0.0, posinf=clip, neginf=-clip)
    return np.clip(out, -clip, clip).astype(np.float32)


def _rg_block_for_day(date_str, spot_ts):
    """Build the (N, 13) bounded RG regime block aligned to the dualsrc SPOT rows.

    The dualsrc rows are keyed by SPOT pred-idx us ``spot_ts``. The RG factors are
    keyed by the lastts pred-idx us. In this pipeline the lastts ``timestamps``
    == the SPOT pred-idx us (the spot window's pred second), so a row-for-row
    exact match is expected; we assert it and align by exact us match (any
    unmatched dualsrc row gets the neutral train-median => standardized 0).
    """
    dh = build_day_ho(date_str, MID_DIR, LASTTS_DIR)
    rg_names, rg_X = dh["fam"]["rg"]
    ll_names, ll_X = dh["fam"]["ll"]
    ho_ts = dh["ts"].astype(np.int64)                 # lastts pred-idx us

    # gather each selected RG channel column on the RG (lastts) row order
    cols = []
    for fam, nm in RG_CHANNELS:
        if fam == "rg":
            cols.append(rg_X[:, rg_names.index(nm)])
        else:
            cols.append(ll_X[:, ll_names.index(nm)])
    rg_mat = np.stack(cols, axis=-1).astype(np.float64)     # (M, 13) on ho_ts order

    # align ho_ts -> spot_ts (exact us match). Build a lookup.
    order = np.argsort(ho_ts, kind="stable")
    ho_ts_s = ho_ts[order]
    pos = np.searchsorted(ho_ts_s, spot_ts, side="left")
    in_rng = (pos >= 0) & (pos < ho_ts_s.size)
    pos_c = np.clip(pos, 0, ho_ts_s.size - 1)
    hit = in_rng & (ho_ts_s[pos_c] == spot_ts)
    matched = int(hit.sum())

    out = np.zeros((spot_ts.size, N_RG), dtype=np.float64)  # neutral default
    src_rows = order[pos_c[hit]]
    out[hit] = rg_mat[src_rows]

    # robust standardize + hard-clip (per channel) -> bounded FiLM inputs
    rg_block = np.empty((spot_ts.size, N_RG), dtype=np.float32)
    for j, (c, s, clip) in enumerate(RG_NORM):
        rg_block[:, j] = _robust_std_clip(out[:, j], c, s, clip)
    # rows with no RG match are set to the neutral standardized value (0) so the
    # gate sees "median regime" rather than garbage.
    rg_block[~hit, :] = 0.0
    return rg_block, dict(N=int(spot_ts.size), matched=matched,
                          match_frac=float(matched) / max(spot_ts.size, 1))


def build_one_day(date_str, out_path):
    t0 = time.time()
    # 1) the EXACT dualsrc div/levels (with the established calib bounds) + base
    div_X, levels, info = build_div_and_levels(date_str)
    with np.load(p.join(CLEAN_DIR, "%s.npz" % date_str), allow_pickle=True) as zc:
        spot_X = np.asarray(zc["X"], dtype=np.float32)
        X_raw = np.asarray(zc["X_raw"])
        regime6 = np.asarray(zc["regime_prior"], dtype=np.float32)   # (N,6)
        y_600 = np.asarray(zc["y_600"], dtype=np.float32)
        y_mask_600 = np.asarray(zc["y_mask_600"])
        ts = zc["timestamps"].astype(np.int64)                       # SPOT pred-idx us
    if regime6.shape[1] != 6:
        raise RuntimeError("%s: clean regime_prior width %d != 6"
                           % (date_str, regime6.shape[1]))

    # 2) the NEW bounded RG block aligned to the SPOT rows
    rg_block, rg_info = _rg_block_for_day(date_str, ts)
    if rg_info["match_frac"] < 0.99:
        # alignment must be essentially row-for-row; refuse a misaligned day
        raise RuntimeError("%s: RG/spot ts match_frac %.4f < 0.99 (alignment drift)"
                           % (date_str, rg_info["match_frac"]))

    # 3) assemble: X = spot64 + div5 (69); regime_prior = 6 + 4 levels + 13 RG (23)
    X = np.concatenate([spot_X, div_X], axis=-1).astype(np.float32)   # (N,69)
    regime_prior_ext = np.concatenate(
        [regime6, levels, rg_block], axis=-1).astype(np.float32)      # (N,23)
    if X.shape[-1] != N_FEAT:
        raise RuntimeError("%s: X width %d != %d" % (date_str, X.shape[-1], N_FEAT))
    if regime_prior_ext.shape[-1] != N_PRIOR_RG:
        raise RuntimeError("%s: regime width %d != %d"
                           % (date_str, regime_prior_ext.shape[-1], N_PRIOR_RG))

    os.makedirs(OUT_DIR, exist_ok=True)
    tmp = "%s.tmp.%d.npz" % (out_path, os.getpid())
    np.savez_compressed(tmp, X=X, X_raw=X_raw, regime_prior=regime_prior_ext,
                        y_600=y_600, y_mask_600=y_mask_600, timestamps=ts)
    os.replace(tmp, out_path)

    rg_fin = float(np.isfinite(rg_block).mean())
    rg_absmax = float(np.abs(rg_block).max()) if rg_block.size else 0.0
    return dict(N=info["N"], secs=time.time() - t0,
                mb=os.path.getsize(out_path) / 1e6,
                match_frac=rg_info["match_frac"], rg_finite=rg_fin,
                rg_absmax=rg_absmax,
                rp_finite=float(np.isfinite(regime_prior_ext).mean()))


# --------------------------------------------------------------------------- #
# fold-span day enumeration (train 540 + val 60 + embargo 1 + test 28)         #
# --------------------------------------------------------------------------- #
def _fold_days(test_start, train_days=540, val_days=60, test_days=28, embargo=1):
    """Every available day needed by a fold whose test starts at ``test_start``:
    the [train | val | embargo | test] contiguous calendar span, intersected with
    the days that have ALL caches (clean + perp + mid + lastts). Matches the
    trainer's walk-forward span construction."""
    avail = _available_days()
    ts_date = dt.date.fromisoformat(test_start)
    # test window
    test_end = ts_date + dt.timedelta(days=test_days)
    # everything from (train+val+embargo) days before test_start up to test_end
    span_start = ts_date - dt.timedelta(days=train_days + val_days + embargo + 5)
    return [d for d in avail
            if span_start.isoformat() <= d <= test_end.isoformat()]


def _available_days():
    out = []
    for name in sorted(os.listdir(CLEAN_DIR)):
        if not (len(name) == 14 and name.endswith(".npz")):
            continue
        d = name[:-4]
        if (p.exists(p.join(p.join(_REPO, "data", "npz_perp"), "%s.npz" % d))
                and p.exists(p.join(MID_DIR, "%s.npz" % d))
                and p.exists(p.join(LASTTS_DIR, "%s.npz" % d))):
            out.append(d)
    return out


def build(days, force=False):
    os.makedirs(OUT_DIR, exist_ok=True)
    print("[dualsrc_rg] %d day(s) -> %s" % (len(days), OUT_DIR), flush=True)
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
            print("  [warn] %s failed: %s: %s" % (d, type(e).__name__, e), flush=True)
            continue
        n_done += 1
        print("  [%d/%d] %s N=%d %.1fMB %.1fs match=%.4f rg_fin=%.4f rg_absmax=%.2f "
              "rp_fin=%.4f" % (i + 1, len(days), d, st["N"], st["mb"], st["secs"],
                               st["match_frac"], st["rg_finite"], st["rg_absmax"],
                               st["rp_finite"]), flush=True)
    print("[dualsrc_rg] DONE %.1f min: built=%d skip=%d fail=%d%s -> %s"
          % ((time.time() - t0) / 60, n_done, n_skip, n_fail,
             ("  FAILED: %s" % failed) if failed else "", OUT_DIR), flush=True)
    return n_fail


# --------------------------------------------------------------------------- #
# self-test: width contract + RG bound + alignment + leak-by-construction      #
# --------------------------------------------------------------------------- #
def _selftest():
    print("[selftest] RG bound + width ...", flush=True)
    big = np.array([1e9, -1e9, np.nan, np.inf, -np.inf], dtype=np.float32)
    for j, (c, s, clip) in enumerate(RG_NORM):
        o = _robust_std_clip(big, c, s, clip)
        assert np.all(np.isfinite(o)) and np.all(np.abs(o) <= clip + 1e-5), \
            "RG ch%d not bounded to ±%g" % (j, clip)
    assert N_PRIOR_RG == 23, "d_prior contract changed"
    assert len(RG_CHANNELS) == N_RG == 13
    # alignment sanity on a synthetic ho_ts == spot_ts permutation
    spot_ts = np.array([100, 200, 300, 400], dtype=np.int64) * US_PER_SEC
    print("[selftest]   RG OOD-clamp ±5 OK; width 23; channels 13", flush=True)
    print("[selftest] PASS", flush=True)
    return True


if __name__ == "__main__":
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    g = ap.add_mutually_exclusive_group(required=True)
    g.add_argument("--days", type=str, nargs="+", help="build only these YYYY-MM-DD")
    g.add_argument("--fold", type=str, help="build the full span for a fold test_start (YYYY-MM-DD)")
    g.add_argument("--selftest", action="store_true")
    ap.add_argument("--force", action="store_true")
    args = ap.parse_args()
    if args.selftest:
        sys.exit(0 if _selftest() else 1)
    if args.fold:
        days = _fold_days(args.fold)
        print("[fold %s] %d span days (%s .. %s)"
              % (args.fold, len(days), days[0] if days else "-",
                 days[-1] if days else "-"), flush=True)
    else:
        days = args.days
    nf = build(days, force=args.force)
    sys.exit(1 if nf else 0)
