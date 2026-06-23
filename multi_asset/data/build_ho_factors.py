"""HIGHER-ORDER / DYNAMIC dual-source factors for BTC perp y_600.

> created 2026-06-20 | status: research-gate | branch: dual-source-perp

WHY THIS EXISTS (build BEYOND the shallow + rich sets)
------------------------------------------------------
The shallow cross-venue set (perp/spot ratio + lead-lag +0.0095, divergence
+0.0073) and the rich set (build_rich_xfeats.py: funding clock, multi-scale
basis level/z/mom/emadev, static book divergences, liq proxy) are LEVEL /
single-window constructs. The rich gate showed they predict the basis-change r
(an identity, r==basis change over the horizon, r_var ~0.3% of perp var) but on
the TRADABLE perp_y the union is +0.04 STRONG yet -0.012 CHOPPY (hurts).

This module builds genuinely HIGHER-ORDER, *dynamic* factors -- the rate, shape,
persistence and regime of the microstructure, multi-scale {60,600,3600}s, each
with an explicit mechanism. NOT +-*/ of levels. All strictly <= t (verified by
the gate's +600s shift sentinel + permutation null).

It reuses the per-second mid grid (mid_cache) and the dual-venue 64-feat last-<=t
snapshots (lastts_cache), and the causal helpers from build_rich_xfeats.

FAMILIES
  BD  basis dynamics      : OU half-life / reversion speed, vol TERM-STRUCTURE
                            ratios, momentum+acceleration ratio, curvature,
                            percentile-regime spread across windows.
  LL  time-varying leadlag: rolling spot<->perp cross-corr peak-lag + strength,
                            multi-scale; lead-lag REGIME (does lead strength itself
                            predict perp catch-up?).
  OF  order-flow higher-ord: OFI/divergence persistence (autocorr), flow momentum,
                            self-excitation / clustering (Hawkes-style intensity),
                            signed-flow acceleration, multi-horizon flow.
  BS  book-shape evolution: depth-concentration CHANGE over time, microprice
                            curvature dynamics, slope dynamics, cross-venue
                            book-shape divergence rate.
  XS  cross-scale interact : basis-dislocation x vol-regime, divergence x trend,
                            designed regime-conditional products.
  RG  regime indicators    : realized-vol term-structure, variance-ratio
                            (trend-vs-chop, causal), Hurst-like, liquidity regime,
                            lead-lag regime -- multi-scale (for FiLM/regime_prior).
"""
from __future__ import annotations
import os.path as p
import sys
import numpy as np

_REPO = "/mnt/storage/private/work_hsy/quant_research_multi_asset"
if _REPO not in sys.path:
    sys.path.insert(0, _REPO)

from multi_asset.data.build_rich_xfeats import (
    per_second_source, _causal_roll_mean_std, _causal_roll_sum, _causal_ema_shift1,
    _lag_on_grid, _sample_grid, _pctrank_at, FEAT, EPS, US, CLIP_BPS,
)

# multi-scale horizons mandated by the brief
SCALES = {"60s": 60, "600s": 600, "3600s": 3600}


# --------------------------------------------------------------------------- #
# extra causal grid helpers (higher-order: autocorr, cross-corr, variance-ratio)
# --------------------------------------------------------------------------- #
def _causal_roll_autocorr1(x, win):
    """Lag-1 autocorrelation of x over a trailing `win` window, SHIFT(1).
    corr(x[i-win..i-2], x[i-win+1..i-1]). O(T) via shifted prefix sums on the
    paired product. Mechanism use: persistence/clustering of a flow series."""
    x = np.asarray(x, np.float64)
    T = x.size
    x1 = np.empty(T); x1[0] = 0.0; x1[1:] = x[:-1]          # x lagged by 1
    # rolling means/vars (shift1) of x and x1 and their product over win
    mx, sx = _causal_roll_mean_std(x, win)
    mx1, sx1 = _causal_roll_mean_std(x1, win)
    prod = x * x1
    sp = _causal_roll_sum(prod, win)
    i = np.arange(T); lo = np.maximum(0, i - win); cnt = (i - lo).astype(np.float64)
    with np.errstate(invalid="ignore", divide="ignore"):
        cov = sp / np.where(cnt > 0, cnt, 1.0) - mx * mx1
        ac = cov / ((sx * sx1) + EPS)
    ac[cnt < 5] = np.nan
    return np.clip(ac, -1.0, 1.0)


