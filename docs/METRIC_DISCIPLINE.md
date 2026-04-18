# Metric Discipline for LOB Mid-Frequency Forecasting

_Authoritative rules for how we evaluate models, ablations, and make go/no-go decisions on this project._

## Why this document exists

Our spec (`docs/superpowers/specs/2026-04-16-v4-design.md`) sets a Pearson corr bar (≥ 0.12 on h=180). But financial returns — especially crypto at a 180-second horizon — are heavy-tailed. A Pearson-only gate can be mis-aligned with actual trading P&L:

- **Pearson is sensitive to outliers.** A few 5σ realized-return days can inflate OR deflate Pearson dramatically without reflecting signal quality.
- **Spearman (rank IC) is what trading actually needs.** Whether you can rank "this window will move up more than that one" is the decision-relevant quantity for long/short or size-by-confidence strategies. Magnitude refinement on top is secondary.
- **Industry practice** (Two Sigma, Renaissance, Citadel alpha research): rank IC is primary, Pearson reported alongside for magnitude calibration.

So we keep the Pearson spec bar (discipline + magnitude check), but we **promote Spearman to equal status** as the trading-reality metric, and we **require both to be reported on every run.**

## Metric hierarchy

### 1. Spearman rank IC — trading-side primary

- Robust to heavy-tailed realized returns.
- Directly measures "can we rank?" — the decision-relevant quantity for our long/short trading use case.
- Computed on (q50_pred, y_target) over all valid test samples.

### 2. Pearson correlation — spec compliance + magnitude calibration

- The written spec bar (≥ 0.12 on h=180 pooled OOS).
- Exercises magnitude fidelity: if Pearson is materially lower than Spearman, we're predicting direction but not scale — position sizing will be miscalibrated.
- Computed on (q50_pred, y_target) over all valid test samples.

### 3. Direction accuracy — hygiene check

- `mean(sign(q50_pred) == sign(y_target))` on the valid mask.
- Must be strictly > 50% for the signal to be real at all.
- Not a trading metric by itself (doesn't account for magnitude or cost), but a cheap sanity check.

### 4. Weighted Sharpe (Newey-West HAC) — final answer

- Full backtest with 4bps round-trip fee + 1bps/side slippage.
- Position size ∝ |q50| / (q90 − q10), capped.
- Newey-West HAC correction with `overlap_ratio = horizon_sec / stride`.
- Computed via `src/evaluation/backtest_v2.py::BacktestEngine`.

### 5. R² — diagnostic only, NOT a pass/fail gate

- In the SNR < 1% regime, r² values are noisy and small-magnitude.
- Useful to track whether r² is trending up (signal strengthening) but individual r² values are not reliable.

## Divergence handling

| Pearson ≥ 0.12 | Spearman ≥ 0.12 | Verdict | Action |
|:-:|:-:|:-|:-|
| ✅ | ✅ | **Pass** | Ship — spec + trading both satisfied |
| ❌ | ✅ | **Trading-viable, spec non-compliant** | Document, flag, check for outlier influence. With user alignment, can still be deployed as the signal is trading-real. |
| ✅ | ❌ | **Warning: Pearson gamed** | Few-sample dominance. Very likely won't hold in OOS deployment. DO NOT SHIP. |
| ❌ | ❌ | **Fail** | Iterate architecture/features/data, or accept negative result and revert to baseline. |

**Cross-check rule:** if `|Pearson − Spearman| > 0.03`, treat as anomalous and run outlier diagnostics (check top-5 contribution to Pearson, winsorize at 99th percentile, verify Spearman is stable).

## Reporting template

Every experiment result (smoke, fold, pooled) MUST report the full set:

```
<experiment_name>:
  pearson       = <float>   # spec bar 0.12
  spearman      = <float>   # trading bar 0.12
  direction_acc = <float>   # hygiene > 0.50
  sharpe_annual = <float>   # (after backtest)
  val_pearson   = <float>
  val_spearman  = <float>
  n_samples     = <int>
  notes         = <short string if outlier-heavy or otherwise flagged>
```

Scripts MUST compute both Pearson and Spearman on the same valid mask. `scripts/aggregate_folds.py` already does this; `scripts/smoke_sweep.sh` already does this. If adding a new reporter, replicate.

## Pinned definitions

- **Valid mask**: `y_mask_{h} > 0` — used identically for all metrics.
- **q50**: middle column of predictions `(N, 3)`, i.e., index 1.
- **Spearman**: `np.corrcoef(rankdata(q50), rankdata(y))[0,1]`. This is the standard "rank IC".
- **Pearson**: `np.corrcoef(q50, y)[0,1]`.

## Things you are NOT allowed to do

1. **Do not** report Pearson only and omit Spearman (or vice versa) to make a result look better.
2. **Do not** pick a checkpoint by Pearson at epoch X when Spearman peaked at a different epoch. Report both at the same checkpoint.
3. **Do not** re-run the same experiment with a different seed and cherry-pick the better number. Note the seed used and report.
4. **Do not** claim "beats Ridge" based on Pearson if Spearman is lower than Ridge's Spearman. State both.
5. **Do not** use r² as a pass/fail criterion in any form.

## Known past surprises

- **V4 no_attention, fold 0 (2026-04-18):** Pearson 0.101, Spearman 0.107 (aligned — good). Beats Ridge 0.099 on Pearson.
- **V4 full, fold 0 (2026-04-18):** Pearson 0.061, Spearman 0.089. Spearman-Pearson gap of 0.028 — borderline outlier-influenced. Worth investigating if Pearson was drag from 1-2 bad days.

## Why this applies to future work

- **Ablations**: run with this template; never decide on one metric alone.
- **Iterations**: when tuning, track both metrics' trajectories. If Pearson climbs while Spearman stalls, your tweak is overfitting to outliers, not learning signal.
- **Final report**: lead with Spearman, follow with Pearson; explicitly call out any divergence > 0.03 as a caveat.
