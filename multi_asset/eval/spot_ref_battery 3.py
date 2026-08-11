"""spot_ref_battery — dual-caliber eval for the STABLE spot->spot reference.

PURPOSE
-------
Phase-1 of the dual-source perp y_600 "stability-first pivot" needs ONE honest
reference number the later levers (divergence / basis / regime FiLM) must beat:
the spot->spot model (SPOT inputs -> y_600, trained on data/npz_spot). This script
reads each fold's prediction NPZ and reports the project dual-caliber, ADDING two
columns ``perp_battery`` does not: directional accuracy (DA = sign-match rate) and
an EMA-demean caliber.

It deliberately REUSES ``perp_battery``'s pure, unit-tested metric kernels
(pearson / spearman / beta_slope / monotonicity / sigma_ratio / bias_bps,
clean_subsample_factor, de-standardization in load_model) so the numbers are
caliber-identical to the frozen instrument; we only add DA + the EMA-demean
transform on top. ``perp_battery`` itself is NOT modified.

CALIBERS
--------
dense           : all masked windows, raw EMA q50.
clean           : within-fold subsample so labels are >= HORIZON_S apart
                  (== perp_battery's clean; "::4" caliber for the ~180s grid).
EMA-demean      : the milestone caliber. q50' = q50 - mean(q50) (per assembled
                  sample). Demeaning is affine, so Pearson/Spearman/beta/sigma_r/
                  mono are IDENTICAL to the non-demeaned numbers; what it changes
                  is bias_bps (-> ~0) and DA (sign accuracy after removing the
                  long-short bias). We therefore report DA both raw and demeaned.

METRICS (per fold AND pooled, on RAW y, masked):
    n, pearson, spearman, beta, sigma_ratio, monotonicity(decile),
    DA_raw      = mean( sign(q50)      == sign(y) )   over y != 0
    DA_demean   = mean( sign(q50-mean) == sign(y) )   over y != 0
    bias_bps    = mean(q50) * 1e4
    bias_bps_dm = mean(q50 - mean(q50)) * 1e4  (~0 by construction; sanity)

A spot fold is FLAGGED LOUDLY if it "blows up": beta < 0 (sign-flip) or
sigma_ratio < 0.005 (variance collapse) -- the spot baseline is expected to be
stable (healthy beta ~0.5-1.2, no negative-beta blowup); a blow-up here would
change the whole Phase-1 diagnosis.

CLI
---
    python3 multi_asset/eval/spot_ref_battery.py \
        --dirs <d1> [<d2> ...] --names <n1> [<n2> ...] [--ckpt ema|best|both]
"""
from __future__ import annotations

import argparse
import os.path as p
import sys

import numpy as np

_HERE = p.dirname(p.abspath(__file__))
_REPO = p.dirname(p.dirname(_HERE))
if _REPO not in sys.path:
    sys.path.insert(0, _REPO)

# Reuse the FROZEN perp_battery kernels verbatim (caliber-identical numbers).
from multi_asset.eval.perp_battery import (  # noqa: E402
    HORIZON_S,
    _finite_pair,
    _months_array,
    assemble,
    beta_slope,
    bias_bps,
    load_model,
    monotonicity,
    pearson,
    sigma_ratio,
    spearman,
)


# --------------------------------------------------------------------------- #
# extra kernels (DA + demean), built on perp_battery's _finite_pair
# --------------------------------------------------------------------------- #
def directional_accuracy(q50, y):
    """Fraction of rows where sign(q50) == sign(y), over y != 0 (ties dropped).

    Sign(0) is treated as a miss (np.sign(0)=0 never equals +/-1), which is the
    conservative convention; rows with y == 0 are excluded from the denominator.
    """
    a, b = _finite_pair(q50, y)
    nz = b != 0.0
    if nz.sum() < 2:
        return float("nan")
    return float((np.sign(a[nz]) == np.sign(b[nz])).mean())


def compute_ref_metrics(q50, y):
    """dual-caliber dict + DA(raw) + DA(demean) + bias(raw/demean)."""
    a, b = _finite_pair(q50, y)
    a_dm = a - a.mean() if a.size else a
    return {
        "n": int(a.size),
        "pearson": pearson(a, b),
        "spearman": spearman(a, b),
        "beta": beta_slope(a, b),
        "sigma_ratio": sigma_ratio(a, b),
        "monotonicity": monotonicity(a, b),
        "DA_raw": directional_accuracy(a, b),
        "DA_demean": directional_accuracy(a_dm, b),
        "bias_bps": bias_bps(a),
        "bias_bps_dm": bias_bps(a_dm),
    }