def _causal_crosscorr_at_lag(a, b, win, lag):
    """Trailing windowed correlation between a[i] and b[i-lag] (b lags a by `lag`),
    SHIFT(1). >0 at lag>0 means a LEADS b by `lag` seconds. O(T) prefix sums."""
    a = np.asarray(a, np.float64); b = np.asarray(b, np.float64)
    T = a.size
    bl = np.empty(T); bl[:lag] = 0.0; bl[lag:] = b[:-lag] if lag > 0 else b
    ma, sa = _causal_roll_mean_std(a, win)
    mb, sb = _causal_roll_mean_std(bl, win)
    sp = _causal_roll_sum(a * bl, win)
    i = np.arange(T); lo = np.maximum(0, i - win); cnt = (i - lo).astype(np.float64)
    with np.errstate(invalid="ignore", divide="ignore"):
        cov = sp / np.where(cnt > 0, cnt, 1.0) - ma * mb
        cc = cov / ((sa * sb) + EPS)
    cc[cnt < 10] = np.nan
    return np.clip(cc, -1.0, 1.0)


def _variance_ratio(ret_1s, win, q):
    """Lo-MacKinlay variance ratio VR(q) = Var(q-period ret)/(q*Var(1-period ret)),
    causal over trailing `win`, SHIFT(1). VR>1 -> trending (positive autocorr),
    VR<1 -> mean-reverting/choppy. Built from rolling vars of 1s and q-summed
    returns. Mechanism: causal trend-vs-chop regime indicator."""
    r1 = np.asarray(ret_1s, np.float64)
    rq = _causal_roll_sum(r1, q)               # rolling q-second cumulative return
    _, s1 = _causal_roll_mean_std(r1, win)
    _, sq = _causal_roll_mean_std(rq, win)
    with np.errstate(invalid="ignore", divide="ignore"):
        vr = (sq * sq) / (q * (s1 * s1) + EPS)
    return vr


# =========================================================================== #
# FAMILY BD -- BASIS DYNAMICS (higher-order)
# =========================================================================== #
# MECHANISM: the basis mean-reverts to a carry anchor. The shallow/rich sets used
# the LEVEL/z of the basis. The *dynamics* -- how FAST it reverts (OU half-life),
# whether its vol is rising across scales (term structure), and its curvature --
# carry information about the *rate* of the imminent perp move beyond the level.
def family_basis_dynamics(src, pred_sec=None):
    sec = src["sec"]; basis = src["basis_bps"]
    cols = {}
    dbasis = np.zeros_like(basis); dbasis[1:] = np.diff(basis)
    # --- OU mean-reversion speed via AR(1) on the basis, per scale ---
    # d basis_t = -kappa*(basis - mu)*dt + noise  ->  basis_t ~ phi*basis_{t-1}.
    # Estimate phi causally as rolling lag-1 autocorr of the *level*; kappa=-ln(phi),
    # half-life = ln2/kappa. Mechanism: fast-reverting basis snaps back inside the
    # 600s horizon (predicts the perp catch-up direction strength).
    for tag, win in SCALES.items():
        phi = _causal_roll_autocorr1(basis, win)             # AR(1) coef of level
        phi_c = np.clip(phi, 1e-3, 0.999)
        kappa = -np.log(phi_c)                                # reversion speed
        half_life = np.log(2.0) / (kappa + EPS)              # seconds to half-revert
        cols[f"bd_ou_phi_{tag}"] = phi
        cols[f"bd_ou_halflife_{tag}"] = np.clip(half_life, 0.0, 1e4)
    # --- basis realized-vol TERM STRUCTURE (ratios across scales) ---
    rv = {}
    for tag, win in SCALES.items():
        _, s = _causal_roll_mean_std(dbasis, win)
        rv[tag] = s
    cols["bd_basisvol_ts_60_600"] = (rv["60s"] + EPS) / (rv["600s"] + EPS)    # short/med
    cols["bd_basisvol_ts_600_3600"] = (rv["600s"] + EPS) / (rv["3600s"] + EPS)  # med/long
    # --- momentum / acceleration RATIO (curvature of the basis path) ---
    l60, o60 = _lag_on_grid(sec, basis, 60)
    l600, o600 = _lag_on_grid(sec, basis, 600)
    l1200, o1200 = _lag_on_grid(sec, basis, 1200)
    mom_fast = np.full(sec.size, np.nan); mom_fast[o60] = basis[o60] - l60[o60]
    mom_slow = np.full(sec.size, np.nan); mom_slow[o600] = basis[o600] - l600[o600]
    # acceleration over 600s windows: (b_t - b_t600) - (b_t600 - b_t1200)
    acc = np.full(sec.size, np.nan); good = o600 & o1200
    acc[good] = (basis[good] - l600[good]) - (l600[good] - l1200[good])
    cols["bd_mom_ratio_60_600"] = mom_fast / (np.abs(mom_slow) + EPS)
    cols["bd_accel_600s"] = acc
    # --- curvature: 2nd derivative normalised by local vol (designed) ---
    cols["bd_curvature_600s"] = acc / (rv["600s"] * 600.0 + EPS)
    out = {} if pred_sec is not None else cols
    if pred_sec is not None:
        # sample all the full-grid cols at the prediction seconds (cheap),
        # then add the pctrank-spread computed ONLY at pred seconds (O(N*win)).
        for k, v in cols.items():
            out[k] = _sample_grid(sec, v, pred_sec)
    # --- multi-window percentile-rank SPREAD (regime dislocation persistence) ---
    psec = pred_sec if pred_sec is not None else sec
    pr30 = _pctrank_at(sec, basis, 1800, psec)
    pr120 = _pctrank_at(sec, basis, 7200, psec)
    out["bd_pctrank_spread_30_120"] = pr30 - pr120  # short-window extreme vs long
    return out


