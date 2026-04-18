"""Aggregate walk-forward fold results into single-scalar summaries.

Given an experiments directory with per-fold subfolders (``fold_0/``, ``fold_1/``,
...) containing ``test_preds.npz`` + ``test_results.json`` + ``metrics.json``,
produce:
  1. Per-fold table (val_corr, test_corr, Sharpe, PnL) for inspection.
  2. Pooled OOS IC across all test predictions concatenated.
  3. Mean ± std of per-fold IC (Information Ratio = mean/std).
  4. Statistical significance test (t-test on fold IC vs 0).
  5. Backtest aggregates (net PnL, Sharpe, max drawdown) across pooled PnL.

CLI
---
    python scripts/aggregate_folds.py \\
        --exp-dir experiments/v3_revin \\
        --out experiments/v3_revin/SUMMARY.json \\
        --baseline-corr 0.099

``--baseline-corr`` is optional but recommended — prints ``V3 vs Ridge delta``
per fold and pooled.
"""
from __future__ import annotations

import argparse
import json
import math
from pathlib import Path
from typing import Any, Dict, List, Optional

import numpy as np


def _safe_json_load(path: Path) -> Optional[dict]:
    try:
        return json.loads(path.read_text())
    except (FileNotFoundError, json.JSONDecodeError):
        return None


def _load_fold(fold_dir: Path) -> Optional[Dict[str, Any]]:
    """Load one fold's artefacts; returns None if incomplete."""
    metrics = _safe_json_load(fold_dir / "metrics.json")
    test_results = _safe_json_load(fold_dir / "test_results.json")
    preds_path = fold_dir / "test_preds.npz"
    if metrics is None or test_results is None or not preds_path.exists():
        return None
    try:
        npz = np.load(str(preds_path), allow_pickle=True)
        predictions = np.asarray(npz["predictions"])  # (N, n_quantiles) or (N,)
        targets = np.asarray(npz["targets"])
        mask = np.asarray(npz["mask"]).astype(bool)
        y_sigma = float(npz["y_sigma"]) if "y_sigma" in npz.files else 1.0
        y_median = float(npz["y_median"]) if "y_median" in npz.files else 0.0
    except Exception:
        return None
    # point prediction = q50 (index 1) if multi-quantile, else predictions
    if predictions.ndim == 2 and predictions.shape[-1] >= 3:
        point_pred = predictions[:, 1]
    else:
        point_pred = predictions.ravel()
    return {
        "fold_dir": fold_dir.name,
        "metrics": metrics,
        "test_results": test_results,
        "point_pred": point_pred,
        "targets": targets,
        "mask": mask,
        "y_sigma": y_sigma,
        "y_median": y_median,
    }


def _safe_corr(a: np.ndarray, b: np.ndarray) -> float:
    if a.size < 2 or np.std(a) == 0 or np.std(b) == 0:
        return float("nan")
    return float(np.corrcoef(a, b)[0, 1])


