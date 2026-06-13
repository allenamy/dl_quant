"""GBDT cross-sectional CEILING PROBE on OUR 44-feature multi-asset y600 data.

Question this settles: is our DL plateau (~0.049 cs-rank-IC) an INFORMATION
ceiling (GBDT ~= DL on the same snapshot inputs => our 44 features carry no
nonlinear headroom the DL is missing) or does DL leave snapshot signal on the
table (GBDT BEATS DL) or does temporal/cross-asset depth genuinely add over the
snapshot (GBDT FALLS BELOW DL => the escape hatch is real)?

FAITHFUL PORT of collaborator's gbdt_cs_alpha.py methodology applied to OUR data:
  - causal walk-forward, 1-day embargo, test stride = horizon (non-overlap clean600)
  - per-snapshot cross-sectional Spearman eval over the 14 assets (>=5 valid)
  - cross-sectionally-DEMEANED target (our residual caliber) -- T0: equal-demean
    then per-asset MAD-sigma normalize then clip +/-5 (EXACTLY the caliber our
    0.049 DL plateau is measured in -- see train_temporal_spatial residual loss)
  - features: csfeat = [raw 44 | per-snapshot cross-sectional-z 44] = 88-dim
    (matches their [raw|cs-z] concat); plus a 44-raw-only variant

REUSES target_study.py's exact loaders (load_panel / xsec_zscore / xsec_spearman /
fold_day_lists / mad_sigma / ridge_*) so feature loading + fold layout + eval are
bit-identical to our ridge baseline and the DL trainer's fold layout.

Models on IDENTICAL rows / target / eval:
  (a) ridge            -- reproduce our ~0.0445 linear ceiling (sanity anchor)
  (b) GBDT regression_l2
  (c) GBDT lambdarank  (per-snapshot groups)

CPU-only. Falls back to sklearn HistGradientBoostingRegressor if lightgbm absent
(states so in JSON). Writes /tmp/gbdt_probe.json.
"""
from __future__ import annotations

import json
import sys
import time

import numpy as np

sys.path.insert(0, "/tmp")
import target_study as T  # noqa: E402  -- reuse exact loaders/eval

# ---- GBDT regularization: anti-overfit for R^2 < 1% (match collaborator) ----
GBDT_PARAMS = dict(
    objective="regression_l2",
    num_leaves=15,
    min_child_samples=2000,
    feature_fraction=0.5,
    bagging_fraction=0.7,
    bagging_freq=1,
    lambda_l2=5.0,
    learning_rate=0.03,
    num_iterations=300,
    max_depth=-1,
    verbosity=-1,
    seed=0,
    num_threads=0,
)
RANK_PARAMS = dict(GBDT_PARAMS)
RANK_PARAMS.update(objective="lambdarank", metric="ndcg",
                   label_gain=list(range(64)))   # large gain table for group sizes
N_RANK_BINS = 32   # discretize residual target -> graded relevance for lambdarank
CLIP = 5.0


def try_import_lgb():
    try:
        import lightgbm as lgb  # noqa: F401
        return lgb, lgb.__version__, "lightgbm"
    except Exception:
        return None, None, None


def build_residual_target(Y, m_eq, trm_rows, clip=CLIP):
    """T0 caliber: equal cross-sectional demean -> per-asset MAD-sigma (TRAIN
    rows only) -> clip +/-5. EXACTLY target_study.build_target('T0', ...)."""
    e = Y - m_eq[:, None]
    sig = T.mad_sigma(e, trm_rows)                       # train-only MAD per asset
    with np.errstate(all="ignore"):
        r = e / sig[None, :]
    r = np.clip(r, -clip, clip)
    r[:, ~np.isfinite(sig)] = np.nan
    return r, sig


def flatten_with_groups(feat, r, day, rows):
    """Pool (ts,asset) train samples with finite features+target. Also return
    per-snapshot group sizes (consecutive same-ts rows) for lambdarank."""
    F = feat.shape[-1]
    xs, ys, grp = [], [], []
    for i in rows:
        blk = feat[i]                                    # (S,F)
        rv = r[i]                                        # (S,)
        ok = np.isfinite(blk).all(-1) & np.isfinite(rv)
        n = int(ok.sum())
        if n < 2:
            continue
        xs.append(blk[ok])
        ys.append(rv[ok])
        grp.append(n)
    if not xs:
        return (np.zeros((0, F), np.float32), np.zeros((0,), np.float64),
                np.zeros((0,), np.int32))
    return (np.concatenate(xs).astype(np.float32),
            np.concatenate(ys).astype(np.float64),
            np.array(grp, np.int32))