# =========================================================================== #
# FAMILY LL -- TIME-VARYING LEAD-LAG (does the lead-lag itself predict?)
# =========================================================================== #
# MECHANISM: spot is measured ~2x cleaner and can LEAD perp. The rich set took a
# static spot-minus-perp cumulative gap. Here we measure the *rolling cross-corr
# peak-lag and strength*: if spot currently leads perp strongly (high cross-corr
# at +lag), a spot move not yet matched by perp predicts a perp catch-up. The
# lead-lag STRENGTH is itself a regime: when coupling is tight, the gap closes
# fast (stronger r); when decoupled, perp wanders on its own forces.
def family_leadlag(src):
    sec = src["sec"]
    sret = src["spot_ret_1s"]; pret = src["perp_ret_1s"]
    cols = {}
    LAGS = [1, 3, 5, 10, 30]
    for tag, win in {"600s": 600, "3600s": 3600}.items():
        # cross-corr of perp_ret[t] with spot_ret[t-lag] (spot leads): scan lags
        ccs = np.stack([_causal_crosscorr_at_lag(pret, sret, win, lg) for lg in LAGS], 0)
        peak = np.nanmax(ccs, axis=0)                          # strength of spot lead
        argl = np.array(LAGS)[np.nanargmax(np.nan_to_num(ccs, nan=-9), axis=0)]
        cols[f"ll_peakcorr_{tag}"] = peak                      # how tightly spot leads
        cols[f"ll_peaklag_{tag}"] = argl.astype(np.float64)    # at what lag
        # contemporaneous coupling (lag-0) for the regime contrast
        cc0 = _causal_crosscorr_at_lag(pret, sret, win, 0)
        cols[f"ll_couple0_{tag}"] = cc0
        cols[f"ll_leadgain_{tag}"] = peak - cc0                # lead beyond contemporaneous
    # spot cumulative move NOT yet in perp, GATED by current lead strength:
    s_cum = _causal_roll_sum(sret, 30); p_cum = _causal_roll_sum(pret, 30)
    gap = s_cum - p_cum
    strength = _causal_crosscorr_at_lag(pret, sret, 600, 5)
    cols["ll_gap_x_strength_30s"] = gap * np.clip(strength, 0, 1)  # designed: catch-up pressure
    return cols


