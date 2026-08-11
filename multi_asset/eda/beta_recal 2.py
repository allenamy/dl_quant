#!/usr/bin/env python
"""
beta_recal.py — RE-FRAME magnitude calibration around the CORRECT objective:
    beta(realized_y on prediction) ~ 1   (conditional-mean correctness)
NOT sigma_pred = sigma_y (CCC / sigma-match), which manufactures over-confident noise.

INSIGHT: for a predictor with correlation rho to y, a well-calibrated conditional-mean
predictor has sigma_pred/sigma_y ~ rho. For our low-SNR (rho~0.05-0.12) that small
sigma_ratio is HONEST (only ~rho^2 of variance is predictable), not a defect.
The calibration target is beta -> 1. Forcing sigma_ratio -> 1 (CCC) implies beta = 1/rho
of over-confidence -> beta collapses far below 1 once you eval realized vs scaled pred.

CONTRACT: CPU numpy/sklearn on EXISTING saved preds. No training, no GPU.
Adapted from /tmp/calib.py (isotonic). Reuses its loader, demean, causal forward-chain,
row_rank_ic. Works in cross-sectionally-demeaned NORMALIZED-residual units (shared map),
then de-normalizes to bps via * resid_sigma * 1e4 (identical units to calib.py).

Per horizon, per fold, STRICTLY CAUSAL (forward-chaining expanding window over fold's own
test days; the map applied to day d_k is fit ONLY on days < d_k of the same fold; first
WARMUP_DAYS flagged and excluded from all reported (after) metrics).

TASKS:
 1. RAW (uncalibrated) beta = cov(y, yhat)/var(yhat) in return space (demeaned), per-asset
    and pooled, BEFORE calibration. Plus sigma_ratio (diagnostic only) and IC (=corr).
 2. POST-HOC beta LINEAR rescale: yhat_cal = beta_fold * yhat (beta from prior days only).
    NOTE on the algebra: regressing realized on s*yhat gives slope beta_raw/s, so to send
    the slope -> 1 we set s = beta_raw, i.e. MULTIPLY the demeaned pred by the regression
    slope. Here beta_raw~0.5 (pred is ~1/beta too dispersed: sigma_ratio ~ IC/beta), so the
    fix SHRINKS the pred and moves sigma_ratio down to ~IC (the honest level). (Dividing by
    beta would inflate the pred and HALVE the slope — the wrong direction; the prompt's
    "1/beta" intuition refers to the over-confidence factor, the applied scale is *beta*.)
    Re-measure beta (should ~1), confirm rank-IC unchanged, confirm sigma_ratio -> ~IC.
 3. ISOTONIC (same causal scheme) — measure the BETA of the isotonic output (the metric
    /tmp/calib.py never reported). Compare: which gets beta closest to 1 while rank-safe.
 4. Sizing usability: position ∝ yhat_cal. Report the implied bet-size scale factor that
    CCC (sigma-match) would have applied vs the beta=1 calib — show CCC over-sizes ~1/IC.
 5. Corrected dual-caliber schema: beta (target~1), IC, sigma_ratio(=IC diag), per fold.

CCC-IS-WRONG demonstration: report what beta CCC (scale so sigma_pred=sigma_y) would imply
when you regress realized on the CCC-scaled pred -> beta_ccc = IC (collapses to rho).
"""
import os, json, time
import numpy as np
from scipy.stats import rankdata
from sklearn.isotonic import IsotonicRegression

DATA = "/mnt/storage/private/work_hsy/quant_research_multi_asset/multi_asset/exports/train"
HORIZONS = ["HF60_y", "HF180_y", "RAW_y600"]
SYMBOLS = ['bnfbtc','bnfeth','bnfsol','bnfbnb','bnfxrp','bnfdog','bnfada',
           'bnflink','bnfbch','bnftrx','bnfltc','bnfdot','bnffil','bnfetc']
NFOLD = 3
WARMUP_DAYS = 8
MIN_FIT = 2000
OUT_JSON = "/tmp/beta_recal.json"


def load_horizon(h):
    pr = np.load(f"{DATA}/{h}/panel_ref.npz", allow_pickle=True)
    panel = dict(day=pr["day"], Y=pr["Y"].astype(np.float64), CL=pr["CL"], ts=pr["ts"])
    folds = []
    for f in range(NFOLD):
        d = np.load(f"{DATA}/{h}/fold_{f}_preds.npz", allow_pickle=True)
        folds.append(dict(pred=d["pred"].astype(np.float64), te_rows=d["te_rows"],
                          resid_sigma=d["resid_sigma"].astype(np.float64),
                          horizon=int(d["horizon"])))
    return panel, folds


