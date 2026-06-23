#!/usr/bin/env python
"""
Calibration + dual-caliber tradeable output for multi-asset crypto predictions.

CONTRACT: CPU numpy/sklearn job on EXISTING saved predictions (no training, no GPU).

Model is a strong RANKER, weak MAGNITUDE predictor:
  - cross-sectional rank-IC strong (y60~0.12, y180~0.07, y600~0.05)
  - sigma_pred/sigma_act ~0.08-0.15 (magnitude shrunk ~10x)
  - decile-monotonicity high -> rank->return map IS monotone -> calibration is a pure SCALE fix.

Per horizon, per fold, STRICTLY CAUSAL:
  Folds are temporally ordered & disjoint (fold0<fold1<fold2). Within a fold we use
  FORWARD-CHAINING (expanding window) over the fold's own test DAYS:
    sort the fold's test days chronologically; to calibrate rows on day d_k,
    fit the isotonic map ONLY on rows from days [d_0 .. d_{k-1}] (strictly earlier, same fold).
  The first WARMUP_DAYS days are calibrated using a pooled isotonic fit on those
  warmup days themselves (the only days with no prior history) -- this is the single
  unavoidable in-sample region and is FLAGGED in the output (causal_warmup=True).
  No calibrated row outside the warmup is ever fit on itself or any future row.

Units: `pred` is in NORMALIZED RESIDUAL units. return-space = pred * resid_sigma (per asset).
We calibrate in cross-sectionally-demeaned NORMALIZED-residual space (so the monotone map is
cross-asset shared), then de-normalize to bps via * resid_sigma * 1e4.

Tasks:
 1. Isotonic magnitude calibration (causal). sigma ratio before/after, decile-mono, rank-IC unchanged.
 2. expected_residual_bps = m(zhat) * resid_sigma * 1e4.
 3. Tail probs from calibrated point + empirical residual dist (no quantiles in preds). Reliability/Brier.
 4. Conviction sizing: IC of |calibrated| vs |realized|; sizing-prop-|cal| vs equal-weight book.
 5. 6-item deliverable schema CSV sample.
"""
import os, json, time
import numpy as np
from scipy.stats import rankdata, spearmanr
from sklearn.isotonic import IsotonicRegression

DATA = "/mnt/storage/private/work_hsy/quant_research_multi_asset/multi_asset/exports/train"
HORIZONS = ["HF60_y", "HF180_y", "RAW_y600"]
SYMBOLS = ['bnfbtc','bnfeth','bnfsol','bnfbnb','bnfxrp','bnfdog','bnfada',
           'bnflink','bnfbch','bnftrx','bnfltc','bnfdot','bnffil','bnfetc']
NFOLD = 3
WARMUP_DAYS = 8          # min history before causal calibration kicks in
MIN_FIT = 2000           # min (asset,row) samples to fit a stable isotonic map
N_DECILE = 10
OUT_JSON = "/tmp/calib.json"
OUT_CSV = "/tmp/calib_sample.csv"


def load_horizon(h):
    pr = np.load(f"{DATA}/{h}/panel_ref.npz", allow_pickle=True)
    panel = dict(ts=pr["ts"], day=pr["day"], Y=pr["Y"].astype(np.float64),
                 CL=pr["CL"], symbols=pr["symbols"])
    folds = []
    for f in range(NFOLD):
        d = np.load(f"{DATA}/{h}/fold_{f}_preds.npz", allow_pickle=True)
        folds.append(dict(pred=d["pred"].astype(np.float64), te_rows=d["te_rows"],
                          resid_sigma=d["resid_sigma"].astype(np.float64),
                          horizon=int(d["horizon"])))
    return panel, folds


def xsec_demean(arr, valid):
    """Cross-sectionally (per row) demean over valid assets only. NaN elsewhere."""
    a = np.where(valid, arr, np.nan)
    mean = np.nanmean(a, axis=1, keepdims=True)
    return a - mean  # NaN where invalid or empty-row


