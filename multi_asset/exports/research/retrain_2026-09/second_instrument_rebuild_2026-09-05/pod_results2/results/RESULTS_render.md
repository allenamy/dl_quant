## Gate table (frozen rules: PREREG_second_instrument_rebuild_2026-09-05 §2)

| gate | frozen rule | verdict | printed evidence |
|---|---|---|---|
| G1 panel bitwise | every array: NaN positions + finite values bitwise vs v1 | **FAIL** | results/G1.json: 0/21 arrays bitwise; ts equal True (14329 vs 14329) |
| G1b cache 2022+ vs _ext | informational | — | common ts 486145; unequal share per channel: ret5 0.0e+00 (nan-mismatch 304978), range 0.0e+00 (nan-mismatch 304841), cpos 0.0e+00 (nan-mismatch 165269), log_qv 0.0e+00 (nan-mismatch 304841), log_cnt 0.0e+00 (nan-mismatch 304841), log_avgsz 0.0e+00 (nan-mismatch 177144), tbf 0.0e+00 (nan-mismatch 177144) |
| G2(a) nets bitwise | stage-6 nets vs real 08-21 nets (ref/, pod copies are 144-byte stubs) | **FAIL** | results/G2a.json: d30 bitwise share 0.0000, max|Δ| 9.902e+01 bps, corr 0.9275; ts equal True |
| G2(b) per-gross series | ts set identical AND max|Δ| ≤ 1e-6 bps | **FAIL** | ts_set_identical False (step8 12279 vs ref 9941, ref⊂step8 True); common 9941: max|Δ| 1.169e+02, corr 0.9055 |
| G2(c) device parity | log ≤1e-6 PASS and simple FAIL | **FAIL** | maxabs_diff_vs_pod_backup: log S0 4.498e+01 / d30 5.625e+01; simple S0 2.735e+02 / d30 2.612e+02 |
| G3(a) static census | 0 log/expm1 hits on a return quantity in the 4 scripts | **PASS** | 0 return-path hits; volume-channel hits: pod_stop_arms_v3.py:59; pod_panel_ext.py:26 |
| G3(b1) Y4 == Σ ret5 | full grid bitwise incl. NaN positions | **PASS** | both-finite 3734643, neq 0, nan-mismatch 0; direct float64 window sum on 300 anchors neq 0/75173 |
| G3(b2) y4s vs raw closes | ≥1000 anchors (≥300 in 2020-21), max|Δ| ≤ 2e-5 | **FAIL** | n 1090 (2020-21: 346); max|Δ| 8.357e-05, p99 1.94e-05, median 2.91e-06; cells >2e-5: 9 (within 1.5× float16 bound: 9); max |Δ|/f16_bound 0.44 |
| G4 leakage battery | (i)…(vi) all pass | **FAIL** | (i) PASS (ii) PASS (iii) FAIL (iv) PASS (v) PASS (vi) PASS; hist king admitted to G5: False |

## G1 classification (per array; unequal = both finite and different; nan-mismatch = finite on one side only)

