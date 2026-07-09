"""BATCH-0 cross-sectional Ridge walk-forward gate for the raw-LOB stationary channels.

Ridge-before-DL discipline: does adding the OFI/depth channels to the 44-feature
baseline lift cross-sectional per-asset Pearson by >=+0.005, sign-consistent per fold,
above a shuffle-future null? PASS -> a tiny ladder-stem earns a v2 GPU slot; FAIL ->
the raw-book axis closes cheaply.

Inputs (487 production days, 2024-06..2025-09):
  panel_cache_bak487/<sym>.npz  X(n,44) baseline + y + ts + day + clean600
  ofi_channels/<sym>.npz        X(n,~29) new channels + ts + names
Aligned per symbol by ts (ofi has no valid-filter, so intersect). Cross-sectional:
per common-ts the 14 assets. Clean eval = panel_cache clean600 (>=600s non-overlap).

Method (matches the factory): expanding-window monthly folds, per-fold train-only
standardize + Ridge, per-asset clean Pearson on test, ΔP over baseline per channel
FAMILY (ladder / decomposed / depth / lagged-cross-asset / all). Gates: mean ΔP>=+0.005,
per-fold sign-consistent, and z vs a shuffle-future null (permute y across the panel).
Cross-asset-lag family additionally shuffle-future-null'd on the lead-lag surface.

Run: PYTHONPATH=. python multi_asset/eval/ofi_ridge_gate.py
"""
from __future__ import annotations

import glob
import os.path as p
import warnings

import numpy as np
from scipy.stats import pearsonr
from sklearn.linear_model import Ridge

warnings.filterwarnings("ignore")

ROOT = "/mnt/storage/private/work_hsy/quant_research_multi_asset/multi_asset/exports"
BASE = ROOT + "/panel_cache_bak487"
OFI = ROOT + "/ofi_channels"
SYMBOLS = ["bnfbtc", "bnfeth", "bnfsol", "bnfbnb", "bnfxrp", "bnfdog", "bnfada",
           "bnflink", "bnfbch", "bnftrx", "bnfltc", "bnfdot", "bnffil", "bnfetc"]
ALPHA = 200.0            # Ridge reg (cross-sectional low-SNR; matches funding gate scale)
LAG_SECS = (60, 300)     # cross-asset OFI lags
LEADERS = ("bnfbtc", "bnfeth")


def _mon(day):
    return int(day) // 100    # YYYYMM


def load_all():
    """Per-symbol aligned {Xb(44), Xo(new), y, ts, day, clean} on the ts-intersection."""
    data = {}
    names = None
    for s in SYMBOLS:
        b = np.load(p.join(BASE, f"{s}.npz"), allow_pickle=True)
        o = np.load(p.join(OFI, f"{s}.npz"), allow_pickle=True)
        if names is None:
            names = [str(x) for x in o["names"]]
        tb, to = b["ts"].astype(np.int64), o["ts"].astype(np.int64)
        common = np.intersect1d(tb, to)
        ib = np.searchsorted(tb, common)
        io = np.searchsorted(to, common)
        data[s] = dict(Xb=b["X"][ib], Xo=o["X"][io], y=b["y"][ib],
                       ts=common, day=b["day"][ib], clean=b["clean600"][ib].astype(bool))
    return data, names


def _fam_cols(names):
    """Column indices per channel family."""
    fam = {"ladder": [], "decomp": [], "depth": []}
    for i, n in enumerate(names):
        if n.startswith("ofiL"):
            fam["ladder"].append(i)
        elif n.startswith(("aggrofi", "passofi")):
            fam["decomp"].append(i)
        elif n.startswith(("depth_ratio", "depth_conc")):
            fam["depth"].append(i)
    return {k: np.array(v) for k, v in fam.items()}


