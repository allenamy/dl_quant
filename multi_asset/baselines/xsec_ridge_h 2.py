"""Phase-0a — POOLED cross-sectional Ridge baseline at an ARBITRARY horizon (default 3600s=1h).

> **created:** 2026-07-07 | **Session:** multi-asset-v2 phase-0a (0B) | **状态:** in-progress

REUSE-not-rebuild: identical to xsec_ridge.py (xsec-demean residual target, per-asset
MAD-sigma, xsec-z the 44 features, pooled Ridge ALPHA=10, same 3-fold walk-forward,
embargo, CLEAN non-overlap test rank-IC) — the ONLY change is the TARGET horizon:
- features X + ts + day: REUSED verbatim from panel_cache (180s grid, 44 feats).
- target y_H: from mh_targets_long (1s-grid y_H). ALIGNMENT: load_day_panel(d) windows are
  OFFSET ~10h from the UTC calendar day, so a panel ts's y_H can live in a DIFFERENT mh file
  than its UTC-date. We fill Y GLOBALLY — for every mh file, exact-ns-match its ts against the
  panel common ts and fill (each ts matches exactly one file).
- CL: greedy non-overlap ≥H per panel-cache day (NOT the inherited clean600 ≥600s) — 0C's
  L/S gate inherits the rebalance cadence from THIS mask + annualizes at --horizon H.

Deliverables for 0C's net-cost L/S gate (ls_gate.py --horizon H), schema validated on A1a:
  <OUT>/panel_ref_h{H}.npz   — symbols[S], ts[T], day[T], Y[T,S] (raw 1h fwd logret), CL[T,S] bool (≥H non-overlap)
  <OUT>/fold_{k}_preds_h{H}.npz — te_rows[n] (indices into panel), pred[T,S] (score; NaN outside test)
  <OUT>/xsec_ridge_h{H}.json — mean xsec rank-IC + IC-IR
"""
from __future__ import annotations
import argparse, json, os, os.path as p
import numpy as np
from scipy.stats import spearmanr
from sklearn.linear_model import Ridge

from multi_asset.baselines.xsec_ridge import SYMBOLS, CACHE, FOLDS, EMBARGO, ALPHA

MH_LONG = "/mnt/storage/private/work_hsy/quant_research_multi_asset/multi_asset/exports/mh_targets_long"
OUT = "/mnt/storage/private/work_hsy/quant_research_multi_asset/multi_asset/exports/eda"
NS = 1_000_000_000


