> **创建:** 2026-09-05T04:50:49Z | **Session:** b9646a9e (calib teammate, read-only on `~/dl_quant_live` and `~/wide_shadow`) | **状态:** calibration receipts, no ruling | **作废条件:** any log re-write, executor pricing/top-up change, or a tier rule different from the producer's `qv4h` | **方法:** `docs/PREREG_live_form_health_check_2026-09-05.md` §1 (frozen)

# Live execution cost and fill calibration — combo go-live 08-26 04Z → 09-05 00Z

All numbers below are printed by scripts in this directory (receipts in §12). Units: notional in USDT one-sided; bps = 1/10000 of the notional named in each table; per-anchor rates are means over anchors unless a row says pooled. Labels: VERIFIED = read from the logs with an exact cross-check; INFERRED = a sample or a model assumption is involved.

## 0. Bottom line (steady-state anchors, n = 51)

| quantity | value | label |
|---|---|---|
| maker fee / taker fee (bps of traded notional) | 1.800 / 4.500 | VERIFIED (= venue schedule with BNB discount; fee_paid = BNB × px on 6908/6908 rows) |
| maker share of filled notional | 0.913 (anchor-mean CI95 [+0.894, +0.930]) | VERIFIED |
| maker fill ratio buy / sell / all | 0.853 / 0.843 / 0.848 | VERIFIED |
| fill ratio after top-ups buy / sell / all | 0.939 / 0.920 / 0.929 | VERIFIED |
| −5022 first refusal (share of maker legs sent) | 0.255 pooled; anchor-mean CI95 [+0.236, +0.275] | VERIFIED |
| −5022 refused twice → taker top-up | 0.057 pooled | VERIFIED |
| turnover per anchor (filled / venue gross) | mean 0.0477, median 0.0420, notional-weighted 0.0455 | VERIFIED |
| fee cost per unit of turnover (fee only) | 2.035 bps | VERIFIED |
| replay vector emitted (fee + slippage vs anchor mid), maker_bps / taker_bps / maker_share by tier | (-2.41, 16.79, 0.851) / (-2.44, 16.79, 0.925) / (-1.93, 16.79, 0.921); book cost per unit turnover -0.47 bps | VERIFIED inputs (§8b) |
| fee drag per anchor / per year | 0.0926 bps of gross per anchor = 2.03% of gross per year = 4.06% of NAV per year at 2× | VERIFIED arithmetic (2190 anchors/yr) |
| +60 s markout, maker (notional-weighted) | -6.20 bps on 309 marks = 5.1% of notional; CI95 [-13.71, +1.33]; delay-reweighted -6.73 | INFERRED (non-random 5% subset) |
| paper target vs real, twin + funding (bps of gross per anchor) | +0.26, CI95 [-8.50, +8.91], n = 53 | VERIFIED (canon_reconcile.py reused verbatim) |
| paper (venue-aligned) minus twin = execution discount band | -1.23 bps per anchor, CI95 [-6.10, +3.72] | VERIFIED, wide |

The two calibration products the replay can consume are in §8: the fee-only vector per tier (VERIFIED) and the fee-minus-markout vector (INFERRED, thin and biased coverage). The paper-vs-real band in §9 is the execution discount the prereg asks to carry alongside, not a per-trade cost.

## 1. Anchors and sets

| set | n | first | last | rule |
|---|---|---|---|---|
| all live rows in the window | 59 | 08-26 00Z | 09-05 00Z | anchors.jsonl 08-26 → 09-05 |
| in calibration (`all_calib`) | 57 | 08-26 04Z | 09-05 00Z | combo producer (from 08-26 04Z), not halted, venue gross ≥ 1000 |
| steady (`primary_steady`) | 51 | 08-26 04Z | 09-05 00Z | in calibration minus step-up anchors (excluded from the STEADY subset only: realized_gross moved >15% vs previous traded anchor, or rebuilt from a flat book) |
| pre-deposit steady | 43 | 08-26 04Z | 09-03 12Z | steady, before the 09-03 16Z deposit build |
| post-deposit steady | 8 | 09-03 20Z | 09-05 00Z | steady, gross ≈ 163k |

Excluded from steady (VERIFIED from anchors.jsonl):

| anchor | why |
|---|---|
| 08-26 00Z | pre-combo (producer shadow_loop_v3) |
| 08-26 12Z | step-up anchor (|Δgross|>15% or rebuild from flat) |
| 08-26 16Z | halted / flat book |
| 08-26 20Z | step-up anchor (|Δgross|>15% or rebuild from flat) |
| 08-27 00Z | step-up anchor (|Δgross|>15% or rebuild from flat) |
| 08-27 04Z | step-up anchor (|Δgross|>15% or rebuild from flat) |
| 08-27 12Z | step-up anchor (|Δgross|>15% or rebuild from flat) |
| 09-03 16Z | step-up anchor (|Δgross|>15% or rebuild from flat) |

Row semantics used throughout (VERIFIED from `live/binance_executor.py` and the per-(anchor, symbol) row patterns): one leg = one (anchor, symbol). A −5022 first refusal is an attempt-1 maker reject row; the single maker requote, if it rests, is logged as a second attempt-1 maker row for the same leg; if refused again it is an attempt-2 maker reject row and the residual goes to the taker top-up (`from_reject`). Counts: 9798 unique fills (from 10198 rows, 400 superseded by a backfilled +60 s mark), 15630 legs, 2032 first refusals, 1506 requotes rested, 526 refused twice. Fee identities: fee_paid = commission_BNB × BNB mid on 6908/6908 fee rows (max rel diff 0); Σ fills commission = order fee_conversion qty on 6908/6908; |order filled_notional| = Σ fills on 6908/6908 (max rel diff 4e-16). The 08-26 12:49Z protective flatten (334 taker rows, 29502 USDT) has no fills rows and no fee record; it is outside every table below.

## 2. Liquidity tiers (VERIFIED)

| item | value |
|---|---|
| rule | qv4h >= 5e6 USDT → tier 0; 1e6 <= qv4h < 5e6 → tier 1; qv4h < 1e6 → tier 2 |
| qv4h | expm1(clip(mean over trailing 2016 5m bars of log1p(5m quote volume), 0, 30)) * 48, computed at the nominal anchor row of ~/wide_shadow/state/rolling.npz ch3 |
| source | shadow_loop_v3.py L373/L473/L520 (producer) == w10_universe_recheck.py tier_of (replay device) |
| check | recomputed at the producer's latest anchor 1788580800 (09-05 04Z): the set of names with qv4h ≥ 2.5e5 over the producer's 400 members equals the producer's own `sel_idx` (233 of 233, set identity true, `aux.json prev_rec`) |
| traded notional by tier (steady) | tier 0 13.0%, tier 1 25.4%, tier 2 61.5% |
| note | every traded symbol is tiered by its own qv4h, including names the producer force-exits outside its member set (which it costs at tier-2-worst 4.7 bps) |