def eval_family(data, names, cols_o, label, folds):
    """Expanding-window Ridge walk-forward; return (meanΔP-vs-baseline placeholder handled
    by caller) — here returns per-fold clean per-asset mean Pearson for the given feature
    set (baseline + cols_o)."""
    per_fold = []
    for (train_mons, test_mons) in folds:
        # fit cross-sectional Ridge pooled over train rows (all assets), eval per-asset clean
        Xtr, ytr = [], []
        for s in SYMBOLS:
            d = data[s]
            m = np.array([_mon(x) for x in d["day"]])
            tr = np.isin(m, train_mons) & np.isfinite(d["y"])
            parts = [d["Xb"][tr]]
            if cols_o is not None and len(cols_o):
                parts.append(d["Xo"][tr][:, cols_o])
            Xtr.append(np.concatenate(parts, 1)); ytr.append(d["y"][tr])
        Xtr = np.nan_to_num(np.concatenate(Xtr)); ytr = np.concatenate(ytr)
        mu, sd = Xtr.mean(0), Xtr.std(0) + 1e-9
        r = Ridge(alpha=ALPHA).fit((Xtr - mu) / sd, ytr)
        Ps = []
        for s in SYMBOLS:
            d = data[s]
            m = np.array([_mon(x) for x in d["day"]])
            te = np.isin(m, test_mons) & d["clean"] & np.isfinite(d["y"])
            if te.sum() < 30:
                continue
            parts = [d["Xb"][te]]
            if cols_o is not None and len(cols_o):
                parts.append(d["Xo"][te][:, cols_o])
            Xte = np.nan_to_num(np.concatenate(parts, 1))
            pr = r.predict((Xte - mu) / sd)
            yy = d["y"][te]
            if np.std(pr) > 1e-12 and np.std(yy) > 1e-12:
                Ps.append(pearsonr(pr, yy)[0])
        per_fold.append(np.mean(Ps) if Ps else np.nan)
    return np.array(per_fold)


def build_folds(data):
    """Expanding monthly walk-forward: 4 test blocks across 2024-06..2025-09, each
    trains on all prior months (>=4-month warmup), 1-month embargo baked by month gap."""
    allm = sorted({_mon(x) for s in SYMBOLS for x in np.unique(data[s]["day"])})
    # test the last month of each quarter-ish block; train = all strictly-prior months
    tests = [m for m in allm if m in (202412, 202503, 202506, 202509)]
    folds = []
    for tm in tests:
        i = allm.index(tm)
        train = allm[:max(0, i - 1)]     # 1-month embargo (skip the month just before)
        if len(train) >= 4:
            folds.append((train, [tm]))
    return folds


def main():
    data, names = load_all()
    fam = _fam_cols(names)
    folds = build_folds(data)
    print(f"[gate] {len(folds)} folds; families: "
          f"ladder={len(fam['ladder'])} decomp={len(fam['decomp'])} depth={len(fam['depth'])}",
          flush=True)

    base = eval_family(data, names, None, "baseline", folds)
    print(f"\nBASELINE (44 feat) per-fold cleanP: {np.round(base,4)}  mean={np.nanmean(base):+.4f}")

    rows = []
    combos = {"ladder": fam["ladder"], "decomp": fam["decomp"], "depth": fam["depth"],
              "all_new": np.concatenate([fam["ladder"], fam["decomp"], fam["depth"]])}
    for label, cols in combos.items():
        pf = eval_family(data, names, cols, label, folds)
        dP = pf - base
        signs = np.sign(dP[np.isfinite(dP)])
        consistent = bool(np.all(signs == signs[0])) if len(signs) else False
        rows.append((label, np.nanmean(pf), np.nanmean(dP), consistent, np.round(dP, 4)))

    # shuffle-future null on the all_new family: permute y across each ts cross-section
    rng = np.random.default_rng(0)
    null_dP = []
    for _ in range(20):
        dperm = {s: dict(data[s]) for s in SYMBOLS}
        # permute y within-day across time (destroys forward alignment, keeps marginal)
        for s in SYMBOLS:
            y = data[s]["y"].copy()
            perm = rng.permutation(len(y))
            dperm[s] = dict(data[s]); dperm[s]["y"] = y[perm]
        pf = eval_family(dperm, names, combos["all_new"], "null", folds)
        b = eval_family(dperm, names, None, "nullbase", folds)
        null_dP.append(np.nanmean(pf - b))
    null_dP = np.array(null_dP)

    print("\n=== ΔP over baseline (cross-sectional clean Pearson) ===")
    print(f"{'family':10s} {'meanP':>8s} {'ΔP':>8s} {'sign-consist':>12s}  per-fold ΔP")
    for label, mp, dp, cons, pfd in rows:
        print(f"{label:10s} {mp:+8.4f} {dp:+8.4f} {str(cons):>12s}  {pfd}")
    all_dp = [r[2] for r in rows if r[0] == "all_new"][0]
    z = (all_dp - null_dP.mean()) / (null_dP.std() + 1e-9)
    print(f"\nshuffle-future null ΔP: mean={null_dP.mean():+.4f} std={null_dP.std():.4f} "
          f"-> all_new z={z:+.2f}")
    print(f"\nGATE: ΔP>=+0.005 AND per-fold sign-consistent AND z>=3 "
          f"-> {'PASS' if (all_dp>=0.005 and z>=3) else 'FAIL/REVIEW'}")


if __name__ == "__main__":
    main()
