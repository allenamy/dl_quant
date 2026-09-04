
### Canon form (MEMBERS_TOPN=0, TRADE_TOPN=0, FTRIM=off), FSEED=42: CAL=log vs CAL=simple

| year | log mean | simple mean | log Sharpe | simple Sharpe | log worst mo | simple worst mo | log maxDD | simple maxDD | log w3_king | simple w3_king | log turnover | simple turnover | n |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| 2024 | +0.255 | +0.322 | 0.86 | 1.06 | -380 (2024-04) | -372 (2024-07) | 719 | 694 | 0.629 | 0.420 | 0.0367 | 0.0271 | 2196 |
| 2025 | +0.436 | +0.843 | 1.25 | 2.41 | -367 (2025-12) | -404 (2025-04) | 503 | 671 | 0.692 | 0.460 | 0.0329 | 0.0234 | 2190 |
| 2026 | +1.893 | +3.132 | 3.64 | 6.10 | -280 (2026-08) | +10 (2026-08) | 727 | 682 | 0.368 | 0.053 | 0.0188 | 0.0099 | 1452 |
| 2026<=08-10 | +2.373 | +3.629 | 4.61 | 7.14 | +34 (2026-02) | +161 (2026-01) | 395 | 258 | 0.374 | 0.058 | 0.0190 | 0.0097 | 1332 |
| 2024on | +0.730 | +1.216 | 1.91 | 3.18 | -380 (2024-04) | -404 (2025-04) | 727 | 694 | 0.588 | 0.344 | 0.0308 | 0.0214 | 5838 |

### Live form (MEMBERS_TOPN=829, TRADE_TOPN=400, FTRIM=zero), FSEED=42: CAL=log vs CAL=simple

| year | log mean | simple mean | log Sharpe | simple Sharpe | log worst mo | simple worst mo | log maxDD | simple maxDD | log w3_king | simple w3_king | log turnover | simple turnover | n |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| 2024 | +0.149 | +0.220 | 0.53 | 0.75 | -363 (2024-04) | -343 (2024-07) | 795 | 586 | 0.639 | 0.436 | 0.0375 | 0.0282 | 2196 |
| 2025 | +0.359 | +1.223 | 1.15 | 3.37 | -294 (2025-12) | -370 (2025-04) | 418 | 647 | 0.673 | 0.475 | 0.0357 | 0.0268 | 2190 |
| 2026 | +2.013 | +4.247 | 3.84 | 7.63 | -294 (2026-08) | +85 (2026-08) | 771 | 689 | 0.361 | 0.052 | 0.0236 | 0.0138 | 1452 |
| 2026<=08-10 | +2.512 | +4.823 | 4.83 | 8.70 | +104 (2026-02) | +343 (2026-08) | 452 | 252 | 0.368 | 0.057 | 0.0238 | 0.0136 | 1332 |
| 2024on | +0.691 | +1.597 | 1.88 | 4.00 | -363 (2024-04) | -370 (2025-04) | 795 | 689 | 0.583 | 0.355 | 0.0334 | 0.0241 | 5838 |

### T3c (KMOD_F10=0.5) vs base, live form, CAL=log, FSEED=42

| year | base mean | arm mean | Δ mean | base Sharpe | arm Sharpe | Δ Sharpe | base w3_king | arm w3_king | base turnover | arm turnover | base maxDD | arm maxDD |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| 2024 | +0.149 | +0.109 | -0.040 | 0.53 | 0.38 | -0.15 | 0.639 | 0.639 | 0.0375 | 0.0383 | 795 | 881 |
| 2025 | +0.359 | +0.328 | -0.031 | 1.15 | 1.05 | -0.10 | 0.673 | 0.673 | 0.0357 | 0.0357 | 418 | 457 |
| 2026 | +2.013 | +1.989 | -0.024 | 3.84 | 3.86 | +0.02 | 0.361 | 0.361 | 0.0236 | 0.0240 | 771 | 779 |
| 2026<=08-10 | +2.512 | +2.505 | -0.007 | 4.83 | 4.93 | +0.10 | 0.368 | 0.368 | 0.0238 | 0.0243 | 452 | 454 |
| 2024on | +0.691 | +0.659 | -0.033 | 1.88 | 1.80 | -0.08 | 0.583 | 0.583 | 0.0334 | 0.0337 | 795 | 881 |

