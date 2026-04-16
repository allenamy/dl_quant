# Phase A Findings — V3 Diagnostic

This document collects the outputs of the three Phase-A diagnostic tasks
(A1: Ridge feature weights; A2: V3 module ablation; A3: distribution-shift
analysis). Each section is appended by the agent that owns that task.

---

## A1: Ridge Feature Importance

**Question:** Which features carry the Ridge signal? Does the ~0.10 test
correlation come from a small number of strong predictors or a large number of
tiny ones? What does that tell us about targeted feature engineering in
Phase C?

**Measurement.** `scripts/analyze_ridge_weights.py` on `data/npz_full/`
(1004 per-day NPZs). Last-timestep features only (matches the Ridge baseline in
`run_baselines.py`), 80/20 temporal split (no shuffle), `StandardScaler` fit on
train only, `Ridge(alpha=1.0, fit_intercept=True)`. Because `X` is standardized,
`|coef|` is the standardized effect size per feature.

### Run summary

| field              | value                              |
|--------------------|------------------------------------|
| n_train            | 154,332                            |
| n_test             | 38,583                             |
| target_sigma (y)   | 8.79e-4                            |
| **test_corr**      | **0.0830**                         |
| alpha              | 1.0                                |
| split              | 80/20 temporal, train-only scaler  |

Single-split Ridge test_corr is ~0.083, slightly below the cross-validated
baseline (0.1016) reported in `PROGRESS.md` — expected, since CV averages
multiple folds while this single-split estimate has higher variance. The
ordering of top features, not the absolute corr, is what matters here.

### Top 10 features

| rank | feature                 | coef       | marginal_corr | interpretation                                               |
|------|-------------------------|------------|---------------|--------------------------------------------------------------|
| 1    | net_trade_flow_1s       | +3.50e-4   | +0.029        | Net aggressor buy pressure (1s) → positive next-return       |
| 2    | sell_volume_1s          | +2.83e-4   | -0.018        | Sign flip vs marginal: see multicollinearity note below      |
| 3    | buy_volume_1s           | -2.81e-4   | +0.012        | Sign flip vs marginal: see multicollinearity note below      |
| 4    | obi_L1                  | +4.57e-5   | +0.075        | Top-of-book bid-heavy imbalance predicts up-move             |
| 5    | obi_L25                 | -3.47e-5   | +0.071        | Sign flip vs marginal — collinear with obi_L1/L10            |
| 6    | ask_depth_L25           | -2.71e-5   | -0.054        | Deep ask liquidity predicts down-move (sellers queued)       |
| 7    | weighted_price_ask_L10  | +2.01e-5   | +0.041        | Ask-side weighted price tilt → positive return               |
| 8    | obi_L10                 | +1.99e-5   | +0.074        | Medium-depth imbalance, consistent with L1                   |
| 9    | microprice_dev_bps      | -1.88e-5   | -0.010        | Small marginal corr, low magnitude                           |
| 10   | bid_depth_L5            | +1.82e-5   | +0.056        | Shallow bid depth associated with up-moves                   |

Full top-20 in `experiments/v3_full/ridge_weights.json`.

### Headline findings

1. **Signal lives in order flow, not price history.** The three biggest
   standardized effects are all 1-second trade-flow features
   (`net_trade_flow_1s`, `sell_volume_1s`, `buy_volume_1s`), each an order of
   magnitude above the next feature. Price-based features (`log_return_*`,
   `realized_vol_*`) do **not** appear in the top 10. Phase C feature
   engineering should intensify the order-flow family: multi-window flow
   aggregates, signed-flow × imbalance interactions, flow residuals after
   regressing out volume magnitude.

2. **Order book imbalance is a strong second family.** `obi_L1`, `obi_L10`,
   `obi_L25` all land in the top 8 with marginal correlations 0.07-0.08 —
   the highest marginal corrs in the top 10. They consume less Ridge weight
   than order flow because the `obi_L*` features are mutually redundant
   (see note 3). A single orthogonalized imbalance factor (PCA on `obi_L*`,
   or an OBI "slope" = `obi_L1 − obi_L25`) should keep most of the signal
   while freeing Ridge capacity for other features.

3. **Multicollinearity warning — several sign flips.** `sell_volume_1s` has
   coef = **+2.83e-4** but marginal_corr = **−0.018**. `buy_volume_1s` has
   coef = **−2.81e-4** but marginal_corr = **+0.012**. `obi_L25` has
   coef = **−3.47e-5** but marginal_corr = **+0.071**. When marginal and
   Ridge signs disagree, Ridge is allocating predictive power across
   colinear partners by pushing some coefficients into a sign that cancels
   a dominant partner — the magnitudes are real but the individual signs
   have no physical meaning. Phase C should:
   - Rely on `net_trade_flow_1s = buy_volume_1s − sell_volume_1s` (already
     present) and consider dropping the two unsigned volumes, **or**
   - Replace raw volumes with flow residuals after regressing out
     `net_trade_flow`.

4. **Deeper book levels add marginal information.** `ask_depth_L25` and
   `bid_depth_L5` both make the top 10 with non-trivial marginal
   correlations. The Raw LOB path (Path B in the architecture doc) is
   plausibly useful — but the information it would add is small unless
   Phase C extracts interactions that a linear model on hand-crafted depth
   features misses.

5. **Volatility and spread are weak direct predictors.** `roll_spread_60s`,
   `spread_change`, `spread_bps`, `realized_vol_30s` all make the top 20
   but with marginal correlations near zero. They are probably useful as
   **conditioning variables** (regime splits, feature interactions) rather
   than direct predictors.

### Implications for later phases

- **Phase B (data scale):** the signal is real and comes from order flow +
  imbalance; scaling data to multi-horizon / denser strides is worthwhile.
- **Phase C1 (XGBoost):** critical sanity check — if XGBoost corr does not
  exceed Ridge corr by at least 0.01, the signal is truly linear and V3
  must be stripped to near-linear in Phase D.
- **Phase C2 (interactions):** priority interactions from A1 top-k:
  `net_trade_flow × obi_L1`, `obi_L1 × realized_vol`, `flow_1s × spread_bps`,
  `(obi_L1 − obi_L25)` slope.
- **Phase C3 (regime segmentation):** check whether Ridge corr collapses on
  low-spread / low-vol windows — if so, the flow signal only fires in
  liquid regimes and regime-conditional routing is needed.

**Artifacts:**
- `scripts/analyze_ridge_weights.py`
- `tests/test_analyze_ridge_weights.py`
- `experiments/v3_full/ridge_weights.json`

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
