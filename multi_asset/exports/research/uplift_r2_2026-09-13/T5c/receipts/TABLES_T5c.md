# TABLES · T5c (rendered by `devices/t5c_tables.py` from receipts; do not edit by hand)

King chain only (V2MAIN arm NOT MEASURED). Window 2026-08-31 00:00Z .. 2026-09-10 00:00Z, 61 anchors, 11 UTC-day blocks — **CIs are descriptive**. Units bps / 4h anchor / unit gross of the book. D_K = deployed king chain (state_H_kc); R_K = A0 replay king chain (KA lineage). Target layer only. Rendered 2026-09-13T08:27:50Z.

## T0 · gates
| gate | result |
|---|---|
| G-UM (carry-forward mask) | True; prefix 10039 rows bitwise, 60 rows added = last row |
| G-X (KA runs vs T1 C0 arms, anchors <= 08-30 20Z) | True; 20 arrays bitwise per seed, 10038 rows |
| G-KC (8d79186b on v4 x0910 features vs A0 king, 2026 overlap; not blocking) | bitwise 94.0% of 572435 cells; member Spearman median 1.0000, min 0.9027; by month median Jan–Jul 1.0000, **Aug 0.9620** ⇒ label: feature-lineage switch |
| KA array | prefix copy bitwise True; extension 66 anchors × 400–400 names; sha `af379984c688…` |
| G-RAW (device y4 == x0910 meta == dlw RAW y4s) | True |
| G-SIM-R (king chain + legs vs device, 66 anchors, KA and KB, both seeds) | True; max|Δ| KA_s42 0.0e+00/0.0e+00, KA_s2027 0.0e+00/0.0e+00, KB_s42 0.0e+00/0.0e+00, KB_s2027 0.0e+00/0.0e+00 |
| G-T1c (deployed book vs T1 D2; T5 §6.2 short price) | True; 61 anchors, max|Δ| price 2.2e-14, carry 0.0e+00; short price -4.5274112841 vs -4.5274112841 |
| G-CLOSE (Shapley and fixed order, P/C/K/N, per anchor) | True; max 3.6e-14 |
| G-ARCH-D (target_live = 0.55·kc + 0.45·fc, 66 anchors) | True; max|Δ| 0.0e+00 |
| G-ING-S (sel count = producer log; archived nonzero ⊆ pm∩sel∩LIVE) | True; violations 0; count mismatches 0 |
| G-ING-V (backward EMA 09-13 → 09-04 00Z reproduces stored fund z) | True; max|Δz| 0.0e+00 |
| G-ING-B (M1 base) | **False** — (i) 09-13 04Z M1 fund z max|Δ| 0.0e+00, old z 0.0e+00, fund_base_n 523 = 523; (ii) per-anchor fund_base_n mismatches at 2026-09-04 04:00Z, 2026-09-04 08:00Z: 2026-09-04 04:00Z recon 522 vs logged 449; 2026-09-04 08:00Z recon 522 vs logged 460 |
| G-ING-T (FTRIM-recorded rn8 vs ledger reconstruction) | True; 844 names checked, max|Δ| 0.0e+00, missing 0 |
| G-POD | GPU 0 %, 2 MiB → 0 %, 2 MiB; PIDs 333197 Tl;  339489 Tl → 333197 Tl;  339489 Tl |

