# TABLES · T5 (rendered by `devices/t5_tables.py` from receipts; do not edit by hand)

Units: modelled carry, bps / 4h anchor / unit gross, positive = paid. A_T5 = 27 combo anchors 2026-08-26 04Z..08-30 20Z (excl. 08-29 20Z, 08-30 00Z). CIs: UTC-day block bootstrap over **5 day-blocks — descriptive, not a test**. Rendered 2026-09-13T07:27:40Z.

## T0 · gates
| gate | result |
|---|---|
| G-P (T5 device vs T1 arms, 24 arrays, both seeds) | True; window anchors 31; derived sha `4c5b972eebfb…` |
| G-T1 (reproduce T1) | True; D2 A29 mean 2.217588879 vs T1 2.217588879, per-anchor maxabs 0.0e+00; replay A30 carry s42 1.0126543749 vs 1.0126543749, s2027 1.0186763002 vs 1.0186763002 |
| G-PANEL (device panel rows == x0910 rows, FN & IV, 30 rows × 829) | True |
| G-SIM-R (simulator all-R vs device dump) | True; max|Δ| s42 {'sm': '0.0e+00', 'smf': '0.0e+00', 'smb': '0.0e+00', 'smr': '0.0e+00', 'legs_T1rows': '3.5e-18', 'SMC': '0.0e+00', 'SMFC': '0.0e+00', 'carry_T1cal': '0.0e+00', 'leg_identity': '3.5e-18'}; s2027 {'sm': '0.0e+00', 'smf': '0.0e+00', 'smb': '0.0e+00', 'smr': '0.0e+00', 'legs_T1rows': '1.7e-18', 'SMC': '0.0e+00', 'SMFC': '0.0e+00', 'carry_T1cal': '0.0e+00', 'leg_identity': '3.5e-18'} |
| G-ARCH-D (target_live == 0.55·kc + 0.45·fc) | True; maxabs 0.0e+00 (Mac and pod2) |
| G-LEG (Σ legs = book) | True; R 3.5e-18, B_N 1.7e-18 |
| G-CLOSE (every lens, per anchor) | True; max 2.7e-15 |
| G-ING-V (backward EMA 09-13 → 09-04 00Z reproduces stored fund z) | True; max|Δz| 0.0e+00; acc rel err max 4.9e-13 |
| G-ING-S (archived nonzero ⊆ pm∩sel∩LIVE; sel count == producer log) | True; violations 0; count mismatches 0 |
| G-POD | GPU 0 %, 2 MiB → 0 %, 2 MiB; PIDs 333197 Tl;  339489 Tl → 333197 Tl;  339489 Tl |
| K group included (T4 served-king arrays for the window) | False → (e) NOT MEASURED in the main table |

## T1 · headline (A_T5, n = 27)
| seed | C_D deployed | C_R replay (T1 caliber) | Δ | C_D / C_R |
|---|---|---|---|---|
| 42 | +2.186 [+1.818, +2.555] | +0.995 [+0.929, +1.065] | +1.192 [+0.870, +1.514] | +2.198 [+1.916, +2.481] |
| 2027 | +2.186 [+1.818, +2.555] | +1.000 [+0.932, +1.073] | +1.186 [+0.867, +1.506] | +2.186 [+1.910, +2.467] |

Excluded king-form anchors (descriptive): 2026-08-26 00:00Z C_D 1.779 vs C_R 0.953 (s42); 2026-08-30 00:00Z C_D 3.497 vs C_R 1.530 (s42). T1's 2.218 (A29) includes these two.

