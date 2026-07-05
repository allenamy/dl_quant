> **创建:** 2026-07-06 · **Session:** fable-regime-breakthrough (agent stage0C-d3-factors) · **状态:** final · **作废条件:** Run1 substrate retrained / new best single model supersedes d1_<m>_run1 folds.

# Run1 (best single model) — production preds export + base-model metric battery

**Deliverable:** honest walk-forward OOS production simulation of the Run1 single model (each month = its own `experiments/d1gate/d1_<m>_run1/fold_0` test preds, concatenated chronologically 2025-08 → 2026-05), plus a full base-model metric battery vs the production baseline. CPU-only. Single seed, walk-forward OOS, strict time isolation.

## Export
`exports/run1_production_preds_from_2025_08.csv` — 130,698 rows (129,876 valid by mask; 110,898 with raw-y ground truth). Columns: `timestamp_ms, datetime_utc, month, y_pred_bps, y_true_bps, mask, has_ytrue`.

**Caliber (0B-verified, node-identity clean):** `y_pred_bps` = denorm of the Run1 q50 = `(pred[:,1]·y_sigma + y_median)·1e4`. `y_true_bps` = production CSV **raw** `y_true_ret_bps` — NOT the npz `targets` (those are ±5σ-clipped-normalized; although only 1–3 % of nodes are clipped, on heavy-tailed crypto returns that tail carries so much covariance that denorm(clipped) correlates only **0.88** with raw y on 2025-10, max Δ 893 bps — so clipped targets are unusable as realized returns). `builder = multi_asset/eval/mkrun1_commonY.py` / `run1_production_report.py`.

**Coverage per month (raw-y ground truth):**
| month | valid | raw-y | % | flag |
|---|---|---|---|---|
| 2025_08 | 13,272 | 4,067 | 31% | PARTIAL — prod CSV covers only 4,315 of the month; also backtest calib-warmup |
| 2025_09 | 13,272 | 3,534 | 27% | PARTIAL — prod CSV covers only 3,534; calib-warmup |
| 2025_10 … 2026_04 | 13,272 | ~13,270 | 100% | FULL |
| 2026_05 | 10,428 | 10,414 | 100% | FULL but partial month (22 days) |

2025-08/09 metrics are on the prod-CSV-covered subset only (raw-y ground truth is not available for the rest); read them as indicative, not full-month.

## Headline verdict (canonical per-day-CLEAN caliber = `headline_audit.cd()`, RAW y)

**Run1 beats production on the caliber that matches how we report and how we trade.** Pooled OOS (27,854 per-day non-overlap clean rows):

| metric (pooled) | RUN1 | PROD | Δ |
|---|---|---|---|
| **Pearson cd-CLEAN** (per-day-avg, headline) | **+0.0487** | +0.0398 | **+0.0089 (+22%)** |
| **Spearman cd-CLEAN** | **+0.0572** | +0.0391 | **+0.0181 (+46%)** |
| Pearson DENSE | +0.0264 | +0.0353 | −0.0089 (prod) |
| Spearman DENSE | **+0.0430** | +0.0332 | +0.0098 |
| Pearson pooled-clean (single, not per-day) | +0.0219 | +0.0395 | −0.0176 (prod) |
| corr-R² cd (=Pearson²) | 0.0024 | 0.0016 | Run1 |
| predictive-R² raw / β-rescaled | +0.000 / −0.001 | +0.000 / +0.002 | ~0 both |
| DirAcc overall / **\|y\|>σ** / **top-20% tail** | 0.516 / 0.516 / **0.536** | 0.515 / 0.510 / 0.531 | Run1 on the tradeable ones |
| β (y on ŷ) · σŷ/σy | +0.55 · **0.040** | +11.86 · 0.003 | see note |
| long-short bias (mean ŷ) | −0.014 bps | +0.002 bps | both near-zero ✓ |
| bin-monotonicity spearman · up-steps | +0.552 · 4/9 | — | regime-dependent |

Run1 wins the canonical **cd-CLEAN Pearson (7/10 months)** and **cd-CLEAN Spearman**, wins **Spearman at every caliber**, wins the two **tradeable DirAcc** cuts (|y|>σ and top-20% tail), and has a **healthy non-collapsed prediction distribution** (σŷ/σy 0.040 ≥ 0.02 guard; β 0.55). Production edges Run1 on **DENSE / pooled-clean Pearson only** — a rank-preserving flip explained below.

