"""milestone_caliber_eval — reproduce the SINGLE-ASSET milestone caliber on a run.

WHY
---
The single-asset y_600 milestone headline (REG_arch P=+0.0646, strong-month
2025-04=0.0816) was, per the repo's own adversarial audit
(``multi_asset/exports/OVERNIGHT_PROGRESS_2026_05_20.md`` 2026-06-12), computed
in a NON-raw caliber:

  * **5σ-clip(y)** — the realized target y_600 was winsorized (the crash-day
    tails saturated, e.g. fold0 1.51% of rows at ±47.7 bps). On RAW y the SAME
    model scores ~0.037 (panel-honest), the 0.0646 needs the clip. (OVERNIGHT
    line 285: "0.0646 记录是在 5σ-CLIPPED y 上算的".)
  * **causal EMA-demean(q50)** — milestone §3.2:
        q50_live[i] = q50[i] - EMA_lag1(q50[0..i-1]; α=0.01)   # warmup=50
    This is a live-calibration hygiene step; its Pearson effect is **−0.0006**
    (it does NOT inflate — documented in the milestone). It mainly fixes DC bias.

So this script reports Pearson under FOUR calibers so the caliber decomposition
is explicit and we can localise where any "0.08" lives:

    raw                 : de-standardised q50 vs RAW de-standardised y
    clip5               : raw q50 vs 5σ-CLIPPED y (clip standardised y at ±5)
    ema                 : causal-EMA-demean(q50) vs RAW y
    clip5+ema           : causal-EMA-demean(q50) vs 5σ-CLIPPED y   ← MILESTONE

Pearson/Spearman/beta/sigma_ratio/mono/DA per fold + pooled, DENSE and CLEAN
(perp_battery clean subsample). Reuses perp_battery kernels + load_model so the
de-standardisation/affine handling is caliber-identical to the frozen instrument.

5σ DEFINITION
-------------
The saved ``targets`` are STANDARDISED in-file (perp_battery: y_raw = y_std *
y_sigma + y_median). "5σ" in the milestone = 5 standard deviations of y. We clip
the STANDARDISED y at ±5 (i.e. raw y at ±5·y_sigma) — the canonical reading.
``--clip_k`` overrides the 5. Pearson is NOT affine-invariant to clipping (it
changes the data), which is exactly the point: clip5 vs raw isolates the tail
effect.

CLI
---
    python3 multi_asset/eval/milestone_caliber_eval.py \
        --dirs <d1> [<d2> ...] --names <n1> [...] [--ckpt ema|best|both] [--clip_k 5.0]
"""
from __future__ import annotations

import argparse
import glob
import os.path as p
import sys

import numpy as np

_HERE = p.dirname(p.abspath(__file__))
_REPO = p.dirname(p.dirname(_HERE))
if _REPO not in sys.path:
    sys.path.insert(0, _REPO)

from multi_asset.eval.perp_battery import (  # noqa: E402
    _finite_pair,
    beta_slope,
    bias_bps,
    clean_subsample_factor,
    monotonicity,
    pearson,
    sigma_ratio,
    spearman,
)


# --------------------------------------------------------------------------- #
# milestone caliber transforms
# --------------------------------------------------------------------------- #
def causal_ema_demean(q50, alpha=0.01, warmup=50):
    """Milestone §3.2: q50_live[i] = q50[i] - EMA_lag1(q50[0..i-1]; alpha).

    Strictly causal (sample i uses only [0..i-1]). The EMA is the lag-1 running
    exponential mean of q50; for i < warmup the EMA is still spinning up so we
    subtract the running simple mean up to i-1 (matching the milestone's
    warmup=50 spirit: don't trust the EMA before it has seen ~warmup points).
    Returns an array same length as q50 (NaN for i==0 where no history exists;
    callers drop NaNs via _finite_pair).
    """
    q = np.asarray(q50, dtype=np.float64)
    n = q.size
    out = np.empty(n, dtype=np.float64)
    ema = 0.0
    have = False
    run_sum = 0.0
    for i in range(n):
        if not have:
            out[i] = np.nan          # no history for the very first sample
        elif i < warmup:
            out[i] = q[i] - (run_sum / i)        # simple running mean of [0..i-1]
        else:
            out[i] = q[i] - ema                  # EMA of [0..i-1]
        # update running stats with sample i AFTER using history [0..i-1]
        run_sum += q[i]
        ema = q[i] if not have else (1 - alpha) * ema + alpha * q[i]
        have = True
    return out


def clip5_y_std(y_std, k=5.0):
    """5σ-clip on the STANDARDISED y: clip at ±k (k std units)."""
    return np.clip(np.asarray(y_std, dtype=np.float64), -k, k)


# --------------------------------------------------------------------------- #
# loader that keeps STANDARDISED q50 + y AND timestamps (we need std-space y to
# apply the ±5 clip; de-standardisation is a common affine so Pearson is the same)
# --------------------------------------------------------------------------- #
def load_folds_std(model_dir, ckpt):
    fname = "ema_test_preds.npz" if ckpt == "ema" else "test_preds.npz"
    files = sorted(glob.glob(p.join(model_dir, "fold_*", fname)))
    if not files:
        raise FileNotFoundError(f"no {fname} under {model_dir}/fold_*")
    folds = []
    for f in files:
        z = np.load(f)
        q50_std = z["predictions"][:, 1].astype(np.float64)
        y_std = z["targets"].astype(np.float64)
        mask = z["mask"].astype(bool) if "mask" in z else np.ones(y_std.shape, bool)
        ts = z["timestamps"].astype(np.int64) if "timestamps" in z else np.arange(y_std.size)
        ysig = float(z["y_sigma"]) if "y_sigma" in z else 1.0
        ymed = float(z["y_median"]) if "y_median" in z else 0.0
        valid = mask & np.isfinite(q50_std) & np.isfinite(y_std)
        folds.append({
            "fold": int(p.basename(p.dirname(f)).split("_")[1]),
            "q50_std": q50_std[valid], "y_std": y_std[valid],
            "ts": ts[valid], "ysig": ysig, "ymed": ymed,
        })
    return folds