# =========================================================================== #
# FAMILY OF -- ORDER-FLOW HIGHER-ORDER (perp last-snapshot driven)
# =========================================================================== #
# MECHANISM: signed order flow is the proximate cause of price moves. Levels are
# in the 64-feat set. The HIGHER-ORDER content is (i) PERSISTENCE -- autocorr of
# the flow tells whether the current imbalance will continue (informed/herded)
# or revert (noise); (ii) SELF-EXCITATION -- Hawkes-style intensity: a burst of
# large-trade arrivals raises the probability of further bursts (clustering) ->
# continuation; (iii) flow ACCELERATION -- the rate of change of the imbalance.
# Built from the perp per-second residual flow proxy (resid_ret as flow sign) and
# the perp last-snapshot flow channels.
def family_orderflow(src, perp_last, pred_sec):
    sec = src["sec"]
    resid = src["resid_ret_1s"]                  # perp-specific 1s impulse (flow proxy)
    aresid = np.abs(resid)
    cols = {}
    # --- persistence: rolling lag-1 autocorr of the signed residual impulse ---
    for tag, win in SCALES.items():
        cols[f"of_persist_{tag}"] = _causal_roll_autocorr1(resid, win)
    # --- Hawkes-style self-excitation intensity: EMA of large-impulse arrivals ---
    # large = |resid| > 2*trailing std; intensity = decaying count (clustering).
    _, rstd = _causal_roll_mean_std(resid, 600)
    large = (aresid > 2.0 * (rstd + EPS)).astype(np.float64)
    for tag, span in {"60s": 60, "600s": 600}.items():
        cols[f"of_hawkes_intensity_{tag}"] = _causal_ema_shift1(large, span)
    # branching-ratio proxy: intensity now vs intensity baseline (excitation gain)
    base_int = _causal_ema_shift1(large, 3600)
    cols["of_excite_gain"] = (_causal_ema_shift1(large, 60) + EPS) / (base_int + EPS)
    # --- flow momentum & acceleration of the signed impulse (multi-horizon) ---
    f60 = _causal_roll_sum(resid, 60); f600 = _causal_roll_sum(resid, 600)
    cols["of_flowmom_60s"] = f60
    cols["of_flowmom_ratio_60_600"] = f60 / (np.abs(f600) + EPS)
    l30, o30 = _lag_on_grid(sec, f60, 30)
    acc = np.full(sec.size, np.nan); acc[o30] = f60[o30] - l30[o30]
    cols["of_flowaccel_60s"] = acc
    out = {k: _sample_grid(sec, v, pred_sec) for k, v in cols.items()}
    # --- trade-size distribution shift from the perp snapshot (entropy proxy) ---
    # large_trade_arrival_60s vs trade_intensity_30s: a rising ratio = size up-shift
    lta = perp_last[:, FEAT["large_trade_arrival_60s"]]
    ti = perp_last[:, FEAT["trade_intensity_30s"]]
    out["of_largeshare"] = lta / (ti + EPS)            # share of flow in large prints
    # vpin term structure (toxicity acceleration): vpin60 vs vpin300
    out["of_vpin_ts"] = (perp_last[:, FEAT["vpin_60s"]] + EPS) / (perp_last[:, FEAT["vpin_300s"]] + EPS)
    return out


