"""D3 Stage-0C decisive CHEAP gate (no GPU): does a new-information family add per-day-CLEAN Pearson
on top of the deployed model prediction, in the drift months 2026-01..05?

For each test month, fit walk-forward Ridge on EXPANDING PRIOR MONTHS ONLY (no test-month fitting):
  base: y_true_ret_bps ~ [y_pred]                 (per-day-CLEAN P reproduces the honest ~0.039 baseline)
  aug : y_true_ret_bps ~ [y_pred, family feats]   (standardized; features joined strictly <=t)
Delta = per-day-CLEAN P(aug) - P(base) on the test month. Report per month, pooled drift (2026-01..05),
strong-month guard (2025-10). Plus three artifact guards:
  (i)  shuffle-future null   -- permute feature DAYS; |Delta| must stay < 0.002
  (ii) trailing-vol control  -- add aux_trail_vol_1h to BOTH base and aug; if Delta collapses => vol proxy
  (iii) family-A short x cascade conditional-IC vs the H5 short-decile x funding structure

KILL GATES (team-lead spec):
  cascade A / basket-ECM B : pooled drift Delta < +0.005  OR any drift month < -0.003  => DEAD
  flow C / settlement D    : pooled drift Delta < +0.003  => DEAD
  shuffle-future |Delta| >= 0.002  OR  pure-vol-proxy  => DEAD regardless

Run LOCAL:
  python multi_asset/eval/ridge_gate_d3.py --families A C B D \
    --cascade exports/d3_cascade_flow_5m.csv --basket exports/d3_basket_ecm_1h.csv
"""
from __future__ import annotations
import numpy as np, pandas as pd, argparse, os
from scipy.stats import pearsonr
from sklearn.linear_model import RidgeCV

MONTHS = ["2025_08","2025_09","2025_10","2025_11","2025_12",
          "2026_01","2026_02","2026_03","2026_04","2026_05"]
DRIFT  = ["2026_01","2026_02","2026_03","2026_04","2026_05"]
STRONG = "2025_10"
HZ_MS  = 600_000
DAY_MS = 86_400_000
ALPHAS = np.logspace(-2, 4, 13)

FAM = {
    "A": ["a_sweep_count","a_run_len_max","a_run_notional_signed","a_impact_per_notional",
          "a_burst_flow_signed","a_size_p99_med","a_size_asym_side",
          "a_casc_net_1h","a_casc_intensity_6h"],
    "C": ["c_flow_ac1_1h","c_vpin_1h","c_netflow_z_6h","c_aggr_ratio_drift","c_flow_price_div_1h"],
    "B": ["b_ecm_residual","b_ecm_resid_z","b_breadth","b_dispersion","b_beta_compression","b_basket_ret_1h"],
    "D": ["d_mins_to_next_funding","d_mins_since_funding","d_is_weekend","d_is_us_session"],
}


# ---------------- per-day-CLEAN caliber (matches final_deliverable_l01.py) ----------------
def clean_idx(ts):
    o = np.argsort(ts); keep = []; last = -1e18
    for i in o:
        if ts[i] - last >= HZ_MS:
            keep.append(i); last = ts[i]
    return np.array(keep, dtype=int)


def perday_clean_P(pred, y, ts):
    """Mean over UTC days of within-day Pearson(pred,y) on greedy >=600s non-overlap rows."""
    dk = ts // DAY_MS; rs = []
    for d in np.unique(dk):
        m = np.where(dk == d)[0]
        k = clean_idx(ts[m])
        if len(k) > 20:
            pk = pred[m][k]; yk = y[m][k]
            if pk.std() > 1e-12 and yk.std() > 1e-12:
                r = pearsonr(pk, yk)[0]
                if np.isfinite(r):
                    rs.append(r)
    return np.mean(rs) if rs else np.nan


