"""perp_battery — dual-caliber eval harness for BTC-perp y_600 models.

ONE frozen instrument to compare models (frozen baseline vs monthly rolling, and
later variants) under the project's dual-caliber discipline. Reads each model's
per-fold prediction NPZs and prints a per-month + pooled metrics table.

Layout (per model dir):
    <dir>/fold_*/ema_test_preds.npz   (EMA checkpoint, primary)
    <dir>/fold_*/test_preds.npz       (BEST checkpoint)
Each NPZ:
    predictions (N,3)  q10,q50,q90  -> col 1 (q50) is the point pred
    targets     (N,)   perp y_600 (STANDARDIZED in-file; see y_sigma/y_median)
    mask        (N,)   bool valid-window mask
    timestamps  (N,)   int64 us
    y_sigma, y_median  scalars used at train time to standardize y

CALIBER NOTE
------------
The saved `predictions`/`targets` are in STANDARDIZED units (per-fold y_sigma~1.3e-3,
y_median~0). We de-standardize BOTH q50 and y back to raw return units
(val*y_sigma + y_median) so that **bias_bps is physically a basis-point number**.
Pearson / Spearman / monotonicity are invariant to this affine map, and beta
(slope of y on q50) and sigma-ratio (std q50 / std y) are invariant to a *common*
affine applied to both series — so the de-standardization changes only bias_bps's
interpretability, not the correlation/calibration numbers. The pooled EMA q50
Pearson therefore reproduces the standardized reference (e.g. roll2026 ~= 0.0247).

Metrics (per calendar month AND pooled), on RAW y, no clipping, masked:
    pearson, spearman, beta=cov(y,q50)/var(q50), sigma_ratio=std(q50)/std(y),
    monotonicity=Spearman(decile_index, decile_mean_y) over 10 q50 bins,
    bias_bps=mean(q50)*1e4
Reported under TWO samples:
    dense — all masked windows
    clean — subsample so label spacing >= 600s (factor = ceil(600/median_gap_s),
            applied within each fold so its native grid is respected)

CLI:
    python3 multi_asset/eval/perp_battery.py \
        --dirs <d1> <d2> ... --names <n1> <n2> ... [--ckpt ema|best|both]
Prints an aligned per-month + pooled table per model; if exactly two dirs are
given, also prints a frozen-vs-rolling pooled delta (name2 - name1).
"""
from __future__ import annotations

import argparse
import datetime as dt
import glob
import json
import os.path as p

import numpy as np
from scipy.stats import pearsonr, spearmanr

HORIZON_S = 600
N_BINS = 10
STRONG_MONTHS = {"2025-02", "2025-04"}  # trending/strong-signal windows


# --------------------------------------------------------------------------- #
# metric kernels (pure, unit-tested)
# --------------------------------------------------------------------------- #
def _finite_pair(a, b):
    a = np.asarray(a, dtype=np.float64)
    b = np.asarray(b, dtype=np.float64)
    m = np.isfinite(a) & np.isfinite(b)
    return a[m], b[m]


def pearson(q50, y):
    a, b = _finite_pair(q50, y)
    if a.size < 2 or a.std() == 0 or b.std() == 0:
        return float("nan")
    return float(pearsonr(a, b)[0])


def spearman(q50, y):
    a, b = _finite_pair(q50, y)
    if a.size < 2:
        return float("nan")
    return float(spearmanr(a, b).correlation)


def beta_slope(q50, y):
    """OLS slope of y on q50 = cov(y, q50) / var(q50)."""
    a, b = _finite_pair(q50, y)  # a=q50, b=y
    if a.size < 2:
        return float("nan")
    va = a.var()
    if va == 0:
        return float("nan")
    cov = np.cov(b, a, bias=True)[0, 1]
    return float(cov / va)


