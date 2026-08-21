"""STAGE C1 — cross-venue / basis interaction factors from the EXISTING npz
caches (no Tardis re-read).

Mechanism under test
--------------------
A model using ONLY spot last-timestep features gets ~half the Pearson on the
**perp** ``y_600`` target that the same features get on the *spot* target
(0.013 vs ~0.026 on choppy 2026). Hypothesis: the perp target carries a
basis/funding component orthogonal to spot book features, so spot-only IC is
lost. These 6 factors are perp-vs-spot DIVERGENCES designed to recover that lost
IC cheaply, evaluated by Ridge walk-forward (``perpY_basis_gate.py``).

Inputs (READ-ONLY, both 1247 days, IDENTICAL per-day length, constant per-day
ts offset ≤±4s — causal-safe, see GATE A loader docstring):
  data/npz_spot/<day>.npz : X (N,600,64) spot features, timestamps
  data/npz_perp/<day>.npz : X (N,600,64) SAME 64 features on the PERP book,
                            y_600 (perp target), y_mask_600, timestamps

We use ONLY the last timestep ``X[:, -1, :]`` of each window (matches the GATE A
Ridge which is a last-timestep model) and join perp↔spot BY POSITION per day
(the constant whole-second offset is a label-snapshot convention, not a row
misalignment — asserted equal length + constant shift by the caller).

The 6 factors (column indices verified against the embedded ``features`` array,
== build_factor_leg.EXPECTED_FEATURES):

  idx  6  obi_L5
  idx 15  weighted_price_bid_L10   = (w_bid - mid)/mid * 1e4   (bps, mid-relative)
  idx 16  weighted_price_ask_L10   = (w_ask - mid)/mid * 1e4
  idx 19  realized_vol_60s
  idx 45  net_trade_flow_1s
  idx 47  cumulative_net_flow_30s
  idx 52  microprice_dev_bps       = (micro - mid)/mid * 1e4   (bps)

  1. perp_spot_obi_diff_L5   = perp.obi_L5 − spot.obi_L5
        cross-venue book-imbalance divergence (perp leads in derivatives flow).
  2. perp_spot_microdev_diff = perp.microprice_dev_bps − spot.microprice_dev_bps
        which venue's microprice is pulling harder off mid (lead-side pressure).
  3. spot_flow_lead_perp     = z(spot.cumulative_net_flow_30s) − z(perp.same)
        per-day standardized; positive ⇒ spot buying relatively harder than perp
        (the classic spot-leads-perp footprint). z = (x−median)/MAD over the day
        (robust; symmetric transform on both venues — see CAUSALITY note below).
  4. perp_spot_vol_ratio     = perp.realized_vol_60s / (spot.realized_vol_60s+eps)
        relative volatility regime; perp vol spikes (liquidations) lead moves.
  5. basis_proxy_bps         = perp.weighted_price_bid_L10 − spot.weighted_price_bid_L10
        **NOTE / honest caveat:** weighted_price_bid_L10 is a *mid-relative bps
        deviation* (each venue measured vs its OWN mid), NOT an absolute price.
        The two mids therefore CANCEL, so this is the cross-venue *bid-side book-
        skew* difference, NOT a true perp−spot mid basis. The 64-feat schema has
        NO absolute price/mid feature (all prices are mid-relative for
        stationarity), so a genuine funding/basis (perp_mid − spot_mid) is NOT
        reconstructable here (consistent with "no funding/OI on disk"). This is
        the closest available proxy and is a real cross-venue pressure signal.
  6. basis_proxy_dev         = basis_proxy_bps − causal_EMA(basis_proxy_bps)
        de-meaned mean-reversion of the proxy. EMA is built on a shift(1) copy
        (strictly ≤ t-1) so basis_proxy_dev[t] uses NO information from t.

CAUSALITY notes
---------------
* Factors 1,2,4,5 are pure same-timestep cross-venue arithmetic on ≤t inputs —
  causal by construction.
* Factor 3's per-day robust-z uses the whole day's median/MAD (a mild within-day
  look-ahead of the *scale*, identical on both venues). This is the EDA
  normalization the task specifies; it cannot manufacture directional signal that
  the permute-y null + venue-cross-shift sentinel would not catch, and a strictly
  causal expanding-z variant is provided (``causal_z=True``) for the sentinel.
* Factor 6's EMA is strictly causal (shift(1) before ewm), so the de-meaned value
  at t depends only on t and the past.

This module is import-only for the gate; ``--selftest`` runs a quick real-day
sanity print. ``permute_y_null`` / venue-cross-shift sentinel live in the gate.
"""
from __future__ import annotations