## T2 · construction bridge — Shapley (primary), fixed order, one-at-a-time, leave-one-out
| component | s42 mean | s42 share of Δ | s2027 mean | s2027 share | order step s42 / s2027 | one-at-a-time s42 | leave-one-out s42 |
|---|---|---|---|---|---|---|---|
| G0 口径(装置 carry 分子只含成员) | +0.000 [-0.000, +0.000] | +0.0% [-0.0, +0.0] | +0.000 [-0.000, +0.000] | +0.0% [-0.0, +0.0] | — | — | — |
| T FTRIM(回放有, 部署窗内无) | +0.694 [+0.556, +0.844] | +58.2% [+44.3, +80.3] | +0.698 [+0.560, +0.849] | +58.8% [+44.5, +81.7] | +0.607 / +0.614 | +0.607 | +0.735 |
| W 席位 w3 | -0.009 [-0.015, -0.002] | -0.7% [-1.7, -0.1] | -0.013 [-0.020, -0.006] | -1.1% [-2.2, -0.4] | -0.052 / -0.056 | -0.006 | -0.003 |
| B fund 秩基(829 基 → 成员内) | -0.034 [-0.039, -0.030] | -2.9% [-3.9, -2.2] | -0.035 [-0.041, -0.031] | -3.0% [-4.0, -2.3] | -0.072 / -0.074 | -0.094 | +0.005 |
| V fund 值与新鲜度(面板 → 生产者 EMA) | -0.060 [-0.074, -0.049] | -5.1% [-7.2, -3.7] | -0.061 [-0.075, -0.050] | -5.2% [-7.4, -3.8] | +0.022 / +0.022 | -0.127 | -0.001 |
| M 成员集(meta∩UMASK → 生产者 400) | +0.061 [+0.029, +0.115] | +5.2% [+2.5, +9.3] | +0.061 [+0.028, +0.116] | +5.1% [+2.4, +9.5] | +0.071 / +0.071 | +0.040 | +0.057 |
| X 出场规则 | -0.003 [-0.010, +0.004] | -0.3% [-0.8, +0.4] | -0.003 [-0.010, +0.004] | -0.2% [-0.8, +0.4] | +0.020 / +0.021 | +0.003 | +0.000 |
| S 可交易门 | +0.002 [-0.003, +0.005] | +0.2% [-0.3, +0.4] | +0.002 [-0.002, +0.006] | +0.2% [-0.2, +0.5] | +0.000 / +0.000 | -0.006 | -0.000 |
| P 止损层(回放独有) | +0.220 [+0.048, +0.426] | +18.5% [+4.3, +32.0] | +0.221 [+0.052, +0.427] | +18.6% [+4.4, +32.1] | +0.239 / +0.241 | +0.131 | +0.304 |
| H 状态路径(部署暖启动) | +0.321 [+0.147, +0.517] | +27.0% [+15.0, +37.8] | +0.319 [+0.145, +0.513] | +26.9% [+14.8, +37.7] | +0.363 / +0.355 | +0.310 | +0.354 |
| Z 执行口径 reshape | +0.010 [+0.001, +0.018] | +0.8% [+0.1, +1.3] | +0.010 [+0.001, +0.019] | +0.9% [+0.1, +1.4] | +0.004 / +0.005 | +0.014 | +0.004 |
| REM 分数(king + V2MAIN)与未对上部分 | -0.011 [-0.033, +0.002] | -0.9% [-2.6, +0.2] | -0.013 [-0.039, +0.003] | -1.1% [-3.2, +0.3] | — | — | — |

Fixed order: T → B → W → V → M → S → X → P → H → Z. Shapley efficiency maxabs 1.8e-15 / 1.1e-15. Node skips 0 / 0.

## T3 · per UTC day (s42; s2027 within ±0.02)
| day | n | C_D | C_R | Δ | φ_T | φ_H | φ_P | φ_M | REM |
|---|---|---|---|---|---|---|---|---|---|
| 08-26 | 5 | 2.324 | 1.094 | +1.230 | +0.455 | +0.570 | +0.209 | +0.055 | +0.003 |
| 08-27 | 6 | 2.615 | 0.981 | +1.634 | +0.675 | +0.368 | +0.622 | +0.028 | -0.002 |
| 08-28 | 6 | 1.719 | 0.878 | +0.840 | +0.692 | +0.101 | +0.143 | +0.026 | +0.004 |
| 08-29 | 5 | 1.685 | 0.959 | +0.726 | +0.687 | +0.051 | +0.060 | +0.042 | -0.010 |
| 08-30 | 5 | 2.598 | 1.087 | +1.511 | +0.966 | +0.552 | +0.003 | +0.170 | -0.055 |

