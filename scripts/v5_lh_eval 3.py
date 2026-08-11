#!/usr/bin/env python3
"""V5-LH comprehensive evaluation.

Aggregates per-(fold, seed) test predictions produced by `v5_lh_train.py`
into pooled metrics and a Markdown report.

Highlights:
  - Seed ensemble via median across seeds per fold
  - Clean y_600 metrics: subsample every 10th sample (stride 60→600) for
    honest non-overlapping IC (plan §7.3)
  - Pearson + Spearman + direction accuracy (METRIC_DISCIPLINE)
  - V5-LH × V4 ensemble (equal-weight pooled) when V4 predictions are
    provided via --v4-preds-dir
  - Gate check: y_600 Pearson ≥ 0.07, Spearman ≥ 0.08, non-regression on
    y_180 if two-horizon training was done

Usage:
  python3 scripts/v5_lh_eval.py --exp-dir experiments/v5_lh \
      --output-dir experiments/v5_lh/eval [--v4-preds-dir experiments/v4_noattn_700d]
"""
from __future__ import annotations

import argparse
import json
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent))

import numpy as np
from scipy.stats import pearsonr, spearmanr


SEEDS = (1, 2, 3)
FOLDS = (0, 1, 2)


def _load_seed_ensemble(exp_dir: pathlib.Path, fold: int, horizon: int, seeds=SEEDS):
    """Load per-seed test preds for a (fold, horizon) and median-ensemble q50.

    Returns: (p_median, p_std, y, mask, y_sigma). Missing seed files are
    silently skipped; returns None if nothing loaded.
    """
    preds = []
    y = None
    mask = None
    y_sigma = None
    for s in seeds:
        f = exp_dir / f"fold_{fold}_seed{s}" / f"test_preds_y{horizon}.npz"
        if not f.exists():
            continue
        d = np.load(str(f))
        preds.append(d["predictions"][:, 1])  # q50
        if y is None:
            y = d["targets"]
            mask = d["mask"].astype(bool)
            y_sigma = float(d["y_sigma"]) if "y_sigma" in d.files else 1.0
    if not preds:
        return None
    preds = np.stack(preds, axis=0)
    p_median = np.median(preds, axis=0)
    p_std = np.std(preds, axis=0) if len(preds) > 1 else np.zeros_like(p_median)
    return p_median, p_std, y, mask, y_sigma


def _clean_metrics(p: np.ndarray, y: np.ndarray, mask: np.ndarray, stride_every: int = 10):
    """Clean-stride subsample then compute Pearson/Spearman/direction accuracy."""
    m = mask.copy()
    sub = np.zeros_like(m)
    sub[::stride_every] = True
    sel = m & sub & np.isfinite(p) & np.isfinite(y)
    p_s = p[sel]
    y_s = y[sel]
    if len(p_s) < 30:
        return {"pearson": float("nan"), "spearman": float("nan"),
                "dir_acc": float("nan"), "n": int(len(p_s))}
    return {
        "pearson": float(pearsonr(p_s, y_s)[0]),
        "spearman": float(spearmanr(p_s, y_s)[0]),
        "dir_acc": float((np.sign(p_s) == np.sign(y_s)).mean()),
        "n": int(len(p_s)),
    }


def _dense_metrics(p: np.ndarray, y: np.ndarray, mask: np.ndarray):
    sel = mask.astype(bool) & np.isfinite(p) & np.isfinite(y)
    p_s = p[sel]
    y_s = y[sel]
    if len(p_s) < 30:
        return {"pearson": float("nan"), "spearman": float("nan"),
                "dir_acc": float("nan"), "n": int(len(p_s))}
    return {
        "pearson": float(pearsonr(p_s, y_s)[0]),
        "spearman": float(spearmanr(p_s, y_s)[0]),
        "dir_acc": float((np.sign(p_s) == np.sign(y_s)).mean()),
        "n": int(len(p_s)),
    }


def _load_v4_pooled(v4_dir: pathlib.Path, folds=FOLDS):
    """Load V4 q50 preds + targets pooled across folds (for ensemble)."""
    all_p, all_y, all_m = [], [], []
    for f in folds:
        path = v4_dir / f"fold_{f}" / "test_preds.npz"
        if not path.exists():
            return None
        d = np.load(str(path))
        # V4 stores shape (N, 3) for quantiles or (N,) for point
        if d["predictions"].ndim == 2:
            p = d["predictions"][:, 1]
        else:
            p = d["predictions"]
        all_p.append(p)
        all_y.append(d["targets"])
        all_m.append(d["mask"].astype(bool))
    return (np.concatenate(all_p), np.concatenate(all_y), np.concatenate(all_m))


