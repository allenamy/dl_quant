# Phase A Findings — V3 Diagnostic

This document collects the outputs of the three Phase-A diagnostic tasks
(A1: Ridge feature weights; A2: V3 module ablation; A3: distribution-shift
analysis). Each section is appended by the agent that owns that task.

---

## A3: Distribution Shift (Fold 0)

**Question:** Is non-stationarity (not overfitting) the dominant V3 failure mode?

**Method:** Population Stability Index (PSI) of each last-timestep feature and
the target, comparing the fold-0 train window vs. the fold-0 test window. PSI
uses 10 equal-mass train quantiles as bin edges (with `-inf`/`+inf` extrapolation)
and `eps=1e-6` to guard `log(0)`.

**Fold 0 window (from `experiments/v3_full/psi.json`):**

| | Days | Samples (masked) |
|---|---|---|
| Train | 2023-01-01 → 2023-06-29 (180 d) | 26 550 |
| Test  | 2023-07-30 → 2023-08-28 (30 d)  |  8 406 |

**Target PSI:** **0.349** — **SEVERE** (threshold 0.25).

- Train target mean/std: `+2.43e-06 / 9.01e-04`
- Test  target mean/std: `−4.72e-06 / 4.51e-04`
- Test volatility is **half** the train volatility (`σ_test ≈ 0.50 · σ_train`).
  Under quantile loss trained on higher volatility, the model’s q10/q90 are
  expected to be miscalibrated (too wide), biasing median predictions and
  degrading directional Sharpe on test.

**Top 10 shifted features:**

| Rank | Feature                 | PSI   | Interpretation |
|---:  | :---                    | ---:  | :--- |
| 1    | `spread_bps`            | 6.802 | catastrophic — spread regime totally different |
| 2    | `realized_vol_300s`     | 1.329 | severe — vol regime shifted |
| 3    | `ask_depth_L5`          | 1.313 | severe |
| 4    | `ask_depth_L25`         | 1.245 | severe |
| 5    | `bid_depth_L5`          | 1.111 | severe |
| 6    | `kyle_lambda_30s`       | 1.048 | severe — liquidity price-impact shifted |
| 7    | `price_impact_30s`      | 1.048 | severe |
| 8    | `vpin_300s`             | 1.046 | severe — flow-toxicity shifted |
| 9    | `bid_concentration`     | 1.032 | severe |
| 10   | `ask_concentration`     | 1.005 | severe |

**Aggregate across all 58 features:**

| Band                 | Count | % |
|---                   |  ---: | ---: |
| Negligible (PSI <0.10)  |  9 | 16 % |
| Mild       (0.10–0.25)  | 21 | 36 % |
| Severe     (PSI ≥0.25)  | 28 | 48 % |

Median PSI = 0.227, mean PSI = 0.524. Nearly half of the input features cross
the “recalibrate” threshold between a 180-day train window and the very next
30-day test window.

### Conclusion

**Yes — distribution shift alone is large enough to explain V3’s failure
relative to Ridge, independent of any overfitting.** Evidence:

1. Target PSI 0.349 > 0.25 means the quantile head is being evaluated on a
   distribution it was never calibrated for (half the train volatility).
2. 28 of 58 features (48 %) are in the severe band, with the top
   microstructure drivers (`spread_bps`, `realized_vol_300s`, depth, Kyle λ,
   VPIN) all ≥ 1.0 — orders of magnitude past the severity threshold.
3. Ridge’s relative robustness is consistent with this: a linear model with
   L2 shrinkage degrades gracefully under covariate shift, whereas V3’s
   dual-path encoders (MaskNet gates, GDCN crosses, Conv2d over normalized
   bps+log1p) learn higher-order feature interactions that break when the
   marginal distributions move.

**Implication for redesign:** any V3 improvement that does not address
non-stationarity first (robust normalization, feature rebasing per day,
rolling-window retraining, regime-conditioned heads) will not close the gap
with Ridge, regardless of architecture changes. Phase-B data expansion and
Phase-C model redesign must include an explicit distribution-shift mitigation.

**Artifacts:**
- `scripts/analyze_distribution_shift.py`
- `experiments/v3_full/psi.json`
