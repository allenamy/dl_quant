## T1 · Devices, inputs, receipts (VERIFIED = printed by the scripts named)
| item | value |
|---|---|
| verbatim trainer | `/workspace/pod_f10_train_ext.py` sha256 `93cc2cdf925a1dada9190a5d86664d28c811d9ba0ecf3eaf377d54fc554f2598` |
| monthly trainer | `/workspace/review_scratch/dl_monthly_wf/pod_f10_train_monthly.py` sha256 `7bb39f8d93f2daf749535f8a6d91aecd15e8e3361de80138a29c6fbb6270b51e` = verbatim lines 1–260 (byte-identical, `cmp` receipt in run log) + `monthly_section.py` sha256 `a4b04a7e09f228232aaabf6206eab287e7c34cf8876794b5615c0623c471cc86`; `trainer.diff` 143 lines |
| mE60 run self-report | arm V2MAIN seed 42 cost 3.52 ldd 0.25 afix 0 epochs 15 lr 0.0003 win/burn/stride 96/24/48 embargo **60**; torch 2.11.0+cu128 cuda 12.8 gpu NVIDIA RTX PRO 4500 Blackwell; self_sha 7bb39f8d93f2daf7 base_sha 93cc2cdf925a1dad |
| mE60 inputs | targets `31d043e8f160a1d4` fea82 `9bc111a47cee54fc` fea89 `bebf272031549970` legs `facf53f7355da98f` (targets/fea82/fea89 asserted == 09-01 gate run `f8_ext/results/f10_V2MAIN_s42.json`) |
| mE60 env given | `{"ARM": "V2MAIN", "V2": "1", "SEED": "42", "COST": null, "LDD": null, "AFIX": null, "LDC": null, "CTXA": null, "REC": null, "PLE": null, "EPOCHS": null, "LR": null, "NCOL": null, "EXTRA": null, "LPP": null, "F10_DLW": "/workspace/dlw_ext", "F10_OUT": "/workspace/f8_ext", "MWF_OUT": "/workspace/review_scratch/dl_monthly_wf", "EMBARGO": "60", "MWF_TAG": null, "MONTHS": null, "FORCE": null}` |
| mE60 fold rule | `{"test": "calendar month YM", "train": "i < first_te - EMBM and ST[i+1]-ST[i] >= 50", "validation": "last 15% of train anchors (verbatim)", "rng": "torch.manual_seed(SEED+YM); np.random.seed(SEED+YM) per fold", "label_window": "5m rows [E+1, E+48] => label end = E + 4h", "causality": "max(E_train) + 4h <= E[first_te] - EMBM*4h", "grid": "4h anchors (all diffs 14400 s asserted)"}` |
| mE1 run self-report | arm V2MAIN seed 42 cost 3.52 ldd 0.25 afix 0 epochs 15 lr 0.0003 win/burn/stride 96/24/48 embargo **1**; torch 2.11.0+cu128 cuda 12.8 gpu NVIDIA RTX PRO 4500 Blackwell; self_sha 7bb39f8d93f2daf7 base_sha 93cc2cdf925a1dad |
| mE1 inputs | targets `31d043e8f160a1d4` fea82 `9bc111a47cee54fc` fea89 `bebf272031549970` legs `facf53f7355da98f` (targets/fea82/fea89 asserted == 09-01 gate run `f8_ext/results/f10_V2MAIN_s42.json`) |
| mE1 env given | `{"ARM": "V2MAIN", "V2": "1", "SEED": "42", "COST": null, "LDD": null, "AFIX": null, "LDC": null, "CTXA": null, "REC": null, "PLE": null, "EPOCHS": null, "LR": null, "NCOL": null, "EXTRA": null, "LPP": null, "F10_DLW": "/workspace/dlw_ext", "F10_OUT": "/workspace/f8_ext", "MWF_OUT": "/workspace/review_scratch/dl_monthly_wf", "EMBARGO": "1", "MWF_TAG": null, "MONTHS": null, "FORCE": null}` |
| mE1 fold rule | `{"test": "calendar month YM", "train": "i < first_te - EMBM and ST[i+1]-ST[i] >= 50", "validation": "last 15% of train anchors (verbatim)", "rng": "torch.manual_seed(SEED+YM); np.random.seed(SEED+YM) per fold", "label_window": "5m rows [E+1, E+48] => label end = E + 4h", "causality": "max(E_train) + 4h <= E[first_te] - EMBM*4h", "grid": "4h anchors (all diffs 14400 s asserted)"}` |
| replay device | `/workspace/review_scratch/dl_monthly_wf/replay/w10_health.py` sha256 `8684d9a9f43a8d15beaa559cd12bd8f2977a3d088b01b93835f60f2bbf98a53d` (= health_check w10_health.py) |
| replay masks/cost | umask_UPIT `ccb7a0805be2a106` costb_fee_steady `9349ca634747772d` meta_newprod `831857dd6a203523` pinned king `158cd4ac8f8f30f7` |
| yearly-fold file (baseline) | `/workspace/f8_2026-08-22/preds/f10_V2MAIN_s42.npy` sha256 `baf747ceb31f10d614ffac79b9c969c499e1c3e9f82edfec246d7cfb0f353ace` |
| stitched mE60 (ext grid, pure) | `/workspace/review_scratch/dl_monthly_wf/preds/f10_V2MAIN_mE60_s42.npy` sha256 `2c6e9756feabd0447e79fc93eaf65e0a14967eb1b3072789b48e37b6e60915cf` |
| stitched mE1 (ext grid, pure) | `/workspace/review_scratch/dl_monthly_wf/preds/f10_V2MAIN_mE1_s42.npy` sha256 `54bd748d2f1553774ebb5a72de61e417cbac9b7298f4e47775dbd546464b6bb0` |
| equivalence receipt | PASS [dl_monthly_wf device default path (log) vs axisB R0_pinned_log_s42] dev/probe_artifacts/w10_ablation_series_eq_pinned_log_s42.npz vs /workspace/review_scratch/cadence_seats/axisB/dev/probe_artifacts/w10_ablation_series_R0_pinned_log_s42.npz: arrays {'d30_n2_c42_rec': True, 'S0_rec': True, 'd30_n2_c42_W': True, 'S0_W': True} shapes {'d30_n2_c42_rec': ((10038, 23), (10038, 23)), 'S0_rec': ((10 |
| equivalence receipt | PASS [dl_monthly_wf baseline arm (prod, yearly FPRED) vs health_check M1_UPIT_prod_s42_ccal] dev_alt/probe_artifacts/w10_ablation_series_BASE_M1_UPIT_prod_s42_ccal.npz vs /workspace/review_scratch/health_check/dev_alt/probe_artifacts/w10_ablation_series_M1_UPIT_prod_s42_ccal.npz: arrays {'d30_n2_c42_rec': True, 'S0_rec': True, 'd30_n2_c42_W': True, 'S0_W': True} shapes {'d30_n2_c42_rec': ((10038,  |

## T2 · Fold table mE60 (embargo 60 anchors; VERIFIED `results/f10_V2MAIN_mE60_s42.json`; wall-clock per fit on the RTX PRO 4500)
| test month | n_test | n_train | max train label end | cutoff | causal | windows/epoch | best ep | best va | α* | net bps/anchor (train frame) | ES5 | turnover | wall s | s/epoch | test-month IC |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| 202501 | 186 | 6504 | 2024-12-22 00:00 | 2024-12-22 00:00 | OK | 113 | 6 | -3.166 | 0.0969 | +0.286 | 22.4 | 0.0728 | 280 | 18.6 | +0.0140 |
| 202502 | 168 | 6690 | 2025-01-22 00:00 | 2025-01-22 00:00 | OK | 116 | 3 | -3.481 | 0.0971 | +0.024 | 24.9 | 0.0810 | 295 | 19.6 | +0.0158 |
| 202503 | 186 | 6858 | 2025-02-19 00:00 | 2025-02-19 00:00 | OK | 119 | 1 | -3.348 | 0.0988 | -0.033 | 9.5 | 0.0862 | 306 | 20.4 | -0.0077 |
| 202504 | 180 | 7044 | 2025-03-22 00:00 | 2025-03-22 00:00 | OK | 123 | 1 | -3.469 | 0.0986 | +0.515 | 12.9 | 0.0863 | 314 | 20.9 | +0.0423 |
| 202505 | 186 | 7224 | 2025-04-21 00:00 | 2025-04-21 00:00 | OK | 126 | 2 | -4.249 | 0.0983 | +0.238 | 25.3 | 0.0818 | 323 | 21.5 | +0.0330 |
| 202506 | 180 | 7410 | 2025-05-22 00:00 | 2025-05-22 00:00 | OK | 129 | 2 | -3.652 | 0.0978 | -0.344 | 10.0 | 0.0846 | 332 | 22.2 | +0.0054 |
| 202507 | 186 | 7590 | 2025-06-21 00:00 | 2025-06-21 00:00 | OK | 132 | 0 | -4.317 | 0.0996 | +0.100 | 25.4 | 0.0702 | 339 | 22.6 | -0.0084 |
| 202508 | 186 | 7776 | 2025-07-22 00:00 | 2025-07-22 00:00 | OK | 136 | 1 | -4.355 | 0.0983 | +0.017 | 15.2 | 0.0737 | 351 | 23.4 | +0.0046 |
| 202509 | 180 | 7962 | 2025-08-22 00:00 | 2025-08-22 00:00 | OK | 139 | 4 | -3.799 | 0.0956 | +2.677 | 28.4 | 0.0547 | 358 | 23.9 | +0.0114 |
| 202510 | 186 | 8142 | 2025-09-21 00:00 | 2025-09-21 00:00 | OK | 142 | 6 | -3.886 | 0.0955 | +6.188 | 51.9 | 0.0276 | 364 | 24.2 | +0.0301 |
| 202511 | 180 | 8328 | 2025-10-22 00:00 | 2025-10-22 00:00 | OK | 145 | 7 | -4.882 | 0.0952 | +1.080 | 53.6 | 0.0142 | 366 | 24.4 | +0.0249 |
| 202512 | 186 | 8508 | 2025-11-21 00:00 | 2025-11-21 00:00 | OK | 149 | 11 | -6.529 | 0.0947 | +0.596 | 39.7 | 0.0193 | 376 | 25.1 | +0.0171 |
| 202601 | 186 | 8694 | 2025-12-22 00:00 | 2025-12-22 00:00 | OK | 152 | 10 | -7.659 | 0.0943 | +1.328 | 36.8 | 0.0271 | 384 | 25.6 | +0.0176 |
| 202602 | 168 | 8880 | 2026-01-22 00:00 | 2026-01-22 00:00 | OK | 155 | 11 | -8.225 | 0.0943 | +3.626 | 29.6 | 0.0386 | 390 | 26.0 | +0.0122 |
| 202603 | 186 | 9048 | 2026-02-19 00:00 | 2026-02-19 00:00 | OK | 158 | 1 | -7.661 | 0.0969 | +2.664 | 23.7 | 0.0605 | 402 | 26.8 | -0.0032 |
| 202604 | 180 | 9234 | 2026-03-22 00:00 | 2026-03-22 00:00 | OK | 161 | 5 | -7.323 | 0.0946 | +5.765 | 39.1 | 0.0572 | 412 | 27.5 | +0.0257 |
| 202605 | 186 | 9414 | 2026-04-21 00:00 | 2026-04-21 00:00 | OK | 165 | 2 | -7.029 | 0.0962 | +2.326 | 35.1 | 0.0481 | 420 | 28.0 | +0.0064 |
| 202606 | 180 | 9600 | 2026-05-22 00:00 | 2026-05-22 00:00 | OK | 168 | 0 | -6.907 | 0.0994 | +5.546 | 51.0 | 0.0417 | 426 | 28.4 | +0.0192 |
| 202607 | 186 | 9780 | 2026-06-21 00:00 | 2026-06-21 00:00 | OK | 171 | 7 | -7.350 | 0.0938 | +4.292 | 41.4 | 0.0379 | 432 | 28.8 | +0.0211 |
| 202608 | 180 | 9966 | 2026-07-22 00:00 | 2026-07-22 00:00 | OK | 174 | 2 | -6.673 | 0.0969 | -0.126 | 49.8 | 0.0414 | 438 | 29.2 | +0.0319 |

wall-clock: 20 fits, mean 365 s, min 280 s, max 438 s, total 2.03 h

## T2 · Fold table mE1 (embargo 1 anchors; VERIFIED `results/f10_V2MAIN_mE1_s42.json`; wall-clock per fit on the RTX PRO 4500)
| test month | n_test | n_train | max train label end | cutoff | causal | windows/epoch | best ep | best va | α* | net bps/anchor (train frame) | ES5 | turnover | wall s | s/epoch | test-month IC |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| 202501 | 186 | 6563 | 2024-12-31 20:00 | 2024-12-31 20:00 | OK | 114 | 6 | -3.164 | 0.0971 | +0.402 | 21.9 | 0.0715 | 294 | 19.6 | +0.0122 |
| 202502 | 168 | 6749 | 2025-01-31 20:00 | 2025-01-31 20:00 | OK | 117 | 3 | -3.814 | 0.0974 | +0.075 | 30.7 | 0.0802 | 301 | 20.1 | +0.0183 |
| 202503 | 186 | 6917 | 2025-02-28 20:00 | 2025-02-28 20:00 | OK | 120 | 1 | -3.459 | 0.0989 | +0.070 | 9.4 | 0.0855 | 306 | 20.4 | -0.0064 |
| 202504 | 180 | 7103 | 2025-03-31 20:00 | 2025-03-31 20:00 | OK | 124 | 1 | -3.152 | 0.0989 | +0.013 | 13.4 | 0.0864 | 319 | 21.3 | +0.0356 |
| 202505 | 186 | 7283 | 2025-04-30 20:00 | 2025-04-30 20:00 | OK | 127 | 2 | -4.429 | 0.0983 | +0.225 | 29.0 | 0.0822 | 327 | 21.8 | +0.0346 |
| 202506 | 180 | 7469 | 2025-05-31 20:00 | 2025-05-31 20:00 | OK | 130 | 2 | -3.260 | 0.0981 | -0.220 | 9.7 | 0.0846 | 334 | 22.2 | +0.0022 |
| 202507 | 186 | 7649 | 2025-06-30 20:00 | 2025-06-30 20:00 | OK | 133 | 3 | -5.036 | 0.0973 | +0.751 | 22.1 | 0.0722 | 336 | 22.4 | +0.0311 |
| 202508 | 186 | 7835 | 2025-07-31 20:00 | 2025-07-31 20:00 | OK | 137 | 2 | -3.811 | 0.0968 | -0.519 | 15.0 | 0.0776 | 354 | 23.6 | +0.0112 |
| 202509 | 180 | 8021 | 2025-08-31 20:00 | 2025-08-31 20:00 | OK | 140 | 4 | -3.551 | 0.0955 | +2.620 | 28.5 | 0.0545 | 356 | 23.7 | +0.0188 |
| 202510 | 186 | 8201 | 2025-09-30 20:00 | 2025-09-30 20:00 | OK | 143 | 2 | -3.860 | 0.0977 | +6.357 | 48.2 | 0.0286 | 367 | 24.4 | +0.0297 |
| 202511 | 180 | 8387 | 2025-10-31 20:00 | 2025-10-31 20:00 | OK | 146 | 14 | -5.028 | 0.0948 | +1.080 | 53.6 | 0.0142 | 367 | 24.5 | +0.0186 |
| 202512 | 186 | 8567 | 2025-11-30 20:00 | 2025-11-30 20:00 | OK | 150 | 12 | -7.029 | 0.0943 | +0.597 | 39.7 | 0.0192 | 380 | 25.3 | +0.0192 |
| 202601 | 186 | 8753 | 2025-12-31 20:00 | 2025-12-31 20:00 | OK | 153 | 0 | -7.835 | 0.0991 | +1.317 | 37.0 | 0.0280 | 385 | 25.7 | +0.0256 |
| 202602 | 168 | 8939 | 2026-01-31 20:00 | 2026-01-31 20:00 | OK | 156 | 13 | -7.971 | 0.0941 | +3.651 | 29.6 | 0.0386 | 400 | 26.7 | +0.0127 |
| 202603 | 186 | 9107 | 2026-02-28 20:00 | 2026-02-28 20:00 | OK | 159 | 1 | -7.855 | 0.0972 | +2.801 | 23.4 | 0.0610 | 406 | 27.1 | +0.0179 |
| 202604 | 180 | 9293 | 2026-03-31 20:00 | 2026-03-31 20:00 | OK | 163 | 5 | -7.374 | 0.0951 | +5.976 | 38.5 | 0.0571 | 418 | 27.8 | +0.0292 |
| 202605 | 186 | 9473 | 2026-04-30 20:00 | 2026-04-30 20:00 | OK | 166 | 0 | -6.821 | 0.0980 | +2.363 | 33.4 | 0.0488 | 426 | 28.4 | +0.0027 |
| 202606 | 180 | 9659 | 2026-05-31 20:00 | 2026-05-31 20:00 | OK | 169 | 0 | -6.956 | 0.0994 | +5.405 | 50.5 | 0.0423 | 432 | 28.8 | +0.0239 |
| 202607 | 186 | 9839 | 2026-06-30 20:00 | 2026-06-30 20:00 | OK | 172 | 4 | -6.981 | 0.0951 | +4.293 | 40.3 | 0.0413 | 437 | 29.1 | +0.0340 |
| 202608 | 180 | 10025 | 2026-07-31 20:00 | 2026-07-31 20:00 | OK | 175 | 7 | -6.131 | 0.0941 | -0.113 | 45.2 | 0.0389 | 446 | 29.7 | +0.0428 |

wall-clock: 20 fits, mean 369 s, min 294 s, max 446 s, total 2.05 h

## T3 · Score-level: IC levels, paired ΔIC vs yearly, overlap agreement (VERIFIED `logs/ic_*.json`; ext-grid dlw targets y4s = Π(1+r5)−1; rank IC per anchor over members)
| window / file | n | IC mean | anchor s.e. | share>0 |
|---|---|---|---|---|
| 2025/yearly | 2190 | +0.0224 | 0.0023 | 0.581 |
| 2025/mE60 | 2190 | +0.0151 | 0.0022 | 0.559 |
| 2025/mE1 | 2190 | +0.0188 | 0.0021 | 0.571 |
| 2026<=cut/yearly | 1332 | +0.0126 | 0.0022 | 0.580 |
| 2026<=cut/mE60 | 1332 | +0.0144 | 0.0023 | 0.565 |
| 2026<=cut/mE1 | 1332 | +0.0212 | 0.0024 | 0.592 |
| 2025->26<=cut/yearly | 3522 | +0.0187 | 0.0016 | 0.581 |
| 2025->26<=cut/mE60 | 3522 | +0.0149 | 0.0016 | 0.561 |
| 2025->26<=cut/mE1 | 3522 | +0.0197 | 0.0016 | 0.579 |
| 2026-08-11->30/mE60 | 120 | +0.0377 | 0.0091 | 0.625 |
| 2026-08-11->30/mE1 | 120 | +0.0512 | 0.0083 | 0.717 |

| ΔIC pair (window) | n | Δ mean | anchor s.e. | CI95 day-block | P(Δ>0) |
|---|---|---|---|---|---|
| 2025/mE60 | 2190 | -0.0073 | 0.0018 | [-0.0111, -0.0037] | 0.001 |
| 2025/mE1 | 2190 | -0.0037 | 0.0017 | [-0.0071, -0.0004] | 0.017 |
| 2025/mE1-mE60 | 2190 | +0.0036 | 0.0010 | [+0.0013, +0.0061] | 0.999 |
| 2026<=cut/mE60 | 1332 | +0.0018 | 0.0021 | [-0.0021, +0.0060] | 0.796 |
| 2026<=cut/mE1 | 1332 | +0.0085 | 0.0022 | [+0.0040, +0.0129] | 1.000 |
| 2026<=cut/mE1-mE60 | 1332 | +0.0068 | 0.0017 | [+0.0034, +0.0103] | 1.000 |
| 2025->26<=cut/mE60 | 3522 | -0.0039 | 0.0014 | [-0.0068, -0.0011] | 0.004 |
| 2025->26<=cut/mE1 | 3522 | +0.0009 | 0.0013 | [-0.0018, +0.0039] | 0.749 |
| 2025->26<=cut/mE1-mE60 | 3522 | +0.0048 | 0.0009 | [+0.0028, +0.0068] | 1.000 |
| 2026-08-11->30/mE1-mE60 | 120 | +0.0135 | 0.0051 | [+0.0013, +0.0259] | 0.985 |

| overlap agreement (per-anchor Spearman monthly vs yearly) | n | mean | median | p5 | p95 | min |
|---|---|---|---|---|---|---|
| 2026<=cut/mE60 | 1332 | 0.5339 | 0.5817 | 0.0791 | 0.8782 | -0.0862 |
| 2025/mE60 | 2190 | 0.6650 | 0.7776 | 0.0958 | 0.8689 | -0.2073 |
| 2025->26<=cut/mE60 | 3522 | 0.6154 | 0.7394 | 0.0881 | 0.8727 | -0.2073 |
| 2026<=cut/mE1 | 1332 | 0.4715 | 0.4410 | 0.1108 | 0.8550 | -0.0476 |
| 2025/mE1 | 2190 | 0.6663 | 0.6871 | 0.3421 | 0.8428 | -0.0177 |
| 2025->26<=cut/mE1 | 3522 | 0.5926 | 0.6343 | 0.1883 | 0.8459 | -0.0476 |

| test month | yearly | mE60 | mE1 |
|---|---|---|---|
| 202501 | +0.0197 | +0.0140 | +0.0122 |
| 202502 | +0.0110 | +0.0158 | +0.0183 |
| 202503 | +0.0155 | -0.0077 | -0.0064 |
| 202504 | +0.0398 | +0.0423 | +0.0356 |
| 202505 | +0.0251 | +0.0330 | +0.0346 |
| 202506 | +0.0076 | +0.0054 | +0.0022 |
| 202507 | +0.0357 | -0.0084 | +0.0311 |
| 202508 | +0.0083 | +0.0046 | +0.0112 |
| 202509 | +0.0174 | +0.0114 | +0.0188 |
| 202510 | +0.0287 | +0.0301 | +0.0297 |
| 202511 | +0.0262 | +0.0249 | +0.0186 |
| 202512 | +0.0332 | +0.0171 | +0.0192 |
| 202601 | +0.0150 | +0.0176 | +0.0256 |
| 202602 | +0.0155 | +0.0122 | +0.0127 |
| 202603 | +0.0138 | -0.0032 | +0.0179 |
| 202604 | +0.0098 | +0.0257 | +0.0292 |
| 202605 | +0.0105 | +0.0064 | +0.0027 |
| 202606 | +0.0179 | +0.0192 | +0.0239 |
| 202607 | +0.0073 | +0.0211 | +0.0340 |
| 202608 | +0.0095 | +0.0319 | +0.0428 |

## T4 · IC by model age (each fold model scores its month and the following five; paired on anchors where all six ages exist; VERIFIED `logs/ic_*.json` age_curve)
| variant | n anchors | span | age1 | age2 | age3 | age4 | age5 | age6 | Δ(1−2) | Δ(1−3) | Δ(1−4) | Δ(1−5) | Δ(1−6) [CI95] | age1 == stitched (max abs) |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| mE60 | 2736 | 2025-06-01 00:00 → 2026-08-30 20:00 | +0.0144 | +0.0173 | +0.0207 | +0.0141 | +0.0136 | +0.0140 | -0.0029 | -0.0063 | +0.0003 | +0.0007 | +0.0003 [-0.0032,+0.0039] | 0.0 |
| mE1 | 2736 | 2025-06-01 00:00 → 2026-08-30 20:00 | +0.0214 | +0.0212 | +0.0249 | +0.0192 | +0.0188 | +0.0190 | +0.0002 | -0.0036 | +0.0022 | +0.0026 | +0.0024 [-0.0008,+0.0056] | 0.0 |

## T5 · F10 score-leg return by window (rank-leg on dlw members, bps/anchor per unit gross; VERIFIED `logs/ic_*.json` leg_levels)
| window / file | n | mean bps | Sharpe(anchor) | %/gross/yr |
|---|---|---|---|---|
| 2025/yearly | 2190 | +2.329 | +4.30 | +51.0 |
| 2025/mE60 | 2190 | +1.356 | +2.67 | +29.7 |
| 2025/mE1 | 2190 | +1.528 | +3.14 | +33.5 |
| 2026<=cut/yearly | 1332 | +2.305 | +4.36 | +50.5 |
| 2026<=cut/mE60 | 1332 | +1.266 | +2.54 | +27.7 |
| 2026<=cut/mE1 | 1332 | +1.185 | +2.26 | +25.9 |
| 2025->26<=cut/yearly | 3522 | +2.320 | +4.33 | +50.8 |
| 2025->26<=cut/mE60 | 3522 | +1.322 | +2.62 | +29.0 |
| 2025->26<=cut/mE1 | 3522 | +1.398 | +2.79 | +30.6 |
| 2026-08-11->30/mE60 | 120 | +4.867 | +8.29 | +106.6 |
| 2026-08-11->30/mE1 | 120 | +6.926 | +12.27 | +151.7 |

| Δ leg vs yearly (window/variant) | n | Δ mean | CI95 day-block | P(Δ>0) |
|---|---|---|---|---|
| 2025/mE60 | 2190 | -0.972 | [-1.806, -0.127] | 0.011 |
| 2025/mE1 | 2190 | -0.801 | [-1.645, +0.038] | 0.030 |
| 2026<=cut/mE60 | 1332 | -1.039 | [-2.215, +0.158] | 0.043 |
| 2026<=cut/mE1 | 1332 | -1.120 | [-2.382, +0.182] | 0.049 |
| 2025->26<=cut/mE60 | 3522 | -0.997 | [-1.673, -0.307] | 0.001 |
| 2025->26<=cut/mE1 | 3522 | -0.922 | [-1.617, -0.198] | 0.009 |

## T6 · Leakage gate V3′ on the stitched files (VERIFIED `logs/leakcheck_*.json`)
yearly spectrum on the common window (2025-01-01 → 2026-08-10 20:00Z (full set, stride 1)): k-3:+0.1159 k-2:+0.0360 k-1:-0.2945 k+0:+0.0187 k+1:+0.0022 k+2:-0.0040 k+3:-0.0036
| file | n test anchors | own spectrum k−3..+3 (full) | common-window spectrum | ① future no peak (full / stride) | ② max|Δ| vs yearly (common) | ③ pre-fold finite | verdict |
|---|---|---|---|---|---|---|---|
| mE60 | 3642 | +0.1280 -0.0281 -0.1607 +0.0156 +0.0055 -0.0002 -0.0015 | +0.1236 -0.0250 -0.1571 +0.0149 +0.0047 -0.0005 -0.0018 | OK / OK (max future 0.0055) | 0.1374 FAIL | 0 OK | FAIL |
| mE1 | 3642 | +0.1348 -0.0360 -0.2152 +0.0206 +0.0090 +0.0029 -0.0009 | +0.1308 -0.0341 -0.2110 +0.0197 +0.0079 +0.0024 -0.0014 | OK / OK (max future 0.0090) | 0.0834 FAIL | 0 OK | FAIL |

V3P_GATE_MONTHLY FAIL ['mE60', 'mE1']

## T7 · Replay (device w10_health.py, arm d30_n2_c42, U-PIT · m1 · prod · fee-only · LEGS=101 · LOOK=900 · msharpe · FTRIM zero; n=10038 anchors 2022-01-31 00:00→2026-08-30 20:00; cut 2026-08-10 20:00; VERIFIED `replay/results/judge_dl.json`)
units: g = net_ex/gross_total, bps per anchor per unit gross (primary); net_ex per unit NAV also given; %/gross/yr = mean*2190/100; bootstrap {'blocks': 'UTC day', 'n': 2000, 'seed': 20260905}
| arm | FPRED | PHI | 2025 mean S DD %/yr | 2026≤cut | 2025→26≤cut [CI95] | 2024→26≤cut | gross | w_king | turn/gross | cost/gross | carry/gross | fires |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| BASE | (default f10_V2MAIN_s{FSEED}) | 0.45 | +0.651 S+1.14 DD1133 +14.2% | +3.189 S+4.96 DD435 +69.8% | +1.611 S+2.69 DD1133 +35.3% [+0.712,+2.529] | +1.206 S+2.21 DD1241 +26.4% | 0.607 | 0.608 | 0.07172 | 0.151 | +0.714 | 828 |
| PHI1_BASE | (default f10_V2MAIN_s{FSEED}) | 1.0 | +0.668 S+1.28 DD554 +14.6% | +3.260 S+4.76 DD485 +71.4% | +1.648 S+2.80 DD554 +36.1% [+0.670,+2.520] | +1.274 S+2.40 DD959 +27.9% | 0.609 | 0.608 | 0.10517 | 0.221 | +0.488 | 623 |
| mE60spl | f10_V2MAIN_mE60spl_s42.npy | 0.45 | +0.469 S+0.81 DD1207 +10.3% | +3.011 S+4.68 DD418 +65.9% | +1.431 S+2.37 DD1207 +31.3% [+0.475,+2.367] | +1.095 S+1.99 DD1241 +24.0% | 0.621 | 0.608 | 0.06707 | 0.141 | +0.722 | 832 |
| mE60pure | f10_V2MAIN_mE60_s42.npy | 0.45 | +0.488 S+0.84 DD1207 +10.7% | +3.011 S+4.68 DD418 +65.9% | +1.442 S+2.39 DD1207 +31.6% [+0.521,+2.360] | +0.725 S+1.32 DD1655 +15.9% | 0.620 | 0.608 | 0.06723 | 0.142 | +0.722 | 832 |
| PHI1_mE60spl | f10_V2MAIN_mE60spl_s42.npy | 1.0 | +0.567 S+1.07 DD577 +12.4% | +2.930 S+4.28 DD453 +64.2% | +1.461 S+2.46 DD577 +32.0% [+0.522,+2.412] | +1.158 S+2.17 DD959 +25.4% | 0.620 | 0.608 | 0.10195 | 0.215 | +0.492 | 611 |
| mE1spl | f10_V2MAIN_mE1spl_s42.npy | 0.45 | +0.567 S+0.97 DD1213 +12.4% | +2.986 S+4.63 DD411 +65.4% | +1.482 S+2.44 DD1213 +32.5% [+0.517,+2.396] | +1.127 S+2.04 DD1241 +24.7% | 0.618 | 0.608 | 0.06892 | 0.145 | +0.724 | 826 |
| mE1pure | f10_V2MAIN_mE1_s42.npy | 0.45 | +0.586 S+1.01 DD1213 +12.8% | +2.986 S+4.63 DD411 +65.4% | +1.494 S+2.46 DD1213 +32.7% [+0.559,+2.419] | +0.757 S+1.37 DD1655 +16.6% | 0.618 | 0.608 | 0.06908 | 0.145 | +0.724 | 827 |
| PHI1_mE1spl | f10_V2MAIN_mE1spl_s42.npy | 1.0 | +0.620 S+1.16 DD556 +13.6% | +3.051 S+4.45 DD449 +66.8% | +1.539 S+2.58 DD556 +33.7% [+0.564,+2.440] | +1.207 S+2.26 DD959 +26.4% | 0.615 | 0.608 | 0.10381 | 0.219 | +0.509 | 611 |

| Δ pair | pre-2025 | 2025 | 2026≤cut | **2025→26≤cut** | postcut | ΔSharpe 25on | Δturn% | maxDD ref→x (bps gross) |
|---|---|---|---|---|---|---|---|---|
| mE60spl-BASE (PRIMARY: spliced, identical state entering 2025-01) | +0.0000 [+0.0000,+0.0000] P0.00 (=0) | -0.1812 [-0.4003,+0.0384] P0.05 | -0.1777 [-0.4078,+0.0433] P0.06 | **-0.1799 [-0.3353,-0.0126] P0.02** | -0.0457 [-0.1745,+0.0805] P0.25 | -0.321 | -6.5% | 1133→1207 |
| mE60pure-BASE (sensitivity: NaN before 2025-01) | -0.3363 [-0.5719,-0.1081] P0.00 | -0.1626 [-0.3835,+0.0536] P0.07 | -0.1777 [-0.4031,+0.0371] P0.05 | **-0.1683 [-0.3271,-0.0143] P0.01** | -0.0457 [-0.1772,+0.0762] P0.25 | -0.301 | -6.3% | 1133→1207 |
| PHI1 mE60spl-BASE (F10 book alone, auxiliary) | +0.0000 [+0.0000,+0.0000] P0.00 (=0) | -0.1011 [-0.6556,+0.4448] P0.38 | -0.3301 [-0.7250,+0.0320] P0.04 | **-0.1877 [-0.5631,+0.2049] P0.18** | +0.2099 [-0.1299,+0.5713] P0.87 | -0.333 | -3.1% | 554→577 |
| mE1spl-BASE (PRIMARY: spliced, identical state entering 2025-01) | +0.0000 [+0.0000,+0.0000] P0.00 (=0) | -0.0837 [-0.3062,+0.1504] P0.24 | -0.2029 [-0.4719,+0.0378] P0.06 | **-0.1287 [-0.3071,+0.0403] P0.08** | -0.0354 [-0.1414,+0.0607] P0.25 | -0.247 | -3.9% | 1133→1213 |
| mE1pure-BASE (sensitivity: NaN before 2025-01) | -0.3363 [-0.5683,-0.1091] P0.00 | -0.0648 [-0.3056,+0.1711] P0.28 | -0.2029 [-0.4744,+0.0328] P0.05 | **-0.1170 [-0.2903,+0.0581] P0.10** | -0.0354 [-0.1390,+0.0639] P0.24 | -0.228 | -3.7% | 1133→1213 |
| PHI1 mE1spl-BASE (F10 book alone, auxiliary) | +0.0000 [+0.0000,+0.0000] P0.00 (=0) | -0.0482 [-0.6296,+0.5703] P0.44 | -0.2090 [-0.5545,+0.1407] P0.12 | **-0.1090 [-0.5207,+0.2761] P0.28** | +0.4998 [-0.7255,+2.1640] P0.72 | -0.213 | -1.3% | 554→556 |
| mE1spl-mE60spl (embargo effect at monthly cadence) | +0.0000 [+0.0000,+0.0000] P0.00 (=0) | +0.0976 [-0.0587,+0.2562] P0.89 | -0.0251 [-0.2502,+0.1875] P0.44 | **+0.0512 [-0.0847,+0.1789] P0.78** | +0.0103 [-0.0863,+0.1171] P0.55 | +0.073 | +2.8% | 1207→1213 |

## T8 · Frozen comparison (lead's rule: 'monthly not worse than yearly' ⇔ 2025→26 CI95 upper of Δ(net_ex per gross) > 0 AND ΔIC ≥ 0; no admission decision)
| variant | book Δg 2025→26 [CI95] (spliced, primary) | upper>0 | pure-file sensitivity Δg [CI95] | ΔIC 2025→26 ± s.e. [CI95] | ΔIC≥0 | not worse |
|---|---|---|---|---|---|---|
| mE60 | -0.1799 [-0.3353,-0.0126] | False | -0.1683 [-0.3271,-0.0143] | -0.0039 ± 0.0014 [-0.0068,-0.0011] | False | **False** |
| mE1 | -0.1287 [-0.3071,+0.0403] | True | -0.1170 [-0.2903,+0.0581] | +0.0009 ± 0.0013 [-0.0018,+0.0039] | True | **True** |

## T9 · Commands (verbatim from the command logs)

`/workspace/review_scratch/dl_monthly_wf/logs/commands.txt`:
```
LAUNCH 2026-09-05T07:16:51Z gpu_mem_used=2 MiB other_train_procs=0
CMD[E60] 2026-09-05T07:16:52Z: env ARM=V2MAIN V2=1 SEED=42 F10_DLW=/workspace/dlw_ext F10_OUT=/workspace/f8_ext MWF_OUT=/workspace/review_scratch/dl_monthly_wf EMBARGO=60 /workspace/venv/bin/python /workspace/review_scratch/dl_monthly_wf/pod_f10_train_monthly.py
END[E60] rc=1 2026-09-05T07:17:13Z
TRAIN_FAILED E60 rc=1 2026-09-05T07:17:13Z
LAUNCH 2026-09-05T07:21:56Z gpu_mem_used=2 MiB other_train_procs=0
CMD[E60] 2026-09-05T07:21:56Z: env ARM=V2MAIN V2=1 SEED=42 F10_DLW=/workspace/dlw_ext F10_OUT=/workspace/f8_ext MWF_OUT=/workspace/review_scratch/dl_monthly_wf EMBARGO=60 /workspace/venv/bin/python /workspace/review_scratch/dl_monthly_wf/pod_f10_train_monthly.py
LEAD APPROVAL 2026-09-05T07:25:40Z: E60 and E1 run concurrently (two own processes). Sequential loop run_train.sh (pid 95313) killed with SIGKILL; E60 python pid 95324 continues untouched (started 07:21:56Z).
CMD[E1] 2026-09-05T07:25:40Z: env ARM=V2MAIN V2=1 SEED=42 F10_DLW=/workspace/dlw_ext F10_OUT=/workspace/f8_ext MWF_OUT=/workspace/review_scratch/dl_monthly_wf EMBARGO=1 /workspace/venv/bin/python /workspace/review_scratch/dl_monthly_wf/pod_f10_train_monthly.py
PID[E1] python 95754 (launcher 95748) 2026-09-05T07:25:40Z
NOTE 2026-09-05T07:26:02Z: E60 tail watcher relaunched (pid 95879) with T0 computed from 07:21:56Z (first instance had a wrong hardcoded epoch, killed before writing).
                                                                                                                                                          INCIDENT 2026-09-05T08:19:08Z: /workspace disk quota exceeded ~08:0xZ (lead: another agent, freed 7.4 GB at 08:14:57Z). Both trainers died silently ~08:09:30Z (E60 pid 95324 at fold 202509 ep11, E1 pid 95754 at fold 202509 ep1): log lines stop, no traceback (the log file is on /workspace so the traceback write failed too), launcher END lines lost for the same reason. verify_artifacts.py --fix at 08:18Z: folds 202501..202508 complete and loada
CMD[E60-restart] 2026-09-05T08:19:08Z: env ARM=V2MAIN V2=1 SEED=42 F10_DLW=/workspace/dlw_ext F10_OUT=/workspace/f8_ext MWF_OUT=/workspace/review_scratch/dl_monthly_wf EMBARGO=60 /workspace/venv/bin/python /workspace/review_scratch/dl_monthly_wf/pod_f10_train_monthly.py
CMD[E1-restart] 2026-09-05T08:19:08Z: env ARM=V2MAIN V2=1 SEED=42 F10_DLW=/workspace/dlw_ext F10_OUT=/workspace/f8_ext MWF_OUT=/workspace/review_scratch/dl_monthly_wf EMBARGO=1 /workspace/venv/bin/python /workspace/review_scratch/dl_monthly_wf/pod_f10_train_monthly.py
PID[E60-restart] python 98737 (launcher 98728) 2026-09-05T08:19:08Z
PID[E1-restart] python 98740 (launcher 98729) 2026-09-05T08:19:08Z
DRY-RUN START 2026-09-05T08:19:14Z: full analysis chain on the 8 finished folds (2025-01..08) to test code paths; every output below is overwritten by the final pass
DRY-RUN END 2026-09-05T08:24:20Z
END[E60-restart] python 98737 rc=0 2026-09-05T09:39:18Z wall 4810 s; MWF_TRAIN_DONE lines in log: 1
CMD[replay-check E60 202501] 2026-09-05T09:39:39Z: env ARM=V2MAIN V2=1 SEED=42 F10_DLW=/workspace/dlw_ext F10_OUT=/workspace/f8_ext MWF_OUT=/workspace/review_scratch/dl_monthly_wf/replay_check EMBARGO=60 MONTHS=202501 /workspace/venv/bin/python /workspace/review_scratch/dl_monthly_wf/pod_f10_train_monthly.py
END[E1-restart] python 98740 rc=0 2026-09-05T09:40:10Z wall 4862 s; MWF_TRAIN_DONE lines in log: 1
END[replay-check] rc=0 2026-09-05T09:44:45Z wall 306 s
REPLAY_CHECK 2026-09-05T09:45:01Z: scores: bitwise equal True max|Δ| 0.0 share exactly equal 1.0 n cells 1430611 weights: bitwise equal True max|Δ| 0.0
FINAL START 2026-09-05T09:45:22Z: final analysis pass on 20/20 folds per variant (dry-run outputs overwritten)
VERIFY rc=0 VERIFY OK
STITCH rc=0
IC rc=0
LEAKCHECK rc=3 (3 = gate-literal FAIL, see log)
JUDGE rc=0
```

`/workspace/review_scratch/dl_monthly_wf/replay/logs/commands.txt`:
```
CMD[eq_pinned_log_s42] (cwd=/workspace/review_scratch/dl_monthly_wf/replay/dev) 2026-09-05T07:17:03Z: env LEGS=101 CAL=log SLOW_NPY=/workspace/shadow_bundle_v3/slow_pred_pinned.npy WRULE=msharpe LOOK=900 FSEED=42 MEMBERS_TOPN=829 TRADE_TOPN=400 FTRIM=zero OUT_TAG=eq_pinned_log_s42 /workspace/venv/bin/python ../w10_health.py
CMD[BASE_M1_UPIT_prod_s42_ccal] (cwd=/workspace/review_scratch/dl_monthly_wf/replay/dev_alt) 2026-09-05T07:17:03Z: env LEGS=101 CAL=log SLOW_NPY=/workspace/shadow_bundle_v3/slow_pred_pinned.npy WRULE=msharpe LOOK=900 MEMBERS_TOPN=829 FTRIM=zero PHI=0.45 FSEED=42 UMASK_SCOPE=m1 UMASK_NPZ=/workspace/review_scratch/health_check/masks/umask_UPIT.npz COSTB_JSON=/workspace/review_scratch/health_check/calib/costb_fee_steady.json OUT_TAG=BASE_M1_UPIT_prod_s42_ccal /workspace/venv/bin/python ../w10_health.py
END[BASE_M1_UPIT_prod_s42_ccal] rc=0 2026-09-05T07:17:29Z
END[eq_pinned_log_s42] rc=0 2026-09-05T07:17:33Z
DRY-RUN START 2026-09-05T08:19:14Z: full analysis chain on the 8 finished folds (2025-01..08) to test code paths; every output below is overwritten by the final pass
CMD[M1_mE60pure_prod_s42_ccal] (cwd=/workspace/review_scratch/dl_monthly_wf/replay/dev_alt) 2026-09-05T08:19:18Z: env LEGS=101 CAL=log SLOW_NPY=/workspace/shadow_bundle_v3/slow_pred_pinned.npy WRULE=msharpe LOOK=900 MEMBERS_TOPN=829 FTRIM=zero FSEED=42 UMASK_SCOPE=m1 UMASK_NPZ=/workspace/review_scratch/health_check/masks/umask_UPIT.npz COSTB_JSON=/workspace/review_scratch/health_check/calib/costb_fee_steady.json PHI=0.45 FPRED=f10_V2MAIN_mE60_s42.npy OUT_TAG=M1_mE60pure_prod_s42_ccal /workspace/venv/bin/python ../w10_health.py
CMD[PHI1_mE60spl_prod_s42_ccal] (cwd=/workspace/review_scratch/dl_monthly_wf/replay/dev_alt) 2026-09-05T08:19:18Z: env LEGS=101 CAL=log SLOW_NPY=/workspace/shadow_bundle_v3/slow_pred_pinned.npy WRULE=msharpe LOOK=900 MEMBERS_TOPN=829 FTRIM=zero FSEED=42 UMASK_SCOPE=m1 UMASK_NPZ=/workspace/review_scratch/health_check/masks/umask_UPIT.npz COSTB_JSON=/workspace/review_scratch/health_check/calib/costb_fee_steady.json PHI=1.0 FPRED=f10_V2MAIN_mE60spl_s42.npy OUT_TAG=PHI1_mE60spl_prod_s42_ccal /workspace/venv/bin/python ../w10_health.py
CMD[M1_mE60spl_prod_s42_ccal] (cwd=/workspace/review_scratch/dl_monthly_wf/replay/dev_alt) 2026-09-05T08:19:18Z: env LEGS=101 CAL=log SLOW_NPY=/workspace/shadow_bundle_v3/slow_pred_pinned.npy WRULE=msharpe LOOK=900 MEMBERS_TOPN=829 FTRIM=zero FSEED=42 UMASK_SCOPE=m1 UMASK_NPZ=/workspace/review_scratch/health_check/masks/umask_UPIT.npz COSTB_JSON=/workspace/review_scratch/health_check/calib/costb_fee_steady.json PHI=0.45 FPRED=f10_V2MAIN_mE60spl_s42.npy OUT_TAG=M1_mE60spl_prod_s42_ccal /workspace/venv/bin/python ../w10_health.py
CMD[PHI1_BASE_prod_s42_ccal] (cwd=/workspace/review_scratch/dl_monthly_wf/replay/dev_alt) 2026-09-05T08:19:18Z: env LEGS=101 CAL=log SLOW_NPY=/workspace/shadow_bundle_v3/slow_pred_pinned.npy WRULE=msharpe LOOK=900 MEMBERS_TOPN=829 FTRIM=zero FSEED=42 UMASK_SCOPE=m1 UMASK_NPZ=/workspace/review_scratch/health_check/masks/umask_UPIT.npz COSTB_JSON=/workspace/review_scratch/health_check/calib/costb_fee_steady.json PHI=1.0 OUT_TAG=PHI1_BASE_prod_s42_ccal /workspace/venv/bin/python ../w10_health.py
END[M1_mE60pure_prod_s42_ccal] rc=0 2026-09-05T08:19:44Z
END[PHI1_mE60spl_prod_s42_ccal] rc=0 2026-09-05T08:19:44Z
END[M1_mE60spl_prod_s42_ccal] rc=0 2026-09-05T08:19:44Z
END[PHI1_BASE_prod_s42_ccal] rc=0 2026-09-05T08:19:45Z
CMD[M1_mE1spl_prod_s42_ccal] (cwd=/workspace/review_scratch/dl_monthly_wf/replay/dev_alt) 2026-09-05T08:19:52Z: env LEGS=101 CAL=log SLOW_NPY=/workspace/shadow_bundle_v3/slow_pred_pinned.npy WRULE=msharpe LOOK=900 MEMBERS_TOPN=829 FTRIM=zero FSEED=42 UMASK_SCOPE=m1 UMASK_NPZ=/workspace/review_scratch/health_check/masks/umask_UPIT.npz COSTB_JSON=/workspace/review_scratch/health_check/calib/costb_fee_steady.json PHI=0.45 FPRED=f10_V2MAIN_mE1spl_s42.npy OUT_TAG=M1_mE1spl_prod_s42_ccal /workspace/venv/bin/python ../w10_health.py
CMD[PHI1_mE1spl_prod_s42_ccal] (cwd=/workspace/review_scratch/dl_monthly_wf/replay/dev_alt) 2026-09-05T08:19:52Z: env LEGS=101 CAL=log SLOW_NPY=/workspace/shadow_bundle_v3/slow_pred_pinned.npy WRULE=msharpe LOOK=900 MEMBERS_TOPN=829 FTRIM=zero FSEED=42 UMASK_SCOPE=m1 UMASK_NPZ=/workspace/review_scratch/health_check/masks/umask_UPIT.npz COSTB_JSON=/workspace/review_scratch/health_check/calib/costb_fee_steady.json PHI=1.0 FPRED=f10_V2MAIN_mE1spl_s42.npy OUT_TAG=PHI1_mE1spl_prod_s42_ccal /workspace/venv/bin/python ../w10_health.py
CMD[M1_mE1pure_prod_s42_ccal] (cwd=/workspace/review_scratch/dl_monthly_wf/replay/dev_alt) 2026-09-05T08:19:52Z: env LEGS=101 CAL=log SLOW_NPY=/workspace/shadow_bundle_v3/slow_pred_pinned.npy WRULE=msharpe LOOK=900 MEMBERS_TOPN=829 FTRIM=zero FSEED=42 UMASK_SCOPE=m1 UMASK_NPZ=/workspace/review_scratch/health_check/masks/umask_UPIT.npz COSTB_JSON=/workspace/review_scratch/health_check/calib/costb_fee_steady.json PHI=0.45 FPRED=f10_V2MAIN_mE1_s42.npy OUT_TAG=M1_mE1pure_prod_s42_ccal /workspace/venv/bin/python ../w10_health.py
END[M1_mE1pure_prod_s42_ccal] rc=0 2026-09-05T08:20:16Z
END[PHI1_mE1spl_prod_s42_ccal] rc=0 2026-09-05T08:20:17Z
END[M1_mE1spl_prod_s42_ccal] rc=0 2026-09-05T08:20:17Z
FINAL START 2026-09-05T09:45:22Z: final analysis pass on 20/20 folds per variant (dry-run outputs overwritten)
CMD[M1_mE60pure_prod_s42_ccal] (cwd=/workspace/review_scratch/dl_monthly_wf/replay/dev_alt) 2026-09-05T09:45:35Z: env LEGS=101 CAL=log SLOW_NPY=/workspace/shadow_bundle_v3/slow_pred_pinned.npy WRULE=msharpe LOOK=900 MEMBERS_TOPN=829 FTRIM=zero FSEED=42 UMASK_SCOPE=m1 UMASK_NPZ=/workspace/review_scratch/health_check/masks/umask_UPIT.npz COSTB_JSON=/workspace/review_scratch/health_check/calib/costb_fee_steady.json PHI=0.45 FPRED=f10_V2MAIN_mE60_s42.npy OUT_TAG=M1_mE60pure_prod_s42_ccal /workspace/venv/bin/python ../w10_health.py
CMD[PHI1_BASE_prod_s42_ccal] (cwd=/workspace/review_scratch/dl_monthly_wf/replay/dev_alt) 2026-09-05T09:45:35Z: env LEGS=101 CAL=log SLOW_NPY=/workspace/shadow_bundle_v3/slow_pred_pinned.npy WRULE=msharpe LOOK=900 MEMBERS_TOPN=829 FTRIM=zero FSEED=42 UMASK_SCOPE=m1 UMASK_NPZ=/workspace/review_scratch/health_check/masks/umask_UPIT.npz COSTB_JSON=/workspace/review_scratch/health_check/calib/costb_fee_steady.json PHI=1.0 OUT_TAG=PHI1_BASE_prod_s42_ccal /workspace/venv/bin/python ../w10_health.py
CMD[M1_mE60spl_prod_s42_ccal] (cwd=/workspace/review_scratch/dl_monthly_wf/replay/dev_alt) 2026-09-05T09:45:35Z: env LEGS=101 CAL=log SLOW_NPY=/workspace/shadow_bundle_v3/slow_pred_pinned.npy WRULE=msharpe LOOK=900 MEMBERS_TOPN=829 FTRIM=zero FSEED=42 UMASK_SCOPE=m1 UMASK_NPZ=/workspace/review_scratch/health_check/masks/umask_UPIT.npz COSTB_JSON=/workspace/review_scratch/health_check/calib/costb_fee_steady.json PHI=0.45 FPRED=f10_V2MAIN_mE60spl_s42.npy OUT_TAG=M1_mE60spl_prod_s42_ccal /workspace/venv/bin/python ../w10_health.py
CMD[PHI1_mE60spl_prod_s42_ccal] (cwd=/workspace/review_scratch/dl_monthly_wf/replay/dev_alt) 2026-09-05T09:45:35Z: env LEGS=101 CAL=log SLOW_NPY=/workspace/shadow_bundle_v3/slow_pred_pinned.npy WRULE=msharpe LOOK=900 MEMBERS_TOPN=829 FTRIM=zero FSEED=42 UMASK_SCOPE=m1 UMASK_NPZ=/workspace/review_scratch/health_check/masks/umask_UPIT.npz COSTB_JSON=/workspace/review_scratch/health_check/calib/costb_fee_steady.json PHI=1.0 FPRED=f10_V2MAIN_mE60spl_s42.npy OUT_TAG=PHI1_mE60spl_prod_s42_ccal /workspace/venv/bin/python ../w10_health.py
END[M1_mE60pure_prod_s42_ccal] rc=0 2026-09-05T09:46:02Z
END[PHI1_BASE_prod_s42_ccal] rc=0 2026-09-05T09:46:03Z
END[PHI1_mE60spl_prod_s42_ccal] rc=0 2026-09-05T09:46:03Z
END[M1_mE60spl_prod_s42_ccal] rc=0 2026-09-05T09:46:03Z
CMD[M1_mE1spl_prod_s42_ccal] (cwd=/workspace/review_scratch/dl_monthly_wf/replay/dev_alt) 2026-09-05T09:46:10Z: env LEGS=101 CAL=log SLOW_NPY=/workspace/shadow_bundle_v3/slow_pred_pinned.npy WRULE=msharpe LOOK=900 MEMBERS_TOPN=829 FTRIM=zero FSEED=42 UMASK_SCOPE=m1 UMASK_NPZ=/workspace/review_scratch/health_check/masks/umask_UPIT.npz COSTB_JSON=/workspace/review_scratch/health_check/calib/costb_fee_steady.json PHI=0.45 FPRED=f10_V2MAIN_mE1spl_s42.npy OUT_TAG=M1_mE1spl_prod_s42_ccal /workspace/venv/bin/python ../w10_health.py
CMD[M1_mE1pure_prod_s42_ccal] (cwd=/workspace/review_scratch/dl_monthly_wf/replay/dev_alt) 2026-09-05T09:46:10Z: env LEGS=101 CAL=log SLOW_NPY=/workspace/shadow_bundle_v3/slow_pred_pinned.npy WRULE=msharpe LOOK=900 MEMBERS_TOPN=829 FTRIM=zero FSEED=42 UMASK_SCOPE=m1 UMASK_NPZ=/workspace/review_scratch/health_check/masks/umask_UPIT.npz COSTB_JSON=/workspace/review_scratch/health_check/calib/costb_fee_steady.json PHI=0.45 FPRED=f10_V2MAIN_mE1_s42.npy OUT_TAG=M1_mE1pure_prod_s42_ccal /workspace/venv/bin/python ../w10_health.py
CMD[PHI1_mE1spl_prod_s42_ccal] (cwd=/workspace/review_scratch/dl_monthly_wf/replay/dev_alt) 2026-09-05T09:46:10Z: env LEGS=101 CAL=log SLOW_NPY=/workspace/shadow_bundle_v3/slow_pred_pinned.npy WRULE=msharpe LOOK=900 MEMBERS_TOPN=829 FTRIM=zero FSEED=42 UMASK_SCOPE=m1 UMASK_NPZ=/workspace/review_scratch/health_check/masks/umask_UPIT.npz COSTB_JSON=/workspace/review_scratch/health_check/calib/costb_fee_steady.json PHI=1.0 FPRED=f10_V2MAIN_mE1spl_s42.npy OUT_TAG=PHI1_mE1spl_prod_s42_ccal /workspace/venv/bin/python ../w10_health.py
END[M1_mE1pure_prod_s42_ccal] rc=0 2026-09-05T09:46:35Z
END[PHI1_mE1spl_prod_s42_ccal] rc=0 2026-09-05T09:46:36Z
END[M1_mE1spl_prod_s42_ccal] rc=0 2026-09-05T09:46:36Z
```

`/workspace/review_scratch/dl_monthly_wf/replay/logs/replay_chain.log`:
```
METRICS_mE60 rc=0 2026-09-05T08:19:52Z
cb83330cf6f1808a41389de7a1eca7949f254d31c9a0b331d4618914129ff937  dev_alt/probe_artifacts/w10_ablation_series_M1_mE60spl_prod_s42_ccal.npz
2faa43911b1a1ae6b00694fc5680accb92072dab1995aa7c9ceb8119146be952  dev_alt/probe_artifacts/w10_ablation_series_M1_mE60pure_prod_s42_ccal.npz
e954c1bc1cd18ca6fd264cfe296ac9958e6d7cd0d94881e234e89edfe460529b  dev_alt/probe_artifacts/w10_ablation_series_PHI1_mE60spl_prod_s42_ccal.npz
bfc27a250f81d1a6bfa2057ef194530a03d2d9a6a87aeea02a4bf5a93d2b982a  dev_alt/probe_artifacts/w10_ablation_series_PHI1_BASE_prod_s42_ccal.npz
32bfecb9cf9c0e5caebd4d77ad3ee5cf8334be3e75bf04b2cd66cb8550d9d12a  dev_alt/probe_artifacts/w10_ablation_series_BASE_M1_UPIT_prod_s42_ccal.npz
REPLAY_mE60_DONE 2026-09-05T08:19:52Z
METRICS_mE1 rc=0 2026-09-05T08:20:21Z
5d52e04915683bb6728588b20ca11205475942c1b0d01ec29014a6841d6c5cc4  dev_alt/probe_artifacts/w10_ablation_series_M1_mE1spl_prod_s42_ccal.npz
e58f2f1c9cbae601388a288964f0fb81876634864ff36dd9acad57316f03b5ef  dev_alt/probe_artifacts/w10_ablation_series_M1_mE1pure_prod_s42_ccal.npz
af7a53b3fa1e6c915c9b802476536876268d3d4914165ef3771619880ab16864  dev_alt/probe_artifacts/w10_ablation_series_PHI1_mE1spl_prod_s42_ccal.npz
REPLAY_mE1_DONE 2026-09-05T08:20:21Z
METRICS_mE60 rc=0 2026-09-05T09:46:10Z
7037b8ab81833c204181e1bcf70f0530ab37684fb3fd1146de510e9b512f6ffe  dev_alt/probe_artifacts/w10_ablation_series_M1_mE60spl_prod_s42_ccal.npz
5e433f7bdd664dd1758cccbe470559821cd2c63c1f2147d2c25346bc08a032b2  dev_alt/probe_artifacts/w10_ablation_series_M1_mE60pure_prod_s42_ccal.npz
529c1ec9b3f074048d172fa57d8d8e43ad6a6ccad75499bbf1a4d58e642192ca  dev_alt/probe_artifacts/w10_ablation_series_PHI1_mE60spl_prod_s42_ccal.npz
bfc27a250f81d1a6bfa2057ef194530a03d2d9a6a87aeea02a4bf5a93d2b982a  dev_alt/probe_artifacts/w10_ablation_series_PHI1_BASE_prod_s42_ccal.npz
32bfecb9cf9c0e5caebd4d77ad3ee5cf8334be3e75bf04b2cd66cb8550d9d12a  dev_alt/probe_artifacts/w10_ablation_series_BASE_M1_UPIT_prod_s42_ccal.npz
REPLAY_mE60_DONE 2026-09-05T09:46:10Z
METRICS_mE1 rc=0 2026-09-05T09:46:40Z
ef4d5265fbde60461c8b523a3e7384d54c8c5dae9cf12b207cdcecd3ab6d21de  dev_alt/probe_artifacts/w10_ablation_series_M1_mE1spl_prod_s42_ccal.npz
44ae27bb684eb793c79c4c64999b01302f8027129f0dbc25ae7ca9d14daa3b75  dev_alt/probe_artifacts/w10_ablation_series_M1_mE1pure_prod_s42_ccal.npz
c8e16f2e984be425f7bcc4c0a4cb874df5ba27126c2dc6472a90c5c758806090  dev_alt/probe_artifacts/w10_ablation_series_PHI1_mE1spl_prod_s42_ccal.npz
REPLAY_mE1_DONE 2026-09-05T09:46:40Z
```

`/workspace/review_scratch/dl_monthly_wf/replay/logs/eq_chain.log`:
```
EQ1 rc=0
EQ2 rc=0
EQ_CHAIN_DONE 2026-09-05T07:17:36Z
```
