> **创建:** 2026-06-21 00:30 UTC | **Session:** dual-source-v2 Gate 1 | **状态:** final | **作废条件:** 若 RG-FiLM 以非 multiplicative 形式重测且 PASS

# GATE 1 — RG regime FiLM conditioning (perp y_600, STRONG folds)

Generated: Sun Jun 21 12:06:27 AM UTC 2026

## Fold day-lists (apples-to-apples check)
```
[train_dual_lob] Fold 0: train=2024-01-01..2024-11-30(335d) val=2024-12-02..2025-01-30 test=2025-02-01..2025-02-28
[train_dual_lob] Fold 1: train=2024-01-01..2025-01-28(394d) val=2025-01-30..2025-03-30 test=2025-04-01..2025-04-28
```

## perp_battery — BEST ckpt (dense + CLEAN, per-month + pooled)
```

======================================================================================
MODEL: BASELINE_matched   ckpt=best
======================================================================================

[DENSE]  (raw y, masked)
month   regime         N   Pearson  Spearman     beta   sig_r   mono   bias_bps
--------------------------------------------------------------------------------------
2025-02 STRONG     13272    0.0261    0.0209    0.561  0.0466   0.44    -0.0279
2025-04 STRONG     13272   -0.0140   -0.0009   -0.972  0.0144  -0.15     0.9501
--------------------------------------------------------------------------------------
POOLED             26544    0.0236    0.0206    0.558  0.0423   0.82     0.4611

[CLEAN]  (raw y, masked; clean stride>=600s)
month   regime         N   Pearson  Spearman     beta   sig_r   mono   bias_bps
--------------------------------------------------------------------------------------
2025-02 STRONG      3318   -0.0096    0.0024   -0.214  0.0447  -0.05    -0.0307
2025-04 STRONG      3318   -0.0351   -0.0071   -2.502  0.0140  -0.37     0.9423
--------------------------------------------------------------------------------------
POOLED              6636    0.0022    0.0176    0.054  0.0410   0.48     0.4558

======================================================================================
MODEL: RG_enriched   ckpt=best
======================================================================================

[DENSE]  (raw y, masked)
month   regime         N   Pearson  Spearman     beta   sig_r   mono   bias_bps
--------------------------------------------------------------------------------------
2025-02 STRONG     13272    0.0138   -0.0025    0.339  0.0406  -0.38     0.4720
2025-04 STRONG     13272    0.0147    0.0233    0.460  0.0320   0.24     0.0380
--------------------------------------------------------------------------------------
POOLED             26544    0.0082    0.0076    0.214  0.0382   0.03     0.2550

[CLEAN]  (raw y, masked; clean stride>=600s)
month   regime         N   Pearson  Spearman     beta   sig_r   mono   bias_bps
--------------------------------------------------------------------------------------
2025-02 STRONG      3318   -0.0381   -0.0374   -0.976  0.0391  -0.66     0.4670
2025-04 STRONG      3318   -0.0082    0.0141   -0.266  0.0307  -0.14     0.0333
--------------------------------------------------------------------------------------
POOLED              6636   -0.0311   -0.0126   -0.845  0.0368  -0.67     0.2501

######################################################################################
FROZEN-vs-ROLLING DELTA  (RG_enriched - BASELINE_matched)   ckpt=best
######################################################################################

[DENSE] pooled delta
metric        BASELINE_matched   RG_enriched         delta
--------------------------------------------------------
Pearson               0.0236        0.0082       -0.0154
Spearman              0.0206        0.0076       -0.0130
beta                   0.558         0.214        -0.344
sigma_ratio           0.0423        0.0382       -0.0041
monotonicity            0.82          0.03         -0.79
bias_bps              0.4611        0.2550       -0.2061

[CLEAN] pooled delta
metric        BASELINE_matched   RG_enriched         delta
--------------------------------------------------------
Pearson               0.0022       -0.0311       -0.0333
Spearman              0.0176       -0.0126       -0.0302
beta                   0.054        -0.845        -0.900
sigma_ratio           0.0410        0.0368       -0.0042
monotonicity            0.48         -0.67         -1.15
bias_bps              0.4558        0.2501       -0.2056

saved metrics json -> /tmp/gate1_best.json
```