def _blowup_flags(m):
    flags = []
    if m["beta"] is not None and np.isfinite(m["beta"]) and m["beta"] < 0:
        flags.append("NEG-BETA(sign-flip)")
    if (m["sigma_ratio"] is not None and np.isfinite(m["sigma_ratio"])
            and m["sigma_ratio"] < 0.005):
        flags.append("SIGMA-COLLAPSE")
    return flags


# --------------------------------------------------------------------------- #
# per-fold + pooled assembly (reuse perp_battery.assemble for clean subsample)
# --------------------------------------------------------------------------- #
def per_fold_and_pooled(folds, sample):
    """Return {fold_label: metrics, 'POOLED': metrics} for one sample caliber.

    Per FOLD here (not per calendar month) because the spot->spot reference is a
    single test month per fold; fold == month in this setup, and per-fold is what
    the task asks for ("per-fold + pooled").
    """
    out = {}
    # assemble each fold independently for the clean subsample to respect its grid
    for fd in folds:
        q, y, ts = assemble([fd], sample)
        if q.size == 0:
            continue
        out[f"fold_{fd['fold']}"] = compute_ref_metrics(q, y)
    q, y, ts = assemble(folds, sample)
    if q.size:
        out["POOLED"] = compute_ref_metrics(q, y)
    return out


# --------------------------------------------------------------------------- #
# rendering
# --------------------------------------------------------------------------- #
_HEAD = (f"{'fold':<9}{'N':>9}{'Pearson':>10}{'Spearman':>10}{'beta':>8}"
         f"{'sig_r':>8}{'mono':>7}{'DA_raw':>8}{'DA_dm':>8}{'bias':>9}{'bias_dm':>9}")


def _fmt(v, w, prec):
    if v is None or (isinstance(v, float) and not np.isfinite(v)):
        return "nan".rjust(w)
    return f"{v:>{w}.{prec}f}"


def _row(label, m):
    return (f"{label:<9}{m['n']:>9d}"
            f"{_fmt(m['pearson'],10,4)}{_fmt(m['spearman'],10,4)}{_fmt(m['beta'],8,3)}"
            f"{_fmt(m['sigma_ratio'],8,4)}{_fmt(m['monotonicity'],7,2)}"
            f"{_fmt(m['DA_raw'],8,4)}{_fmt(m['DA_demean'],8,4)}"
            f"{_fmt(m['bias_bps'],9,3)}{_fmt(m['bias_bps_dm'],9,3)}")


def render(name, ckpt, by_sample):
    L = [f"\n{'='*100}", f"SPOT->SPOT REFERENCE: {name}   ckpt={ckpt}", "=" * 100]
    blow = []
    for sample in ("dense", "clean"):
        tbl = by_sample.get(sample, {})
        L.append(f"\n[{sample.upper()}]  (raw y, masked"
                 + ("; clean stride>=600s)" if sample == "clean" else ")"))
        L.append(_HEAD)
        L.append("-" * 100)
        for k in sorted(k for k in tbl if k != "POOLED"):
            L.append(_row(k, tbl[k]))
            f = _blowup_flags(tbl[k])
            if f:
                blow.append(f"  !! {name} {sample} {k}: {', '.join(f)}")
        if "POOLED" in tbl:
            L.append("-" * 100)
            L.append(_row("POOLED", tbl["POOLED"]))
            f = _blowup_flags(tbl["POOLED"])
            if f:
                blow.append(f"  !! {name} {sample} POOLED: {', '.join(f)}")
    if blow:
        L.append("\n" + "#" * 100)
        L.append("BLOW-UP FLAGS (spot baseline expected STABLE; investigate):")
        L.extend(blow)
        L.append("#" * 100)
    else:
        L.append("\n[OK] no blow-up flags (beta>=0 and sigma_ratio>=0.005 on all "
                 "folds + pooled) -- spot reference is STABLE.")
    return "\n".join(L)


def run(dirs, names, ckpts):
    out = []
    for d, nm in zip(dirs, names):
        for ckpt in ckpts:
            try:
                folds = load_model(d, ckpt)
            except FileNotFoundError as e:
                out.append(f"[skip] {nm} ckpt={ckpt}: {e}")
                continue
            by_sample = {s: per_fold_and_pooled(folds, s) for s in ("dense", "clean")}
            out.append(render(nm, ckpt, by_sample))
    text = "\n".join(out)
    print(text)
    return text


def main():
    ap = argparse.ArgumentParser(description="spot->spot reference dual-caliber eval")
    ap.add_argument("--dirs", nargs="+", required=True)
    ap.add_argument("--names", nargs="+", required=True)
    ap.add_argument("--ckpt", choices=["ema", "best", "both"], default="both")
    args = ap.parse_args()
    if len(args.dirs) != len(args.names):
        ap.error("--dirs and --names must match length")
    ckpts = ["ema", "best"] if args.ckpt == "both" else [args.ckpt]
    run(args.dirs, args.names, ckpts)


if __name__ == "__main__":
    main()