def monotonicity(q50, y, n_bins=N_BINS):
    """Spearman of (decile index) vs (decile mean-y).

    q50 is split into n_bins equal-count quantile bins; for each bin we take the
    mean of y; then rank-correlate the bin index (0..n_bins-1) against those
    means. +1 = perfectly monotone-increasing calibration.
    """
    a, b = _finite_pair(q50, y)  # a=q50, b=y
    if a.size < n_bins * 2:
        return float("nan")
    order = np.argsort(a, kind="stable")
    a_s, b_s = a[order], b[order]
    # equal-count bins via array_split on the sorted order (robust to ties/dups)
    idx = np.array_split(np.arange(a_s.size), n_bins)
    bin_means = np.array([b_s[ix].mean() for ix in idx if ix.size > 0])
    bin_idx = np.arange(bin_means.size)
    if bin_means.size < 2 or np.all(bin_means == bin_means[0]):
        return float("nan")
    return float(spearmanr(bin_idx, bin_means).correlation)


def sigma_ratio(q50, y):
    a, b = _finite_pair(q50, y)
    if a.size < 2 or b.std() == 0:
        return float("nan")
    return float(a.std() / b.std())


def bias_bps(q50):
    a = np.asarray(q50, dtype=np.float64)
    a = a[np.isfinite(a)]
    if a.size == 0:
        return float("nan")
    return float(a.mean() * 1e4)


def compute_metrics(q50, y):
    """Full dual-caliber metric dict on already-aligned (q50, y); guards NaNs."""
    a, b = _finite_pair(q50, y)
    return {
        "n": int(a.size),
        "pearson": pearson(a, b),
        "spearman": spearman(a, b),
        "beta": beta_slope(a, b),
        "sigma_ratio": sigma_ratio(a, b),
        "monotonicity": monotonicity(a, b),
        "bias_bps": bias_bps(a),
    }


def clean_subsample_factor(timestamps):
    """Subsample factor so label spacing >= HORIZON_S: ceil(600 / median_gap_s).

    median_gap derived from the *sorted* timestamp diffs (µs). Factor >= 1.
    """
    ts = np.sort(np.asarray(timestamps, dtype=np.int64))
    if ts.size < 2:
        return 1
    d = np.diff(ts)
    d = d[d > 0]
    if d.size == 0:
        return 1
    median_gap_s = float(np.median(d)) / 1e6
    if median_gap_s <= 0:
        return 1
    return max(1, int(np.ceil(HORIZON_S / median_gap_s)))


# --------------------------------------------------------------------------- #
# loading + de-standardization
# --------------------------------------------------------------------------- #
def _ckpt_filename(ckpt):
    return "ema_test_preds.npz" if ckpt == "ema" else "test_preds.npz"


def load_model(model_dir, ckpt):
    """Load all folds for one model+ckpt. Returns per-fold list of dicts with
    de-standardized raw-unit q50 & y, plus mask & timestamps. Folds kept separate
    so clean subsampling respects each fold's native time grid.

    De-standardization uses a SINGLE COMMON affine (mean y_sigma / y_median across
    folds), not per-fold scalars. The per-fold scalars are near-identical (spread
    ~1e-4 on ~1.25e-3) and a single global affine is the right caliber: it is
    correlation/rank preserving AND keeps relative fold weighting identical to
    pooling in standardized space, so pooled Pearson reproduces the standardized
    reference exactly (e.g. roll2026 = 0.0247) while q50/y sit in real return units
    so bias_bps is genuinely basis points. (A per-fold affine would reweight folds
    by their differing sigma and drift the pooled Pearson by ~4e-4.)"""
    fname = _ckpt_filename(ckpt)
    fold_files = sorted(glob.glob(p.join(model_dir, "fold_*", fname)))
    if not fold_files:
        raise FileNotFoundError(f"no {fname} under {model_dir}/fold_*")
    raw = []
    sigmas, medians = [], []
    for f in fold_files:
        z = np.load(f)
        q50_std = z["predictions"][:, 1].astype(np.float64)
        y_std = z["targets"].astype(np.float64)
        mask = z["mask"].astype(bool) if "mask" in z else np.ones(y_std.shape, bool)
        ts = z["timestamps"].astype(np.int64)
        sigmas.append(float(z["y_sigma"]) if "y_sigma" in z else 1.0)
        medians.append(float(z["y_median"]) if "y_median" in z else 0.0)
        raw.append((f, q50_std, y_std, mask, ts))
    ysig = float(np.mean(sigmas))   # common affine across folds
    ymed = float(np.mean(medians))
    folds = []
    for f, q50_std, y_std, mask, ts in raw:
        q50 = q50_std * ysig + ymed
        y = y_std * ysig + ymed
        valid = mask & np.isfinite(q50) & np.isfinite(y)
        folds.append({
            "fold": int(p.basename(p.dirname(f)).split("_")[1]),
            "q50": q50[valid], "y": y[valid], "ts": ts[valid],
        })
    return folds