## T4 · L-S lens: side (own sign) × 8h-equivalent current rate (TC1)
| cell | C_D cell | C_R cell | Δ cell s42 | share s42 | share s2027 |
|---|---|---|---|---|---|
| long|<=-30bp | -0.003 | -0.004 | +0.001 [+0.000, +0.002] | +0.1% [+0.0, +0.1] | +0.0% [+0.0, +0.1] |
| long|-10..0bp | -0.005 | -0.005 | -0.000 [-0.002, +0.001] | -0.0% [-0.1, +0.1] | -0.0% [-0.1, +0.1] |
| long|0..10bp | +0.438 | +0.453 | -0.015 [-0.021, -0.010] | -1.2% [-2.2, -0.8] | -1.3% [-2.4, -0.8] |
| long|10..30bp | +0.132 | +0.102 | +0.030 [+0.016, +0.044] | +2.6% [+1.4, +3.7] | +2.5% [+1.3, +3.5] |
| short|<=-30bp | +1.304 | +0.333 | +0.971 [+0.652, +1.284] | +81.5% [+73.7, +86.2] | +81.7% [+74.0, +86.3] |
| short|-30..-10bp | +0.333 | +0.129 | +0.203 [+0.163, +0.257] | +17.1% [+12.3, +24.3] | +17.0% [+12.3, +24.3] |
| short|-10..0bp | +0.139 | +0.141 | -0.002 [-0.015, +0.013] | -0.2% [-1.1, +1.4] | -0.3% [-1.2, +1.4] |
| short|0..10bp | -0.151 | -0.155 | +0.005 [+0.002, +0.007] | +0.4% [+0.2, +0.5] | +0.4% [+0.2, +0.5] |

**TC1** short ∧ rn8 ≤ −10bp: share of Δ +98.5% [+97.6, +99.1] (s42) / +98.7% [+97.8, +99.2] (s2027) ⇒ **YES / YES**. That cohort is 74.8% of the deployed book's carry and 46.5% of the replay's; its gross share 6.4% (D) vs 2.2% (R).

## T5 · L-N lens: name sets (task b, c)
| cell | s42 mean | s42 share | s2027 share |
|---|---|---|---|
| onlyD_long | +0.084 [+0.073, +0.097] | +7.0% [+5.6, +9.3] | +7.1% [+5.6, +9.3] |
| onlyD_short | +0.231 [+0.158, +0.324] | +19.4% [+14.8, +24.5] | +19.5% [+14.8, +24.7] |
| onlyR_long | -0.040 [-0.044, -0.037] | -3.4% [-4.7, -2.7] | -3.5% [-4.8, -2.7] |
| onlyR_short | -0.006 [-0.024, +0.007] | -0.5% [-2.5, +0.7] | -0.5% [-2.6, +0.8] |
| common_same_long | -0.025 [-0.029, -0.020] | -2.1% [-3.1, -1.4] | -2.2% [-3.3, -1.5] |
| common_same_short | +0.956 [+0.723, +1.209] | +80.2% [+74.9, +85.0] | +80.3% [+74.9, +85.0] |
| common_opposite | -0.008 [-0.010, -0.006] | -0.7% [-1.0, -0.5] | -0.6% [-0.9, -0.4] |

Names per anchor (mean): only in D 27.3, only in R 8.9, common 252.9. Top common names by Σ(w̃_D − w̃_R)·c (s42, bps/anchor; weights ×1e3 per unit gross; rn8 mean bp):

