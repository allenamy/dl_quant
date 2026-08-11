"""A2 — Per-asset Ridge walk-forward SNR gate (Phase 1, PROJECT-DEFINING).

Answers: which of the 14 assets carry any y_600 signal, and does the multi-asset
premise hold? Reads the compact cache built by build_feature_cache.py (each slow
share day already read once), so this step is fast.

Per asset, INDEPENDENT:
  - Walk-forward folds over the cached day window, strictly time-ordered, with a
    1-day embargo between train and test (val sits between, also embargoed).
  - Per fold: standardize X on TRAIN only (no leakage); normalize y by the TRAIN
    fold MAD-sigma (MAD*1.4826) — the project convention; RidgeCV alpha picked by
    its internal LOO on train.
  - Eval on CLEAN test (clean600 non-overlap, stride>=600 subsample): pooled
    Pearson, Spearman, beta (y on yhat), sigma_yhat/sigma_y, bias (mean yhat bps),
    and per-fold Pearson for sign-consistency.

Gate (report, don't decide): count assets with pooled clean P>=+0.02 AND no fold
sign-flip; tier strong(>=0.04)/moderate(0.02-0.04)/weak(<0.02). BTC vs 0.065.

Output: multi_asset/exports/eda/a2_ridge_snr.json + a markdown table (stdout +
a2_ridge_snr.md).
"""
from __future__ import annotations

import json
import os.path as p
import sys

import numpy as np
from scipy.stats import pearsonr, spearmanr
from sklearn.linear_model import RidgeCV

sys.path.insert(0, p.dirname(p.dirname(p.dirname(p.abspath(__file__)))))

SYMBOLS = [
    "bnfbtc", "bnfeth", "bnfsol", "bnfbnb", "bnfxrp", "bnfdog", "bnfada",
    "bnflink", "bnfbch", "bnftrx", "bnfltc", "bnfdot", "bnffil", "bnfetc",
]

CACHE_DIR = ("/mnt/storage/private/work_hsy/quant_research_multi_asset/"
             "multi_asset/exports/panel_cache")
EXPORT_DIR = ("/mnt/storage/private/work_hsy/quant_research_multi_asset/"
              "multi_asset/exports/eda")

ALPHAS = np.logspace(-2, 4, 13)
EMBARGO_DAYS = 1

# Rolling walk-forward fold layout over the ORDERED unique day list (indices into
# the unique-day array). train ~250 / val ~20 / test ~40, rolling by ~80 days.
# 487 days available => fold 2 test ends well within range.
FOLDS = [
    dict(tr=(0, 250), va=(251, 271), te=(272, 312)),
    dict(tr=(80, 330), va=(331, 351), te=(352, 392)),
    dict(tr=(160, 410), va=(411, 431), te=(432, 472)),
]


def mad_sigma(x: np.ndarray) -> float:
    x = x[np.isfinite(x)]
    if x.size == 0:
        return np.nan
    med = np.median(x)
    return float(np.median(np.abs(x - med)) * 1.4826)


def load_sym(sym: str):
    d = np.load(p.join(CACHE_DIR, f"{sym}.npz"))
    return d["X"], d["y"], d["day"], d["clean600"]


def fold_day_ranges(unique_days: np.ndarray, fold: dict):
    """Map index-range fold spec to (train_days, test_days) with a 1-day embargo
    on each side of the test block. Returns sets of day ints, or None if the fold
    extends past the available days."""
    n = unique_days.shape[0]
    (tr0, tr1) = fold["tr"]
    (te0, te1) = fold["te"]
    if te1 > n:
        return None
    train_days = unique_days[tr0:tr1]
    test_days = unique_days[te0:te1]
    # 1-day embargo: drop train days within EMBARGO_DAYS of the test block.
    # (val sits between train end and test start, already separating them; we
    # additionally drop any train day whose index is within the embargo of test.)
    embargo_lo = te0 - EMBARGO_DAYS
    train_idx = np.arange(tr0, tr1)
    train_idx = train_idx[train_idx < embargo_lo]
    train_days = unique_days[train_idx]
    return set(train_days.tolist()), set(test_days.tolist())