## perp_battery — EMA ckpt (dense + CLEAN, per-month + pooled)
```

======================================================================================
MODEL: BASELINE_matched   ckpt=ema
======================================================================================

[DENSE]  (raw y, masked)
month   regime         N   Pearson  Spearman     beta   sig_r   mono   bias_bps
--------------------------------------------------------------------------------------
2025-02 STRONG     13272    0.0324    0.0331    1.227  0.0264   0.55     0.2418
2025-04 STRONG     13272   -0.0217   -0.0005   -1.410  0.0154  -0.01     1.1264
--------------------------------------------------------------------------------------
POOLED             26544    0.0230    0.0254    0.752  0.0306   0.72     0.6841

[CLEAN]  (raw y, masked; clean stride>=600s)
month   regime         N   Pearson  Spearman     beta   sig_r   mono   bias_bps
--------------------------------------------------------------------------------------
2025-02 STRONG      3318   -0.0008    0.0245   -0.030  0.0252  -0.02     0.2399
2025-04 STRONG      3318   -0.0292   -0.0019   -1.982  0.0147  -0.31     1.1203
--------------------------------------------------------------------------------------
POOLED              6636    0.0096    0.0279    0.324  0.0296   0.73     0.6801

======================================================================================
MODEL: RG_enriched   ckpt=ema
======================================================================================

[DENSE]  (raw y, masked)
month   regime         N   Pearson  Spearman     beta   sig_r   mono   bias_bps
--------------------------------------------------------------------------------------
2025-02 STRONG     13272   -0.0119    0.0095   -0.123  0.0972   0.12     0.5718
2025-04 STRONG     13272    0.0149    0.0326    0.649  0.0230   0.45    -0.0963
--------------------------------------------------------------------------------------
POOLED             26544   -0.0103    0.0097   -0.139  0.0738  -0.16     0.2377

[CLEAN]  (raw y, masked; clean stride>=600s)
month   regime         N   Pearson  Spearman     beta   sig_r   mono   bias_bps
--------------------------------------------------------------------------------------
2025-02 STRONG      3318   -0.0329   -0.0043   -0.327  0.1008  -0.30     0.5976
2025-04 STRONG      3318   -0.0118    0.0135   -0.528  0.0224  -0.09    -0.0963
--------------------------------------------------------------------------------------
POOLED              6636   -0.0296   -0.0105   -0.387  0.0765  -0.61     0.2506

######################################################################################
FROZEN-vs-ROLLING DELTA  (RG_enriched - BASELINE_matched)   ckpt=ema
######################################################################################

[DENSE] pooled delta
metric        BASELINE_matched   RG_enriched         delta
--------------------------------------------------------
Pearson               0.0230       -0.0103       -0.0332
Spearman              0.0254        0.0097       -0.0157
beta                   0.752        -0.139        -0.890
sigma_ratio           0.0306        0.0738       +0.0433
monotonicity            0.72         -0.16         -0.88
bias_bps              0.6841        0.2377       -0.4463

[CLEAN] pooled delta
metric        BASELINE_matched   RG_enriched         delta
--------------------------------------------------------
Pearson               0.0096       -0.0296       -0.0392
Spearman              0.0279       -0.0105       -0.0385
beta                   0.324        -0.387        -0.710
sigma_ratio           0.0296        0.0765       +0.0468
monotonicity            0.73         -0.61         -1.35
bias_bps              0.6801        0.2506       -0.4294

saved metrics json -> /tmp/gate1_ema.json
```

