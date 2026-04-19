# Comprehensive V4 vs Ridge/XGB Evaluation — Design Spec

**Date:** 2026-04-18  
**Phase:** A (current). Phase B (Savitzky-Golay feature work) follows.

## Goal

Produce a near-production-grade evaluation of the three alpha candidates (V4 noattn DL, Ridge, XGBoost) on the matched 3-fold walk-forward test set, covering dimensions that a discretionary/quant PM would ask for before production deployment — not just numeric correlation. Incorporate `docs/PROJECT_PRINCIPLES.md` principles 1, 2, 3, 4, 6, 7, 8.

## Non-goals

- Transaction cost sweep beyond flat bps
- Capacity / market impact modeling
- XGBoost hyperparameter tuning (use current defaults)
- Formal Probability of Backtest Overfitting test (reserved for Phase A2)
- Live paper trading (separate project)

## Architecture

Three stages, each writes artifacts so later stages can iterate:

### Stage 1 — Baseline prediction dump
Modify `src/baselines/evaluate_baselines.py`:
- Add CLI flag `--save-predictions <dir>`.
- When set, after each `(fold, model)` evaluation, save `{dir}/fold_{f}_{model}_preds.npz` with fields: `predictions` (N,), `targets` (N,), `mask` (N,), `timestamps` (N,).
- Backwards-compatible: no flag = current behavior.
- Re-run matched baseline on pod with flag set (~10 min).

### Stage 2 — Comprehensive eval script
New `scripts/comprehensive_eval.py`:
- **Input:**
  - `--v4-exp-dir experiments/v4_noattn_700d` — has `fold_{0,1,2}/test_preds.npz`
  - `--baseline-pred-dir experiments/baselines_v4_matched_preds` — has `fold_{f}_{model}_preds.npz`
  - `--feature-npz-dir data/npz_v4` — for regime features (rolling vol, hour-of-day)
  - `--output-dir experiments/eval_comprehensive`
- **Output:**
  - `metrics.json` — machine-readable full table
  - `REPORT.md` — human-readable summary with embedded plots
  - `figures/*.png` — 12 plots
  - `tables/summary.csv`, `tables/ensemble_weights.json`

### Stage 3 — Review + decide
User reads REPORT.md. Findings inform Phase B.

## 11 metric categories

| # | Category | Metrics | Plot | Principle |
|---|---|---|---|:-:|
| 1 | Core IC | Pearson, Spearman, Kendall τ × {per-fold, pooled} × {3 models} + bootstrapped 95% CI | `01_ic_with_ci.png` | 2 |
| 2 | Temporal stability | Day-by-day IC, IC-IR, rolling-7d IC | `02_temporal_ic.png` | 2, 8 |
| 3 | Autocorrelation | Prediction AC(1,5,30), residual AC, target AC | `03_autocorr.png` | - |
| 4 | Decile/Quantile returns | Mean fwd return per pred-decile, monotonicity test (Spearman(decile_idx, mean_return)), long-short spread | `04_decile_returns.png` | - |
| 5 | Regime conditional | IC split by low/mid/high `rolling_vol_5min`, by up/down past 1hr, by hour-of-day | `05_regime_heatmap.png` | 7 |
| 6 | Risk | Sharpe (HAC Newey-West), Sortino, max DD, CVaR-95%, hit rate by direction | `06_equity_drawdown.png` | 3 |
| 7 | Calibration (V4) | Actual coverage of q10 / q50 / q90 vs nominal; q10<q50<q90 violation rate | `07_calibration_v4.png` | - |
| 8 | Cross-model consistency | Pairwise Pearson between V4/Ridge/XGB predictions; flag > 0.8 | `08_cross_model_corr.png` | 6 |
| 9 | Confidence gating (V4) | τ-sweep on `|q50| / (q90-q10)`, Sharpe(τ*), trade_rate(τ*) | `09_confidence_gating.png` | 3 |
| 10 | DL attribution (V4) | OLS: q50 ≈ β·momentum + β·vol + β·hour + ε. Report R², Pearson(ε, y) | `10_attribution_v4.png` | 4 |
| 11 | Ensemble projection | Given ICs + pairwise corrs, Grinold-Kahn theoretical IR; optimal linear weights | `11_ensemble_projection.png` | 1 |
| + | Monthly concentration | Per-month Spearman on test period; flag top-20%-months contribute ≥60% pattern | `12_monthly_concentration.png` | 8 |

## Key design choices

- **Predictions-only eval** — script takes NPZ files, not models. Re-usable for any future architecture.
- **Trading signal = q50** for V4, raw prediction for Ridge/XGB.
- **Always report per-fold AND pooled** — metric-discipline.md requirement.
- **Bootstrapped CIs** use block bootstrap (block_len=60) to respect serial correlation, 1000 resamples.
- **Regime features** loaded from NPZ's last-timestep row: `rolling_vol_5min` for vol regime, past-hour log_return_60s sign for trend, `timestamps % 86400` for hour-of-day.
- **Confidence gating (V4 only)** — iterate τ ∈ {10 quantiles of `|q50|/(q90-q10)`}, compute Sharpe per τ, pick τ* maximizing Sharpe. Report Sharpe(τ=0) [baseline] AND Sharpe(τ*).
- **DL attribution OLS** — run on V4's q50 vs 5 simple regressors from input features; worry threshold R² > 0.8 (V4 is mostly momentum) or residual-Pearson < 0.03 (DL adds nothing).
- **Ensemble projection** — Clarke-de Silva-Thorley formula: given IC vector `r`, covariance `Σ`, optimal weights `w = Σ⁻¹r / (1'Σ⁻¹r)`, combined IC = `√(r' Σ⁻¹ r)`.
- **Monthly concentration** — compute per-month Spearman on test period, compute gini-like concentration index; > 0.5 = flag.

## Data flow

```
Pod (re-run baseline with --save-predictions):
  experiments/baselines_v4_matched_preds/
    fold_0_Ridge_preds.npz, fold_0_XGBoost_preds.npz
    fold_1_Ridge_preds.npz, fold_1_XGBoost_preds.npz
    fold_2_Ridge_preds.npz, fold_2_XGBoost_preds.npz
  
Rsync to local

Local (run comprehensive_eval.py):
  Reads V4 test_preds.npz × 3 folds + baseline preds × 6 files
  For regime features: reads last-timestep of each test-day NPZ
  Writes experiments/eval_comprehensive/{metrics.json, REPORT.md, figures/*.png}
```

## Testing

- Unit test for each metric category using synthetic data with known expected values:
  - `test_ic_with_known_correlation`: inject gaussian with corr=0.3, assert measured corr within [0.28, 0.32]
  - `test_decile_monotonic`: inject monotonic decile means, assert test passes
  - `test_calibration_perfect_quantiles`: inject oracle quantiles, assert coverage matches nominal
  - `test_ensemble_projection_correct_formula`: two-model case with known answer
- Integration smoke test: use one fold's worth of synthetic preds, assert REPORT.md generated and ≥ 12 figures present.

## Deliverables checklist

- [ ] `src/baselines/evaluate_baselines.py` has `--save-predictions` flag (with unit test)
- [ ] Pod baseline re-run with flag, 6 preds files created
- [ ] Rsync preds files to local
- [ ] `scripts/comprehensive_eval.py` implementing all 11 categories
- [ ] 12 figures generated
- [ ] `REPORT.md` with embedded plots + narrative summary
- [ ] `metrics.json` + `tables/*.csv`
- [ ] Memory entry capturing key findings

## Time estimate

~2 days. Stage 1: 2 hours. Stage 2: 1.5 days. Stage 3: 0.5 days (review + writeup).
