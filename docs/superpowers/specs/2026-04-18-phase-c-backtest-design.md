# Phase C — Comprehensive V4+XGB Ensemble Backtest

**Date:** 2026-04-18
**Scope:** Full production-grade backtest with strict no-leakage discipline.
**Supersedes:** `src/evaluation/backtest.py` (naive), `src/evaluation/backtest_v2.py` (partial).
**Related:** Phase A eval `experiments/eval_comprehensive/`, HORIZON_DECISION.md

## Terminology Lock-In

| Term | Refers to |
|---|---|
| **V4** | DL model (DualPathLOBModelV3 class, noattn config, y_180 horizon) — the "V4" label is definitive; class name "V3" is code-gen artifact |
| **Ensemble** | V4 + XGBoost Grinold-Kahn optimal weighting |
| **Baseline** | Ridge (linear, 65 params) used for contrast |
| **V3 (config/code)** | Legacy code — **do not refer to DL model as V3** |

All new files use no version suffix (`backtest_engine.py`, `phase_c_eval.py`).

## Non-goals

- Retraining V4 with new configs (use existing predictions)
- Full SWA across all 3 folds (fold 2 only has topk; skipped)
- Kelly sizing with real options pricing (simplified Kelly approximation is fine)
- Internal crossing / exchange-specific routing

## Architecture

```
┌────────────────────────────────────────────────────────────────┐
│ Stage 1: Ensemble Predictions (scripts/ensemble_v4_xgb.py)     │
│  V4 + XGBoost on matched 3-fold (from Phase A preds)           │
│  → experiments/phase_c/ensemble_preds/fold_{0,1,2}.npz         │
└────────────────────────────────────────────────────────────────┘
                            ↓
┌────────────────────────────────────────────────────────────────┐
│ Stage 2: Backtest Engine (src/evaluation/backtest_engine.py)   │
│  - Realistic execution (limit order fills, depth slippage)     │
│  - Walk-forward τ* calibration (val set)                       │
│  - Proper crypto 24/7 annualization                            │
│  - Funding rate (basic)                                        │
└────────────────────────────────────────────────────────────────┘
                            ↓
┌────────────────────────────────────────────────────────────────┐
│ Stage 3: Comprehensive Evaluation (scripts/phase_c_eval.py)    │
│   7 metric categories + 4 stress scenarios + bootstrap CIs     │
└────────────────────────────────────────────────────────────────┘
                            ↓
┌────────────────────────────────────────────────────────────────┐
│ Stage 4: Report (experiments/phase_c/REPORT.md)                │
│  ~20 plots, comprehensive tables, executive summary            │
└────────────────────────────────────────────────────────────────┘
```

## Stage 1 — V4+XGB Ensemble

**Key design:** Use Grinold-Kahn optimal weights, with weights calibrated on **pooled per-fold validation set** (NOT on test set — avoids lookahead).

Since we lack separate val-set predictions, use equal-weight as conservative fallback. Per Phase A Cat 11 result: theoretical optimal weights V4=0.61, XGBoost=0.55, Ridge=−0.06 → proxy: **V4:XGB = 0.55:0.45** (normalized positive) → expected pooled IC **~0.10**.