| name | contribution | w_D | w_R | rn8 |
|---|---|---|---|---|
| ONGUSDT | +0.4900 | -7.47 | -1.25 | -169.1 |
| ACEUSDT | +0.0924 | -7.09 | -1.25 | -31.7 |
| TUTUSDT | +0.0816 | -2.81 | -0.65 | -43.6 |
| COTIUSDT | +0.0779 | -8.24 | -2.61 | -27.7 |
| HOMEUSDT | +0.0771 | -7.52 | -2.45 | -30.5 |
| BICOUSDT | +0.0744 | -7.02 | -3.15 | -37.5 |
| SANDUSDT | +0.0259 | -5.55 | -2.35 | -16.4 |
| STORJUSDT | +0.0211 | -1.95 | -0.65 | -57.3 |
| CLOUSDT | +0.0174 | +7.43 | +2.03 | +6.5 |
| ZKPUSDT | +0.0092 | +0.57 | +1.54 | -6.1 |
| HUSDT | +0.0091 | +7.80 | +2.03 | +3.1 |
| RIVERUSDT | +0.0077 | +7.66 | +3.33 | +3.6 |
| MANTRAUSDT | +0.0077 | -4.48 | -3.66 | -8.8 |
| SIRENUSDT | -0.0066 | +7.91 | +9.37 | +9.1 |
| EDENUSDT | +0.0056 | -7.09 | -7.50 | -9.8 |

## T6 · L-C lens: chains, legs, seats (task a)
| book | K chain | F (V2MAIN) chain | K-king | K-fund | F-f10 | F-fund | inherited (K+F) |
|---|---|---|---|---|---|---|---|
| R s42 | +0.618 | +0.377 | +0.094 | +0.523 | +0.050 | +0.327 | +0.000 |
| B_N s42 (D rules, R scores) | +1.318 | +0.879 | +0.024 | +0.105 | +0.009 | +0.134 | +1.925 |
| R s2027 | +0.619 | +0.381 | +0.095 | +0.525 | +0.045 | +0.336 | +0.000 |
| B_N s2027 (D rules, R scores) | +1.319 | +0.881 | +0.024 | +0.105 | +0.009 | +0.135 | +1.926 |
| D (archived) | +1.313 [+1.008, +1.639] | +0.874 [+0.699, +1.063] | not measurable | not measurable | not measurable | not measurable | — |

Seats (mean over A_T5): replay w3 = [0.333, 0.000, 0.667]; deployed w3m = [0.224, 0.000, 0.776]. Fund-leg share of the replay's carry 85.5%. The B_N leg split keeps banded positions on their inherited attribution (T1 leg convention), so its "inherited" column is a bookkeeping convention, not a staleness measure.

## T7 · names behind each large component (per-name Shapley, s42, bps/anchor; weights ×1e3)

**T FTRIM(回放有, 部署窗内无)** (component mean +0.694):

| name | φ | w_D | w_R | rn8 bp | live |
|---|---|---|---|---|---|
| ONGUSDT | +0.1869 | -7.47 | -1.25 | -169.1 | True |
| TUTUSDT | +0.0798 | -2.81 | -0.65 | -43.6 | True |
| BICOUSDT | +0.0705 | -7.02 | -3.15 | -37.5 | True |
| COTIUSDT | +0.0699 | -8.24 | -2.61 | -27.7 | True |
| ACEUSDT | +0.0661 | -7.09 | -1.25 | -31.7 | True |
| HOMEUSDT | +0.0640 | -7.52 | -2.45 | -30.5 | True |
| ONTUSDT | +0.0350 | -7.35 | +0.00 | -31.5 | True |
| SANDUSDT | +0.0344 | -5.55 | -2.35 | -16.4 | True |
| SKRUSDT | +0.0165 | -1.99 | +0.00 | -23.4 | True |
| EDENUSDT | +0.0133 | -7.09 | -7.50 | -9.8 | True |

**H 状态路径(部署暖启动)** (component mean +0.321):

| name | φ | w_D | w_R | rn8 bp | live |
|---|---|---|---|---|---|
| ONGUSDT | +0.0974 | -7.47 | -1.25 | -169.1 | True |
| ONTUSDT | +0.0372 | -7.35 | +0.00 | -31.5 | True |
| ACEUSDT | +0.0355 | -7.09 | -1.25 | -31.7 | True |
| HOMEUSDT | +0.0270 | -7.52 | -2.45 | -30.5 | True |
| BICOUSDT | +0.0233 | -7.02 | -3.15 | -37.5 | True |
| TUTUSDT | +0.0217 | -2.81 | -0.65 | -43.6 | True |
| COTIUSDT | +0.0212 | -8.24 | -2.61 | -27.7 | True |
| SKRUSDT | +0.0204 | -1.99 | +0.00 | -23.4 | True |
| BMTUSDT | +0.0158 | -7.18 | +0.00 | -9.5 | True |
| STORJUSDT | +0.0130 | -1.95 | -0.65 | -57.3 | True |