def build_panel_h(horizon: int, cache_dir: str = CACHE):
    """Reuse <cache_dir> X/ts/day; GLOBAL-fill target y_horizon; ≥horizon non-overlap CL."""
    per = {}; fnames = None
    for s in SYMBOLS:
        d = np.load(p.join(cache_dir, f"{s}.npz"), allow_pickle=True)
        per[s] = (d["X"], d["ts"].astype(np.int64), d["day"].astype(np.int64))
        if fnames is None and "factor_names" in d.files:
            fnames = [str(x) for x in d["factor_names"]]
    common = np.array(sorted(set.intersection(*[set(per[s][1].tolist()) for s in SYMBOLS])), dtype=np.int64)
    cidx = {int(t): i for i, t in enumerate(common)}
    nT, nS, nF = len(common), len(SYMBOLS), per[SYMBOLS[0]][0].shape[1]
    X = np.full((nT, nS, nF), np.nan, np.float32)
    DAY = np.zeros(nT, np.int64)
    for si, s in enumerate(SYMBOLS):
        Xs, tss, dys = per[s]; idx = {int(t): i for i, t in enumerate(tss)}
        for t in common:
            j = idx[int(t)]; i = cidx[int(t)]
            X[i, si] = Xs[j]
            if si == 0:
                DAY[i] = dys[j]     # panel-cache day (the fold layout is defined on this)

    # GLOBAL-fill Y = y_horizon: each common ts matches exactly ONE mh file (exact ns ts).
    Y = np.full((nT, nS), np.nan, np.float32); filled = np.zeros(nT, bool)
    for f in sorted(os.listdir(MH_LONG)):
        if not (f.endswith(".npz") and f[:-4].isdigit()):
            continue
        z = np.load(p.join(MH_LONG, f)); yts = z["ts"].astype(np.int64)
        yv = z[f"y_{horizon}"]; ym = z[f"m_{horizon}"]
        pos = np.searchsorted(yts, common)
        okc = (pos < len(yts)) & (yts[np.clip(pos, 0, len(yts) - 1)] == common)
        rows = np.where(okc)[0]; cols = pos[rows]
        for si in range(nS):
            m = ym[si, cols]
            Y[rows[m], si] = yv[si, cols[m]]
        filled[rows] = True

    # CL: greedy non-overlap >= horizon per panel-cache day (per-ts, broadcast to all assets).
    CL = np.zeros((nT, nS), bool); Hns = horizon * NS
    for d in np.unique(DAY):
        r = np.where(DAY == d)[0]; last = -(1 << 62); keep = []
        for i in r:
            if int(common[i]) - last >= Hns:
                keep.append(i); last = int(common[i])
        if keep:
            CL[np.array(keep)] = True
    print(f"panel_h{horizon}: nT={nT} nS={nS} nF={nF} days={len(np.unique(DAY))} "
          f"ts_filled={filled.mean():.3f} Y_finite={np.isfinite(Y).mean():.3f} "
          f"CL_ts_frac={CL.any(1).mean():.3f}", flush=True)
    return common, DAY, X, Y, CL, fnames


def _standalone_ic(X, Y, CL, day, uniq, fnames):
    """Univariate xsec rank-IC per factor: spearman(factor_f across assets, y_resid) on clean
    test ts (all folds' test days), demeaned per ts. Shows which slow factors carry 1h signal."""
    nF = X.shape[2]
    te_days = set()
    for fold in FOLDS:
        n = uniq.shape[0]
        if fold["te"][1] <= n:
            te_days |= set(uniq[fold["te"][0]:fold["te"][1]].tolist())
    tem = np.isin(day, list(te_days))
    Yr = np.full_like(Y, np.nan)
    for i in np.where(tem)[0]:
        row = Y[i]; v = np.isfinite(row)
        if v.sum() >= 5: Yr[i, v] = row[v] - row[v].mean()
    out = {}
    for f in range(nF):
        ics = []
        for i in np.where(tem)[0]:
            v = CL[i] & np.isfinite(X[i, :, f]) & np.isfinite(Yr[i])
            if v.sum() >= 5:
                ic = spearmanr(X[i, v, f], Yr[i, v])[0]
                if np.isfinite(ic): ics.append(ic)
        nm = fnames[f] if fnames else f"f{f}"
        out[nm] = round(float(np.mean(ics)), 4) if ics else None
    return out


