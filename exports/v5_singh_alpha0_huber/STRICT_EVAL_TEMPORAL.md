# V5 singh α=0+Huber — Phase A Temporal Stability Evaluation

**Input:** `exports/v5_singh_alpha0_huber/y600_predictions_all_folds.csv` (49,953 valid samples)
**Time range:** 2025-02-09 00:10:00+00:00 → 2025-09-09 07:37:00+00:00
**Model output column:** `y_pred_q50_bps` (raw, uncalibrated). Live calibration tested separately.

## 1. Monthly IC trajectory

| Month | n | y_mean | ŷ_mean | Pearson | Spearman | DirAcc |
|---|---:|---:|---:|---:|---:|---:|
| 2025-02 | 4,268 | -0.078 | +0.195 | +0.1042 | +0.1169 | 0.547 |
| 2025-03 | 4,613 | -0.240 | +0.180 | +0.0222 | +0.0475 | 0.520 |
| 2025-04 | 9,017 | +0.126 | +0.131 | +0.0653 | +0.0626 | 0.519 |
| 2025-05 | 7,722 | -0.217 | +0.123 | +0.0474 | +0.0531 | 0.523 |
| 2025-06 | 9,984 | +0.325 | +0.189 | +0.0779 | +0.0858 | 0.532 |
| 2025-07 | 8,261 | +0.329 | +0.231 | +0.0772 | +0.0675 | 0.523 |
| 2025-08 | 4,585 | -0.168 | +0.234 | +0.0555 | +0.0495 | 0.519 |
| 2025-09 | 1,503 | +0.930 | +0.221 | +0.0405 | +0.0745 | 0.550 |

**Worst-month Pearson:** `+0.0222` (2025-03)
**Worst-month Spearman:** `+0.0475` (2025-03)
**Best-month Pearson:** `+0.1042` (2025-02)
**Pearson std across months:** `0.0256` (CoV 0.417)
**Spearman std across months:** `0.0231` (CoV 0.332)
**Months with Pearson < 0.03:** 1 / 8

## 2. Regime adaptation — rolling-mean correlation

Does ŷ_mean track y_mean over time? Strong correlation = model adapts to regime.

Daily n: 210 days. Rolling 30-day window applied.

**Rolling 30d ŷ_mean ↔ y_mean correlation: `-0.2090`**
- Target for regime adaptation: ≥ 0.3 ✓
- 0.0 ~ 0.1: model does not adapt to regime
- < 0: model adapts in WRONG direction

5-row sample (rolling 30d means, bps):
| day | roll30_y | roll30_ŷ |
|---|---:|---:|
| 2025-02-23 | -0.0389 | +0.1505 |
| 2025-04-03 | +0.0346 | +0.2272 |
| 2025-05-14 | +0.1466 | +0.1270 |
| 2025-06-22 | +0.2604 | +0.1444 |
| 2025-07-31 | +0.2634 | +0.2308 |
| 2025-09-09 | -0.0641 | +0.2224 |

## 3. Worst rolling 30-day Pearson

For each day, compute Pearson over [day-30, day] window. Find worst.

**Worst rolling-30d Pearson: `+0.0120`** (2025-04-03)
**Best rolling-30d Pearson: `+0.1227`** (2025-02-28)
**Days with rolling-30d Pearson < 0.03:** 11 / 209 (5.3%)
**Days with rolling-30d Pearson < 0:** 0 / 209 (0.0%)

## 4. Vol-regime stratified IC

Split samples by absolute realized return into 3 vol buckets, report IC per bucket.

Vol bucket cutoffs: [low ≤ 3.83, mid ≤ 9.43, high > 9.43] bps |y|.

| Bucket | n | y_mean | ŷ_mean | Pearson | Spearman |
|---|---:|---:|---:|---:|---:|
| low_vol | 16,651 | -0.030 | +0.180 | +0.0359 | +0.0421 |
| mid_vol | 16,651 | -0.119 | +0.160 | +0.0446 | +0.0427 |
| high_vol | 16,651 | +0.425 | +0.200 | +0.0866 | +0.0897 |

## 5. Static-prediction detector

If model adapts, monthly ŷ_mean variance should be commensurate with monthly y_mean variance scaled by ρ.
Specifically: `var(monthly_ŷ_mean) / var(monthly_y_mean)` should be ≈ ρ² ~ 0.005 (since ρ ~ 0.07).
Much smaller → model output is too static (doesn't adapt). Much larger → over-extrapolating.

- var(monthly y_mean): `0.1582` bps²
- var(monthly ŷ_mean): `0.0018` bps²
- **Ratio (ŷ/y): `0.0114`** (target ≥ ρ² ~ 0.005)
- ✓ Model output adapts proportionally to ρ

## 6. Temporal scorecard

| Gate | PASS |
|---|:-:|
| Worst-month Pearson > 0.03 | ✗ |
| Worst-month Spearman > 0.03 | ✓ |
| Months with P > 0.03: ≥ 80% | ✓ |
| Pearson CoV < 0.5 | ✓ |
| Regime adaptation corr ≥ 0.3 | ✗ |
| Worst rolling-30d P > 0.02 | ✗ |
| Days with rolling-30d P < 0: ≤ 5% | ✓ |
| Static-detector ratio in [0.005, 0.05] | ✓ |
| Vol regime: all 3 buckets P > 0.04 | ✗ |

**Score: 5 / 9 gates PASS**