**P 止损层(回放独有)** (component mean +0.220):

| name | φ | w_D | w_R | rn8 bp | live |
|---|---|---|---|---|---|
| ONGUSDT | +0.2351 | -7.47 | -1.25 | -169.1 | True |
| CLOUSDT | +0.0149 | +7.43 | +2.03 | +6.5 | True |
| RIVERUSDT | +0.0083 | +7.66 | +3.33 | +3.6 | True |
| HUSDT | +0.0071 | +7.80 | +2.03 | +3.1 | True |
| BEATUSDT | +0.0030 | +7.52 | +1.79 | +1.8 | True |
| SKYAIUSDT | +0.0024 | +5.83 | +1.97 | +1.4 | True |
| TUTUSDT | +0.0021 | -2.81 | -0.65 | -43.6 | True |
| AVAAIUSDT | +0.0019 | +7.20 | +3.25 | +1.3 | True |
| BSBUSDT | +0.0014 | +5.70 | +1.80 | +1.1 | True |
| 1000PEPEUSDT | +0.0014 | +4.24 | +0.24 | +0.8 | True |

**M 成员集(meta∩UMASK → 生产者 400)** (component mean +0.061):

| name | φ | w_D | w_R | rn8 bp | live |
|---|---|---|---|---|---|
| ONTUSDT | +0.0531 | -7.35 | +0.00 | -31.5 | True |
| SKRUSDT | +0.0410 | -1.99 | +0.00 | -23.4 | True |
| BTRUSDT | +0.0270 | +6.78 | +0.00 | +10.9 | True |
| GASUSDT | +0.0164 | -6.10 | +0.00 | -7.5 | True |
| BMTUSDT | +0.0159 | -7.18 | +0.00 | -9.5 | True |
| INXUSDT | +0.0072 | +6.15 | +0.00 | +3.0 | True |
| CYSUSDT | +0.0069 | +6.03 | +0.00 | +3.2 | True |
| LSKUSDT | +0.0054 | -3.93 | +0.00 | -6.3 | True |
| BRUSDT | +0.0031 | +6.45 | +0.00 | +1.3 | True |
| SWARMSUSDT | +0.0030 | +1.55 | +0.00 | +4.5 | True |

**V fund 值与新鲜度(面板 → 生产者 EMA)** (component mean -0.060):

| name | φ | w_D | w_R | rn8 bp | live |
|---|---|---|---|---|---|
| ONGUSDT | -0.0119 | -7.47 | -1.25 | -169.1 | True |
| TUTUSDT | -0.0065 | -2.81 | -0.65 | -43.6 | True |
| BICOUSDT | -0.0063 | -7.02 | -3.15 | -37.5 | True |
| HOMEUSDT | -0.0060 | -7.52 | -2.45 | -30.5 | True |
| COTIUSDT | -0.0044 | -8.24 | -2.61 | -27.7 | True |
| SANDUSDT | -0.0040 | -5.55 | -2.35 | -16.4 | True |
| BTWUSDT | -0.0039 | +0.00 | +10.79 | +5.6 | False |
| ACEUSDT | -0.0037 | -7.09 | -1.25 | -31.7 | True |
| SLXUSDT | -0.0021 | +0.00 | -5.43 | -4.0 | False |
| JSTUSDT | -0.0015 | -5.28 | -5.47 | -6.9 | True |

**B fund 秩基(829 基 → 成员内)** (component mean -0.034):

