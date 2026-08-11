"""Perp feature-families Ridge gate (LEAK-FREE perp y_600, CLEAN ::4).

Question this answers (NUMBERS only -- no GO/NO-GO):
  Prior single-asset feature work was lazy -- it gated only 4 basis channels on
  top of the SPOT-64 set, and never used the PERP order book at all. This script
  builds a RICH, mechanism-grounded feature set on TOP of SPOT-64 and measures
  which families add genuine signal over SPOT-64, leak-free, CLEAN caliber:

    (a) SPOT-64                          baseline (the production feature set)
    (b) SPOT-64 + PERP-64                same 64 features computed on the PERP book
    (c) SPOT-64 + CROSS-VENUE DIVERGENCE perp_feat - spot_feat for directional /
                                          flow channels (OBI, microprice, flow,
                                          vpin, kyle, depth, spread)
    (d) SPOT-64 + BASIS                  basis_bps, basis_z(30min), basis_mom(300s),
                                          basis_ema_dev(60s)  -- all strictly <= t
    (e) SPOT-64 + RELATIVE              perp/spot ratios (rvol, spread, volume) +
                                          a causal spot-vs-perp net-flow lead-lag z
    (f) SPOT-64 + ALL

For each family it reports pooled CLEAN Pearson, the per-family BLOCK delta-P vs
the SPOT-64 baseline, a quick add-one-in over the top individual cross-venue /
basis channels, and a y-permutation NULL band so a delta-P can be told apart from
sampling noise.

TARGET = the LEAK-FREE perp y_600 from ``npz_spot2perp_clean`` (re-anchored to the
spot prediction-second; corr 0.999 with raw perp y but causally clean). The clean
file's ``timestamps`` are byte-identical to the spot file's, so the join is exact.

LEAKAGE: SPOT-64 and PERP-64 are prebuilt last-<=t snapshots (nothing to shuffle).
PERP-64 and divergences are contemporaneous (<= t) -- fine. BASIS and the lead-lag
z are built strictly from mid_cache values at second floor(ts) -- i.e. the mid at
or before the prediction second -- so they are <= t by construction. We also run a
y-permutation null band on every family.

Caliber: last-timestep features, MAD-sigma norm fit on TRAIN only, walk-forward,
::4 CLEAN (stride 4 -> non-overlapping w.r.t. nothing here since these are already
prediction-time snapshots; ::4 matches the project's CLEAN convention and de-
correlates adjacent samples), 1-day embargo, lambda picked on VAL.

Run (server):
  /root/miniconda3/envs/hsy_v5push/bin/python -m multi_asset.eda.perp_feature_families_gate \
      --report --json_out /tmp/perp_feat_gate.json
"""
from __future__ import annotations

import argparse
import glob
import json
import os.path as p
import sys

import numpy as np
from scipy.stats import pearsonr, spearmanr

sys.path.insert(0, p.dirname(p.dirname(p.dirname(p.abspath(__file__)))))  # repo root
from multi_asset.eda.leakage_null import permute_y_null  # noqa: E402
from multi_asset.eda.perpY_ridge_gate import (  # noqa: E402
    EMBARGO_DAYS, LAMBDAS, MIN_TRAIN_DAYS, SUBSAMPLE, TEST_DAYS, VAL_DAYS,
    _fit_select, _metrics, _predict,
)

DATA_DIR = "/mnt/storage/private/work_hsy/quant_research_multi_asset/data"
# FEATURES come from the prebuilt lean last-timestep cache (spot_last/perp_last are
# bit-for-bit identical to npz_spot/npz_perp X[:, -1, :], cross-verified, and ~10x
# cheaper to read -- the heavy npz X decompresses 600 timesteps/file). The TARGET
# comes from npz_spot2perp_clean (the LEAK-FREE re-anchored perp y_600); the
# lastts_cache's own y_600 is the RAW perp y, NOT leak-free, so it is NOT used.
LASTTS_DIR = p.join(DATA_DIR, "lastts_cache")
CLEAN_DIR = p.join(DATA_DIR, "npz_spot2perp_clean")
MID_DIR = p.join(DATA_DIR, "mid_cache")

