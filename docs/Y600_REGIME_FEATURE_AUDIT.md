# Phase A.5.1 — V5 Singh Feature Regime-Adaptation Audit

**Audit period:** 2024-01-01 → 2025-09-09 (606 days, 592 with forward window)
**Question:** Do existing 64 features (or 6 regime_prior) at daily-aggregation level predict next-30-day y_600 mean?
**Method:** For each feature, compute Pearson(daily_mean(feature), next_30d_y_mean). All causal (uses t-end < forward window start).

**Hypothesis:**
- If any feature |corr| ≥ 0.10: existing input has regime info → ARCHITECTURE issue (model can't use additive baseline)
- If all |corr| < 0.05: regime info missing → FEATURE issue (need lookback features)
- 0.05-0.10 region: marginal, prefer architecture fix

## Top 20 features by |corr| with next-30d y_mean

| Rank | Feature | corr | |corr| |
|---:|---|---:|---:|
| 1 | `feat_56_book_pressure_imbalance` | -0.1419 | 0.1419 |
| 2 | `feat_07_obi_L10` | -0.1384 | 0.1384 |
| 3 | `feat_14_depth_ratio_L5` | -0.1367 | 0.1367 |
| 4 | `feat_06_obi_L5` | -0.1367 | 0.1367 |
| 5 | `feat_08_obi_L25` | -0.1289 | 0.1289 |
| 6 | `feat_05_obi_L1` | -0.1286 | 0.1286 |
| 7 | `feat_28_bid_amt_ratio_L1` | -0.1241 | 0.1241 |
| 8 | `feat_13_ask_depth_L25` | +0.1174 | 0.1174 |
| 9 | `feat_15_weighted_price_bid_L10` | +0.1172 | 0.1172 |
| 10 | `feat_16_weighted_price_ask_L10` | -0.1164 | 0.1164 |
| 11 | `feat_29_ask_amt_ratio_L1` | -0.1111 | 0.1111 |
| 12 | `rp_5` | -0.1108 | 0.1108 |
| 13 | `feat_37_second_of_day_cos` | -0.1104 | 0.1104 |
| 14 | `feat_19_realized_vol_60s` | -0.1083 | 0.1083 |
| 15 | `feat_18_realized_vol_30s` | -0.1077 | 0.1077 |
| 16 | `feat_23_ask_slope_L10` | -0.1076 | 0.1076 |
| 17 | `feat_20_realized_vol_300s` | -0.1076 | 0.1076 |
| 18 | `rp_0` | -0.1050 | 0.1050 |
| 19 | `feat_22_bid_slope_L10` | -0.1020 | 0.1020 |
| 20 | `feat_32_bid_amt_ratio_L3` | -0.0974 | 0.0974 |

## Statistics

- **Max |corr|:** `0.1419` (feature: `feat_56_book_pressure_imbalance`)
- **Median |corr|:** `0.0602`
- **Features with |corr| ≥ 0.10:** 19 / 70
- **Features with |corr| ≥ 0.05:** 44 / 70
- **Mean |corr|:** `0.0689`

## Diagnostic

**Architecture issue likely**: 19 features carry regime info but model output is regime-anti-correlated (-0.21).
PPNetGate is multiplicative-only (gates magnitude, can't shift baseline). Need additive head bias from regime features.

## Baseline: past y_600 as feature

- Past 30-day y_600_mean → next 30-day y_600_mean: corr = `+0.3201`
  - This is the SIMPLEST regime feature. Should be ≥ 0.20 for regime to be predictable.

- Past 7-day y_600_mean → next 30-day y_600_mean: corr = `+0.1217`