| name | φ | w_D | w_R | rn8 bp | live |
|---|---|---|---|---|---|
| ONGUSDT | -0.0063 | -7.47 | -1.25 | -169.1 | True |
| BICOUSDT | -0.0041 | -7.02 | -3.15 | -37.5 | True |
| HOMEUSDT | -0.0036 | -7.52 | -2.45 | -30.5 | True |
| TUTUSDT | -0.0036 | -2.81 | -0.65 | -43.6 | True |
| COTIUSDT | -0.0025 | -8.24 | -2.61 | -27.7 | True |
| SANDUSDT | -0.0024 | -5.55 | -2.35 | -16.4 | True |
| ACEUSDT | -0.0022 | -7.09 | -1.25 | -31.7 | True |
| JSTUSDT | -0.0012 | -5.28 | -5.47 | -6.9 | True |
| STORJUSDT | -0.0009 | -1.95 | -0.65 | -57.3 | True |
| GWEIUSDT | -0.0008 | -6.27 | -7.91 | -5.1 | True |

## T8 · TC2: August deep-negative short cohort vs early-September short-side price losses (deployed book, D2 on x0910 y4)

E2a = 61 anchors (08-31 00Z..09-10 00Z), 09-06 = 6 anchors, C_Aug = 29 names. **M1 = 0.190**, M2 (09-06) = 0.151, M3 = 0.227 ⇒ **DIFFERENT NAMES** (threshold 0.2; M1 is within 0.011 of it). Short-side price over E2a: all names -4.53 bps/anchor; C_Aug names +0.47 bps/anchor.

| top short loser (E2a) | Σ short price bps | 09-06 | in C_Aug | Aug carry Σ | anchors short | short ∧ rn8 ≤ −10bp |
|---|---|---|---|---|---|---|
| USELESSUSDT | -44.59 | +2.45 | False | 0.00 | 30 | 1 |
| FLOCKUSDT | -36.53 | -10.13 | False | 0.00 | 54 | 17 |
| ARBUSDT | -29.22 | -3.59 | False | 0.00 | 61 | 0 |
| MINAUSDT | -28.28 | -1.82 | True | 0.10 | 61 | 9 |
| COTIUSDT | -27.54 | -6.71 | True | 3.00 | 61 | 14 |
| NEARUSDT | -15.12 | -5.18 | False | 0.00 | 61 | 0 |
| ATOMUSDT | -13.85 | -1.44 | False | 0.00 | 61 | 0 |
| INJUSDT | -13.37 | -4.00 | False | 0.00 | 61 | 0 |
| PORTALUSDT | -12.91 | -1.92 | True | 0.08 | 61 | 4 |
| SIGNUSDT | -12.00 | -3.15 | False | 0.00 | 46 | 1 |
| EPICUSDT | -11.81 | -2.28 | False | 0.00 | 61 | 0 |
| AEROUSDT | -11.24 | -0.45 | False | 0.00 | 61 | 0 |
| WALUSDT | -11.12 | -1.85 | False | 0.00 | 61 | 0 |
| STXUSDT | -10.61 | +0.11 | True | 0.06 | 61 | 0 |
| APTUSDT | -9.72 | -0.93 | False | 0.00 | 61 | 0 |

| C_Aug name (by Aug carry) | Aug carry Σ bps | E2a short price Σ bps |
|---|---|---|
| ONGUSDT | 16.40 | +3.69 |
| TUTUSDT | 3.40 | +35.71 |
| BICOUSDT | 3.40 | +5.47 |
| HOMEUSDT | 3.06 | +7.73 |
| COTIUSDT | 3.00 | -27.54 |
| ACEUSDT | 2.97 | -5.66 |
| ONTUSDT | 2.93 | -2.47 |
| SKRUSDT | 1.85 | +9.88 |
| SANDUSDT | 1.22 | +1.60 |
| STORJUSDT | 0.95 | +0.00 |
| EDENUSDT | 0.91 | +11.95 |
| BMTUSDT | 0.66 | +11.00 |