## 3. Fees (VERIFIED)

| set | tier | fills maker / taker | maker notional | taker notional | maker share | maker fee bps | taker fee bps | blended fee bps |
|---|---|---|---|---|---|---|---|---|
| steady | 0 | 689 / 148 | 15302 | 2676 | 0.851 | 1.800 | 4.500 | 2.202 |
| steady | 1 | 1860 / 183 | 32487 | 2648 | 0.925 | 1.799 | 4.499 | 2.002 |
| steady | 2 | 3995 / 356 | 78278 | 6718 | 0.921 | 1.800 | 4.500 | 2.013 |
| steady | all | 6544 / 687 | 126066 | 12041 | 0.913 | 1.800 | 4.500 | 2.035 |
| all_calib | 0 | 848 / 290 | 28722 | 9214 | 0.757 | 1.801 | 4.504 | 2.458 |
| all_calib | 1 | 2371 / 414 | 75500 | 15341 | 0.831 | 1.801 | 4.505 | 2.258 |
| all_calib | 2 | 5087 / 697 | 154646 | 21347 | 0.879 | 1.801 | 4.504 | 2.129 |
| all_calib | all | 8306 / 1401 | 258868 | 45902 | 0.849 | 1.801 | 4.504 | 2.208 |

Venue-side cross-check of the same fees (daily_nav COMMISSION, BNB units, since 00:00Z each day) against the log's commission split by whether the fill opened or reduced a position:

| day | venue COMMISSION BNB | log all fills BNB | log opening fills only BNB | venue / all | venue / opening |
|---|---|---|---|---|---|
| 20260826 | 0.007163 | 0.007539 | 0.006971 | 0.950 | 1.027 |
| 20260827 | 0.008055 | 0.008767 | 0.008055 | 0.919 | 1.000 |
| 20260828 | 0.001201 | 0.001916 | 0.001201 | 0.627 | 1.000 |
| 20260829 | 0.001656 | 0.003351 | 0.001656 | 0.494 | 1.000 |
| 20260830 | 0.002410 | 0.005092 | 0.002410 | 0.473 | 1.000 |
| 20260831 | 0.001777 | 0.003589 | 0.001777 | 0.495 | 1.000 |
| 20260901 | 0.001225 | 0.002621 | 0.001225 | 0.467 | 1.000 |
| 20260902 | 0.001819 | 0.003652 | 0.001819 | 0.498 | 1.000 |
| 20260903 | 0.043970 | 0.046346 | 0.043970 | 0.949 | 1.000 |
| 20260904 | 0.005203 | 0.010710 | 0.005203 | 0.486 | 1.000 |
| 20260905 | 0.002589 | 0.005132 | 0.002589 | 0.504 | 1.000 |
| total | TOTAL venue 0.077067 vs log all 0.098715 (ratio 0.781) vs opening-only 0.076875 (ratio 1.002) | | | | |

Reading: the venue field reproduces the opening-fill commission exactly and is missing every reducing fill's commission (§10 finding 1). The fee tables above therefore use the per-trade `fee_paid` (userTrades), which is complete.

## 4. Maker share and fill ratios (VERIFIED)

| set | tier | legs sent | maker fill ratio buy | sell | all | after top-up buy | sell | all |
|---|---|---|---|---|---|---|---|---|
| steady | 0 | 768 | 0.810 | 0.799 | 0.804 | 0.933 | 0.954 | 0.945 |
| steady | 1 | 1774 | 0.904 | 0.840 | 0.871 | 0.961 | 0.925 | 0.942 |
| steady | 2 | 3479 | 0.841 | 0.855 | 0.848 | 0.931 | 0.909 | 0.921 |
| steady | all | 6021 | 0.853 | 0.843 | 0.848 | 0.939 | 0.920 | 0.929 |
| all_calib | 0 | 982 | 0.595 | 0.764 | 0.701 | 0.934 | 0.920 | 0.925 |
| all_calib | 1 | 2157 | 0.745 | 0.831 | 0.795 | 0.956 | 0.956 | 0.956 |
| all_calib | 2 | 4252 | 0.803 | 0.805 | 0.804 | 0.920 | 0.907 | 0.915 |
| all_calib | all | 7391 | 0.769 | 0.807 | 0.788 | 0.930 | 0.926 | 0.928 |
| pre_deposit | 0 | 605 | 0.765 | 0.771 | 0.769 | 0.939 | 0.937 | 0.938 |
| pre_deposit | 1 | 1371 | 0.883 | 0.808 | 0.845 | 0.941 | 0.882 | 0.912 |
| pre_deposit | 2 | 2790 | 0.854 | 0.830 | 0.842 | 0.913 | 0.878 | 0.895 |
| pre_deposit | all | 4766 | 0.851 | 0.817 | 0.834 | 0.922 | 0.888 | 0.904 |
| post_deposit | 0 | 163 | 0.866 | 0.854 | 0.861 | 0.925 | 0.989 | 0.956 |
| post_deposit | 1 | 403 | 0.934 | 0.878 | 0.904 | 0.987 | 0.976 | 0.981 |
| post_deposit | 2 | 689 | 0.817 | 0.909 | 0.859 | 0.963 | 0.976 | 0.969 |
| post_deposit | all | 1255 | 0.855 | 0.892 | 0.873 | 0.964 | 0.978 | 0.971 |

Fill ratio = filled notional / intended notional of the attempt-1 maker leg, over legs actually sent (skipped-below-minimum and halted legs excluded). After top-up adds the taker top-up fills to the numerator; the residual that is never sent is the chase experiment's no-chase arm, dust below the venue minimum, and abandoned top-ups.

## 5. −5022 post-only refusals (VERIFIED)

| set | tier | first refusal rate (legs) | first refusal rate (notional) | refused twice → taker (legs) | requotes that rested / first refusals | taker notional from refusals | taker notional from partial fills |
|---|---|---|---|---|---|---|---|
| steady | 0 | 0.333 | 0.361 | 0.113 | 0.660 | 2385 | 291 |
| steady | 1 | 0.287 | 0.261 | 0.061 | 0.786 | 2124 | 524 |
| steady | 2 | 0.222 | 0.208 | 0.043 | 0.808 | 4024 | 2693 |
| steady | all | 0.255 | 0.241 | 0.057 | 0.776 | 8533 | 3508 |
| all_calib | 0 | 0.352 | 0.415 | 0.140 | 0.604 | 7197 | 2018 |
| all_calib | 1 | 0.306 | 0.340 | 0.075 | 0.756 | 11596 | 3745 |
| all_calib | 2 | 0.236 | 0.263 | 0.052 | 0.778 | 15539 | 5808 |
| all_calib | all | 0.272 | 0.304 | 0.070 | 0.741 | 34332 | 11570 |