## per-day q50_std (blowup check, BEST preds)
```

=== BASELINE ===
  fold_0: overall q50_std(bps)=0.976
      2025-02-01 n= 477 q50_std=  0.369bps
      2025-02-02 n= 477 q50_std=  1.089bps
      2025-02-03 n= 477 q50_std=  2.782bps
      2025-02-04 n= 477 q50_std=  1.016bps
      2025-02-05 n= 477 q50_std=  0.551bps
      2025-02-06 n= 477 q50_std=  0.579bps
      2025-02-07 n= 477 q50_std=  0.627bps
      2025-02-08 n= 477 q50_std=  0.341bps
      2025-02-09 n= 477 q50_std=  0.379bps
      2025-02-10 n= 477 q50_std=  0.513bps
      2025-02-11 n= 477 q50_std=  0.490bps
      2025-02-12 n= 477 q50_std=  0.598bps
      2025-02-13 n= 477 q50_std=  0.578bps
      2025-02-14 n= 477 q50_std=  0.438bps
      2025-02-15 n= 477 q50_std=  0.332bps
      2025-02-16 n= 477 q50_std=  0.337bps
      2025-02-17 n= 477 q50_std=  0.409bps
      2025-02-18 n= 477 q50_std=  0.540bps
      2025-02-19 n= 477 q50_std=  0.417bps
      2025-02-20 n= 477 q50_std=  0.406bps
      2025-02-21 n= 477 q50_std=  0.827bps
      2025-02-22 n= 477 q50_std=  0.339bps
      2025-02-23 n= 477 q50_std=  0.317bps
      2025-02-24 n= 477 q50_std=  0.687bps
      2025-02-25 n= 477 q50_std=  1.873bps
      2025-02-26 n= 477 q50_std=  1.348bps
      2025-02-27 n= 477 q50_std=  0.718bps
      2025-02-28 n= 477 q50_std=  2.144bps
  fold_1: overall q50_std(bps)=0.292
      2025-04-01 n= 477 q50_std=  0.268bps
      2025-04-02 n= 477 q50_std=  0.339bps
      2025-04-03 n= 477 q50_std=  0.274bps
      2025-04-04 n= 477 q50_std=  0.323bps
      2025-04-05 n= 477 q50_std=  0.211bps
      2025-04-06 n= 477 q50_std=  0.364bps
      2025-04-07 n= 477 q50_std=  0.453bps
      2025-04-08 n= 477 q50_std=  0.295bps
      2025-04-09 n= 477 q50_std=  0.388bps
      2025-04-10 n= 477 q50_std=  0.299bps
      2025-04-11 n= 477 q50_std=  0.329bps
      2025-04-12 n= 477 q50_std=  0.232bps
      2025-04-13 n= 477 q50_std=  0.276bps
      2025-04-14 n= 477 q50_std=  0.301bps
      2025-04-15 n= 477 q50_std=  0.277bps
      2025-04-16 n= 477 q50_std=  0.255bps
      2025-04-17 n= 477 q50_std=  0.230bps
      2025-04-18 n= 477 q50_std=  0.173bps
      2025-04-19 n= 477 q50_std=  0.203bps
      2025-04-20 n= 477 q50_std=  0.172bps
      2025-04-21 n= 477 q50_std=  0.280bps
      2025-04-22 n= 477 q50_std=  0.344bps
      2025-04-23 n= 477 q50_std=  0.285bps
      2025-04-24 n= 477 q50_std=  0.271bps
      2025-04-25 n= 477 q50_std=  0.278bps
      2025-04-26 n= 477 q50_std=  0.177bps
      2025-04-27 n= 477 q50_std=  0.202bps
      2025-04-28 n= 477 q50_std=  0.259bps

=== RG ===
  fold_0: overall q50_std(bps)=0.851
      2025-02-01 n= 477 q50_std=  0.135bps
      2025-02-02 n= 477 q50_std=  0.725bps
      2025-02-03 n= 477 q50_std=  2.411bps
      2025-02-04 n= 477 q50_std=  0.936bps
      2025-02-05 n= 477 q50_std=  0.455bps
      2025-02-06 n= 477 q50_std=  0.316bps
      2025-02-07 n= 477 q50_std=  0.465bps
      2025-02-08 n= 477 q50_std=  0.148bps
      2025-02-09 n= 477 q50_std=  0.213bps
      2025-02-10 n= 477 q50_std=  0.340bps
      2025-02-11 n= 477 q50_std=  0.289bps
      2025-02-12 n= 477 q50_std=  0.350bps
      2025-02-13 n= 477 q50_std=  0.397bps
      2025-02-14 n= 477 q50_std=  0.206bps
      2025-02-15 n= 477 q50_std=  0.114bps
      2025-02-16 n= 477 q50_std=  0.287bps
      2025-02-17 n= 477 q50_std=  0.179bps
      2025-02-18 n= 477 q50_std=  0.358bps
      2025-02-19 n= 477 q50_std=  0.218bps
      2025-02-20 n= 477 q50_std=  0.144bps
      2025-02-21 n= 477 q50_std=  0.525bps
      2025-02-22 n= 477 q50_std=  0.088bps
      2025-02-23 n= 477 q50_std=  0.072bps
      2025-02-24 n= 477 q50_std=  0.592bps
      2025-02-25 n= 477 q50_std=  1.271bps
      2025-02-26 n= 477 q50_std=  0.988bps
      2025-02-27 n= 477 q50_std=  0.678bps
      2025-02-28 n= 477 q50_std=  2.057bps
  fold_1: overall q50_std(bps)=0.648
      2025-04-01 n= 477 q50_std=  0.451bps
      2025-04-02 n= 477 q50_std=  0.760bps
      2025-04-03 n= 477 q50_std=  0.564bps
      2025-04-04 n= 477 q50_std=  0.778bps
      2025-04-05 n= 477 q50_std=  0.357bps
      2025-04-06 n= 477 q50_std=  1.008bps
      2025-04-07 n= 477 q50_std=  1.011bps
      2025-04-08 n= 477 q50_std=  0.825bps
      2025-04-09 n= 477 q50_std=  0.886bps
      2025-04-10 n= 477 q50_std=  0.653bps
      2025-04-11 n= 477 q50_std=  0.726bps
      2025-04-12 n= 477 q50_std=  0.466bps
      2025-04-13 n= 477 q50_std=  0.670bps
      2025-04-14 n= 477 q50_std=  0.665bps
      2025-04-15 n= 477 q50_std=  0.520bps
      2025-04-16 n= 477 q50_std=  0.576bps
      2025-04-17 n= 477 q50_std=  0.422bps
      2025-04-18 n= 477 q50_std=  0.257bps
      2025-04-19 n= 477 q50_std=  0.278bps
      2025-04-20 n= 477 q50_std=  0.288bps
      2025-04-21 n= 477 q50_std=  0.568bps
      2025-04-22 n= 477 q50_std=  0.754bps
      2025-04-23 n= 477 q50_std=  0.746bps
      2025-04-24 n= 477 q50_std=  0.501bps
      2025-04-25 n= 477 q50_std=  0.573bps
      2025-04-26 n= 477 q50_std=  0.319bps
      2025-04-27 n= 477 q50_std=  0.358bps
      2025-04-28 n= 477 q50_std=  0.474bps
```
DONE_EVAL

