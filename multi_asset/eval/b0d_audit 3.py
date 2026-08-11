"""AUDIT of the surprising B0d PASS (ΔP +0.0362, per-asset Pearson 0.028->0.064). Before it
earns a Batch-2 FiLM arm, four checks (team-lead 2026-07-10):
  1. shuffle-FUTURE null on B0d (permute Y in time, 20 perms -> z) — my gate only nulled B0b.
  2. per-interaction-term decomposition — is it ONE interpretable term (dispersion x reversal)
     or diffuse (more suspicious)?
  3. ALPHA-sensitivity — the prime suspect: alpha=200 may over-shrink the baseline reversal
     (ret_600s), and g_t x asset_ret interactions merely RECOVER the under-fit main effect =
     a regularization artifact, not a real interaction signal. If ΔP collapses at low alpha,
     it's an artifact.
  4. g_t causality: every component is an aggregate of the causal 44-feat baseline (ret_600s
     idx4, rv_300s idx25 — features_ma is strictly <=t), interactions are (<=t)x(<=t). Stated,
     not leak by construction; the shuffle-null is the empirical backstop.

Run: PYTHONPATH=. python multi_asset/eval/b0d_audit.py
"""
from __future__ import annotations
import numpy as np
from sklearn.linear_model import Ridge
from scipy.stats import pearsonr
from multi_asset.eval.ofi_ridge_gate import SYMBOLS, build_folds
from multi_asset.eval.ofi_xasset_gate import load_common, build_xasset_channels, _fam, RET600

MIN_ASSETS = 5


def _mon(d):
    return int(d) // 100


def eval_set(data, cols_by_sym, folds, alpha):
    """Per-fold clean per-asset Pearson for baseline+cols (cols_by_sym: sym->col idx into Xo,
    or None for baseline-only). Ridge alpha configurable; train rows capped."""
    per = []
    for train_mons, test_mons in folds:
        Xtr, ytr = [], []
        for s in SYMBOLS:
            d = data[s]; m = np.array([_mon(x) for x in d["day"]])
            tr = np.isin(m, train_mons) & np.isfinite(d["y"])
            parts = [d["Xb"][tr]]
            if cols_by_sym is not None:
                parts.append(d["Xo"][tr][:, cols_by_sym])
            Xtr.append(np.concatenate(parts, 1)); ytr.append(d["y"][tr])
        Xtr = np.nan_to_num(np.concatenate(Xtr)); ytr = np.concatenate(ytr)
        if len(ytr) > 400_000:
            sel = np.linspace(0, len(ytr) - 1, 400_000).astype(int); Xtr = Xtr[sel]; ytr = ytr[sel]
        mu, sd = Xtr.mean(0), Xtr.std(0) + 1e-9
        r = Ridge(alpha=alpha).fit((Xtr - mu) / sd, ytr)
        Ps = []
        for s in SYMBOLS:
            d = data[s]; m = np.array([_mon(x) for x in d["day"]])
            te = np.isin(m, test_mons) & d["clean"] & np.isfinite(d["y"])
            if te.sum() < 30:
                continue
            parts = [d["Xb"][te]]
            if cols_by_sym is not None:
                parts.append(d["Xo"][te][:, cols_by_sym])
            Xte = np.nan_to_num(np.concatenate(parts, 1))
            pr = r.predict((Xte - mu) / sd); yy = d["y"][te]
            if np.std(pr) > 1e-12 and np.std(yy) > 1e-12:
                Ps.append(pearsonr(pr, yy)[0])
        per.append(np.mean(Ps) if Ps else np.nan)
    return np.array(per)


def main():
    data, common = load_common()
    names = build_xasset_channels(data)
    fam = _fam(names); b0d = fam["b0d"]; folds = build_folds(data)
    b0d_names = [names[i] for i in b0d]
    base = eval_set(data, None, folds, 200.0)
    full = eval_set(data, b0d, folds, 200.0)
    print(f"baseline mean cleanP {np.nanmean(base):+.4f}  b0d ΔP {np.nanmean(full-base):+.4f} "
          f"per-fold {np.round(full-base,4)}")

    print("\n=== (2) per-term ΔP decomposition (each single interaction) ===")
    for k, nm in zip(b0d, b0d_names):
        pf = eval_set(data, np.array([k]), folds, 200.0)
        print(f"  {nm:16s} ΔP {np.nanmean(pf-base):+.4f}")

    print("\n=== (3) ALPHA sensitivity (regularization-artifact check) ===")
    for a in (10.0, 50.0, 200.0, 1000.0):
        b = eval_set(data, None, folds, a); f = eval_set(data, b0d, folds, a)
        print(f"  alpha={a:7.1f}  baseP {np.nanmean(b):+.4f}  b0d ΔP {np.nanmean(f-b):+.4f}")

    print("\n=== (1) shuffle-FUTURE null on B0d (permute Y in time, 20 perms) ===")
    rng = np.random.default_rng(1); nulls = []
    real = np.nanmean(full - base)
    for _ in range(20):
        dN = {s: dict(data[s]) for s in SYMBOLS}
        perm = rng.permutation(len(common))
        for s in SYMBOLS:
            dN[s] = dict(data[s]); dN[s]["y"] = data[s]["y"][perm]     # break feature->future
        bn = eval_set(dN, None, folds, 200.0); fn = eval_set(dN, b0d, folds, 200.0)
        nulls.append(np.nanmean(fn - bn))
    nulls = np.array(nulls)
    z = (real - nulls.mean()) / (nulls.std() + 1e-9)
    print(f"  real ΔP {real:+.4f}  null mean {nulls.mean():+.4f} std {nulls.std():.4f}  z={z:+.2f}")
    print(f"\nVERDICT: {'ΔP survives (real feature->future structure)' if z>=3 else 'ΔP is null-band (artifact)'}"
          f"; alpha-persistence + single-term decomposition above decide artifact-vs-real.")


if __name__ == "__main__":
    main()