Per-anchor series (all live anchors; C = in calibration, S = steady):

| anchor | set | venue gross | legs sent | −5022 first n | rate (legs) | rate (notional) | refused twice n | maker filled | taker filled | turnover filled/gross | unfilled % of intended | maker share | fee USDT | fee bps of filled | fills (with +60 s mark) |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| 08-26 00Z | -- | 21999 | 77 | 21 | 0.273 | 0.349 | 5 | 1133 | 209 | 0.0610 | 8.9% | 0.844 | 0.30 | 2.218 | 91 (4) |
| 08-26 04Z | CS | 22065 | 99 | 17 | 0.172 | 0.152 | 5 | 1094 | 67 | 0.0526 | 0.7% | 0.942 | 0.23 | 1.952 | 113 (5) |
| 08-26 08Z | CS | 22098 | 46 | 15 | 0.326 | 0.402 | 2 | 478 | 23 | 0.0227 | 0.4% | 0.954 | 0.10 | 1.922 | 53 (1) |
| 08-26 12Z | C- | 29536 | 259 | 107 | 0.413 | 0.403 | 50 | 6441 | 1511 | 0.2692 | 1.2% | 0.810 | 1.84 | 2.310 | 357 (10) |
| 08-26 16Z | -- | 0 | 0 | 0 | n/a | n/a | 0 | 0 | 0 | n/a | n/a | n/a | 0.00 | n/a | 0 (0) |
| 08-26 20Z | C- | 15665 | 265 | 92 | 0.347 | 0.308 | 40 | 15641 | 0 | 0.9985 | 31.3% | 1.000 | 2.82 | 1.800 | 329 (10) |
| 08-27 00Z | C- | 22338 | 116 | 48 | 0.414 | 0.421 | 13 | 5186 | 1870 | 0.3159 | 4.8% | 0.735 | 1.77 | 2.515 | 186 (6) |
| 08-27 04Z | C- | 26054 | 241 | 75 | 0.311 | 0.334 | 18 | 3589 | 501 | 0.1570 | 10.6% | 0.878 | 0.87 | 2.129 | 317 (4) |
| 08-27 08Z | CS | 29410 | 247 | 90 | 0.364 | 0.370 | 23 | 3051 | 36 | 0.1050 | 25.4% | 0.988 | 0.57 | 1.833 | 218 (4) |
| 08-27 12Z | C- | 40264 | 271 | 74 | 0.273 | 0.287 | 24 | 10378 | 1086 | 0.2847 | 6.7% | 0.905 | 2.35 | 2.052 | 412 (13) |
| 08-27 16Z | CS | 41284 | 68 | 26 | 0.382 | 0.310 | 6 | 1326 | 202 | 0.0370 | 16.7% | 0.868 | 0.33 | 2.156 | 80 (1) |
| 08-27 20Z | CS | 40828 | 77 | 17 | 0.221 | 0.321 | 4 | 1037 | 248 | 0.0315 | 4.6% | 0.807 | 0.30 | 2.318 | 130 (2) |
| 08-28 00Z | CS | 41103 | 43 | 12 | 0.279 | 0.193 | 4 | 646 | 34 | 0.0166 | 1.7% | 0.950 | 0.13 | 1.939 | 49 (6) |
| 08-28 04Z | CS | 40904 | 81 | 18 | 0.222 | 0.249 | 3 | 827 | 31 | 0.0210 | 3.2% | 0.964 | 0.16 | 1.889 | 142 (5) |
| 08-28 08Z | CS | 40999 | 86 | 13 | 0.151 | 0.107 | 3 | 942 | 39 | 0.0239 | 9.5% | 0.961 | 0.19 | 1.902 | 95 (9) |
| 08-28 12Z | CS | 41321 | 106 | 18 | 0.170 | 0.221 | 2 | 1313 | 56 | 0.0331 | 25.5% | 0.959 | 0.26 | 1.905 | 137 (7) |
| 08-28 16Z | CS | 41282 | 142 | 56 | 0.394 | 0.271 | 18 | 1950 | 167 | 0.0513 | 2.1% | 0.921 | 0.43 | 2.022 | 158 (15) |
| 08-28 20Z | CS | 41298 | 73 | 27 | 0.370 | 0.390 | 6 | 801 | 68 | 0.0210 | 3.3% | 0.922 | 0.17 | 2.008 | 90 (1) |
| 08-29 00Z | CS | 41450 | 67 | 14 | 0.209 | 0.306 | 2 | 887 | 25 | 0.0220 | 19.2% | 0.973 | 0.17 | 1.870 | 77 (8) |
| 08-29 04Z | CS | 41512 | 123 | 19 | 0.154 | 0.142 | 7 | 1909 | 111 | 0.0487 | 10.2% | 0.945 | 0.39 | 1.948 | 145 (2) |
| 08-29 08Z | CS | 41616 | 186 | 49 | 0.263 | 0.231 | 7 | 4308 | 195 | 0.1082 | 11.5% | 0.957 | 0.86 | 1.915 | 230 (6) |
| 08-29 12Z | CS | 42013 | 139 | 27 | 0.194 | 0.271 | 11 | 2228 | 400 | 0.0626 | 16.0% | 0.848 | 0.58 | 2.211 | 151 (3) |
| 08-29 16Z | CS | 42181 | 96 | 28 | 0.292 | 0.443 | 7 | 1074 | 244 | 0.0312 | 17.0% | 0.815 | 0.30 | 2.299 | 106 (3) |
| 08-30 00Z | CS | 42146 | 201 | 32 | 0.159 | 0.141 | 9 | 6134 | 297 | 0.1526 | 7.7% | 0.954 | 1.24 | 1.924 | 277 (8) |
| 08-30 04Z | CS | 42033 | 167 | 32 | 0.192 | 0.148 | 2 | 2740 | 25 | 0.0658 | 10.2% | 0.991 | 0.50 | 1.822 | 177 (5) |
| 08-30 08Z | CS | 42505 | 131 | 22 | 0.168 | 0.136 | 3 | 2034 | 110 | 0.0504 | 16.8% | 0.949 | 0.42 | 1.936 | 137 (1) |
| 08-30 12Z | CS | 42491 | 133 | 33 | 0.248 | 0.209 | 10 | 1852 | 116 | 0.0463 | 7.7% | 0.941 | 0.39 | 1.958 | 146 (2) |
| 08-30 16Z | CS | 42147 | 138 | 37 | 0.268 | 0.266 | 10 | 2576 | 311 | 0.0685 | 5.6% | 0.892 | 0.60 | 2.091 | 150 (3) |
| 08-30 20Z | CS | 41395 | 136 | 51 | 0.375 | 0.417 | 7 | 1981 | 94 | 0.0501 | 9.7% | 0.955 | 0.40 | 1.917 | 143 (1) |
| 08-31 00Z | CS | 41408 | 118 | 41 | 0.347 | 0.330 | 9 | 1596 | 169 | 0.0426 | 3.9% | 0.904 | 0.36 | 2.058 | 133 (10) |
| 08-31 04Z | CS | 41524 | 100 | 32 | 0.320 | 0.418 | 2 | 1742 | 23 | 0.0425 | 10.5% | 0.987 | 0.32 | 1.833 | 107 (7) |
| 08-31 08Z | CS | 41509 | 153 | 58 | 0.379 | 0.336 | 7 | 2695 | 74 | 0.0667 | 6.8% | 0.973 | 0.52 | 1.877 | 180 (12) |
| 08-31 12Z | CS | 41019 | 107 | 29 | 0.271 | 0.204 | 6 | 1752 | 104 | 0.0452 | 11.0% | 0.944 | 0.36 | 1.944 | 101 (10) |
| 08-31 16Z | CS | 41166 | 127 | 35 | 0.276 | 0.332 | 7 | 2069 | 533 | 0.0632 | 3.5% | 0.795 | 0.61 | 2.354 | 153 (9) |
| 08-31 20Z | CS | 40975 | 101 | 20 | 0.198 | 0.169 | 4 | 1512 | 39 | 0.0378 | 15.3% | 0.975 | 0.29 | 1.863 | 104 (7) |
| 09-01 00Z | CS | 40753 | 115 | 35 | 0.304 | 0.277 | 9 | 1265 | 141 | 0.0345 | 6.6% | 0.900 | 0.29 | 2.068 | 131 (9) |
| 09-01 04Z | CS | 40414 | 122 | 28 | 0.230 | 0.171 | 5 | 1824 | 86 | 0.0473 | 6.1% | 0.955 | 0.37 | 1.918 | 138 (8) |
| 09-01 08Z | CS | 40200 | 90 | 36 | 0.400 | 0.436 | 13 | 855 | 288 | 0.0285 | 12.3% | 0.748 | 0.28 | 2.477 | 92 (5) |
| 09-01 12Z | CS | 39934 | 99 | 21 | 0.212 | 0.384 | 0 | 1679 | 0 | 0.0420 | 2.6% | 1.000 | 0.30 | 1.796 | 111 (4) |
| 09-01 16Z | CS | 40212 | 90 | 35 | 0.389 | 0.282 | 6 | 1552 | 115 | 0.0415 | 2.0% | 0.931 | 0.33 | 1.986 | 106 (3) |
| 09-01 20Z | CS | 40417 | 87 | 15 | 0.172 | 0.166 | 3 | 984 | 118 | 0.0273 | 20.9% | 0.893 | 0.23 | 2.085 | 111 (5) |
| 09-02 04Z | CS | 40801 | 123 | 22 | 0.179 | 0.248 | 9 | 4335 | 258 | 0.1126 | 1.6% | 0.944 | 0.90 | 1.953 | 162 (11) |
| 09-02 08Z | CS | 40555 | 95 | 20 | 0.211 | 0.252 | 6 | 2244 | 77 | 0.0572 | 1.6% | 0.967 | 0.44 | 1.885 | 122 (9) |
| 09-02 12Z | CS | 40520 | 101 | 20 | 0.198 | 0.194 | 6 | 1378 | 341 | 0.0424 | 23.5% | 0.802 | 0.40 | 2.332 | 118 (7) |
| 09-02 16Z | CS | 40693 | 93 | 23 | 0.247 | 0.222 | 5 | 1933 | 131 | 0.0507 | 2.9% | 0.936 | 0.41 | 1.967 | 104 (9) |
| 09-02 20Z | CS | 41282 | 86 | 22 | 0.256 | 0.367 | 8 | 1074 | 387 | 0.0354 | -1.8% | 0.735 | 0.37 | 2.514 | 98 (13) |
| 09-03 00Z | CS | 41502 | 80 | 17 | 0.212 | 0.262 | 5 | 1184 | 168 | 0.0326 | 3.9% | 0.876 | 0.29 | 2.133 | 105 (11) |
| 09-03 04Z | CS | 41674 | 101 | 27 | 0.267 | 0.237 | 7 | 1415 | 158 | 0.0377 | 4.0% | 0.900 | 0.33 | 2.068 | 130 (9) |
| 09-03 08Z | CS | 41639 | 102 | 25 | 0.245 | 0.183 | 6 | 2245 | 235 | 0.0596 | 1.5% | 0.905 | 0.51 | 2.053 | 122 (5) |
| 09-03 12Z | CS | 42029 | 91 | 21 | 0.231 | 0.176 | 4 | 1181 | 259 | 0.0343 | 25.0% | 0.820 | 0.33 | 2.287 | 102 (4) |
| 09-03 16Z | C- | 163439 | 218 | 79 | 0.362 | 0.366 | 32 | 91567 | 28893 | 0.7370 | 3.4% | 0.760 | 29.55 | 2.453 | 875 (23) |
| 09-03 20Z | CS | 166138 | 169 | 44 | 0.260 | 0.161 | 8 | 8101 | 2121 | 0.0615 | 2.1% | 0.793 | 2.42 | 2.364 | 292 (6) |
| 09-04 00Z | CS | 165589 | 141 | 31 | 0.220 | 0.219 | 4 | 4481 | 195 | 0.0282 | 2.0% | 0.958 | 0.90 | 1.917 | 180 (12) |
| 09-04 04Z | CS | 164402 | 136 | 27 | 0.199 | 0.252 | 3 | 4697 | 247 | 0.0301 | 5.0% | 0.950 | 0.96 | 1.932 | 182 (10) |
| 09-04 08Z | CS | 163524 | 149 | 40 | 0.268 | 0.231 | 8 | 5270 | 411 | 0.0347 | 2.6% | 0.928 | 1.13 | 1.994 | 210 (6) |
| 09-04 12Z | CS | 161095 | 161 | 51 | 0.317 | 0.371 | 17 | 4096 | 1003 | 0.0317 | 2.6% | 0.803 | 1.18 | 2.316 | 196 (6) |
| 09-04 16Z | CS | 163335 | 188 | 47 | 0.250 | 0.225 | 13 | 13121 | 554 | 0.0837 | 1.2% | 0.959 | 2.62 | 1.917 | 262 (8) |
| 09-04 20Z | CS | 163756 | 139 | 22 | 0.158 | 0.138 | 2 | 4713 | 214 | 0.0301 | 3.9% | 0.957 | 0.94 | 1.916 | 174 (9) |
| 09-05 00Z | CS | 163522 | 172 | 39 | 0.227 | 0.204 | 11 | 3885 | 697 | 0.0280 | 7.7% | 0.848 | 1.01 | 2.211 | 201 (8) |