def xsec_demean(arr, valid):
    a = np.where(valid, arr, np.nan)
    mean = np.nanmean(a, axis=1, keepdims=True)
    return a - mean


def row_rank_ic(pred_d, real_d, valid, min_assets=3):
    rics = []
    for i in range(pred_d.shape[0]):
        vi = valid[i]
        if vi.sum() >= min_assets:
            a = pred_d[i, vi]; b = real_d[i, vi]
            ra = rankdata(a); rb = rankdata(b)
            if ra.std() > 0 and rb.std() > 0:
                rics.append(np.corrcoef(ra, rb)[0, 1])
    return float(np.mean(rics)) if rics else np.nan, len(rics)


def beta_covvar(y, yhat):
    """beta = cov(y, yhat)/var(yhat) — regression slope of realized on prediction."""
    v = np.isfinite(y) & np.isfinite(yhat)
    if v.sum() < 10:
        return np.nan
    yc = y[v] - y[v].mean(); pc = yhat[v] - yhat[v].mean()
    var = np.dot(pc, pc)
    return float(np.dot(yc, pc) / var) if var > 1e-30 else np.nan


def pearson(y, yhat):
    v = np.isfinite(y) & np.isfinite(yhat)
    if v.sum() < 10:
        return np.nan
    a = y[v]; b = yhat[v]
    if a.std() < 1e-30 or b.std() < 1e-30:
        return np.nan
    return float(np.corrcoef(a, b)[0, 1])


def fit_isotonic(x, y):
    iso = IsotonicRegression(out_of_bounds="clip", increasing=True)
    iso.fit(x, y)
    return iso