### T3c (KMOD_F10=0.5) vs base, live form, CAL=log, FSEED=2027

| year | base mean | arm mean | Δ mean | base Sharpe | arm Sharpe | Δ Sharpe | base w3_king | arm w3_king | base turnover | arm turnover | base maxDD | arm maxDD |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| 2024 | +0.217 | +0.178 | -0.039 | 0.78 | 0.63 | -0.15 | 0.639 | 0.639 | 0.0369 | 0.0375 | 740 | 816 |
| 2025 | +0.438 | +0.411 | -0.027 | 1.36 | 1.28 | -0.07 | 0.673 | 0.673 | 0.0336 | 0.0335 | 430 | 476 |
| 2026 | +1.994 | +2.006 | +0.013 | 3.80 | 3.88 | +0.08 | 0.361 | 0.361 | 0.0247 | 0.0252 | 757 | 763 |
| 2026<=08-10 | +2.486 | +2.519 | +0.033 | 4.78 | 4.94 | +0.15 | 0.368 | 0.368 | 0.0250 | 0.0255 | 460 | 479 |
| 2024on | +0.742 | +0.720 | -0.022 | 2.01 | 1.96 | -0.05 | 0.583 | 0.583 | 0.0326 | 0.0329 | 757 | 816 |

### Additional per-year means (all runs; d30_n2_c42; executor caliber columns)

| run | year | pnl_ex | carry_ex | cost_ex | net_ex | netlong | nsel | gross_total | fires | w3_fund |
|---|---|---|---|---|---|---|---|---|---|---|
| pod_canon_callog_s42 | 2024 | +0.574 | +0.238 | 0.081 | +0.255 | -0.0277 | 270 | 0.621 | 362 | 0.371 |
| pod_canon_callog_s42 | 2025 | +1.339 | +0.808 | 0.094 | +0.436 | +0.0008 | 372 | 0.593 | 679 | 0.308 |
| pod_canon_callog_s42 | 2026 | +3.976 | +2.008 | 0.075 | +1.893 | -0.0151 | 318 | 0.865 | 713 | 0.632 |
| pod_canon_calsimple_s42 | 2024 | +0.649 | +0.265 | 0.062 | +0.322 | -0.0172 | 270 | 0.648 | 441 | 0.580 |
| pod_canon_calsimple_s42 | 2025 | +1.646 | +0.736 | 0.067 | +0.843 | -0.0344 | 372 | 0.606 | 735 | 0.540 |
| pod_canon_calsimple_s42 | 2026 | +4.784 | +1.609 | 0.044 | +3.132 | -0.0308 | 318 | 0.740 | 729 | 0.947 |
| pod_live_callog_s42 | 2024 | +0.398 | +0.167 | 0.083 | +0.149 | -0.0028 | 272 | 0.602 | 358 | 0.361 |
| pod_live_callog_s42 | 2025 | +0.910 | +0.447 | 0.104 | +0.359 | -0.0407 | 375 | 0.531 | 584 | 0.327 |
| pod_live_callog_s42 | 2026 | +3.020 | +0.916 | 0.090 | +2.013 | -0.0605 | 324 | 0.779 | 453 | 0.639 |
| pod_live_calsimple_s42 | 2024 | +0.479 | +0.195 | 0.065 | +0.220 | -0.0025 | 272 | 0.636 | 444 | 0.564 |
| pod_live_calsimple_s42 | 2025 | +1.750 | +0.450 | 0.078 | +1.223 | -0.0614 | 375 | 0.549 | 661 | 0.525 |
| pod_live_calsimple_s42 | 2026 | +5.146 | +0.842 | 0.057 | +4.247 | -0.0679 | 324 | 0.689 | 467 | 0.948 |
| pod_live_t3c_callog_s42 | 2024 | +0.367 | +0.171 | 0.087 | +0.109 | +0.0185 | 272 | 0.614 | 365 | 0.361 |
| pod_live_t3c_callog_s42 | 2025 | +0.895 | +0.463 | 0.104 | +0.328 | +0.0074 | 375 | 0.542 | 593 | 0.327 |
| pod_live_t3c_callog_s42 | 2026 | +3.024 | +0.944 | 0.091 | +1.989 | -0.0311 | 324 | 0.781 | 459 | 0.639 |
| pod_live_t3c_callog_s2027 | 2024 | +0.433 | +0.171 | 0.084 | +0.178 | +0.0186 | 272 | 0.612 | 371 | 0.361 |
| pod_live_t3c_callog_s2027 | 2025 | +0.987 | +0.477 | 0.099 | +0.411 | +0.0061 | 375 | 0.556 | 641 | 0.327 |
| pod_live_t3c_callog_s2027 | 2026 | +3.050 | +0.949 | 0.095 | +2.006 | -0.0268 | 324 | 0.786 | 462 | 0.639 |
| pod_live_callog_s2027 | 2024 | +0.465 | +0.167 | 0.081 | +0.217 | -0.0043 | 272 | 0.602 | 374 | 0.361 |
| pod_live_callog_s2027 | 2025 | +0.994 | +0.460 | 0.097 | +0.438 | -0.0455 | 375 | 0.549 | 610 | 0.327 |
| pod_live_callog_s2027 | 2026 | +3.007 | +0.920 | 0.094 | +1.994 | -0.0574 | 324 | 0.782 | 459 | 0.639 |