## 6. +60 s markout (INFERRED — coverage and selection stated)

Sign: positive = the price moved in the direction of our trade after the fill (favourable); negative = adverse selection. Notional-weighted. Only fills with a backfilled mark (`/fapi/v1/aggTrades` first trade at or after fill + 60 s).

| set | type | tier | marks n | coverage of notional | weighted bps | CI95 (fill bootstrap) | median bps |
|---|---|---|---|---|---|---|---|
| steady | maker | 0 | 59 | 7.9% | -14.19 | [-30.75, +2.93] | -1.84 |
| steady | maker | 1 | 124 | 9.3% | -10.88 | [-22.44, +0.39] | -3.32 |
| steady | maker | 2 | 126 | 2.9% | +4.22 | [-5.01, +15.57] | +0.00 |
| steady | maker | all | 309 | 5.2% | -6.20 | [-13.71, +1.33] | -1.73 |
| steady | taker top-up | 0 | 9 | 15.0% | -68.77 | [-93.19, -28.14] | -86.34 |
| steady | taker top-up | 1 | 10 | 2.8% | +1.99 | [-7.11, +18.69] | +21.91 |
| steady | taker top-up | 2 | 2 | 0.6% | -2.15 | [-10.24, +6.73] | -1.76 |
| steady | taker top-up | all | 21 | 4.3% | -53.25 | [-76.53, -15.45] | -10.24 |
| all_calib | maker | 0 | 72 | 8.7% | -13.04 | [-26.01, +0.16] | -2.05 |
| all_calib | maker | 1 | 139 | 9.0% | -14.85 | [-25.74, -0.97] | -3.58 |
| all_calib | maker | 2 | 155 | 2.5% | -4.09 | [-14.75, +9.73] | +0.00 |
| all_calib | maker | all | 366 | 5.1% | -11.33 | [-18.97, -2.69] | -1.91 |
| all_calib | taker top-up | 0 | 9 | 4.3% | -68.77 | [-93.11, -28.49] | -86.34 |
| all_calib | taker top-up | 1 | 19 | 6.8% | -2.03 | [-4.79, +1.39] | -4.02 |
| all_calib | taker top-up | 2 | 2 | 0.2% | -2.15 | [-10.24, +6.73] | -1.76 |
| all_calib | taker top-up | all | 30 | 3.2% | -20.06 | [-44.10, -4.99] | -4.02 |