def process_fold(panel, fold):
    day_all = panel["day"]; Y = panel["Y"]; CL = panel["CL"]
    te = fold["te_rows"]; rs = fold["resid_sigma"]
    p = fold["pred"][te]            # (R,14) normalized residual units
    y = Y[te]                       # (R,14) raw return
    cl = CL[te]
    days = day_all[te]
    R, A = p.shape
    valid = np.isfinite(p) & np.isfinite(y) & cl

    # cross-sectional demean (shared-map space). pred already normalized-resid; bring realized
    # into normalized-resid units too (/resid_sigma) for the shared monotone/linear map.
    y_norm = y / rs[None, :]
    pred_d = xsec_demean(p, valid)                  # demeaned normalized pred (the predictor)
    realn_d = xsec_demean(y_norm, valid)            # demeaned normalized realized (target)
    pred_ret_d = pred_d * rs[None, :]               # return-space demeaned pred
    realret_d = xsec_demean(y, valid)               # return-space demeaned realized (raw units)

    vflat = valid.ravel()

    # ---------- TASK 1: BEFORE (raw) metrics ----------
    # pooled beta in RETURN space (raw bps units): realized on prediction
    beta_before_pool = beta_covvar(realret_d.ravel()[vflat], pred_ret_d.ravel()[vflat])
    ic_pool = pearson(realret_d.ravel()[vflat], pred_ret_d.ravel()[vflat])  # scale-free, == norm-space corr
    sp_before = np.nanstd(pred_ret_d.ravel()[vflat])
    sy = np.nanstd(realret_d.ravel()[vflat])
    sig_ratio_before = sp_before / sy
    # per-asset beta (raw)
    beta_before_asset = {}
    for a in range(A):
        va = valid[:, a]
        if va.sum() >= 50:
            beta_before_asset[SYMBOLS[a]] = beta_covvar(realret_d[va, a], pred_ret_d[va, a])
    ric_before, nric = row_rank_ic(pred_d, realn_d, valid)

    # ---------- causal forward-chaining: estimate beta on prior days, apply 1/beta ----------
    udays = np.sort(np.unique(days))
    lin_cal_d = np.full((R, A), np.nan)   # 1/beta linear-rescaled demeaned NORM pred
    iso_cal_d = np.full((R, A), np.nan)   # isotonic-calibrated demeaned NORM pred
    warmup_flag = np.zeros(R, dtype=bool)
    fold_betas = []                       # the causal beta_fold used each day (norm space)

    def beta_norm(mask):
        # beta in normalized demeaned space: cov(realn_d, pred_d)/var(pred_d)
        return beta_covvar(realn_d[mask], pred_d[mask])

    # warmup: identity scaling flagged (no prior history) — use in-sample beta on warmup block
    warm_days = udays[:WARMUP_DAYS]
    warm_rows = np.isin(days, warm_days)
    wm = valid & warm_rows[:, None]
    if wm.sum() >= 50:
        b_w = beta_norm(wm)
        if not np.isfinite(b_w) or abs(b_w) < 1e-6:
            b_w = 1.0
        lin_cal_d[wm] = pred_d[wm] * b_w   # multiply by slope -> regression slope of realized-on-cal -> 1
        iso_w = fit_isotonic(pred_d[wm], realn_d[wm]) if wm.sum() >= MIN_FIT else None
        iso_cal_d[wm] = iso_w.predict(pred_d[wm]) if iso_w is not None else pred_d[wm] * b_w
    warmup_flag[warm_rows] = True

    for k in range(WARMUP_DAYS, len(udays)):
        dk = udays[k]
        hist_rows = np.isin(days, udays[:k])
        hist_mask = valid & hist_rows[:, None]
        cur_rows = (days == dk)
        cur_mask = valid & cur_rows[:, None]
        if cur_mask.sum() == 0:
            continue
        if hist_mask.sum() >= 50:
            b = beta_norm(hist_mask)
            if not np.isfinite(b) or abs(b) < 1e-6:
                b = 1.0
            fold_betas.append(b)
            lin_cal_d[cur_mask] = pred_d[cur_mask] * b   # multiply by slope -> beta->1
            if hist_mask.sum() >= MIN_FIT:
                iso = fit_isotonic(pred_d[hist_mask], realn_d[hist_mask])
                iso_cal_d[cur_mask] = iso.predict(pred_d[cur_mask])
            else:
                iso_cal_d[cur_mask] = pred_d[cur_mask] * b
        else:
            lin_cal_d[cur_mask] = pred_d[cur_mask]
            iso_cal_d[cur_mask] = pred_d[cur_mask]
            warmup_flag[cur_rows] = True

    # ---------- AFTER metrics (exclude warmup for honesty) ----------
    keep = valid & (~warmup_flag[:, None]) & np.isfinite(lin_cal_d) & np.isfinite(iso_cal_d)
    kflat = keep.ravel()

    # de-normalize calibrated to return space (raw bps base units)
    lin_ret_d = lin_cal_d * rs[None, :]
    iso_ret_d = iso_cal_d * rs[None, :]

    real_k = realret_d.ravel()[kflat]
    sy_k = np.nanstd(real_k)

    # ---- 1/beta LINEAR ----
    lin_k = lin_ret_d.ravel()[kflat]
    beta_after_lin = beta_covvar(real_k, lin_k)
    sig_ratio_lin = np.nanstd(lin_k) / sy_k
    ric_lin, _ = row_rank_ic(lin_cal_d, realn_d, keep)
    # per-asset beta after linear
    beta_lin_asset = {}
    for a in range(A):
        ka = keep[:, a]
        if ka.sum() >= 50:
            beta_lin_asset[SYMBOLS[a]] = beta_covvar(realret_d[ka, a], lin_ret_d[ka, a])

    # ---- ISOTONIC ----
    iso_k = iso_ret_d.ravel()[kflat]
    beta_after_iso = beta_covvar(real_k, iso_k)
    sig_ratio_iso = np.nanstd(iso_k) / sy_k
    ric_iso, _ = row_rank_ic(iso_cal_d, realn_d, keep)

    # IC on the kept region (for honest per-fold headline) — scale-free, same for raw/lin/iso-monotone-pres
    ic_k_lin = pearson(real_k, lin_k)      # == raw IC (linear rescale preserves corr exactly)
    ic_k_iso = pearson(real_k, iso_k)      # isotonic can mildly change Pearson

    # ---------- TASK 4: sizing usability ----------
    # position ∝ calibrated bps. Under beta=1 calib, E[realized | pred] = pred, so sizing on
    # bps is correctly scaled (a +5bps pred is a genuine +5bps conditional mean bet).
    # CCC (sigma-match) would multiply the bps by 1/sig_ratio_before to force sigma_pred=sigma_y.
    # CCC (sigma-match) multiplies the demeaned pred by sy/sp = 1/sig_ratio_before so that
    # sigma_pred == sigma_y. The beta=1 linear calib multiplies by beta_before (<1).
    ccc_scale = 1.0 / max(sig_ratio_before, 1e-9)   # CCC multiplicative scale on demeaned pred
    lin_scale = beta_before_pool                    # beta=1 calib multiplicative scale
    # beta CCC would imply: regress realized on the CCC-scaled pred -> slope = beta_before / ccc_scale
    #   = beta_before * sig_ratio_before = IC. So CCC's "conditional mean" has slope ~IC, not 1:
    #   it is ~1/IC times over-confident.
    beta_ccc_implied = beta_before_pool * sig_ratio_before   # == pooled IC; CCC bet is ~1/IC too big
    # bet-size sanity: ratio of CCC bet size to beta=1 bet size at any fixed pred value (~1/IC)
    bet_inflation_ccc = ccc_scale / max(lin_scale, 1e-9)

    diag = dict(
        n_valid=int(valid.sum()), n_keep=int(keep.sum()),
        # task1 raw
        beta_before_pool=beta_before_pool, ic_pool=ic_pool,
        sig_ratio_before=float(sig_ratio_before),
        rank_ic_before=ric_before, n_ric=nric,
        beta_before_asset=beta_before_asset,
        # task2 linear 1/beta
        beta_after_lin=beta_after_lin, sig_ratio_lin=float(sig_ratio_lin),
        rank_ic_lin=ric_lin, ic_lin=ic_k_lin,
        beta_lin_asset=beta_lin_asset,
        median_causal_beta=float(np.median(fold_betas)) if fold_betas else np.nan,
        # task3 isotonic
        beta_after_iso=beta_after_iso, sig_ratio_iso=float(sig_ratio_iso),
        rank_ic_iso=ric_iso, ic_iso=ic_k_iso,
        # task4/CCC
        ccc_scale=float(ccc_scale), beta_ccc_implied=float(beta_ccc_implied),
        bet_inflation_ccc_vs_lin=float(bet_inflation_ccc),
    )
    return diag