---
## GATE 1 VERDICT: **FAIL**

**Gate criteria:** RG ΔP ≥ +0.003 over matched baseline, sign-consistent across BOTH strong folds, CLEAN caliber, β healthy (0.5-1.5), no per-day blowup.

### Decisive numbers (BEST ckpt, CLEAN caliber — primary)
| metric | fold-0 (2025-02) | fold-1 (2025-04) | POOLED |
|---|---|---|---|
| BASELINE P | -0.0096 | -0.0351 | +0.0022 |
| RG P       | -0.0381 | -0.0082 | -0.0311 |
| **ΔP (RG-base)** | **-0.0285** | **+0.0269** | **-0.0333** |
| RG β (CLEAN) | -0.976 | -0.266 | -0.845 |

### Why FAIL (4 independent reasons, any one is disqualifying)
1. **Pooled ΔP = -0.0333 << +0.003** (BEST). EMA even worse (-0.0392). Far below threshold AND negative.
2. **Sign-INCONSISTENT across folds:** RG HURTS fold-0 (-0.0285) but HELPS fold-1 (+0.0269). The two strong folds disagree in sign -> not a robust improvement, exactly the per-fold-flip the gate guards against. (Matches val: RG fold-0 valP 0.035 vs base 0.048 = -0.013; RG fold-1 valP 0.041 vs base 0.015 = +0.027.)
3. **β destroyed:** RG CLEAN pooled β = -0.845 (baseline +0.054); per-fold RG β -0.976/-0.266 — all NEGATIVE/out of [0.5,1.5]. FiLM regime gate corrupted calibration (sign flip = anti-predictive on clean caliber). EMA RG σ_ratio inflated to 0.0765 (over-spread).
4. (Bounding worked: RG channels finite, no per-day q50_std blowup — fold-0 0.851bps, fold-1 0.648bps, no >3x spikes. So FAIL is signal-quality, NOT an OOD/instability artifact.)

### Interpretation
- RG-FiLM is a net-negative perp lever on the matched dual-source model. The factor-study positive (perp_y +0.0061 strong / +0.0036 choppy) does NOT transfer when RG enters as a multiplicative FiLM gate on this backbone.
- The fold-1 help is real but regime-specific (2025-04 had a strong directional move RG could condition on); fold-0 (2025-02, chop) it actively hurt. A lever that flips sign by month is not deployable.
- Both arms are weak/negative on the strict CLEAN ::4 caliber even at baseline (pooled +0.0022 / +0.0096) — consistent with the known perp-book being ~2x less predictive than spot-book and 2025 being a weak regime. RG does not rescue this; it degrades it.

### Decision
**Do NOT merge RG-FiLM conditioning.** Gate 1 fails on ΔP magnitude, sign, and β. Per spec: Gate 1 only — do not proceed to other levers. RG builder integration (build_dualsrc_rg_npz.py + config) committed locally for reproducibility; the model change is rejected.
