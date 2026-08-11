"""DECISIVE B0d test: is the +0.036 gain CROSS-SECTIONAL alpha (survives market-neutral
demeaning = justifies the Batch-2 FiLM arm) or MARKET-TIMING (a common directional signal
that the per-asset-Pearson gate rewards but a dollar-neutral L/S book neutralizes to zero)?

The B0d winner is g_t1(=cap-wtd market return) x asset_ret — a market-state x return interaction.
Per-asset Pearson rewards timing the common market move; cross-sectional rank-IC (per-ts demean
+ rank corr across assets) does NOT. Score the SAME Ridge preds both ways.

Run: PYTHONPATH=. python multi_asset/eval/b0d_xsec_check.py
"""
from __future__ import annotations
import numpy as np
from sklearn.linear_model import Ridge
from scipy.stats import pearsonr, spearmanr
from multi_asset.eval.ofi_ridge_gate import SYMBOLS, build_folds
from multi_asset.eval.ofi_xasset_gate import load_common, build_xasset_channels, _fam

MIN_ASSETS = 5


def _mon(d):
    return int(d) // 100


def fit_pred(data, cols, folds):
    """Return per-fold (pred (n,S), y (n,S), day (n,)) on clean test rows, for baseline+cols."""
    outs = []
    for train_mons, test_mons in folds:
        Xtr, ytr = [], []
        for s in SYMBOLS:
            d = data[s]; m = np.array([_mon(x) for x in d["day"]])
            tr = np.isin(m, train_mons) & np.isfinite(d["y"])
            parts = [d["Xb"][tr]] + ([d["Xo"][tr][:, cols]] if cols is not None else [])
            Xtr.append(np.concatenate(parts, 1)); ytr.append(d["y"][tr])
        Xtr = np.nan_to_num(np.concatenate(Xtr)); ytr = np.concatenate(ytr)
        if len(ytr) > 400_000:
            sel = np.linspace(0, len(ytr) - 1, 400_000).astype(int); Xtr = Xtr[sel]; ytr = ytr[sel]
        mu, sd = Xtr.mean(0), Xtr.std(0) + 1e-9
        r = Ridge(alpha=200.0).fit((Xtr - mu) / sd, ytr)
        # assemble aligned (row, asset) test matrices on the common grid
        s0 = SYMBOLS[0]; m0 = np.array([_mon(x) for x in data[s0]["day"]])
        te_mask = np.isin(m0, test_mons) & data[s0]["clean"]
        rows = np.where(te_mask)[0]
        P = np.full((len(rows), len(SYMBOLS)), np.nan); Ym = np.full_like(P, np.nan)
        for si, s in enumerate(SYMBOLS):
            d = data[s]
            parts = [d["Xb"][rows]] + ([d["Xo"][rows][:, cols]] if cols is not None else [])
            Xte = np.nan_to_num(np.concatenate(parts, 1))
            P[:, si] = r.predict((Xte - mu) / sd); Ym[:, si] = d["y"][rows]
        outs.append((P, Ym))
    return outs


def metrics(outs):
    """per-asset Pearson (gate metric) vs cross-sectional rank-IC (deployment metric)."""
    perasset, xsec = [], []
    for P, Y in outs:
        pa = []
        for si in range(len(SYMBOLS)):
            m = np.isfinite(P[:, si]) & np.isfinite(Y[:, si])
            if m.sum() > 30 and np.std(P[m, si]) > 1e-12 and np.std(Y[m, si]) > 1e-12:
                pa.append(pearsonr(P[m, si], Y[m, si])[0])
        perasset.append(np.mean(pa) if pa else np.nan)
        ics = []
        for t in range(P.shape[0]):
            v = np.isfinite(P[t]) & np.isfinite(Y[t])
            if v.sum() >= MIN_ASSETS and np.std(P[t, v]) > 1e-12 and np.std(Y[t, v]) > 1e-12:
                ics.append(spearmanr(P[t, v], Y[t, v])[0])
        xsec.append(np.mean(ics) if ics else np.nan)
    return np.array(perasset), np.array(xsec)


def main():
    data, common = load_common()
    names = build_xasset_channels(data); b0d = _fam(names)["b0d"]; folds = build_folds(data)
    bpa, bxs = metrics(fit_pred(data, None, folds))
    fpa, fxs = metrics(fit_pred(data, b0d, folds))
    print("metric                 baseline    +B0d      ΔP")
    print(f"per-asset Pearson    {np.nanmean(bpa):+.4f}  {np.nanmean(fpa):+.4f}  {np.nanmean(fpa-bpa):+.4f}  (gate metric — rewards market-timing)")
    print(f"cross-sec rank-IC    {np.nanmean(bxs):+.4f}  {np.nanmean(fxs):+.4f}  {np.nanmean(fxs-bxs):+.4f}  (deployment metric — market-neutral)")
    print(f"\nper-fold xsec ΔrankIC: {np.round(fxs-bxs,4)}")
    dxs = np.nanmean(fxs - bxs)
    print(f"\nVERDICT: {'CROSS-SECTIONAL alpha — survives demean, FiLM arm justified' if dxs >= 0.003 else 'MARKET-TIMING — vanishes under market-neutral demean; per-asset-Pearson gate was misleading, NOT a cross-sectional lever'}")


if __name__ == "__main__":
    main()
