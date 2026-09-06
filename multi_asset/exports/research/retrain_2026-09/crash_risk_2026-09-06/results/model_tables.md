| target · seed | fold | n_train / n_test (events) | AUC | base rate | top-10% rate (lift) | S-b d bps [CI95] | cohort mean bps | top5 gain |
|---|---|---|---|---|---|---|---|---|
| T1 s42 | 2024 | 142806 / 155369 (657) | 0.7890 | 0.0042 | 0.0097 (2.301) | -4.2 [-9.1, +0.5] | +2.9 | age_anchors, coh_mean_du7, n_big_4h, r1d, bars_since_hi7 |
| T1 s42 | 2025 | 298175 / 215087 (1613) | 0.8442 | 0.0075 | 0.0363 (4.842) | -0.7 [-10.9, +9.7] | -1.1 | n_big_4h_r, n_rn8_ge15, coh_mean_du7, r1h_over_r4h, range_ratio |
| T1 s42 | 2026 | 513262 / 103129 (1301) | 0.8641 | 0.0126 | 0.0685 (5.429) | +8.4 [-7.8, +25.4] | +7.8 | coh_mean_rate_over_cap, n_big_4h, min_ret5_4h, coh_mean_du7, n_big_4h_r |
| T1 s2027 | 2024 | 142806 / 155369 (657) | 0.8041 | 0.0042 | 0.0100 (2.358) | -3.2 [-8.2, +1.5] | +2.9 | coh_mean_rate_over_cap, coh_mean_du7, n_big_4h, n_consec_at_cap_r, up_share_3d |
| T1 s2027 | 2025 | 298175 / 215087 (1613) | 0.8391 | 0.0075 | 0.0370 (4.937) | -2.1 [-12.3, +8.2] | -1.1 | coh_mean_du7, n_rn8_ge15, coh_mean_rate_over_cap, accel, age_anchors |
| T1 s2027 | 2026 | 513262 / 103129 (1301) | 0.8629 | 0.0126 | 0.0690 (5.472) | +15.0 [-0.2, +31.7] | +7.8 | coh_mean_du7, n_big_4h_r, coh_mean_rate_over_cap, min_ret5_4h, n_big_4h |
| T3 s42 | 2024 | 142657 / 155367 (711) | 0.7656 | 0.0046 | 0.0117 (2.549) | -3.0 [-8.4, +2.3] | +2.9 | coh_mean_du7, rn8_r, up_share_3d_r, n_big_4h, up_share_3d |
| T3 s42 | 2025 | 297949 / 215087 (2085) | 0.8173 | 0.0097 | 0.0441 (4.552) | +2.2 [-8.0, +13.2] | -1.1 | coh_mean_du7, n_big_4h_r, coh_mean_rate_over_cap, r1h_over_r4h, ema_gap |
| T3 s42 | 2026 | 513060 / 103129 (1578) | 0.8356 | 0.0153 | 0.0780 (5.098) | +6.6 [-9.2, +23.1] | +7.8 | min_ret5_4h, coh_mean_du7, coh_mean_rate_over_cap, n_big_4h_r, n_big_4h |
| T3 s2027 | 2024 | 142657 / 155367 (711) | 0.7694 | 0.0046 | 0.0113 (2.47) | -3.4 [-8.7, +1.8] | +2.9 | coh_mean_rate_over_cap, n_big_4h, accel, r3d, up_share_3d |
| T3 s2027 | 2025 | 297949 / 215087 (2085) | 0.8218 | 0.0097 | 0.0447 (4.607) | -0.5 [-10.2, +9.9] | -1.1 | coh_mean_rate_over_cap, coh_mean_du7, r1h, rn8_r, r1d |
| T3 s2027 | 2026 | 513060 / 103129 (1578) | 0.8369 | 0.0153 | 0.0780 (5.098) | +7.0 [-8.8, +24.6] | +7.8 | n_big_4h_r, min_ret5_4h, coh_mean_du7, coh_mean_rate_over_cap, n_big_4h |

| T2 seed | fold | pinball model / const q05 | coverage model / const | bottom-10% predicted-quantile d bps [CI] | bottom-10% T1 rate / base |
|---|---|---|---|---|---|
| s42 | 2024 | 0.002895 / 0.003046 | 0.096 / 0.063 | -2.8 [-8.7, +3.1] | 0.0105 / 0.0042 |
| s42 | 2025 | 0.003454 / 0.003901 | 0.094 / 0.075 | +1.1 [-10.0, +12.4] | 0.0417 / 0.0075 |
| s42 | 2026 | 0.003726 / 0.004719 | 0.067 / 0.075 | +8.0 [-8.8, +25.6] | 0.0765 / 0.0126 |
| s2027 | 2024 | 0.002917 / 0.003046 | 0.096 / 0.063 | -2.2 [-7.9, +3.5] | 0.0099 / 0.0042 |
| s2027 | 2025 | 0.003478 / 0.003901 | 0.095 / 0.075 | +0.4 [-10.8, +11.4] | 0.0420 / 0.0075 |
| s2027 | 2026 | 0.003730 / 0.004719 | 0.067 / 0.075 | +6.8 [-9.4, +24.1] | 0.0760 / 0.0126 |

reading: {"s42": {"S_a": true, "S_b": false, "S_b_folds_ok": 0, "S_b_2026_ok": false}, "s2027": {"S_a": true, "S_b": false, "S_b_folds_ok": 0, "S_b_2026_ok": false}, "PASS": false, "verdict": "FAIL"}
shift spectrum (T1 s42, AUC by window shift j): {"-2": 0.8367, "-1": 0.8363, "0": 0.8324, "1": 0.8142, "2": 0.8155, "3": 0.8144} peak -2
shuffle-future null (T1 s42): {"2024": {"auc_shuffled_labels": 0.6761, "lift_shuffled": 1.015, "auc_true": 0.789}, "2025": {"auc_shuffled_labels": 0.5425, "lift_shuffled": 1.255, "auc_true": 0.8442}, "2026": {"auc_shuffled_labels": 0.4786, "lift_shuffled": 0.965, "auc_true": 0.8641}}