import argparse
import os.path as p

import numpy as np

# -------- column indices (verified on server vs embedded `features` array) ----
IDX_OBI_L5 = 6
IDX_WPB_L10 = 15            # weighted_price_bid_L10  (mid-relative bps)
IDX_WPA_L10 = 16           # weighted_price_ask_L10
IDX_RV_60S = 19            # realized_vol_60s
IDX_NET_TRADE_FLOW_1S = 45
IDX_CUM_NET_FLOW_30S = 47
IDX_MICRO_DEV_BPS = 52

FACTOR_NAMES = [
    "perp_spot_obi_diff_L5",
    "perp_spot_microdev_diff",
    "spot_flow_lead_perp",
    "perp_spot_vol_ratio",
    "basis_proxy_bps",
    "basis_proxy_dev",
]
N_FACTORS = len(FACTOR_NAMES)

_EPS = 1e-8
EMA_ALPHA = 0.02           # ≈ 50-bar (window-grid) half-life on basis proxy


# ---------------------------------------------------------------------------
# robust per-day z (factor 3)
# ---------------------------------------------------------------------------
def _robust_z_full(x: np.ndarray) -> np.ndarray:
    """(x − median) / (1.4826·MAD) using the WHOLE-day stats (EDA convention).
    Constant transform applied identically to both venues."""
    x = np.asarray(x, dtype=np.float64)
    med = np.nanmedian(x)
    mad = np.nanmedian(np.abs(x - med)) * 1.4826
    scale = mad if (np.isfinite(mad) and mad > _EPS) else 1.0
    return (x - med) / scale


def _robust_z_causal(x: np.ndarray) -> np.ndarray:
    """Strictly causal expanding robust-z: at row t, center/scale use only rows
    [0..t-1] (shift(1)); row 0 -> 0. Used for the causal sentinel variant."""
    x = np.asarray(x, dtype=np.float64)
    n = x.shape[0]
    out = np.zeros(n, dtype=np.float64)
    if n <= 1:
        return out
    # expanding median/MAD over the strictly-past prefix is O(n^2) but n≈480/day
    for t in range(1, n):
        past = x[:t]
        past = past[np.isfinite(past)]
        if past.size < 2:
            continue
        med = np.median(past)
        mad = np.median(np.abs(past - med)) * 1.4826
        scale = mad if (np.isfinite(mad) and mad > _EPS) else 1.0
        out[t] = (x[t] - med) / scale
    return out


def _causal_ema(x: np.ndarray, alpha: float = EMA_ALPHA) -> np.ndarray:
    """EMA of ``x`` over a SHIFT(1) copy so the value at t depends only on
    x[0..t-1] (strictly ≤ t-1). out[0] = 0 (no past). Linear recursion."""
    x = np.asarray(x, dtype=np.float64)
    n = x.shape[0]
    out = np.zeros(n, dtype=np.float64)
    if n <= 1:
        return out
    xs = np.empty(n, dtype=np.float64)        # shift(1): xs[t] = x[t-1]
    xs[0] = np.nan
    xs[1:] = x[:-1]
    s = 0.0
    have = False
    for t in range(1, n):
        v = xs[t]
        if not np.isfinite(v):
            out[t] = s if have else 0.0
            continue
        if not have:
            s = v
            have = True
        else:
            s = alpha * v + (1.0 - alpha) * s
        out[t] = s
    return out