def run_asset(sym: str):
    X, y, day, clean = load_sym(sym)
    unique_days = np.unique(day)
    n_days = unique_days.shape[0]

    yhat_all, ytrue_all = [], []   # pooled CLEAN test (in y-units, RAW return)
    perfold_P = []
    n_test_clean_total = 0
    n_folds_used = 0

    for fi, fold in enumerate(FOLDS):
        rng = fold_day_ranges(unique_days, fold)
        if rng is None:
            continue
        train_days, test_days = rng
        tr_mask = np.isin(day, list(train_days))
        te_mask = np.isin(day, list(test_days)) & clean   # CLEAN test only
        if tr_mask.sum() < 500 or te_mask.sum() < 20:
            continue

        Xtr, ytr = X[tr_mask], y[tr_mask]
        Xte, yte = X[te_mask], y[te_mask]

        # standardize X on TRAIN only
        mu = Xtr.mean(axis=0)
        sd = Xtr.std(axis=0)
        sd = np.where(sd > 1e-12, sd, 1.0)
        Xtr_s = (Xtr - mu) / sd
        Xte_s = (Xte - mu) / sd

        # normalize y by TRAIN MAD-sigma (project convention)
        sig = mad_sigma(ytr)
        if not np.isfinite(sig) or sig <= 0:
            continue
        ytr_n = ytr / sig

        model = RidgeCV(alphas=ALPHAS)
        model.fit(Xtr_s, ytr_n)
        yhat_n = model.predict(Xte_s)      # predicted normalized return
        yhat = yhat_n * sig                # back to RAW return units (y-space)

        # per-fold clean Pearson (sign-consistency)
        if np.std(yhat) > 0 and np.std(yte) > 0 and yte.shape[0] >= 5:
            pf = float(pearsonr(yhat, yte)[0])
        else:
            pf = float("nan")
        perfold_P.append(round(pf, 4))

        yhat_all.append(yhat)
        ytrue_all.append(yte)
        n_test_clean_total += int(yte.shape[0])
        n_folds_used += 1

    if n_folds_used == 0 or not yhat_all:
        return {"sym": sym, "error": "no_usable_folds", "n_days": int(n_days)}

    yhat_all = np.concatenate(yhat_all)
    ytrue_all = np.concatenate(ytrue_all)

    P = float(pearsonr(yhat_all, ytrue_all)[0])
    S = float(spearmanr(yhat_all, ytrue_all)[0])
    # beta: y on yhat (trading slope) = cov / var(yhat)
    vy_hat = float(np.var(yhat_all))
    beta = float(np.cov(ytrue_all, yhat_all)[0, 1] / vy_hat) if vy_hat > 0 else float("nan")
    sig_ratio = float(np.std(yhat_all) / np.std(ytrue_all)) if np.std(ytrue_all) > 0 else float("nan")
    bias_bps = float(np.mean(yhat_all) * 1e4)   # mean yhat in bps (raw return * 1e4)

    # sign-flip: any per-fold P strongly negative, or signs disagree
    finite_pf = [x for x in perfold_P if np.isfinite(x)]
    signs = set(np.sign(x) for x in finite_pf if x != 0)
    strong_neg = any(x <= -0.01 for x in finite_pf)
    sign_flip = (len(signs) > 1) or strong_neg

    return {
        "sym": sym,
        "P": round(P, 4),
        "S": round(S, 4),
        "beta": round(beta, 3),
        "sigma_ratio": round(sig_ratio, 4),
        "bias_bps": round(bias_bps, 3),
        "perfold_P": perfold_P,
        "n_test_clean": n_test_clean_total,
        "n_folds": n_folds_used,
        "sign_flip": bool(sign_flip),
        "n_days": int(n_days),
    }


def tier(P: float) -> str:
    if P >= 0.04:
        return "strong"
    if P >= 0.02:
        return "moderate"
    return "weak"