## T1 · readings (PREREG §6; label needs both seeds)
| lineage · seed | outcome | D_K mean | R_K mean | D_K − R_K | SAME-LOSS | GAP | label | label excl. 09-06 |
|---|---|---|---|---|---|---|---|---|
| KA_s42 | price | -5.96 [-15.89, +2.82] | -4.76 [-13.05, +3.04] | -1.20 [-4.19, +1.59] | True | False | STRATEGY'S OWN LOSS (king chain) | STRATEGY'S OWN LOSS (king chain) |
| KA_s42 | carry | +1.18 [+0.69, +1.75] | +1.00 [+0.87, +1.13] | +0.18 [-0.22, +0.63] | True | False | STRATEGY'S OWN LOSS (king chain) | STRATEGY'S OWN LOSS (king chain) |
| KA_s42 | cost | +0.08 [+0.08, +0.09] | +0.11 [+0.10, +0.12] | -0.02 [-0.04, -0.01] | False | True | DEPLOYMENT DIFFERENCE | DEPLOYMENT DIFFERENCE |
| KA_s42 | net | -7.23 [-17.03, +1.45] | -5.87 [-14.12, +1.89] | -1.36 [-4.35, +1.43] | True | False | STRATEGY'S OWN LOSS (king chain) | STRATEGY'S OWN LOSS (king chain) |
| KA_s2027 | price | -5.96 [-15.89, +2.82] | -5.07 [-13.39, +2.87] | -0.90 [-3.87, +1.81] | True | False | STRATEGY'S OWN LOSS (king chain) | STRATEGY'S OWN LOSS (king chain) |
| KA_s2027 | carry | +1.18 [+0.69, +1.75] | +1.00 [+0.87, +1.13] | +0.18 [-0.23, +0.63] | True | False | STRATEGY'S OWN LOSS (king chain) | STRATEGY'S OWN LOSS (king chain) |
| KA_s2027 | cost | +0.08 [+0.08, +0.09] | +0.11 [+0.09, +0.12] | -0.02 [-0.04, -0.01] | False | True | DEPLOYMENT DIFFERENCE | DEPLOYMENT DIFFERENCE |
| KA_s2027 | net | -7.23 [-17.03, +1.45] | -6.17 [-14.47, +1.68] | -1.05 [-4.05, +1.71] | True | False | STRATEGY'S OWN LOSS (king chain) | STRATEGY'S OWN LOSS (king chain) |
| KB_s42 (sensitivity) | price | -5.96 [-15.89, +2.82] | -4.39 [-12.84, +3.96] | -1.57 [-4.56, +1.37] | True | False | STRATEGY'S OWN LOSS (king chain) | STRATEGY'S OWN LOSS (king chain) |
| KB_s42 (sensitivity) | carry | +1.18 [+0.69, +1.75] | +1.00 [+0.86, +1.14] | +0.18 [-0.22, +0.62] | True | False | STRATEGY'S OWN LOSS (king chain) | STRATEGY'S OWN LOSS (king chain) |
| KB_s42 (sensitivity) | net | -7.23 [-17.03, +1.45] | -5.49 [-13.85, +2.79] | -1.73 [-4.81, +1.22] | True | False | STRATEGY'S OWN LOSS (king chain) | STRATEGY'S OWN LOSS (king chain) |
| KB_s2027 (sensitivity) | price | -5.96 [-15.89, +2.82] | -4.38 [-12.89, +4.03] | -1.58 [-4.54, +1.32] | True | False | STRATEGY'S OWN LOSS (king chain) | STRATEGY'S OWN LOSS (king chain) |
| KB_s2027 (sensitivity) | carry | +1.18 [+0.69, +1.75] | +1.00 [+0.86, +1.14] | +0.18 [-0.22, +0.62] | True | False | STRATEGY'S OWN LOSS (king chain) | STRATEGY'S OWN LOSS (king chain) |
| KB_s2027 (sensitivity) | net | -7.23 [-17.03, +1.45] | -5.48 [-13.91, +2.85] | -1.74 [-4.73, +1.17] | True | False | STRATEGY'S OWN LOSS (king chain) | STRATEGY'S OWN LOSS (king chain) |

## T2 · levels (descriptive; same for both seeds except R_K)
| book | price | carry | cost | net |
|---|---|---|---|---|
| D_K | -5.96 [-15.89, +2.82] | +1.18 [+0.69, +1.75] | +0.082 [+0.076, +0.088] | -7.23 [-17.03, +1.45] |
| R_K (KA s42) | -4.76 [-13.05, +3.04] | +1.00 [+0.87, +1.13] | +0.107 [+0.095, +0.120] | -5.87 [-14.12, +1.89] |
| D_B | -5.36 [-15.77, +3.51] | +1.17 [+0.68, +1.71] | +0.099 [+0.092, +0.109] | -6.63 [-16.68, +2.16] |
| D_F | -4.42 [-15.27, +4.56] | +1.12 [+0.67, +1.63] | +0.126 [+0.106, +0.156] | -5.67 [-16.14, +3.20] |
| R_K (KA s2027) | -5.07 [-13.39, +2.87] | +1.00 [+0.87, +1.13] | +0.106 [+0.095, +0.120] | -6.17 [-14.47, +1.68] |