Why the subset is not random (VERIFIED from `ops/backfill_markout.py` and `markout_diag.out`): the backfill walks symbols in sorted order and fills in time order under a request budget, so the marked fills are the alphabetically-first names (40 of 333 symbols; top: 4USDT, 1000PEPEUSDT, ACEUSDT, 1000BONKUSDT, 0GUSDT) and the earliest fills of each anchor (median rank 0.19 within the anchor; median fill delay 22 s vs 65 s in the population). The subset therefore over-represents fast fills. Re-weighting the subset to the population's fill-delay mix moves the steady maker figure only from −6.2 to −6.7 bps, because the sparse slow bucket (16 marks) is worse still; the symbol selection cannot be corrected from the logs:

| set | type | delay bucket | population notional share | marks n | subset weighted bps |
|---|---|---|---|---|---|
| steady | maker | [0,10) s | 0.070 | 111 | -11.00 |
| steady | maker | [10,60) s | 0.401 | 119 | -2.31 |
| steady | maker | [60,300) s | 0.392 | 63 | -3.36 |
| steady | maker | [300,inf) s | 0.136 | 16 | -27.30 |
| steady | maker | **re-weighted** | | 309 | **-6.73** (raw -6.20) |
| steady | topup_taker | [0,10) s | 0.000 | 0 | n/a |
| steady | topup_taker | [10,60) s | 0.000 | 0 | n/a |
| steady | topup_taker | [60,300) s | 0.000 | 0 | n/a |
| steady | topup_taker | [300,inf) s | 1.000 | 21 | -53.25 |
| steady | topup_taker | **re-weighted** | | 21 | **-53.25** (raw -53.25) |
| all_calib | maker | [0,10) s | 0.049 | 132 | -5.68 |
| all_calib | maker | [10,60) s | 0.307 | 134 | -7.50 |
| all_calib | maker | [60,300) s | 0.491 | 73 | -19.05 |
| all_calib | maker | [300,inf) s | 0.153 | 27 | -20.21 |
| all_calib | maker | **re-weighted** | | 366 | **-15.02** (raw -11.33) |
| all_calib | topup_taker | [0,10) s | 0.000 | 0 | n/a |
| all_calib | topup_taker | [10,60) s | 0.000 | 0 | n/a |
| all_calib | topup_taker | [60,300) s | 0.000 | 0 | n/a |
| all_calib | topup_taker | [300,inf) s | 1.000 | 30 | -20.06 |
| all_calib | topup_taker | **re-weighted** | | 30 | **-20.06** (raw -20.06) |

Supplementary, 100% coverage, not one of the frozen items: fill price versus the anchor mid (`mid_at_anchor`, positive = filled better than the anchor mid). Maker fills beat the anchor mid; taker top-ups, sent up to 900 s later, pay delay plus spread.

| set | type | tier | weighted bps | CI95 | median bps |
|---|---|---|---|---|---|
| steady | maker | 0 | +4.21 | [+3.13, +5.46] | +1.41 |
| steady | maker | 1 | +4.24 | [+3.69, +4.84] | +2.08 |
| steady | maker | 2 | +3.76 | [+3.28, +4.28] | +2.08 |
| steady | maker | all | +3.94 | [+3.57, +4.32] | +2.03 |
| steady | taker top-up | 0 | +119.70 | [-27.65, +301.04] | +14.69 |
| steady | taker top-up | 1 | -79.16 | [-120.82, -39.35] | -35.55 |
| steady | taker top-up | 2 | +6.82 | [-11.17, +26.48] | -13.60 |
| steady | taker top-up | all | +13.00 | [-23.36, +58.43] | -13.00 |
| all_calib | maker | 0 | +5.15 | [+3.02, +8.46] | +1.39 |
| all_calib | maker | 1 | +5.63 | [+4.02, +7.76] | +2.19 |
| all_calib | maker | 2 | +3.95 | [+3.49, +4.45] | +2.15 |
| all_calib | maker | all | +4.57 | [+3.92, +5.35] | +2.10 |
| all_calib | taker top-up | 0 | -5.44 | [-52.35, +55.88] | -17.00 |
| all_calib | taker top-up | 1 | -40.48 | [-62.02, -15.32] | -33.44 |
| all_calib | taker top-up | 2 | -17.17 | [-39.88, +9.94] | -21.26 |
| all_calib | taker top-up | all | -22.61 | [-39.42, -3.83] | -21.26 |