### The one honest divergence (P_cd ≫ P_dense/P_cln for Run1)
Run1's per-day-avg Pearson (+0.0487) is much higher than its dense (+0.0264) and pooled-clean (+0.0219). Production's three agree (~0.035–0.040). Mechanism: **Run1's alpha is intraday-concentrated** — its per-day ranking is strong, but its predictions carry real cross-day level variation (σŷ/σy 0.040) that is not aligned with the cross-day y level, so pooling across days dilutes the *Pearson* (but not the rank → Spearman still wins). Per-day-CLEAN removes cross-day level and is the caliber the milestone/team uses; it is also the caliber that matches trading (intraday, directional, rank-based), consistent with the taker/maker backtest (Run1 maker-tradeable BE 0.760 vs prod 0.424). Production's flat-across-calibers Pearson comes partly from its much smaller pred variance not being able to inject cross-day noise.

**β / σŷ note (diagnostic, NOT a gate — per the IC/β rule):** β and σŷ/σy are scale-dependent and NOT comparable across the two models — Run1 preds are denormed to bps, production `y_pred_raw` is in raw (un-denormed) model units (std 0.069 vs y-std 20.5 bps). Run1's β 0.55 / σŷ/σy 0.040 are the interpretable, bps-scaled diagnostics (healthy, non-collapsed); prod's β 11.86 / σŷ/σy 0.003 reflect un-denormed units, NOT collapse. Cross-model comparison rests on the scale-invariant metrics (Pearson/Spearman/DirAcc/monotonicity/corr-R²).

## Full per-month battery

`P_cd/S_cd` = per-day-CLEAN (canonical headline). `P_den/S_den` = DENSE. `P_cln` = pooled non-overlap. `corR2cl` = Pearson²_clean. `pR2raw/pR2res` = predictive-R² raw / β-rescaled (clean). `DAcl/DAbig/DAtail` = DirAcc all / |y|>σ / top-20%|ŷ| (clean). β·σŷ from clean; bias = mean ŷ (bps).