Deployed book vs deployed king chain, price per anchor: correlation 0.9951; mean(D_B − D_K) +0.60 [-0.16, +1.34].

## T3a · price gap decomposition (Shapley primary; bps/anchor means with CI; shares shown but unstable when the gap CI contains 0)

| component | s42 mean | s42 share | s2027 mean | s2027 share | fixed order s42 / s2027 | one-at-a-time s42 | leave-one-out s42 |
|---|---|---|---|---|---|---|---|
| T FTRIM (D: none before 09-02 12Z, ledger rule after) | +1.32 [+0.20, +2.56] | -110% [-847, +914] | +1.32 [+0.19, +2.56] | -147% [-1185, +1068] | +1.15 / +1.14 | +1.15 | +1.38 |
| W seat (D: archived w3m, seeded from 09-05 16Z) | +0.49 [-0.70, +1.87] | -41% [-594, +621] | +0.48 [-0.71, +1.85] | -53% [-820, +532] | +0.48 / +0.50 | +0.47 | +0.37 |
| B fund rank base (D: members before 09-04 04Z, M1 base after) | -0.13 [-0.61, +0.26] | +10% [-86, +129] | -0.14 [-0.62, +0.25] | +16% [-126, +168] | -0.29 / -0.34 | -0.38 | +0.10 |
| V fund values / freshness | -0.55 [-1.53, +0.29] | +46% [-278, +364] | -0.57 [-1.56, +0.28] | +64% [-345, +520] | -0.33 / -0.36 | -0.88 | -0.57 |
| M member set | +0.01 [-3.45, +3.87] | -1% [-851, +915] | +0.02 [-3.45, +3.88] | -2% [-1090, +1133] | +0.04 / +0.08 | +0.35 | -0.64 |
| X exit rule | -0.14 [-0.59, +0.22] | +12% [-97, +109] | -0.15 [-0.59, +0.21] | +17% [-143, +165] | -0.42 / -0.43 | -0.61 | +0.00 |
| S eligibility | -0.19 [-0.49, +0.09] | +16% [-72, +108] | -0.20 [-0.50, +0.08] | +23% [-98, +167] | -0.01 / -0.01 | -0.77 | -0.03 |
| P replay per-name stop layer | -1.15 [-3.41, +0.39] | +96% [-711, +750] | -0.80 [-2.75, +0.55] | +89% [-560, +861] | -1.04 / -0.69 | -1.13 | -1.10 |
| H state path (D: 08-30 04Z warm start) | -0.24 [-0.83, +0.31] | +20% [-178, +190] | -0.24 [-0.82, +0.30] | +26% [-197, +248] | -0.16 / -0.16 | -0.42 | -0.16 |
| REM king-score differences + unreconciled | -0.62 [-1.32, +0.08] | +52% [-296, +374] | -0.62 [-1.32, +0.08] | +69% [-376, +559] | — | — | — |
| **total D_K − R_K** | -1.20 [-3.97, +1.54] | | -0.90 [-3.73, +1.79] | | excl. 09-06: -0.81 [-4.04, +2.20] / -0.46 [-3.56, +2.42] | | |

Period means (s42): φ_T before/after 09-02 12Z +3.52 / +0.60; φ_B before/after 09-04 04Z -0.14 / -0.11; φ_W before/after 09-05 16Z +1.61 / -0.92; REM before/after 09-01 08Z -0.41 / -0.65.

## T3b · carry gap decomposition (Shapley primary; bps/anchor means with CI; shares shown but unstable when the gap CI contains 0)