def decile_mono(pred_flat, real_flat, n=N_DECILE):
    """Fraction of adjacent-decile transitions where mean realized is increasing.
    Returns (mono_frac, spearman of decile-mean-pred vs decile-mean-real)."""
    if len(pred_flat) < n * 5:
        return np.nan, np.nan
    order = np.argsort(pred_flat)
    bins = np.array_split(order, n)
    mp = np.array([pred_flat[b].mean() for b in bins])
    mr = np.array([real_flat[b].mean() for b in bins])
    inc = np.mean(np.diff(mr) > 0)
    sp = spearmanr(mp, mr).correlation
    return float(inc), float(sp)


def row_rank_ic(pred_d, real_d, valid, min_assets=3):
    """Mean per-row (cross-sectional) Spearman rank-IC over rows with >=min_assets valid."""
    rics = []
    n = pred_d.shape[0]
    for i in range(n):
        vi = valid[i]
        if vi.sum() >= min_assets:
            a = pred_d[i, vi]; b = real_d[i, vi]
            ra = rankdata(a); rb = rankdata(b)
            if ra.std() > 0 and rb.std() > 0:
                rics.append(np.corrcoef(ra, rb)[0, 1])
    return float(np.mean(rics)) if rics else np.nan, len(rics)


def fit_isotonic(x, y):
    iso = IsotonicRegression(out_of_bounds="clip", increasing=True)
    iso.fit(x, y)
    return iso