### config_json as stored in each npz

- `pod_canon_callog_s42`: `{"KMOD_F10": 0.0, "KMOD_L": 0.5, "KMOD_AGREE": 0.0, "SEATF10": 0, "KTAIL": 0, "KMOD": 0.0, "SEATNET": 0, "FUNDSCALE": 0, "FEMAT_NPZ": null, "SLOW_NPY": "/workspace/shadow_bundle_v3/slow_pred_pinned.npy", "W3FIX": null, "MEMBERS_TOPN": 0, "TRADE_TOPN": 0, "FTRIM": "off", "UMASK_NPZ": null, "LOOK": 900, "WRULE": "msharpe", "CAL": "log", "LEGS": "101", "PHI": 0.45, "FSEED": "42", "FPRED": "(default f10_V2MAIN_s{FSEED})"}`
- `pod_canon_calsimple_s42`: `{"KMOD_F10": 0.0, "KMOD_L": 0.5, "KMOD_AGREE": 0.0, "SEATF10": 0, "KTAIL": 0, "KMOD": 0.0, "SEATNET": 0, "FUNDSCALE": 0, "FEMAT_NPZ": null, "SLOW_NPY": "/workspace/shadow_bundle_v3/slow_pred_pinned.npy", "W3FIX": null, "MEMBERS_TOPN": 0, "TRADE_TOPN": 0, "FTRIM": "off", "UMASK_NPZ": null, "LOOK": 900, "WRULE": "msharpe", "CAL": "simple", "LEGS": "101", "PHI": 0.45, "FSEED": "42", "FPRED": "(default f10_V2MAIN_s{FSEED})"}`
- `pod_live_callog_s42`: `{"KMOD_F10": 0.0, "KMOD_L": 0.5, "KMOD_AGREE": 0.0, "SEATF10": 0, "KTAIL": 0, "KMOD": 0.0, "SEATNET": 0, "FUNDSCALE": 0, "FEMAT_NPZ": null, "SLOW_NPY": "/workspace/shadow_bundle_v3/slow_pred_pinned.npy", "W3FIX": null, "MEMBERS_TOPN": 829, "TRADE_TOPN": 400, "FTRIM": "zero", "UMASK_NPZ": null, "LOOK": 900, "WRULE": "msharpe", "CAL": "log", "LEGS": "101", "PHI": 0.45, "FSEED": "42", "FPRED": "(default f10_V2MAIN_s{FSEED})"}`
- `pod_live_calsimple_s42`: `{"KMOD_F10": 0.0, "KMOD_L": 0.5, "KMOD_AGREE": 0.0, "SEATF10": 0, "KTAIL": 0, "KMOD": 0.0, "SEATNET": 0, "FUNDSCALE": 0, "FEMAT_NPZ": null, "SLOW_NPY": "/workspace/shadow_bundle_v3/slow_pred_pinned.npy", "W3FIX": null, "MEMBERS_TOPN": 829, "TRADE_TOPN": 400, "FTRIM": "zero", "UMASK_NPZ": null, "LOOK": 900, "WRULE": "msharpe", "CAL": "simple", "LEGS": "101", "PHI": 0.45, "FSEED": "42", "FPRED": "(default f10_V2MAIN_s{FSEED})"}`
- `pod_live_t3c_callog_s42`: `{"KMOD_F10": 0.5, "KMOD_L": 0.5, "KMOD_AGREE": 0.0, "SEATF10": 0, "KTAIL": 0, "KMOD": 0.0, "SEATNET": 0, "FUNDSCALE": 0, "FEMAT_NPZ": null, "SLOW_NPY": "/workspace/shadow_bundle_v3/slow_pred_pinned.npy", "W3FIX": null, "MEMBERS_TOPN": 829, "TRADE_TOPN": 400, "FTRIM": "zero", "UMASK_NPZ": null, "LOOK": 900, "WRULE": "msharpe", "CAL": "log", "LEGS": "101", "PHI": 0.45, "FSEED": "42", "FPRED": "(default f10_V2MAIN_s{FSEED})"}`
- `pod_live_t3c_callog_s2027`: `{"KMOD_F10": 0.5, "KMOD_L": 0.5, "KMOD_AGREE": 0.0, "SEATF10": 0, "KTAIL": 0, "KMOD": 0.0, "SEATNET": 0, "FUNDSCALE": 0, "FEMAT_NPZ": null, "SLOW_NPY": "/workspace/shadow_bundle_v3/slow_pred_pinned.npy", "W3FIX": null, "MEMBERS_TOPN": 829, "TRADE_TOPN": 400, "FTRIM": "zero", "UMASK_NPZ": null, "LOOK": 900, "WRULE": "msharpe", "CAL": "log", "LEGS": "101", "PHI": 0.45, "FSEED": "2027", "FPRED": "(default f10_V2MAIN_s{FSEED})"}`
- `pod_live_callog_s2027`: `{"KMOD_F10": 0.0, "KMOD_L": 0.5, "KMOD_AGREE": 0.0, "SEATF10": 0, "KTAIL": 0, "KMOD": 0.0, "SEATNET": 0, "FUNDSCALE": 0, "FEMAT_NPZ": null, "SLOW_NPY": "/workspace/shadow_bundle_v3/slow_pred_pinned.npy", "W3FIX": null, "MEMBERS_TOPN": 829, "TRADE_TOPN": 400, "FTRIM": "zero", "UMASK_NPZ": null, "LOOK": 900, "WRULE": "msharpe", "CAL": "log", "LEGS": "101", "PHI": 0.45, "FSEED": "2027", "FPRED": "(default f10_V2MAIN_s{FSEED})"}`