| component | s42 mean | s42 share | s2027 mean | s2027 share | fixed order s42 / s2027 | one-at-a-time s42 | leave-one-out s42 |
|---|---|---|---|---|---|---|---|
| T FTRIM (D: none before 09-02 12Z, ledger rule after) | +0.42 [+0.10, +0.80] | +233% [-1384, +1661] | +0.42 [+0.10, +0.80] | +234% [-1416, +1672] | +0.43 / +0.43 | +0.43 | +0.40 |
| W seat (D: archived w3m, seeded from 09-05 16Z) | -0.02 [-0.04, +0.00] | -9% [-47, +34] | -0.02 [-0.04, +0.00] | -9% [-44, +37] | -0.06 / -0.06 | +0.01 | -0.04 |
| B fund rank base (D: members before 09-04 04Z, M1 base after) | -0.06 [-0.07, -0.06] | -35% [-358, +322] | -0.06 [-0.07, -0.06] | -35% [-351, +346] | -0.14 / -0.14 | -0.14 | +0.02 |
| V fund values / freshness | -0.08 [-0.11, -0.02] | -42% [-442, +345] | -0.08 [-0.11, -0.02] | -43% [-408, +362] | -0.04 / -0.04 | -0.22 | +0.05 |
| M member set | -0.09 [-0.26, +0.01] | -49% [-638, +612] | -0.09 [-0.26, +0.01] | -49% [-626, +622] | -0.04 / -0.04 | -0.14 | -0.05 |
| X exit rule | -0.01 [-0.02, -0.00] | -7% [-74, +74] | -0.01 [-0.02, -0.00] | -7% [-71, +74] | -0.01 / -0.01 | -0.03 | +0.00 |
| S eligibility | -0.01 [-0.02, -0.00] | -7% [-79, +77] | -0.01 [-0.02, -0.00] | -7% [-77, +74] | -0.00 / -0.00 | -0.05 | -0.00 |
| P replay per-name stop layer | +0.02 [+0.00, +0.03] | +9% [-101, +100] | +0.02 [+0.00, +0.03] | +9% [-96, +91] | +0.02 / +0.02 | +0.01 | +0.02 |
| H state path (D: 08-30 04Z warm start) | +0.04 [+0.00, +0.10] | +25% [-114, +138] | +0.04 [-0.00, +0.10] | +24% [-118, +123] | +0.07 / +0.07 | +0.03 | +0.07 |
| REM king-score differences + unreconciled | -0.03 [-0.05, -0.02] | -18% [-212, +176] | -0.03 [-0.05, -0.02] | -18% [-203, +199] | — | — | — |
| **total D_K − R_K** | +0.18 [-0.21, +0.63] | | +0.18 [-0.22, +0.63] | | excl. 09-06: +0.23 [-0.22, +0.74] / +0.23 [-0.22, +0.74] | | |

Period means (s42): φ_T before/after 09-02 12Z +1.36 / +0.11; φ_B before/after 09-04 04Z -0.06 / -0.07; φ_W before/after 09-05 16Z -0.03 / +0.00; REM before/after 09-01 08Z -0.00 / -0.04.

## T3c · net gap decomposition (Shapley primary; bps/anchor means with CI; shares shown but unstable when the gap CI contains 0)