## 7. Turnover per anchor (VERIFIED)

| set | n anchors | mean | median | notional-weighted | p10 | p90 | CI95 of mean (anchor bootstrap) | intended turnover mean | unfilled share of intended (mean) |
|---|---|---|---|---|---|---|---|---|---|
| steady | 51 | 0.0477 | 0.0420 | 0.0455 | 0.0239 | 0.0685 | [+0.0410, +0.0552] | 0.0523 | 0.081 |
| all_calib | 57 | 0.0911 | 0.0426 | 0.0914 | 0.0259 | 0.1543 | [+0.0556, +0.1388] | 0.1047 | 0.083 |
| pre_deposit | 43 | 0.0489 | 0.0425 | 0.0489 | 0.0229 | 0.0681 | n/a | 0.0542 | 0.090 |
| post_deposit | 8 | 0.0410 | 0.0309 | 0.0410 | 0.0282 | 0.0682 | n/a | 0.0422 | 0.034 |

Turnover = Σ|filled notional| of the anchor's maker and top-up fills / the anchor's venue gross after the anchor. The producer's own book-level turnover at the latest anchor is 0.02008 (shadow_log); the executor's filled turnover at 09-05 00Z is 0.0280, the difference being the executor's re-demean, rescale, floors and forced exits.

## 8. All-in cost per unit of turnover by tier

Definition (prereg §1): replay cost = turnover × [maker_share × maker_bps + (1 − maker_share) × taker_bps] per tier, with maker_bps / taker_bps = fee + (−markout). Two versions, because the markout leg is a 5% biased sample:

| set | tier | share of live turnover | maker share | maker fee bps | taker fee bps | fee-only cost per unit turnover (VERIFIED) | maker markout bps | taker markout bps | fee − markout cost per unit turnover (INFERRED) | device COST_B blended (for comparison) |
|---|---|---|---|---|---|---|---|---|---|---|
| steady | 0 | 0.130 | 0.851 | 1.800 | 4.500 | 2.202 | -14.19 | -68.77 | 24.52 | 0.537 |
| steady | 1 | 0.254 | 0.925 | 1.799 | 4.499 | 2.002 | -10.88 | +1.99 | 11.91 | 1.875 |
| steady | 2 | 0.615 | 0.921 | 1.800 | 4.500 | 2.013 | +4.22 | -2.15 | -1.70 | 4.700 |
| steady | all | 1.000 | 0.913 | 1.800 | 4.500 | 2.035 | -6.20 | -53.25 | 12.34 | 3.439 (device on live tier mix) |
| all_calib | 0 | 0.124 | 0.757 | 1.801 | 4.504 | 2.458 | -13.04 | -68.77 | 29.03 | 0.537 |
| all_calib | 1 | 0.298 | 0.831 | 1.801 | 4.505 | 2.258 | -14.85 | -2.03 | 14.94 | 1.875 |
| all_calib | 2 | 0.577 | 0.879 | 1.801 | 4.504 | 2.129 | -4.09 | -2.15 | 5.98 | 4.700 |
| all_calib | all | 1.000 | 0.849 | 1.801 | 4.504 | 2.208 | -11.33 | -20.06 | 14.85 | 3.340 (device on live tier mix) |

Vectors in the device's `COST_B` shape `(maker_bps, taker_bps, maker_share)` per tier 0/1/2:

| version | tier 0 | tier 1 | tier 2 | label |
|---|---|---|---|---|
| live, fee only (steady) | (1.80, 4.50, 0.851) | (1.80, 4.50, 0.925) | (1.80, 4.50, 0.921) | VERIFIED |
| live, fee − raw markout (steady) | (15.99, 73.27, 0.851) | (12.67, 2.51, 0.925) | (-2.42, 6.65, 0.921) | INFERRED, 68/134/128 marks, taker leg on 9/10/2 marks |
| live, fee − delay-reweighted markout, all tiers pooled (steady) | maker 8.53, taker 57.75, maker share 0.913 → 12.82 bps per unit turnover | | | INFERRED |
| device COST_B (unchanged) | (−0.25, 5.0, 0.85) | (0.5, 6.0, 0.75) | (2.0, 8.0, 0.55) | replay default |
| **emitted for the replay: fee + slippage vs anchor mid (steady) = top-level `tiers`** | (-2.41, 16.79, 0.851) | (-2.44, 16.79, 0.925) | (-1.93, 16.79, 0.921) | VERIFIED inputs, 100% coverage; taker slippage pooled across tiers |

### 8b. The vector the replay consumes (top-level `tiers`, `book`; device COST_B order)

Why slippage versus the anchor mid and not the +60 s markout: the paper book is priced at a reference price and the real book at the fill; everything after the fill is common to both, so the incremental cost versus paper is (fill − reference) per unit traded. `mid_at_anchor` is the executor's pricing moment (N + 24 min) and covers every fill. Per-fill slippage is winsorised at ±100 bps; CI95 are anchor-level bootstraps. The 24-minute timing decay between the nominal 4h grid and that moment is not in this vector (paper nominal − paper shifted = +2.85 bps per anchor, §9); the never-filled residual is not either (it is in `book.twin_bps_per_anchor`).