def aggregate(exp_dir: Path, baseline_corr: Optional[float] = None) -> Dict[str, Any]:
    fold_dirs = sorted(p for p in exp_dir.iterdir() if p.is_dir() and p.name.startswith("fold_"))
    if not fold_dirs:
        raise RuntimeError(f"No fold_* subdirectories found in {exp_dir}")

    folds: List[Dict[str, Any]] = []
    for fd in fold_dirs:
        f = _load_fold(fd)
        if f is None:
            print(f"  [skip] {fd.name}: missing artefacts")
            continue
        folds.append(f)

    if not folds:
        raise RuntimeError("No complete folds found")

    # --- per-fold metrics table ---------------------------------------------
    per_fold: List[Dict[str, Any]] = []
    fold_test_corrs: List[float] = []
    fold_test_rank_corrs: List[float] = []
    for f in folds:
        pred = f["point_pred"][f["mask"]]
        tgt = f["targets"][f["mask"]]
        test_corr = _safe_corr(pred, tgt)
        # Per-fold Spearman (rank IC) — see docs/METRIC_DISCIPLINE.md
        test_rank_corr = (
            _safe_corr(
                np.argsort(np.argsort(pred)).astype(float),
                np.argsort(np.argsort(tgt)).astype(float),
            )
            if pred.size > 1 else float("nan")
        )
        # Direction accuracy (hygiene)
        dir_acc = float(np.mean(np.sign(pred) == np.sign(tgt))) if pred.size else float("nan")
        fold_test_corrs.append(test_corr)
        fold_test_rank_corrs.append(test_rank_corr)
        row = {
            "fold": f["fold_dir"],
            "val_corr": f["metrics"].get("val_corr"),
            "val_r2": f["metrics"].get("val_r2"),
            "best_epoch": f["metrics"].get("best_epoch"),
            "test_corr": test_corr,           # Pearson (spec bar)
            "test_rank_corr": test_rank_corr, # Spearman (trading primary)
            "test_direction_acc": dir_acc,
            "test_n": int(f["mask"].sum()),
            "test_sharpe_annual": f["test_results"].get("sharpe_annual"),
            "test_net_pnl_bps": f["test_results"].get("net_pnl_bps"),
            "test_max_drawdown_bps": f["test_results"].get("max_drawdown_bps"),
            "test_win_rate": f["test_results"].get("win_rate"),
            "test_trade_rate": f["test_results"].get("trade_rate"),
        }
        if baseline_corr is not None and test_corr == test_corr:  # not NaN
            row["delta_vs_baseline"] = test_corr - baseline_corr
        per_fold.append(row)

    # --- pooled OOS IC ------------------------------------------------------
    all_pred = np.concatenate([f["point_pred"][f["mask"]] for f in folds])
    all_tgt = np.concatenate([f["targets"][f["mask"]] for f in folds])
    pooled_corr = _safe_corr(all_pred, all_tgt)

    # Rank correlation (Spearman via argsort ranks — no scipy needed)
    pred_rank = np.argsort(np.argsort(all_pred))
    tgt_rank = np.argsort(np.argsort(all_tgt))
    pooled_rank_corr = _safe_corr(pred_rank.astype(float), tgt_rank.astype(float))

    # Pooled R2
    ss_res = float(np.sum((all_tgt - all_pred) ** 2))
    ss_tot = float(np.sum((all_tgt - all_tgt.mean()) ** 2))
    pooled_r2 = 1.0 - ss_res / max(ss_tot, 1e-12)

    # --- mean ± std across folds -------------------------------------------
    finite_fold_corrs = [c for c in fold_test_corrs if c == c]  # NaN filter
    fold_mean = float(np.mean(finite_fold_corrs)) if finite_fold_corrs else float("nan")
    fold_std = float(np.std(finite_fold_corrs, ddof=1)) if len(finite_fold_corrs) > 1 else float("nan")
    ic_ir = fold_mean / fold_std if (fold_std == fold_std and fold_std > 1e-12) else float("nan")

    # t-test on fold IC vs 0
    n_folds = len(finite_fold_corrs)
    if n_folds > 1 and fold_std > 1e-12:
        t_stat = fold_mean * math.sqrt(n_folds) / fold_std
        # Two-sided p-value via t-distribution approximation
        # For n_folds = 8, df = 7. Use scipy if available, else approximation.
        try:
            from scipy import stats
            p_value = 2 * (1.0 - stats.t.cdf(abs(t_stat), df=n_folds - 1))
        except ImportError:
            # Crude: use normal approx (slight over-conservative for small df)
            from math import erf
            p_value = 2 * (1.0 - 0.5 * (1 + erf(abs(t_stat) / math.sqrt(2))))
    else:
        t_stat = float("nan")
        p_value = float("nan")

    # --- pooled backtest ----------------------------------------------------
    # Sum per-fold PnL and costs
    net_pnl_bps = sum(f["test_results"].get("net_pnl_bps", 0.0) or 0.0 for f in folds)
    gross_pnl_bps = sum(f["test_results"].get("gross_pnl_bps", 0.0) or 0.0 for f in folds)
    total_cost_bps = sum(f["test_results"].get("total_cost_bps", 0.0) or 0.0 for f in folds)
    n_trades_pooled = sum(int(f["test_results"].get("n_trades", 0) or 0) for f in folds)
    n_periods_pooled = sum(int(f["test_results"].get("n_periods", 0) or 0) for f in folds)

    # Weighted mean Sharpe across folds (by test_n)
    sharpes = []
    weights = []
    for f in folds:
        s = f["test_results"].get("sharpe_annual")
        n = int(f["mask"].sum())
        if s is not None and s == s:  # NaN filter
            sharpes.append(s)
            weights.append(n)
    weighted_sharpe = (
        float(np.average(sharpes, weights=weights))
        if sharpes else float("nan")
    )

    # --- assemble ----------------------------------------------------------
    summary = {
        "exp_dir": str(exp_dir),
        "n_folds_complete": n_folds,
        "n_folds_total": len(fold_dirs),
        "baseline_corr": baseline_corr,
        "per_fold": per_fold,
        "pooled": {
            "correlation": pooled_corr,
            "rank_correlation": pooled_rank_corr,
            "r2": pooled_r2,
            "n_samples": int(all_pred.size),
        },
        "cross_fold": {
            "mean_corr": fold_mean,
            "std_corr": fold_std,
            "ic_ir": ic_ir,
            "t_stat": t_stat,
            "p_value": p_value,
            "significant_at_p05": bool(p_value == p_value and p_value < 0.05),
        },
        "pooled_backtest": {
            "total_net_pnl_bps": net_pnl_bps,
            "total_gross_pnl_bps": gross_pnl_bps,
            "total_cost_bps": total_cost_bps,
            "n_trades": n_trades_pooled,
            "n_periods": n_periods_pooled,
            "weighted_avg_sharpe": weighted_sharpe,
        },
    }
    if baseline_corr is not None:
        summary["pooled"]["delta_vs_baseline"] = (
            pooled_corr - baseline_corr if pooled_corr == pooled_corr else float("nan")
        )
        summary["cross_fold"]["mean_delta_vs_baseline"] = (
            fold_mean - baseline_corr if fold_mean == fold_mean else float("nan")
        )
    return summary


