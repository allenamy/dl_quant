# y_600 ckpt × seed diagnostic

Methodology: raw dense y_600 (from patched CSV), per-fold-aware pool, q50 predictions

- N_pooled = 48,678 valid (across 3 folds: 15,695 + 16,771 + 17,111)
- Sample units in metric: log-return; bps = ×1e4
- y_true_bps stats: mean ≈ -0.46 bps, std ≈ 9.5 bps (per fold), pooled std ~9.5 bps
- σ_y_pool ≈ 9.5 bps means σ_ŷ/σ_y at 0.05 corresponds to σ_ŷ ≈ 0.5 bps

## Single-seed × ckpt (9 configs)

| Config | P | S | β | σ_ŷ/σ_y | mean(ŷ) bps | top-bin ŷ bps | bin-Sp | per-fold P (std) |
|---|---:|---:|---:|---:|---:|---:|---:|---|
| seed07_BEST | +0.0369 | +0.0451 | +0.856 | 0.043 | -0.176 | -0.042 | +0.503 | [+0.0332, +0.0379, +0.0586] σ=0.0110 |
| seed07_EMA | +0.0444 | +0.0522 | +1.070 | 0.042 | -0.246 | -0.186 | +0.915 | [+0.0387, +0.0376, +0.0588] σ=0.0097 |
| seed07_SWA | +0.0474 | +0.0576 | +1.147 | 0.041 | -0.182 | -0.062 | +0.636 | [+0.0437, +0.0429, +0.0611] σ=0.0084 |
| seed13_BEST | +0.0410 | +0.0542 | +0.972 | 0.042 | -0.239 | -0.101 | +0.539 | [+0.0307, +0.0427, +0.0600] σ=0.0121 |
| seed13_EMA | +0.0490 | +0.0590 | +1.210 | 0.040 | -0.339 | -0.259 | +0.952 | [+0.0407, +0.0497, +0.0610] σ=0.0083 |
| seed13_SWA | +0.0477 | +0.0596 | +1.164 | 0.041 | -0.311 | -0.188 | +0.697 | [+0.0384, +0.0520, +0.0630] σ=0.0100 |
| seed42_BEST | +0.0420 | +0.0500 | +0.806 | 0.052 | -0.106 | -0.057 | +0.939 | [+0.0350, +0.0493, +0.0512] σ=0.0072 |
| seed42_EMA | +0.0402 | +0.0507 | +0.874 | 0.046 | +0.058 | +0.154 | +0.770 | [+0.0313, +0.0497, +0.0589] σ=0.0115 |
| seed42_SWA | +0.0457 | +0.0571 | +1.010 | 0.045 | -0.079 | +0.023 | +0.770 | [+0.0445, +0.0493, +0.0558] σ=0.0046 |

## Ensemble (median/mean × 3 ckpt = 6 configs)

| Config | P | S | β | σ_ŷ/σ_y | mean(ŷ) bps | top-bin ŷ bps | bin-Sp | per-fold P (std) |
|---|---:|---:|---:|---:|---:|---:|---:|---|
| 3seed_median_BEST | +0.0455 | +0.0559 | +1.161 | 0.039 | -0.194 | -0.080 | +0.661 | [+0.0392, +0.0444, +0.0608] σ=0.0092 |
| 3seed_mean_BEST | +0.0475 | +0.0582 | +1.227 | 0.039 | -0.174 | -0.067 | +0.697 | [+0.0418, +0.0471, +0.0604] σ=0.0078 |
| 3seed_median_EMA | +0.0497 | +0.0586 | +1.267 | 0.039 | -0.211 | -0.134 | +0.952 | [+0.0438, +0.0477, +0.0629] σ=0.0082 |
| 3seed_mean_EMA | +0.0497 | +0.0592 | +1.304 | 0.038 | -0.176 | -0.097 | +0.867 | [+0.0442, +0.0500, +0.0632] σ=0.0080 |
| 3seed_median_SWA | +0.0499 | +0.0605 | +1.255 | 0.040 | -0.192 | -0.077 | +0.697 | [+0.0455, +0.0502, +0.0628] σ=0.0073 |
| 3seed_mean_SWA | +0.0500 | +0.0607 | +1.253 | 0.040 | -0.191 | -0.076 | +0.758 | [+0.0454, +0.0509, +0.0631] σ=0.0074 |

## Aggregate by ckpt type (across 3 single seeds + 2 ensembles per ckpt)

| ckpt | mean(P) | min/max(P) | mean(σ_ŷ/σ_y) | mean(\|mean(ŷ)\|) bps | mean(top-bin ŷ) bps | mean(bin-Sp) |
|---|---:|---:|---:|---:|---:|---:|
| BEST | +0.0426 | +0.0369/+0.0475 | 0.043 | 0.178 | -0.069 | +0.668 |
| EMA | +0.0466 | +0.0402/+0.0497 | 0.041 | 0.206 | -0.104 | +0.891 |
| SWA | +0.0481 | +0.0457/+0.0500 | 0.041 | 0.191 | -0.076 | +0.712 |

## Decision criteria

Looking for the config that maximizes:
- **trading-side calibration**: |mean(ŷ)| close to 0, top-bin ŷ > 0, β close to 1.0
- **statistical IC**: P, S high
- **stability**: per-fold P std small
- **σ_ŷ expression**: σ_ŷ/σ_y as high as possible without sacrificing P

Production candidate decision rules:
1. If a single seed clearly wins on level metrics + P/S not worse → use it (defensible vs anti-pattern #14 if pre-declared seed=42 is the winner)
2. If 3seed_mean ≥ 3seed_median on P/S AND level metrics → switch to mean (linear, no tail squeeze)
3. If BEST has best β/top-bin ŷ + similar P/S → switch from EMA to BEST