### Series coverage

- `pod_canon_callog_s42`: d30_n2_c42 anchors 10038 (2022-01-31 00:00 → 2026-08-30 20:00), S0 anchors 10038, W shape [10038, 829]
- `pod_canon_calsimple_s42`: d30_n2_c42 anchors 10038 (2022-01-31 00:00 → 2026-08-30 20:00), S0 anchors 10038, W shape [10038, 829]
- `pod_live_callog_s42`: d30_n2_c42 anchors 10038 (2022-01-31 00:00 → 2026-08-30 20:00), S0 anchors 10038, W shape [10038, 829]
- `pod_live_calsimple_s42`: d30_n2_c42 anchors 10038 (2022-01-31 00:00 → 2026-08-30 20:00), S0 anchors 10038, W shape [10038, 829]
- `pod_live_t3c_callog_s42`: d30_n2_c42 anchors 10038 (2022-01-31 00:00 → 2026-08-30 20:00), S0 anchors 10038, W shape [10038, 829]
- `pod_live_t3c_callog_s2027`: d30_n2_c42 anchors 10038 (2022-01-31 00:00 → 2026-08-30 20:00), S0 anchors 10038, W shape [10038, 829]
- `pod_live_callog_s2027`: d30_n2_c42 anchors 10038 (2022-01-31 00:00 → 2026-08-30 20:00), S0 anchors 10038, W shape [10038, 829]