def _month_label(ts_us):
    return dt.datetime.fromtimestamp(int(ts_us) / 1e6, dt.timezone.utc).strftime("%Y-%m")


def _months_array(ts):
    # vectorized month label via integer arithmetic on us->day is fiddly with
    # variable month lengths; use datetime per unique day for speed/correctness.
    ts = np.asarray(ts, dtype=np.int64)
    days = ts // 86_400_000_000  # us per day
    out = np.empty(ts.shape, dtype=object)
    for d in np.unique(days):
        lbl = dt.datetime.fromtimestamp(int(d) * 86400, dt.timezone.utc).strftime("%Y-%m")
        out[days == d] = lbl
    return out


def assemble(folds, sample):
    """Concatenate folds into q50,y,ts arrays for `sample` in {dense, clean}.

    clean: within each fold, subsample by ceil(600/median_gap) on time-sorted
    order so retained labels are >=600s apart; then concatenate across folds.
    """
    qs, ys, tss = [], [], []
    for fd in folds:
        q, y, ts = fd["q50"], fd["y"], fd["ts"]
        if sample == "clean":
            order = np.argsort(ts, kind="stable")
            q, y, ts = q[order], y[order], ts[order]
            factor = clean_subsample_factor(ts)
            q, y, ts = q[::factor], y[::factor], ts[::factor]
        qs.append(q); ys.append(y); tss.append(ts)
    if not qs:
        return np.array([]), np.array([]), np.array([], dtype=np.int64)
    return np.concatenate(qs), np.concatenate(ys), np.concatenate(tss).astype(np.int64)


def per_month_and_pooled(folds, sample):
    """Return {month: metrics, 'POOLED': metrics} for one sample caliber."""
    q, y, ts = assemble(folds, sample)
    out = {}
    if q.size == 0:
        return out
    months = _months_array(ts)
    for mo in sorted(set(months.tolist())):
        sel = months == mo
        out[mo] = compute_metrics(q[sel], y[sel])
    out["POOLED"] = compute_metrics(q, y)
    return out


# --------------------------------------------------------------------------- #
# rendering
# --------------------------------------------------------------------------- #
_COLS = ["n", "pearson", "spearman", "beta", "sigma_ratio", "monotonicity", "bias_bps"]
_HEAD = ["month", "regime", "N", "Pearson", "Spearman", "beta", "sig_r", "mono", "bias_bps"]


def _regime_tag(month):
    if month == "POOLED":
        return ""
    if month in STRONG_MONTHS:
        return "STRONG"
    if month.startswith("2026-"):
        return "choppy"
    return ""


def _fmt_row(month, m):
    def f(v, w, prec):
        return "nan".rjust(w) if (v is None or (isinstance(v, float) and not np.isfinite(v))) else f"{v:>{w}.{prec}f}"
    return (
        f"{month:<8}{_regime_tag(month):<8}{m['n']:>8d}"
        f"{f(m['pearson'],10,4)}{f(m['spearman'],10,4)}{f(m['beta'],9,3)}"
        f"{f(m['sigma_ratio'],8,4)}{f(m['mono'] if 'mono' in m else m['monotonicity'],7,2)}"
        f"{f(m['bias_bps'],11,4)}"
    )


def _header_line():
    return (f"{'month':<8}{'regime':<8}{'N':>8}{'Pearson':>10}{'Spearman':>10}"
            f"{'beta':>9}{'sig_r':>8}{'mono':>7}{'bias_bps':>11}")