| component | s42 mean | s42 share | s2027 mean | s2027 share | fixed order s42 / s2027 | one-at-a-time s42 | leave-one-out s42 |
|---|---|---|---|---|---|---|---|
| T FTRIM (D: none before 09-02 12Z, ledger rule after) | +0.90 [-0.04, +1.96] | -67% [-487, +502] | +0.91 [-0.04, +1.96] | -86% [-675, +594] | +0.73 / +0.72 | +0.73 | +0.98 |
| W seat (D: archived w3m, seeded from 09-05 16Z) | +0.52 [-0.64, +1.98] | -38% [-604, +612] | +0.51 [-0.65, +1.97] | -48% [-776, +581] | +0.56 / +0.57 | +0.47 | +0.42 |
| B fund rank base (D: members before 09-04 04Z, M1 base after) | -0.06 [-0.51, +0.34] | +4% [-80, +135] | -0.07 [-0.52, +0.32] | +7% [-102, +116] | -0.14 / -0.19 | -0.23 | +0.07 |
| V fund values / freshness | -0.47 [-1.45, +0.38] | +35% [-219, +322] | -0.49 [-1.47, +0.36] | +47% [-349, +378] | -0.29 / -0.32 | -0.65 | -0.63 |
| M member set | +0.10 [-3.50, +3.78] | -7% [-1116, +801] | +0.11 [-3.49, +3.81] | -10% [-1372, +1179] | +0.08 / +0.12 | +0.49 | -0.59 |
| X exit rule | -0.13 [-0.54, +0.22] | +10% [-81, +125] | -0.14 [-0.54, +0.22] | +13% [-109, +159] | -0.41 / -0.42 | -0.58 | +0.00 |
| S eligibility | -0.18 [-0.48, +0.09] | +14% [-58, +83] | -0.19 [-0.49, +0.08] | +18% [-82, +133] | -0.01 / -0.01 | -0.73 | -0.03 |
| P replay per-name stop layer | -1.16 [-3.34, +0.39] | +86% [-671, +816] | -0.81 [-2.70, +0.54] | +77% [-743, +772] | -1.06 / -0.71 | -1.14 | -1.11 |
| H state path (D: 08-30 04Z warm start) | -0.28 [-0.88, +0.28] | +21% [-206, +160] | -0.28 [-0.87, +0.28] | +26% [-200, +234] | -0.23 / -0.23 | -0.45 | -0.23 |
| REM king-score differences + unreconciled | -0.58 [-1.28, +0.12] | +43% [-247, +296] | -0.58 [-1.28, +0.12] | +56% [-346, +438] | — | — | — |
| **total D_K − R_K** | -1.36 [-4.14, +1.48] | | -1.05 [-3.93, +1.74] | | excl. 09-06: -1.01 [-4.15, +2.04] / -0.66 [-3.78, +2.23] | | |

Period means (s42): φ_T before/after 09-02 12Z +2.18 / +0.49; φ_B before/after 09-04 04Z -0.09 / -0.04; φ_W before/after 09-05 16Z +1.66 / -0.92; REM before/after 09-01 08Z -0.41 / -0.61.

## T4 · side lens, price by own-sign side
| book | long | short | gross share short |
|---|---|---|---|
| D_K (s42) | -1.50 [-17.14, +12.35] | -4.46 [-15.65, +7.59] | 0.530 |
| R_K (s42) | +2.12 [-12.61, +14.35] | -6.88 [-17.39, +4.93] | 0.535 |
| R_K (s2027) | +1.81 [-13.23, +14.23] | -6.87 [-17.37, +4.92] | 0.534 |
| D_K − R_K (s42 / s2027) | -3.62 [-7.21, -0.21] / -3.30 [-6.88, +0.07] | +2.42 [+0.83, +3.94] / +2.41 [+0.82, +3.93] | |

## T5 · the deployed king chain's largest short-side price losses and the replay's same names (s42; Σ over window, bps; weights ×1e3)
| name | D_K short Σ | R_K short Σ | w_D mean | w_R mean | rn8 mean bp |
|---|---|---|---|---|---|
| USELESSUSDT | -47.9 | -64.5 | -0.34 | -3.24 | +2.1 |
| FLOCKUSDT | -37.0 | -52.6 | -5.50 | -3.81 | -16.1 |
| COTIUSDT | -30.3 | -35.0 | -8.00 | -8.01 | -6.3 |
| MINAUSDT | -29.7 | -38.5 | -7.60 | -9.85 | -4.4 |
| ARBUSDT | -28.6 | -31.2 | -4.10 | -4.02 | +0.6 |
| PORTALUSDT | -14.2 | -17.3 | -7.95 | -10.12 | -1.7 |
| NEARUSDT | -13.8 | -17.0 | -3.90 | -4.97 | +0.6 |
| SIGNUSDT | -13.7 | +0.0 | -5.33 | +0.00 | -1.5 |
| INJUSDT | -13.6 | -17.1 | -5.77 | -6.71 | -0.9 |
| WALUSDT | -11.4 | +0.0 | -5.96 | +0.00 | +1.0 |
| EPICUSDT | -11.2 | -13.1 | -7.63 | -9.65 | +0.4 |
| STXUSDT | -11.2 | -15.7 | -7.35 | -10.11 | +0.1 |
| AEROUSDT | -10.8 | -12.7 | -5.32 | -6.28 | -0.3 |
| ATOMUSDT | -10.4 | -16.1 | -3.81 | -5.99 | -0.4 |
| DOTUSDT | -9.6 | -8.8 | -2.89 | -2.75 | +0.8 |