def _standardize(x: np.ndarray) -> np.ndarray:
    return (x - x.mean()) / (x.std() + 1e-12)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--exp-dir", type=pathlib.Path, default=pathlib.Path("experiments/v5_lh"))
    ap.add_argument("--output-dir", type=pathlib.Path, default=pathlib.Path("experiments/v5_lh/eval"))
    ap.add_argument("--v4-preds-dir", type=pathlib.Path, default=None,
                    help="V4 predictions directory for ensemble comparison "
                         "(e.g. experiments/v4_noattn_700d). Optional.")
    ap.add_argument("--horizons", nargs="+", type=int, default=[600],
                    help="Horizons to evaluate (should match what trainer produced)")
    args = ap.parse_args()

    args.output_dir.mkdir(parents=True, exist_ok=True)
    results: dict = {"per_fold": {}, "pooled": {}, "v5_lh_plus_v4": {}}

    for horizon in args.horizons:
        # Clean subsample stride: y_600 → stride 10 (600 sec non-overlap),
        # y_180 → stride 3 (180 sec non-overlap), y_300 → stride 5.
        stride = max(1, horizon // 60)

        per_fold_clean = {}
        per_fold_dense = {}
        pooled_p, pooled_y, pooled_m = [], [], []
        for fold in FOLDS:
            loaded = _load_seed_ensemble(args.exp_dir, fold, horizon)
            if loaded is None:
                print(f"[eval] y_{horizon} fold {fold}: NO DATA", file=sys.stderr)
                continue
            p, p_std, y, mask, y_sigma = loaded
            clean = _clean_metrics(p, y, mask, stride_every=stride)
            dense = _dense_metrics(p, y, mask)
            per_fold_clean[fold] = clean
            per_fold_dense[fold] = dense
            print(f"y_{horizon} fold {fold} CLEAN: P={clean['pearson']:.4f} "
                  f"S={clean['spearman']:.4f} DA={clean['dir_acc']:.4f} N={clean['n']:,}")
            pooled_p.append(p[mask])
            pooled_y.append(y[mask])
            pooled_m.append(np.ones(int(mask.sum()), dtype=bool))

        if not pooled_p:
            print(f"[eval] y_{horizon}: no data across any fold")
            continue

        all_p = np.concatenate(pooled_p)
        all_y = np.concatenate(pooled_y)
        all_m = np.concatenate(pooled_m)
        pooled_clean = _clean_metrics(all_p, all_y, all_m, stride_every=stride)
        pooled_dense = _dense_metrics(all_p, all_y, all_m)

        results["per_fold"][horizon] = {"clean": per_fold_clean, "dense": per_fold_dense}
        results["pooled"][horizon] = {"clean": pooled_clean, "dense": pooled_dense}
        print(f"y_{horizon} POOLED CLEAN: P={pooled_clean['pearson']:.4f} "
              f"S={pooled_clean['spearman']:.4f} DA={pooled_clean['dir_acc']:.4f} "
              f"N={pooled_clean['n']:,}")

        # Optional V5-LH × V4 ensemble (on y_600 or equivalent)
        if args.v4_preds_dir is not None and horizon in (180, 600):
            v4 = _load_v4_pooled(args.v4_preds_dir)
            if v4 is not None:
                v4_p, v4_y, v4_m = v4
                # Align: V4 and V5-LH have DIFFERENT indexing because V5-LH
                # drops first ~20 windows per day. We cannot ensemble
                # point-wise without re-aligning. A simpler proxy: pool both
                # separately, standardize, and compute correlation of
                # rank-agreement. Full ensemble would need timestamp matching
                # (future work).
                if len(v4_p) == len(all_p):
                    # Lucky alignment (same fold structure + same filtered indices)
                    ens_p = 0.5 * _standardize(all_p) + 0.5 * _standardize(v4_p)
                    ens_metrics = _dense_metrics(ens_p, all_y, all_m)
                    results["v5_lh_plus_v4"][horizon] = ens_metrics
                    print(f"y_{horizon} ENSEMBLE (50/50 V5-LH+V4): "
                          f"P={ens_metrics['pearson']:.4f} S={ens_metrics['spearman']:.4f}")
                else:
                    results["v5_lh_plus_v4"][horizon] = {
                        "note": f"length mismatch: V5-LH={len(all_p)} V4={len(v4_p)} — "
                                f"ensemble requires per-timestamp alignment (not done)"
                    }

    # Gate check
    primary = 600 if 600 in args.horizons else max(args.horizons)
    if primary in results["pooled"]:
        p600 = results["pooled"][primary]["clean"]["pearson"]
        s600 = results["pooled"][primary]["clean"]["spearman"]
    else:
        p600 = float("nan")
        s600 = float("nan")
    gates = {
        "primary_y600_pearson_ge_0.07": bool(p600 >= 0.07),
        "secondary_y600_spearman_ge_0.08": bool(s600 >= 0.08),
    }
    if 180 in results["pooled"]:
        p180 = results["pooled"][180]["clean"]["pearson"]
        gates["nonregression_y180_pearson_ge_0.08"] = bool(p180 >= 0.08)
    results["gates"] = gates
    results["verdict"] = "PASS" if all(gates.values()) else "FAIL"

    # Write metrics
    with open(args.output_dir / "metrics.json", "w") as f:
        json.dump(results, f, indent=2, default=float)

    # Report
    lines = ["# V5-LH Evaluation Report", ""]
    lines.append(f"**Verdict:** {results['verdict']}\n")
    lines.append("## Pooled metrics (clean subsample — non-overlapping)\n")
    lines.append("| Horizon | Pearson | Spearman | DirAcc | N |")
    lines.append("|---|---:|---:|---:|---:|")
    for h in args.horizons:
        if h not in results["pooled"]:
            continue
        p = results["pooled"][h]["clean"]
        lines.append(f"| y_{h} | {p['pearson']:.4f} | {p['spearman']:.4f} | "
                     f"{p['dir_acc']:.4f} | {p['n']:,} |")

    lines.append("\n## Pooled metrics (dense — for reference, includes overlap)\n")
    lines.append("| Horizon | Pearson | Spearman | DirAcc | N |")
    lines.append("|---|---:|---:|---:|---:|")
    for h in args.horizons:
        if h not in results["pooled"]:
            continue
        p = results["pooled"][h]["dense"]
        lines.append(f"| y_{h} | {p['pearson']:.4f} | {p['spearman']:.4f} | "
                     f"{p['dir_acc']:.4f} | {p['n']:,} |")

    if results["v5_lh_plus_v4"]:
        lines.append("\n## V5-LH × V4 Ensemble (equal-weight standardized)\n")
        lines.append("| Horizon | Pearson | Spearman | DirAcc | N | Note |")
        lines.append("|---|---:|---:|---:|---:|---|")
        for h, e in results["v5_lh_plus_v4"].items():
            if "note" in e:
                lines.append(f"| y_{h} | — | — | — | — | {e['note']} |")
            else:
                lines.append(f"| y_{h} | {e['pearson']:.4f} | {e['spearman']:.4f} | "
                             f"{e['dir_acc']:.4f} | {e['n']:,} | |")

    lines.append("\n## Per-fold details (clean)\n")
    for h in args.horizons:
        if h not in results["per_fold"]:
            continue
        lines.append(f"\n### y_{h}\n")
        lines.append("| Fold | Pearson | Spearman | DirAcc | N |")
        lines.append("|---:|---:|---:|---:|---:|")
        for fold, m in results["per_fold"][h]["clean"].items():
            lines.append(f"| {fold} | {m['pearson']:.4f} | {m['spearman']:.4f} | "
                         f"{m['dir_acc']:.4f} | {m['n']:,} |")

    lines.append("\n## Gates\n")
    for k, v in gates.items():
        mark = "PASS" if v else "FAIL"
        lines.append(f"- `{k}`: {mark}")

    (args.output_dir / "REPORT.md").write_text("\n".join(lines))

    print(f"\n✓ Eval complete: {args.output_dir}/REPORT.md")
    print(f"✓ Verdict: {results['verdict']}")


if __name__ == "__main__":
    main()