# ---------------------------------------------------------------------------
# the 6 factors
# ---------------------------------------------------------------------------
def compute_interaction_factors(spot_last: np.ndarray, perp_last: np.ndarray,
                                causal_z: bool = False) -> np.ndarray:
    """Compute the 6 cross-venue factors at each window's last timestep.

    Parameters
    ----------
    spot_last : (N, 64)  spot features at the window's last timestep (X[:, -1, :])
    perp_last : (N, 64)  perp features at the SAME positions (joined by position)
    causal_z  : if True, factor 3 uses the strictly-causal expanding robust-z
                (for the leakage sentinel); else the whole-day robust-z (EDA).

    Returns
    -------
    F : (N, 6) float64, columns in FACTOR_NAMES order. Non-finite entries are
        left as produced (the gate masks them); see _finite_factors for a
        sanitised variant used by the Ridge.
    """
    spot_last = np.asarray(spot_last, dtype=np.float64)
    perp_last = np.asarray(perp_last, dtype=np.float64)
    if spot_last.shape != perp_last.shape:
        raise ValueError(f"shape mismatch spot{spot_last.shape} perp{perp_last.shape}")
    if spot_last.ndim != 2 or spot_last.shape[1] < 64:
        raise ValueError(f"expected (N,>=64), got {spot_last.shape}")
    n = spot_last.shape[0]
    F = np.empty((n, N_FACTORS), dtype=np.float64)

    # 1. perp − spot OBI(L5)
    F[:, 0] = perp_last[:, IDX_OBI_L5] - spot_last[:, IDX_OBI_L5]

    # 2. perp − spot microprice deviation (bps)
    F[:, 1] = perp_last[:, IDX_MICRO_DEV_BPS] - spot_last[:, IDX_MICRO_DEV_BPS]

    # 3. z(spot cumulative_net_flow_30s) − z(perp same)  [per-day robust-z]
    zfun = _robust_z_causal if causal_z else _robust_z_full
    zs = zfun(spot_last[:, IDX_CUM_NET_FLOW_30S])
    zp = zfun(perp_last[:, IDX_CUM_NET_FLOW_30S])
    F[:, 2] = zs - zp

    # 4. perp / spot realized_vol_60s ratio (clamped log-ish via plain ratio+eps)
    F[:, 3] = perp_last[:, IDX_RV_60S] / (spot_last[:, IDX_RV_60S] + _EPS)

    # 5. basis proxy (mid-relative bid-skew diff; see module caveat)
    basis = perp_last[:, IDX_WPB_L10] - spot_last[:, IDX_WPB_L10]
    F[:, 4] = basis

    # 6. basis proxy − causal EMA(basis)  [strictly ≤ t-1 EMA]
    F[:, 5] = basis - _causal_ema(basis, EMA_ALPHA)

    return F


def finite_factors(F: np.ndarray) -> np.ndarray:
    """Replace non-finite factor entries with 0.0 and clip the vol-ratio outlier
    tail (perp/spot RV can blow up when spot RV≈0). Returns a copy safe for the
    Ridge (the Ridge standardizes columns anyway)."""
    F = np.array(F, dtype=np.float64, copy=True)
    # clip vol ratio to a sane band before sanitising (heavy right tail)
    vr = F[:, 3]
    vr = np.where(np.isfinite(vr), vr, 1.0)
    F[:, 3] = np.clip(vr, 0.0, 50.0)
    F[~np.isfinite(F)] = 0.0
    return F


# ---------------------------------------------------------------------------
# selftest (real day)
# ---------------------------------------------------------------------------
def _selftest(data_dir: str):
    spot = p.join(data_dir, "npz_spot", "2025-04-15.npz")
    perp = p.join(data_dir, "npz_perp", "2025-04-15.npz")
    s = np.load(spot, allow_pickle=True)
    q = np.load(perp, allow_pickle=True)
    sl = s["X"][:, -1, :].astype(np.float64)
    pl = q["X"][:, -1, :].astype(np.float64)
    F = compute_interaction_factors(sl, pl)
    Ff = finite_factors(F)
    print(f"[selftest] N={sl.shape[0]} factors shape {F.shape}")
    for j, nm in enumerate(FACTOR_NAMES):
        col = Ff[:, j]
        print(f"  {nm:24s} finite={np.isfinite(F[:,j]).mean():.3f} "
              f"min/med/max={np.nanmin(col):+.4f}/{np.nanmedian(col):+.4f}/"
              f"{np.nanmax(col):+.4f} std={np.nanstd(col):.4f}")
    # direct identity spot-check
    assert np.allclose(F[:, 0], pl[:, IDX_OBI_L5] - sl[:, IDX_OBI_L5])
    print("[selftest] identity check OK")


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--selftest", action="store_true")
    ap.add_argument("--data-dir",
                    default="/mnt/storage/private/work_hsy/quant_research_multi_asset/data")
    a = ap.parse_args()
    if a.selftest:
        _selftest(a.data_dir)
    else:
        ap.print_help()