## T6 · names where the deployed king chain did worse than the replay (s42; mean bps/anchor of the per-name price gap; weights ×1e3)
| name | gap | w_D | w_R |
|---|---|---|---|
| CYSUSDT | -1.140 | +1.72 | +0.00 |
| BTRUSDT | -0.916 | +0.53 | +0.00 |
| COLLECTUSDT | -0.650 | +9.45 | +7.80 |
| STARUSDT | -0.518 | +10.28 | +8.15 |
| CAPUSDT | -0.431 | +0.00 | -7.29 |
| BTWUSDT | -0.287 | +0.00 | +10.33 |
| HEMIUSDT | -0.284 | +6.33 | +5.17 |
| VELVETUSDT | -0.277 | +5.99 | +2.94 |
| RIVERUSDT | -0.269 | +9.90 | +2.85 |
| SIGNUSDT | -0.224 | -5.33 | +0.00 |
| WALUSDT | -0.187 | -5.96 | +0.00 |
| MAGMAUSDT | -0.155 | +9.68 | +7.80 |

**Per-name Shapley of the price gap (s42), most negative / most positive five:**

- T FTRIM (D: none before 09-02 12Z, ledger rule after): − SOPHUSDT -0.06, FLOCKUSDT -0.06, COTIUSDT -0.04, SANDUSDT -0.02, MOVEUSDT -0.02 · + TUTUSDT +0.34, 0GUSDT +0.12, ZKPUSDT +0.11, ZKCUSDT +0.11, ZORAUSDT +0.11
- P replay per-name stop layer: − COLLECTUSDT -0.56, STARUSDT -0.48, VELVETUSDT -0.32, RIVERUSDT -0.23, ZORAUSDT -0.10 · + CLOUSDT +0.22, FLOCKUSDT +0.13, PROMUSDT +0.11, ONUSDT +0.05, TRIAUSDT +0.05
- M member set: − BTRUSDT -0.82, CYSUSDT -0.65, SIGNUSDT -0.24, WALUSDT -0.16, TWTUSDT -0.11 · + BRUSDT +0.55, IOSTUSDT +0.52, BMTUSDT +0.20, SOPHUSDT +0.17, SKRUSDT +0.14
- V fund values / freshness: − IOSTUSDT -0.26, CAPUSDT -0.12, BTWUSDT -0.05, TUTUSDT -0.05, HEMIUSDT -0.05 · + BULLAUSDT +0.09, SOMIUSDT +0.06, REDUSDT +0.06, AKEUSDT +0.05, FLOCKUSDT +0.05
- W seat (D: archived w3m, seeded from 09-05 16Z): − HEMIUSDT -0.13, BEATUSDT -0.06, COLLECTUSDT -0.05, GRTUSDT -0.04, XANUSDT -0.04 · + BULLAUSDT +0.56, AKEUSDT +0.30, USELESSUSDT +0.16, ZENUSDT +0.09, DASHUSDT +0.07
- H state path (D: 08-30 04Z warm start): − CYSUSDT -0.47, BTRUSDT -0.09, WALUSDT -0.05, BTWUSDT -0.03, ARUSDT -0.03 · + VELVETUSDT +0.09, CLOUSDT +0.08, BRUSDT +0.08, CHIPUSDT +0.06, ZORAUSDT +0.05