SHIFT_TOL_US = 10_000_000   # perp-spot constant label offset tolerance

# fold definitions, split into STRONG vs CHOPPY families for separate reporting.
STRONG_FOLDS = [
    dict(name="strong_2025_02", test_start="2025-02-01"),
    dict(name="strong_2025_04", test_start="2025-04-01"),
]
CHOPPY_FOLDS = [
    dict(name="choppy_2026", test_start="2026-03-01"),
]

# ---------------------------------------------------------------------------
# feature index map (0-based, EXACTLY matches build_factor_leg.EXPECTED_FEATURES)
# ---------------------------------------------------------------------------
FEAT = {  # name -> column index in the 64-feature snapshot
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

# Directional / flow features for the cross-venue divergence family. Mechanism:
# when perp pressure differs from spot pressure, perp is being pushed by perp-only
# forces (funding / leverage / liq) -> predicts a perp-specific move. Sign and
# magnitude of these are comparable across venues (OBI, microprice in bps, signed
# flow, vpin, kyle). Depth/spread divergence = relative liquidity stress.
DIVERGENCE_FEATS = [
    "obi_L1", "obi_L5", "obi_L10", "obi_L25",
    "microprice_dev_bps",
    "net_trade_flow_1s", "trade_imbalance_1s",
    "cumulative_net_flow_30s", "cumulative_net_flow_300s",
    "book_pressure_imbalance",
    "vpin_60s", "vpin_300s",
    "kyle_lambda_30s",
    "bid_depth_L5", "ask_depth_L5",
    "spread_bps",
]


# ---------------------------------------------------------------------------
# loading
# ---------------------------------------------------------------------------
def _names(d, digit=True):
    return {p.basename(f)[:-4] for f in glob.glob(p.join(d, "*.npz"))
            if (not digit) or p.basename(f)[0].isdigit()}


def _all_days():
    """ALL feature days (lastts_cache: 2023-01..2026-05). The clean leak-free
    target only exists 2024-06+, and mid_cache (for basis) likewise -- those are
    used WHERE AVAILABLE; pre-2024-06 days train on the raw perp target with
    basis=0 (see _load_day). Using the full feature history is essential: a Ridge
    on this low-SNR target needs ~700+ train days to leave the noise floor (a
    2024-06+-only train window starves it to P~=0; verified)."""
    return sorted(_names(LASTTS_DIR))


_CLEAN_SET = None
_MID_SET = None


def _has_clean(day):
    global _CLEAN_SET
    if _CLEAN_SET is None:
        _CLEAN_SET = _names(CLEAN_DIR)
    return day in _CLEAN_SET


def _has_mid(day):
    global _MID_SET
    if _MID_SET is None:
        _MID_SET = _names(MID_DIR)
    return day in _MID_SET


def _basis_features(ts_us: np.ndarray, zm) -> np.ndarray:
    """Causal basis features at floor(ts) seconds, strictly <= t.

    Returns (n, 4): [basis_bps, basis_z_30min, basis_mom_300s, basis_ema_dev_60s].

    All built from a full-day 1-Hz spot/perp mid grid: for each prediction second
    we use the mid AT or BEFORE that second (searchsorted 'right'-1), then roll
    *backwards* on the second grid -- no future second is ever touched.
    """
    sec = zm["sec"].astype(np.int64)
    spot_mid = zm["spot_mid"].astype(np.float64)
    perp_mid = zm["perp_mid"].astype(np.float64)

    # full-grid basis in bps (1 Hz); then causal stats on the grid
    grid_basis = (perp_mid - spot_mid) / spot_mid * 1e4          # (S,)
    S = grid_basis.shape[0]

    # causal 30-min (1800s) rolling mean/std on the 1Hz grid -> z
    win_z = 1800
    csum = np.concatenate([[0.0], np.cumsum(grid_basis)])
    csq = np.concatenate([[0.0], np.cumsum(grid_basis ** 2)])
    idx = np.arange(S)
    lo = np.maximum(0, idx - win_z + 1)
    cnt = (idx - lo + 1).astype(np.float64)
    s1 = csum[idx + 1] - csum[lo]
    s2 = csq[idx + 1] - csq[lo]
    mean_z = s1 / cnt
    var_z = np.maximum(s2 / cnt - mean_z ** 2, 0.0)
    std_z = np.sqrt(var_z)
    grid_z = np.zeros(S)
    good = std_z > 1e-9
    grid_z[good] = (grid_basis[good] - mean_z[good]) / std_z[good]

    # causal 300s momentum: basis_t - basis_{t-300}
    win_m = 300
    grid_mom = np.empty(S)
    grid_mom[:win_m] = 0.0
    grid_mom[win_m:] = grid_basis[win_m:] - grid_basis[:-win_m]

    # causal 60s EMA deviation: basis - EMA_60(basis)
    alpha = 2.0 / (60.0 + 1.0)
    ema = np.empty(S)
    ema[0] = grid_basis[0]
    for i in range(1, S):
        ema[i] = alpha * grid_basis[i] + (1 - alpha) * ema[i - 1]
    grid_ema_dev = grid_basis - ema

    # map each prediction ts -> last grid second <= ts
    ts_sec = ts_us // 1_000_000
    pos = np.searchsorted(sec, ts_sec, side="right") - 1
    pos = np.clip(pos, 0, S - 1)

    out = np.column_stack([
        grid_basis[pos], grid_z[pos], grid_mom[pos], grid_ema_dev[pos]
    ]).astype(np.float64)
    return out


BASIS_NAMES = ["basis_bps", "basis_z_30min", "basis_mom_300s", "basis_ema_dev_60s"]


def _relative_features(spot_last: np.ndarray, perp_last: np.ndarray,
                       basis_last: np.ndarray) -> np.ndarray:
    """perp/spot ratios + a causal spot-vs-perp net-flow lead-lag z.

    Returns (n, k). Ratios use log1p of a clipped ratio (heavy-tailed, sign-
    preserving for the volume/vol/spread which are all >= 0). The lead-lag z is
    the standardized GAP between spot and perp signed net flow at the SAME t
    (spot order flow is measured ~2x cleaner / leads perp); a large positive gap
    means spot is buying harder than perp -> perp tends to follow spot.
    """
    eps = 1e-12

    def ratio(a, b):
        r = (a + eps) / (b + eps)
        r = np.clip(r, 1e-3, 1e3)
        return np.log(r)

    cols, names = [], []
    # realized-vol ratios (perp/spot) at 30/60/300s
    for f in ["realized_vol_30s", "realized_vol_60s", "realized_vol_300s"]:
        cols.append(ratio(perp_last[:, FEAT[f]], spot_last[:, FEAT[f]]))
        names.append(f"ratio_{f}")
    # spread ratio
    cols.append(ratio(perp_last[:, FEAT["spread_bps"]],
                      spot_last[:, FEAT["spread_bps"]]))
    names.append("ratio_spread_bps")
    # volume ratio (buy+sell), per venue
    pvol = perp_last[:, FEAT["buy_volume_1s"]] + perp_last[:, FEAT["sell_volume_1s"]]
    svol = spot_last[:, FEAT["buy_volume_1s"]] + spot_last[:, FEAT["sell_volume_1s"]]
    cols.append(ratio(pvol, svol))
    names.append("ratio_volume_1s")

    # causal spot-vs-perp net-flow lead-lag GAP (z over the day, fit per-day from
    # this day's own samples is fine -- it is contemporaneous, not a future stat;
    # but to be strictly causal we standardize by a fixed robust scale = MADs of
    # the per-venue flow, computed below in the gate from TRAIN only would be ideal.
    # Here we emit the RAW gap and let the Ridge MAD-norm (train-only) standardize.)
    gap = (spot_last[:, FEAT["net_trade_flow_1s"]]
           - perp_last[:, FEAT["net_trade_flow_1s"]])
    cols.append(gap)
    names.append("spot_minus_perp_netflow")
    cum_gap = (spot_last[:, FEAT["cumulative_net_flow_30s"]]
               - perp_last[:, FEAT["cumulative_net_flow_30s"]])
    cols.append(cum_gap)
    names.append("spot_minus_perp_cumflow30")

    return np.column_stack(cols).astype(np.float64), names


def _load_day(day: str):
    """Return dict of per-day arrays (positionally joined, masked, ::SUBSAMPLE)
    or (None, reason).

    FEATURES from lastts_cache (spot_last/perp_last = bit-for-bit X[:, -1, :]).
    TARGET: the LEAK-FREE re-anchored perp y_600 from npz_spot2perp_clean WHERE IT
    EXISTS (2024-06+); on earlier days (no clean file) we fall back to the cache's
    RAW perp y_600 (corr ~1.000 with clean). ``is_clean`` flags which samples carry
    the leak-free target. The gate uses is_clean ONLY for TEST/VAL windows (the
    metrics that must be honest); TRAIN may use the fallback raw target on the long
    pre-2024-06 history (a train-target choice cannot leak future test labels).

    BASIS (4 causal channels from mid_cache) exists 2024-06+ only; on earlier days
    we emit basis=0 (the no-information value) so the column is defined across the
    full train window. This makes the BASIS / ALL families' basis coefficient
    slightly CONSERVATIVE (diluted by the zero-filled 2023..2024-05 history); the
    other families are unaffected."""
    lc = np.load(p.join(LASTTS_DIR, f"{day}.npz"))
    lts = lc["timestamps"].astype(np.int64)
    pts = lc["perp_ts"].astype(np.int64)
    diff = pts - lts
    if diff.size == 0:
        return None, "empty"
    if not np.all(diff == diff[0]):
        return None, "nonconst_shift"
    if abs(int(diff[0])) > SHIFT_TOL_US:
        return None, "shift_gt_tol"

    Xs = lc["spot_last"].astype(np.float64)         # spot last-ts (N,64)
    Xp = lc["perp_last"].astype(np.float64)         # perp last-ts (N,64)

    # target: clean where available, else raw perp; track which is leak-free
    if _has_clean(day):
        dc = np.load(p.join(CLEAN_DIR, f"{day}.npz"))
        if not np.array_equal(lc["timestamps"], dc["timestamps"].astype(np.int64)):
            return None, "clean_ts_mismatch"
        y = dc["y_600"].astype(np.float64)
        mask = dc["y_mask_600"].astype(bool)
        is_clean = True
    else:
        y = lc["y_600"].astype(np.float64)          # raw perp (train fallback)
        mask = lc["y_mask_600"].astype(bool)
        is_clean = False

    # basis (causal) where mid_cache exists, else zeros
    if _has_mid(day):
        zm = np.load(p.join(MID_DIR, f"{day}.npz"))
        basis = _basis_features(lts, zm)            # (N,4) causal basis
    else:
        basis = np.zeros((lts.shape[0], 4), dtype=np.float64)

    keep = mask.copy()
    keep[~np.isfinite(y)] = False
    keep &= np.all(np.isfinite(Xs), axis=1)
    keep &= np.all(np.isfinite(Xp), axis=1)
    keep &= np.all(np.isfinite(basis), axis=1)
    idx = np.where(keep)[0][::SUBSAMPLE]
    if idx.size == 0:
        return None, "no_valid_rows"

    return {
        "Xs": Xs[idx], "Xp": Xp[idx], "y": y[idx], "basis": basis[idx],
        "ts": lts[idx],
        "is_clean": np.full(idx.size, is_clean, dtype=bool),
    }, "ok"


def load_all(verbose=False):
    days = _all_days()
    acc = {"Xs": [], "Xp": [], "y": [], "basis": [], "di": [], "mo": [], "ic": []}
    kept_days, skipped = [], {}
    for k, day in enumerate(days):
        d, info = _load_day(day)
        if d is None:
            skipped[day] = info
            continue
        ki = len(kept_days)
        kept_days.append(day)
        n = d["y"].shape[0]
        acc["Xs"].append(d["Xs"]); acc["Xp"].append(d["Xp"])
        acc["y"].append(d["y"]); acc["basis"].append(d["basis"])
        acc["ic"].append(d["is_clean"])
        acc["di"].append(np.full(n, ki, dtype=np.int32))
        acc["mo"].append(np.array([day[:7]] * n))
    out = {
        "Xs": np.concatenate(acc["Xs"]), "Xp": np.concatenate(acc["Xp"]),
        "y": np.concatenate(acc["y"]), "basis": np.concatenate(acc["basis"]),
        "is_clean": np.concatenate(acc["ic"]),
        "day_idx": np.concatenate(acc["di"]), "month": np.concatenate(acc["mo"]),
        "days": kept_days, "skipped": skipped,
    }
    if verbose:
        from collections import Counter
        nclean = int(out["is_clean"].sum())
        print(f"[load] {len(days)} feature days, kept {len(kept_days)}, "
              f"skipped {len(skipped)}; M={out['Xs'].shape[0]} samples "
              f"({nclean} leak-free / {out['Xs'].shape[0]-nclean} raw-fallback)")
        if skipped:
            print("[load] skip reasons:", dict(Counter(skipped.values())))
    return out


# ---------------------------------------------------------------------------
# feature-family assembly (returns the design matrix for a named family)
# ---------------------------------------------------------------------------
def build_family(data, family: str):
    """Return (X, colnames) for a family. SPOT-64 is always the prefix for the
    additive families so block delta-P is a clean nested comparison."""
    Xs, Xp, basis = data["Xs"], data["Xp"], data["basis"]
    spot_names = [f"spot::{n}" for n, _ in sorted(FEAT.items(), key=lambda kv: kv[1])]

    if family == "spot64":
        return Xs, spot_names
    if family == "perp64":
        perp_names = [f"perp::{n}" for n, _ in sorted(FEAT.items(),
                                                      key=lambda kv: kv[1])]
        return np.concatenate([Xs, Xp], axis=1), spot_names + perp_names
    if family == "divergence":
        cols = [Xp[:, FEAT[f]] - Xs[:, FEAT[f]] for f in DIVERGENCE_FEATS]
        D = np.column_stack(cols)
        names = [f"div::{f}" for f in DIVERGENCE_FEATS]
        return np.concatenate([Xs, D], axis=1), spot_names + names
    if family == "basis":
        names = [f"basis::{n}" for n in BASIS_NAMES]
        return np.concatenate([Xs, basis], axis=1), spot_names + names
    if family == "relative":
        rel, rel_names = _relative_features(Xs, Xp, basis)
        return np.concatenate([Xs, rel], axis=1), spot_names + [f"rel::{n}" for n in rel_names]
    if family == "all":
        perp_div = np.column_stack([Xp[:, FEAT[f]] - Xs[:, FEAT[f]]
                                    for f in DIVERGENCE_FEATS])
        rel, rel_names = _relative_features(Xs, Xp, basis)
        X = np.concatenate([Xs, Xp, perp_div, basis, rel], axis=1)
        names = (spot_names
                 + [f"perp::{n}" for n, _ in sorted(FEAT.items(), key=lambda kv: kv[1])]
                 + [f"div::{f}" for f in DIVERGENCE_FEATS]
                 + [f"basis::{n}" for n in BASIS_NAMES]
                 + [f"rel::{n}" for n in rel_names])
        return X, names
    raise ValueError(family)


# ---------------------------------------------------------------------------
# walk-forward over a chosen fold set, pooled (re-implements the perpY harness'
# walk-forward but with a parametrizable fold list, so STRONG / CHOPPY can be
# reported separately and on an ARBITRARY design matrix X).
# ---------------------------------------------------------------------------
def _walk(X, y, day_idx, days, folds, is_clean, norm="madz"):
    """Walk-forward pooled over `folds`. TRAIN spans the full history [0, val); the
    leak-free constraint (is_clean) is applied ONLY to VAL and TEST -- those are the
    selection / scoring sets that must be honest. The test windows (2025-02, 2025-04,
    2026-03) are all 2024-06+ so they are fully leak-free regardless."""
    def first_ge(date):
        for i, d in enumerate(days):
            if d >= date:
                return i
        return len(days)

    pooled_yh, pooled_y, perfold_P, meta = [], [], [], []
    for fold in folds:
        ts0 = first_ge(fold["test_start"])
        te0, te1 = ts0, ts0 + TEST_DAYS
        va0, va1 = te0 - VAL_DAYS, te0
        tr0, tr1 = 0, va0 - EMBARGO_DAYS
        if te1 > len(days) or va0 < 0 or (tr1 - tr0) < MIN_TRAIN_DAYS:
            meta.append(dict(name=fold["name"], status="unavailable"))
            continue
        tr_m = np.isin(day_idx, list(range(tr0, tr1)))
        va_m = np.isin(day_idx, list(range(va0, va1))) & is_clean
        te_m = np.isin(day_idx, list(range(te0, te1))) & is_clean
        if tr_m.sum() < 500 or va_m.sum() < 20 or te_m.sum() < 20:
            meta.append(dict(name=fold["name"], status="too_few_samples"))
            continue
        sel = _fit_select(X[tr_m], y[tr_m], X[va_m], y[va_m], norm)
        if sel is None:
            meta.append(dict(name=fold["name"], status="bad_sigma"))
            continue
        w, b, center, scale, sig, lam, valP = sel
        yhat = _predict(X[te_m], w, b, center, scale, sig)
        yte = y[te_m]
        m = _metrics(yhat, yte)
        perfold_P.append(m["P"])
        pooled_yh.append(yhat); pooled_y.append(yte)
        meta.append(dict(name=fold["name"], status="ok",
                         test_span=f"{days[te0]}..{days[te1-1]}",
                         best_lam=lam, val_P=round(valP, 4),
                         P=round(m["P"], 4), S=round(m["S"], 4),
                         beta=round(m["beta"], 3),
                         sig_ratio=round(m["sig_ratio"], 4),
                         bias_bps=round(m["bias_bps"], 3), n_test=int(te_m.sum())))
    if not pooled_yh:
        return dict(pooled=None, folds=meta)
    yh = np.concatenate(pooled_yh); yy = np.concatenate(pooled_y)
    pm = _metrics(yh, yy)
    finite = [x for x in perfold_P if np.isfinite(x)]
    signs = set(np.sign(x) for x in finite if x != 0)
    sign_consistent = (len(signs) <= 1) and not any(x <= -0.01 for x in finite)
    return dict(folds=meta, pooled=dict(
        P=round(pm["P"], 4), S=round(pm["S"], 4), beta=round(pm["beta"], 3),
        sig_ratio=round(pm["sig_ratio"], 4), bias_bps=round(pm["bias_bps"], 3),
        n=pm["n"], perfold_P=[round(x, 4) for x in perfold_P],
        sign_consistent=bool(sign_consistent),
        pooled_yhat=yh, pooled_y=yy))


# ---------------------------------------------------------------------------
# orchestration
# ---------------------------------------------------------------------------
FAMILIES = ["spot64", "perp64", "divergence", "basis", "relative", "all"]
FAMILY_LABEL = {
    "spot64": "(a) SPOT-64 baseline",
    "perp64": "(b) + PERP-64",
    "divergence": "(c) + CROSS-VENUE DIVERGENCE",
    "basis": "(d) + BASIS",
    "relative": "(e) + RELATIVE",
    "all": "(f) + ALL",
}


def run_regime(data, folds, null_n, label):
    """Run all families on one regime (fold set); return a result dict."""
    res = {"label": label, "families": {}}
    base_P = None
    base_pred = None
    for fam in FAMILIES:
        X, names = build_family(data, fam)
        wf = _walk(X, data["y"], data["day_idx"], data["days"], folds,
                   data["is_clean"])
        pooled = wf["pooled"]
        if pooled is None:
            res["families"][fam] = dict(status="unavailable", folds=wf["folds"])
            continue
        entry = dict(
            P=pooled["P"], S=pooled["S"], beta=pooled["beta"],
            sig_ratio=pooled["sig_ratio"], bias_bps=pooled["bias_bps"],
            n=pooled["n"], n_feat=X.shape[1], perfold_P=pooled["perfold_P"],
            sign_consistent=pooled["sign_consistent"],
        )
        if fam == "spot64":
            base_P = pooled["P"]
            base_pred = pooled["pooled_yhat"]
            entry["null_band_975"] = round(
                permute_y_null(pooled["pooled_yhat"], pooled["pooled_y"],
                               n=null_n, seed=0), 4)
        else:
            entry["block_dP"] = round(pooled["P"] - base_P, 4)
        res["families"][fam] = entry
    res["base_P"] = base_P
    # store baseline null band at the regime level too
    res["null_band_975"] = res["families"]["spot64"].get("null_band_975")
    res["_base_pred_n"] = None if base_pred is None else int(base_pred.size)
    return res


def add_one_in(data, folds, null_n):
    """Add each top individual cross-venue / basis / relative channel to SPOT-64
    one at a time and report delta-P. This isolates which single channels carry
    the signal vs. the block (where collinearity can mask an individual gainer)."""
    Xs = data["Xs"]
    spot_names = [f"spot::{n}" for n, _ in sorted(FEAT.items(), key=lambda kv: kv[1])]
    base = _walk(Xs, data["y"], data["day_idx"], data["days"], folds,
                 data["is_clean"])
    if base["pooled"] is None:
        return {"status": "baseline_unavailable"}
    base_P = base["pooled"]["P"]
    nb = round(permute_y_null(base["pooled"]["pooled_yhat"],
                              base["pooled"]["pooled_y"], n=null_n, seed=0), 4)

    Xp, basis = data["Xp"], data["basis"]
    rel, rel_names = _relative_features(Xs, Xp, basis)

    candidates = []  # (label, column-vector)
    for f in DIVERGENCE_FEATS:
        candidates.append((f"div::{f}", Xp[:, FEAT[f]] - Xs[:, FEAT[f]]))
    for j, n in enumerate(BASIS_NAMES):
        candidates.append((f"basis::{n}", basis[:, j]))
    for j, n in enumerate(rel_names):
        candidates.append((f"rel::{n}", rel[:, j]))
    # a few raw perp-only channels worth isolating (the most directional ones)
    for f in ["obi_L5", "microprice_dev_bps", "net_trade_flow_1s",
              "cumulative_net_flow_300s", "book_pressure_imbalance", "vpin_300s"]:
        candidates.append((f"perp::{f}", Xp[:, FEAT[f]]))

    rows = []
    for lab, col in candidates:
        X = np.column_stack([Xs, col])
        wf = _walk(X, data["y"], data["day_idx"], data["days"], folds,
                   data["is_clean"])
        if wf["pooled"] is None:
            continue
        dP = wf["pooled"]["P"] - base_P
        rows.append(dict(feat=lab, P=wf["pooled"]["P"], dP=round(dP, 4),
                         beta=wf["pooled"]["beta"],
                         sig_ratio=wf["pooled"]["sig_ratio"]))
    rows.sort(key=lambda r: r["dP"], reverse=True)
    return {"base_P": base_P, "null_band_975": nb, "rows": rows}


# ---------------------------------------------------------------------------
# reporting
# ---------------------------------------------------------------------------
def _fmt_family_table(res):
    lines = []
    nb = res.get("null_band_975")
    lines.append(f"\n### {res['label']}   (baseline null band 97.5% |IC| = {nb})")
    lines.append(f"{'family':30s} {'nfeat':>5s} {'P':>8s} {'S':>8s} "
                 f"{'beta':>7s} {'sigR':>7s} {'block dP':>9s} {'>null?':>7s} "
                 f"{'perfold_P':>22s}")
    for fam in FAMILIES:
        e = res["families"].get(fam, {})
        if e.get("status") == "unavailable":
            lines.append(f"{FAMILY_LABEL[fam]:30s}  (unavailable)")
            continue
        dP = e.get("block_dP")
        dP_s = "(base)" if fam == "spot64" else f"{dP:+.4f}"
        gt = "" if fam == "spot64" else (
            "YES" if (nb is not None and abs(dP) > nb) else "no")
        pf = str(e.get("perfold_P"))
        lines.append(f"{FAMILY_LABEL[fam]:30s} {e['n_feat']:5d} {e['P']:+8.4f} "
                     f"{e['S']:+8.4f} {e['beta']:+7.3f} {e['sig_ratio']:7.4f} "
                     f"{dP_s:>9s} {gt:>7s} {pf:>22s}")
    return "\n".join(lines)


def _fmt_add_one(res, label):
    if res.get("status"):
        return f"\n### add-one-in ({label}): {res['status']}"
    lines = [f"\n### add-one-in ({label})   base_P={res['base_P']:+.4f}  "
             f"null band 97.5% = {res['null_band_975']}"]
    lines.append(f"{'feature':34s} {'P':>8s} {'dP':>9s} {'beta':>7s} "
                 f"{'sigR':>7s} {'>null?':>7s}")
    nb = res["null_band_975"]
    for r in res["rows"]:
        gt = "YES" if abs(r["dP"]) > nb else "no"
        lines.append(f"{r['feat']:34s} {r['P']:+8.4f} {r['dP']:+9.4f} "
                     f"{r['beta']:+7.3f} {r['sig_ratio']:7.4f} {gt:>7s}")
    return "\n".join(lines)


def _strip(obj):
    if isinstance(obj, dict):
        return {k: _strip(v) for k, v in obj.items()
                if not isinstance(v, np.ndarray)}
    if isinstance(obj, list):
        return [_strip(v) for v in obj]
    if isinstance(obj, (np.floating,)):
        return float(obj)
    if isinstance(obj, (np.integer,)):
        return int(obj)
    return obj


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--null_n", type=int, default=1000)
    ap.add_argument("--n_addone", type=int, default=8,
                    help="how many top add-one-in rows to print (full set in json)")
    ap.add_argument("--report", action="store_true")
    ap.add_argument("--json_out", default="")
    ap.add_argument("--md_out", default="")
    args = ap.parse_args()

    data = load_all(verbose=True)

    out = {"n_samples": int(data["Xs"].shape[0]),
           "n_days": len(data["days"]),
           "n_skipped": len(data["skipped"]),
           "subsample": SUBSAMPLE, "caliber": "CLEAN ::4, leak-free perp y_600",
           "lambdas": LAMBDAS}

    strong = run_regime(data, STRONG_FOLDS, args.null_n, "STRONG (2025-02 + 2025-04)")
    choppy = run_regime(data, CHOPPY_FOLDS, args.null_n, "CHOPPY (2026-03)")
    ao_strong = add_one_in(data, STRONG_FOLDS, args.null_n)
    ao_choppy = add_one_in(data, CHOPPY_FOLDS, args.null_n)

    out["strong"] = _strip(strong)
    out["choppy"] = _strip(choppy)
    out["add_one_in_strong"] = _strip(ao_strong)
    out["add_one_in_choppy"] = _strip(ao_choppy)

    md = []
    md.append("# Perp feature-families Ridge gate (LEAK-FREE perp y_600, CLEAN ::4)")
    md.append(f"\nsamples={out['n_samples']}  days={out['n_days']}  "
              f"skipped={out['n_skipped']}  null_n={args.null_n}  "
              f"caliber={out['caliber']}")
    md.append(_fmt_family_table(strong))
    md.append(_fmt_family_table(choppy))
    # add-one-in: print top n_addone in console; full set goes to json/md
    def trim(res, k):
        if res.get("status"):
            return res
        r2 = dict(res); r2["rows"] = res["rows"][:k]
        return r2
    md.append(_fmt_add_one(trim(ao_strong, args.n_addone), "STRONG"))
    md.append(_fmt_add_one(trim(ao_choppy, args.n_addone), "CHOPPY"))
    md_text = "\n".join(md)
    print(md_text)

    if args.md_out:
        full = list(md[:-2])
        full.append(_fmt_add_one(ao_strong, "STRONG (full)"))
        full.append(_fmt_add_one(ao_choppy, "CHOPPY (full)"))
        with open(args.md_out, "w") as f:
            f.write("\n".join(full) + "\n")
        print(f"\nWrote {args.md_out}")
    if args.json_out:
        with open(args.json_out, "w") as f:
            json.dump(out, f, indent=2, default=float)
        print(f"Wrote {args.json_out}")


if __name__ == "__main__":
    main()