def render_model(name, ckpt, by_sample):
    lines = [f"\n{'='*86}", f"MODEL: {name}   ckpt={ckpt}", "=" * 86]
    for sample in ("dense", "clean"):
        table = by_sample.get(sample, {})
        lines.append(f"\n[{sample.upper()}]  (raw y, masked"
                     + (f"; clean stride>={HORIZON_S}s)" if sample == "clean" else ")"))
        lines.append(_header_line())
        lines.append("-" * 86)
        months = [k for k in table if k != "POOLED"]
        for mo in sorted(months):
            lines.append(_fmt_row(mo, table[mo]))
        if "POOLED" in table:
            lines.append("-" * 86)
            lines.append(_fmt_row("POOLED", table["POOLED"]))
    return "\n".join(lines)


def render_delta(name_a, name_b, a_by_sample, b_by_sample, ckpt):
    """Pooled delta b - a (rolling - frozen) per sample."""
    lines = [f"\n{'#'*86}", f"FROZEN-vs-ROLLING DELTA  ({name_b} - {name_a})   ckpt={ckpt}", "#" * 86]
    for sample in ("dense", "clean"):
        a = a_by_sample.get(sample, {}).get("POOLED")
        b = b_by_sample.get(sample, {}).get("POOLED")
        if a is None or b is None:
            continue
        lines.append(f"\n[{sample.upper()}] pooled delta")
        lines.append(f"{'metric':<14}{name_a:>14}{name_b:>14}{'delta':>14}")
        lines.append("-" * 56)
        for key, lbl, prec in [("pearson", "Pearson", 4), ("spearman", "Spearman", 4),
                               ("beta", "beta", 3), ("sigma_ratio", "sigma_ratio", 4),
                               ("monotonicity", "monotonicity", 2), ("bias_bps", "bias_bps", 4)]:
            va, vb = a[key], b[key]
            d = (vb - va) if (np.isfinite(va) and np.isfinite(vb)) else float("nan")
            lines.append(f"{lbl:<14}{va:>14.{prec}f}{vb:>14.{prec}f}{d:>+14.{prec}f}")
    return "\n".join(lines)


# --------------------------------------------------------------------------- #
# CLI
# --------------------------------------------------------------------------- #
def run(dirs, names, ckpts):
    results = {}  # name -> ckpt -> {sample -> table}
    out_lines = []
    for d, nm in zip(dirs, names):
        results[nm] = {}
        for ckpt in ckpts:
            try:
                folds = load_model(d, ckpt)
            except FileNotFoundError as e:
                out_lines.append(f"[skip] {nm} ckpt={ckpt}: {e}")
                continue
            by_sample = {s: per_month_and_pooled(folds, s) for s in ("dense", "clean")}
            results[nm][ckpt] = by_sample
            out_lines.append(render_model(nm, ckpt, by_sample))

    # frozen-vs-rolling delta when exactly two models given
    if len(dirs) == 2:
        na, nb = names[0], names[1]
        for ckpt in ckpts:
            a = results.get(na, {}).get(ckpt)
            b = results.get(nb, {}).get(ckpt)
            if a and b:
                out_lines.append(render_delta(na, nb, a, b, ckpt))

    text = "\n".join(out_lines)
    print(text)
    return results, text


def main():
    ap = argparse.ArgumentParser(description="dual-caliber perp y_600 eval battery")
    ap.add_argument("--dirs", nargs="+", required=True, help="model result dirs")
    ap.add_argument("--names", nargs="+", required=True, help="display names (== len dirs)")
    ap.add_argument("--ckpt", choices=["ema", "best", "both"], default="ema",
                    help="which checkpoint preds to evaluate (default ema)")
    ap.add_argument("--json_out", default=None, help="optional path to dump metrics json")
    args = ap.parse_args()
    if len(args.dirs) != len(args.names):
        ap.error(f"--dirs ({len(args.dirs)}) and --names ({len(args.names)}) must match")
    ckpts = ["ema", "best"] if args.ckpt == "both" else [args.ckpt]

    results, _ = run(args.dirs, args.names, ckpts)

    if args.json_out:
        json.dump(results, open(args.json_out, "w"), indent=2, default=float)
        print(f"\nsaved metrics json -> {args.json_out}")


if __name__ == "__main__":
    main()