# ---------------- joins (strict <=t) ----------------
def join_le_t(close_arr, feat_vals, ts):
    """For each ts, take the last feature row with close <= ts (strict causality). NaN if none."""
    idx = np.searchsorted(close_arr, ts, side="right") - 1
    ok = idx >= 0
    out = np.full((len(ts), feat_vals.shape[1]), np.nan)
    out[ok] = feat_vals[idx[ok]]
    return out


def calendar_feats(ts_ms):
    """Family D: funding-settlement proximity (00/08/16 UTC) + weekend/US-session dummies."""
    sec = ts_ms // 1000
    tod = sec % 86400
    settle = np.array([0, 8, 16, 24]) * 3600
    to_next = np.min((settle[None, :] - tod[:, None]) % 86400, axis=1) / 60.0  # minutes to next
    since = np.min((tod[:, None] - settle[None, :]) % 86400, axis=1) / 60.0
    dow = (sec // 86400 + 3) % 7  # Monday=0 (1970-01-01 = Thursday = 3)
    is_weekend = ((dow == 5) | (dow == 6)).astype(float)  # Sat, Sun
    hod = tod / 3600.0
    is_us = ((hod >= 13) & (hod < 21)).astype(float)
    return np.column_stack([to_next, since, is_weekend, is_us])


# ---------------- walk-forward Ridge gate ----------------
def _fit_predict(Xtr, ytr, Xte):
    mu = np.nanmedian(Xtr, axis=0)
    Xtr = np.where(np.isnan(Xtr), mu, Xtr); Xte = np.where(np.isnan(Xte), mu, Xte)
    m = Xtr.mean(0); s = Xtr.std(0); s[s < 1e-12] = 1.0
    Xtr = (Xtr - m) / s; Xte = (Xte - m) / s
    r = RidgeCV(alphas=ALPHAS).fit(Xtr, ytr)
    return r.predict(Xte)


def walk_forward(months_arr, y, ypred, ts, feat_mat, base_extra=None):
    """Returns per-month dict of (baseP, augP, delta). base=[ypred(,extra)], aug=base+feat_mat."""
    res = {}
    for i, mk in enumerate(MONTHS):
        if i == 0:
            continue
        tr = np.isin(months_arr, MONTHS[:i]); te = months_arr == mk
        if te.sum() < 100 or tr.sum() < 500:
            continue
        base_cols = [ypred[:, None]] + ([base_extra] if base_extra is not None else [])
        Xb = np.hstack(base_cols)
        Xa = np.hstack(base_cols + [feat_mat])
        pb = _fit_predict(Xb[tr], y[tr], Xb[te])
        pa = _fit_predict(Xa[tr], y[tr], Xa[te])
        bP = perday_clean_P(pb, y[te], ts[te])
        aP = perday_clean_P(pa, y[te], ts[te])
        res[mk] = (bP, aP, aP - bP)
    return res


def _pooled(res, keys):
    d = [res[k][2] for k in keys if k in res and np.isfinite(res[k][2])]
    b = [res[k][0] for k in keys if k in res and np.isfinite(res[k][0])]
    a = [res[k][1] for k in keys if k in res and np.isfinite(res[k][1])]
    return (np.mean(b) if b else np.nan, np.mean(a) if a else np.nan, np.mean(d) if d else np.nan)


def _fp(cols, tr, te, y):
    X = np.column_stack(cols); mu = np.nanmedian(X[tr], 0); X = np.where(np.isnan(X), mu, X)
    m = X[tr].mean(0); s = X[tr].std(0); s[s < 1e-12] = 1.0
    Xs = (X - m) / s
    return RidgeCV(alphas=ALPHAS).fit(Xs[tr], y[tr]).predict(Xs[te])


def transfer_diagnostic(months_arr, y, ypred, ts, join_ecm, join_cn):
    """Why the strongest orthogonal features (cascade-net + ECM-z) fail the pre-registered gate:
    in-sample (test-fitted ORACLE) signal exists, but it is NON-TRANSFERABLE out-of-sample.
    Compares: oracle in-sample; expanding-prior (pre-registered gate); leave-one-drift-month-out;
    with drop-one-month concentration + shuffle-future null on the LOO estimator."""
    print("\n" + "=" * 96)
    print("TRANSFER DIAGNOSTIC  (features = [cascade a_casc_net_1h, basket b_ecm_resid_z])")
    print("=" * 96)
    dm = np.isin(months_arr, DRIFT)
    ecm = join_ecm(ts); cn = join_cn(ts)

    def pooled_over(sel_train, drop=None):
        dset = [d for d in DRIFT if d != drop]; bP = []; aP = []
        for mk in dset:
            te = months_arr == mk; tr = sel_train(mk, dset)
            if tr.sum() < 500: continue
            bP.append(perday_clean_P(_fp([ypred], tr, te, y), y[te], ts[te]))
            aP.append(perday_clean_P(_fp([ypred, ecm, cn], tr, te, y), y[te], ts[te]))
        return np.mean(bP), np.mean(aP), np.mean(aP) - np.mean(bP)

    # oracle (test-month IN-SAMPLE = ceiling, peek)
    pb = _fp([ypred], dm, dm, y); pa = _fp([ypred, ecm, cn], dm, dm, y)
    obase = np.mean([perday_clean_P(pb[months_arr[dm] == m], y[dm][months_arr[dm] == m], ts[dm][months_arr[dm] == m]) for m in DRIFT])
    oaug  = np.mean([perday_clean_P(pa[months_arr[dm] == m], y[dm][months_arr[dm] == m], ts[dm][months_arr[dm] == m]) for m in DRIFT])
    print(f"  oracle in-sample (test-fitted, CEILING):        baseP={obase:+.4f} augP={oaug:+.4f} Delta={oaug-obase:+.4f}")
    exp = pooled_over(lambda mk, ds: np.isin(months_arr, MONTHS[:MONTHS.index(mk)]))
    print(f"  expanding-prior (PRE-REGISTERED GATE):          baseP={exp[0]:+.4f} augP={exp[1]:+.4f} Delta={exp[2]:+.4f}")
    loo = pooled_over(lambda mk, ds: np.isin(months_arr, [d for d in ds if d != mk]))
    print(f"  leave-one-drift-month-out (drift-only train):   baseP={loo[0]:+.4f} augP={loo[1]:+.4f} Delta={loo[2]:+.4f}")
    loo_d = pooled_over(lambda mk, ds: np.isin(months_arr, [d for d in ds if d != mk]), drop="2026_03")
    print(f"  LOO drop-2026_03 (concentration test):          Delta={loo_d[2]:+.4f}  (LOO lift is single-month if this ~0)")
    # shuffle-future null on the LOO estimator
    rng = np.random.default_rng(0); dates = np.unique(ts // DAY_MS); nd = []
    for _ in range(6):
        perm = rng.permutation(dates); dmap = dict(zip(dates, perm))
        tn = ts + (np.array([dmap[d] for d in (ts // DAY_MS)]) - (ts // DAY_MS)) * DAY_MS
        en = join_ecm(tn); cnn = join_cn(tn)
        bP = []; aP = []
        for mk in DRIFT:
            te = months_arr == mk; tr = np.isin(months_arr, [d for d in DRIFT if d != mk])
            bP.append(perday_clean_P(_fp([ypred], tr, te, y), y[te], ts[te]))
            aP.append(perday_clean_P(_fp([ypred, en, cnn], tr, te, y), y[te], ts[te]))
        nd.append(np.mean(aP) - np.mean(bP))
    nd = np.array(nd)
    print(f"  LOO shuffle-future null: mean={np.nanmean(nd):+.4f} max|Delta|={np.nanmax(np.abs(nd)):.4f}  (LOO estimator noise floor)")
    print("  READ: oracle>0 but expanding~0 AND LOO-lift single-month-driven AND < shuffle floor => in-sample-only, NON-TRANSFERABLE.")


# ---------------- short x cascade / funding conditional (family A) ----------------
def load_funding_le_t(ts_ms):
    f = pd.read_csv("data/funding/btcusdt_funding.csv", usecols=["fundingTime_ms", "fundingRate"])
    ft = f["fundingTime_ms"].values.astype(np.int64); fr = f["fundingRate"].values.astype(float)
    o = np.argsort(ft); ft = ft[o]; fr = fr[o]
    idx = np.searchsorted(ft, ts_ms, side="right") - 1
    out = np.where(idx >= 0, fr[np.clip(idx, 0, len(fr) - 1)], np.nan)
    return out


def _day_clustered_t(day, val_a, val_b, group):
    """Day-clustered t of (mean over top group - mean over bottom group), computed per UTC day."""
    df = pd.DataFrame({"day": day, "y": val_a, "g": group})
    hi = df[df.g == 2].groupby("day")["y"].mean()
    lo = df[df.g == 0].groupby("day")["y"].mean()
    j = pd.concat([hi.rename("hi"), lo.rename("lo")], axis=1).dropna()
    sp = (j["hi"] - j["lo"]).values
    if len(sp) < 5:
        return np.nan, len(sp), np.nan
    return sp.mean() / (sp.std(ddof=1) / np.sqrt(len(sp))), len(sp), sp.mean()


def short_conditional(ts, y, ypred_dem, casc_net, fund, drift_mask):
    """Among per-day bottom-decile |pred| SHORT rows on drift months: does cascade-net tercile move
    realized y (day-clustered), and does it increment over the H5 funding-tercile structure?"""
    m = drift_mask & np.isfinite(casc_net) & np.isfinite(fund)
    ts_, y_, p_, c_, f_ = ts[m], y[m], ypred_dem[m], casc_net[m], fund[m]
    day = ts_ // DAY_MS
    # short rows = per-day bottom decile of predicted return (most-negative preds)
    short = np.zeros(len(p_), bool)
    for d in np.unique(day):
        di = np.where(day == d)[0]
        if len(di) < 20: continue
        thr = np.quantile(p_[di], 0.10)
        short[di[p_[di] <= thr]] = True
    s = np.where(short)[0]
    if len(s) < 200:
        return {"n_short": len(s)}
    def terc(x):
        q = np.quantile(x, [1/3, 2/3]); return np.digitize(x, q)
    cg = terc(c_[s]); fg = terc(f_[s])
    t_casc, nd_c, sp_c = _day_clustered_t(day[s], y_[s], None, cg)
    t_fund, nd_f, sp_f = _day_clustered_t(day[s], y_[s], None, fg)
    # increment over funding: cascade tercile spread within the middle funding tercile only
    midf = fg == 1
    if midf.sum() > 100:
        t_casc_gf, nd_gf, sp_gf = _day_clustered_t(day[s][midf], y_[s][midf], None, cg[midf])
    else:
        t_casc_gf, nd_gf, sp_gf = np.nan, 0, np.nan
    return {"n_short": len(s), "t_casc": t_casc, "spread_casc_bps": sp_c,
            "t_fund": t_fund, "spread_fund_bps": sp_f,
            "t_casc_given_fund": t_casc_gf, "spread_casc_gf_bps": sp_gf}


# ---------------- main ----------------
def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--backtest", default="exports/final_l01/y600_backtest_dataset.csv")
    ap.add_argument("--cascade", default="exports/d3_cascade_flow_5m.csv")
    ap.add_argument("--basket", default="exports/d3_basket_ecm_1h.csv")
    ap.add_argument("--families", nargs="+", default=["A", "C", "B", "D"])
    ap.add_argument("--n-shuf", type=int, default=5)
    a = ap.parse_args()

    df = pd.read_csv(a.backtest)
    df = df[df.y_true_ret_bps != 0].reset_index(drop=True)   # drop mask / y_true==0 rows
    ts = df.timestamp_ms.values.astype(np.int64)
    y = df.y_true_ret_bps.values.astype(float)
    ypred = df.y_pred_raw.values.astype(float)
    ypred_dem = df.y_pred_demeaned.values.astype(float)
    months_arr = df.month.values
    print(f"loaded {len(df)} rows (mask/y==0 dropped), months {sorted(set(months_arr))}")

    # cascade/flow features (families A, C) + vol control
    casc = pd.read_csv(a.cascade).sort_values("bar_close_ms")
    cc = casc.bar_close_ms.values.astype(np.int64)
    def cascade_join(ts_arr, cols):
        return join_le_t(cc, casc[cols].values.astype(float), ts_arr)
    vol_ctrl = cascade_join(ts, ["aux_trail_vol_1h"])
    casc_net = cascade_join(ts, ["a_casc_net_1h"])[:, 0]

    # basket (family B)
    have_B = os.path.exists(a.basket)
    if have_B:
        bkt = pd.read_csv(a.basket).sort_values("close_time_ms")
        bc = bkt.close_time_ms.values.astype(np.int64)

    def build_feat(fam, ts_arr):
        if fam in ("A", "C"):
            return cascade_join(ts_arr, FAM[fam])
        if fam == "B":
            return join_le_t(bc, bkt[FAM["B"]].values.astype(float), ts_arr)
        if fam == "D":
            return calendar_feats(ts_arr)

    print("\n" + "=" * 96)
    print("RIDGE GATE  (per-day-CLEAN P; base=y~ypred, aug=y~[ypred,feats]; expanding-prior walk-forward)")
    print("=" * 96)
    verdicts = {}
    for fam in a.families:
        if fam == "B" and not have_B:
            print(f"\n### FAMILY {fam}: basket file {a.basket} MISSING -- skipped"); continue
        kill_thr = 0.005 if fam in ("A", "B") else 0.003
        feat = build_feat(fam, ts)
        res = walk_forward(months_arr, y, ypred, ts, feat)
        res_vc = walk_forward(months_arr, y, ypred, ts, feat, base_extra=vol_ctrl)

        print(f"\n### FAMILY {fam}  ({len(FAM[fam])} feats: {', '.join(FAM[fam])})")
        print(f"  {'month':8s} {'baseP':>8s} {'augP':>8s} {'Delta':>8s} {'Delta|volctrl':>14s}")
        for mk in MONTHS[1:]:
            if mk not in res: continue
            dvc = res_vc.get(mk, (np.nan, np.nan, np.nan))[2]
            tag = "  <STRONG" if mk == STRONG else ("  <drift" if mk in DRIFT else "")
            print(f"  {mk:8s} {res[mk][0]:+8.4f} {res[mk][1]:+8.4f} {res[mk][2]:+8.4f} {dvc:+14.4f}{tag}")
        b_d, a_d, dd = _pooled(res, DRIFT)
        _, _, dd_vc = _pooled(res_vc, DRIFT)
        sg = res.get(STRONG, (np.nan, np.nan, np.nan))
        worst_drift = min((res[k][2] for k in DRIFT if k in res), default=np.nan)
        print(f"  POOLED DRIFT  baseP={b_d:+.4f} augP={a_d:+.4f}  Delta={dd:+.4f}  (vol-ctrl Delta={dd_vc:+.4f})")
        print(f"  STRONG {STRONG} Delta={sg[2]:+.4f} (guard: must not drop >0.003)  | worst drift month Delta={worst_drift:+.4f}")

        # shuffle-future null (permute feature days)
        rng = np.random.default_rng(0); null_deltas = []
        dates = np.unique(ts // DAY_MS)
        for _ in range(a.n_shuf):
            perm = rng.permutation(dates)
            dmap = dict(zip(dates, perm))
            ts_null = ts + (np.array([dmap[d] for d in (ts // DAY_MS)]) - (ts // DAY_MS)) * DAY_MS
            feat_null = build_feat(fam, ts_null)
            rn = walk_forward(months_arr, y, ypred, ts, feat_null)
            null_deltas.append(_pooled(rn, DRIFT)[2])
        null_deltas = np.array(null_deltas)
        max_abs_null = np.nanmax(np.abs(null_deltas))
        print(f"  shuffle-future null pooled-drift Delta: mean={np.nanmean(null_deltas):+.4f} "
              f"max|Delta|={max_abs_null:.4f} (must be <0.002)")

        # verdict
        vol_proxy = np.isfinite(dd) and np.isfinite(dd_vc) and dd > 0 and (dd_vc < 0.5 * dd - 1e-9)
        dead = (not np.isfinite(dd)) or (dd < kill_thr) or (np.isfinite(worst_drift) and worst_drift < -0.003) \
               or (max_abs_null >= 0.002) or vol_proxy
        reasons = []
        if not np.isfinite(dd) or dd < kill_thr: reasons.append(f"pooled Delta {dd:+.4f} < {kill_thr}")
        if np.isfinite(worst_drift) and worst_drift < -0.003: reasons.append(f"drift month {worst_drift:+.4f} < -0.003")
        if max_abs_null >= 0.002: reasons.append(f"shuffle |Delta| {max_abs_null:.4f} >= 0.002")
        if vol_proxy: reasons.append(f"vol proxy (Delta {dd:+.4f} -> {dd_vc:+.4f} under vol control)")
        verdicts[fam] = ("DEAD" if dead else "SURVIVES", dd, reasons)
        print(f"  >>> FAMILY {fam} VERDICT: {'DEAD' if dead else 'SURVIVES'}"
              + (f"  [{'; '.join(reasons)}]" if reasons else "  [passes all gates]"))

        if fam == "A":
            fund = load_funding_le_t(ts)
            drift_mask = np.isin(months_arr, DRIFT)
            sc = short_conditional(ts, y, ypred_dem, casc_net, fund, drift_mask)
            print(f"  short x cascade conditional (drift, per-day bottom-decile pred shorts, n={sc.get('n_short')}):")
            if "t_casc" in sc:
                print(f"    cascade-net tercile spread on shorts: {sc['spread_casc_bps']:+.2f}bps  day-clustered t={sc['t_casc']:+.2f}")
                print(f"    funding tercile spread on shorts     : {sc['spread_fund_bps']:+.2f}bps  day-clustered t={sc['t_fund']:+.2f} (H5: ~-3.59, t=-2.43)")
                print(f"    cascade | mid-funding tercile        : {sc['spread_casc_gf_bps']:+.2f}bps  day-clustered t={sc['t_casc_given_fund']:+.2f}")
                a_specific_dead = (abs(sc['t_casc']) < 2.4) and (abs(sc.get('t_casc_given_fund', 0) or 0) < 2.0)
                print(f"    family-A conditional: {'FAILS (|t|<2.4 and no increment over funding)' if a_specific_dead else 'has structure'}")

    if have_B and "A" in a.families:
        transfer_diagnostic(months_arr, y, ypred, ts,
                            join_ecm=lambda t: join_le_t(bc, bkt[["b_ecm_resid_z"]].values.astype(float), t)[:, 0],
                            join_cn=lambda t: join_le_t(cc, casc[["a_casc_net_1h"]].values.astype(float), t)[:, 0])

    print("\n" + "=" * 96)
    print("SUMMARY")
    for fam in a.families:
        if fam in verdicts:
            v = verdicts[fam]
            print(f"  {fam}: {v[0]:9s} pooled-drift Delta={v[1]:+.4f}" + (f"  ({'; '.join(v[2])})" if v[2] else ""))
    print("DONE_RIDGE_GATE_D3.")


if __name__ == "__main__":
    main()