### RUN1
```
   month  n_cl   P_cd   S_cd  P_den  S_den  P_cln corR2cl pR2raw pR2res  DAcl DAbig DAtail  beta  sigr   bias
 2025_08* 1027 +0.0498 +0.0400 +0.0214 +0.0306 +0.0376 0.0014 +0.001 +0.001 0.498 0.523 0.490 +1.09 0.034 +0.066
 2025_09*  889 +0.0754 +0.0818 +0.0483 +0.0652 +0.0587 0.0035 +0.002 -0.001 0.521 0.548 0.545 +1.92 0.031 -0.016
 2025_10  3332 +0.1003 +0.1012 +0.0367 +0.0511 +0.0479 0.0023 +0.000 -0.004 0.509 0.530 0.552 +3.45 0.014 +0.281
 2025_11  3332 +0.0545 +0.0581 +0.0507 +0.0465 +0.0631 0.0040 +0.003 +0.001 0.515 0.523 0.525 +2.06 0.031 -0.488
 2025_12  3332 +0.0580 +0.0690 +0.0163 +0.0585 +0.0351 0.0012 +0.001 +0.001 0.513 0.519 0.528 +0.77 0.045 -0.105
 2026_01  3332 +0.0253 +0.0176 +0.0688 +0.0288 +0.0500 0.0025 +0.001 +0.002 0.505 0.514 0.492 +2.73 0.018 -0.039
 2026_02  3332 +0.0078 +0.0283 +0.0227 +0.0484 -0.0004 0.0000 -0.004 -0.003 0.514 0.499 0.543 -0.01 0.061 +0.291
 2026_03  3330 +0.0284 +0.0503 +0.0308 +0.0553 +0.0196 0.0004 +0.000 -0.000 0.519 0.519 0.542 +0.82 0.024 -0.177
 2026_04  3332 +0.0433 +0.0491 +0.0121 +0.0488 +0.0210 0.0004 -0.002 -0.001 0.520 0.507 0.549 +0.28 0.074 +0.072
 2026_05  2616 +0.0534 +0.0890 +0.0420 +0.0614 +0.0301 0.0009 -0.000 -0.001 0.544 0.537 0.553 +0.78 0.038 +0.043
  POOLED 27854 +0.0487 +0.0572 +0.0264 +0.0430 +0.0219 0.0005 +0.000 -0.001 0.516 0.516 0.536 +0.55 0.040 -0.014
```
### PRODUCTION (same nodes, prod y_pred_raw)
```
   month  n_cl   P_cd   S_cd  P_den  S_den  P_cln corR2cl pR2raw pR2res  DAcl DAbig DAtail  beta  sigr   bias
 2025_08* 1027 +0.0407 +0.0496 +0.0372 +0.0351 +0.0392 0.0015 +0.000 +0.001 0.520 0.515 0.537 +24.21 0.002 -0.003
 2025_09*  889 +0.0434 +0.0108 +0.0524 +0.0457 +0.0556 0.0031 +0.000 +0.003 0.497 0.482 0.534 +15.63 0.004 +0.011
 2025_10  3332 +0.0844 +0.0646 +0.0970 +0.0478 +0.0789 0.0062 -0.000 +0.002 0.528 0.518 0.538 +30.88 0.003 +0.003
 2025_11  3332 +0.0671 +0.0593 +0.0536 +0.0441 +0.0806 0.0065 +0.000 +0.005 0.513 0.531 0.567 +22.56 0.004 -0.011
 2025_12  3332 +0.0482 +0.0449 +0.0213 +0.0459 +0.0295 0.0009 +0.000 +0.000 0.509 0.500 0.539 +15.15 0.002 +0.005
 2026_01  3332 +0.0304 +0.0136 +0.0432 +0.0163 +0.0463 0.0021 -0.000 +0.001 0.506 0.489 0.504 +20.66 0.002 +0.031
 2026_02  3332 +0.0183 +0.0205 +0.0198 +0.0220 +0.0162 0.0003 -0.000 +0.000 0.516 0.518 0.493 +7.65 0.002 -0.029
 2026_03  3330 +0.0139 +0.0291 +0.0225 +0.0219 +0.0340 0.0012 +0.000 +0.001 0.512 0.488 0.544 +10.45 0.003 -0.003
 2026_04  3332 +0.0312 +0.0489 +0.0212 +0.0429 +0.0189 0.0004 +0.000 -0.000 0.526 0.527 0.546 +2.64 0.007 -0.000
 2026_05  2616 +0.0162 +0.0435 +0.0187 +0.0444 +0.0026 0.0000 -0.001 -0.002 0.517 0.520 0.532 +0.61 0.004 +0.019
  POOLED 27854 +0.0398 +0.0391 +0.0353 +0.0332 +0.0395 0.0016 +0.000 +0.002 0.515 0.510 0.531 +11.86 0.003 +0.002
```
`*` = partial raw-y coverage (see table above).

## Bin monotonicity (Run1 pooled CLEAN, decile ŷ → mean realized y_bps)
```
 bin:      0     1     2     3     4     5     6     7     8     9
 mean y:-1.49 +0.25 -0.14 -0.44 -0.48 -0.07 +0.18 -0.08 +0.35 +0.20   spearman +0.552, up-steps 4/9
```
Bottom decile most-negative (−1.49) and top decile positive (+0.20) — directionally correct extremes — but the middle is noisy (only 4/9 monotone up-steps). **Monotonicity is regime-dependent:** strong/trending months clean (2025_10 +0.68, 2025_11 +0.71), choppy-drift months break (2026_02 +0.08, 2026_04 +0.14). Consistent with the regime-dependence of the signal.

## Honest read
1. **R² is ~0 everywhere** (corr-R² 0.0005–0.0024; predictive-R² ~0.000): the signal's value is in **rank/sign**, not variance reduction — expected for the R²<1% regime; predictive-R² is the wrong lens (and scale-dependent), corr-R² is the honest information measure.
2. **Run1 > production on the tradeable/rank metrics** (cd Pearson +22%, cd Spearman +46%, DA |y|>σ and tail, calibration health), reinforcing the backtest verdict (Run1 maker-tradeable & > prod). The single caliber where prod leads — DENSE/pooled Pearson — is a level-noise/scale artifact that Spearman and per-day-CLEAN both reverse.
3. **DirAcc is modest** (tradeable cuts ~0.52–0.54) and **taker-cost still binds** (see the taker/maker verdict: maker-only at ≤0.76 bps/side, not taker-tradeable). This report characterizes the base model's information; it does not change the net-of-cost conclusion.

**Caliber cross-check:** `P_cd` reproduces `headline_audit.cd()` exactly (2025-10 raw-y: 0.1003 = 0.1003). 0B cross-check requested.