def process_fold(panel, fold):
    """Return per-(asset,row) calibrated arrays + diagnostics for one fold, causally."""
    day_all = panel["day"]; Y = panel["Y"]; CL = panel["CL"]
    te = fold["te_rows"]; rs = fold["resid_sigma"]
    p = fold["pred"][te]            # (R,14) normalized residual units
    y = Y[te]                       # (R,14) raw return
    cl = CL[te]
    days = day_all[te]             # (R,)
    R, A = p.shape

    valid = np.isfinite(p) & np.isfinite(y) & cl   # (R,14)

    # cross-sectional demean (shared map across assets -> demean both in their native units;
    # pred in normalized resid units, realized target in normalized resid units = y / resid_sigma)
    y_norm = y / rs[None, :]                        # realized in normalized residual units
    pred_d = xsec_demean(p, valid)                  # demeaned normalized pred (input z)
    realn_d = xsec_demean(y_norm, valid)            # demeaned normalized realized (target)

    # ---- BEFORE metrics (raw demeaned pred, return space) ----
    pred_ret_d = pred_d * rs[None, :]               # return-space demeaned pred
    realret_d = xsec_demean(y, valid)               # return-space demeaned realized
    vflat = valid.ravel()
    sp_before = np.nanstd(pred_ret_d.ravel()[vflat])
    sy = np.nanstd(realret_d.ravel()[vflat])
    sig_ratio_before = sp_before / sy
    mono_before = decile_mono(pred_ret_d.ravel()[vflat], realret_d.ravel()[vflat])
    ric_before, nric = row_rank_ic(pred_d, realn_d, valid)

    # ---- CAUSAL forward-chaining isotonic over test days ----
    udays = np.sort(np.unique(days))
    cal_norm_d = np.full((R, A), np.nan)            # calibrated demeaned (normalized resid units)
    warmup_flag = np.zeros(R, dtype=bool)

    # warmup: fit on the warmup days themselves (only days w/o prior history) - flagged
    warm_days = udays[:WARMUP_DAYS]
    warm_mask_rows = np.isin(days, warm_days)
    wm = valid & warm_mask_rows[:, None]
    if wm.sum() >= MIN_FIT:
        iso_w = fit_isotonic(pred_d[wm], realn_d[wm])
        cal_norm_d[wm] = iso_w.predict(pred_d[wm])
        warmup_flag[warm_mask_rows] = True
    else:
        # not enough -> identity-on-mean fallback: scale by global beta
        beta = np.nansum(pred_d[wm] * realn_d[wm]) / max(np.nansum(pred_d[wm] ** 2), 1e-12)
        cal_norm_d[wm] = pred_d[wm] * beta
        warmup_flag[warm_mask_rows] = True

    # expanding window for the rest
    for k in range(WARMUP_DAYS, len(udays)):
        dk = udays[k]
        hist_days = udays[:k]                       # strictly earlier
        hist_rows = np.isin(days, hist_days)
        hist_mask = valid & hist_rows[:, None]
        cur_rows = (days == dk)
        cur_mask = valid & cur_rows[:, None]
        if cur_mask.sum() == 0:
            continue
        if hist_mask.sum() >= MIN_FIT:
            iso = fit_isotonic(pred_d[hist_mask], realn_d[hist_mask])
            cal_norm_d[cur_mask] = iso.predict(pred_d[cur_mask])
        else:
            # shouldn't happen given WARMUP_DAYS, but safe fallback
            beta = np.nansum(pred_d[hist_mask] * realn_d[hist_mask]) / max(np.nansum(pred_d[hist_mask] ** 2), 1e-12)
            cal_norm_d[cur_mask] = pred_d[cur_mask] * beta
            warmup_flag[cur_rows] = True

    # ---- AFTER metrics ----
    cal_ret_d = cal_norm_d * rs[None, :]            # return-space calibrated demeaned
    valid_cal = valid & np.isfinite(cal_norm_d)
    vcflat = valid_cal.ravel()
    sp_after = np.nanstd(cal_ret_d.ravel()[vcflat])
    sig_ratio_after = sp_after / sy
    mono_after = decile_mono(cal_ret_d.ravel()[vcflat], realret_d.ravel()[vcflat])
    ric_after, _ = row_rank_ic(cal_norm_d, realn_d, valid_cal)

    # ---- Task 3: tail probabilities from calibrated point + empirical residual dist ----
    # residual = realized_norm_demeaned - calibrated_norm_demeaned ; build empirical resid std
    resid = realn_d - cal_norm_d
    resid_v = resid.ravel()[vcflat]
    resid_std = np.nanstd(resid_v)                  # normalized-resid-units spread of calibration error
    # Per asset-timestamp: P(realized > +1sigma_asset) where sigma_asset is in NORMALIZED units = 1
    # (y_norm already standardized by resid_sigma). Use threshold = +/-1 in normalized realized units.
    # predicted tail prob from Normal(cal_norm_d, resid_std):
    from math import erf, sqrt
    def norm_sf(z):  # P(X> z) for standard normal cdf complement
        return 0.5 * (1.0 - erf(z / sqrt(2.0)))
    thr = 1.0  # +/-1 normalized-residual-unit (i.e. 1 per-asset resid sigma) on the demeaned realized
    z_up = (thr - cal_norm_d) / max(resid_std, 1e-9)
    z_dn = (-thr - cal_norm_d) / max(resid_std, 1e-9)
    sf = np.vectorize(norm_sf)
    tail_up = sf(z_up)                              # P(resid_realized > +1)
    tail_dn = 1.0 - sf(z_dn)                        # P(resid_realized < -1)
    # reliability / Brier on the UP tail (exclude warmup region for honesty)
    keep = valid_cal & (~warmup_flag[:, None])
    kflat = keep.ravel()
    realized_up = (realn_d.ravel()[kflat] > thr).astype(float)
    pred_up = tail_up.ravel()[kflat]
    brier_up = float(np.mean((pred_up - realized_up) ** 2)) if kflat.sum() else np.nan
    base_rate_up = float(realized_up.mean()) if kflat.sum() else np.nan
    brier_base = float(np.mean((base_rate_up - realized_up) ** 2)) if kflat.sum() else np.nan
    # reliability curve: bin predicted tail prob into deciles, compare to realized freq
    rel_curve = []
    if kflat.sum() > 100:
        order = np.argsort(pred_up); bins = np.array_split(order, N_DECILE)
        for b in bins:
            rel_curve.append([float(pred_up[b].mean()), float(realized_up[b].mean()), int(len(b))])

    # ---- Task 4: conviction sizing ----
    # quality proxy: IC of |calibrated| vs |realized| (per-row, then mean)
    abs_cal = np.abs(cal_norm_d); abs_real = np.abs(realn_d)
    conv_ic, _ = row_rank_ic(abs_cal, abs_real, valid_cal, min_assets=3)
    # book test: long-short book, sizing prop to calibrated value vs equal-weight (sign only)
    # per row build weights, realize pnl = sum(w * realized_return_demeaned)
    eq_pnl = []; sz_pnl = []
    for i in range(R):
        vi = valid_cal[i]
        if vi.sum() < 3:
            continue
        c = cal_norm_d[i, vi]              # calibrated signal (normalized)
        rret = realret_d[i, vi]            # realized return demeaned
        # equal weight: sign(c)/N normalized to gross 1
        s = np.sign(c)
        if np.abs(s).sum() == 0:
            continue
        w_eq = s / np.abs(s).sum()
        # size-weighted: c / sum|c| (conviction sizing)
        if np.abs(c).sum() == 0:
            continue
        w_sz = c / np.abs(c).sum()
        eq_pnl.append(float(np.dot(w_eq, rret)))
        sz_pnl.append(float(np.dot(w_sz, rret)))
    eq_pnl = np.array(eq_pnl); sz_pnl = np.array(sz_pnl)
    def sharpe(x):
        return float(x.mean() / (x.std() + 1e-12) * np.sqrt(len(x))) if len(x) else np.nan
    sizing_lift = dict(
        eq_mean=float(eq_pnl.mean()) if len(eq_pnl) else np.nan,
        sz_mean=float(sz_pnl.mean()) if len(sz_pnl) else np.nan,
        eq_sharpe=sharpe(eq_pnl), sz_sharpe=sharpe(sz_pnl),
        n_rows=int(len(eq_pnl)),
    )

    # ---- deliverable per (ts,asset) arrays (return to caller for CSV building) ----
    exp_bps = cal_norm_d * rs[None, :] * 1e4        # expected_residual_bps == calibrated_residual_bps here
    deliverable = dict(
        days=days, valid=valid_cal, warmup=warmup_flag,
        cal_norm_d=cal_norm_d, exp_bps=exp_bps,
        tail_up=tail_up, tail_dn=tail_dn, resid_std=resid_std,
        realn_d=realn_d, ts=panel["ts"][te],
    )

    diag = dict(
        n_valid=int(valid.sum()), n_rows_clean=int((valid.sum(1) >= 2).sum()),
        sig_ratio_before=float(sig_ratio_before), sig_ratio_after=float(sig_ratio_after),
        mono_frac_before=mono_before[0], mono_sp_before=mono_before[1],
        mono_frac_after=mono_after[0], mono_sp_after=mono_after[1],
        rank_ic_before=ric_before, rank_ic_after=ric_after, n_ric_rows=nric,
        rank_ic_delta=float(ric_after - ric_before),
        tail_brier_up=brier_up, tail_brier_base=brier_base, tail_base_rate_up=base_rate_up,
        tail_reliability_curve=rel_curve,
        conviction_ic_abs=conv_ic, sizing=sizing_lift,
        resid_std_norm=float(resid_std),
        warmup_days=WARMUP_DAYS, n_warmup_rows=int(warmup_flag.sum()),
    )
    return diag, deliverable