## T9 · diagnostics
| item | s42 | s2027 |
|---|---|---|
| REM split: flow at A (C_D − v(N′)) | -0.0045 [-0.0143, +0.0003] | -0.0048 [-0.0151, +0.0002] |
| REM split: carried state (v(N′) − v(G)) | -0.0065 [-0.0186, +0.0021] | -0.0081 [-0.0240, +0.0028] |
| B_N vs D: unit-gross L1 distance / weight correlation | 0.0283 / 0.9992 | 0.0269 / 0.9992 |
| replay FTRIM kills per anchor (king chain / V2MAIN chain); members; sel | 8.2 / 8.2; 373; 261 | 8.2 / 8.2; 373; 261 |

## T10 · ADDENDUM 1 (post-hoc proxy for e): replay king model, column 80 v0 → v1 (T4 K0 → K1)
| seed | φ_K1 mean | share of Δ | at R node | at N node | node range | K0–K1 member rank corr (mean / min) | reading |
|---|---|---|---|---|---|---|---|
| 42 | +0.00006 [-0.00041, +0.00055] | +0.0% [-0.0, +0.1] | +0.00008 | +0.00085 | [-0.0090, +0.0057] | 0.9959 / 0.9917 | NEGLIGIBLE |
| 2027 | +0.00003 [-0.00045, +0.00053] | +0.0% [-0.0, +0.1] | +0.00001 | +0.00085 | [-0.0091, +0.0057] | 0.9959 / 0.9917 | NEGLIGIBLE |

Gate A1: K0 rows == device SLOW rows True; K0 nodes == main run True. Not the served booster 29ffaf58.

## T11 · devices and inputs
| item | sha256 |
|---|---|
| t5_bridge.py (self) | `d5e84953e24f523125b831a1908731ed19953e744230619efa8d41a873d58f38` |
| t5_drive.py (self) | `7a6c8fc6d8d87405ec6de237b445da63b4721cc8c2e405624b4af00156f0f1ea` |
| w10_sleeve_t5.py (derived) | `4c5b972eebfb48c3423b0f6c1336b13cb588fb8ec8edf9c7948d67c59dc05add` |
| t5_live_ingredients.py (self) | `e5759bfe8eaefd4aa4acbb5d4946df51d0f70b0408b7b5c9e3893d59d332bd39` |
| t5_addendum_h2b.py (self) | `3bab9a87cf2db625af7e82c1cfcefe2326c80286f4282740b25458aad95594b7` |
| /workspace/uplift_r2_2026-09-13/T5/arms/C0_s42_t5.npz | `05f37b068b14c3bc967793a03f94405b202126be433501dc7399c0ff6b0dc8a3` |
| /workspace/uplift_r2_2026-09-13/T5/arms/C0_s2027_t5.npz | `ee53e0a65435f5ef1fc0b1b2d45c776ddc7bb7adbc99ca5c496823ab2b9d4883` |
| /workspace/uplift_r2_2026-09-13/T5/receipts/T5_live_ingredients.npz | `378981640fa7268aa54ba27231f3694d378f51de2b2c143d744745a00db263f9` |
| /workspace/uplift_2026-09-11/r6/out/meta_newprod_v4_x0910.npz | `a8eb359701c71acfe853a295eb055bdbb04e1c29b6534ccdf23aeaff69907245` |
| /workspace/uplift_2026-09-11/r6/out/wide_panel_4h_v2ext_x0910.npz | `042478f7d8e9f9476341a2acb310828fcf1f5d4a855c2ad0105a08e78f604549` |
| /workspace/uplift_r2_2026-09-13/T1/receipts/T1_d2.npz | `70d742fdce7ede314c11a06475cccb1f30bcc5b483f87b8c7d150f4390cbabb6` |
| /workspace/uplift_r2_2026-09-13/T1/receipts/RECEIPT_T1_addendum1.json | `af7d493a3fc01776c827d881348a454318fbaba5f94d80da3987c84d951f4093` |
| arms C0_s42_t5 / C0_s2027_t5 (pod2) | `05f37b068b14c3bc967793a03f94405b202126be433501dc7399c0ff6b0dc8a3` / `ee53e0a65435f5ef1fc0b1b2d45c776ddc7bb7adbc99ca5c496823ab2b9d4883` |
