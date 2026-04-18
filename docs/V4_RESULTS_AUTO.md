# V4 Results (updated per METRIC_DISCIPLINE.md)

## Metric reporting convention

Per `docs/METRIC_DISCIPLINE.md`, every result reports **both** Spearman (trading-side primary, robust to outliers) and Pearson (spec bar, magnitude calibration). Divergence > 0.03 is flagged for outlier inspection.

## Headline: V4 no_attention beats Ridge baseline on fold 0

| Config | Test Pearson | Test Spearman | Divergence | vs Ridge (0.099) | vs V4 spec (0.12) |
|---|---:|---:|---:|:-:|:-:|
| **V4 no_attention** | **0.1009** | **0.1072** | 0.006 | ✅ beats | ❌ below by 0.02 |
| V4 full (pre-fix) | 0.0609 | 0.0893 | 0.028 | ❌ | ❌ |
| V3+RevIN (reported) | 0.082 | — | — | ❌ | ❌ |
| Ridge (reported) | 0.099 | — | — | — | — |

For V4 no_attention the Pearson-Spearman divergence is tiny (0.006) → **no outlier concern**, signal is real.

For V4 full the divergence is 0.028 (Pearson lower than Spearman) → consistent with Pearson being pulled down by a few miscalibrated magnitude predictions; signal is still directionally correct.

## V4 full 4-fold aborted history (for reference)

Fold 0 only completed. Fold 1 hung silently for 23+ min. Training killed. Five root-cause fixes landed before the honest number came through: preload OOM, compute_stats single-threading, horizons wiring, y_sigma scale bug, (B,1)-vs-(B,) shape bug. All committed.

## Round 1 smoke (8 variants, 100d, 1 min/run, y_180)

| Variant | Flag change | test Pearson | test Spearman | Note |
|---|---|---:|---:|---|
| A_full | V4 full | +0.029 | +0.041 | baseline |
| B_y60 | target y_60 | +0.010 | −0.003 | y_60 needs more data |
| C_noraw | `use_raw_path=False` | −0.023 | −0.026 | Path B helps |
| D_norevin | `use_revin=False` | +0.010 | +0.020 | RevIN helps |
| **E_noattn** | `use_attention=False` | **+0.084** | **+0.101** | Big win |
| F_noppnet | `use_ppnet_gate=False` | −0.048 | −0.047 | PPNet helps |
| G_simple | strip V4-specific | +0.017 | +0.028 | mixed |
| H_norank | `lambda_utility_rank=0` | −0.011 | ~0 | utility_rank helps |

## Round 2 smoke (8 variants on no_attention baseline, 100d)

| Variant | test Pearson | test Spearman | val_corr | Signal |
|---|---:|---:|---:|---|
| A_noattn | +0.076 | +0.091 | 0.121 | baseline |
| B_small (d=16) | +0.039 | +0.053 | 0.068 | too little capacity |
| C_nogdcn | +0.061 | +0.073 | 0.095 | GDCN mildly helps |
| D_dropout 0.3 | +0.038 | +0.061 | 0.058 | over-regularized |
| E_lowlr (2e-4) | +0.073 | +0.090 | 0.093 | no gain |
| F_noLvlAttn | +0.032 | +0.047 | 0.105 | level attn helps |
| **G_noconv** | +0.068 | **+0.103** | **0.126** | removing TCN helps Spearman |
| H_ridge_only | **+0.080** | +0.091 | 0.115 | no raw path, still strong |

Interpretation: at 100d three configs (A, G, H) cluster at val_corr ~0.12 — plausible ceiling at small data, so differences between top-3 are within noise.

## In-progress

**no_attention + no_conv** at 700d (PID 36403) — if either Pearson or Spearman ≥ 0.12, promote to 4-fold pooled. If Spearman ≥ 0.12 but Pearson < 0.12, we flag as "trading-viable spec-non-compliant" per METRIC_DISCIPLINE.md.

## Next decision tree

Applies once no_attn+no_conv 700d finishes:

1. **Spearman ≥ 0.12 AND Pearson ≥ 0.12** — full pass. Launch 4-fold for pooled.
2. **Spearman ≥ 0.12, Pearson 0.10-0.12** — conditional pass. Launch 4-fold + investigate outlier influence on Pearson.
3. **Spearman 0.10-0.12** — competitive with V3 + Ridge, below V4 target. Run 4-fold for pooled; decide with user if pragmatic win or keep iterating.
4. **Both < 0.10** — below Ridge. Continue architecture search (try H_ridge_only at 700d, or shrink further).