| array | pass | n both-finite | n unequal | n nan-mismatch (NaN only in rebuilt / only in v1) | max|Δ| | max rel | symbols affected | class |
|---|---|---|---|---|---|---|---|---|
| elig | FAIL | — | 2274 | — | — | — | — | bool |
| Y4 | FAIL | 3730035 | 0 | 4608 (0 / 4608) | 0.00e+00 | 0.0e+00 | 348 | coverage (NaN-position only: one side has data the other lacks) |
| Y24 | FAIL | 3727693 | 0 | 6348 (0 / 6348) | 0.00e+00 | 0.0e+00 | 348 | coverage (NaN-position only: one side has data the other lacks) |
| f_rev_4h | FAIL | 11878741 | 2694 | 0 (0 / 0) | 2.33e-01 | 2.3e+11 | 222 | data content differs (raw zip rows or code path) — see hand check |
| f_rev_24h | FAIL | 11878741 | 2694 | 0 (0 / 0) | 3.63e-01 | 3.6e+11 | 222 | data content differs (raw zip rows or code path) — see hand check |
| f_rev_3d | FAIL | 11878741 | 2694 | 0 (0 / 0) | 3.90e-01 | 2.6e+10 | 222 | data content differs (raw zip rows or code path) — see hand check |
| f_mom_7d | FAIL | 11878741 | 2694 | 0 (0 / 0) | 3.90e-01 | 1.1e+03 | 222 | data content differs (raw zip rows or code path) — see hand check |
| f_mom_30d | FAIL | 11878741 | 2694 | 0 (0 / 0) | 3.90e-01 | 5.0e+03 | 222 | data content differs (raw zip rows or code path) — see hand check |
| f_mom_7d_x24 | FAIL | 11878741 | 1362 | 0 (0 / 0) | 2.78e-01 | 9.5e+02 | 222 | data content differs (raw zip rows or code path) — see hand check |
| f_vol_7d | FAIL | 11878741 | 2726 | 0 (0 / 0) | 2.85e-03 | 1.4e+00 | 226 | data content differs (raw zip rows or code path) — see hand check |
| f_volq_ratio | FAIL | 3439310 | 2694 | 0 (0 / 0) | 4.58e+00 | 4.5e+12 | 222 | data content differs (raw zip rows or code path) — see hand check |
| f_amihud_24h | FAIL | 3430964 | 1314 | 1380 (0 / 1380) | 3.03e+02 | 5.2e+10 | 222 | data content differs (raw zip rows or code path) — see hand check |
| f_range_24h | FAIL | 11878741 | 2694 | 0 (0 / 0) | 2.34e-02 | 2.3e+10 | 222 | data content differs (raw zip rows or code path) — see hand check |
| f_cpos_24h | FAIL | 11878741 | 2694 | 0 (0 / 0) | 7.99e-01 | 5.9e+11 | 222 | data content differs (raw zip rows or code path) — see hand check |
| f_tbf_24h | FAIL | 11878741 | 2694 | 0 (0 / 0) | 6.92e-01 | 6.1e+11 | 222 | data content differs (raw zip rows or code path) — see hand check |
| f_asz_24h | FAIL | 11878741 | 2694 | 0 (0 / 0) | 7.33e+00 | 7.3e+12 | 222 | data content differs (raw zip rows or code path) — see hand check |
| f_fund_now | FAIL | 2401631 | 0 | 1155487 (0 / 1155487) | 0.00e+00 | 0.0e+00 | 385 | coverage (NaN-position only: one side has data the other lacks) |
| f_fund_iv | FAIL | 2401631 | 138 | 1155487 (0 / 1155487) | 3.00e+00 | 7.5e-01 | 390 | funding-source difference (pod2 funding zips 2019-09..2026-08 for 829 symbols + 09-01 API tail vs the 08-21 pod's funding set) — see per-year table |
| f_fund_ema | FAIL | 2401631 | 0 | 1155487 (0 / 1155487) | 0.00e+00 | 0.0e+00 | 385 | coverage (NaN-position only: one side has data the other lacks) |
| f_fund_ema_v1 | FAIL | 2401631 | 324 | 1155487 (0 / 1155487) | 5.11e-03 | 1.9e+00 | 390 | funding-source difference (pod2 funding zips 2019-09..2026-08 for 829 symbols + 09-01 API tail vs the 08-21 pod's funding set) — see per-year table |
| f_fund_ema_v2 | FAIL | 2401631 | 316 | 1155487 (0 / 1155487) | 4.53e-02 | 3.9e+00 | 390 | funding-source difference (pod2 funding zips 2019-09..2026-08 for 829 symbols + 09-01 API tail vs the 08-21 pod's funding set) — see per-year table |

Per-year detail for failing arrays (n unequal / n nan-mismatch / max|Δ|):

- `Y4`: 2020: 0/0/0.0e+00 | 2021: 0/0/0.0e+00 | 2022: 0/0/0.0e+00 | 2023: 0/0/0.0e+00 | 2024: 0/0/0.0e+00 | 2025: 0/0/0.0e+00 | 2026: 0/4608/0.0e+00; top symbols [['ZRXUSDT', 19], ['AGIXUSDT', 19], ['TONUSDT', 19], ['SUPERUSDT', 19], ['OCEANUSDT', 19], ['OMGUSDT', 19]]
- `Y24`: 2020: 0/0/0.0e+00 | 2021: 0/0/0.0e+00 | 2022: 0/0/0.0e+00 | 2023: 0/0/0.0e+00 | 2024: 0/0/0.0e+00 | 2025: 0/0/0.0e+00 | 2026: 0/6348/0.0e+00; top symbols [['ZRXUSDT', 24], ['AGIXUSDT', 24], ['TONUSDT', 24], ['SUPERUSDT', 24], ['OCEANUSDT', 24], ['OMGUSDT', 24]]
- `f_rev_4h`: 2020: 0/0/0.0e+00 | 2021: 0/0/0.0e+00 | 2022: 0/0/0.0e+00 | 2023: 0/0/0.0e+00 | 2024: 0/0/0.0e+00 | 2025: 0/0/0.0e+00 | 2026: 2694/0/2.3e-01; top symbols [['ZRXUSDT', 18], ['SUPERUSDT', 18], ['MASKUSDT', 18], ['KNCUSDT', 18], ['BANDUSDT', 18], ['1000000BOBUSDT', 12]]
- `f_rev_24h`: 2020: 0/0/0.0e+00 | 2021: 0/0/0.0e+00 | 2022: 0/0/0.0e+00 | 2023: 0/0/0.0e+00 | 2024: 0/0/0.0e+00 | 2025: 0/0/0.0e+00 | 2026: 2694/0/3.6e-01; top symbols [['ZRXUSDT', 18], ['SUPERUSDT', 18], ['MASKUSDT', 18], ['KNCUSDT', 18], ['BANDUSDT', 18], ['1000000BOBUSDT', 12]]
- `f_rev_3d`: 2020: 0/0/0.0e+00 | 2021: 0/0/0.0e+00 | 2022: 0/0/0.0e+00 | 2023: 0/0/0.0e+00 | 2024: 0/0/0.0e+00 | 2025: 0/0/0.0e+00 | 2026: 2694/0/3.9e-01; top symbols [['ZRXUSDT', 18], ['SUPERUSDT', 18], ['MASKUSDT', 18], ['KNCUSDT', 18], ['BANDUSDT', 18], ['1000000BOBUSDT', 12]]
- `f_mom_7d`: 2020: 0/0/0.0e+00 | 2021: 0/0/0.0e+00 | 2022: 0/0/0.0e+00 | 2023: 0/0/0.0e+00 | 2024: 0/0/0.0e+00 | 2025: 0/0/0.0e+00 | 2026: 2694/0/3.9e-01; top symbols [['ZRXUSDT', 18], ['SUPERUSDT', 18], ['MASKUSDT', 18], ['KNCUSDT', 18], ['BANDUSDT', 18], ['1000000BOBUSDT', 12]]
- `f_mom_30d`: 2020: 0/0/0.0e+00 | 2021: 0/0/0.0e+00 | 2022: 0/0/0.0e+00 | 2023: 0/0/0.0e+00 | 2024: 0/0/0.0e+00 | 2025: 0/0/0.0e+00 | 2026: 2694/0/3.9e-01; top symbols [['ZRXUSDT', 18], ['SUPERUSDT', 18], ['MASKUSDT', 18], ['KNCUSDT', 18], ['BANDUSDT', 18], ['1000000BOBUSDT', 12]]
- `f_mom_7d_x24`: 2020: 0/0/0.0e+00 | 2021: 0/0/0.0e+00 | 2022: 0/0/0.0e+00 | 2023: 0/0/0.0e+00 | 2024: 0/0/0.0e+00 | 2025: 0/0/0.0e+00 | 2026: 1362/0/2.8e-01; top symbols [['ZRXUSDT', 12], ['SUPERUSDT', 12], ['MASKUSDT', 12], ['KNCUSDT', 12], ['BANDUSDT', 12], ['1000000BOBUSDT', 6]]
- `f_vol_7d`: 2020: 0/0/0.0e+00 | 2021: 0/0/0.0e+00 | 2022: 0/0/0.0e+00 | 2023: 0/0/0.0e+00 | 2024: 0/0/0.0e+00 | 2025: 0/0/0.0e+00 | 2026: 2726/0/2.8e-03; top symbols [['ZRXUSDT', 18], ['SUPERUSDT', 18], ['MASKUSDT', 18], ['KNCUSDT', 18], ['BANDUSDT', 18], ['1000000BOBUSDT', 12]]
- `f_volq_ratio`: 2020: 0/0/0.0e+00 | 2021: 0/0/0.0e+00 | 2022: 0/0/0.0e+00 | 2023: 0/0/0.0e+00 | 2024: 0/0/0.0e+00 | 2025: 0/0/0.0e+00 | 2026: 2694/0/4.6e+00; top symbols [['ZRXUSDT', 18], ['SUPERUSDT', 18], ['MASKUSDT', 18], ['KNCUSDT', 18], ['BANDUSDT', 18], ['1000000BOBUSDT', 12]]
- `f_amihud_24h`: 2020: 0/0/0.0e+00 | 2021: 0/0/0.0e+00 | 2022: 0/0/0.0e+00 | 2023: 0/0/0.0e+00 | 2024: 0/0/0.0e+00 | 2025: 0/0/0.0e+00 | 2026: 1314/1380/3.0e+02; top symbols [['ZRXUSDT', 18], ['SUPERUSDT', 18], ['MASKUSDT', 18], ['KNCUSDT', 18], ['BANDUSDT', 18], ['1000000BOBUSDT', 12]]
- `f_range_24h`: 2020: 0/0/0.0e+00 | 2021: 0/0/0.0e+00 | 2022: 0/0/0.0e+00 | 2023: 0/0/0.0e+00 | 2024: 0/0/0.0e+00 | 2025: 0/0/0.0e+00 | 2026: 2694/0/2.3e-02; top symbols [['ZRXUSDT', 18], ['SUPERUSDT', 18], ['MASKUSDT', 18], ['KNCUSDT', 18], ['BANDUSDT', 18], ['1000000BOBUSDT', 12]]
- `f_cpos_24h`: 2020: 0/0/0.0e+00 | 2021: 0/0/0.0e+00 | 2022: 0/0/0.0e+00 | 2023: 0/0/0.0e+00 | 2024: 0/0/0.0e+00 | 2025: 0/0/0.0e+00 | 2026: 2694/0/8.0e-01; top symbols [['ZRXUSDT', 18], ['SUPERUSDT', 18], ['MASKUSDT', 18], ['KNCUSDT', 18], ['BANDUSDT', 18], ['1000000BOBUSDT', 12]]
- `f_tbf_24h`: 2020: 0/0/0.0e+00 | 2021: 0/0/0.0e+00 | 2022: 0/0/0.0e+00 | 2023: 0/0/0.0e+00 | 2024: 0/0/0.0e+00 | 2025: 0/0/0.0e+00 | 2026: 2694/0/6.9e-01; top symbols [['ZRXUSDT', 18], ['SUPERUSDT', 18], ['MASKUSDT', 18], ['KNCUSDT', 18], ['BANDUSDT', 18], ['1000000BOBUSDT', 12]]
- `f_asz_24h`: 2020: 0/0/0.0e+00 | 2021: 0/0/0.0e+00 | 2022: 0/0/0.0e+00 | 2023: 0/0/0.0e+00 | 2024: 0/0/0.0e+00 | 2025: 0/0/0.0e+00 | 2026: 2694/0/7.3e+00; top symbols [['ZRXUSDT', 18], ['SUPERUSDT', 18], ['MASKUSDT', 18], ['KNCUSDT', 18], ['BANDUSDT', 18], ['1000000BOBUSDT', 12]]
- `f_fund_now`: 2020: 0/19136/0.0e+00 | 2021: 0/96882/0.0e+00 | 2022: 0/113930/0.0e+00 | 2023: 0/160652/0.0e+00 | 2024: 0/245209/0.0e+00 | 2025: 0/316990/0.0e+00 | 2026: 0/202688/0.0e+00; top symbols [['EOSUSDT', 14329], ['KNCUSDT', 13469], ['ZRXUSDT', 13457], ['BANDUSDT', 13247], ['ICXUSDT', 12963], ['MATICUSDT', 12737]]
- `f_fund_iv`: 2020: 0/19136/0.0e+00 | 2021: 0/96882/0.0e+00 | 2022: 0/113930/0.0e+00 | 2023: 0/160652/0.0e+00 | 2024: 0/245209/0.0e+00 | 2025: 0/316990/0.0e+00 | 2026: 138/202688/3.0e+00; top symbols [['EOSUSDT', 14329], ['KNCUSDT', 13469], ['ZRXUSDT', 13457], ['BANDUSDT', 13247], ['ICXUSDT', 12963], ['MATICUSDT', 12737]]
- `f_fund_ema`: 2020: 0/19136/0.0e+00 | 2021: 0/96882/0.0e+00 | 2022: 0/113930/0.0e+00 | 2023: 0/160652/0.0e+00 | 2024: 0/245209/0.0e+00 | 2025: 0/316990/0.0e+00 | 2026: 0/202688/0.0e+00; top symbols [['EOSUSDT', 14329], ['KNCUSDT', 13469], ['ZRXUSDT', 13457], ['BANDUSDT', 13247], ['ICXUSDT', 12963], ['MATICUSDT', 12737]]
- `f_fund_ema_v1`: 2020: 0/19136/0.0e+00 | 2021: 0/96882/0.0e+00 | 2022: 0/113930/0.0e+00 | 2023: 0/160652/0.0e+00 | 2024: 0/245209/0.0e+00 | 2025: 0/316990/0.0e+00 | 2026: 324/202688/5.1e-03; top symbols [['EOSUSDT', 14329], ['KNCUSDT', 13469], ['ZRXUSDT', 13457], ['BANDUSDT', 13247], ['ICXUSDT', 12963], ['MATICUSDT', 12737]]
- `f_fund_ema_v2`: 2020: 0/19136/0.0e+00 | 2021: 0/96882/0.0e+00 | 2022: 0/113930/0.0e+00 | 2023: 0/160652/0.0e+00 | 2024: 0/245209/0.0e+00 | 2025: 0/316990/0.0e+00 | 2026: 316/202688/4.5e-02; top symbols [['EOSUSDT', 14329], ['KNCUSDT', 13469], ['ZRXUSDT', 13457], ['BANDUSDT', 13247], ['ICXUSDT', 12963], ['MATICUSDT', 12737]]

Y4 hand check from raw zips: [{"anchor": "2026-08-14 20:00", "symbol": "QCOMUSDT", "rebuilt": -0.0022832155227661133, "v1": NaN, "hand_from_raw_zips": -0.0022832155227661133, "n_finite_bars": 48, "n_close_rows_found": 49}, {"anchor": "2026-08-15 00:00", "symbol": "CHESSUSDT", "rebuilt": 0.0, "v1": NaN, "hand_from_raw_zips": 0.0, "n_finite_bars": 48, "n_close_rows_found": 49}, {"anchor": "2026-08-14 12:00", "symbol": "ZESTUSDT", "rebuilt": 0.016560733318328857, "v1": NaN, "hand_from_raw_zips": 0.016560733318328857, "n_finite_bars": 48, "n_close_rows_found": 49}, {"anchor": "2026-08-13 04:00", "symbol": "ANTHROPICUSDT", "rebuilt": 0.006886780261993408, "v1": NaN, "hand_from_raw_zips": 0.006886780261993408, "n_finite_bars": 48, "n_close_rows_found": 49}, {"anchor": "2026-08-13 20:00", "symbol": "ORBSUSDT", "rebuilt": 0.0, "v1": NaN, "hand_from_raw_zips": 0.0, "n_finite_bars": 48, "n_close_rows_found": 49}, {"anchor": "2026-08-14 20:00", "symbol": "KSTRUSDT", "rebuilt": 0.0032274723052978516, "v1": NaN, "hand_from_raw_zips": 0.0032274723052978516, "n_finite_bars": 48, "n_close_rows_found": 49}]

## Meta vs 08-21 meta (informational)

E_ts equal True (12985 vs 12985; 2020-09-11 20:00..2026-08-15 20:00 vs 2020-09-11 20:00..2026-08-15 20:00); names equal True; members equal 12967/12985; y4 unequal 0 nan-mismatch 6348; qvk unequal 3836; BITWISE_ALL False

## King rebuilt vs 08-21 king (informational)

| year | n anchors | finite frac rebuilt/ref | finite mask equal | Pearson(pred) | bitwise share | IC rebuilt | IC ref |
|---|---|---|---|---|---|---|---|
| 2020 | 667 | 0.0000/0.0000 | True | nan | nan | +nan | +nan |
| 2021 | 2190 | 0.0000/0.0000 | True | nan | nan | +nan | +nan |
| 2022 | 2190 | 0.1679/0.1679 | True | 0.8527 | 0.0000 | +0.0625 | +0.0603 |
| 2023 | 2190 | 0.2260/0.2260 | True | 0.8586 | 0.0000 | +0.0550 | +0.0557 |
| 2024 | 2196 | 0.3304/0.3304 | True | 0.8552 | 0.0000 | +0.0605 | +0.0621 |
| 2025 | 2190 | 0.4681/0.4681 | True | 0.8095 | 0.0000 | +0.0637 | +0.0617 |
| 2026 | 1362 | 0.4825/0.4825 | False | 0.8723 | 0.0000 | +0.0582 | +0.0580 |

fold IC (script json): rebuilt {'2022': 0.0625, '2023': 0.055, '2024': 0.0605, '2025': 0.0637, '2026': 0.0582} vs 08-21 {'2022': 0.0603, '2023': 0.0557, '2024': 0.0621, '2025': 0.0617, '2026': 0.058}

## G4 leakage battery detail

- (i) fold 2022: train 2857 anchors, max(train E_ts)+4h = 2022-01-01 00:00 ≤ first test 2022-01-01 00:00 (gap 0 s), overlap False → PASS
- (i) fold 2023: train 5047 anchors, max(train E_ts)+4h = 2023-01-01 00:00 ≤ first test 2023-01-01 00:00 (gap 0 s), overlap False → PASS
- (i) fold 2024: train 7237 anchors, max(train E_ts)+4h = 2024-01-01 00:00 ≤ first test 2024-01-01 00:00 (gap 0 s), overlap False → PASS
- (i) fold 2025: train 9433 anchors, max(train E_ts)+4h = 2025-01-01 00:00 ≤ first test 2025-01-01 00:00 (gap 0 s), overlap False → PASS
- (i) fold 2026: train 11623 anchors, max(train E_ts)+4h = 2026-01-01 00:00 ≤ first test 2026-01-01 00:00 (gap 0 s), overlap False → PASS
- (ii) pre-2022 anchors 2857 with finite cells 0; finite mask == member∧finite(y4) for 10128/10128 anchors; unused anchors with values 0 → PASS
- (vi) ret5_sum_48_v: window [E-w,E-1] bitwise 100/100; shifted window [E-w+1,E] differs in 94/100
- (vi) range_mean_288_v: window [E-w,E-1] bitwise 100/100; shifted window [E-w+1,E] differs in 86/100
- (vi) vol_2016_v: window [E-w,E-1] bitwise 100/100; shifted window [E-w+1,E] differs in 20/100
- (vi) → PASS
- (iii) shuffle-future null (per seed × fold): s0/2022: null -0.0013 vs 2·SE 0.0061 (true +0.0625) PASS; s0/2023: null +0.0022 vs 2·SE 0.0059 (true +0.0550) PASS; s0/2024: null -0.0002 vs 2·SE 0.0054 (true +0.0605) PASS; s0/2025: null -0.0027 vs 2·SE 0.0052 (true +0.0637) PASS; s0/2026: null +0.0046 vs 2·SE 0.0052 (true +0.0582) PASS; s1/2022: null +0.0081 vs 2·SE 0.0061 (true +0.0625) FAIL; s1/2023: null -0.0031 vs 2·SE 0.0059 (true +0.0550) PASS; s1/2024: null +0.0014 vs 2·SE 0.0054 (true +0.0605) PASS; s1/2025: null -0.0026 vs 2·SE 0.0052 (true +0.0637) PASS; s1/2026: null +0.0021 vs 2·SE 0.0052 (true +0.0582) PASS; s2/2022: null +0.0070 vs 2·SE 0.0061 (true +0.0625) FAIL; s2/2023: null -0.0023 vs 2·SE 0.0059 (true +0.0550) PASS; s2/2024: null +0.0022 vs 2·SE 0.0054 (true +0.0605) PASS; s2/2025: null -0.0034 vs 2·SE 0.0052 (true +0.0637) PASS; s2/2026: null +0.0098 vs 2·SE 0.0052 (true +0.0582) FAIL → FAIL
  - information (not the gate): 2022: seed-mean null +0.0046, 2·SE_anchor 0.0061, 2·SE_dayblock 0.0064; 2023: seed-mean null -0.0011, 2·SE_anchor 0.0059, 2·SE_dayblock 0.0061; 2024: seed-mean null +0.0011, 2·SE_anchor 0.0054, 2·SE_dayblock 0.0054; 2025: seed-mean null -0.0029, 2·SE_anchor 0.0052, 2·SE_dayblock 0.0049; 2026: seed-mean null +0.0055, 2·SE_anchor 0.0052, 2·SE_dayblock 0.0059
- (iv) offset spectrum k=-6..6: -6:-0.0545 -5:-0.0564 -4:-0.0587 -3:-0.0633 -2:-0.0713 -1:-0.1185 0:+0.0601 1:+0.0466 2:+0.0401 3:+0.0369 4:+0.0355 5:+0.0352 6:+0.0314; peak k=0, max|corr(k=1..3)|=0.0466 < corr(0)=0.0601 → PASS (n anchors 10128)
- (v) fold 2024: IC no-embargo refit +0.06051 (stage-5 file +0.06051, refit==file True), embargo-60 +0.05938, Δ -0.00113 → PASS
- (v) fold 2025: IC no-embargo refit +0.06371 (stage-5 file +0.06371, refit==file True), embargo-60 +0.06417, Δ +0.00046 → PASS

## G2 attribution

- ATTR(1) device form (same meta/panel/king; w10 recheck device vs pod_stop_arms_v3): common 12279, max|Δ| 5.62e+01 bps, mean Δ -0.0738, corr 0.9846; by year Δ: 2021 +0.002, 2022 +0.001, 2023 -0.017, 2024 -0.019, 2025 -0.136, 2026 -0.396
- ATTR(2) inputs (stage-6 rebuilt nets vs real 08-21 nets): common 12279, max|Δ| 9.90e+01, mean Δ -0.2372, corr 0.9275; by year (stage6/0821): 2021 -1.876/-1.777, 2022 +0.790/+0.856, 2023 +0.078/+0.429, 2024 +0.180/+0.404, 2025 +0.947/+1.206, 2026 +2.432/+2.971
- ATTR(3) gross: step-8 gross_total mean 0.7374 vs 08-21 implied 0.7939
- G2(b) by year (step8 per-gross / 08-21 per-gross / Δ): 2022 +1.019/+1.379/-0.361, 2023 +0.054/+0.580/-0.526, 2024 +0.355/+0.585/-0.230, 2025 +1.205/+1.471/-0.266, 2026 +2.279/+2.317/-0.037

## DIAGNOSTIC for G2(a) (not a gate, not a G5 arm)

- v1 funding symbols 450 vs rebuilt 829; 08-21 king re-indexed: 12985/12985 anchors (grids identical True)
- residual funding mismatch after masking to the 450 symbols: f_fund_now: unequal 0, nan-mismatch 4472, max|Δ| 0.0e+00; f_fund_iv: unequal 138, nan-mismatch 4472, max|Δ| 3.0e+00; f_fund_ema: unequal 0, nan-mismatch 4472, max|Δ| 0.0e+00; f_fund_ema_v1: unequal 324, nan-mismatch 4472, max|Δ| 5.1e-03; f_fund_ema_v2: unequal 316, nan-mismatch 4472, max|Δ| 4.5e-02
- DIAG-A (funding masked to 08-21 coverage + real 08-21 king) `nets_diagA_-30_2_42.npy`: n 12279/12279 (first 2021-01-06 16:00 vs 2021-01-06 16:00), bitwise 0.7637, max|Δ| 7.98e+00, mean Δ -0.0041, corr 0.99998; by year diag/0821 (bitwise share): 2021 -1.777/-1.777 (0.91), 2022 +0.858/+0.856 (0.32), 2023 +0.429/+0.429 (0.74), 2024 +0.404/+0.404 (1.00), 2025 +1.206/+1.206 (0.79), 2026 +2.931/+2.971 (0.85)
- DIAG-A (funding masked to 08-21 coverage + real 08-21 king) `nets_diagA_0_0_0.npy`: n 12279/12279 (first 2021-01-06 16:00 vs 2021-01-06 16:00), bitwise 0.7642, max|Δ| 7.00e+00, mean Δ -0.0037, corr 0.99998; by year diag/0821 (bitwise share): 2021 -2.038/-2.038 (0.91), 2022 +0.700/+0.699 (0.32), 2023 +0.328/+0.328 (0.74), 2024 +0.382/+0.382 (1.00), 2025 +1.107/+1.107 (0.79), 2026 +2.885/+2.921 (0.85)
- DIAG-B (rebuilt 829-symbol funding + real 08-21 king) `nets_diagB_-30_2_42.npy`: n 12279/12279 (first 2021-01-06 16:00 vs 2021-01-06 16:00), bitwise 0.0000, max|Δ| 9.65e+01, mean Δ -0.1650, corr 0.94506; by year diag/0821 (bitwise share): 2021 -1.876/-1.777 (0.00), 2022 +0.791/+0.856 (0.00), 2023 +0.111/+0.429 (0.00), 2024 +0.197/+0.404 (0.00), 2025 +1.135/+1.206 (0.00), 2026 +2.702/+2.971 (0.00)
- DIAG-B (rebuilt 829-symbol funding + real 08-21 king) `nets_diagB_0_0_0.npy`: n 12279/12279 (first 2021-01-06 16:00 vs 2021-01-06 16:00), bitwise 0.0000, max|Δ| 9.67e+01, mean Δ -0.1503, corr 0.95154; by year diag/0821 (bitwise share): 2021 -2.049/-2.038 (0.00), 2022 +0.630/+0.699 (0.00), 2023 -0.013/+0.328 (0.00), 2024 +0.117/+0.382 (0.00), 2025 +1.001/+1.107 (0.00), 2026 +2.841/+2.921 (0.00)

## G3 detail

- (b3) Σ-simple[E,E+47] − Π(1+r)−1[E+1,E+48], cell level per year (bps): 2020: +0.579 (|·| 35.91, n 46708); 2021: +1.656 (|·| 46.49, n 249993); 2022: +0.464 (|·| 29.51, n 316546); 2023: +0.299 (|·| 21.85, n 434966); 2024: +0.274 (|·| 25.48, n 645818); 2025: +0.756 (|·| 28.81, n 1069449); 2026: +0.223 (|·| 25.28, n 937159)
- (b2) worst cells: [{"anchor": "2023-08-17 20:00", "symbol": "THETAUSDT", "y4s": -0.07914084941148758, "raw": -0.07905727923627692, "y4old": -0.0690145492553711, "year": 2023, "clipped": false, "f16_bound": 0.00018803074276341496, "abs_diff": 8.357316255569458e-05}, {"anchor": "2021-09-07 12:00", "symbol": "BZRXUSDT", "y4s": -0.17895668745040894, "raw": -0.1788765208387264, "y4old": -0.13731002807617188, "year": 2021, "clipped": false, "f16_bound": 0.0006587846838579126, "abs_diff": 8.016824722290039e-05}, {"anchor": "2021-07-18 16:00", "symbol": "CHRUSDT", "y4s": 0.08602378517389297, "raw": 0.08598452278589841, "y4old": 0.08795785903930664, "year": 2021, "clipped": false, "f16_bound": 0.00026563661828034926, "abs_diff": 3.9264559745788574e-05}]

## Adapter receipts

- pinned king re-indexed onto the hist grid: src 158cd4ac8f8f30f7 shape [10176, 829] → [12985, 829], mapped 10086 anchors, rows bitwise equal 10086/10086; finite by year {'2020': 0.0, '2021': 0.0, '2022': 0.0, '2023': 0.0, '2024': 0.33035500449331057, '2025': 0.46808389929000666, '2026': 0.4825090470446321}
- prod-caliber meta: oldsum vs meta y4 exact_eq 1.0, newprod vs dlw y4s exact_eq 1.0 (cells 3700640), per-year Π−Σ (bps): 2020 -0.579, 2021 -1.656, 2022 -0.464, 2023 -0.299, 2024 -0.274, 2025 -0.756, 2026 -0.223

## Patches (logs/patches/*.diff) and key file hashes

| file | sha256 | size |
|---|---|---|
| 08_setup_dev.diff | 6e1f4f1d2b312940 | 4306 |
| 10_G5_arms.diff | 9d72b87c994a7037 | 4954 |
| dl_klines_fast.diff | c24a1975e6606c88 | 1614 |
| dl_klines_paced.diff | 5c7d46b53ea58a3b | 10328 |
| judge_rebuild.diff | 5a0ccaec85d3aa47 | 27930 |
| pod_build_wide_ext.py.diff | adeed9f959aa8c42 | 2588 |
| pod_fea_wide_hist.py.diff | 3ac2fd9873c2ae8f | 3185 |
| pod_panel_ext.py.diff | 7b9f6fa765fc15a1 | 1278 |
| pod_slow_hist_folds.py.diff | 9b55534c536312a7 | 2001 |
| pod_stop_arms_v3.py.diff | 03e8c3f08ee09998 | 2296 |
| data/dlnative_5m_wide829_f16_hist.npz | 5d5fd0f2f7622465 | 2290946807 |
| data/wide_panel_4h_hist_v2_rebuilt.npz | 9f3e4ae14ef9ff1e | 259081104 |
| data/wide_fea_hist_rebuilt.npy | 3568c673b274959b | 1765388788 |
| data/wide_fea_hist_meta_rebuilt.npz | 509d8b5453239391 | 27831856 |
| data/slow_pred_hist_oos_rebuilt.npy | 1090418fa793f87c | 43058388 |
| data/nets_histv2_-30_2_42.npy | c1eaca5318a911a5 | 196592 |
| data/nets_histv2_0_0_0.npy | b56d7c61917423ed | 196592 |
| data/dlw_hist/data/dlw_targets.npz | ba10902ef312bb9c | 240180930 |
| data/meta_hist_newprod.npz | 60af00925262f3db | 110685571 |
| data/slow_pred_pinned_on_hist.npy | f48b57f9aff20dce | 43058388 |
| logs/klines5m_SHA256SUMS.txt | 1cf680ab883e0602 | 3625156 |
| logs/klines5m_404.txt | 4ef3553af5d2d6f3 | 2093168 |