def rank_labels(y, groups):
    """Per-group quantile-bin the (continuous) residual into 0..N_RANK_BINS-1
    graded relevance (lambdarank needs nonneg integer labels)."""
    out = np.zeros(len(y), np.int32)
    off = 0
    for g in groups:
        seg = y[off:off + g]
        nb = min(N_RANK_BINS, g)                          # can't have more bins than rows
        # rank within group -> scaled to 0..nb-1
        order = np.argsort(np.argsort(seg))
        out[off:off + g] = (order * nb // g).astype(np.int32)
        off += g
    return out


def predict_panel(model, feat, rows, kind, lgb):
    """Predict per (ts,asset); return pred array shaped like Y with nan where
    features invalid. Ridge uses closed-form w,b0; GBDT uses model.predict."""
    nT, nS, F = feat.shape
    pred = np.full((nT, nS), np.nan)
    for i in rows:
        blk = feat[i]
        ok = np.isfinite(blk).all(-1)
        if ok.sum() < 5:
            continue
        Xq = blk[ok]
        if kind == "ridge":
            w, b0 = model
            pv = Xq @ w + b0
        else:
            pv = model.predict(Xq)
        pred[i, np.where(ok)[0]] = pv
    return pred


def run_model(kind, feat, Y, m_eq, day, uniq, vmask_clean, lgb):
    """Train per fold on stride-180 train rows, eval per fold on clean600 test
    rows (stride>=600 non-overlap) with cross-sectional Spearman vs RAW y."""
    all_ics, per_fold = [], []
    for fold in T.FOLDS:
        trd, vad, ted = T.fold_day_lists(uniq, fold)
        # collaborator trains on train+val (no early-stop here -> fixed rounds);
        # keep val days IN train to maximize signal, matches their fixed-param GBDT.
        trva_days = np.concatenate([trd, vad])
        trm = np.isin(day, trva_days)
        tem = np.isin(day, ted)
        trm_rows = np.where(trm)[0]
        te_rows = np.where(tem)[0]
        # residual target built with TRAIN-only MAD sigma (causal)
        r, _sig = build_residual_target(Y, m_eq, trm)
        Xf, yf, grp = flatten_with_groups(feat, r, day, trm_rows)
        if len(Xf) < 1000:
            per_fold.append(None)
            continue

        if kind == "ridge":
            G, b, xm, ym = T.ridge_fit_gram(Xf, yf)
            w, b0 = T.ridge_solve(G, b, xm, ym, 10.0)   # alpha=10 (xsec_ridge.py)
            model = (w, b0)
        elif kind == "gbdt_reg":
            ds = lgb.Dataset(Xf, label=yf, free_raw_data=False)
            model = lgb.train(GBDT_PARAMS, ds, num_boost_round=GBDT_PARAMS["num_iterations"])
        elif kind == "gbdt_rank":
            rl = rank_labels(yf, grp)
            ds = lgb.Dataset(Xf, label=rl, group=grp, free_raw_data=False)
            model = lgb.train(RANK_PARAMS, ds, num_boost_round=RANK_PARAMS["num_iterations"])
        else:
            raise ValueError(kind)

        pred = predict_panel(model, feat, te_rows, kind, lgb)
        ics = T.xsec_spearman(pred, Y, vmask_clean, te_rows)
        all_ics.append(ics)
        per_fold.append(round(float(ics.mean()), 4) if len(ics) else None)

    cat = np.concatenate(all_ics) if all_ics else np.array([])
    pooled = float(cat.mean()) if len(cat) else float("nan")
    ir = (float(cat.mean() / cat.std() * np.sqrt(len(cat)))
          if len(cat) and cat.std() > 0 else None)
    return dict(pooled_rank_ic=round(pooled, 4),
                per_fold=per_fold,
                ir=round(ir, 2) if ir is not None else None,
                n_ts=int(len(cat)))


def main():
    t0 = time.time()
    lgb, lgb_ver, backend = try_import_lgb()
    print(f"GBDT backend: {backend} ({lgb_ver})" if lgb else
          "lightgbm UNAVAILABLE -> sklearn fallback", flush=True)

    ts, day, X, Y_all, CL_all, capw = T.load_panel()
    Y = Y_all["y600"]
    CL = CL_all["y600"]
    uniq = np.unique(day)
    nT, nS, F = X.shape
    print(f"panel nT={nT} nS={nS} F={F} days={len(uniq)}", flush=True)
    assert F == 44, f"expected 44 hand features, got {F}"

    # cross-sectional z of features (per-snapshot, >=5 valid) -- target_study path
    Xz, vx = T.xsec_zscore(X)                            # Xz nan where invalid
    # raw features: keep nan where the SAME validity mask is False (so both
    # variants train/eval on identical rows -> apples-to-apples)
    Xraw = X.astype(np.float32).copy()
    Xraw[~vx] = np.nan

    # 88-dim [raw | cs-z]; nan where either invalid (== vx)
    feat88 = np.concatenate([Xraw, Xz], axis=-1).astype(np.float32)   # (T,S,88)
    feat44 = Xraw                                                     # (T,S,44)

    m_eq, _m_cw = T.market_means(Y, capw)

    # eval validity: clean600 test rows with finite raw-y and >=5 valid-feature
    # assets -- matches target_study vmask_clean (vx & finite(Y) & CL)
    vmask_clean = vx & np.isfinite(Y) & CL

    if lgb is None:
        # sklearn fallback: HistGradientBoostingRegressor for reg; no native rank
        from sklearn.ensemble import HistGradientBoostingRegressor

        class _SkWrap:
            def __init__(self, m):
                self.m = m
            def predict(self, X):
                return self.m.predict(np.nan_to_num(X))

        def _sk_train(params, ds, num_boost_round):
            m = HistGradientBoostingRegressor(
                max_iter=300, learning_rate=0.03, max_leaf_nodes=15,
                min_samples_leaf=2000, l2_regularization=5.0,
                max_features=0.5, random_state=0)
            m.fit(ds._X, ds._y)
            return _SkWrap(m)

        class _SkDS:
            def __init__(self, X, label=None, group=None, free_raw_data=False):
                self._X = np.nan_to_num(X)
                self._y = label

        class _LgbShim:
            Dataset = _SkDS
            train = staticmethod(_sk_train)
        lgb = _LgbShim()
        SK_FALLBACK = True
    else:
        SK_FALLBACK = False

    variants = {"feat88_raw+csz": feat88, "feat44_raw": feat44}
    models = ["ridge", "gbdt_reg"]
    if not SK_FALLBACK:
        models.append("gbdt_rank")

    out = {
        "meta": dict(
            backend=("sklearn_HistGBR_fallback" if SK_FALLBACK else backend),
            backend_version=lgb_ver,
            target_caliber="T0 equal-demean / per-asset train-MAD-sigma / clip+-5"
                           " (matches DL 0.049 residual plateau caliber)",
            eval="per-snapshot cross-sectional Spearman vs RAW y, clean600 test"
                 " (stride>=600 non-overlap), >=5 valid assets, pooled+per-fold",
            train_stride=180, test_stride="clean600 (>=600s non-overlap)",
            folds=str(T.FOLDS), embargo=T.EMBARGO, val_days=T.VAL_DAYS,
            gbdt_params=GBDT_PARAMS, n_rank_bins=N_RANK_BINS,
            dl_plateau_ref=0.049, linear_ceiling_ref=0.0445,
            n_features=int(F), n_assets=int(nS), n_days=int(len(uniq)),
        ),
        "results": {},
    }

    for vname, feat in variants.items():
        out["results"][vname] = {}
        for kind in models:
            tt = time.time()
            res = run_model(kind, feat, Y, m_eq, day, uniq, vmask_clean, lgb)
            res["sec"] = round(time.time() - tt, 1)
            out["results"][vname][kind] = res
            print(f"[{vname}] {kind:10s} pooled={res['pooled_rank_ic']:+.4f} "
                  f"per-fold={res['per_fold']} ir={res['ir']} "
                  f"n_ts={res['n_ts']} ({res['sec']}s)", flush=True)

    # verdict vs DL plateau
    dl = 0.049
    best_gbdt = max(
        (out["results"][v][k]["pooled_rank_ic"]
         for v in variants for k in models if k != "ridge"
         and np.isfinite(out["results"][v][k]["pooled_rank_ic"])),
        default=float("nan"))
    delta = best_gbdt - dl
    if not np.isfinite(best_gbdt):
        verdict = "INCONCLUSIVE (no finite GBDT result)"
    elif delta > 0.003:
        verdict = (f"GBDT BEATS DL (best GBDT {best_gbdt:+.4f} vs DL {dl:+.4f}, "
                   f"+{delta:.4f}) => our DL leaves snapshot signal on the table")
    elif delta < -0.003:
        verdict = (f"GBDT BELOW DL (best GBDT {best_gbdt:+.4f} vs DL {dl:+.4f}, "
                   f"{delta:+.4f}) => temporal/cross-asset DL genuinely adds over"
                   f" the snapshot -- the escape hatch is real")
    else:
        verdict = (f"GBDT MATCHES DL (best GBDT {best_gbdt:+.4f} vs DL {dl:+.4f}, "
                   f"{delta:+.4f}, |d|<=0.003) => INFORMATION-BOUND: our 44 features"
                   f" contain no nonlinear headroom beyond the linear ceiling")
    out["meta"]["best_gbdt_pooled"] = round(best_gbdt, 4) if np.isfinite(best_gbdt) else None
    out["meta"]["verdict"] = verdict
    print("VERDICT:", verdict, flush=True)

    with open("/tmp/gbdt_probe.json", "w") as f:
        json.dump(out, f, indent=2)
    print(f"WROTE /tmp/gbdt_probe.json  (total {(time.time()-t0)/60:.1f} min)", flush=True)


if __name__ == "__main__":
    main()
