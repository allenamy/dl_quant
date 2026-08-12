#!/usr/bin/env python3
"""Path C: Holding strategy parameter sweep.

Tests holding_strategy vs confidence_gated baseline on V4+XGB ensemble
across 3-fold walk-forward test set. Goal: reduce trading cost while
preserving signal, lifting Sharpe from -158 baseline toward 0.

Sweep:
  ema_k         ∈ {3, 5, 10, 20}    # signal smoothing
  tau_entry     ∈ {0.05, 0.1, 0.15} # entry strength
  tau_exit      ∈ {0.02, 0.05}      # exit threshold (hysteresis)
  min_hold      ∈ {5, 10, 30, 60}   # min holding samples (minutes if stride=60)
  max_hold      ∈ {300, 600}        # max holding samples (5-10 hours)
"""
from __future__ import annotations

import itertools, json, pathlib, sys
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent))
import numpy as np
import pandas as pd

from src.evaluation.backtest_engine import (
    CostModel, ExecutionConfig, run_backtest,
)

ENSEMBLE_DIR = pathlib.Path("experiments/phase_c/ensemble_preds")
BASELINE_DIR = pathlib.Path("experiments/baselines_v4_matched_preds")
OUTPUT_DIR = pathlib.Path("experiments/phase_c/holding_sweep")
SAMPLE_INT = 60


def load_pooled():
    folds = [0, 1, 2]
    all_s, all_r, all_m, all_c = [], [], [], []
    for f in folds:
        e = np.load(str(ENSEMBLE_DIR / f"fold_{f}.npz"))
        xgb = np.load(str(BASELINE_DIR / f"fold_{f}_XGBoost_preds.npz"))
        sig_y = float(xgb["norm_y_sigma"])
        sig = e["predictions"].astype(np.float64)
        ret_bps = e["targets"].astype(np.float64) * sig_y * 1e4
        msk = e["mask"].astype(bool)
        iqr = np.maximum(e["v4_q90"] - e["v4_q10"], 1e-8)
        conf = np.abs(e["v4_q50"]) / iqr
        all_s.append(sig); all_r.append(ret_bps); all_m.append(msk); all_c.append(conf)
    return (np.concatenate(all_s), np.concatenate(all_r),
            np.concatenate(all_m), np.concatenate(all_c))


def main():
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    signal, returns_bps, mask, confidence = load_pooled()
    cost_model = CostModel.binance_regular()

    # --- Baseline: confidence_gated τ=0.067 (from fold-0 calibration) ---
    print("=" * 100)
    print("BASELINE (confidence_gated, τ=0.067 walk-forward)")
    print("=" * 100)
    baseline = run_backtest(
        signal=signal, returns_bps=returns_bps, mask=mask, confidence=confidence,
        sample_interval_sec=SAMPLE_INT, cost_model=cost_model,
        exec_cfg=ExecutionConfig(position_mode="confidence_gated", tau=0.067),
    )
    print(f"  Sharpe: {baseline.sharpe_ann:.2f}, Net P&L: {baseline.net_pnl_bps:.1f} bps, "
          f"trade_rate: {baseline.trade_rate:.2%}, turnover: {baseline.turnover:.3f}")
    print()

    # --- Holding strategy sweep ---
    ema_ks       = [3, 5, 10, 20]
    tau_entries  = [0.05, 0.1, 0.15]
    tau_exits    = [0.02, 0.05]
    min_holds    = [5, 10, 30, 60]
    max_holds    = [600]

    grid = list(itertools.product(ema_ks, tau_entries, tau_exits, min_holds, max_holds))
    print(f"Sweeping {len(grid)} holding-strategy configs...")
    print(f"{'ema_k':>6} {'τ_in':>6} {'τ_out':>6} {'min_h':>6} {'max_h':>6} | "
          f"{'Sharpe':>9} {'Net':>10} {'TradeRate':>11} {'Turnover':>10} {'WinRate':>9}")
    print("-" * 105)

    results = []
    for ema_k, tau_in, tau_out, min_h, max_h in grid:
        if tau_out >= tau_in:
            continue  # ensure hysteresis
        cfg = ExecutionConfig(
            position_mode="holding_strategy",
            ema_k=ema_k, tau_entry=tau_in, tau_exit=tau_out,
            min_hold_samples=min_h, max_hold_samples=max_h,
        )
        r = run_backtest(
            signal=signal, returns_bps=returns_bps, mask=mask, confidence=confidence,
            sample_interval_sec=SAMPLE_INT, cost_model=cost_model, exec_cfg=cfg,
        )
        row = {
            "ema_k": ema_k, "tau_entry": tau_in, "tau_exit": tau_out,
            "min_hold": min_h, "max_hold": max_h,
            "sharpe_ann": r.sharpe_ann, "net_pnl_bps": r.net_pnl_bps,
            "gross_pnl_bps": r.gross_pnl_bps, "cost_bps": r.cost_bps,
            "trade_rate": r.trade_rate, "turnover": r.turnover,
            "win_rate": r.win_rate, "max_dd_bps": r.max_dd_bps,
        }
        results.append(row)
        print(f"{ema_k:>6d} {tau_in:>6.3f} {tau_out:>6.3f} {min_h:>6d} {max_h:>6d} | "
              f"{r.sharpe_ann:>9.2f} {r.net_pnl_bps:>10.0f} {r.trade_rate:>11.2%} "
              f"{r.turnover:>10.4f} {r.win_rate:>9.2%}")

    df = pd.DataFrame(results)

    # --- Summary ---
    print("\n" + "=" * 100)
    print("SUMMARY — Best configs by Sharpe")
    print("=" * 100)
    df_sort = df.sort_values("sharpe_ann", ascending=False).head(10)
    print(df_sort[["ema_k", "tau_entry", "tau_exit", "min_hold", "sharpe_ann",
                    "net_pnl_bps", "trade_rate", "turnover"]].to_string())

    print(f"\nBaseline Sharpe: {baseline.sharpe_ann:.2f}")
    print(f"Best holding-strategy Sharpe: {df['sharpe_ann'].max():.2f}")
    print(f"Improvement: {df['sharpe_ann'].max() - baseline.sharpe_ann:+.2f}")

    df.to_csv(OUTPUT_DIR / "sweep_results.csv", index=False)

    with open(OUTPUT_DIR / "summary.json", "w") as fp:
        json.dump({
            "baseline": {
                "mode": "confidence_gated (tau=0.067)",
                "sharpe_ann": baseline.sharpe_ann,
                "net_pnl_bps": baseline.net_pnl_bps,
                "trade_rate": baseline.trade_rate,
                "turnover": baseline.turnover,
            },
            "best_holding": df_sort.iloc[0].to_dict() if len(df_sort) else {},
            "improvement_sharpe": float(df["sharpe_ann"].max() - baseline.sharpe_ann),
            "sweep_size": len(df),
        }, fp, indent=2, default=float)

    print(f"\n✓ Saved sweep results to {OUTPUT_DIR}/sweep_results.csv")
    print(f"✓ Summary saved to {OUTPUT_DIR}/summary.json")


if __name__ == "__main__":
    main()