def main():
    results = {}
    for s in SYMBOLS:
        try:
            results[s] = run_asset(s)
        except FileNotFoundError:
            results[s] = {"sym": s, "error": "cache_missing"}
        except Exception as e:
            results[s] = {"sym": s, "error": f"{type(e).__name__}: {e}"}

    # gate
    passing = []
    tiers = {"strong": [], "moderate": [], "weak": []}
    for s in SYMBOLS:
        r = results[s]
        if "error" in r:
            continue
        t = tier(r["P"])
        tiers[t].append(s)
        if r["P"] >= 0.02 and not r["sign_flip"]:
            passing.append(s)

    btc = results.get("bnfbtc", {})
    btc_P = btc.get("P")
    btc_gap = round(btc_P - 0.065, 4) if isinstance(btc_P, float) else None

    summary = {
        "analysis": "A2_per_asset_ridge_snr",
        "cache_dir": CACHE_DIR,
        "folds": FOLDS,
        "embargo_days": EMBARGO_DAYS,
        "alphas": "logspace(-2,4,13)",
        "eval": "CLEAN test (clean600 non-overlap stride>=600), pooled across folds",
        "y_norm": "per-train-fold MAD-sigma (MAD*1.4826)",
        "gate_def": "pooled clean P>=+0.02 AND no fold sign-flip (no per-fold P<=-0.01, signs agree)",
        "n_pass_gate": len(passing),
        "pass_gate_syms": passing,
        "tiers": {k: v for k, v in tiers.items()},
        "btc_P": btc_P,
        "btc_vs_0.065_single_asset_25level": btc_gap,
        "per_symbol": results,
    }

    import os
    os.makedirs(EXPORT_DIR, exist_ok=True)
    with open(p.join(EXPORT_DIR, "a2_ridge_snr.json"), "w") as f:
        json.dump(summary, f, indent=2)

    # markdown table
    lines = []
    lines.append("# A2 — Per-asset Ridge walk-forward SNR (clean y_600)\n")
    lines.append(f"Cache window 2024-06-01..2025-09-30, 3 rolling walk-forward folds, "
                 f"1-day embargo, per-fold standardization, clean (>=600s non-overlap) test.\n")
    lines.append("| sym | P | S | beta | sigma_yhat/sigma_y | bias_bps | per-fold P | n_test_clean | sign_flip | tier |")
    lines.append("|-----|---|---|------|--------------------|----------|------------|--------------|-----------|------|")
    for s in SYMBOLS:
        r = results[s]
        if "error" in r:
            lines.append(f"| {s} | ERR | - | - | - | - | {r['error']} | - | - | - |")
            continue
        lines.append(f"| {s} | {r['P']:+.4f} | {r['S']:+.4f} | {r['beta']:+.2f} | "
                     f"{r['sigma_ratio']:.4f} | {r['bias_bps']:+.3f} | "
                     f"{r['perfold_P']} | {r['n_test_clean']} | "
                     f"{'YES' if r['sign_flip'] else 'no'} | {tier(r['P'])} |")
    lines.append("")
    lines.append(f"**Gate pass (P>=+0.02 AND no sign-flip): {len(passing)}/14** -> {passing}")
    lines.append(f"**Tiers** — strong(>=0.04): {tiers['strong']}; "
                 f"moderate(0.02-0.04): {tiers['moderate']}; weak(<0.02): {tiers['weak']}")
    if isinstance(btc_P, float):
        lines.append(f"**BTC-on-bar-data P = {btc_P:+.4f}** vs 0.065 (single-asset 25-level) "
                     f"=> gap {btc_gap:+.4f}")
    md = "\n".join(lines)
    with open(p.join(EXPORT_DIR, "a2_ridge_snr.md"), "w") as f:
        f.write(md + "\n")

    print(md)
    print(f"\nWrote {p.join(EXPORT_DIR, 'a2_ridge_snr.json')}")
    print(f"Wrote {p.join(EXPORT_DIR, 'a2_ridge_snr.md')}")


if __name__ == "__main__":
    main()