def run(horizon: int, cache_dir: str = CACHE, tag: str = None):
    tag = tag or f"h{horizon}"
    ts, day, X, Y, CL, fnames = build_panel_h(horizon, cache_dir)
    uniq = np.unique(day); nS = len(SYMBOLS)

    def fold_days(fold):
        n = uniq.shape[0]
        if fold["te"][1] > n: return None
        te0, te1 = fold["te"]; tr0, tr1 = fold["tr"]
        tri = np.arange(tr0, tr1); tri = tri[tri < te0 - EMBARGO]
        return set(uniq[tri].tolist()), set(uniq[te0:te1].tolist())

    def xsdemean(Yb, rows):
        out = np.full_like(Yb, np.nan)
        for i in np.where(rows)[0]:
            row = Yb[i]; v = np.isfinite(row)
            if v.sum() >= 5: out[i, v] = row[v] - row[v].mean()
        return out

    def xsz(Xb, rows):
        out = np.full_like(Xb, np.nan)
        for i in np.where(rows)[0]:
            blk = Xb[i]; v = np.isfinite(blk).all(1)
            if v.sum() >= 5:
                mu = blk[v].mean(0); sd = blk[v].std(0); sd = np.where(sd > 1e-9, sd, 1.0)
                out[i, v] = (blk[v] - mu) / sd
        return out

    all_ic = []; folds_written = []
    for fk, fold in enumerate(FOLDS):
        r = fold_days(fold)
        if r is None: continue
        trd, ted = r
        trm = np.isin(day, list(trd)); tem = np.isin(day, list(ted))
        Ytr_res = xsdemean(Y, trm); Yte_res = xsdemean(Y, tem)
        sig = np.array([np.median(np.abs(Ytr_res[trm, si][np.isfinite(Ytr_res[trm, si])] -
                        np.median(Ytr_res[trm, si][np.isfinite(Ytr_res[trm, si])]))) * 1.4826
                        if np.isfinite(Ytr_res[trm, si]).sum() > 10 else np.nan for si in range(nS)])
        Xtr_z = xsz(X, trm); Xte_z = xsz(X, tem)
        xs, ys = [], []
        for i in np.where(trm)[0]:
            for si in range(nS):
                if np.isfinite(Xtr_z[i, si]).all() and np.isfinite(Ytr_res[i, si]) and np.isfinite(sig[si]) and sig[si] > 0:
                    xs.append(Xtr_z[i, si]); ys.append(Ytr_res[i, si] / sig[si])
        if len(xs) < 1000: continue
        model = Ridge(alpha=ALPHA); model.fit(np.array(xs), np.array(ys))
        pred_TS = np.full((len(ts), nS), np.nan, np.float32); te_rows = []
        for i in np.where(tem)[0]:
            v = np.isfinite(Xte_z[i]).all(1) & CL[i] & np.isfinite(Yte_res[i])
            if v.sum() >= 5:
                pr = model.predict(Xte_z[i, v])
                icv = spearmanr(pr, Yte_res[i, v])[0]
                if np.isfinite(icv): all_ic.append(icv)
                pred_TS[i, v] = pr; te_rows.append(i)
        if te_rows:
            np.savez(p.join(OUT, f"fold_{fk}_preds_{tag}.npz"),
                     te_rows=np.array(te_rows, np.int64), pred=pred_TS)
            folds_written.append(fk)

    os.makedirs(OUT, exist_ok=True)
    np.savez(p.join(OUT, f"panel_ref_{tag}.npz"),
             symbols=np.array(SYMBOLS, dtype=object), ts=ts, day=day, Y=Y, CL=CL)
    standalone = _standalone_ic(X, Y, CL, day, uniq, fnames)
    ic = np.array(all_ic)
    res = dict(analysis=f"phase0_xsec_ridge_pooled_{tag}", horizon_sec=horizon, cache=cache_dir,
               target=f"xsec-demeaned residual / per-asset MAD-sigma (y_{horizon})",
               features=f"xsec-z {X.shape[2]}-factor {p.basename(cache_dir)}",
               mean_xsec_rank_ic=round(float(ic.mean()), 4) if len(ic) else None,
               ir=round(float(ic.mean() / ic.std() * np.sqrt(len(ic))), 3) if len(ic) and ic.std() > 0 else None,
               n_ts=int(len(ic)), folds_with_preds=folds_written, tag=tag,
               standalone_xsec_rank_ic=standalone, vs_y600_xsec_rank_ic=0.0744)
    json.dump(res, open(p.join(OUT, f"xsec_ridge_{tag}.json"), "w"), indent=2)
    print(json.dumps(res, indent=2))
    print(f"TAG={tag}  panel_ref -> {OUT}/panel_ref_{tag}.npz  preds -> fold_*_preds_{tag}.npz")


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--horizon", type=int, default=3600)
    ap.add_argument("--cache", default=CACHE)
    ap.add_argument("--tag", default=None)
    a = ap.parse_args()
    run(a.horizon, a.cache, a.tag)