# =========================================================================== #
# FAMILY BS -- BOOK-SHAPE EVOLUTION (rate of change of the perp book shape)
# =========================================================================== #
# MECHANISM: it is not the book shape but its CHANGE that signals incoming
# pressure -- depth withdrawing on one side (concentration shifting), the
# microprice curving, the slope steepening. The 64-feat set has the LEVELS
# (bid/ask concentration, slope, microprice_dev); here we expose their causal
# CHANGE over {60,600}s from the per-snapshot grid, plus the cross-venue
# shape-divergence RATE (perp book reshaping faster than spot = perp-specific).
def family_bookshape(src, spot_last, perp_last, pred_sec, ts_grid):
    # snapshots are at irregular pred seconds; build a per-pred-row diff by lagging
    # the snapshot series in pred-row space aligned by time. We compute changes
    # directly on the pred grid (rows are time-sorted) using time-aware lags.
    cols = {}
    tsec = ts_grid // US                                  # pred second of each row
    def _row_lag(feat_arr, lag_s):
        # value of feat_arr at the row whose pred-second is closest to (t - lag_s)
        target = tsec - lag_s
        pos = np.searchsorted(tsec, target, side="right") - 1
        ok = pos >= 0
        out = np.full(feat_arr.shape[0], np.nan)
        out[ok] = feat_arr[np.clip(pos[ok], 0, feat_arr.shape[0]-1)]
        return out
    # perp book-shape CHANGES
    for nm in ["bid_concentration", "ask_concentration", "microprice_dev_bps",
               "bid_slope_L10", "ask_slope_L10", "book_pressure_imbalance"]:
        cur = perp_last[:, FEAT[nm]]
        for lag in (60, 600):
            cols[f"bs_d_{nm}_{lag}s"] = cur - _row_lag(cur, lag)
    # microprice curvature: (mpdev now) - 2*(60s ago) + (120s ago)  -- 2nd diff
    mp = perp_last[:, FEAT["microprice_dev_bps"]]
    cols["bs_microprice_curv"] = mp - 2*_row_lag(mp, 60) + _row_lag(mp, 120)
    # depth-concentration ASYMMETRY change (bid vs ask reshaping)
    casym = perp_last[:, FEAT["bid_concentration"]] - perp_last[:, FEAT["ask_concentration"]]
    cols["bs_d_concasym_60s"] = casym - _row_lag(casym, 60)
    # cross-venue shape-divergence RATE: d(perp_obi_L5 - spot_obi_L5)/dt over 60s
    div_obi = perp_last[:, FEAT["obi_L5"]] - spot_last[:, FEAT["obi_L5"]]
    cols["bs_xshape_div_rate_60s"] = div_obi - _row_lag(div_obi, 60)
    div_mp = perp_last[:, FEAT["microprice_dev_bps"]] - spot_last[:, FEAT["microprice_dev_bps"]]
    cols["bs_xshape_divmp_rate_60s"] = div_mp - _row_lag(div_mp, 60)
    return {k: np.nan_to_num(v, nan=0.0, posinf=0.0, neginf=0.0) for k, v in cols.items()}


# =========================================================================== #
# FAMILY RG -- REGIME INDICATORS (for FiLM / regime_prior) + XS interactions
# =========================================================================== #
# MECHANISM: the signal is regime-dependent (strong/trending months pay, choppy
# don't). A CAUSAL regime indicator lets a model (FiLM) gate its alpha. We expose
# realized-vol term structure, the variance-ratio (trend vs chop), a Hurst-like
# exponent, a liquidity regime (perp/spot spread+depth), and the lead-lag regime.
# XS = designed cross-scale interaction products (dislocation x vol-regime, etc.)
def family_regime(src, spot_last, perp_last, pred_sec):
    sec = src["sec"]
    sret = src["spot_ret_1s"]; pret = src["perp_ret_1s"]; basis = src["basis_bps"]
    cols = {}
    # realized-vol term structure of PERP returns (short/long)
    rv = {}
    for tag, win in SCALES.items():
        _, s = _causal_roll_mean_std(pret, win); rv[tag] = s
    cols["rg_rvol_ts_60_600"] = (rv["60s"] + EPS) / (rv["600s"] + EPS)
    cols["rg_rvol_ts_600_3600"] = (rv["600s"] + EPS) / (rv["3600s"] + EPS)
    cols["rg_rvol_600s"] = rv["600s"]
    # variance ratio (trend vs chop), multi-scale q
    cols["rg_vr_q30_w3600"] = _variance_ratio(pret, 3600, 30)
    cols["rg_vr_q120_w3600"] = _variance_ratio(pret, 3600, 120)
    # Hurst-like: log(VR(q))/(2 log q) + 0.5  (H>0.5 trending, <0.5 reverting)
    vr = _variance_ratio(pret, 3600, 60)
    cols["rg_hurst_like"] = 0.5 + np.log(np.clip(vr, 1e-3, 1e3)) / (2*np.log(60))
    out = {k: _sample_grid(sec, v, pred_sec) for k, v in cols.items()}
    # liquidity regime from snapshots: perp/spot spread ratio & depth ratio
    out["rg_liq_spread_ratio"] = np.log((perp_last[:, FEAT["spread_bps"]] + EPS) /
                                        (spot_last[:, FEAT["spread_bps"]] + EPS))
    out["rg_liq_depth_ratio"] = np.log((perp_last[:, FEAT["bid_depth_L25"]] +
                                        perp_last[:, FEAT["ask_depth_L25"]] + EPS) /
                                       (spot_last[:, FEAT["bid_depth_L25"]] +
                                        spot_last[:, FEAT["ask_depth_L25"]] + EPS))
    # --- XS cross-scale designed interactions (regime-conditional dislocation) ---
    # basis z-ish (level/local-vol) x vol regime: a dislocation in a high-vol regime
    # reverts harder. Build a causal basis-z(600) and multiply by rvol term ratio.
    bm, bs = _causal_roll_mean_std(basis, 600)
    bz600 = _sample_grid(sec, (basis - bm)/(bs+EPS), pred_sec)
    out["xs_basisz_x_volregime"] = bz600 * out["rg_rvol_ts_60_600"]
    out["xs_basisz_x_vr"] = bz600 * out["rg_vr_q30_w3600"]
    # cross-venue obi divergence x trend indicator (div pays in trends)
    div_obi5 = perp_last[:, FEAT["obi_L5"]] - spot_last[:, FEAT["obi_L5"]]
    out["xs_divobi_x_hurst"] = div_obi5 * out["rg_hurst_like"]
    return out