def main():
    t0 = time.time()
    results = {}
    csv_rows = []
    for h in HORIZONS:
        panel, folds = load_horizon(h)
        results[h] = dict(per_fold=[], horizon=int(folds[0]["horizon"]))
        for f in range(NFOLD):
            diag, deliv = process_fold(panel, folds[f])
            diag["fold"] = f
            results[h]["per_fold"].append(diag)
            print(f"[{h} fold{f}] sig_ratio {diag['sig_ratio_before']:.3f}->{diag['sig_ratio_after']:.3f} "
                  f"mono {diag['mono_frac_before']}->{diag['mono_frac_after']} "
                  f"rankIC {diag['rank_ic_before']:.4f}->{diag['rank_ic_after']:.4f} "
                  f"(d={diag['rank_ic_delta']:+.4f}) Brier {diag['tail_brier_up']:.4f} vs base {diag['tail_brier_base']:.4f} "
                  f"convIC {diag['conviction_ic_abs']:.4f} szSharpe {diag['sizing']['sz_sharpe']:.2f} vs eq {diag['sizing']['eq_sharpe']:.2f}",
                  flush=True)
            # collect CSV sample rows from fold 2 (latest, most production-like), first ~30 valid rows
            if f == 2 and h == "RAW_y600":
                days = deliv["days"]; ts = deliv["ts"]; valid = deliv["valid"]; warm = deliv["warmup"]
                cnt = 0
                for i in range(valid.shape[0]):
                    if warm[i]:
                        continue
                    vi = valid[i]
                    if vi.sum() < 3:
                        continue
                    for a in np.where(vi)[0]:
                        csv_rows.append(dict(
                            horizon=h, fold=f, ts=int(ts[i]), day=int(days[i]),
                            asset=SYMBOLS[a],
                            expected_residual_bps=round(float(deliv["exp_bps"][i, a]), 4),
                            calibrated_residual_bps=round(float(deliv["exp_bps"][i, a]), 4),
                            conviction_width_bps="",  # no quantiles in preds -> not available
                            tail_prob_up=round(float(deliv["tail_up"][i, a]), 5),
                            tail_prob_dn=round(float(deliv["tail_dn"][i, a]), 5),
                            sigma_ratio_postcalib=round(float(results[h]["per_fold"][f]["sig_ratio_after"]), 4),
                            causal_warmup=False,
                        ))
                    cnt += 1
                    if cnt >= 40:
                        break

        # horizon-level averages
        pf = results[h]["per_fold"]
        results[h]["avg"] = dict(
            sig_ratio_before=float(np.mean([d["sig_ratio_before"] for d in pf])),
            sig_ratio_after=float(np.mean([d["sig_ratio_after"] for d in pf])),
            mono_frac_before=float(np.nanmean([d["mono_frac_before"] for d in pf])),
            mono_frac_after=float(np.nanmean([d["mono_frac_after"] for d in pf])),
            rank_ic_before=float(np.mean([d["rank_ic_before"] for d in pf])),
            rank_ic_after=float(np.mean([d["rank_ic_after"] for d in pf])),
            rank_ic_delta=float(np.mean([d["rank_ic_delta"] for d in pf])),
            tail_brier_up=float(np.nanmean([d["tail_brier_up"] for d in pf])),
            tail_brier_base=float(np.nanmean([d["tail_brier_base"] for d in pf])),
            conviction_ic_abs=float(np.nanmean([d["conviction_ic_abs"] for d in pf])),
            sz_sharpe=float(np.nanmean([d["sizing"]["sz_sharpe"] for d in pf])),
            eq_sharpe=float(np.nanmean([d["sizing"]["eq_sharpe"] for d in pf])),
        )

    # write CSV sample
    if csv_rows:
        import csv
        keys = list(csv_rows[0].keys())
        with open(OUT_CSV, "w", newline="") as fh:
            w = csv.DictWriter(fh, fieldnames=keys)
            w.writeheader()
            w.writerows(csv_rows)

    results["_meta"] = dict(
        elapsed_s=round(time.time() - t0, 1),
        causality="forward-chaining expanding-window over fold's test days; calibrated day d_k fit only on days < d_k (same fold); first WARMUP_DAYS days flagged causal_warmup; folds temporally disjoint & ordered",
        units="calibrate in cross-sectionally-demeaned NORMALIZED residual units; bps = cal_norm_demeaned * resid_sigma * 1e4",
        n_csv_sample=len(csv_rows), csv=OUT_CSV,
    )
    with open(OUT_JSON, "w") as fh:
        json.dump(results, fh, indent=2, default=lambda o: None if isinstance(o, float) and not np.isfinite(o) else o)
    print(f"\nDONE in {results['_meta']['elapsed_s']}s -> {OUT_JSON}, sample CSV {OUT_CSV} ({len(csv_rows)} rows)", flush=True)


if __name__ == "__main__":
    main()