## T7 · replay diagnostics
| item | s42 | s2027 |
|---|---|---|
| replay FTRIM kills per anchor (king chain) | 8.3 | 8.3 |
| replay eligible names per anchor | 229 | 229 |
| replay stop layer: names blocked per anchor / new fires in window | 9.2 / 18 | 9.0 / 18 |
| node skips | 0 | 0 |

## T8 · devices and inputs
| item | sha256 |
|---|---|
| t5c_bridge.py | `e401f48ef68235a74b257e9a1ed712e9457f25384b80629c8273fa5099b7178a` |
| t5c_drive.py | `9f5ec0258eb1b8baf716c5e2c5d867e41bc38d7b184a0c9390ff77bad9439d75` |
| w10_sleeve_t5c.py (derived) | `23604230871b8fc7efd7b3ba31fccaf6850a3d159ce08f872755dd6068a0a8c5` |
| t5c_king_extend.py | `04df75a7d77dd4558e2cc145fd9c888f27ee9356c6265eb335cec6e84297d83d` |
| t5c_live_ingredients.py | `fbf6c759c0c44aa6d0b7b6b60d2452ac9b2aa4f82101fc6364ecc05b705f831b` |
| /workspace/uplift_r2_2026-09-13/T5c/arms/KA_s42.npz | `21772c5924148db2b4485598eb3ae2d42e0d2b7e14f7bc8d71df94bbb72d528b` |
| /workspace/uplift_r2_2026-09-13/T5c/arms/KA_s2027.npz | `50fe99e006441d639c66e83788acb659af189269e1f8ccc7106e7d039891ee0e` |
| /workspace/uplift_r2_2026-09-13/T5c/arms/KB_s42.npz | `81b6aea8c255fbacae290102e91f03053706c61a8e32005a2c7ae8ce37619010` |
| /workspace/uplift_r2_2026-09-13/T5c/arms/KB_s2027.npz | `3111db69ab8363d5f86bfa4dae2e98a08be0eb393d52d7a331a553a9f35bbe52` |
| /workspace/uplift_r2_2026-09-13/T5c/receipts/T5c_live_ingredients.npz | `5db35a4f77f992916680c67b920605d3a1d99576b735b6e48c847bee2845612f` |
| /workspace/uplift_2026-09-11/r6/out/meta_newprod_v4_x0910.npz | `a8eb359701c71acfe853a295eb055bdbb04e1c29b6534ccdf23aeaff69907245` |
| /workspace/uplift_2026-09-11/r6/out/wide_panel_4h_v2ext_x0910.npz | `042478f7d8e9f9476341a2acb310828fcf1f5d4a855c2ad0105a08e78f604549` |
| /workspace/uplift_2026-09-11/r6/out/dlw_v4raw_x0910/data/dlw_targets.npz | `5b628413d0c06d2a989c1ab624783238e7871a9f6a84675be372901a5fbb27de` |
| /workspace/uplift_2026-09-11/r3k/costb_PWR_G230k.json | `295b4e7b462373e495fe995ca993fd7a96ab64d050a66ada0d670acf7e9b3d53` |
| /workspace/uplift_r2_2026-09-13/T1/receipts/T1_d2.npz | `70d742fdce7ede314c11a06475cccb1f30bcc5b483f87b8c7d150f4390cbabb6` |
| arm KA_s42 (pod2 only) | `21772c5924148db2b4485598eb3ae2d42e0d2b7e14f7bc8d71df94bbb72d528b` |
| arm KA_s2027 (pod2 only) | `50fe99e006441d639c66e83788acb659af189269e1f8ccc7106e7d039891ee0e` |
| arm KB_s42 (pod2 only) | `81b6aea8c255fbacae290102e91f03053706c61a8e32005a2c7ae8ce37619010` |
| arm KB_s2027 (pod2 only) | `3111db69ab8363d5f86bfa4dae2e98a08be0eb393d52d7a331a553a9f35bbe52` |
| carry-forward mask (pod2) | `60e25a184da5f88e76826935646368b384dd6e0b244506b849260daacf4ff0e4` |
