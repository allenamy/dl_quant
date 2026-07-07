# V5 dualh α=0+Huber predictions — colleague backtest export

**Created:** 2026-05-05 04:05 UTC | **Session:** v5-alpha0-huber-winner | **Source:** experiments/v5_final/dualh_alpha0_huber/fold_{0,1,2}/test_preds.npz

## What this is

V5 conformer_hardened **dualh** (multi-horizon: y_180 aux 0.3 + y_600 primary 1.0) with **train-time bias-fixed loss**:

```
L = 0.10 · pinball(q10/q50/q90)                      # quantile safety net
  + 0.50 · utility_rank(score=q50, α=0.0)            # Spearman primary
  + 0.50 · plain Huber(q50, y, δ=2, w_wrong=0)       # Pearson + magnitude + bias
```

Single seed=42, 3-fold walk-forward, **BEST checkpoint** (NOT EMA — EMA performs worse here).

## Why this CSV (vs the prior multi-seed-median ones)

The prior production CSVs (baseline_plus, V5 dualh BASELINE) had a structural q50 negative bias caused by `utility_alpha=1.0` (model ranks by q10, but `q50 = q10 + softplus(δ)` forces q50 to be biased low for q10 to remain a clean ranking signal). This caused calibration view "top y-bin ŷ_mean" to come out **negative** — the model said negative even on the most-profitable y-bins.

This CSV is the **train-time fix** (no post-hoc demean):

| Metric | This (α=0+Huber) | Prior V5 BASELINE | V4 baseline_plus 3-seed median |
|---|---:|---:|---:|
| Pooled Pearson | +0.0622 | +0.0646 | +0.0497 |
| Pooled Spearman | +0.0672 | +0.0688 | +0.0586 |
| β | +1.06 | +1.05 | +1.27 |
| **Mean q50 bias (bps)** | **+0.14** ✓ | **-0.41** ✗ | -0.50 |
| **Top y-bin ŷ_mean (bps)** | **+0.22** ✓ | **-0.30** ✗ | (similar to V5 BASELINE) |
| Bin-monotonicity (Spearman) | +0.976 | +0.891 | (similar) |
| Top 10% ŷ → y_mean (bps) | +1.124 | +1.168 | +1.05 |
| per-fold P std | 0.005 | 0.008 | 0.008 |

**Conclusion:** ~3% Pearson/Spearman cost in exchange for fixing the calibration sign + tighter fold variance. Direct trade signal (top-decile-ŷ → y) is preserved.

## Files

| File | Content |
|---|---|
| `y600_predictions_fold_{0,1,2}.csv` | Per-fold test-set predictions (strict OOS). |
| `y600_predictions_all_folds.csv` | Combined: 50,846 rows, 49,953 valid (mask=1). No dedup needed (folds don't overlap on this run). |

## Columns (13)

- `timestamp_us` — int64 UTC microseconds; **end** of the 600-step input window.
- `datetime_utc` — ISO-8601 for convenience.
- `fold` — 0/1/2.
- `horizon_sec` — 600.
- `mask` — 1 if forward-return window fully observed; 0 if masked.
- `y_true_logret` / `y_true_bps` — realised 600s forward log-return.
- `y_pred_q10/q50/q90_logret` — predicted 10/50/90 percentiles of forward return distribution (monotonic by construction).
- `y_pred_q50_bps` — q50 in bps (×1e4) for trading convenience. **Use this directly as expected-return signal — no demean needed.**
- `y_pred_q50_z` — raw z-scored model output.
- `y_sigma_train_bps` — train-set MAD-sigma in bps (per-fold); multiply z by 1e-4·y_sigma to un-normalise.

## Backtest semantics

- Target at `t` = `log(mid[t+600s] / mid[t])`. Signal known at `t`.
- **Position entry** at `t` (anchor = end of input window).
- **Position exit** at `t + 600s` (pure signal P&L). For longer-hold strategies overlay your own logic.
- Filter: use `mask == 1` only.

## Coverage

- fold 0: 2025-02-09 → 2025-05-11
- fold 1: 2025-04-10 → 2025-07-10
- fold 2: 2025-06-11 → 2025-09-09

## Cost economics (heads-up — unchanged)

Single-asset BTC y_600 IC ~0.06. At 2 bps/trade round-trip, always-trade ≈ deeply negative Sharpe; best holding strategy is near break-even. **Production requires breadth (multi-asset) or maker-only orders.** This CSV improves the *signal quality* (q50 bias and top-y-bin calibration), not the trade economics.