# =========================================================================== #
# top-level per-day assembly
# =========================================================================== #
HO_FAMILIES = ("bd", "ll", "of", "bs", "rg")


def _finalize(cols, sec=None, pred_sec=None):
    """Optionally sample grid cols at pred_sec, then nan/inf->0 and stack."""
    if pred_sec is not None and sec is not None:
        cols = {k: _sample_grid(sec, v, pred_sec) if np.asarray(v).size == sec.size else v
                for k, v in cols.items()}
    names = list(cols.keys())
    X = np.column_stack([np.asarray(cols[n], np.float64) for n in names])
    X = np.nan_to_num(X, nan=0.0, posinf=0.0, neginf=0.0)
    return names, X


def build_day_ho(day, mid_dir, lastts_dir):
    lc = np.load(p.join(lastts_dir, f"{day}.npz"))
    ts = lc["timestamps"].astype(np.int64)
    perp_ts = lc["perp_ts"].astype(np.int64)
    spot_last = lc["spot_last"].astype(np.float64)
    perp_last = lc["perp_last"].astype(np.float64)
    pred_sec = ts // US
    zm = np.load(p.join(mid_dir, f"{day}.npz"))
    src = per_second_source(zm["sec"].astype(np.int64), zm["spot_mid"], zm["perp_mid"])
    sec = src["sec"]

    fam = {}
    fam["bd"] = _finalize(family_basis_dynamics(src, pred_sec))
    fam["ll"] = _finalize(family_leadlag(src), sec, pred_sec)
    fam["of"] = _finalize(family_orderflow(src, perp_last, pred_sec))      # already sampled
    fam["bs"] = _finalize(family_bookshape(src, spot_last, perp_last, pred_sec, ts))
    fam["rg"] = _finalize(family_regime(src, spot_last, perp_last, pred_sec))
    return dict(ts=ts, perp_ts=perp_ts, fam=fam)


if __name__ == "__main__":
    import argparse
    ap = argparse.ArgumentParser()
    ap.add_argument("--probe", nargs="*", default=["2025-02-10", "2026-03-15"])
    args = ap.parse_args()
    MID = p.join(_REPO, "data", "mid_cache"); LAST = p.join(_REPO, "data", "lastts_cache")
    for day in args.probe:
        d = build_day_ho(day, MID, LAST)
        print(f"\n=== {day} N={d['ts'].size} ===")
        tot = 0
        for f in HO_FAMILIES:
            names, X = d["fam"][f]; tot += len(names)
            fin = np.isfinite(X).all(axis=1).mean()
            print(f"  {f} k={len(names):2d} finite={fin:.3f} std=[{X.std(0).min():.2e},{X.std(0).max():.2e}]")
            print(f"     {names}")
        print(f"  TOTAL k={tot}")