def _caliber_arrays(fd, caliber, clip_k):
    """Return (q50, y) for the requested caliber, time-sorted (EMA needs order)."""
    order = np.argsort(fd["ts"], kind="stable")
    q_std = fd["q50_std"][order]
    y_std = fd["y_std"][order]
    ysig, ymed = fd["ysig"], fd["ymed"]
    # de-standardise to raw return units (affine; Pearson invariant)
    q_raw = q_std * ysig + ymed
    y_raw = y_std * ysig + ymed
    if caliber == "raw":
        return q_raw, y_raw, order
    if caliber == "clip5":
        y_clip = clip5_y_std(y_std, clip_k) * ysig + ymed
        return q_raw, y_clip, order
    if caliber == "ema":
        return causal_ema_demean(q_raw), y_raw, order
    if caliber == "clip5+ema":
        y_clip = clip5_y_std(y_std, clip_k) * ysig + ymed
        return causal_ema_demean(q_raw), y_clip, order
    raise ValueError(caliber)


def _metrics(q, y):
    a, b = _finite_pair(q, y)
    return {
        "n": int(a.size), "pearson": pearson(a, b), "spearman": spearman(a, b),
        "beta": beta_slope(a, b), "sigma_ratio": sigma_ratio(a, b),
        "mono": monotonicity(a, b), "bias_bps": bias_bps(a),
    }


def eval_caliber(folds, caliber, sample, clip_k):
    """Per-fold + pooled metrics for one caliber and one sample (dense|clean)."""
    out = {}
    pooled_q, pooled_y = [], []
    for fd in folds:
        q, y, _ = _caliber_arrays(fd, caliber, clip_k)
        ts = np.sort(fd["ts"])
        if sample == "clean":
            factor = clean_subsample_factor(ts)
            q, y = q[::factor], y[::factor]
        out[f"fold_{fd['fold']}"] = _metrics(q, y)
        pooled_q.append(q); pooled_y.append(y)
    if pooled_q:
        out["POOLED"] = _metrics(np.concatenate(pooled_q), np.concatenate(pooled_y))
    return out


_CALIBERS = ["raw", "clip5", "ema", "clip5+ema"]


def render(name, ckpt, by, clip_k):
    L = [f"\n{'='*92}",
         f"MILESTONE-CALIBER EVAL: {name}  ckpt={ckpt}  (clip_k={clip_k}σ; "
         f"EMA α=0.01 warmup=50)", "=" * 92]
    for sample in ("dense", "clean"):
        L.append(f"\n[{sample.upper()}]")
        L.append(f"{'caliber':<12}{'scope':<9}{'N':>9}{'Pearson':>10}{'Spearman':>10}"
                 f"{'beta':>8}{'sig_r':>8}{'mono':>7}{'bias_bps':>10}")
        L.append("-" * 92)
        for cal in _CALIBERS:
            tbl = by[sample][cal]
            for scope in sorted(k for k in tbl if k != "POOLED") + (["POOLED"] if "POOLED" in tbl else []):
                m = tbl[scope]
                def f(v, w, pr):
                    return "nan".rjust(w) if (v is None or not np.isfinite(v)) else f"{v:>{w}.{pr}f}"
                L.append(f"{cal:<12}{scope:<9}{m['n']:>9d}{f(m['pearson'],10,4)}"
                         f"{f(m['spearman'],10,4)}{f(m['beta'],8,3)}{f(m['sigma_ratio'],8,4)}"
                         f"{f(m['mono'],7,2)}{f(m['bias_bps'],10,3)}")
            L.append("")
    # headline summary: pooled Pearson per caliber, both samples
    L.append("HEADLINE pooled Pearson:")
    for sample in ("dense", "clean"):
        row = "  ".join(f"{cal}={by[sample][cal].get('POOLED',{}).get('pearson',float('nan')):+.4f}"
                        for cal in _CALIBERS)
        L.append(f"  [{sample}] {row}")
    return "\n".join(L)


def run(dirs, names, ckpts, clip_k):
    for d, nm in zip(dirs, names):
        for ckpt in ckpts:
            try:
                folds = load_folds_std(d, ckpt)
            except FileNotFoundError as e:
                print(f"[skip] {nm} ckpt={ckpt}: {e}")
                continue
            by = {s: {cal: eval_caliber(folds, cal, s, clip_k) for cal in _CALIBERS}
                  for s in ("dense", "clean")}
            print(render(nm, ckpt, by, clip_k))


def main():
    ap = argparse.ArgumentParser(description="milestone-caliber (5σ-clip + EMA-demean) eval")
    ap.add_argument("--dirs", nargs="+", required=True)
    ap.add_argument("--names", nargs="+", required=True)
    ap.add_argument("--ckpt", choices=["ema", "best", "both"], default="both")
    ap.add_argument("--clip_k", type=float, default=5.0, help="σ-clip multiple (default 5)")
    args = ap.parse_args()
    if len(args.dirs) != len(args.names):
        ap.error("--dirs and --names length mismatch")
    ckpts = ["ema", "best"] if args.ckpt == "both" else [args.ckpt]
    run(args.dirs, args.names, ckpts, args.clip_k)


if __name__ == "__main__":
    main()