def _format_report(summary: Dict[str, Any]) -> str:
    out: List[str] = []
    out.append("=" * 78)
    out.append(f"Walk-forward aggregate: {summary['exp_dir']}")
    out.append(f"Folds complete: {summary['n_folds_complete']} / {summary['n_folds_total']}")
    if summary.get("baseline_corr") is not None:
        out.append(f"Baseline correlation (Ridge): {summary['baseline_corr']:.4f}")
    out.append("")
    # Per-fold table
    out.append(f"{'Fold':<10s} {'ValCorr':>9s} {'TestCorr':>9s} {'TestN':>7s} "
               f"{'Sharpe':>8s} {'NetPnL(bps)':>12s} {'TradeRate':>10s}")
    out.append("-" * 78)
    for r in summary["per_fold"]:
        vc = r["val_corr"]; tc = r["test_corr"]
        sh = r["test_sharpe_annual"]; pn = r["test_net_pnl_bps"]; tr = r["test_trade_rate"]
        out.append(
            f"{r['fold']:<10s} "
            f"{(vc if vc is not None else 0):>+9.4f} "
            f"{(tc if tc == tc else 0):>+9.4f} "
            f"{r['test_n']:>7d} "
            f"{(sh if sh is not None and sh == sh else 0):>+8.2f} "
            f"{(pn if pn is not None else 0):>+12.1f} "
            f"{(tr if tr is not None else 0):>10.2%}"
        )
    out.append("-" * 78)
    # Pooled / cross-fold
    p = summary["pooled"]; cf = summary["cross_fold"]; pb = summary["pooled_backtest"]
    out.append("")
    out.append(f"Pooled OOS IC (all {p['n_samples']} test samples concatenated):")
    out.append(f"  Pearson corr:     {p['correlation']:+.4f}")
    out.append(f"  Spearman corr:    {p['rank_correlation']:+.4f}")
    out.append(f"  R²:               {p['r2']:+.4f}")
    if "delta_vs_baseline" in p:
        out.append(f"  Δ vs Ridge:       {p['delta_vs_baseline']:+.4f}")
    out.append("")
    out.append(f"Cross-fold stability:")
    out.append(f"  Mean fold corr:   {cf['mean_corr']:+.4f}")
    out.append(f"  Std fold corr:    {cf['std_corr']:.4f}")
    out.append(f"  IC-IR:            {cf['ic_ir']:+.2f}")
    out.append(f"  t-statistic:      {cf['t_stat']:+.2f}")
    out.append(f"  p-value (vs 0):   {cf['p_value']:.4f}  "
               f"{'[significant]' if cf['significant_at_p05'] else '[not significant]'}")
    out.append("")
    out.append(f"Pooled backtest:")
    out.append(f"  Gross PnL:        {pb['total_gross_pnl_bps']:+.1f} bps")
    out.append(f"  Costs:            {pb['total_cost_bps']:.1f} bps")
    out.append(f"  Net PnL:          {pb['total_net_pnl_bps']:+.1f} bps")
    out.append(f"  Trades:           {pb['n_trades']:,} across {pb['n_periods']:,} periods")
    out.append(f"  Weighted Sharpe:  {pb['weighted_avg_sharpe']:+.2f}")
    out.append("=" * 78)
    return "\n".join(out)


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--exp-dir", required=True, help="Directory containing fold_* subfolders")
    ap.add_argument("--out", help="Optional JSON output path")
    ap.add_argument("--baseline-corr", type=float, default=None,
                    help="Baseline (e.g. Ridge) correlation for delta calculation")
    args = ap.parse_args()

    summary = aggregate(Path(args.exp_dir), baseline_corr=args.baseline_corr)
    print(_format_report(summary))
    if args.out:
        Path(args.out).parent.mkdir(parents=True, exist_ok=True)
        Path(args.out).write_text(json.dumps(summary, indent=2, default=str))
        print(f"\nJSON summary written to {args.out}")


if __name__ == "__main__":
    main()