Alternative: use inverse-variance weighting (each model's per-fold val IC variance).

**Output:** `ensemble_preds/fold_{0,1,2}.npz` with fields `predictions` (N,), `targets` (N,), `mask` (N,), `timestamps` (N,).

## Stage 2 — Backtest Engine

### Realism checklist

1. **Order type:** Maker limit order at mid ± small aggressiveness; fallback to taker market order if unfilled after `t_cancel_sec`.
2. **Fill model:**
   - Maker: fill probability = f(queue position, price aggressiveness). Simplification: `fill_prob = 0.7` if within 1 tick of best bid/ask, else 0.
   - Taker: always fills, with depth-dependent slippage.
3. **Slippage:** For taker orders, walk the book up/down to fill the position, compute VWAP. Use `X_raw` 20-level data.
4. **Latency:** Signal at t applied to fill at t+latency_ms (default 500 ms). No look-ahead.
5. **Fees:** Binance Futures BTCUSDT — maker 0.02%, taker 0.04%.
6. **Funding rate:** Use historical 8h funding for BTCUSDT (fetch from Binance if available, else flat 0.01% avg).
7. **Position sizing:** Confidence-gated. `position = sign(q50) × min(1, |q50| / (q90 − q10) / τ*)`. τ* calibrated on val set.
8. **No look-ahead:** Every decision at t uses only data available at t or earlier.
9. **Mark-to-market:** P&L accumulates on position changes + funding accruals. Use close-to-close log returns.

### Walk-forward τ* calibration

For each fold:
1. Compute confidence scores on **val set**
2. Sweep τ ∈ quantiles(confidence_val, [0.0, 0.1, ..., 1.0])
3. For each τ, compute val Sharpe under execution model
4. Pick τ* = argmax Sharpe on val
5. Apply τ* to test set, report test Sharpe

**Invariant:** τ* is NEVER optimized on test set.

### Annualization

- Crypto: 365 × 24 × 3600 seconds/year = 31,536,000 sec
- Our samples: ~60 sec apart (stride 60)
- Annualization factor: √(31,536,000 / 60) = √525,600 ≈ 725
- Apply to per-sample Sharpe: `sharpe_ann = (mean / std) × 725`

## Stage 3 — Comprehensive Evaluation

### 7 metric categories

| # | Category | Metrics |
|---|---|---|
| 1 | Signal quality | IC (Pearson/Spearman/Kendall), IC-IR daily/monthly, stability index |
| 2 | Execution | Fill rate (maker %), realized slippage (bps), round-trip cost |
| 3 | Returns | Gross/net PnL, Sharpe (HAC Newey-West), Sortino, Calmar, turnover |
| 4 | Risk | Max DD, avg DD, CVaR-95/99%, tail ratio, max time underwater |
| 5 | Regime | IC by vol tertile, trend direction, hour-of-day heatmap, monthly |
| 6 | Position mgmt | τ* value, trade rate, Kelly occupancy, vol-scaled sizing stats |
| 7 | Statistical | Bootstrap 95% CI on Sharpe, PBO, Deflated Sharpe, stability index |

### 4 stress scenarios

1. **Oct 2024 flash crash event** — if test period covers, isolate worst 10 trading hours
2. **Highest-vol monthly bucket** — find the month with max realized vol, run strategy
3. **Asia→EU handoff (03:00-06:00 UTC)** — historically thin liquidity
4. **Regime transition days** — days with sign flip in rolling 4h trend

### Additional I'm adding (judgment call)

- **Prediction confidence distribution** (histogram with quantile bands)
- **Hit rate vs confidence bucket** (calibration of predicted strength)
- **Correlation to benchmarks** (BTC buy-and-hold as reference)
- **Cumulative P&L attribution by fold** (check no single fold dominates)
- **τ* sensitivity analysis** (is optimum sharp or flat? → stability concern)
- **Monte Carlo bootstrap of P&L** (block bootstrap, block=60)

### Bootstrap methodology

Block bootstrap (block_len = 60 samples), 2000 resamples, report 95% CI for:
- Sharpe
- Max DD
- Pearson/Spearman IC
- Annualized return

## Stage 4 — Report

**Structure:**

```
experiments/phase_c/
├── REPORT.md              # Executive summary + embedded figures
├── REPORT_ZH.md           # Chinese version
├── metrics.json           # Machine-readable full results
├── figures/
│   ├── 01_signal_quality.png
│   ├── 02_execution_stats.png
│   ├── 03_equity_curve.png
│   ├── 04_drawdown_underwater.png
│   ├── 05_returns_dist.png
│   ├── 06_regime_heatmap.png
│   ├── 07_position_sizing.png
│   ├── 08_confidence_calibration.png
│   ├── 09_tau_sweep.png
│   ├── 10_bootstrap_sharpe.png
│   ├── 11_rolling_sharpe.png
│   ├── 12_monthly_returns.png
│   ├── 13_stress_oct2024.png
│   ├── 14_stress_monthly_vol.png
│   ├── 15_stress_asia_handoff.png
│   ├── 16_stress_regime_transition.png
│   ├── 17_hit_rate_by_confidence.png
│   ├── 18_pnl_attribution_by_fold.png
│   ├── 19_benchmark_comparison.png
│   └── 20_tau_stability.png
├── tables/
│   ├── summary.csv        # One row per (metric, value, CI_low, CI_high)
│   ├── per_fold.csv
│   └── stress_scenarios.csv
└── executive_summary.md   # One-pager
```

## Validation Checklist (逻辑漏洞检查)

Before declaring Phase C done, verify:

- [ ] τ* from val set, applied to test — never reverse
- [ ] Signal delay ≥ 500 ms applied consistently
- [ ] Fees match Binance Futures (maker 0.02%, taker 0.04%)
- [ ] Slippage uses actual orderbook depth (not flat %)
- [ ] Funding rate accrual at 8-hour boundaries
- [ ] Annualization factor = 725 (not 252 or 365)
- [ ] Bootstrap blocks respect serial correlation (block_len = 60)
- [ ] Stress tests isolated correctly (no leakage into main metrics)
- [ ] Ensemble weights from val, applied to test
- [ ] No single fold dominates P&L (if so, flag concentration)
- [ ] Turnover reasonable (check by inspection)
- [ ] Regime splits don't have look-ahead (use rolling past data only)

## Timeline

- Day 1: Stage 1 (ensemble) + Stage 2 core (cost model + τ* calibration)
- Day 2: Stage 2 completion + Stage 3 (metric categories 1-4)
- Day 3: Stage 3 (categories 5-7 + stress tests) + Stage 4 (report)

Total: ~3 days focused work.
