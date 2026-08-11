# V5 singh α=0+Huber — Strict Eval on LIVE-CALIBRATED q50

**CSV:** `exports/v5_singh_alpha0_huber/y600_predictions_live.csv` (49,803 rows after mask=1 + warmup=False filter, raw bps)
**Calibration:** causal rolling EMA-demean (α=0.01, HL≈69 samples≈11.5h, per-fold reset, 50-sample warmup excluded)
**Time range:** 2025-02-09T02:40:00Z → 2025-09-09T07:37:00Z

## 1. Sample IC — Pearson / Spearman / R²

| Slice | n | Pearson | Spearman | reg R² |
|---|---:|---:|---:|---:|
| fold 0 | 16,166 | +0.0533 | +0.0671 | +0.00270 |
| fold 1 | 17,808 | +0.0618 | +0.0633 | +0.00357 |
| fold 2 | 15,829 | +0.0665 | +0.0666 | +0.00384 |
| **POOLED** | **49,803** | **+0.0587** | **+0.0658** | **+0.00338** |
| per-fold std | | 0.0055 | 0.0017 | |

## 2. Bootstrap 95% CI (stationary block)

- Pearson: **+0.0587** [+0.0446, +0.0733]
- Spearman: **+0.0658** [+0.0561, +0.0756]
- Significance — Pearson lower bound > 0: ✓; Spearman lower bound > 0: ✓

## 3. Calibration — β / σ / bias

- β_y_on_ŷ (trading slope; perfect=1.0) = `+1.005`
- σŷ/σy = `0.0583` (model expresses 5.8% of y's amplitude)
- ŷ_mean = `+0.0004` bps, y_mean = `+0.0928` bps, bias = `-0.0923` bps

## 4. Trading View — deciles by ŷ → y_mean

| ŷ bin | n | ŷ_mean | y_mean | y_t_stat | dirAcc |
|---:|---:|---:|---:|---:|---:|
| 0 | 4,981 | -1.176 | -1.214 | -6.55 | 0.555 |
| 1 | 4,980 | -0.709 | -0.513 | -2.95 | 0.533 |
| 2 | 4,980 | -0.477 | -0.439 | -2.59 | 0.526 |
| 3 | 4,980 | -0.284 | -0.410 | -2.41 | 0.522 |
| 4 | 4,980 | -0.105 | +0.034 | +0.20 | 0.500 |
| 5 | 4,981 | +0.072 | +0.405 | +2.42 | 0.493 |
| 6 | 4,980 | +0.255 | +0.139 | +0.83 | 0.503 |
| 7 | 4,980 | +0.448 | +0.712 | +4.23 | 0.530 |
| 8 | 4,980 | +0.678 | +0.890 | +5.39 | 0.534 |
| 9 | 4,981 | +1.302 | +1.324 | +6.88 | 0.543 |

- Top-bot spread: **+2.538** bps
- Top decile y_t_stat: **+6.88**
- Bot decile y_t_stat: **-6.55**

## 5. Calibration View — deciles by y → ŷ_mean (USER PRIMARY)

| y bin | n | y_mean | ŷ_mean | sign |
|---:|---:|---:|---:|:-:|
| 0 | 4,981 | -22.167 | -0.058 | ✓ NEG |
| 1 | 4,980 | -10.238 | -0.064 | ✓ NEG |
| 2 | 4,980 | -6.249 | -0.036 | ✓ NEG |
| 3 | 4,980 | -3.424 | -0.030 | ✓ NEG |
| 4 | 4,979 | -1.100 | -0.019 | ✓ NEG |
| 5 | 4,982 | +1.033 | +0.016 | ✓ POS |
| 6 | 4,980 | +3.411 | +0.026 | ✓ POS |
| 7 | 4,980 | +6.344 | +0.017 | ✓ POS |
| 8 | 4,981 | +10.617 | +0.061 | ✓ POS |
| 9 | 4,980 | +22.702 | +0.092 | ✓ POS |

- **Top y-bin ŷ_mean = `+0.092` bps** (target ≥ 0): ✓ PASS
- **Bottom y-bin ŷ_mean = `-0.058` bps** (target ≤ 0): ✓ PASS
- Bin-Spearman (calibration view): `+0.9758`
- **Calibration line passes through origin**: ✓

## 6. Monotonicity — bin-Spearman

- Calibration view: `+0.9758`
- Trading view: `+0.9879`

## 7. Direction Accuracy

- Overall: **0.5254**
- Tail (|y| > 2σ_y, n=2,873): **0.5312**

## 8. Residual Auto-Correlation

| lag | resid AC | ŷ AC | y AC |
|---:|---:|---:|---:|
| 1 | +0.6826 | +0.1927 | +0.6782 |
| 5 | +0.0030 | +0.0277 | -0.0066 |
| 10 | -0.0164 | +0.0161 | -0.0181 |
| 30 | -0.0035 | +0.0128 | -0.0028 |

## 9. Per-fold Stability

- per-fold Pearson std: `0.0055` (CoV 0.090)
- per-fold Spearman std: `0.0017` (CoV 0.025)

## 10. Quantile Coverage (raw q10/q90)

- P(y < q10) = `0.091` (target 0.10)
- P(y > q90) = `0.086` (target 0.10)

## 11. PASS/FAIL Scorecard (live-calibrated)

| Gate | PASS |
|---|:-:|
| Pearson > 0.04 | ✓ |
| Spearman > 0.04 | ✓ |
| Bootstrap CI Pearson > 0 | ✓ |
| Bootstrap CI Spearman > 0 | ✓ |
| β_y_on_ŷ in [0.5, 2.0] | ✓ |
| σŷ/σy ≥ 0.02 | ✓ |
| |bias| < 0.05 bps (live should be near-zero) | ✗ |
| Top y-bin ŷ_mean > 0 (USER PRIMARY) | ✓ |
| Bottom y-bin ŷ_mean < 0 (USER PRIMARY) | ✓ |
| Calibration line crosses origin | ✓ |
| Bin-Spearman calib ≥ 0.85 | ✓ |
| Bin-Spearman trade ≥ 0.85 | ✓ |
| Tail DirAcc ≥ 0.52 | ✓ |
| Top-bot spread ≥ 1.0 bps | ✓ |
| per-fold P CoV < 0.20 | ✓ |

**Score: 14 / 15 gates PASS**