| tier | share of filled notional | maker fee | maker fill vs anchor mid, winsorised (CI95) [raw, median, n] | **maker_bps** | taker fee | taker fill vs anchor mid, pooled all tiers (CI95) [raw, median, n] | this tier only | **taker_bps** | **maker_share** | cost per unit turnover |
|---|---|---|---|---|---|---|---|---|---|---|
| tier0_qv4h>=5e6 | 0.130 | 1.80 | +4.21 [+2.83, +6.09] [+4.21, +1.41, 689] | **-2.41** | 4.50 | -12.29 [-21.26, -2.82] [+13.00, -13.00, 687] | -0.20 (n 148) → 4.70 | **16.79** | **0.851** | 0.44 |
| tier1_qv4h>=1e6 | 0.254 | 1.80 | +4.24 [+3.61, +4.98] [+4.24, +2.08, 1860] | **-2.44** | 4.50 | -12.29 [-21.26, -2.82] [+13.00, -13.00, 687] | -39.63 (n 183) → 44.13 | **16.79** | **0.925** | -0.99 |
| tier2_rest | 0.615 | 1.80 | +3.73 [+3.21, +4.38] [+3.76, +2.08, 3995] | **-1.93** | 4.50 | -12.29 [-21.26, -2.82] [+13.00, -13.00, 687] | -6.34 (n 356) → 10.84 | **16.79** | **0.921** | -0.45 |
| book (all tiers) | 1.000 | 1.80 | +3.92 [+3.47, +4.46] | **-2.12** | 4.50 | -12.29 [-21.26, -2.82] | | **16.79** | **0.913** | -0.47 |

Same vector on all 57 calibration anchors (ramps and deposit build included; in `alternatives`): (-3.35, 35.42, 0.757) / (-3.82, 35.42, 0.831) / (-2.13, 35.42, 0.879); book cost per unit turnover 2.99 bps.

Units chain (VERIFIED arithmetic, printed by `cost_calib.py`):

| step | steady | all_calib |
|---|---|---|
| fee, bps of gross per anchor (Σ fees / Σ venue gross) | 0.0926 | 0.2019 |
| × 2190 anchors = % of gross per year | 2.0276 | 4.4224 |
| × 2 = % of NAV per year at 2× gross | 4.0552 | 8.8449 |
| check: turnover × fee-only cost per unit turnover (bps of gross per anchor) | 0.0926 | 0.2019 |
| device COST_B on the live tier mix, bps per unit turnover | 3.4395 | 3.3398 |

## 9. Paper target vs real (twin), refreshed on all anchors to date (VERIFIED; `canon_reconcile.py` reused verbatim, sha 03ab6539…)

Canonical set = clean 4h windows from the first combo anchor to the last closable anchor: n = 53, 08-26 04Z → 09-04 20Z (exclusions: halted 08-26 16Z, flattened 08-26 12Z, missing-next-anchor slots). bps of realized gross per anchor.

| measure | mean | s.e. | CI95 (bootstrap) | n | meaning |
|---|---|---|---|---|---|
| paper Π, nominal grid (N, N+4h], target weights | +3.78 | 4.58 | [-4.93, +12.81] | 53 | what the target book would have made priced at the 4h grid |
| paper Π shifted 25 min (venue pricing moment) | +0.93 | 4.22 | [-7.12, +9.24] | 53 | same book priced when the executor actually trades |
| twin = venue positions × Δmid | +2.16 | 4.46 | [-6.46, +10.84] | 53 | the real positions' price P&L |
| funding paid in window | -1.90 | 0.09 | | 53 | carry actually paid |
| twin + funding | +0.26 | 4.45 | [-8.50, +8.91] | 53 | real P&L per anchor before fees |
| paper (shifted) − twin | -1.23 | 2.53 | [-6.10, +3.72] | 53 | execution discount band, price leg only |
| paper (nominal) − twin − funding | +3.51 | | [-2.70, +9.51] | 53 | everything the paper book does not pay |
| corr(paper shifted, twin) | 0.832 | | | | |

Same measures on the reconcile script's other sets (mean bps per anchor):

| set | n | paper Π | paper Π shifted 25 min | twin | funding | twin + funding | s.e. |
|---|---|---|---|---|---|---|---|
| canon | 53 | +3.78 | +0.93 | +2.16 | -1.90 | +0.26 | 4.45 |
| canon_ex_0903 | 47 | +5.73 | +2.19 | +1.52 | -1.95 | -0.43 | 4.92 |
| canon_ex_0903_and_0904 | 40 | +7.44 | +3.81 | +2.59 | -2.09 | +0.49 | 5.45 |
| I1_set | 50 | +2.93 | +0.57 | +0.36 | -1.92 | -1.56 | 4.74 |
| I2_set | 55 | +2.87 | +0.36 | +0.67 | -1.86 | -1.19 | 4.47 |
| canon_plus_flatten_anchor | 54 | +2.91 | +0.24 | +0.85 | -1.86 | -1.01 | 4.55 |

Daily check against the executor's own equity (daily_nav, net of transfers), USDT:

| nav day | span | equity Δ net of transfers | twin | funding in span | twin + funding | residual | fills vs anchor mid | paper Π | paper Π shifted | windows | notes |
|---|---|---|---|---|---|---|---|---|---|---|---|
| 20260826 | (08-25 20:46Z, 08-26 20:45Z] | +70.8 | -6.0 | -15.6 | -21.6 | +92.4 | +7.4 | +114.1 | +119.3 | 6 | pre-combo anchor (producer=shadow_loop_v; pre-combo anchor (producer=shadow_loop_v; book flattened intra-window (ladder_flat; flat book at anchor (opening_halted=True |
| 20260827 | (08-26 20:45Z, 08-27 20:41Z] | -64.2 | -70.1 | -35.2 | -105.3 | +41.1 | +5.6 | +102.3 | +49.3 | 6 |  |
| 20260828 | (08-27 20:41Z, 08-28 20:41Z] | +169.1 | +207.5 | -41.7 | +165.8 | +3.3 | +4.1 | +304.9 | +339.7 | 6 |  |
| 20260829 | (08-28 20:41Z, 08-29 20:29Z] | +411.2 | +392.4 | -44.9 | +347.5 | +63.7 | +2.9 | +344.0 | +276.3 | 5 |  |
| 20260830 | (08-29 20:29Z, 08-30 20:42Z] | -171.8 | -56.0 | -69.2 | -125.2 | -46.7 | +6.4 | -272.3 | -227.1 | 6 | next anchor row missing -> no 4h end mid |
| 20260831 | (08-30 20:42Z, 08-31 20:41Z] | -267.0 | -186.9 | -54.3 | -241.2 | -25.7 | +1.1 | -167.2 | -157.8 | 6 |  |
| 20260901 | (08-31 20:41Z, 09-01 20:41Z] | -336.9 | -304.8 | -57.9 | -362.6 | +25.7 | +2.2 | +36.7 | -97.7 | 6 |  |
| 20260902 | (09-01 20:41Z, 09-02 20:41Z] | +778.1 | +691.7 | -38.5 | +653.2 | +124.9 | +70.3 | +607.8 | +297.8 | 5 | next anchor row missing -> no 4h end mid |
| 20260903 | (09-02 20:41Z, 09-03 20:43Z] | -136.1 | +131.2 | -47.6 | +83.6 | -219.8 | -44.6 | -566.3 | -420.8 | 6 |  |
| 20260904 | (09-03 20:43Z, 09-04 20:43Z] | -438.7 | -287.6 | -114.4 | -402.0 | -36.7 | +1.9 | -689.9 | -616.9 | 6 |  |
| 20260905 | (09-04 20:43Z, 09-05 00:43Z] | -204.0 | -242.3 | -16.8 | -259.1 | +55.1 | +0.0 | +216.5 | -202.0 | 1 | PARTIAL day;  |
| sum 08-27…09-03 (full days, clean) | | +382.4 | | | +415.9 | -33.5 | +48.0 | | | | |
| sum all days incl. 08-26 flatten day and partial 09-05 | | -189.6 | | | -266.9 | +77.3 | +57.2 | | | | |

Execution discount per unit of turnover, book level: (paper shifted − twin) / steady turnover = -27.1 bps per unit turnover, CI95 [-134.0, +81.8]. book-level twin gap divided by steady turnover per anchor; the CI is ±50 bps per unit turnover wide at n=53 — reported as a band, not a calibration.

## 10. Findings and limitations

| # | finding | label | receipt |
|---|---|---|---|
| 1 | daily_nav.realised_by_type.COMMISSION equals the pilot-log commission of position-OPENING fills only. Position-REDUCING fills' COMMISSION rows are missing. Cause: live/binance_broker.py realised-income pagination dedupes rows on tranId; a reducing fill's COMMISSION row shares its tranId with the same trade's REALIZED_PNL row, so the second of the pair is dropped. Reproduced by classifying every fill as opening/reducing from the previous anchor's position_readback. Money at stake: small: commission is charged in BNB (~0.002 BNB/day at 41k gross, ~0.005-0.011 BNB/day at 163k gross); REALIZED_PNL rows are the ones kept. Also note realised_pnl sums COMMISSION in BNB units with USDT rows. Effect on this report: none — fees here come from /fapi/v1/userTrades via orders.fee_paid (= commission_BNB x bookTicker BNB mid, exact on 6908/6908 rows) and fills.commission; daily_nav COMMISSION must not be used for fee totals. | VERIFIED (exact match on 10/11 days; 08-26 differs by the flatten event whose fees are not in fills.jsonl) | commission_collision_test.py -> commission_collision_test.out |
| 2 | +60 s markout coverage is 5% of notional and the marked fills are selected by symbol order and fill order, not at random; the taker leg rests on 21–30 marks. The fee-minus-markout cost vector is therefore INFERRED and should not replace the device cost without a full backfill (the backfill ordering is a known-unfixed item in STATE §3). | INFERRED | markout_diag.out, §6 |
| 3 | The step-up anchors (leverage ramp 08-26/27, deposit build 09-03 16Z) have 2–3× the taker share and 4–20× the turnover of steady anchors; they are in `all_calib` and out of `primary_steady`. Using `all_calib` fee drag as a run-rate would overstate it (4.4% vs 2.0% of gross per year). | VERIFIED | §1, §8 |
| 4 | Fees are exactly the venue schedule with the BNB discount (maker 0.020% × 0.9, taker 0.050% × 0.9); there is no observed variation by tier, side or day, so `maker_bps`/`taker_bps` fee legs are constants and the calibration content is in maker share, fill ratio, refusal rate and turnover. | VERIFIED | §3 |
| 5 | Funding settlement actuals versus the panel carry were not computed (not required by the task). | — | — |
| 6 | The 08-26 12:49Z protective flatten (E-0826-F) is outside all fee/fill tables: no fills rows exist for it and its fees are only in the venue's 08-26 COMMISSION. | VERIFIED | §1 |
| 7 | The pilot journal (journal_2026-09-02_forward_gate_42.md L26) quotes a −5022 refusal of 76% for the 09-03 16Z deposit build under an unstated definition. This report's definition (first refusals / maker legs sent) gives 0.362 by legs (79/218) and 0.366 by notional, with 32 legs refused twice. The two are not the same quantity; the journal figure should be re-derived from its generating line before reuse. | VERIFIED (this report's number) | §5 series |

## 11. Product

`cost_calib.json` (this directory). Keys: `calib.primary_steady` / `calib.all_calib` / `calib.pre_deposit` / `calib.post_deposit` each with `tiers.{0,1,2}` and `all` → `{maker_bps_fee, taker_bps_fee, maker_share, fill_ratio_maker(_buy/_sell), fill_ratio_after_topup(_buy/_sell), reject5022_first_rate, reject5022_to_taker_rate, markout60_maker_bps, markout60_taker_bps, markout60_coverage_notional, markout60_n, cost_per_unit_turnover_fee_only_bps, cost_per_unit_turnover_fee_minus_markout_bps, share_of_filled_notional, COST_B_format_fee_only, COST_B_format_fee_minus_markout}`, plus `turnover_per_anchor`, `units_chain`, `anchors{n, first, last}`; `per_anchor` (series); `per_anchor_summary`; `uncertainty` (bootstrap CIs); `markout_poststratified`; `twin_gap`; `fee_crosscheck_daily`; `findings`; `tier_rule`; `receipts`.

## 12. Receipts

| file | sha256 | produced by |
|---|---|---|
| cost_calib.py | ff3ec02f1fa61367… | this directory |
| canon_reconcile.py | 03ab65399c008406… | copied verbatim from multi_asset/exports/research/retrain_2026-09/review_caliber_wf/gap_live_pnl/ |
| canon_report.json | 679755f411343c3e… | this directory |
| commission_collision_test.py | 5cdec3e78161b66e… | this directory |
| markout_diag.py | 4200fa48d41aa526… | this directory |
| finalize_and_render.py | ec0dc22937602239… | this directory |
| cost_calib.json | (written by finalize_and_render.py at 2026-09-05T04:50:49Z) | |

Commands (run in this directory, in order):

```
cd <calib dir> && cp <research repo>/multi_asset/exports/research/retrain_2026-09/review_caliber_wf/gap_live_pnl/canon_reconcile.py . && python3 canon_reconcile.py > canon_run.log
python3 cost_calib.py > calib_run.log
python3 markout_diag.py > markout_diag.out
python3 finalize_and_render.py
```

Inputs: pilot log days 20260826…20260905 under `~/dl_quant_live/state/live/pilot_log/`; `~/wide_shadow/state/rolling.npz` sha 463c05d0ffc01f21…; `~/wide_shadow/shadow_bundle/config.json` sha 3a8422f377519cac…; `~/wide_shadow/state/aux.json` (tier check). Nothing under `~/dl_quant_live` or `~/wide_shadow` was written.
