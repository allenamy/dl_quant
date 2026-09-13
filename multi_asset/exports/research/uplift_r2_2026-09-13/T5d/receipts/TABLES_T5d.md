# TABLES · T5d (rendered by `devices/t5d_tables.py` from receipts; do not edit by hand)

King chain only (V2MAIN arm NOT MEASURED). Window 2026-08-31 00:00Z .. 2026-09-10 00:00Z, 61 anchors, 11 UTC-day blocks — **CIs are descriptive**. Units bps / 4h anchor / unit gross. D_K = deployed king chain; R_K = A0 replay king chain. Target layer only. Calibers: **T5C** = T5c weights priced with x0910 intervals (reproduces T5c); **FIX** = the same weights priced with corrected intervals; **REG** = regenerated replay (corrected panel: FTRIM, fund EMA, state and W regenerated) priced with corrected intervals. D_K is archived, so its FIX and REG values are the same. Equivalence band δ = 0.25. Rendered 2026-09-13T13:20:02Z.

## T0 · gates
| gate | blocking | result |
|---|---|---|
| G-FREEZE / G-ENV | yes | every device asserts prereg sha `a1ef16cd…`; env whitelists: interval_sources (Mac) CPATH,HOME,LC_CTYPE,LIBRARY_PATH,MANPATH,PATH,SDKROOT,__CF_USER_TEXT_ENCODING; ivfix_panel HOME,LC_CTYPE,PATH; bridge HOME,LC_CTYPE,PATH; posthoc HOME,LC_CTYPE,PATH; drive children env per run recorded (`RECEIPT_T5d_drive.json`) |
| G-POD | yes | all pod2 devices under `nice -n 10`, bridge Pool(16), others one process; GPU before → after: ivfix_panel 0 %, 2 MiB → 0 %, 2 MiB; drive 0 %, 2 MiB → 0 %, 2 MiB; bridge 0 %, 2 MiB → 0 %, 2 MiB; posthoc 0 %, 2 MiB → 0 %, 2 MiB; posthoc_seed 0 %, 2 MiB → 0 %, 2 MiB; posthoc_fallback 0 %, 2 MiB → 0 %, 2 MiB; PIDs 333197/339489 unchanged in every receipt: True |
| G-R6 (r6 algebra with r6's own intervals reproduces x0910 tail cells) | yes | True; 829 symbols with events, 676 seeded; mismatches f_fund_now 0, f_fund_iv 0, f_fund_ema 0, f_fund_ema_v1 0, f_fund_ema_v2 0 |
| G-IV-LEDGER (ledger iv vs snapped timestamp gap, same settlement) | no | 38443 tail settlements: ledger 32595, gap 5837; ledger ≠ gap **0**; settlements whose interval changed 778, names 23 |
| G-IV-EXEC (iv_true vs executor funding_interval_h) | no | 14591 settlements checked, **22** mismatches (names COTI, SKR, SOPH, T, ZKC); classification in P1 |
| G-SCOPE (only tail f_fund_iv / v1 / v2 differ) | yes | True; f_fund_ema_v1 870 cells, 18 names, pre-cut 0; f_fund_ema_v2 924 cells, 18 names, pre-cut 0; f_fund_iv 547 cells, 23 names, pre-cut 0; f_fund_now and f_fund_ema unchanged |
| G-UM / G-KA (mask, KA/KB kings and T5c arms = T5c receipts) | yes | True |
| G-X′ (T5d arms = T5c arms on anchors ≤ 08-31 00Z) | yes | True; 50 arrays per run bitwise; arrays that change after the cut: S0_W, S0_rec, d30_n2_c42_T1AGG, d30_n2_c42_T1C4, d30_n2_c42_T1ID, d30_n2_c42_T1RN, d30_n2_c42_T1SMR, d30_n2_c42_T1TRR, d30_n2_c42_W, d30_n2_c42_rec, legs_fund |
| G-PRED (synthetic label controls a–d, before real data) | yes | True; a NOT A SHARED LOSS (neither lost; no gap) · b STRATEGY'S OWN LOSS (king chain, target layer) · c NOT A SHARED LOSS (deployed only lost; gap) GAP=True · d BOTH LOST, DEPLOYMENT GAP |
| G-RAW | yes | True |
| G-SIM-R (simulator = regenerated arms, king chain and legs) | yes | True; KA_s42 0.0e+00/0.0e+00, KA_s2027 0.0e+00/0.0e+00, KB_s42 0.0e+00/0.0e+00, KB_s2027 0.0e+00/0.0e+00 |
| G-T1c (x0910 caliber reproduces T1 D2 and T5 §6.2) | yes | True; n 61, max|Δ| price 2.2e-14, carry 0.0e+00; short price -4.5274112841 |
| G-ARCH-D | yes | True; max|Δ| 0.0e+00 |
| G-FIXW (fixed weights: price and cost bitwise unchanged; T5c caliber recomputed bitwise) | yes | True |
| G-T5C (T5c readings reproduced from the T5c arms) | yes | True; max|Δ| 0.0e+00 |
| G-CLOSE (Shapley and fixed order close per anchor, REG) | yes | True; max 2.8e-14 |
| bridge run 2 vs run 1 (descriptive fields added only) | — | True; run-1 fields changed: /self_sha256, /built_utc, /wall_s; fields added 50; components npz identical True |

## T1 · interval correction
| item | value |
|---|---|
| pre-freeze scan (08-30 04Z..09-10 00Z, timestamp gap) | incumbent 4056 cells, 0 mismatches; tail 40552 cells, **547** mismatches, 23 names |
| producer ledger (two aux snapshots) | 523 symbols, 46522 settlements from 2026-08-28 00Z; snapshot conflicts 0 |
| executor funding records 08-30..09-11 | 317 symbols, 15249 settlements; duplicate rows 0; interval conflicts 0 |
| names with a changed settlement interval | COTI, GLW, GOOGL, GS, HD, HK0700, HK1810, IOST, MINIMAX, NVDA, POPMART, PYPL, QCOM, SKR, SOPH, STRC, TENCENT, TER, T, WDC, WEN, ZHIPU, ZKC |
| corrected panel | `a5d7fb9731b259e8…` (pod2 `T5d/panel/`) |

## T2 · the two deltas (k 89; level CIs here use k 89 and differ slightly from T3/T4)

Δ_fixed = FIX − T5C (same weights, corrected intervals); Δ_regen = REG − T5C (regenerated replay); weight effect = REG − FIX. Price and cost cannot move under fixed weights (G-FIXW).

| book · seed | outcome | T5C | FIX | REG | Δ_fixed | Δ_regen | weight effect | Δ_regen excl. 09-06 |
|---|---|---|---|---|---|---|---|---|
| R_K KA_s42 | price | -4.76 [-13.47, +2.85] | -4.76 [-13.47, +2.85] | -4.83 [-13.46, +2.75] | +0.000 [+0.000, +0.000] | -0.069 [-0.171, +0.037] | -0.069 [-0.171, +0.037] | -0.099 [-0.199, -0.003] |
| R_K KA_s42 | carry | +1.00 [+0.87, +1.13] | +1.02 [+0.88, +1.16] | +0.98 [+0.85, +1.12] | +0.018 [+0.007, +0.029] | -0.017 [-0.038, -0.001] | -0.034 [-0.054, -0.017] | -0.007 [-0.015, +0.000] |
| R_K KA_s42 | cost | +0.11 [+0.09, +0.12] | +0.11 [+0.09, +0.12] | +0.11 [+0.09, +0.12] | +0.000 [+0.000, +0.000] | -0.001 [-0.001, +0.000] | -0.001 [-0.001, +0.000] | -0.001 [-0.001, +0.000] |
| R_K KA_s42 | net | -5.87 [-14.54, +1.71] | -5.89 [-14.55, +1.69] | -5.92 [-14.49, +1.62] | -0.018 [-0.029, -0.007] | -0.052 [-0.160, +0.071] | -0.034 [-0.136, +0.083] | -0.091 [-0.190, +0.003] |
| R_K KA_s2027 | price | -5.07 [-13.87, +2.64] | -5.07 [-13.87, +2.64] | -5.16 [-13.85, +2.48] | +0.000 [+0.000, +0.000] | -0.092 [-0.204, +0.021] | -0.092 [-0.204, +0.021] | -0.124 [-0.231, -0.029] |
| R_K KA_s2027 | carry | +1.00 [+0.87, +1.13] | +1.02 [+0.89, +1.16] | +0.99 [+0.85, +1.12] | +0.018 [+0.007, +0.029] | -0.016 [-0.038, -0.000] | -0.034 [-0.054, -0.016] | -0.007 [-0.015, +0.001] |
| R_K KA_s2027 | cost | +0.11 [+0.09, +0.12] | +0.11 [+0.09, +0.12] | +0.11 [+0.09, +0.12] | +0.000 [+0.000, +0.000] | -0.001 [-0.001, +0.000] | -0.001 [-0.001, +0.000] | -0.001 [-0.001, +0.000] |
| R_K KA_s2027 | net | -6.17 [-14.93, +1.45] | -6.19 [-14.95, +1.43] | -6.25 [-14.91, +1.31] | -0.018 [-0.029, -0.007] | -0.075 [-0.191, +0.051] | -0.057 [-0.167, +0.063] | -0.117 [-0.221, -0.023] |
| R_K KB_s42 (sensitivity) | price | -4.39 [-13.26, +3.82] | -4.39 [-13.26, +3.82] | -4.41 [-13.25, +3.80] | +0.000 [+0.000, +0.000] | -0.017 [-0.141, +0.113] | -0.017 [-0.141, +0.113] | -0.040 [-0.172, +0.086] |
| R_K KB_s42 (sensitivity) | carry | +1.00 [+0.86, +1.14] | +1.02 [+0.87, +1.16] | +0.98 [+0.84, +1.13] | +0.018 [+0.007, +0.029] | -0.016 [-0.037, -0.001] | -0.034 [-0.052, -0.017] | -0.007 [-0.015, +0.001] |
| R_K KB_s42 (sensitivity) | cost | +0.10 [+0.09, +0.12] | +0.10 [+0.09, +0.12] | +0.10 [+0.09, +0.12] | +0.000 [+0.000, +0.000] | -0.001 [-0.001, +0.000] | -0.001 [-0.001, +0.000] | -0.000 [-0.001, +0.000] |
| R_K KB_s42 (sensitivity) | net | -5.49 [-14.30, +2.77] | -5.51 [-14.31, +2.73] | -5.49 [-14.25, +2.71] | -0.018 [-0.029, -0.007] | -0.000 [-0.131, +0.135] | +0.018 [-0.108, +0.148] | -0.033 [-0.164, +0.091] |
| R_K KB_s2027 (sensitivity) | price | -4.38 [-13.28, +3.92] | -4.38 [-13.28, +3.92] | -4.39 [-13.28, +3.87] | +0.000 [+0.000, +0.000] | -0.012 [-0.135, +0.116] | -0.012 [-0.135, +0.116] | -0.035 [-0.170, +0.090] |
| R_K KB_s2027 (sensitivity) | carry | +1.00 [+0.86, +1.14] | +1.02 [+0.87, +1.17] | +0.99 [+0.84, +1.13] | +0.018 [+0.007, +0.029] | -0.016 [-0.037, -0.001] | -0.034 [-0.053, -0.017] | -0.007 [-0.015, +0.001] |
| R_K KB_s2027 (sensitivity) | cost | +0.10 [+0.09, +0.12] | +0.10 [+0.09, +0.12] | +0.10 [+0.09, +0.12] | +0.000 [+0.000, +0.000] | -0.001 [-0.001, +0.000] | -0.001 [-0.001, +0.000] | -0.000 [-0.001, +0.000] |
| R_K KB_s2027 (sensitivity) | net | -5.48 [-14.34, +2.85] | -5.50 [-14.35, +2.82] | -5.48 [-14.30, +2.80] | -0.018 [-0.029, -0.007] | +0.004 [-0.127, +0.139] | +0.022 [-0.102, +0.153] | -0.028 [-0.159, +0.095] |
| D_K (archived; no regeneration) | price | -5.96 [-16.70, +2.92] | -5.96 [-16.70, +2.92] | = FIX | +0.000 [+0.000, +0.000] | — | — | — |
| D_K (archived; no regeneration) | carry | +1.18 [+0.68, +1.72] | +1.43 [+0.76, +2.21] | = FIX | +0.253 [+0.045, +0.505] | — | — | — |
| D_K (archived; no regeneration) | cost | +0.08 [+0.08, +0.09] | +0.08 [+0.08, +0.09] | = FIX | +0.000 [+0.000, +0.000] | — | — | — |
| D_K (archived; no regeneration) | net | -7.23 [-17.79, +1.55] | -7.48 [-18.01, +1.31] | = FIX | -0.253 [-0.505, -0.045] | — | — | — |
| D_B (archived; no regeneration) | price | -5.36 [-16.61, +3.66] | -5.36 [-16.61, +3.66] | = FIX | +0.000 [+0.000, +0.000] | — | — | — |
| D_B (archived; no regeneration) | carry | +1.17 [+0.67, +1.68] | +1.41 [+0.76, +2.16] | = FIX | +0.248 [+0.043, +0.498] | — | — | — |
| D_B (archived; no regeneration) | cost | +0.10 [+0.09, +0.11] | +0.10 [+0.09, +0.11] | = FIX | +0.000 [+0.000, +0.000] | — | — | — |
| D_B (archived; no regeneration) | net | -6.63 [-17.46, +2.31] | -6.88 [-17.65, +2.04] | = FIX | -0.248 [-0.498, -0.043] | — | — | — |

## T3 · readings with the corrected predicate (PREREG_T5d §6.1–§6.2; label needs both seeds)

| seed · caliber | outcome | D_K mean | R_K mean | D_K − R_K | LOSS_D | LOSS_R | SAME | GAP | label | what the paired CI excludes |
|---|---|---|---|---|---|---|---|---|---|---|
| KA_s42 · T5C | price | -5.96 [-15.89, +2.82] | -4.76 [-13.05, +3.04] | -1.20 [-4.19, +1.59] | True | True | True | False | STRATEGY'S OWN LOSS (king chain, target layer) | not detected, not excluded: differences below -4.19 or above +1.59 are excluded (95%, descriptive) |
| KA_s42 · T5C | carry | +1.18 [+0.69, +1.75] | +1.00 [+0.87, +1.13] | +0.18 [-0.22, +0.63] | — | — | True | False | SAME LEVEL | not detected, not excluded: differences below -0.22 or above +0.63 are excluded (95%, descriptive) |
| KA_s42 · T5C | cost | +0.08 [+0.08, +0.09] | +0.11 [+0.10, +0.12] | -0.02 [-0.04, -0.01] | — | — | False | True | DEPLOYMENT GAP | detected |
| KA_s42 · T5C | net | -7.23 [-17.03, +1.45] | -5.87 [-14.12, +1.89] | -1.36 [-4.35, +1.43] | True | True | True | False | STRATEGY'S OWN LOSS (king chain, target layer) | not detected, not excluded: differences below -4.35 or above +1.43 are excluded (95%, descriptive) |
| KA_s42 · FIX | price | -5.96 [-15.89, +2.82] | -4.76 [-13.05, +3.04] | -1.20 [-4.19, +1.59] | True | True | True | False | STRATEGY'S OWN LOSS (king chain, target layer) | not detected, not excluded: differences below -4.19 or above +1.59 are excluded (95%, descriptive) |
| KA_s42 · FIX | carry | +1.43 [+0.76, +2.24] | +1.02 [+0.88, +1.16] | +0.42 [-0.16, +1.10] | — | — | True | False | SAME LEVEL | not detected, not excluded: differences below -0.16 or above +1.10 are excluded (95%, descriptive) |
| KA_s42 · FIX | cost | +0.08 [+0.08, +0.09] | +0.11 [+0.10, +0.12] | -0.02 [-0.04, -0.01] | — | — | False | True | DEPLOYMENT GAP | detected |
| KA_s42 · FIX | net | -7.48 [-17.24, +1.21] | -5.89 [-14.13, +1.86] | -1.59 [-4.70, +1.29] | True | True | True | False | STRATEGY'S OWN LOSS (king chain, target layer) | not detected, not excluded: differences below -4.70 or above +1.29 are excluded (95%, descriptive) |
| KA_s42 · REG | price | -5.96 [-15.89, +2.82] | -4.83 [-13.05, +2.94] | -1.13 [-4.15, +1.71] | True | True | True | False | STRATEGY'S OWN LOSS (king chain, target layer) | not detected, not excluded: differences below -4.15 or above +1.71 are excluded (95%, descriptive) |
| KA_s42 · REG | carry | +1.43 [+0.76, +2.24] | +0.98 [+0.85, +1.13] | +0.45 [-0.13, +1.13] | — | — | True | False | SAME LEVEL | not detected, not excluded: differences below -0.13 or above +1.13 are excluded (95%, descriptive) |
| KA_s42 · REG | cost | +0.08 [+0.08, +0.09] | +0.11 [+0.09, +0.12] | -0.02 [-0.04, -0.01] | — | — | False | True | DEPLOYMENT GAP | detected |
| KA_s42 · REG | net | -7.48 [-17.24, +1.21] | -5.92 [-14.04, +1.79] | -1.56 [-4.74, +1.38] | True | True | True | False | STRATEGY'S OWN LOSS (king chain, target layer) | not detected, not excluded: differences below -4.74 or above +1.38 are excluded (95%, descriptive) |
| KA_s42 · REG_excl_0906 | price | -2.45 [-9.88, +4.37] | -1.74 [-7.48, +4.42] | -0.71 [-3.86, +2.18] | True | True | True | False | STRATEGY'S OWN LOSS (king chain, target layer) | not detected, not excluded: differences below -3.86 or above +2.18 are excluded (95%, descriptive) |
| KA_s42 · REG_excl_0906 | carry | +1.52 [+0.78, +2.36] | +1.00 [+0.86, +1.16] | +0.52 [-0.12, +1.24] | — | — | True | False | SAME LEVEL | not detected, not excluded: differences below -0.12 or above +1.24 are excluded (95%, descriptive) |
| KA_s42 · REG_excl_0906 | cost | +0.08 [+0.08, +0.09] | +0.11 [+0.10, +0.12] | -0.03 [-0.04, -0.01] | — | — | False | True | DEPLOYMENT GAP | detected |
| KA_s42 · REG_excl_0906 | net | -4.05 [-11.27, +2.84] | -2.85 [-8.56, +3.26] | -1.20 [-4.61, +1.84] | True | True | True | False | STRATEGY'S OWN LOSS (king chain, target layer) | not detected, not excluded: differences below -4.61 or above +1.84 are excluded (95%, descriptive) |
| KA_s2027 · T5C | price | -5.96 [-15.89, +2.82] | -5.07 [-13.39, +2.87] | -0.90 [-3.87, +1.81] | True | True | True | False | STRATEGY'S OWN LOSS (king chain, target layer) | not detected, not excluded: differences below -3.87 or above +1.81 are excluded (95%, descriptive) |
| KA_s2027 · T5C | carry | +1.18 [+0.69, +1.75] | +1.00 [+0.87, +1.13] | +0.18 [-0.23, +0.63] | — | — | True | False | SAME LEVEL | not detected, not excluded: differences below -0.23 or above +0.63 are excluded (95%, descriptive) |
| KA_s2027 · T5C | cost | +0.08 [+0.08, +0.09] | +0.11 [+0.09, +0.12] | -0.02 [-0.04, -0.01] | — | — | False | True | DEPLOYMENT GAP | detected |
| KA_s2027 · T5C | net | -7.23 [-17.03, +1.45] | -6.17 [-14.47, +1.68] | -1.05 [-4.05, +1.71] | True | True | True | False | STRATEGY'S OWN LOSS (king chain, target layer) | not detected, not excluded: differences below -4.05 or above +1.71 are excluded (95%, descriptive) |
| KA_s2027 · FIX | price | -5.96 [-15.89, +2.82] | -5.07 [-13.39, +2.87] | -0.90 [-3.87, +1.81] | True | True | True | False | STRATEGY'S OWN LOSS (king chain, target layer) | not detected, not excluded: differences below -3.87 or above +1.81 are excluded (95%, descriptive) |
| KA_s2027 · FIX | carry | +1.43 [+0.76, +2.24] | +1.02 [+0.88, +1.16] | +0.41 [-0.16, +1.10] | — | — | True | False | SAME LEVEL | not detected, not excluded: differences below -0.16 or above +1.10 are excluded (95%, descriptive) |
| KA_s2027 · FIX | cost | +0.08 [+0.08, +0.09] | +0.11 [+0.09, +0.12] | -0.02 [-0.04, -0.01] | — | — | False | True | DEPLOYMENT GAP | detected |
| KA_s2027 · FIX | net | -7.48 [-17.24, +1.21] | -6.19 [-14.48, +1.66] | -1.29 [-4.36, +1.50] | True | True | True | False | STRATEGY'S OWN LOSS (king chain, target layer) | not detected, not excluded: differences below -4.36 or above +1.50 are excluded (95%, descriptive) |
| KA_s2027 · REG | price | -5.96 [-15.89, +2.82] | -5.16 [-13.39, +2.73] | -0.80 [-3.79, +1.93] | True | True | True | False | STRATEGY'S OWN LOSS (king chain, target layer) | not detected, not excluded: differences below -3.79 or above +1.93 are excluded (95%, descriptive) |
| KA_s2027 · REG | carry | +1.43 [+0.76, +2.24] | +0.99 [+0.85, +1.13] | +0.45 [-0.13, +1.13] | — | — | True | False | SAME LEVEL | not detected, not excluded: differences below -0.13 or above +1.13 are excluded (95%, descriptive) |
| KA_s2027 · REG | cost | +0.08 [+0.08, +0.09] | +0.11 [+0.09, +0.12] | -0.02 [-0.04, -0.01] | — | — | False | True | DEPLOYMENT GAP | detected |
| KA_s2027 · REG | net | -7.48 [-17.24, +1.21] | -6.25 [-14.45, +1.59] | -1.23 [-4.37, +1.67] | True | True | True | False | STRATEGY'S OWN LOSS (king chain, target layer) | not detected, not excluded: differences below -4.37 or above +1.67 are excluded (95%, descriptive) |
| KA_s2027 · REG_excl_0906 | price | -2.45 [-9.88, +4.37] | -2.11 [-8.19, +4.20] | -0.33 [-3.49, +2.39] | True | True | True | False | STRATEGY'S OWN LOSS (king chain, target layer) | not detected, not excluded: differences below -3.49 or above +2.39 are excluded (95%, descriptive) |
| KA_s2027 · REG_excl_0906 | carry | +1.52 [+0.78, +2.36] | +1.01 [+0.86, +1.16] | +0.52 [-0.12, +1.24] | — | — | True | False | SAME LEVEL | not detected, not excluded: differences below -0.12 or above +1.24 are excluded (95%, descriptive) |
| KA_s2027 · REG_excl_0906 | cost | +0.08 [+0.08, +0.09] | +0.11 [+0.10, +0.12] | -0.03 [-0.04, -0.01] | — | — | False | True | DEPLOYMENT GAP | detected |
| KA_s2027 · REG_excl_0906 | net | -4.05 [-11.27, +2.84] | -3.23 [-9.22, +3.06] | -0.82 [-4.11, +2.08] | True | True | True | False | STRATEGY'S OWN LOSS (king chain, target layer) | not detected, not excluded: differences below -4.11 or above +2.08 are excluded (95%, descriptive) |
| KB_s42 · T5C | price | -5.96 [-15.89, +2.82] | -4.39 [-12.84, +3.96] | -1.57 [-4.56, +1.37] | True | True | True | False | STRATEGY'S OWN LOSS (king chain, target layer) | not detected, not excluded: differences below -4.56 or above +1.37 are excluded (95%, descriptive) |
| KB_s42 · T5C | carry | +1.18 [+0.69, +1.75] | +1.00 [+0.86, +1.14] | +0.18 [-0.22, +0.62] | — | — | True | False | SAME LEVEL | not detected, not excluded: differences below -0.22 or above +0.62 are excluded (95%, descriptive) |
| KB_s42 · T5C | cost | +0.08 [+0.08, +0.09] | +0.10 [+0.09, +0.12] | -0.02 [-0.03, -0.01] | — | — | False | True | DEPLOYMENT GAP | detected |
| KB_s42 · T5C | net | -7.23 [-17.03, +1.45] | -5.49 [-13.85, +2.79] | -1.73 [-4.81, +1.22] | True | True | True | False | STRATEGY'S OWN LOSS (king chain, target layer) | not detected, not excluded: differences below -4.81 or above +1.22 are excluded (95%, descriptive) |
| KB_s42 · FIX | price | -5.96 [-15.89, +2.82] | -4.39 [-12.84, +3.96] | -1.57 [-4.56, +1.37] | True | True | True | False | STRATEGY'S OWN LOSS (king chain, target layer) | not detected, not excluded: differences below -4.56 or above +1.37 are excluded (95%, descriptive) |
| KB_s42 · FIX | carry | +1.43 [+0.76, +2.24] | +1.02 [+0.87, +1.16] | +0.42 [-0.15, +1.10] | — | — | True | False | SAME LEVEL | not detected, not excluded: differences below -0.15 or above +1.10 are excluded (95%, descriptive) |
| KB_s42 · FIX | net | -7.48 [-17.24, +1.21] | -5.51 [-13.85, +2.77] | -1.97 [-5.09, +1.02] | True | True | True | False | STRATEGY'S OWN LOSS (king chain, target layer) | not detected, not excluded: differences below -5.09 or above +1.02 are excluded (95%, descriptive) |
| KB_s42 · REG | price | -5.96 [-15.89, +2.82] | -4.41 [-12.76, +3.84] | -1.56 [-4.63, +1.45] | True | True | True | False | STRATEGY'S OWN LOSS (king chain, target layer) | not detected, not excluded: differences below -4.63 or above +1.45 are excluded (95%, descriptive) |
| KB_s42 · REG | carry | +1.43 [+0.76, +2.24] | +0.98 [+0.84, +1.13] | +0.45 [-0.12, +1.13] | — | — | True | False | SAME LEVEL | not detected, not excluded: differences below -0.12 or above +1.13 are excluded (95%, descriptive) |
| KB_s42 · REG | cost | +0.08 [+0.08, +0.09] | +0.10 [+0.09, +0.12] | -0.02 [-0.03, -0.01] | — | — | False | True | DEPLOYMENT GAP | detected |
| KB_s42 · REG | net | -7.48 [-17.24, +1.21] | -5.49 [-13.72, +2.74] | -1.99 [-5.19, +1.06] | True | True | True | False | STRATEGY'S OWN LOSS (king chain, target layer) | not detected, not excluded: differences below -5.19 or above +1.06 are excluded (95%, descriptive) |
| KB_s42 · REG_excl_0906 | price | -2.45 [-9.88, +4.37] | -1.44 [-7.69, +5.20] | -1.00 [-4.33, +1.88] | True | True | True | False | STRATEGY'S OWN LOSS (king chain, target layer) | not detected, not excluded: differences below -4.33 or above +1.88 are excluded (95%, descriptive) |
| KB_s42 · REG_excl_0906 | carry | +1.52 [+0.78, +2.36] | +1.00 [+0.85, +1.17] | +0.52 [-0.11, +1.23] | — | — | True | False | SAME LEVEL | not detected, not excluded: differences below -0.11 or above +1.23 are excluded (95%, descriptive) |
| KB_s42 · REG_excl_0906 | cost | +0.08 [+0.08, +0.09] | +0.11 [+0.10, +0.12] | -0.03 [-0.04, -0.01] | — | — | False | True | DEPLOYMENT GAP | detected |
| KB_s42 · REG_excl_0906 | net | -4.05 [-11.27, +2.84] | -2.55 [-8.80, +4.04] | -1.50 [-4.81, +1.44] | True | True | True | False | STRATEGY'S OWN LOSS (king chain, target layer) | not detected, not excluded: differences below -4.81 or above +1.44 are excluded (95%, descriptive) |
| KB_s2027 · T5C | price | -5.96 [-15.89, +2.82] | -4.38 [-12.89, +4.03] | -1.58 [-4.54, +1.32] | True | True | True | False | STRATEGY'S OWN LOSS (king chain, target layer) | not detected, not excluded: differences below -4.54 or above +1.32 are excluded (95%, descriptive) |
| KB_s2027 · T5C | carry | +1.18 [+0.69, +1.75] | +1.00 [+0.86, +1.14] | +0.18 [-0.22, +0.62] | — | — | True | False | SAME LEVEL | not detected, not excluded: differences below -0.22 or above +0.62 are excluded (95%, descriptive) |
| KB_s2027 · T5C | cost | +0.08 [+0.08, +0.09] | +0.10 [+0.09, +0.12] | -0.02 [-0.03, -0.01] | — | — | False | True | DEPLOYMENT GAP | detected |
| KB_s2027 · T5C | net | -7.23 [-17.03, +1.45] | -5.48 [-13.91, +2.85] | -1.74 [-4.73, +1.17] | True | True | True | False | STRATEGY'S OWN LOSS (king chain, target layer) | not detected, not excluded: differences below -4.73 or above +1.17 are excluded (95%, descriptive) |
| KB_s2027 · FIX | price | -5.96 [-15.89, +2.82] | -4.38 [-12.89, +4.03] | -1.58 [-4.54, +1.32] | True | True | True | False | STRATEGY'S OWN LOSS (king chain, target layer) | not detected, not excluded: differences below -4.54 or above +1.32 are excluded (95%, descriptive) |
| KB_s2027 · FIX | carry | +1.43 [+0.76, +2.24] | +1.02 [+0.87, +1.16] | +0.41 [-0.15, +1.09] | — | — | True | False | SAME LEVEL | not detected, not excluded: differences below -0.15 or above +1.09 are excluded (95%, descriptive) |
| KB_s2027 · FIX | net | -7.48 [-17.24, +1.21] | -5.50 [-13.92, +2.82] | -1.98 [-5.05, +0.97] | True | True | True | False | STRATEGY'S OWN LOSS (king chain, target layer) | not detected, not excluded: differences below -5.05 or above +0.97 are excluded (95%, descriptive) |
| KB_s2027 · REG | price | -5.96 [-15.89, +2.82] | -4.39 [-12.78, +3.96] | -1.57 [-4.59, +1.40] | True | True | True | False | STRATEGY'S OWN LOSS (king chain, target layer) | not detected, not excluded: differences below -4.59 or above +1.40 are excluded (95%, descriptive) |
| KB_s2027 · REG | carry | +1.43 [+0.76, +2.24] | +0.99 [+0.84, +1.13] | +0.45 [-0.12, +1.12] | — | — | True | False | SAME LEVEL | not detected, not excluded: differences below -0.12 or above +1.12 are excluded (95%, descriptive) |
| KB_s2027 · REG | cost | +0.08 [+0.08, +0.09] | +0.10 [+0.09, +0.12] | -0.02 [-0.03, -0.01] | — | — | False | True | DEPLOYMENT GAP | detected |
| KB_s2027 · REG | net | -7.48 [-17.24, +1.21] | -5.48 [-13.82, +2.84] | -2.00 [-5.17, +1.00] | True | True | True | False | STRATEGY'S OWN LOSS (king chain, target layer) | not detected, not excluded: differences below -5.17 or above +1.00 are excluded (95%, descriptive) |
| KB_s2027 · REG_excl_0906 | price | -2.45 [-9.88, +4.37] | -1.39 [-7.69, +5.27] | -1.05 [-4.42, +1.81] | True | True | True | False | STRATEGY'S OWN LOSS (king chain, target layer) | not detected, not excluded: differences below -4.42 or above +1.81 are excluded (95%, descriptive) |
| KB_s2027 · REG_excl_0906 | carry | +1.52 [+0.78, +2.36] | +1.00 [+0.85, +1.17] | +0.52 [-0.11, +1.23] | — | — | True | False | SAME LEVEL | not detected, not excluded: differences below -0.11 or above +1.23 are excluded (95%, descriptive) |
| KB_s2027 · REG_excl_0906 | cost | +0.08 [+0.08, +0.09] | +0.11 [+0.10, +0.12] | -0.03 [-0.04, -0.01] | — | — | False | True | DEPLOYMENT GAP | detected |
| KB_s2027 · REG_excl_0906 | net | -4.05 [-11.27, +2.84] | -2.50 [-8.84, +4.11] | -1.55 [-4.86, +1.39] | True | True | True | False | STRATEGY'S OWN LOSS (king chain, target layer) | not detected, not excluded: differences below -4.86 or above +1.39 are excluded (95%, descriptive) |

**Label changes.** T5c receipt label (old predicate) → T5C caliber (new predicate) → FIX → REG, per outcome:

| seed | outcome | T5c (old) | T5C (new) | FIX | REG | REG excl. 09-06 |
|---|---|---|---|---|---|---|
| KA_s42 | price | STRATEGY'S OWN LOSS (king chain) | STRATEGY'S OWN LOSS (king chain, target layer) | STRATEGY'S OWN LOSS (king chain, target layer) | STRATEGY'S OWN LOSS (king chain, target layer) | STRATEGY'S OWN LOSS (king chain, target layer) |
| KA_s42 | carry | STRATEGY'S OWN LOSS (king chain) | SAME LEVEL | SAME LEVEL | SAME LEVEL | SAME LEVEL |
| KA_s42 | cost | DEPLOYMENT DIFFERENCE | DEPLOYMENT GAP | DEPLOYMENT GAP | DEPLOYMENT GAP | DEPLOYMENT GAP |
| KA_s42 | net | STRATEGY'S OWN LOSS (king chain) | STRATEGY'S OWN LOSS (king chain, target layer) | STRATEGY'S OWN LOSS (king chain, target layer) | STRATEGY'S OWN LOSS (king chain, target layer) | STRATEGY'S OWN LOSS (king chain, target layer) |
| KA_s2027 | price | STRATEGY'S OWN LOSS (king chain) | STRATEGY'S OWN LOSS (king chain, target layer) | STRATEGY'S OWN LOSS (king chain, target layer) | STRATEGY'S OWN LOSS (king chain, target layer) | STRATEGY'S OWN LOSS (king chain, target layer) |
| KA_s2027 | carry | STRATEGY'S OWN LOSS (king chain) | SAME LEVEL | SAME LEVEL | SAME LEVEL | SAME LEVEL |
| KA_s2027 | cost | DEPLOYMENT DIFFERENCE | DEPLOYMENT GAP | DEPLOYMENT GAP | DEPLOYMENT GAP | DEPLOYMENT GAP |
| KA_s2027 | net | STRATEGY'S OWN LOSS (king chain) | STRATEGY'S OWN LOSS (king chain, target layer) | STRATEGY'S OWN LOSS (king chain, target layer) | STRATEGY'S OWN LOSS (king chain, target layer) | STRATEGY'S OWN LOSS (king chain, target layer) |
| KB_s42 | price | STRATEGY'S OWN LOSS (king chain) | STRATEGY'S OWN LOSS (king chain, target layer) | STRATEGY'S OWN LOSS (king chain, target layer) | STRATEGY'S OWN LOSS (king chain, target layer) | STRATEGY'S OWN LOSS (king chain, target layer) |
| KB_s42 | carry | STRATEGY'S OWN LOSS (king chain) | SAME LEVEL | SAME LEVEL | SAME LEVEL | SAME LEVEL |
| KB_s42 | cost | DEPLOYMENT DIFFERENCE | DEPLOYMENT GAP | DEPLOYMENT GAP | DEPLOYMENT GAP | DEPLOYMENT GAP |
| KB_s42 | net | STRATEGY'S OWN LOSS (king chain) | STRATEGY'S OWN LOSS (king chain, target layer) | STRATEGY'S OWN LOSS (king chain, target layer) | STRATEGY'S OWN LOSS (king chain, target layer) | STRATEGY'S OWN LOSS (king chain, target layer) |
| KB_s2027 | price | STRATEGY'S OWN LOSS (king chain) | STRATEGY'S OWN LOSS (king chain, target layer) | STRATEGY'S OWN LOSS (king chain, target layer) | STRATEGY'S OWN LOSS (king chain, target layer) | STRATEGY'S OWN LOSS (king chain, target layer) |
| KB_s2027 | carry | STRATEGY'S OWN LOSS (king chain) | SAME LEVEL | SAME LEVEL | SAME LEVEL | SAME LEVEL |
| KB_s2027 | cost | DEPLOYMENT DIFFERENCE | DEPLOYMENT GAP | DEPLOYMENT GAP | DEPLOYMENT GAP | DEPLOYMENT GAP |
| KB_s2027 | net | STRATEGY'S OWN LOSS (king chain) | STRATEGY'S OWN LOSS (king chain, target layer) | STRATEGY'S OWN LOSS (king chain, target layer) | STRATEGY'S OWN LOSS (king chain, target layer) | STRATEGY'S OWN LOSS (king chain, target layer) |

## T4 · levels (k 81)
| book | caliber | price | carry | cost | net |
|---|---|---|---|---|---|
| D_K | T5C | -5.96 [-15.89, +2.82] | +1.18 [+0.69, +1.75] | +0.082 [+0.076, +0.088] | -7.23 [-17.03, +1.45] |
| D_K | corrected | -5.96 [-15.89, +2.82] | +1.43 [+0.76, +2.24] | +0.082 [+0.076, +0.088] | -7.48 [-17.24, +1.21] |
| D_B | T5C | -5.36 [-15.77, +3.51] | +1.17 [+0.68, +1.71] | +0.099 [+0.092, +0.109] | -6.63 [-16.68, +2.16] |
| D_B | corrected | -5.36 [-15.77, +3.51] | +1.41 [+0.77, +2.19] | +0.099 [+0.092, +0.109] | -6.88 [-16.84, +1.93] |
| D_F | T5C | -4.42 [-15.27, +4.56] | +1.12 [+0.67, +1.63] | +0.126 [+0.106, +0.156] | -5.67 [-16.14, +3.20] |
| D_F | corrected | -4.42 [-15.27, +4.56] | +1.36 [+0.77, +2.06] | +0.126 [+0.106, +0.156] | -5.90 [-16.44, +2.96] |
| R_K KA_s42 | T5C | -4.76 [-13.05, +3.04] | +1.00 [+0.87, +1.13] | +0.107 [+0.095, +0.120] | -5.87 [-14.12, +1.89] |
| R_K KA_s42 | FIX | -4.76 [-13.05, +3.04] | +1.02 [+0.88, +1.16] | +0.107 [+0.095, +0.120] | -5.89 [-14.13, +1.86] |
| R_K KA_s42 | REG | -4.83 [-13.05, +2.94] | +0.98 [+0.85, +1.13] | +0.106 [+0.094, +0.120] | -5.92 [-14.04, +1.79] |
| R_K KA_s2027 | T5C | -5.07 [-13.39, +2.87] | +1.00 [+0.87, +1.13] | +0.106 [+0.095, +0.120] | -6.17 [-14.47, +1.68] |
| R_K KA_s2027 | FIX | -5.07 [-13.39, +2.87] | +1.02 [+0.88, +1.16] | +0.106 [+0.095, +0.120] | -6.19 [-14.48, +1.66] |
| R_K KA_s2027 | REG | -5.16 [-13.39, +2.73] | +0.99 [+0.85, +1.13] | +0.106 [+0.094, +0.120] | -6.25 [-14.45, +1.59] |
| R_K KB_s42 | T5C | -4.39 [-12.84, +3.96] | +1.00 [+0.86, +1.14] | +0.105 [+0.095, +0.116] | -5.49 [-13.85, +2.79] |
| R_K KB_s42 | FIX | -4.39 [-12.84, +3.96] | +1.02 [+0.87, +1.16] | +0.105 [+0.095, +0.116] | -5.51 [-13.85, +2.77] |
| R_K KB_s42 | REG | -4.41 [-12.76, +3.84] | +0.98 [+0.84, +1.13] | +0.104 [+0.094, +0.116] | -5.49 [-13.72, +2.74] |
| R_K KB_s2027 | T5C | -4.38 [-12.89, +4.03] | +1.00 [+0.86, +1.14] | +0.105 [+0.095, +0.116] | -5.48 [-13.91, +2.85] |
| R_K KB_s2027 | FIX | -4.38 [-12.89, +4.03] | +1.02 [+0.87, +1.16] | +0.105 [+0.095, +0.116] | -5.50 [-13.92, +2.82] |
| R_K KB_s2027 | REG | -4.39 [-12.78, +3.96] | +0.99 [+0.84, +1.13] | +0.104 [+0.094, +0.116] | -5.48 [-13.82, +2.84] |

Deployed book vs deployed king chain, price per anchor: correlation 0.9951; mean(D_B − D_K) +0.60 [-0.16, +1.34].

## T5 · replay FTRIM trigger switches and weight distance (REG vs T5C, KA)

| seed | switches (all in window) | mean L1 weight distance in window | largest L1 (anchor) | names with the largest mean |Δw| (×1e3) |
|---|---|---|---|---|
| KA_s42 | 18 (18) | 0.0133 | 2026-09-05 12:00Z 0.0207; 2026-09-02 08:00Z 0.0203; 2026-09-02 04:00Z 0.0203 | ZKC 1.70, T 1.24, COTI 0.58, WIF 0.20, ENSO 0.19, XRP 0.18, MANA 0.18, EPIC 0.18 |
| KA_s2027 | 18 (18) | 0.0130 | 2026-09-02 08:00Z 0.0202; 2026-09-05 12:00Z 0.0202; 2026-09-02 04:00Z 0.0201 | ZKC 1.70, T 1.24, COTI 0.58, WIF 0.20, ENSO 0.19, MANA 0.18, EPIC 0.18, AERO 0.17 |

| anchor | name | funding rate now | iv x0910 → true | rn8 bp x0910 → true | killed T5C / REG |
|---|---|---|---|---|---|
| 2026-08-31 04:00Z | COTIUSDT | -0.000221 | 4 → 1 | -4.4 → -17.7 | False / True |
| 2026-08-31 08:00Z | COTIUSDT | -0.000191 | 4 → 1 | -3.8 → -15.3 | False / True |
| 2026-08-31 16:00Z | COTIUSDT | -0.000144 | 4 → 1 | -2.9 → -11.5 | False / True |
| 2026-08-31 20:00Z | ZKCUSDT | -0.000347 | 4 → 1 | -6.9 → -27.8 | False / True |
| 2026-09-01 00:00Z | ZKCUSDT | -0.000345 | 4 → 1 | -6.9 → -27.6 | False / True |
| 2026-09-01 08:00Z | ZKCUSDT | -0.000382 | 4 → 1 | -7.6 → -30.5 | False / True |
| 2026-09-01 12:00Z | ZKCUSDT | -0.000403 | 4 → 1 | -8.1 → -32.2 | False / True |
| 2026-09-01 16:00Z | ZKCUSDT | -0.000341 | 4 → 1 | -6.8 → -27.3 | False / True |
| 2026-09-01 20:00Z | ZKCUSDT | -0.000290 | 4 → 1 | -5.8 → -23.2 | False / True |
| 2026-09-02 00:00Z | ZKCUSDT | -0.000310 | 4 → 1 | -6.2 → -24.8 | False / True |
| 2026-09-02 04:00Z | ZKCUSDT | -0.000225 | 4 → 1 | -4.5 → -18.0 | False / True |
| 2026-09-04 08:00Z | TUSDT | -0.000498 | 4 → 1 | -10.0 → -39.9 | False / True |
| 2026-09-04 16:00Z | TUSDT | -0.000390 | 4 → 1 | -7.8 → -31.2 | False / True |
| 2026-09-04 20:00Z | TUSDT | -0.000288 | 4 → 1 | -5.8 → -23.1 | False / True |
| 2026-09-05 00:00Z | TUSDT | -0.000404 | 4 → 1 | -8.1 → -32.3 | False / True |
| 2026-09-05 04:00Z | TUSDT | -0.000245 | 4 → 1 | -4.9 → -19.6 | False / True |
| 2026-09-05 08:00Z | TUSDT | -0.000240 | 4 → 1 | -4.8 → -19.2 | False / True |
| 2026-09-05 12:00Z | TUSDT | -0.000132 | 4 → 1 | -2.6 → -10.5 | False / True |

Switch list identical for s2027: True.

## T6a · price gap decomposition on REG (Shapley primary; bps/anchor; shares unstable when the gap CI contains 0; T5c value for comparison)

| component | s42 mean | s42 share | s2027 mean | s2027 share | T5c s42 | fixed order s42 / s2027 | one-at-a-time s42 | leave-one-out s42 |
|---|---|---|---|---|---|---|---|---|
| T FTRIM (D: none before 09-02 12Z, ledger rule after) | +1.44 [+0.25, +2.73] | -127% [-1025, +917] | +1.44 [+0.25, +2.73] | -180% [-1249, +1125] | +1.32 | +1.23 / +1.25 | +1.23 | +1.51 |
| W seat (D: archived w3m, seeded from 09-05 16Z) | +0.47 [-0.72, +1.85] | -42% [-570, +624] | +0.47 [-0.73, +1.84] | -58% [-633, +670] | +0.49 | +0.47 / +0.49 | +0.42 | +0.36 |
| B fund rank base (D: members before 09-04 04Z, M1 base after) | -0.14 [-0.62, +0.26] | +12% [-113, +132] | -0.15 [-0.63, +0.25] | +18% [-137, +141] | -0.13 | -0.30 / -0.35 | -0.42 | +0.10 |
| V fund values / freshness | -0.28 [-1.00, +0.33] | +25% [-180, +180] | -0.30 [-1.01, +0.32] | +37% [-247, +231] | -0.55 | -0.32 / -0.35 | -0.95 | -0.00 |
| M member set | -0.29 [-3.32, +2.90] | +26% [-758, +816] | -0.28 [-3.32, +2.92] | +34% [-1110, +953] | +0.01 | +0.04 / +0.08 | -0.25 | -0.64 |
| X exit rule | -0.15 [-0.59, +0.22] | +13% [-128, +112] | -0.16 [-0.60, +0.21] | +19% [-127, +142] | -0.14 | -0.42 / -0.43 | -0.63 | +0.00 |
| S eligibility | -0.20 [-0.49, +0.08] | +17% [-110, +113] | -0.20 [-0.50, +0.08] | +25% [-122, +158] | -0.19 | -0.01 / -0.01 | -0.77 | -0.03 |
| P replay per-name stop layer | -1.14 [-3.40, +0.39] | +101% [-860, +677] | -0.79 [-2.73, +0.55] | +99% [-642, +758] | -1.15 | -1.04 / -0.69 | -1.13 | -1.10 |
| H state path (D: 08-30 04Z warm start) | -0.23 [-0.82, +0.30] | +21% [-161, +198] | -0.23 [-0.81, +0.30] | +28% [-218, +223] | -0.24 | -0.16 / -0.16 | -0.39 | -0.16 |
| REM king-score differences + unreconciled | -0.62 [-1.32, +0.08] | +55% [-290, +431] | -0.62 [-1.32, +0.08] | +77% [-450, +496] | -0.62 | — | — | — |
| **total D_K − R_K** | -1.13 [-3.96, +1.67] | | -0.80 [-3.68, +1.93] | | -1.20 | excl. 09-06: -0.71 [-3.98, +2.35] / -0.33 [-3.46, +2.59] | | |

REM reading (model difference): s42 not detected, not excluded: -1.32 .. +0.08; s2027 not detected, not excluded: -1.32 .. +0.08. Period means (s42): φ_T before/after 09-02 12Z +3.76 / +0.68; φ_B before/after 09-04 04Z -0.16 / -0.12; φ_W before/after 09-05 16Z +1.60 / -0.95; REM before/after 09-01 08Z -0.41 / -0.65. Closure max 2.8e-14 / fixed order 7.1e-15.

## T6b · carry gap decomposition on REG (Shapley primary; bps/anchor; shares unstable when the gap CI contains 0; T5c value for comparison)

| component | s42 mean | s42 share | s2027 mean | s2027 share | T5c s42 | fixed order s42 / s2027 | one-at-a-time s42 | leave-one-out s42 |
|---|---|---|---|---|---|---|---|---|
| T FTRIM (D: none before 09-02 12Z, ledger rule after) | +0.54 [+0.15, +1.01] | +120% [-250, +538] | +0.54 [+0.15, +1.01] | +120% [-242, +554] | +0.42 | +0.47 / +0.47 | +0.47 | +0.59 |
| W seat (D: archived w3m, seeded from 09-05 16Z) | -0.02 [-0.05, +0.00] | -5% [-11, +4] | -0.02 [-0.05, +0.01] | -5% [-11, +4] | -0.02 | -0.07 / -0.06 | +0.01 | -0.07 |
| B fund rank base (D: members before 09-04 04Z, M1 base after) | -0.07 [-0.07, -0.06] | -14% [-128, +85] | -0.06 [-0.07, -0.06] | -14% [-131, +83] | -0.06 | -0.14 / -0.14 | -0.15 | +0.03 |
| V fund values / freshness | -0.11 [-0.12, -0.09] | -24% [-207, +133] | -0.11 [-0.12, -0.09] | -24% [-212, +128] | -0.08 | -0.04 / -0.04 | -0.23 | +0.00 |
| M member set | +0.07 [-0.06, +0.22] | +15% [-44, +68] | +0.07 [-0.06, +0.22] | +15% [-47, +67] | -0.09 | +0.16 / +0.15 | -0.03 | +0.18 |
| X exit rule | -0.03 [-0.04, -0.01] | -6% [-45, +27] | -0.03 [-0.04, -0.01] | -6% [-45, +27] | -0.01 | -0.01 / -0.01 | -0.03 | +0.00 |
| S eligibility | -0.01 [-0.02, -0.00] | -3% [-29, +22] | -0.01 [-0.02, -0.00] | -3% [-31, +22] | -0.01 | -0.00 / -0.00 | -0.05 | -0.00 |
| P replay per-name stop layer | +0.01 [-0.00, +0.03] | +3% [-28, +44] | +0.01 [-0.00, +0.03] | +3% [-24, +39] | +0.02 | +0.02 / +0.02 | +0.01 | +0.01 |
| H state path (D: 08-30 04Z warm start) | +0.09 [+0.01, +0.19] | +20% [-20, +76] | +0.09 [+0.01, +0.19] | +20% [-19, +77] | +0.04 | +0.10 / +0.10 | +0.12 | +0.10 |
| REM king-score differences + unreconciled | -0.03 [-0.06, +0.00] | -6% [-85, +65] | -0.03 [-0.06, +0.00] | -6% [-88, +63] | -0.03 | — | — | — |
| **total D_K − R_K** | +0.45 [-0.12, +1.13] | | +0.45 [-0.12, +1.13] | | +0.18 | excl. 09-06: +0.52 [-0.11, +1.31] / +0.52 [-0.11, +1.31] | | |

REM reading (model difference): s42 economically negligible: excluded beyond ±0.25; s2027 economically negligible: excluded beyond ±0.25. Period means (s42): φ_T before/after 09-02 12Z +1.71 / +0.15; φ_B before/after 09-04 04Z -0.06 / -0.07; φ_W before/after 09-05 16Z -0.04 / +0.01; REM before/after 09-01 08Z +0.06 / -0.04. Closure max 1.3e-15 / fixed order 4.4e-16.

## T6c · net gap decomposition on REG (Shapley primary; bps/anchor; shares unstable when the gap CI contains 0; T5c value for comparison)

| component | s42 mean | s42 share | s2027 mean | s2027 share | T5c s42 | fixed order s42 / s2027 | one-at-a-time s42 | leave-one-out s42 |
|---|---|---|---|---|---|---|---|---|
| T FTRIM (D: none before 09-02 12Z, ledger rule after) | +0.91 [-0.05, +1.93] | -58% [-512, +398] | +0.91 [-0.04, +1.94] | -74% [-549, +467] | +0.90 | +0.77 / +0.79 | +0.77 | +0.92 |
| W seat (D: archived w3m, seeded from 09-05 16Z) | +0.51 [-0.65, +1.99] | -33% [-496, +650] | +0.50 [-0.67, +1.98] | -41% [-569, +517] | +0.52 | +0.55 / +0.56 | +0.42 | +0.44 |
| B fund rank base (D: members before 09-04 04Z, M1 base after) | -0.07 [-0.53, +0.34] | +4% [-95, +114] | -0.08 [-0.54, +0.33] | +6% [-78, +135] | -0.06 | -0.15 / -0.21 | -0.27 | +0.06 |
| V fund values / freshness | -0.17 [-0.83, +0.46] | +11% [-119, +154] | -0.19 [-0.84, +0.45] | +15% [-150, +180] | -0.47 | -0.28 / -0.31 | -0.72 | -0.00 |
| M member set | -0.36 [-3.63, +2.74] | +23% [-595, +733] | -0.35 [-3.61, +2.77] | +28% [-942, +784] | +0.10 | -0.12 / -0.08 | -0.22 | -0.82 |
| X exit rule | -0.12 [-0.53, +0.24] | +8% [-84, +100] | -0.13 [-0.53, +0.23] | +11% [-101, +133] | -0.13 | -0.42 / -0.42 | -0.60 | +0.00 |
| S eligibility | -0.19 [-0.48, +0.09] | +12% [-52, +67] | -0.19 [-0.49, +0.09] | +16% [-78, +99] | -0.18 | -0.01 / -0.01 | -0.72 | -0.03 |
| P replay per-name stop layer | -1.15 [-3.32, +0.40] | +74% [-651, +668] | -0.80 [-2.68, +0.55] | +65% [-557, +780] | -1.16 | -1.06 / -0.71 | -1.14 | -1.10 |
| H state path (D: 08-30 04Z warm start) | -0.32 [-0.91, +0.24] | +21% [-142, +172] | -0.31 [-0.91, +0.25] | +26% [-164, +198] | -0.28 | -0.26 / -0.25 | -0.51 | -0.26 |
| REM king-score differences + unreconciled | -0.59 [-1.29, +0.13] | +38% [-265, +237] | -0.59 [-1.29, +0.13] | +48% [-268, +334] | -0.58 | — | — | — |
| **total D_K − R_K** | -1.56 [-4.50, +1.43] | | -1.23 [-4.24, +1.71] | | -1.36 | excl. 09-06: -1.20 [-4.50, +1.95] / -0.82 [-4.12, +2.24] | | |

REM reading (model difference): s42 not detected, not excluded: -1.29 .. +0.13; s2027 not detected, not excluded: -1.29 .. +0.13. Period means (s42): φ_T before/after 09-02 12Z +2.07 / +0.53; φ_B before/after 09-04 04Z -0.10 / -0.05; φ_W before/after 09-05 16Z +1.67 / -0.95; REM before/after 09-01 08Z -0.47 / -0.61. Closure max 2.1e-14 / fixed order 7.1e-15.

Cost gap on REG: s42 -0.024 [-0.038, -0.011] (REM -0.001 [-0.003, +0.000]), s2027 -0.023 [-0.037, -0.010].

## T7 · side lens, price by own-sign side (REG)
| book | long | short | gross share short |
|---|---|---|---|
| D_K | -1.50 [-17.14, +12.35] | -4.46 [-15.65, +7.59] | 0.530 |
| R_K (s42) | +2.13 [-12.59, +14.32] | -6.96 [-17.34, +4.91] | 0.535 |
| R_K (s2027) | +1.81 [-13.20, +14.20] | -6.97 [-17.34, +4.90] | 0.534 |
| D_K − R_K (s42 / s2027) | -3.63 [-7.25, -0.20] / -3.31 [-6.92, +0.11] | +2.50 [+0.87, +4.08] / +2.51 [+0.88, +4.10] | |

## T8 · the deployed king chain's largest short-side price losses and the regenerated replay's same names (s42; Σ over window, bps; weights ×1e3; rn8 from the corrected panel)
| name | D_K short Σ | R_K short Σ | w_D mean | w_R mean | rn8 mean bp |
|---|---|---|---|---|---|
| USELESSUSDT | -47.9 | -63.9 | -0.34 | -3.21 | +2.1 |
| FLOCKUSDT | -37.0 | -52.7 | -5.50 | -3.82 | -16.1 |
| COTIUSDT | -30.3 | -35.2 | -8.00 | -7.43 | -7.6 |
| MINAUSDT | -29.7 | -38.7 | -7.60 | -9.89 | -4.4 |
| ARBUSDT | -28.6 | -31.0 | -4.10 | -3.90 | +0.6 |
| PORTALUSDT | -14.2 | -17.4 | -7.95 | -10.12 | -1.7 |
| NEARUSDT | -13.8 | -17.2 | -3.90 | -5.01 | +0.6 |
| SIGNUSDT | -13.7 | +0.0 | -5.33 | +0.00 | -1.5 |
| INJUSDT | -13.6 | -17.5 | -5.77 | -6.87 | -0.9 |
| WALUSDT | -11.4 | +0.0 | -5.96 | +0.00 | +1.0 |
| EPICUSDT | -11.2 | -13.4 | -7.63 | -9.70 | +0.4 |
| STXUSDT | -11.2 | -15.8 | -7.35 | -10.11 | +0.1 |
| AEROUSDT | -10.8 | -13.0 | -5.32 | -6.44 | -0.3 |
| ATOMUSDT | -10.4 | -16.1 | -3.81 | -6.01 | -0.4 |
| DOTUSDT | -9.6 | -9.0 | -2.89 | -2.76 | +0.8 |

## T9 · names where the deployed king chain did worse than the regenerated replay (s42; mean bps/anchor of the per-name price gap; weights ×1e3)
| name | gap | w_D | w_R |
|---|---|---|---|
| CYSUSDT | -1.140 | +1.72 | +0.00 |
| BTRUSDT | -0.916 | +0.53 | +0.00 |
| COLLECTUSDT | -0.640 | +9.45 | +7.82 |
| STARUSDT | -0.519 | +10.28 | +8.15 |
| CAPUSDT | -0.447 | +0.00 | -7.35 |
| BTWUSDT | -0.287 | +0.00 | +10.31 |
| HEMIUSDT | -0.282 | +6.33 | +5.19 |
| VELVETUSDT | -0.280 | +5.99 | +2.93 |
| RIVERUSDT | -0.269 | +9.90 | +2.85 |
| SIGNUSDT | -0.224 | -5.33 | +0.00 |
| WALUSDT | -0.187 | -5.96 | +0.00 |
| MAGMAUSDT | -0.155 | +9.68 | +7.81 |

**Per-name Shapley of the price gap (s42, REG), most negative / most positive five:**

- T FTRIM (D: none before 09-02 12Z, ledger rule after): − FLOCKUSDT -0.05, COTIUSDT -0.03, SANDUSDT -0.03, EDGEUSDT -0.02, MOVEUSDT -0.02 · + TUTUSDT +0.34, ZKCUSDT +0.16, 0GUSDT +0.12, ZKPUSDT +0.11, ZORAUSDT +0.11
- P replay per-name stop layer: − COLLECTUSDT -0.56, STARUSDT -0.48, VELVETUSDT -0.32, RIVERUSDT -0.23, ZORAUSDT -0.10 · + CLOUSDT +0.22, FLOCKUSDT +0.13, PROMUSDT +0.11, ONUSDT +0.05, TRIAUSDT +0.05
- M member set: − BTRUSDT -0.82, CYSUSDT -0.65, SIGNUSDT -0.24, WALUSDT -0.16, TWTUSDT -0.11 · + BRUSDT +0.55, IOSTUSDT +0.25, BMTUSDT +0.20, SKRUSDT +0.17, SOPHUSDT +0.11
- V fund values / freshness: − CAPUSDT -0.12, BTWUSDT -0.05, TUTUSDT -0.05, HEMIUSDT -0.04, COLLECTUSDT -0.04 · + BULLAUSDT +0.09, SOMIUSDT +0.06, REDUSDT +0.06, AKEUSDT +0.05, FLOCKUSDT +0.05
- W seat (D: archived w3m, seeded from 09-05 16Z): − HEMIUSDT -0.14, BEATUSDT -0.06, COLLECTUSDT -0.04, GRTUSDT -0.04, XANUSDT -0.04 · + BULLAUSDT +0.57, AKEUSDT +0.29, USELESSUSDT +0.16, ZENUSDT +0.09, DASHUSDT +0.07
- H state path (D: 08-30 04Z warm start): − CYSUSDT -0.47, BTRUSDT -0.09, WALUSDT -0.05, BTWUSDT -0.03, ARUSDT -0.03 · + VELVETUSDT +0.09, CLOUSDT +0.08, BRUSDT +0.08, CHIPUSDT +0.05, ZORAUSDT +0.05

## T10 · replay diagnostics (REG)
| item | s42 | s2027 |
|---|---|---|
| replay FTRIM kills per anchor, REG (T5C) | 8.61 (8.31) | 8.61 (8.31) |
| replay eligible names per anchor | 229 | 229 |
| replay stop layer: names blocked per anchor / new fires in window | 9.2 / 18 | 9.0 / 18 |
| node skips | 0 | 0 |

## P · POST-HOC description (`devices/t5d_posthoc.py`, written after the bridge numbers were seen; not a gate, not a reading)

### P1 · per-settlement interval sources
| item | value |
|---|---|
| re-derivation of the corrected tail cells from the per-settlement list = T5d panel | True (f_fund_now 0, f_fund_iv 0, f_fund_ema 0, f_fund_ema_v1 0, f_fund_ema_v2 0) |
| tail settlements by source | fallback_x0910 11, gap 5837, ledger 32595 |
| settlements in the 24 h before the cut by source | gap 515, ledger 2835 |
| settlements whose interval changed | 778 (list in the receipt; full per-settlement list `iv_sources_per_settlement.csv.gz`, sha `8dbe87d31ddb6dad…`) |

Settlements with neither a ledger record nor a usable gap (interval left at the x0910 value; seconds since the previous record from the per-settlement list):

| name | settlement | iv used | seconds since previous record | hours to next | executor | in force at tail anchors |
|---|---|---|---|---|---|---|
| GLWUSDT | 2026-08-31 00:00Z | 8 | 1 | 1.0 | None | none |
| GOOGLUSDT | 2026-09-04 00:00Z | 8 | 1 | 8.0 | None | 2026-09-04 04:00Z |
| GSUSDT | 2026-09-01 00:00Z | 8 | 1 | 8.0 | None | 2026-09-01 04:00Z |
| HDUSDT | 2026-09-03 00:00Z | 8 | 1 | 8.0 | None | 2026-09-03 04:00Z |
| NVDAUSDT | 2026-09-10 00:00Z | 8 | 1 | 8.0 | None | none |
| PYPLUSDT | 2026-09-04 00:00Z | 8 | 1 | 8.0 | None | 2026-09-04 04:00Z |
| QCOMUSDT | 2026-09-03 00:00Z | 8 | 1 | 8.0 | None | 2026-09-03 04:00Z |
| STRCUSDT | 2026-08-31 00:00Z | 8 | 1 | 1.0 | None | none |
| TERUSDT | 2026-09-04 00:00Z | 8 | 1 | 8.0 | None | 2026-09-04 04:00Z |
| WDCUSDT | 2026-09-08 00:00Z | 8 | 1 | 8.0 | None | 2026-09-08 04:00Z |
| WENUSDT | 2026-09-01 00:00Z | 8 | 1 | 8.0 | None | 2026-09-01 04:00Z |

Weights on the 8 in-force cells of these settlements (`RECEIPT_T5d_posthoc_fallback.json`): cells with any nonzero weight in the deployed king chain, the deployed book or any replay arm (T5C/REG × KA/KB × two seeds): **0**; max |w| 0.0e+00; name in the replay member set at those cells: False.

Executor mismatches inside the recomputed range: 18; the executor value equals an interval that iv_true takes within the next 8 h: 16; equals one within the previous 8 h: 0.

Not classified (2): SOPHUSDT 2026-09-11 09:00Z; SOPHUSDT 2026-09-11 12:00Z — both after the window end, where the event data stop at the 09-11 15:04Z fetch.

| name | settlement | iv_true (source, gap) | executor | iv_true within next 8 h |
|---|---|---|---|---|
| COTIUSDT | 2026-08-31 17:00Z | 1 (ledger, 1.0) | 4 | [1.0, 1.0, 1.0, 4.0] |
| COTIUSDT | 2026-08-31 18:00Z | 1 (ledger, 1.0) | 4 | [1.0, 1.0, 4.0] |
| COTIUSDT | 2026-08-31 19:00Z | 1 (ledger, 1.0) | 4 | [1.0, 4.0] |
| COTIUSDT | 2026-08-31 20:00Z | 1 (ledger, 1.0) | 4 | [4.0, 4.0] |
| SKRUSDT | 2026-08-31 00:00Z | 4 (ledger, 4.0) | 1 | [1.0, 1.0, 1.0, 1.0, 1.0, 1.0, 1.0, 1.0] |
| SKRUSDT | 2026-09-07 17:00Z | 1 (ledger, 1.0) | 4 | [1.0, 1.0, 1.0, 4.0] |
| SKRUSDT | 2026-09-07 18:00Z | 1 (ledger, 1.0) | 4 | [1.0, 1.0, 4.0] |
| SKRUSDT | 2026-09-07 19:00Z | 1 (ledger, 1.0) | 4 | [1.0, 4.0] |
| SKRUSDT | 2026-09-07 20:00Z | 1 (ledger, 1.0) | 4 | [4.0, 4.0] |
| SOPHUSDT | 2026-09-08 12:00Z | 4 (ledger, 4.0) | 1 | [1.0, 1.0, 1.0, 1.0, 1.0, 1.0, 1.0, 1.0] |
| SOPHUSDT | 2026-09-11 09:00Z | 1 (ledger, 1.0) | 4 | [2.0] |
| SOPHUSDT | 2026-09-11 12:00Z | 2 (ledger, 2.0) | 4 | [] |
| TUSDT | 2026-09-05 21:00Z | 1 (ledger, 1.0) | 4 | [1.0, 1.0, 1.0, 4.0] |
| TUSDT | 2026-09-05 22:00Z | 1 (ledger, 1.0) | 4 | [1.0, 1.0, 4.0] |
| TUSDT | 2026-09-05 23:00Z | 1 (ledger, 1.0) | 4 | [1.0, 4.0] |
| TUSDT | 2026-09-06 00:00Z | 1 (ledger, 1.0) | 4 | [4.0, 4.0] |
| ZKCUSDT | 2026-09-02 17:00Z | 1 (ledger, 1.0) | 4 | [2.0, 4.0] |
| ZKCUSDT | 2026-09-02 20:00Z | 2 (ledger, 2.0) | 4 | [4.0, 4.0] |

Executor settlements before the recomputed range where the event-stream (x0910 lineage) interval differs from the executor:

| name | settlement | stream iv | executor | ledger | gap |
|---|---|---|---|---|---|
| COTIUSDT | 2026-08-29 21:00Z | 4 | 1 | 1.0 | 1.0 |
| COTIUSDT | 2026-08-29 22:00Z | 4 | 1 | 1.0 | 1.0 |
| COTIUSDT | 2026-08-29 23:00Z | 4 | 1 | 1.0 | 1.0 |
| COTIUSDT | 2026-08-30 00:00Z | 4 | 1 | 1.0 | 1.0 |

### P2 · incumbent rows (≤ 08-31 00Z) against the producer ledger
| item | value |
|---|---|
| base panel rows 2026-08-28 00:00Z .. 2026-08-31 00:00Z: in-force settlement found in ledger | 9880 cells checked; not in ledger 0; rate ≠ ledger-aligned stream rate 0; **f_fund_iv ≠ ledger iv 0** (names: none) |
| event-stream settlements 08-28 00Z .. 08-31 00Z vs ledger | 9007 checked; **iv ≠ ledger 68** (names: COTIUSDT, IOSTUSDT, ZKCUSDT) |

Counterfactual only (the check after this table shows the stored seed was **not** built with these intervals): v1 EMA seed at the cut if the base panel had used the event-stream intervals on the mismatching pre-cut settlements (linear response):

| name | settlements | v1 seed | correction | rank of seed → corrected (of finite) | decay at 09-02 00Z / window end |
|---|---|---|---|---|---|
| COTIUSDT | 49 | -5.623e-03 | -1.729e-03 | 1 → 1 (of 676) | 0.630 / 0.099 |
| IOSTUSDT | 7 | +9.983e-05 | -2.917e-04 | 472 → 36 (of 676) | 0.630 / 0.099 |
| ZKCUSDT | 12 | -3.468e-03 | -1.184e-03 | 4 → 3 (of 676) | 0.630 / 0.099 |

**Which intervals built the stored v1 EMA seed** (`RECEIPT_T5d_posthoc_seed.json`; recursion from the stored v1 at 2026-08-28 00:00Z to 2026-08-31 00:00Z, max relative error vs stored float32 at each anchor):

| names | ledger/gap intervals | x0910 event-stream intervals |
|---|---|---|
| 517 control names (no interval difference) | median 7.7e-08, p99 2.0e-07 | same vectors |
| COTIUSDT (49 of 72 settlements differ) | 8.8e-08 | 0.307 |
| IOSTUSDT (7 of 9 settlements differ) | 7.3e-08 | 2.922 |
| ZKCUSDT (12 of 27 settlements differ) | 1.0e-07 | 0.341 |

### P3 · where the regenerated weights moved the replay (REG − T5C, bps/anchor)

**KA_s42** — totals: price -0.0691, carry weight part -0.0344, carry repricing part +0.0178, cost -0.0006, net -0.0519 (residual vs components 1.9e-14).

| subset | price | carry (weight) | carry (repricing) | cost | net |
|---|---|---|---|---|---|
| FTRIM-switch names (COTI, T, ZKC) | -0.0164 | -0.0376 | +0.0178 | -0.0008 | +0.0042 |
| other names with changed intervals | +0.0000 | +0.0000 | +0.0000 | +0.0000 | +0.0000 |
| all other names | -0.0527 | +0.0032 | +0.0000 | +0.0002 | -0.0561 |

| UTC day | anchors | price | carry | cost | net | contribution to window-mean net |
|---|---|---|---|---|---|---|
| 08-31 | 6 | -0.209 | +0.016 | -0.0011 | -0.223 | -0.0219 |
| 09-01 | 6 | -0.358 | -0.021 | -0.0019 | -0.335 | -0.0330 |
| 09-02 | 6 | -0.021 | -0.004 | +0.0014 | -0.019 | -0.0019 |
| 09-03 | 6 | +0.067 | -0.005 | +0.0012 | +0.072 | +0.0070 |
| 09-04 | 6 | +0.059 | -0.009 | -0.0014 | +0.069 | +0.0068 |
| 09-05 | 6 | -0.256 | -0.008 | -0.0009 | -0.247 | -0.0243 |
| 09-06 | 6 | +0.202 | -0.104 | -0.0009 | +0.307 | +0.0302 |
| 09-07 | 6 | -0.202 | -0.031 | -0.0005 | -0.171 | -0.0168 |
| 09-08 | 6 | +0.074 | -0.003 | -0.0006 | +0.078 | +0.0077 |
| 09-09 | 6 | -0.082 | -0.000 | -0.0003 | -0.082 | -0.0081 |
| 09-10 | 1 | +0.142 | +0.003 | -0.0035 | +0.142 | +0.0023 |

Names with the largest |price change|: ZKC -0.0526 (net -0.0481), T +0.0390 (net +0.0547), CAP +0.0155 (net +0.0148), COLLECT -0.0100 (net -0.0100), AKE +0.0092 (net +0.0092), USELESS +0.0084 (net +0.0085).


| name (most negative net change) | price | carry (weight) | carry (repricing) | cost | net | interval changed | FTRIM switch |
|---|---|---|---|---|---|---|---|
| ZKCUSDT | -0.0526 | -0.0125 | +0.0081 | -0.00014 | -0.0481 | True | True |
| COLLECTUSDT | -0.0100 | +0.0001 | +0.0000 | -0.00001 | -0.0100 | False | False |
| CAKEUSDT | -0.0081 | -0.0000 | +0.0000 | -0.00000 | -0.0080 | False | False |
| SOMIUSDT | -0.0070 | -0.0001 | +0.0000 | +0.00004 | -0.0069 | False | False |
| LDOUSDT | -0.0065 | +0.0000 | +0.0000 | -0.00002 | -0.0065 | False | False |
| INJUSDT | -0.0060 | +0.0001 | +0.0000 | -0.00002 | -0.0061 | False | False |
| EPICUSDT | -0.0059 | +0.0000 | +0.0000 | +0.00000 | -0.0059 | False | False |
| AIOUSDT | -0.0050 | +0.0001 | +0.0000 | -0.00002 | -0.0050 | False | False |
| BOMEUSDT | -0.0046 | -0.0001 | +0.0000 | +0.00002 | -0.0046 | False | False |
| AEROUSDT | -0.0045 | +0.0000 | +0.0000 | +0.00001 | -0.0045 | False | False |

**KA_s2027** — totals: price -0.0919, carry weight part -0.0342, carry repricing part +0.0178, cost -0.0005, net -0.0749 (residual vs components 3.6e-14).

| subset | price | carry (weight) | carry (repricing) | cost | net |
|---|---|---|---|---|---|
| FTRIM-switch names (COTI, T, ZKC) | -0.0167 | -0.0376 | +0.0178 | -0.0008 | +0.0038 |
| other names with changed intervals | +0.0000 | +0.0000 | +0.0000 | +0.0000 | +0.0000 |
| all other names | -0.0751 | +0.0034 | +0.0000 | +0.0002 | -0.0787 |

| UTC day | anchors | price | carry | cost | net | contribution to window-mean net |
|---|---|---|---|---|---|---|
| 08-31 | 6 | -0.212 | +0.016 | -0.0013 | -0.226 | -0.0223 |
| 09-01 | 6 | -0.438 | -0.020 | -0.0018 | -0.416 | -0.0409 |
| 09-02 | 6 | -0.051 | -0.004 | +0.0012 | -0.049 | -0.0048 |
| 09-03 | 6 | +0.004 | -0.005 | +0.0013 | +0.008 | +0.0008 |
| 09-04 | 6 | +0.017 | -0.009 | -0.0016 | +0.027 | +0.0026 |
| 09-05 | 6 | -0.277 | -0.007 | -0.0008 | -0.269 | -0.0265 |
| 09-06 | 6 | +0.203 | -0.105 | -0.0008 | +0.309 | +0.0303 |
| 09-07 | 6 | -0.186 | -0.031 | -0.0004 | -0.155 | -0.0153 |
| 09-08 | 6 | +0.076 | -0.003 | -0.0005 | +0.079 | +0.0078 |
| 09-09 | 6 | -0.088 | +0.000 | -0.0003 | -0.088 | -0.0086 |
| 09-10 | 1 | +0.117 | +0.003 | -0.0035 | +0.118 | +0.0019 |

Names with the largest |price change|: ZKC -0.0527 (net -0.0481), T +0.0390 (net +0.0547), CAP +0.0159 (net +0.0151), USELESS -0.0132 (net -0.0132), COLLECT -0.0106 (net -0.0106), AKE +0.0094 (net +0.0093).


| name (most negative net change) | price | carry (weight) | carry (repricing) | cost | net | interval changed | FTRIM switch |
|---|---|---|---|---|---|---|---|
| ZKCUSDT | -0.0527 | -0.0125 | +0.0081 | -0.00014 | -0.0481 | True | True |
| USELESSUSDT | -0.0132 | -0.0000 | +0.0000 | +0.00001 | -0.0132 | False | False |
| COLLECTUSDT | -0.0106 | +0.0001 | +0.0000 | -0.00001 | -0.0106 | False | False |
| CAKEUSDT | -0.0081 | -0.0000 | +0.0000 | -0.00000 | -0.0080 | False | False |
| SOMIUSDT | -0.0070 | -0.0001 | +0.0000 | +0.00004 | -0.0070 | False | False |
| LDOUSDT | -0.0065 | +0.0000 | +0.0000 | -0.00002 | -0.0065 | False | False |
| INJUSDT | -0.0061 | +0.0001 | +0.0000 | -0.00002 | -0.0063 | False | False |
| EPICUSDT | -0.0060 | +0.0000 | +0.0000 | +0.00000 | -0.0060 | False | False |
| AIOUSDT | -0.0051 | +0.0001 | +0.0000 | -0.00002 | -0.0051 | False | False |
| BOMEUSDT | -0.0047 | -0.0001 | +0.0000 | +0.00002 | -0.0046 | False | False |

### P4 · construction-only part of the D_K − R_K gap (sum of the nine group Shapley values = total − REM; k 90)
| seed | caliber | outcome | total | REM (model) | construction | reading |
|---|---|---|---|---|---|---|
| KA_s42 | REG | price | -1.13 [-3.97, +1.64] | -0.62 [-1.28, +0.08] | -0.51 [-3.06, +1.95] | not detected, not excluded: below -3.06 or above +1.95 excluded (95%, descriptive) |
| KA_s42 | REG | carry | +0.45 [-0.12, +1.12] | -0.03 [-0.06, +0.00] | +0.48 [-0.07, +1.13] | not detected, not excluded: below -0.07 or above +1.13 excluded (95%, descriptive) |
| KA_s42 | REG | net | -1.56 [-4.51, +1.40] | -0.59 [-1.27, +0.12] | -0.97 [-3.60, +1.69] | not detected, not excluded: below -3.60 or above +1.69 excluded (95%, descriptive) |
| KA_s42 | T5C | price | -1.20 [-4.01, +1.53] | -0.62 [-1.28, +0.08] | -0.58 [-3.09, +1.86] | not detected, not excluded: below -3.09 or above +1.86 excluded (95%, descriptive) |
| KA_s42 | T5C | carry | +0.18 [-0.22, +0.65] | -0.03 [-0.05, -0.02] | +0.21 [-0.18, +0.67] | not detected, not excluded: below -0.18 or above +0.67 excluded (95%, descriptive) |
| KA_s42 | T5C | net | -1.36 [-4.20, +1.43] | -0.58 [-1.26, +0.12] | -0.77 [-3.30, +1.73] | not detected, not excluded: below -3.30 or above +1.73 excluded (95%, descriptive) |
| KA_s2027 | REG | price | -0.80 [-3.65, +1.85] | -0.62 [-1.28, +0.08] | -0.19 [-2.76, +2.19] | not detected, not excluded: below -2.76 or above +2.19 excluded (95%, descriptive) |
| KA_s2027 | REG | carry | +0.45 [-0.12, +1.12] | -0.03 [-0.06, +0.00] | +0.48 [-0.07, +1.13] | not detected, not excluded: below -0.07 or above +1.13 excluded (95%, descriptive) |
| KA_s2027 | REG | net | -1.23 [-4.18, +1.67] | -0.59 [-1.27, +0.12] | -0.64 [-3.34, +1.91] | not detected, not excluded: below -3.34 or above +1.91 excluded (95%, descriptive) |
| KA_s2027 | T5C | price | -0.90 [-3.71, +1.70] | -0.62 [-1.28, +0.08] | -0.28 [-2.81, +2.06] | not detected, not excluded: below -2.81 or above +2.06 excluded (95%, descriptive) |
| KA_s2027 | T5C | carry | +0.18 [-0.23, +0.64] | -0.03 [-0.05, -0.02] | +0.21 [-0.18, +0.66] | not detected, not excluded: below -0.18 or above +0.66 excluded (95%, descriptive) |
| KA_s2027 | T5C | net | -1.05 [-3.84, +1.70] | -0.58 [-1.26, +0.12] | -0.47 [-2.97, +1.95] | not detected, not excluded: below -2.97 or above +1.95 excluded (95%, descriptive) |

### P5 · where the deployed books' fixed-weight carry correction comes from (`devices/t5d_posthoc_dk_carry.py`; Σ w·(C4 corrected − C4 x0910)·1e4 / 61; producer FTRIM from 2026-09-02 12:00Z)

**D_K** — total +0.2526 (before FTRIM start +0.1972 over 15 anchors, after +0.0554 over 46); residual vs components 1.1e-15.

| name | total | before FTRIM start | after | held anchors with a changed interval | first .. last | mean weight there (×1e3) | carry ratio corrected / x0910 |
|---|---|---|---|---|---|---|---|
| SKRUSDT | +0.2070 | +0.1780 | +0.0289 | 47 | 2026-08-31 04:00Z .. 2026-09-07 20:00Z | -3.89 | 4 |
| IOSTUSDT | +0.0443 | +0.0000 | +0.0443 | 19 | 2026-09-07 00:00Z .. 2026-09-10 00:00Z | +2.34 | 0.125 |
| SOPHUSDT | -0.0191 | +0.0000 | -0.0191 | 9 | 2026-09-08 16:00Z .. 2026-09-10 00:00Z | +0.72 | 4 |
| ZKCUSDT | +0.0138 | +0.0130 | +0.0009 | 17 | 2026-08-31 04:00Z .. 2026-09-02 20:00Z | -5.67 | 2, 4 |
| COTIUSDT | +0.0061 | +0.0061 | +0.0000 | 5 | 2026-08-31 04:00Z .. 2026-08-31 20:00Z | -9.46 | 4 |
| TUSDT | +0.0003 | +0.0000 | +0.0003 | 3 | 2026-09-05 16:00Z .. 2026-09-06 00:00Z | -2.29 | 4 |

**D_B** — total +0.2481 (before FTRIM start +0.1884 over 15 anchors, after +0.0597 over 46).

| name | total | before FTRIM start | after | held anchors with a changed interval | first .. last | mean weight there (×1e3) | carry ratio corrected / x0910 |
|---|---|---|---|---|---|---|---|
| SKRUSDT | +0.1975 | +0.1685 | +0.0290 | 47 | 2026-08-31 04:00Z .. 2026-09-07 20:00Z | -3.82 | 4 |
| IOSTUSDT | +0.0510 | +0.0000 | +0.0510 | 21 | 2026-09-06 16:00Z .. 2026-09-10 00:00Z | +2.83 | 0.125 |
| SOPHUSDT | -0.0216 | +0.0000 | -0.0216 | 9 | 2026-09-08 16:00Z .. 2026-09-10 00:00Z | +1.13 | 4 |
| ZKCUSDT | +0.0149 | +0.0140 | +0.0009 | 17 | 2026-08-31 04:00Z .. 2026-09-02 20:00Z | -5.99 | 2, 4 |
| COTIUSDT | +0.0060 | +0.0060 | +0.0000 | 5 | 2026-08-31 04:00Z .. 2026-08-31 20:00Z | -9.18 | 4 |
| TUSDT | +0.0003 | +0.0000 | +0.0003 | 3 | 2026-09-05 16:00Z .. 2026-09-06 00:00Z | -1.93 | 4 |


## T11 · devices and inputs
| item | sha256 |
|---|---|
| t5d_interval_sources.py | `ef5a20b900aaf7e6fb4a3c2e3b01b8c54d8223a6c22368af50e8f8188d1f8105` |
| t5d_ivfix_panel.py | `63c16a6836fd205dfaca425fdce312999974e3575945e16144970ffab2650829` |
| t5d_drive.py | `7408b2fab740835f57796de54cd9fbc4306b3dd23305deda4ead2004df1e27aa` |
| w10_sleeve_t5c.py (T5c device, unchanged) | `23604230871b8fc7efd7b3ba31fccaf6850a3d159ce08f872755dd6068a0a8c5` |
| t5d_bridge.py (run 2) | `b99b870c70950f78074e2a025da3c8c4ed25738227ba635e98c892e540bd296e` |
| t5d_bridge.py (run 1, archived) | `99b46129a5840732e0ec27787eb0998b563653c9ee7844b3f8c83e55e18c655f` |
| t5d_posthoc.py | `329934eee97877768ee5b19d48efc6fd7824ed04310160e129596bb3dbf86422` |
| corrected panel (pod2) | `a5d7fb9731b259e875d1d5229e23005c524635452d95c142e2c0d3aab2881f4e` |
| bridge components npz | `2cc33650694bbf1afbad8a5b9b7ed5648ae7a34ad22fd8bb643a54933121f094` |
| interval source list (cc_tmp) | `0006e2afffa2c618a033fd1b362680d60444997cc1a696c33f1709eddf9127fd` |
| per-settlement source list (pod2, cc_tmp) | `8dbe87d31ddb6dad0a35412c3bde8dcd1977c6186a9cb9235d2799943fa10a97` |
| t5d_posthoc_seed.py | `12a32cea3c51bd9b415e5f9fab280f30571955358326e4c926880c5b4d54edb5` |
| t5d_posthoc_fallback.py | `2cd0df5b957e1f53145759c53d0301ff56da5955f97800f637c6755602848cee` |
| t5d_posthoc_dk_carry.py (Mac) | `a64babfd40ab5eddbf31658d0710e43976bb897a5febf6a5dbafaadf334cda9c` |
| /workspace/uplift_2026-09-11/r6/r6_panel_splice.py | `cccc5b6be9248671ac9370b6313eaa8a3e9b397414d86db18db2b344e836743d` |
| /workspace/data/wide_panel_4h_v2ext.npz | `5e67c0559daa904d8f0526b6e268e93dcb45aab89d82646cf79a794445481116` |
| /workspace/uplift_2026-09-11/r6/out/wide_panel_4h_v2ext_x0910.npz | `042478f7d8e9f9476341a2acb310828fcf1f5d4a855c2ad0105a08e78f604549` |
| /workspace/uplift_2026-09-11/r6/dl/r6_fund_sep.json.gz | `bfd9bc65c24916ac7824cd7348a0773f0b7e1dc544797089c020b7742f2e885b` |
| /workspace/uplift_r2_2026-09-13/T5d/inputs/t5d_interval_sources.json | `0006e2afffa2c618a033fd1b362680d60444997cc1a696c33f1709eddf9127fd` |
| /workspace/fund_aug.json.gz | `8a9e771577602dd1875a87fb07f982bc2c255e740966f911469420a44a53a8c2` |
| arm KA_s42 (pod2 only) | `e4d386007f88a7c2dc862c7d817db36eeba872c862553b9546d46f7dbf9f6786` |
| arm KA_s2027 (pod2 only) | `4be316c9fd8b35c99ace31c53259f56de59c8d23e601123a99bf48717e245f7b` |
| arm KB_s42 (pod2 only) | `99f7859f9fbb80145d57a86cc1001d715dae1c8b37cf160e48d69f17b23ad85b` |
| arm KB_s2027 (pod2 only) | `c41124a52293d182ae508db0f2559775f0a5459c7e4fdd678cb841d7695ae15d` |
