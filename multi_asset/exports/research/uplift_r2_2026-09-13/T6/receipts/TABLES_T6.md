# TABLES_T6 (rendered by `devices/t6_tables.py`)

Sources: `receipts/RECEIPT_T6_compute.json` sha256 `7c41281a44eb07f7a3bdbbf5b780a195490eab4a49978a0e6c97dcd9d4d87d5d` (device `t6_compute.py` sha256 `103974f3d7958a4e506bb3b38208d188e0c9f692a106999ab7deb57404f134fc`); `receipts/POSTHOC_T6_decomposition.json` sha256 `9ed66309b70f9a4589be589691be048bfd0542aeb96f733c1f81c568b3d6ba44` (device `t6_posthoc.py` sha256 `6b4ec88f2937f583d0c5c7d3395b110a1865e420537a2b15c49cac05befed5c5`, **POST-HOC**).

Units: SR = annualized net Sharpe of g = net_ex/gross_total (bps / 4h anchor / unit gross), ×√2190. W_FULL = 2022-01-31 00Z…2026-08-30 20Z (10,038 anchors); FROZEN = 2025-03-01 00Z…2026-08-10 20Z (3,168); W_ALPHA = W_FULL minus first 900 (9,138).

## A. Gates

GATE-X extraction: s42 True, s2027 True (every member's g re-hashes to FAMILY_T6.json).

| GATE-0 item | reproduced | published | tol | pass |
|---|---|---|---|---|
| s42_WALPHA_g | 0.6341956722 | 0.6341957000 | 5e-07 | True |
| s42_WALPHA_SR | 1.2912234378 | 1.2912000000 | 5e-05 | True |
| s42_WFULL_g | 0.5607541233 | 0.5608000000 | 5e-05 | True |
| s42_WFULL_SR | 1.1061629689 | 1.1062000000 | 5e-05 | True |
| s42_FROZEN_SR | 2.9357130374 | 2.9357130374 | 1e-09 | True |
| s2027_FROZEN_SR | 2.9021472126 | 2.9021000000 | 5e-05 | True |
| s2027_WALPHA_g | 0.6579358470 | 0.6579000000 | 5e-05 | True |
| s2027_WALPHA_SR | 1.3298650689 | 1.3299000000 | 5e-05 | True |

GATE-I: splits 12870, block length 627 (W_FULL F1 s42, 6 oldest rows dropped), equal blocks True, max |block-sum SR − direct SR| over 20 random splits × 125 members = 1.07e-14 ⇒ True.

| control | rep | PBO | slope | P(OOS loss) | SEL | SEL SR | N_eff | DSR(SEL,N_eff) | nested SR | planted picks | haircut | gate checks | pass |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| C1 | 0 | 0.0000 | -0.937 | 0.0000 | m124 | 3.735 | 123.5 | 1.000 | +3.576 | 4/4 | +0.000 | PBO_le_0p05=True, SEL_is_planted=True, nested_picks_planted_ge3=True, DSR_ge_0p95=True | **True** |
| C1 | 1 | 0.0000 | -1.000 | 0.0000 | m124 | 3.550 | 123.5 | 1.000 | +3.196 | 4/4 | +0.000 | PBO_le_0p05=True, SEL_is_planted=True, nested_picks_planted_ge3=True, DSR_ge_0p95=True | True |
| C1 | 2 | 0.0000 | -1.000 | 0.0000 | m124 | 4.466 | 123.5 | 1.000 | +4.465 | 4/4 | +0.000 | PBO_le_0p05=True, SEL_is_planted=True, nested_picks_planted_ge3=True, DSR_ge_0p95=True | True |
| C1 | 3 | 0.0000 | -1.000 | 0.0000 | m124 | 3.877 | 123.5 | 1.000 | +3.788 | 4/4 | +0.000 | PBO_le_0p05=True, SEL_is_planted=True, nested_picks_planted_ge3=True, DSR_ge_0p95=True | True |
| C1 | 4 | 0.0019 | -0.958 | 0.0019 | m124 | 3.415 | 123.5 | 1.000 | +2.930 | 3/4 | -0.728 | PBO_le_0p05=True, SEL_is_planted=True, nested_picks_planted_ge3=True, DSR_ge_0p95=True | True |
| C1 | 5 | 0.0000 | -1.000 | 0.0000 | m124 | 4.555 | 123.5 | 1.000 | +4.615 | 4/4 | +0.000 | PBO_le_0p05=True, SEL_is_planted=True, nested_picks_planted_ge3=True, DSR_ge_0p95=True | True |
| C1 | 6 | 0.0000 | -1.000 | 0.0000 | m124 | 3.401 | 123.5 | 1.000 | +3.338 | 4/4 | +0.000 | PBO_le_0p05=True, SEL_is_planted=True, nested_picks_planted_ge3=True, DSR_ge_0p95=True | True |
| C1 | 7 | 0.0000 | -1.000 | 0.0000 | m124 | 3.997 | 123.5 | 1.000 | +3.790 | 4/4 | +0.000 | PBO_le_0p05=True, SEL_is_planted=True, nested_picks_planted_ge3=True, DSR_ge_0p95=True | True |
| C1 | 8 | 0.0016 | -0.968 | 0.0016 | m124 | 2.912 | 123.5 | 0.999 | +2.453 | 4/4 | +0.000 | PBO_le_0p05=True, SEL_is_planted=True, nested_picks_planted_ge3=True, DSR_ge_0p95=True | True |
| C1 | 9 | 0.0000 | -1.000 | 0.0000 | m124 | 4.494 | 123.5 | 1.000 | +4.806 | 4/4 | +0.000 | PBO_le_0p05=True, SEL_is_planted=True, nested_picks_planted_ge3=True, DSR_ge_0p95=True | True |
| C2 | 0 | 0.8089 | -0.968 | 0.7846 | m117 | 0.908 | 123.5 | 0.299 | -0.509 | 0/4 | -1.308 | PBO_ge_0p30=True, nested_SR_within_2p5SE=True, DSR_lt_0p95=True | **True** |
| C2 | 1 | 0.4520 | +0.074 | 0.4022 | m100 | 1.426 | 123.5 | 0.582 | +0.121 | 0/4 | -1.059 | PBO_ge_0p30=True, nested_SR_within_2p5SE=True, DSR_lt_0p95=True | True |
| C2 | 2 | 0.3632 | -0.352 | 0.3612 | m087 | 1.405 | 123.5 | 0.622 | +0.513 | 0/4 | -1.031 | PBO_ge_0p30=True, nested_SR_within_2p5SE=True, DSR_lt_0p95=True | True |
| C2 | 3 | 0.6276 | -0.523 | 0.6187 | m002 | 1.105 | 123.5 | 0.448 | +0.353 | 0/4 | -0.403 | PBO_ge_0p30=True, nested_SR_within_2p5SE=True, DSR_lt_0p95=True | True |
| C2 | 4 | 0.5669 | -0.405 | 0.5056 | m061 | 1.143 | 123.5 | 0.365 | -0.549 | 0/4 | -2.259 | PBO_ge_0p30=True, nested_SR_within_2p5SE=True, DSR_lt_0p95=True | True |
| C2 | 5 | 0.3560 | +0.266 | 0.3503 | m031 | 1.502 | 123.5 | 0.747 | +0.407 | 0/4 | -1.191 | PBO_ge_0p30=True, nested_SR_within_2p5SE=True, DSR_lt_0p95=True | True |
| C2 | 6 | 0.4780 | -0.306 | 0.4812 | m017 | 1.344 | 123.4 | 0.648 | +0.625 | 0/4 | -0.843 | PBO_ge_0p30=True, nested_SR_within_2p5SE=True, DSR_lt_0p95=True | True |
| C2 | 7 | 0.5962 | -0.734 | 0.5796 | m007 | 0.959 | 123.5 | 0.265 | -0.110 | 0/4 | -1.017 | PBO_ge_0p30=True, nested_SR_within_2p5SE=True, DSR_lt_0p95=True | True |
| C2 | 8 | 0.5900 | -0.277 | 0.5960 | m083 | 1.064 | 123.5 | 0.489 | -0.174 | 0/4 | -0.846 | PBO_ge_0p30=True, nested_SR_within_2p5SE=True, DSR_lt_0p95=True | True |
| C2 | 9 | 0.3747 | -0.622 | 0.3485 | m057 | 1.284 | 123.5 | 0.584 | +0.202 | 0/4 | -1.242 | PBO_ge_0p30=True, nested_SR_within_2p5SE=True, DSR_lt_0p95=True | True |

GATE-C verdict (replicate 0 of each control): **True**; ALL GATES: **True**.

## B. CSCV-PBO (S = 16, all 12,870 splits)

| family · seed | window | N | T used | PBO | median logit | slope OOS~IS | intercept | corr | P(OOS loss) | mean SR_IS(n*) | mean SR_OOS(n*) | most selected (share) |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| F1_s42 | W_FULL | 125 | 10032 | **0.1568** | 4.127 | -0.641 | +3.052 | -0.450 | 0.0322 | 2.097 | 1.708 | XIB_PWR230k_s42 0.58; IB_LAG50_PWR230k_s42 0.24; Ns_A0_s42 0.11; TW_Ns_stale1_s42 0.04; WIRE_A0_s42 0.03 |
| F1_s42 | FROZEN | 125 | 3168 | **0.1873** | 3.186 | -0.706 | +5.892 | -0.695 | 0.0099 | 3.877 | 3.153 | XIB_PWR230k_s42 0.35; IB_LAG50_PWR230k_s42 0.31; C_AS_fast_a005 0.14; G_A0_k0_s42_FIT 0.10; C_AS_fast_a010 0.04 |
| F1_s42 | W_ALPHA | 125 | 9136 | **0.2307** | 4.127 | -0.723 | +3.165 | -0.509 | 0.0577 | 2.171 | 1.596 | XIB_PWR230k_s42 0.55; IB_LAG50_PWR230k_s42 0.21; TW_Ns_stale1_s42 0.10; Ns_A0_s42 0.08; WIRE_A0_s42 0.03 |
| F1_s2027 | W_FULL | 70 | 10032 | **0.1473** | 3.541 | -0.731 | +3.206 | -0.524 | 0.0256 | 2.076 | 1.688 | IB_LAG50_PWR230k_s2027 0.42; XIB_PWR230k_s2027 0.38; Ns_A0_s2027 0.13; TW_Ns_stale1_s2027 0.04; WIRE_A0_s2027 0.03 |
| F1_s2027 | FROZEN | 70 | 3168 | **0.2099** | 1.808 | -0.731 | +5.701 | -0.739 | 0.0049 | 3.736 | 2.969 | IB_LAG50_PWR230k_s2027 0.31; XIB_PWR230k_s2027 0.29; G_A0_k0_s2027_FIT 0.15; S_a010_b50e4_s2027 0.10; S_a005_b25e4_s2027 0.08 |
| F2_s42 | W_FULL | 88 | 10032 | **0.1509** | 4.477 | -0.662 | +3.128 | -0.493 | 0.0233 | 2.094 | 1.743 | XIB_PWR230k_s42 0.82; Ns_A0_s42 0.14; N_A0_s42 0.03; S_a005_b25e4_s42 0.00; R12_BYP_either_90_a100_s42 0.00 |
| F2_s42 | FROZEN | 88 | 3168 | **0.1618** | 4.477 | -0.711 | +6.062 | -0.703 | 0.0103 | 3.803 | 3.359 | XIB_PWR230k_s42 0.82; S_a005_b25e4_s42 0.07; R12_BYP_rally_90_a100_s42 0.04; Ns_A0_s42 0.02; S_a010_b50e4_s42 0.02 |
| F3_s42 | W_FULL | 101 | 10032 | **0.5078** | 0.000 | -0.753 | +2.039 | -0.604 | 0.1227 | 1.648 | 0.798 | Ns_A0_s42 0.39; C_AS_fast_a005 0.11; S_a005_b25e4_s42 0.10; WIRE_A0_s42 0.07; C_AS_fast_a010 0.07 |
| F3_s42 | FROZEN | 101 | 3168 | **0.2998** | 1.474 | -0.875 | +5.794 | -0.727 | 0.0145 | 3.525 | 2.710 | C_AS_fast_a005 0.35; C_AS_fast_a010 0.31; R7_FUND 0.12; S_a005_b25e4_s42 0.05; S_a010_b50e4_s42 0.03 |
| F4_s42 | W_FULL | 147 | 10032 | **0.3603** | 2.110 | -0.353 | +2.081 | -0.194 | 0.0256 | 2.305 | 1.268 | XIB_PWR230k_s42 0.39; SL_ORTHLAG_PWR230k_s42 0.15; IB_LAG50_PWR230k_s42 0.12; PWR_C_TBF3D__p 0.10; P6_AMX_PWR_s42 0.06 |
| F4_s42 | FROZEN | 147 | 3168 | **0.2162** | 2.737 | -0.312 | +4.020 | -0.228 | 0.0473 | 3.908 | 2.799 | XIB_PWR230k_s42 0.34; IB_LAG50_PWR230k_s42 0.29; C_AS_fast_a005 0.12; G_A0_k0_s42_FIT 0.09; C_AS_fast_a010 0.04 |
| F5_s42 | W_FULL | 108 | 10032 | **0.1517** | 3.980 | -0.641 | +3.052 | -0.450 | 0.0322 | 2.097 | 1.708 | XIB_PWR230k_s42 0.58; IB_LAG50_PWR230k_s42 0.24; Ns_A0_s42 0.11; TW_Ns_stale1_s42 0.04; WIRE_A0_s42 0.03 |
| F5_s42 | FROZEN | 108 | 3168 | **0.1779** | 3.035 | -0.709 | +5.906 | -0.697 | 0.0099 | 3.877 | 3.157 | XIB_PWR230k_s42 0.35; IB_LAG50_PWR230k_s42 0.31; C_AS_fast_a005 0.14; G_A0_k0_s42_FIT 0.10; C_AS_fast_a010 0.04 |

## C. DSR (Bailey & López de Prado 2014; N_eff = participation ratio; P(SR>3) = PSR(3/√2190 + SR0), T6 extension)


**F1_s42 · W_FULL** — N_raw 125, **N_eff 1.570**, cross-member sd of SR 0.4519, SR min / median / max -0.672 / 1.006 / 2.062

| target | member | SR | rank | skew | kurt | PSR(0) undeflated | PSR(3.0) undeflated | N | SR0 (ann.) | P(true SR>0) | P(true SR>3.0) |
|---|---|---|---|---|---|---|---|---|---|---|---|
| SEL | XIB_PWR230k_s42 | 2.0620 | 1/125 | -0.559 | 12.93 | 1.0000 | 0.0240 | N_eff 1.57 (floored to 2) | 0.2349 | 0.9999 | 0.006690 |
| | | | | | | | | N_raw 125 | 1.1787 | 0.9688 | 0.000004 |
| | | | | | | | | 300 | 1.3085 | 0.9440 | 0.000001 |
| | | | | | | | | 825 (ledger low) | 1.4462 | 0.9030 | 0.000000 |
| | | | | | | | | 1,221 (ledger high) | 1.4965 | 0.8835 | 0.000000 |
| A0 | A0_PWR230k_s42 | 1.1062 | 34/125 | -0.995 | 24.55 | 0.9903 | 0.0000 | N_eff 1.57 (floored to 2) | 0.2349 | 0.9672 | 0.000003 |
| | | | | | | | | N_raw 125 | 1.1787 | 0.4391 | 0.000000 |
| | | | | | | | | 300 | 1.3085 | 0.3345 | 0.000000 |
| | | | | | | | | 825 (ledger low) | 1.4462 | 0.2363 | 0.000000 |
| | | | | | | | | 1,221 (ledger high) | 1.4965 | 0.2048 | 0.000000 |

**F1_s42 · FROZEN** — N_raw 125, **N_eff 1.507**, cross-member sd of SR 0.7291, SR min / median / max -1.028 / 2.673 / 3.758

| target | member | SR | rank | skew | kurt | PSR(0) undeflated | PSR(3.0) undeflated | N | SR0 (ann.) | P(true SR>0) | P(true SR>3.0) |
|---|---|---|---|---|---|---|---|---|---|---|---|
| SEL | XIB_PWR230k_s42 | 3.7576 | 1/125 | -0.360 | 8.16 | 1.0000 | 0.8141 | N_eff 1.51 (floored to 2) | 0.3790 | 1.0000 | 0.672353 |
| | | | | | | | | N_raw 125 | 1.9016 | 0.9857 | 0.088722 |
| | | | | | | | | 300 | 2.1111 | 0.9739 | 0.055281 |
| | | | | | | | | 825 (ledger low) | 2.3331 | 0.9535 | 0.031626 |
| | | | | | | | | 1,221 (ledger high) | 2.4144 | 0.9434 | 0.025396 |
| A0 | A0_PWR230k_s42 | 2.9357 | 27/125 | -0.178 | 6.42 | 0.9998 | 0.4694 | N_eff 1.51 (floored to 2) | 0.3790 | 0.9989 | 0.298514 |
| | | | | | | | | N_raw 125 | 1.9016 | 0.8913 | 0.009518 |
| | | | | | | | | 300 | 2.1111 | 0.8373 | 0.004733 |
| | | | | | | | | 825 (ledger low) | 2.3331 | 0.7638 | 0.002121 |
| | | | | | | | | 1,221 (ledger high) | 2.4144 | 0.7330 | 0.001556 |

**F1_s42 · W_ALPHA** — N_raw 125, **N_eff 1.592**, cross-member sd of SR 0.4814, SR min / median / max -0.721 / 1.187 / 2.108

| target | member | SR | rank | skew | kurt | PSR(0) undeflated | PSR(3.0) undeflated | N | SR0 (ann.) | P(true SR>0) | P(true SR>3.0) |
|---|---|---|---|---|---|---|---|---|---|---|---|
| SEL | XIB_PWR230k_s42 | 2.1078 | 1/125 | -0.179 | 9.04 | 1.0000 | 0.0350 | N_eff 1.59 (floored to 2) | 0.2502 | 0.9999 | 0.010189 |
| | | | | | | | | N_raw 125 | 1.2555 | 0.9582 | 0.000006 |
| | | | | | | | | 300 | 1.3938 | 0.9264 | 0.000002 |
| | | | | | | | | 825 (ledger low) | 1.5404 | 0.8754 | 0.000000 |
| | | | | | | | | 1,221 (ledger high) | 1.5940 | 0.8516 | 0.000000 |
| A0 | A0_PWR230k_s42 | 1.2912 | 38/125 | -0.106 | 8.11 | 0.9958 | 0.0002 | N_eff 1.59 (floored to 2) | 0.2502 | 0.9831 | 0.000033 |
| | | | | | | | | N_raw 125 | 1.2555 | 0.5290 | 0.000000 |
| | | | | | | | | 300 | 1.3938 | 0.4172 | 0.000000 |
| | | | | | | | | 825 (ledger low) | 1.5404 | 0.3058 | 0.000000 |
| | | | | | | | | 1,221 (ledger high) | 1.5940 | 0.2685 | 0.000000 |

**F1_s2027 · W_FULL** — N_raw 70, **N_eff 1.669**, cross-member sd of SR 0.4619, SR min / median / max 0.046 / 1.056 / 2.032

| target | member | SR | rank | skew | kurt | PSR(0) undeflated | PSR(3.0) undeflated | N | SR0 (ann.) | P(true SR>0) | P(true SR>3.0) |
|---|---|---|---|---|---|---|---|---|---|---|---|
| SEL | XIB_PWR230k_s2027 | 2.0321 | 1/70 | -0.573 | 13.07 | 1.0000 | 0.0206 | N_eff 1.67 (floored to 2) | 0.2401 | 0.9999 | 0.005426 |
| | | | | | | | | N_raw 70 | 1.1096 | 0.9741 | 0.000006 |
| | | | | | | | | 300 | 1.3374 | 0.9285 | 0.000001 |
| | | | | | | | | 825 (ledger low) | 1.4780 | 0.8787 | 0.000000 |
| | | | | | | | | 1,221 (ledger high) | 1.5295 | 0.8554 | 0.000000 |
| A0 | A0_PWR230k_s2027 | 1.1417 | 24/70 | -0.994 | 24.46 | 0.9920 | 0.0000 | N_eff 1.67 (floored to 2) | 0.2401 | 0.9715 | 0.000005 |
| | | | | | | | | N_raw 70 | 1.1096 | 0.5270 | 0.000000 |
| | | | | | | | | 300 | 1.3374 | 0.3397 | 0.000000 |
| | | | | | | | | 825 (ledger low) | 1.4780 | 0.2388 | 0.000000 |
| | | | | | | | | 1,221 (ledger high) | 1.5295 | 0.2064 | 0.000000 |

**F1_s2027 · FROZEN** — N_raw 70, **N_eff 1.572**, cross-member sd of SR 0.7346, SR min / median / max -0.890 / 2.679 / 3.586

| target | member | SR | rank | skew | kurt | PSR(0) undeflated | PSR(3.0) undeflated | N | SR0 (ann.) | P(true SR>0) | P(true SR>3.0) |
|---|---|---|---|---|---|---|---|---|---|---|---|
| SEL | XIB_PWR230k_s2027 | 3.5857 | 1/70 | -0.384 | 8.12 | 1.0000 | 0.7551 | N_eff 1.57 (floored to 2) | 0.3818 | 0.9999 | 0.595032 |
| | | | | | | | | N_raw 70 | 1.7648 | 0.9841 | 0.082199 |
| | | | | | | | | 300 | 2.1270 | 0.9573 | 0.034568 |
| | | | | | | | | 825 (ledger low) | 2.3506 | 0.9274 | 0.018702 |
| | | | | | | | | 1,221 (ledger high) | 2.4325 | 0.9131 | 0.014707 |
| A0 | A0_PWR230k_s2027 | 2.9021 | 17/70 | -0.214 | 6.48 | 0.9997 | 0.4536 | N_eff 1.57 (floored to 2) | 0.3818 | 0.9987 | 0.283823 |
| | | | | | | | | N_raw 70 | 1.7648 | 0.9123 | 0.013230 |
| | | | | | | | | 300 | 2.1270 | 0.8222 | 0.004013 |
| | | | | | | | | 825 (ledger low) | 2.3506 | 0.7445 | 0.001764 |
| | | | | | | | | 1,221 (ledger high) | 2.4325 | 0.7121 | 0.001285 |

**F2_s42 · W_FULL** — N_raw 88, **N_eff 1.267**, cross-member sd of SR 0.3632, SR min / median / max -0.201 / 1.051 / 2.062

| target | member | SR | rank | skew | kurt | PSR(0) undeflated | PSR(3.0) undeflated | N | SR0 (ann.) | P(true SR>0) | P(true SR>3.0) |
|---|---|---|---|---|---|---|---|---|---|---|---|
| SEL | XIB_PWR230k_s42 | 2.0620 | 1/88 | -0.559 | 12.93 | 1.0000 | 0.0240 | N_eff 1.27 (floored to 2) | 0.1888 | 1.0000 | 0.008746 |
| | | | | | | | | N_raw 88 | 0.9026 | 0.9928 | 0.000052 |
| | | | | | | | | 300 | 1.0516 | 0.9835 | 0.000014 |
| | | | | | | | | 825 (ledger low) | 1.1622 | 0.9711 | 0.000005 |
| | | | | | | | | 1,221 (ledger high) | 1.2026 | 0.9650 | 0.000003 |
| A0 | A0_PWR230k_s42 | 1.1062 | 27/88 | -0.995 | 24.55 | 0.9903 | 0.0000 | N_eff 1.27 (floored to 2) | 0.1888 | 0.9737 | 0.000005 |
| | | | | | | | | N_raw 88 | 0.9026 | 0.6664 | 0.000000 |
| | | | | | | | | 300 | 1.0516 | 0.5459 | 0.000000 |
| | | | | | | | | 825 (ledger low) | 1.1622 | 0.4529 | 0.000000 |
| | | | | | | | | 1,221 (ledger high) | 1.2026 | 0.4192 | 0.000000 |

**F2_s42 · FROZEN** — N_raw 88, **N_eff 1.239**, cross-member sd of SR 0.6031, SR min / median / max -0.686 / 2.761 / 3.758

| target | member | SR | rank | skew | kurt | PSR(0) undeflated | PSR(3.0) undeflated | N | SR0 (ann.) | P(true SR>0) | P(true SR>3.0) |
|---|---|---|---|---|---|---|---|---|---|---|---|
| SEL | XIB_PWR230k_s42 | 3.7576 | 1/88 | -0.360 | 8.16 | 1.0000 | 0.8141 | N_eff 1.24 (floored to 2) | 0.3135 | 1.0000 | 0.699734 |
| | | | | | | | | N_raw 88 | 1.4989 | 0.9961 | 0.191095 |
| | | | | | | | | 300 | 1.7462 | 0.9911 | 0.121903 |
| | | | | | | | | 825 (ledger low) | 1.9299 | 0.9844 | 0.083481 |
| | | | | | | | | 1,221 (ledger high) | 1.9971 | 0.9810 | 0.071968 |
| A0 | A0_PWR230k_s42 | 2.9357 | 20/88 | -0.178 | 6.42 | 0.9998 | 0.4694 | N_eff 1.24 (floored to 2) | 0.3135 | 0.9991 | 0.326154 |
| | | | | | | | | N_raw 88 | 1.4989 | 0.9567 | 0.031129 |
| | | | | | | | | 300 | 1.7462 | 0.9220 | 0.015405 |
| | | | | | | | | 825 (ledger low) | 1.9299 | 0.8849 | 0.008690 |
| | | | | | | | | 1,221 (ledger high) | 1.9971 | 0.8685 | 0.006971 |

**F3_s42 · W_FULL** — N_raw 101, **N_eff 1.512**, cross-member sd of SR 0.3996, SR min / median / max -0.201 / 1.034 / 1.440

| target | member | SR | rank | skew | kurt | PSR(0) undeflated | PSR(3.0) undeflated | N | SR0 (ann.) | P(true SR>0) | P(true SR>3.0) |
|---|---|---|---|---|---|---|---|---|---|---|---|
| SEL | Ns_A0_s42 | 1.4398 | 1/101 | -0.510 | 10.33 | 0.9989 | 0.0005 | N_eff 1.51 (floored to 2) | 0.2077 | 0.9955 | 0.000088 |
| | | | | | | | | N_raw 101 | 1.0126 | 0.8177 | 0.000000 |
| | | | | | | | | 300 | 1.1570 | 0.7258 | 0.000000 |
| | | | | | | | | 825 (ledger low) | 1.2786 | 0.6338 | 0.000000 |
| | | | | | | | | 1,221 (ledger high) | 1.3232 | 0.5977 | 0.000000 |
| A0 | A0_PWR230k_s42 | 1.1062 | 27/101 | -0.995 | 24.55 | 0.9903 | 0.0000 | N_eff 1.51 (floored to 2) | 0.2077 | 0.9712 | 0.000005 |
| | | | | | | | | N_raw 101 | 1.0126 | 0.5784 | 0.000000 |
| | | | | | | | | 300 | 1.1570 | 0.4573 | 0.000000 |
| | | | | | | | | 825 (ledger low) | 1.2786 | 0.3578 | 0.000000 |
| | | | | | | | | 1,221 (ledger high) | 1.3232 | 0.3233 | 0.000000 |

**F3_s42 · FROZEN** — N_raw 101, **N_eff 1.451**, cross-member sd of SR 0.7057, SR min / median / max -1.028 / 2.666 / 3.332

| target | member | SR | rank | skew | kurt | PSR(0) undeflated | PSR(3.0) undeflated | N | SR0 (ann.) | P(true SR>0) | P(true SR>3.0) |
|---|---|---|---|---|---|---|---|---|---|---|---|
| SEL | C_AS_fast_a005 | 3.3319 | 1/101 | -0.076 | 6.16 | 1.0000 | 0.6542 | N_eff 1.45 (floored to 2) | 0.3668 | 0.9998 | 0.483336 |
| | | | | | | | | N_raw 101 | 1.7884 | 0.9675 | 0.040827 |
| | | | | | | | | 300 | 2.0435 | 0.9382 | 0.020375 |
| | | | | | | | | 825 (ledger low) | 2.2584 | 0.9003 | 0.010641 |
| | | | | | | | | 1,221 (ledger high) | 2.3370 | 0.8828 | 0.008265 |
| A0 | A0_PWR230k_s42 | 2.9357 | 21/101 | -0.178 | 6.42 | 0.9998 | 0.4694 | N_eff 1.45 (floored to 2) | 0.3668 | 0.9989 | 0.303559 |
| | | | | | | | | N_raw 101 | 1.7884 | 0.9144 | 0.013559 |
| | | | | | | | | 300 | 2.0435 | 0.8564 | 0.005968 |
| | | | | | | | | 825 (ledger low) | 2.2584 | 0.7904 | 0.002800 |
| | | | | | | | | 1,221 (ledger high) | 2.3370 | 0.7624 | 0.002090 |

**F4_s42 · W_FULL** — N_raw 147, **N_eff 2.130**, cross-member sd of SR 0.6954, SR min / median / max -3.779 / 1.006 / 2.062

| target | member | SR | rank | skew | kurt | PSR(0) undeflated | PSR(3.0) undeflated | N | SR0 (ann.) | P(true SR>0) | P(true SR>3.0) |
|---|---|---|---|---|---|---|---|---|---|---|---|
| SEL | XIB_PWR230k_s42 | 2.0620 | 1/147 | -0.559 | 12.93 | 1.0000 | 0.0240 | N_eff 2.13 | 0.4011 | 0.9998 | 0.002371 |
| | | | | | | | | N_raw 147 | 1.8522 | 0.6710 | 0.000000 |
| | | | | | | | | 300 | 2.0137 | 0.5406 | 0.000000 |
| | | | | | | | | 825 (ledger low) | 2.2254 | 0.3652 | 0.000000 |
| | | | | | | | | 1,221 (ledger high) | 2.3030 | 0.3057 | 0.000000 |
| A0 | A0_PWR230k_s42 | 1.1062 | 43/147 | -0.995 | 24.55 | 0.9903 | 0.0000 | N_eff 2.13 | 0.4011 | 0.9318 | 0.000001 |
| | | | | | | | | N_raw 147 | 1.8522 | 0.0575 | 0.000000 |
| | | | | | | | | 300 | 2.0137 | 0.0276 | 0.000000 |
| | | | | | | | | 825 (ledger low) | 2.2254 | 0.0090 | 0.000000 |
| | | | | | | | | 1,221 (ledger high) | 2.3030 | 0.0057 | 0.000000 |

**F4_s42 · FROZEN** — N_raw 147, **N_eff 2.056**, cross-member sd of SR 1.2525, SR min / median / max -4.368 / 2.608 / 3.758

| target | member | SR | rank | skew | kurt | PSR(0) undeflated | PSR(3.0) undeflated | N | SR0 (ann.) | P(true SR>0) | P(true SR>3.0) |
|---|---|---|---|---|---|---|---|---|---|---|---|
| SEL | XIB_PWR230k_s42 | 3.7576 | 1/147 | -0.360 | 8.16 | 1.0000 | 0.8141 | N_eff 2.06 | 0.6830 | 0.9999 | 0.535047 |
| | | | | | | | | N_raw 147 | 3.3358 | 0.6905 | 0.001185 |
| | | | | | | | | 300 | 3.6266 | 0.5614 | 0.000359 |
| | | | | | | | | 825 (ledger low) | 4.0080 | 0.3839 | 0.000064 |
| | | | | | | | | 1,221 (ledger high) | 4.1476 | 0.3228 | 0.000032 |
| A0 | A0_PWR230k_s42 | 2.9357 | 27/147 | -0.178 | 6.42 | 0.9998 | 0.4694 | N_eff 2.06 | 0.6830 | 0.9964 | 0.186373 |
| | | | | | | | | N_raw 147 | 3.3358 | 0.3166 | 0.000025 |
| | | | | | | | | 300 | 3.6266 | 0.2050 | 0.000005 |
| | | | | | | | | 825 (ledger low) | 4.0080 | 0.1005 | 0.000001 |
| | | | | | | | | 1,221 (ledger high) | 4.1476 | 0.0742 | 0.000000 |

**F5_s42 · W_FULL** — N_raw 108, **N_eff 1.620**, cross-member sd of SR 0.4694, SR min / median / max -0.672 / 0.957 / 2.062

| target | member | SR | rank | skew | kurt | PSR(0) undeflated | PSR(3.0) undeflated | N | SR0 (ann.) | P(true SR>0) | P(true SR>3.0) |
|---|---|---|---|---|---|---|---|---|---|---|---|
| SEL | XIB_PWR230k_s42 | 2.0620 | 1/108 | -0.559 | 12.93 | 1.0000 | 0.0240 | N_eff 1.62 (floored to 2) | 0.2440 | 0.9999 | 0.006339 |
| | | | | | | | | N_raw 108 | 1.2006 | 0.9654 | 0.000003 |
| | | | | | | | | 300 | 1.3592 | 0.9309 | 0.000001 |
| | | | | | | | | 825 (ledger low) | 1.5021 | 0.8812 | 0.000000 |
| | | | | | | | | 1,221 (ledger high) | 1.5545 | 0.8578 | 0.000000 |
| A0 | A0_PWR230k_s42 | 1.1062 | 25/108 | -0.995 | 24.55 | 0.9903 | 0.0000 | N_eff 1.62 (floored to 2) | 0.2440 | 0.9657 | 0.000003 |
| | | | | | | | | N_raw 108 | 1.2006 | 0.4210 | 0.000000 |
| | | | | | | | | 300 | 1.3592 | 0.2965 | 0.000000 |
| | | | | | | | | 825 (ledger low) | 1.5021 | 0.2014 | 0.000000 |
| | | | | | | | | 1,221 (ledger high) | 1.5545 | 0.1718 | 0.000000 |

**F5_s42 · FROZEN** — N_raw 108, **N_eff 1.567**, cross-member sd of SR 0.7673, SR min / median / max -1.028 / 2.648 / 3.758

| target | member | SR | rank | skew | kurt | PSR(0) undeflated | PSR(3.0) undeflated | N | SR0 (ann.) | P(true SR>0) | P(true SR>3.0) |
|---|---|---|---|---|---|---|---|---|---|---|---|
| SEL | XIB_PWR230k_s42 | 3.7576 | 1/108 | -0.360 | 8.16 | 1.0000 | 0.8141 | N_eff 1.57 (floored to 2) | 0.3988 | 1.0000 | 0.663863 |
| | | | | | | | | N_raw 108 | 1.9623 | 0.9828 | 0.077761 |
| | | | | | | | | 300 | 2.2216 | 0.9649 | 0.042175 |
| | | | | | | | | 825 (ledger low) | 2.4553 | 0.9377 | 0.022673 |
| | | | | | | | | 1,221 (ledger high) | 2.5408 | 0.9243 | 0.017765 |
| A0 | A0_PWR230k_s42 | 2.9357 | 19/108 | -0.178 | 6.42 | 0.9998 | 0.4694 | N_eff 1.57 (floored to 2) | 0.3988 | 0.9988 | 0.290357 |
| | | | | | | | | N_raw 108 | 1.9623 | 0.8772 | 0.007818 |
| | | | | | | | | 300 | 2.2216 | 0.8028 | 0.003200 |
| | | | | | | | | 825 (ledger low) | 2.4553 | 0.7167 | 0.001327 |
| | | | | | | | | 1,221 (ledger high) | 2.5408 | 0.6812 | 0.000944 |

## D. Nested walk-forward selection (expanding training from 2022-01-31 00Z; criterion = SR on all earlier anchors)

| family · seed | window | H* (hindsight best on window) | SR(H*, window) | **SR nested** [CI95] | SR(H*, nested span) | SR(A0, span) | span best | **haircut = nested − H*(span)** [CI95] | level haircut | span anchors / days |
|---|---|---|---|---|---|---|---|---|---|---|
| F1_s42 | W_FULL | XIB_PWR230k_s42 | 2.062 | **1.610** [0.578, 2.711] | 2.261 | 1.374 | XIB_PWR230k_s42 2.261 | **-0.652** [-1.735, +0.392] | -0.453 | 8028 / 1338 |
| F1_s42 | FROZEN | XIB_PWR230k_s42 | 3.758 | **2.202** [0.457, 3.939] | 3.758 | 2.936 | XIB_PWR230k_s42 3.758 | **-1.555** [-3.347, +0.200] | -1.555 | 3168 / 528 |
| F1_s2027 | W_FULL | XIB_PWR230k_s2027 | 2.032 | **1.613** [0.595, 2.637] | 2.222 | 1.416 | XIB_PWR230k_s2027 2.222 | **-0.610** [-1.704, +0.418] | -0.419 | 8028 / 1338 |
| F1_s2027 | FROZEN | XIB_PWR230k_s2027 | 3.586 | **2.187** [0.405, 3.918] | 3.586 | 2.902 | XIB_PWR230k_s2027 3.586 | **-1.398** [-3.170, +0.297] | -1.398 | 3168 / 528 |
| F2_s42 | W_FULL | XIB_PWR230k_s42 | 2.062 | **1.603** [0.571, 2.706] | 2.261 | 1.374 | XIB_PWR230k_s42 2.261 | **-0.658** [-1.742, +0.384] | -0.459 | 8028 / 1338 |
| F2_s42 | FROZEN | XIB_PWR230k_s42 | 3.758 | **2.204** [0.459, 3.941] | 3.758 | 2.936 | XIB_PWR230k_s42 3.758 | **-1.554** [-3.344, +0.199] | -1.554 | 3168 / 528 |
| F3_s42 | W_FULL | Ns_A0_s42 | 1.440 | **1.358** [0.342, 2.427] | 1.464 | 1.374 | C_AS_fast_a010 1.547 | **-0.106** [-0.326, +0.117] | -0.081 | 8028 / 1338 |
| F3_s42 | FROZEN | C_AS_fast_a005 | 3.332 | **1.104** [-0.545, 2.881] | 3.332 | 2.936 | C_AS_fast_a005 3.332 | **-2.228** [-4.511, +0.079] | -2.228 | 3168 / 528 |
| F4_s42 | W_FULL | XIB_PWR230k_s42 | 2.062 | **1.399** [0.415, 2.388] | 2.261 | 1.374 | XIB_PWR230k_s42 2.261 | **-0.862** [-2.073, +0.275] | -0.663 | 8028 / 1338 |
| F4_s42 | FROZEN | XIB_PWR230k_s42 | 3.758 | **0.990** [-0.685, 2.523] | 3.758 | 2.936 | XIB_PWR230k_s42 3.758 | **-2.768** [-5.181, -0.467] | -2.768 | 3168 / 528 |
| F5_s42 | W_FULL | XIB_PWR230k_s42 | 2.062 | **1.610** [0.578, 2.711] | 2.261 | 1.374 | XIB_PWR230k_s42 2.261 | **-0.652** [-1.735, +0.392] | -0.453 | 8028 / 1338 |
| F5_s42 | FROZEN | XIB_PWR230k_s42 | 3.758 | **2.202** [0.457, 3.939] | 3.758 | 2.936 | XIB_PWR230k_s42 3.758 | **-1.555** [-3.347, +0.200] | -1.555 | 3168 / 528 |

**Per segment · F1_s42 · W_FULL** (negative Sharpe printed as NEG)

| segment | anchors | training anchors | selected (by training SR) | SR train | SR OOS | mean g OOS | A0 SR | H* SR | best member in segment | best SR |
|---|---|---|---|---|---|---|---|---|---|---|
| 2022 (training only) | 2010 | — | — | — | — | — | +0.010 | +1.274 | Ns_A0_s42 | 1.337 |
| 2023-01-01 00Z .. 2023-12-31 20Z | 2190 | 2010 | Ns_A0_s42 | 1.337 | -0.088 NEG | -0.035 | -1.936 NEG | +0.047 | WIRE_A0_s42 | 0.504 |
| 2024-01-01 00Z .. 2024-12-31 20Z | 2196 | 4200 | WIRE_A0_s42 | 0.762 | +2.125 | +1.033 | +1.088 | +1.780 | WIRE_A0_s42 | 2.125 |
| 2025-01-01 00Z .. 2025-12-31 20Z | 2190 | 6396 | WIRE_A0_s42 | 1.269 | -0.108 NEG | -0.072 | +1.187 | +1.936 | IB_LAG50_PWR230k_s42 | 1.936 |
| 2026-01-01 00Z .. 2026-08-30 20Z | 1452 | 8586 | IB_LAG50_PWR230k_s42 | 1.328 | +5.356 | +3.519 | +4.516 | +5.358 | XIB_PWR230k_s42 | 5.358 |

**Per segment · F1_s42 · FROZEN** (negative Sharpe printed as NEG)

| segment | anchors | training anchors | selected (by training SR) | SR train | SR OOS | mean g OOS | A0 SR | H* SR | best member in segment | best SR |
|---|---|---|---|---|---|---|---|---|---|---|
| 2025-03-01 00Z .. 2025-12-31 20Z | 1836 | 6750 | WIRE_A0_s42 | 1.386 | -0.607 NEG | -0.414 | +0.831 | +1.715 | C_AS_fast_a005 | 1.927 |
| 2026-01-01 00Z .. 2026-08-10 20Z | 1332 | 8586 | IB_LAG50_PWR230k_s42 | 1.328 | +6.281 | +4.077 | +5.433 | +6.283 | XIB_PWR230k_s42 | 6.283 |

**Per segment · F1_s2027 · W_FULL** (negative Sharpe printed as NEG)

| segment | anchors | training anchors | selected (by training SR) | SR train | SR OOS | mean g OOS | A0 SR | H* SR | best member in segment | best SR |
|---|---|---|---|---|---|---|---|---|---|---|
| 2022 (training only) | 2010 | — | — | — | — | — | +0.010 | +1.274 | Ns_A0_s2027 | 1.337 |
| 2023-01-01 00Z .. 2023-12-31 20Z | 2190 | 2010 | Ns_A0_s2027 | 1.337 | -0.114 NEG | -0.045 | -1.816 NEG | +0.026 | WIRE_A0_s2027 | 0.484 |
| 2024-01-01 00Z .. 2024-12-31 20Z | 2196 | 4200 | WIRE_A0_s2027 | 0.754 | +2.069 | +1.006 | +1.027 | +1.831 | WIRE_A0_s2027 | 2.069 |
| 2025-01-01 00Z .. 2025-12-31 20Z | 2190 | 6396 | WIRE_A0_s2027 | 1.244 | +0.106 | +0.069 | +1.306 | +1.985 | IB_LAG50_PWR230k_s2027 | 1.987 |
| 2026-01-01 00Z .. 2026-08-30 20Z | 1452 | 8586 | IB_LAG50_PWR230k_s2027 | 1.352 | +5.079 | +3.367 | +4.526 | +5.082 | XIB_PWR230k_s2027 | 5.082 |

**Per segment · F1_s2027 · FROZEN** (negative Sharpe printed as NEG)

| segment | anchors | training anchors | selected (by training SR) | SR train | SR OOS | mean g OOS | A0 SR | H* SR | best member in segment | best SR |
|---|---|---|---|---|---|---|---|---|---|---|
| 2025-03-01 00Z .. 2025-12-31 20Z | 1836 | 6750 | WIRE_A0_s2027 | 1.402 | -0.457 NEG | -0.310 | +0.869 | +1.667 | IB_LAG50_PWR230k_s2027 | 1.669 |
| 2026-01-01 00Z .. 2026-08-10 20Z | 1332 | 8586 | IB_LAG50_PWR230k_s2027 | 1.352 | +5.975 | +3.914 | +5.352 | +5.978 | XIB_PWR230k_s2027 | 5.978 |

## E. POST-HOC decomposition (written after reading §B–§D; descriptive, no verdict rests on it)

**PH1 — F1 minus the XIB_LAG50 line {XIB_PWR230k, IB_LAG50_PWR230k}**

| seed · window | N | N_eff | PBO | P(OOS loss) | slope | most selected | SEL (SR) | DSR(SEL,N_eff) | nested SR | H* (span SR) | haircut [CI95] | nested picks |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| s42_W_FULL | 123 | 1.57 | **0.4798** | 0.1254 | -0.773 | Ns_A0_s42 0.38; IB_OIV 0.12; C_AS_fast_a005 0.09 | Ns_A0_s42 (1.440) | 0.9951 | 1.358 | Ns_A0_s42 (1.464) | -0.106 [-0.326, +0.117] | Ns_A0_s42 → WIRE_A0_s42 → WIRE_A0_s42 → Ns_A0_s42 |
| s42_FROZEN | 123 | 1.51 | **0.3638** | 0.0137 | -0.887 | C_AS_fast_a005 0.31; C_AS_fast_a010 0.27; G_A0_k0_s42_FIT 0.19 | C_AS_fast_a005 (3.332) | 0.9998 | 1.104 | C_AS_fast_a005 (3.332) | -2.228 [-4.511, +0.079] | WIRE_A0_s42 → Ns_A0_s42 |
| s2027_W_FULL | 68 | 1.66 | **0.3825** | 0.1123 | -0.748 | Ns_A0_s2027 0.42; S_a005_b25e4_s2027 0.14; F05_s2027 0.11 | Ns_A0_s2027 (1.512) | 0.9970 | 1.431 | Ns_A0_s2027 (1.553) | -0.122 [-0.353, +0.104] | Ns_A0_s2027 → WIRE_A0_s2027 → WIRE_A0_s2027 → Ns_A0_s2027 |
| s2027_FROZEN | 68 | 1.57 | **0.3450** | 0.0089 | -0.966 | G_A0_k0_s2027_FIT 0.24; S_a010_b50e4_s2027 0.22; A_X5_s2027 0.16 | S_a010_b50e4_s2027 (3.239) | 0.9997 | 1.216 | S_a010_b50e4_s2027 (3.239) | -2.023 [-4.387, +0.365] | WIRE_A0_s2027 → Ns_A0_s2027 |

**PH2 — where the hindsight best H\* and A0 ranked on the training data at each nested selection point (F1)**

| seed · window | segment | selected | SR train (selected) | H* SR train | H* rank | A0 SR train | A0 rank | N |
|---|---|---|---|---|---|---|---|---|
| s42_W_FULL | 2023-01-01 00Z .. 2023-12-31 20Z | Ns_A0_s42 | 1.337 | 1.274 | 3 | +0.010 | 56 | 125 |
| s42_W_FULL | 2024-01-01 00Z .. 2024-12-31 20Z | WIRE_A0_s42 | 0.762 | 0.714 | 3 | -0.799 | 75 | 125 |
| s42_W_FULL | 2025-01-01 00Z .. 2025-12-31 20Z | WIRE_A0_s42 | 1.269 | 1.076 | 5 | -0.125 | 54 | 125 |
| s42_W_FULL | 2026-01-01 00Z .. 2026-08-30 20Z | IB_LAG50_PWR230k_s42 | 1.328 | 1.327 | 2 | +0.283 | 43 | 125 |
| s42_FROZEN | 2025-03-01 00Z .. 2025-12-31 20Z | WIRE_A0_s42 | 1.386 | 1.204 | 5 | +0.088 | 50 | 125 |
| s42_FROZEN | 2026-01-01 00Z .. 2026-08-10 20Z | IB_LAG50_PWR230k_s42 | 1.328 | 1.327 | 2 | +0.283 | 43 | 125 |
| s2027_W_FULL | 2023-01-01 00Z .. 2023-12-31 20Z | Ns_A0_s2027 | 1.337 | 1.274 | 3 | +0.010 | 38 | 70 |
| s2027_W_FULL | 2024-01-01 00Z .. 2024-12-31 20Z | WIRE_A0_s2027 | 0.754 | 0.705 | 3 | -0.752 | 53 | 70 |
| s2027_W_FULL | 2025-01-01 00Z .. 2025-12-31 20Z | WIRE_A0_s2027 | 1.244 | 1.086 | 5 | -0.116 | 39 | 70 |
| s2027_W_FULL | 2026-01-01 00Z .. 2026-08-30 20Z | IB_LAG50_PWR230k_s2027 | 1.352 | 1.351 | 2 | +0.330 | 28 | 70 |
| s2027_FROZEN | 2025-03-01 00Z .. 2025-12-31 20Z | WIRE_A0_s2027 | 1.402 | 1.252 | 5 | +0.137 | 36 | 70 |
| s2027_FROZEN | 2026-01-01 00Z .. 2026-08-10 20Z | IB_LAG50_PWR230k_s2027 | 1.352 | 1.351 | 2 | +0.330 | 28 | 70 |

**PH3 — nested selection minus A0 on the nested span (paired UTC-day block bootstrap, 2,000 draws)**

| seed · window | SR nested | SR A0 | difference [CI95] | days |
|---|---|---|---|---|
| s42_W_FULL | 1.610 | 1.374 | +0.235 [-0.849, +1.283] | 1338 |
| s42_FROZEN | 2.202 | 2.936 | -0.733 [-2.571, +1.047] | 528 |
| s2027_W_FULL | 1.613 | 1.416 | +0.196 [-0.882, +1.219] | 1338 |
| s2027_FROZEN | 2.187 | 2.902 | -0.715 [-2.567, +1.000] | 528 |