def main():
    t0 = time.time()
    results = {}
    for h in HORIZONS:
        panel, folds = load_horizon(h)
        results[h] = dict(per_fold=[], horizon=int(folds[0]["horizon"]))
        for f in range(NFOLD):
            d = process_fold(panel, folds[f]); d["fold"] = f
            results[h]["per_fold"].append(d)
            print("[%s f%d] beta %.3f -> lin %.3f / iso %.3f | IC %.4f | sigr %.4f -> lin %.4f / iso %.4f | rankIC %.4f -> lin %.4f / iso %.4f | beta_ccc_implied %.3f"
                  % (h, f, d["beta_before_pool"], d["beta_after_lin"], d["beta_after_iso"],
                     d["ic_pool"], d["sig_ratio_before"], d["sig_ratio_lin"], d["sig_ratio_iso"],
                     d["rank_ic_before"], d["rank_ic_lin"], d["rank_ic_iso"], d["beta_ccc_implied"]),
                  flush=True)
        pf = results[h]["per_fold"]
        m = lambda k: float(np.nanmean([x[k] for x in pf]))
        results[h]["avg"] = dict(
            beta_before_pool=m("beta_before_pool"), beta_after_lin=m("beta_after_lin"),
            beta_after_iso=m("beta_after_iso"), ic_pool=m("ic_pool"),
            sig_ratio_before=m("sig_ratio_before"), sig_ratio_lin=m("sig_ratio_lin"),
            sig_ratio_iso=m("sig_ratio_iso"), rank_ic_before=m("rank_ic_before"),
            rank_ic_lin=m("rank_ic_lin"), rank_ic_iso=m("rank_ic_iso"),
            rank_ic_delta_lin=float(m("rank_ic_lin") - m("rank_ic_before")),
            rank_ic_delta_iso=float(m("rank_ic_iso") - m("rank_ic_before")),
            beta_ccc_implied=m("beta_ccc_implied"),
            median_causal_beta=m("median_causal_beta"),
        )

    results["_meta"] = dict(
        elapsed_s=round(time.time() - t0, 1),
        objective="beta(realized on pred)->1 (conditional-mean correctness); sigma_ratio is a diagnostic ~ IC, NOT a target",
        ccc_note="CCC (sigma-match) forces sigma_pred=sigma_y; the implied regression beta of the CCC-scaled pred collapses to ~IC (beta_ccc_implied), i.e. CCC manufactures ~1/IC over-confidence",
        causality="forward-chaining expanding-window over fold test days; map for day d_k fit only on days<d_k same fold; first %d days warmup-flagged & excluded from after-metrics" % WARMUP_DAYS,
        units="calibrate in xsec-demeaned NORMALIZED residual units; bps = cal_norm * resid_sigma * 1e4; beta measured in return space",
    )
    with open(OUT_JSON, "w") as fh:
        json.dump(results, fh, indent=2,
                  default=lambda o: None if isinstance(o, float) and not np.isfinite(o) else o)
    print("\nDONE in %.1fs -> %s" % (results["_meta"]["elapsed_s"], OUT_JSON), flush=True)


if __name__ == "__main__":
    main()
