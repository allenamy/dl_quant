> **创建:** 2026-09-13 15:xxZ | **Session:** https://claude.ai/code/session_01BzpuBRGZh8oPvpD8NgqsME (aud-prod, auditor teammate, read-only) | **状态:** 审计登记册(只读; 未改任何实盘文件; 由 devices_prod/build/build_audit_prod.py 从已提交收据生成) | **作废条件:** shadow_loop_v3.py ≠ e9c98374、combo_stage.py ≠ b5c698f9、bundle MANIFEST 或 slow2026.txt ≠ 8d79186b、f10_live_s42_np.npz ≠ 351ae26b、任一被引收据 sha 改变,或任一登记项被修复/裁定后需差异复核

# AUDIT_PROD — producer and model-serving layer (read-only, 2026-09-13)

Companion data: `AUDIT_PROD.json` (same register, same wording) and `AUDIT_PROD_columns.csv` (every king and V2MAIN input column: definition sources, classification, measured statistics).

## 0. What was audited, frozen at what

| Object | Value |
|---|---|
| shadow_loop_v3.py (serving) | `e9c9837412130884bc72d4bbcb52b33e9dc8660274b76ae68f46639d2d21b36e` |
| combo_stage.py (serving) | `b5c698f9d1ee9acb73c9bf5f3a1e15843d3298e95a810ebf0107a7d68c6ee358` |
| dlw_features.py (serving) | `29ae6a985d891e56340378bb432c0370e914b93709eec44f54592472e4d20a76` |
| f8_higher_order_features.py (serving) | `2c500c7ad2bb0f5ddccf431021df50a106a39f4d228bd6cf2d074c5c12f66a5f` |
| slow2026.txt (serving) | `8d79186b6380132cb67684acf1ebfcdb2c53261c850f46a4908b06bfa7a81282` |
| config.json (serving) | `3a8422f377519cac77b0c42305d2ba40a4b7a42a830f0542bda844f66647c94e` |
| f10_live_s42_np.npz (serving) | `351ae26bd6b4a203431a280427fc0bbc968c66e903532168765d654e7e57b3a4` |
| pod_fea_ext.py (training; pod2 runtime copy has the same sha, receipts_prod/pod2_provenance.txt) | `02157bda4fe0f6cd6f42215a0a5551b819b817249de4d3ffda26a2963e6a0378` |
| pod_fea_ext_clamp.py (training; pod2 runtime copy has the same sha, receipts_prod/pod2_provenance.txt) | `b9f9c72816241715fc4b767950420e74f50adbbbcfc4ea77b362407ab5efa4ac` |
| pod_dlw_features_ext.py (training; pod2 runtime copy has the same sha, receipts_prod/pod2_provenance.txt) | `e86725cc2768bb6265dd8fb2b3580629706166da012298768b1c0788e8f5a624` |
| pod_f8_build_ext.py (training; pod2 runtime copy has the same sha, receipts_prod/pod2_provenance.txt) | `f606bffa620004f69ace3704ca19d8f3643b764e918f5eea5a4575b40587f07e` |
| pod_dlw_targets_ext.py (training; pod2 runtime copy has the same sha, receipts_prod/pod2_provenance.txt) | `c21683ee23b775b46d927b9b606418d3039379f9fc279c027119fd36d73bce89` |
| pod_panel_ext.py (training; pod2 runtime copy has the same sha, receipts_prod/pod2_provenance.txt) | `db7f0474b64fb3098a8d1a6af29f61423d7b99c74c6834eb6424b77d1642b5ac` |
| pod_export_bundle_v3.py (training; pod2 runtime copy has the same sha, receipts_prod/pod2_provenance.txt) | `c210bac649071e30530147e4b808f662d87e07ad521eaadb307b3453c348dc6a` |
| pod_f10_refit_ext.py (training; pod2 runtime copy has the same sha, receipts_prod/pod2_provenance.txt) | `ea3675b8012ea266646571f6e1550f248d894cae832b190a8beab27befab9fb7` |
| Training-side data compared | x0910 extension: king features 048ea709…, DL targets 5b628413…, fea82 e8377803…, fea89 d4a33cc3…, cache 81152994… (receipts_prod/parity_x0910_extract.json) |
| Served inputs compared | T4 served records 942d20a9… (41 anchors) + T4b served records 6f121afe… (6 anchors); live rolling cache copy 9ef804fe… (after the 12Z anchor) |
| Running processes | com.hsy.shadowloop PID 10900 (since 09-05 12:47Z), com.hsy.combolive PID 30944, com.hsy.sidecar PID 30943 (receipts_prod/runtime_processes.txt) |
| Research branch | research/book-uplift-2026-09-11 |

Constraints kept: ~/wide_shadow and ~/dl_quant_live only read (production feature code executed from sha-checked copies or from file text, bytecode writing disabled); no exchange API call; Mac devices refused to start inside N+10..N+55 of an anchor; pod2 CPU only, nice 19, ≤ 8 cores, PIDs 333197/339489 untouched, dd probe before the extraction write; bulky data in ~/cc_tmp/aud_prod; every device committed before it ran (failed first runs kept and named).

Status legend: **FIXED_DEPLOYED** fix running; **VERIFIED_IMMATERIAL** checked, no effect at the stated resolution; **OPEN_MEASURED_MATERIAL** defect confirmed with numbers; **OPEN_NOT_MEASURED** mechanism confirmed, size not measured; **PENDING_USER_DECISION** needs a ruling or an experiment readout; **DOC_STALE** code/state right, a document is wrong. Method: VERIFIED = computed or read in this audit; CITED = taken from a named receipt; INFERRED = reasoning, not measured.

## 1. Result

**P0: 0. P1: 0.** No item reaches P1: nothing found changes the live book without a ruling today; the largest findings are model-input representation gaps measured at the score layer (PROD-01/02/03, PROD-06..09) whose book-layer size is unmeasured.

| Status | Count |
|---|---:|
| FIXED_DEPLOYED | 0 |
| VERIFIED_IMMATERIAL | 9 |
| OPEN_MEASURED_MATERIAL | 11 |
| OPEN_NOT_MEASURED | 4 |
| PENDING_USER_DECISION | 3 |
| DOC_STALE | 4 |
| **Total** | **31** |

By severity: P0 0, P1 0, P2 11, P3 20.

## 2. Short answers

1. **Column-by-column definition parity** (`AUDIT_PROD_columns.csv`, 82 king builder columns + 171 V2MAIN columns). King (78 served): 77 DIFFERENT, 1 EQUIVALENT_FORMULA (fund_now), 4 builder columns not served. Every kline column differs in timestamp alignment (PROD-01) and float16 storage (PROD-05); every rank column also in cross-section universe (PROD-02); column 80 in unit (PROD-04). V2MAIN (171): 40 IDENTICAL_CODE, 2 EQUIVALENT_FORMULA, 129 DIFFERENT. The serving feature code is the training builder with only path constants changed (dlw_features L16; f8 L17-23); the differences are inputs to that code: member universe for every rank (PROD-06), the scored anchor's members reused on history rows (PROD-07), btcv definition (PROD-08), cache length in the two trend columns (PROD-09), column 80/81 unit and fill (PROD-37, T4b). No column is UNVERIFIABLE: every served column was reproduced bitwise from production code and every training column from the training builders.
2. **Measured** (feature and score layers, no P&L). King, 32 anchors: stored training features vs served inputs on the same names → king-score Spearman median 0.9353 (PROD-03); training clock alone 0.9843 (PROD-01); rank universe alone 0.9470 (PROD-02); float16 alone ~1.0 (PROD-05). V2MAIN, 17 anchors: stored training rows vs served inputs → V2MAIN-score Spearman median 0.9824 (PROD-06); history-member approximation alone 0.9998 (PROD-07); training code on training members reproduces the stored rows except the trend columns (G-F10CODE, PROD-09).
3. **Membership and liquidity.** Production members = top 400 of the live 450; training members (king and DL, identical sets) = top 400 of all 829 cache names: Jaccard median 0.660, the whole difference is the universe (PROD-02, PROD-11). A0 replay members = 373 masked crypto names: overlap 332/400 (PROD-10). qv4h is the same quantity in production and A0 (PROD-12).
4. **Serving-state artefacts.** Seat: 819 of 900 window rows are the 09-05 seed (PROD-20; no re-seeding step for October, PROD-21). D17: decaying, immaterial, not recurring (PROD-22); the builder interval rule that caused it is still live in research builders (PROD-23) and FX-PROD P9 is a separate live append defect (PROD-40). FTRIM residual and band freeze (PROD-24). Uniform redistribution after withholding: EXE-03 confirmed and generalised (PROD-25).
5. **Follow-ups from the lead.** P3 qv4h: PROD-12. P4 other-feature parity: PROD-01..03, PROD-06..09, PROD-37. P10 float16 train / float32 serve: PROD-05 (no served decile or selection change; 4 of 18,800 row paths). FTRIM as served: PROD-24; stop overlay as served: PROD-32 (the served stop is the executor's per_name_stop). EXE-03: confirmed, PROD-25. CHK-01: confirmed with mechanism, PROD-26. Phase-1 G-P2 residual mechanism: PROD-36.

## 3. Column parity (appendix CSV has every column)

### 3.1 King (8d79186b), 78 served columns, ordered by booster gain rank

Columns: gain rank · name · class · share of common cells with |Δ| > 1e-3 (served vs stored training; relative for values, rank units for ranks) · per-anchor Spearman served vs stored · Spearman training clock vs serving clock · median |Δrank| from the universe (ranks only) · king-score Spearman when only this column takes the training clock · deciles changed (median, of 400) · rows whose leaf path changes if only this column is cast to float16 (47 anchors).

| gain | column | class | >1e-3 share | Spearman S vs T | Spearman clock | universe |Δrank| | score Spearman (clock swap) | deciles | P10 rows |
|---:|---|---|---:|---:|---:|---:|---:|---:|---:|
| 1 | range_mean_48_r | DIFFERENT | 0.933 | 0.9992 | 0.9991 | 0.018 | 0.99955 | 10 | 0 |
| 2 | ret5_sum_864_r | DIFFERENT | 0.916 | 0.9981 | 0.9979 | 0.015 | 0.99856 | 27 | 0 |
| 3 | vol_48_r | DIFFERENT | 0.939 | 0.9987 | 0.9983 | 0.020 | 0.99986 | 6 | 0 |
| 4 | cpos_mean_48_v | DIFFERENT | 0.939 | 0.9788 | 0.9804 | 0.000 | 0.99784 | 27 | 1 |
| 5 | vol_288_r | DIFFERENT | 0.920 | 0.9999 | 0.9999 | 0.015 | 0.99998 | 2 | 0 |
| 6 | cpos_mean_48_r | DIFFERENT | 0.978 | 0.9787 | 0.9804 | 0.020 | 0.99673 | 46 | 0 |
| 7 | fund_ema | DIFFERENT | 0.636 | 0.8462 |  |  |  |  | 0 |
| 8 | ret5_sum_864_v | DIFFERENT | 0.962 | 0.9981 | 0.9979 | 0.000 | 0.99987 | 6 | 0 |
| 9 | ret5_sum_2016_v | DIFFERENT | 0.951 | 0.9993 | 0.9992 | 0.000 | 0.99989 | 4 | 0 |
| 10 | fund_now | EQUIVALENT_FORMULA | 0.028 | 1.0000 |  |  |  |  | 0 |
| 11 | cpos_mean_288_v | DIFFERENT | 0.742 | 0.9977 | 0.9978 | 0.000 | 0.99985 | 6 | 0 |
| 12 | ret5_sum_2016_r | DIFFERENT | 0.917 | 0.9993 | 0.9992 | 0.018 | 0.99983 | 6 | 0 |
| 13 | log_cnt_mean_48_r | DIFFERENT | 0.953 | 0.9998 | 0.9997 | 0.045 | 0.99996 | 2 | 0 |
| 14 | ret5_sum_8640_r | DIFFERENT | 0.928 | 0.9998 | 0.9998 | 0.015 | 0.99997 | 2 | 0 |
| 15 | vol_48_v | DIFFERENT | 0.764 | 0.9987 | 0.9983 | 0.000 | 0.99996 | 2 | 0 |
| 16 | range_mean_288_r | DIFFERENT | 0.889 | 1.0000 | 0.9999 | 0.010 | 1.00000 | 0 | 0 |
| 17 | range_mean_48_v | DIFFERENT | 0.910 | 0.9993 | 0.9991 | 0.000 | 0.99988 | 4 | 0 |
| 18 | range_mean_2016_r | DIFFERENT | 0.941 | 1.0000 | 1.0000 | 0.015 | 1.00000 | 0 | 0 |
| 19 | tbf_mean_48_r | DIFFERENT | 0.970 | 0.9831 | 0.9852 | 0.015 | 0.99947 | 8 | 0 |
| 20 | tbf_mean_48_v | DIFFERENT | 0.923 | 0.9832 | 0.9853 | 0.000 | 0.99940 | 8 | 1 |
| 21 | log_qv_mean_48_r | DIFFERENT | 0.979 | 0.9997 | 0.9997 | 0.095 | 0.99977 | 4 | 0 |
| 22 | cpos_mean_288_r | DIFFERENT | 0.950 | 0.9977 | 0.9977 | 0.015 | 0.99997 | 1 | 0 |
| 23 | cpos_mean_864_v | DIFFERENT | 0.370 | 0.9994 | 0.9994 | 0.000 | 0.99997 | 2 | 0 |
| 24 | ret5_sum_8640_v | DIFFERENT | 0.902 | 0.9998 | 0.9998 | 0.000 | 0.99999 | 2 | 0 |
| 25 | cpos_mean_8640_r | DIFFERENT | 0.956 | 0.9999 | 0.9999 | 0.015 | 0.99998 | 0 | 0 |
| 26 | tbf_mean_288_r | DIFFERENT | 0.964 | 0.9982 | 0.9984 | 0.018 | 0.99987 | 3 | 0 |
| 27 | vol_8640_r | DIFFERENT | 0.954 | 1.0000 | 1.0000 | 0.018 | 1.00000 | 0 | 0 |
| 28 | log_avgsz_mean_48_r | DIFFERENT | 0.993 | 0.9994 | 0.9995 | 0.138 | 0.99995 | 2 | 0 |
| 29 | cpos_mean_2016_r | DIFFERENT | 0.944 | 0.9998 | 0.9998 | 0.015 | 0.99999 | 0 | 0 |
| 30 | tbf_mean_2016_v | DIFFERENT | 0.003 | 0.9998 | 0.9998 | 0.000 | 0.99999 | 0 | 0 |
| 31 | cpos_mean_864_r | DIFFERENT | 0.939 | 0.9994 | 0.9994 | 0.013 | 0.99991 | 4 | 0 |
| 32 | tbf_mean_288_v | DIFFERENT | 0.584 | 0.9982 | 0.9984 | 0.000 | 0.99988 | 4 | 0 |
| 33 | log_avgsz_mean_48_v | DIFFERENT | 0.723 | 0.9994 | 0.9995 | 0.000 | 0.99997 | 2 | 1 |
| 34 | cpos_mean_8640_v | DIFFERENT | 0.000 | 0.9998 | 0.9998 | 0.000 | 1.00000 | 0 | 0 |
| 35 | cpos_mean_2016_v | DIFFERENT | 0.036 | 0.9997 | 0.9997 | 0.000 | 0.99999 | 2 | 0 |
| 36 | vol_2016_v | DIFFERENT | 0.044 | 1.0000 | 1.0000 | 0.000 | 1.00000 | 0 | 0 |
| 37 | log_avgsz_mean_288_v | DIFFERENT | 0.112 | 1.0000 | 1.0000 | 0.000 | 1.00000 | 0 | 0 |
| 38 | tbf_mean_864_r | DIFFERENT | 0.954 | 0.9995 | 0.9996 | 0.017 | 0.99997 | 2 | 0 |
| 39 | tbf_mean_2016_r | DIFFERENT | 0.900 | 0.9998 | 0.9998 | 0.007 | 1.00000 | 0 | 0 |
| 40 | tbf_mean_8640_r | DIFFERENT | 0.977 | 0.9999 | 1.0000 | 0.040 | 1.00000 | 0 | 0 |
| 41 | range_mean_8640_r | DIFFERENT | 0.937 | 1.0000 | 1.0000 | 0.018 | 1.00000 | 0 | 0 |
| 42 | range_mean_864_r | DIFFERENT | 0.899 | 1.0000 | 1.0000 | 0.008 | 1.00000 | 0 | 0 |
| 43 | tbf_mean_864_v | DIFFERENT | 0.142 | 0.9995 | 0.9995 | 0.000 | 0.99997 | 2 | 1 |
| 44 | log_avgsz_mean_8640_v | DIFFERENT | 0.000 | 1.0000 | 1.0000 | 0.000 | 1.00000 | 0 | 0 |
| 45 | range_mean_8640_v | DIFFERENT | 0.002 | 1.0000 | 1.0000 | 0.000 | 1.00000 | 0 | 0 |
| 46 | vol_8640_v | DIFFERENT | 0.008 | 1.0000 | 1.0000 | 0.000 | 1.00000 | 0 | 0 |
| 47 | tbf_mean_8640_v | DIFFERENT | 0.000 | 0.9998 | 0.9999 | 0.000 | 1.00000 | 0 | 0 |
| 48 | log_cnt_mean_48_v | DIFFERENT | 0.708 | 0.9998 | 0.9998 | 0.000 | 1.00000 | 0 | 0 |
| 49 | vol_2016_r | DIFFERENT | 0.948 | 1.0000 | 1.0000 | 0.015 | 1.00000 | 0 | 0 |
| 50 | vol_288_v | DIFFERENT | 0.345 | 0.9999 | 0.9999 | 0.000 | 1.00000 | 0 | 0 |
| 51 | log_avgsz_mean_8640_r | DIFFERENT | 0.993 | 1.0000 | 1.0000 | 0.158 | 1.00000 | 0 | 0 |
| 52 | log_avgsz_mean_864_v | DIFFERENT | 0.003 | 1.0000 | 1.0000 | 0.000 | 1.00000 | 0 | 0 |
| 53 | log_qv_mean_48_v | DIFFERENT | 0.680 | 0.9997 | 0.9997 | 0.000 | 0.99999 | 0 | 0 |
| 54 | range_mean_2016_v | DIFFERENT | 0.048 | 1.0000 | 1.0000 | 0.000 | 1.00000 | 0 | 0 |
| 55 | log_cnt_mean_8640_r | DIFFERENT | 0.985 | 1.0000 | 1.0000 | 0.052 | 1.00000 | 0 | 0 |
| 56 | log_avgsz_mean_288_r | DIFFERENT | 0.993 | 1.0000 | 1.0000 | 0.148 | 1.00000 | 0 | 0 |
| 57 | log_avgsz_mean_2016_r | DIFFERENT | 0.994 | 1.0000 | 1.0000 | 0.166 | 1.00000 | 0 | 0 |
| 58 | log_cnt_mean_2016_r | DIFFERENT | 0.948 | 1.0000 | 1.0000 | 0.068 | 1.00000 | 0 | 0 |
| 59 | vol_864_v | DIFFERENT | 0.138 | 1.0000 | 1.0000 | 0.000 | 1.00000 | 0 | 0 |
| 60 | range_mean_864_v | DIFFERENT | 0.213 | 1.0000 | 1.0000 | 0.000 | 1.00000 | 0 | 0 |
| 61 | vol_864_r | DIFFERENT | 0.890 | 1.0000 | 1.0000 | 0.008 | 1.00000 | 0 | 0 |
| 62 | log_avgsz_mean_2016_v | DIFFERENT | 0.000 | 1.0000 | 1.0000 | 0.000 | 1.00000 | 0 | 0 |
| 63 | log_qv_mean_288_v | DIFFERENT | 0.086 | 1.0000 | 1.0000 | 0.000 | 1.00000 | 0 | 0 |
| 64 | log_qv_mean_8640_r | DIFFERENT | 0.990 | 1.0000 | 1.0000 | 0.115 | 1.00000 | 0 | 0 |
| 65 | log_qv_mean_864_r | DIFFERENT | 0.981 | 1.0000 | 1.0000 | 0.108 | 1.00000 | 0 | 0 |
| 66 | log_avgsz_mean_864_r | DIFFERENT | 0.994 | 1.0000 | 1.0000 | 0.165 | 1.00000 | 0 | 0 |
| 67 | range_mean_288_v | DIFFERENT | 0.581 | 1.0000 | 0.9999 | 0.000 | 1.00000 | 0 | 0 |
| 68 | log_cnt_mean_8640_v | DIFFERENT | 0.000 | 1.0000 | 1.0000 | 0.000 | 1.00000 | 0 | 0 |
| 69 | log_cnt_mean_864_r | DIFFERENT | 0.934 | 1.0000 | 1.0000 | 0.058 | 1.00000 | 0 | 0 |
| 70 | log_qv_mean_2016_r | DIFFERENT | 0.984 | 1.0000 | 1.0000 | 0.130 | 1.00000 | 0 | 0 |
| 71 | log_cnt_mean_2016_v | DIFFERENT | 0.000 | 1.0000 | 1.0000 | 0.000 | 1.00000 | 0 | 0 |
| 72 | log_cnt_mean_288_v | DIFFERENT | 0.126 | 1.0000 | 1.0000 | 0.000 | 1.00000 | 0 | 0 |
| 73 | log_qv_mean_8640_v | DIFFERENT | 0.000 | 1.0000 | 1.0000 | 0.000 | 1.00000 | 0 | 0 |
| 74 | log_cnt_mean_864_v | DIFFERENT | 0.003 | 1.0000 | 1.0000 | 0.000 | 1.00000 | 0 | 0 |
| 75 | log_qv_mean_288_r | DIFFERENT | 0.977 | 1.0000 | 1.0000 | 0.095 | 1.00000 | 0 | 0 |
| 76 | log_qv_mean_2016_v | DIFFERENT | 0.000 | 1.0000 | 1.0000 | 0.000 | 1.00000 | 0 | 0 |
| 77 | log_cnt_mean_288_r | DIFFERENT | 0.950 | 1.0000 | 1.0000 | 0.050 | 1.00000 | 0 | 0 |
| 78 | log_qv_mean_864_v | DIFFERENT | 0.001 | 1.0000 | 1.0000 | 0.000 | 1.00000 | 0 | 0 |

### 3.2 V2MAIN (351ae26b), 171 columns by family

Columns with any cell above 1e-3 per comparison (relative for values and H z-scores, absolute for ranks and rank products), and the V2MAIN-score Spearman when the family's columns are swapped from served to stored training values on common names.

| family | columns | served vs stored training | history members (F_S vs F_H) | universe + btcv (F_H vs F_D) | code identity (F_D vs stored) | score Spearman (family swap) |
|---|---:|---:|---:|---:|---:|---:|
| x82_value | 40 | 0 | 0 | 0 | 0 | 1.0000 |
| x82_rank | 40 | 40 | 0 | 40 | 0 | 0.9955 |
| fund | 2 | 2 | 0 | 2 | 0 | 0.9988 |
| A | 10 | 10 | 0 | 10 | 0 | 0.9996 |
| B | 8 | 8 | 0 | 8 | 0 | 0.9992 |
| C | 8 | 8 | 0 | 8 | 2 | 0.9997 |
| D | 9 | 9 | 0 | 9 | 0 | 0.9993 |
| E | 7 | 7 | 0 | 7 | 0 | 0.9983 |
| F | 9 | 9 | 0 | 9 | 0 | 0.9975 |
| G | 8 | 8 | 0 | 8 | 0 | 0.9997 |
| H | 10 | 9 | 5 | 9 | 0 | 0.9995 |
| I | 10 | 10 | 0 | 10 | 0 | 0.9992 |
| J | 10 | 10 | 3 | 10 | 0 | 0.9986 |
| C_trend | 2 | 2 | 0 | 2 | 2 | 0.9999 |
| H_btcv | 5 | 4 | 0 | 4 | 0 | 1.0000 |
| H_disp | 5 | 5 | 5 | 5 | 0 | 0.9995 |
| J_drank | 3 | 3 | 3 | 3 | 0 | 0.9996 |

## 4. Register

### PROD-01 · King kline features are trained on rows [E-w, E-1] and served on rows [E-w+1, E]; the October chain keeps the training clock

- **Layer:** MODEL INPUT / king (clock)  
- **Status:** OPEN_MEASURED_MATERIAL · **Severity:** P2 — About a quarter of king deciles move per anchor at the score layer; the book-layer effect was not detectable at ±0.3 bps/anchor (G3 on v4e) and has not been measured for 8d79186b; no export gate checks the clock.  
- **Affects:** live_trading, future_eval, future_retrain · **Method:** VERIFIED

All 76 served kline columns are computed one 5-minute bar later at serving than in training (the builder's cumulative sums have a leading zero row, the producer slices through the anchor row). On 32 anchors (2026-09-05 16Z..09-10 20Z), scoring the served names with the training clock (served members, float16 store) against the served input gives king-score Spearman median 0.9843 (min 0.9693), deciles changed median 95 of 400 names, top-decile overlap median 0.900 (min 0.800). Largest single columns (served X with one column swapped to the training clock): cpos_mean_48_r (gain rank 6): score Spearman 0.9967, deciles changed 46; cpos_mean_48_v (gain rank 4): score Spearman 0.9978, deciles changed 27; ret5_sum_864_r (gain rank 2): score Spearman 0.9986, deciles changed 27; tbf_mean_48_v (gain rank 20): score Spearman 0.9994, deciles changed 8; tbf_mean_48_r (gain rank 19): score Spearman 0.9995, deciles changed 8; range_mean_48_r (gain rank 1): score Spearman 0.9995, deciles changed 10. Recorded before as E-0909-F: G4 on the v4 booster (Spearman 0.976-0.990), G3 book A1e-A1 UNDECIDED; the clock-corrected v4e export failed the guard band by 0.007. The October chain still builds king features with the training clock.

Evidence:
- pod_fea_ext.py (02157bda) L50/L52/L56 -- training window rows [E-w, E-1]
- shadow_loop_v3.py (e9c98374) L358 (rows [E-w+1, E]) + L397 float32 -- serving window rows [E-w+1, E]
- receipts_prod/parity_king.json (9dbba68b, device file parity_king.py sha256 fad9f3c2): score_arms.TP, pair_stats.clock_TP_vs_TPE, score_clock_substitution_per_column; gates (all bitwise): G-PRED booster(served X) == recorded pred 47/47; G-SREP production code text L355-404 on the live cache reproduces served members + 76 columns 47/47; G-TREP training-builder formula reproduces the stored x0910 features 1,056,000/1,056,000 cells; G-DATA production code on the pod cache (live 450) == served 32/32
- receipts_prod/pod2_provenance.txt: w3_monthly_chain_2026-09-12/device/pod_fea_ext_clamp.py b9f9c728 (= review_scratch copy used by x0910)
- docs/PREREG_king_clock_E_2026-09-09.md AMENDMENT 2-4; docs/HANDOFF_round2_b0a573a1_closure_2026-09-09.md §3 (G3/G4 tables)

Recommended action: Before the October export, put the clock contract to the user: train on the serving clock (pod_fea_ext_e.py, judged with a CI-based book gate rather than the guard band) or serve rows [E-w, E-1]. Add a producer-path raw-feature parity gate to the export (training builder vs producer code on the same anchors, as G-TREP/G-SREP here; cf. AUDIT_TRAIN TRN-18).

### PROD-02 · King rank columns use a different cross-section in training (all 829 cache names) than at serving (live-450 members); 82 of 400 recent training members are outside the live 450

- **Layer:** MODEL INPUT / king (rank universe)  
- **Status:** OPEN_MEASURED_MATERIAL · **Severity:** P2 — Score-layer change larger than the clock effect; it enters every 2026 research king score and any retrain that includes 2026 anchors; book layer not measured.  
- **Affects:** future_eval, future_retrain · **Method:** VERIFIED

On 147 anchors (2026-08-17 04Z..09-10 20Z) production members and king-training members overlap with Jaccard median 0.660; the 82 (median) training-only members are all outside the live 450 (tokenized equities such as AAPLUSDT, AMZNUSDT, ANTHROPICUSDT and non-pinned listings). Restricting the training rule to the live 450 leaves a symmetric difference of median 0 (max 2, the clock); the forward-finite term, the divisor and float32 change 0 names. Ranks of the same names shift (largest median |Δrank|: log_avgsz_mean_2016_r 0.166, log_avgsz_mean_864_r 0.165) while order among common names is kept. Scoring the common names with the two rank sets (training clock on both) gives king-score Spearman median 0.9470 (min 0.8767), deciles changed median 126, top-decile overlap median 0.774. The in-service booster's label years (< 2026) hold 24 non-crypto pairs, all in 2025 (AUDIT_DATA C6), so the live model is served a crypto-only cross-section close to its training years; every 2026 research king score is computed on the stock-inclusive cross-section (7.3% of 2026 member pairs).

Evidence:
- pod_fea_ext.py (02157bda) L75; members L37-39 -- members from every cache name
- shadow_loop_v3.py (e9c98374) L403; members L365-377 -- members among the 450 fetched names
- receipts_prod/members_audit.json (eb8d5da7, device file members_audit.py sha256 7bc0a664): summary.PK, K_not_P_outside_live450, pathK_symdiff_to_P, one_at_a_time_symdiff_vs_P, top_symbols.K_not_P; gates V1/V2/V3 all pass
- receipts_prod/parity_king.json (9dbba68b, device file parity_king.py sha256 fad9f3c2): pair_stats.universe_Trep_vs_TP, score_arms.universe_common
- docs/audit_pipeline_2026-09-13/devices_data/receipts/AD_C_cache_members.json C6_universe_class_in_training_members (king_meta_members 2025 noncrypto_pairs 24; 2026 42,363, share 0.0726)

Recommended action: Use one member universe for training, research replay and serving (the 2026-09-08 CRYPTO-default ruling), applied inside the member rules of pod_fea_ext_clamp.py and pod_dlw_targets_raw.py before the next export; until then label 2026 research king scores 'research cross-section'.

### PROD-03 · Research king inputs at 2026 anchors are not the served inputs: on common names the in-service booster's scores agree with Spearman 0.94, not the 0.994 T4 measured for column 80 alone

- **Layer:** MODEL INPUT / king (research vs served, total)  
- **Status:** OPEN_MEASURED_MATERIAL · **Severity:** P2 — Every replay contrast that treats the research king as the live king, including P2 S2's production-path history, carries this score gap; its book-layer size is unmeasured.  
- **Affects:** future_eval · **Method:** VERIFIED

The stored x0910 training rows (the representation behind A0's pinned king and P2 S2's injected king) re-scored with 8d79186b against the served inputs on the same names: Spearman median 0.9353 (min 0.7602), deciles changed median 144, top-decile overlap median 0.742 (min 0.258); with the served fund columns swapped in: 0.9411. The gap combines PROD-01 (clock), PROD-02 (rank universe) and column 80 (PROD-04).

Evidence:
- receipts_prod/parity_king.json (9dbba68b, device file parity_king.py sha256 fad9f3c2): score_arms.Tstored_common_as_stored, Tstored_common_fund_from_S; gates (all bitwise): G-PRED booster(served X) == recorded pred 47/47; G-SREP production code text L355-404 on the live cache reproduces served members + 76 columns 47/47; G-TREP training-builder formula reproduces the stored x0910 features 1,056,000/1,056,000 cells; G-DATA production code on the pod cache (live 450) == served 32/32
- multi_asset/exports/research/uplift_r2_2026-09-13/T4/RESULT_T4_king_feature_skew_2026-09-13.md §3 (column 80 only: per-anchor Spearman 0.9944)
- docs/PREREG_producer_parity_phase2_oos_2026-09-12.md A2.2 D1 (king OOF injected into the production path)

Recommended action: For production-path replays compute king predictions from producer-definition features (serving clock, serving members, v1 column 80) or label the king arm 'research representation'; add this score contrast to P2's G2-C-BIND.

### PROD-04 · King column 80 fund EMA trained v0, served v1 (H2b / T4)

- **Layer:** MODEL INPUT / king (column 80)  
- **Status:** VERIFIED_IMMATERIAL · **Severity:** P3 — Book effect below ±0.05 bps/anchor at T4's resolution; the defect itself persists.  
- **Affects:** live_trading, future_retrain · **Method:** VERIFIED

Known (T4). Measured here on common names over 32 anchors: served vs stored training value median relative difference 0.500 (4h names served = 2x training), per-anchor Spearman median 0.846. T4 judged the book effect NOT MATERIAL (Δg +0.018 [-0.030, +0.063] bps/anchor, ΔIC -0.0001 ± 0.00017). The October export reintroduces it (AUDIT_TRAIN TRN-04).

Evidence:
- pod_fea_ext.py (02157bda) L61/L80; panel v0 pod_panel_ext.py (db7f0474) L124-133, stale L160
- shadow_loop_v3.py (e9c98374) L344 v1 EMA; L410 fresh<=12h; L418/L419
- receipts_prod/parity_king.json (9dbba68b, device file parity_king.py sha256 fad9f3c2): pair_stats.total_S_vs_T.fund_ema
- uplift_r2_2026-09-13/T4/RESULT_T4_king_feature_skew_2026-09-13.md §0/§5

Recommended action: Decide the column-80 caliber together with PROD-01/PROD-02 before the October export (serve v0 or train v1).

### PROD-05 · King trained on float16-stored features and served float32: no decile or selection change on 47 served anchors; 4 of 18,800 row paths change

- **Layer:** MODEL INPUT / king (precision, P10)  
- **Status:** VERIFIED_IMMATERIAL · **Severity:** P3 — Resolution: decile level over 47 anchors x 400 names; rank level 30 name-anchors.  
- **Affects:** live_trading · **Method:** VERIFIED

Of 24,800 booster thresholds, 24,024 sit on the midpoint of two adjacent float16 values (largest distance 2.3e-13 of a float16 step, the model file's print precision), where a float32 input and its float16 round trip branch differently only when the float32 value lies exactly on the midpoint; 776 (in 47 columns, mostly rank columns; fund_now 22) sit on a float16 grid value (distance 0.500 step), where float32 inputs in the half step above the threshold branch differently. Served inputs, 47 anchors: 275 of 1,466,400 cells lie inside such a risk window. Casting every served input to float16 before predict changes the leaf path of 4 rows (cpos_mean_48_v 1, log_avgsz_mean_48_v 1, tbf_mean_48_v 1, tbf_mean_864_v 1), 30 rank positions (21 on one anchor), 0 deciles, top/bottom-decile overlap 1.00/1.00, max |Δpred| 0.0056 (served score sd ≈ 0.024), king-leg z max change 0.050 on one name (0.0165 after the masked seat). Storage alone (float16 vs float32 at the serving clock) changes no cell by more than 1e-3 in any column; float64 vs float32 window sums change at most 94 rank cells in a column (ties). fund_now shows 280 cells above 1e-3 relative from float16 quantisation of rates near 2e-5, with no leaf change.

Evidence:
- pod_fea_ext.py (02157bda) L65 + L72
- shadow_loop_v3.py (e9c98374) L358 (rows [E-w+1, E]) + L397 float32
- receipts_prod/parity_king.json (9dbba68b, device file parity_king.py sha256 fad9f3c2): P10_f16_cast, thresholds_f16.per_column, pair_stats.store_TPE_vs_TPE32 and reduction_TPE32_vs_S
- devices_prod/build/build_audit_prod.py threshold check (lightgbm dump of slow2026.txt 8d79186b)

Recommended action: None. Do not add a float16 cast to serving; it buys nothing measurable.

### PROD-06 · V2MAIN inputs differ between training and serving almost entirely through the member universe of every cross-sectional rank; score Spearman 0.982

- **Layer:** MODEL INPUT / V2MAIN (rank universe)  
- **Status:** OPEN_MEASURED_MATERIAL · **Severity:** P2 — Every rank-based V2MAIN input is on a different cross-section from training for the served model and for every 2026 research score; book layer not measured.  
- **Affects:** live_trading, future_eval, future_retrain · **Method:** VERIFIED

On 17 anchors (09-05 16Z..09-10 20Z) the served 171 columns vs the stored x0910 training rows on common names give V2MAIN-score Spearman median 0.9824 (min 0.9646), max rank change median 0.179; 130 of 171 columns have cells beyond 1e-3. Holding code and data fixed and changing only the member sets (production-rule members on live450 vs training members on 829 names) reproduces the gap: Spearman 0.9823 (min 0.9640); the same code on training members reproduces the stored training rows (Spearman 1.0000, max score change 0.00012). Score Spearman when one family is swapped to training values: x82_rank 0.9955, F 0.9975, E 0.9983, J 0.9986, fund 0.9988, I 0.9992, B 0.9992, D 0.9993, H 0.9995, A 0.9996, C 0.9997, G 0.9997, x82_value 1.0000. The in-service V2MAIN (trained through 2026-08-30) saw 2026 cross-sections that include tokenized equities (7.3% of 2026 member pairs, AUDIT_DATA C6); it is served crypto-only live-450 cross-sections.

Evidence:
- dlw_features.py (29ae6a98) L44 (rows [E-w+1, E], float16 X); f8_higher_order_features.py (2c500c7a) L112; combo_stage.py (b5c698f9) L123 (scored anchor's members on every history row)
- pod_dlw_features_ext.py (e86725cc) L44 (differs from serving only at L16 default PANEL path); pod_f8_build_ext.py (f606bffa) same statement (differs from serving only in the path constants L17-23); pod_dlw_targets_ext.py (c21683ee) L100 (own members per anchor, 829 names, forward-finite)
- receipts_prod/parity_f10.json (cdaa197e, device file parity_f10.py sha256 fed8b141): score.FS_vs_T171/FH_vs_FD/FD_vs_T171, pair_stats, score_family_substitution_FS_with_T171; gates: G-F10SREP production 40-day cache reproduces served combo_X171/scol/f10 bitwise 6/6 (also the T4b 234-239-row view 6/6); G-MEMBERCODE 3/3; G-F10CODE PASS (training code on training members reproduces the stored rows; trend_288 0.9888, trend_2016 0.9994 bitwise share); G-BOOT bundle tail == pod cache on live450 (0 diffs)
- receipts_prod/members_audit.json (eb8d5da7, device file members_audit.py sha256 7bc0a664): summary.PD (Jaccard median 0.660)
- devices_data/receipts/AD_C_cache_members.json C6 (dl_targets_members 2026 noncrypto share 0.0726)

Recommended action: Same fix as PROD-02: one member universe (CRYPTO default) in pod_dlw_targets_raw.py member selection before the October DL retrain; add a served-vs-builder X171 parity gate at export (this device's G-F10SREP/G-F10CODE pattern).

### PROD-07 · Serving reuses the scored anchor's member set on every history row; only the 24h rank-change and dispersion columns move, score Spearman 0.9998

- **Layer:** MODEL INPUT / V2MAIN (history members)  
- **Status:** OPEN_MEASURED_MATERIAL · **Severity:** P3 — Real but small at the score layer (Spearman >= 0.9996); confined to 8 columns.  
- **Affects:** live_trading, future_eval · **Method:** VERIFIED

combo_stage writes members = pm for all history anchors ('近似'), while training uses each anchor's own members. Rebuilding the served rows with each history row's production member set changes only 8 columns (J:drank_m7_1d, J:drank_v7_1d, J:drank_r24_1d, H:disp_z, H:r4xdisp, H:r24xdisp, H:m7xdisp, H:v7xdisp): J:drank cells beyond 1e-3 5437/6020/4715 of ~6,800 (max 0.5 where a name was not a member 24h earlier), H:disp_z median relative change 0.063 (max 0.206). V2MAIN score Spearman median 0.99982 (min 0.99960), max rank change median 0.073 (max 0.135). Early rows of the long cache without a full 7-day window reused the first full-window member set (40 rows, outside every scored anchor's windows); anchors without a weights file used the production member code (['2026-08-18 16Z', '2026-08-29 20Z']).

Evidence:
- combo_stage.py (b5c698f9) L123 (scored anchor's members on every history row)
- f8_higher_order_features.py (2c500c7a) L335
- f8_higher_order_features.py (2c500c7a) L350, causal z L354
- receipts_prod/parity_f10.json (cdaa197e, device file parity_f10.py sha256 fed8b141): pair_stats.history_members_FS_vs_FH, score.FS_vs_FH, FH_early_rows_fallback; gates: G-F10SREP production 40-day cache reproduces served combo_X171/scol/f10 bitwise 6/6 (also the T4b 234-239-row view 6/6); G-MEMBERCODE 3/3; G-F10CODE PASS (training code on training members reproduces the stored rows; trend_288 0.9888, trend_2016 0.9994 bitwise share); G-BOOT bundle tail == pod cache on live450 (0 diffs)

Recommended action: Store per-anchor member sets in producer state and pass them to the 171 pipeline (a producer change; bundle with the PROD-06 universe fix).

### PROD-08 · btcv is defined differently in training (zero-filled, divisor E-S) and serving (nanstd with back-fill) but the served values are equal

- **Layer:** MODEL INPUT / V2MAIN (btcv)  
- **Status:** VERIFIED_IMMATERIAL · **Severity:** P3 — Resolution 1e-3 relative on every cell of 17 anchors.  
- **Affects:** live_trading · **Method:** VERIFIED

H:btcv_z: 0 cells beyond 1e-3 between served rows and stored training rows (and between F_H and F_D) on 17 anchors; swapping the btcv family to training values leaves V2MAIN score Spearman 0.99998 (the products carry rank-universe differences). The back-fill matters only in short caches (PROD-36).

Evidence:
- combo_stage.py (b5c698f9) L59 (nanstd rows [i-2016, i), first 7 days back-filled)
- pod_dlw_targets_ext.py (c21683ee) L88 (zero-filled, divisor E-S)
- receipts_prod/parity_f10.json (cdaa197e, device file parity_f10.py sha256 fed8b141): pair_stats.total_FS_vs_T171['H:btcv_z'], universe_btcv_FH_vs_FD['H:btcv_z']

Recommended action: None for live; see PROD-36 for replays.

### PROD-09 · The two trend columns depend on cache length (global cumulative sums); the same code on a 48-day cache differs from the 4.7-year training build in 1.1% / 0.06% of cells

- **Layer:** MODEL INPUT / V2MAIN (trend cumsum length)  
- **Status:** VERIFIED_IMMATERIAL · **Severity:** P3 — Resolution: rank changes <= 0.005 on 1.1% of trend_288 cells; score Spearman 0.9999.  
- **Affects:** live_trading, future_retrain · **Method:** VERIFIED

G-F10CODE: with training members, training btcv and the pod cache, every column reproduces the stored training rows bitwise except C:trend_288 (0.9888 bitwise; 76 cells beyond 1e-3, max 0.0050 rank units) and C:trend_2016 (0.9994; 4 cells, max 0.0025). Serving runs on a 40-day cache, training on the full history, so near-tied trend values rank differently. Swapping the trend columns alone leaves V2MAIN score Spearman 0.99991. Same mechanism AUDIT_TRAIN TRN-16 found in the STEP1 gate.

Evidence:
- f8_higher_order_features.py (2c500c7a) L210
- receipts_prod/parity_f10.json (cdaa197e, device file parity_f10.py sha256 fed8b141): gates.G-F10CODE, pair_stats.code_identity_FD_vs_T171
- AUDIT_TRAIN TRN-16

Recommended action: Adopt the local-window trend builder (pod_f8_build_stable.py, TRN-16) for training and serving together.

### PROD-10 · The A0 research replay trades a different member set from production: 373 masked crypto names vs the producer's top-400 of the live 450

- **Layer:** MEMBERSHIP / replay universe  
- **Status:** OPEN_MEASURED_MATERIAL · **Severity:** P3 — Known replay deviation with a measured ~5% share of one carry gap; not a live defect.  
- **Affects:** future_eval · **Method:** VERIFIED

Production rule reproduced exactly (V1 {'anchors': 161, 'exact': 161, 'mismatch': [], 'first': '2026-08-17 04Z', 'last': '2026-09-13 04Z', 'PASS': True}, V2 {'anchors': 148, 'exact': 148, 'mismatch': [], 'PASS': True}; data parity DP {'common_rows': 10896, 'first': '2026-08-04 04:05Z', 'last': '2026-09-11 00:00Z', 'channels': {'ret5': {'cells': 4903200, 'nan_pattern_diff': 0, 'pod_finite_prod_nan': 0, 'prod_finite_pod_nan': 0, 'both_finite': 4903200, 'bitwise_equal': 4903200, 'bitwise_diff': 0}, 'range': {'cells': 4903200, 'nan_pattern_diff': 0, 'pod_finite_prod_nan': 0, 'prod_finite_pod_nan': 0, 'both_finite': 4903200, 'bitwise_equal': 4903200, 'bitwise_diff': 0}, 'cpos': {'cells': 4903200, 'nan_pattern_diff': 0, 'pod_finite_prod_nan': 0, 'prod_finite_pod_nan': 0, 'both_finite': 4889587, 'bitwise_equal': 4889587, 'bitwise_diff': 0}, 'log_qv': {'cells': 4903200, 'nan_pattern_diff': 0, 'pod_finite_prod_nan': 0, 'prod_finite_pod_nan': 0, 'both_finite': 4903200, 'bitwise_equal': 4903200, 'bitwise_diff': 0}, 'log_cnt': {'cells': 4903200, 'nan_pattern_diff': 0, 'pod_finite_prod_nan': 0, 'prod_finite_pod_nan': 0, 'both_finite': 4903200, 'bitwise_equal': 4903200, 'bitwise_diff': 0}, 'log_avgsz': {'cells': 4903200, 'nan_pattern_diff': 0, 'pod_finite_prod_nan': 0, 'prod_finite_pod_nan': 0, 'both_finite': 4894094, 'bitwise_equal': 4894094, 'bitwise_diff': 0}, 'tbf': {'cells': 4903200, 'nan_pattern_diff': 0, 'pod_finite_prod_nan': 0, 'prod_finite_pod_nan': 0, 'both_finite': 4894094, 'bitwise_equal': 4894094, 'bitwise_diff': 0}}, 'snapshot_nonlive_cells_finite': 5071920, 'rows_from_2026-09-01': {'rows': 2881, 'nan_pattern_diff': 0, 'bitwise_diff': 0}, 'PASS': True}). Over 142 anchors the A0 member set (all names with finite meta qvk, masked by umask_UPIT_CRYPTO; no top-400 cut) has 373 names; overlap with production members median 332, production-only 68, A0-only 41 (13 outside the live 450). Liquidity-selected sets: Jaccard median 0.893 (min 0.865); production-selected names missing from A0's selection are almost all not A0 members (2976 of 2984 name-anchors); A0-selected names missing from production are mostly outside the live 450 (992 of 1058). T5 attributes 5.2% / 5.1% of the August carry gap (+0.061 bps/anchor) to the member set; the counts here are consistent with a small, persistent universe share.

Evidence:
- receipts_prod/members_audit.json (eb8d5da7, device file members_audit.py sha256 7bc0a664): summary.R, summary.SEL, summary.T5_window
- multi_asset/exports/research/uplift_r2_2026-09-13/T5/RESULT_T5_deployed_carry_gap_2026-09-13.md L25/L66 (M 成员集 +0.061, 5.2%/5.1%)
- docs/PREREG_producer_parity_phase2_oos_2026-09-12.md A2.2 D4 (P2 uses PIT universe, not pins)

Recommended action: Keep A0 vs production universe as a named deviation in every replay-vs-live contrast; P2's production-path replay already runs the producer's own member code.

### PROD-11 · The forward-finite member term (D20), the window divisor and float32 change no member in 147 recent anchors; the one-bar clock changes at most 2

- **Layer:** MEMBERSHIP / training rule terms  
- **Status:** VERIFIED_IMMATERIAL · **Severity:** P3 — Resolution one name per anchor over 2026-08-17..09-10; periods with delistings not covered.  
- **Affects:** future_eval, future_retrain · **Method:** VERIFIED

Path from each training rule to the production rule, one factor at a time, on 147 anchors: universe to live 450 changes median 164 names (all of the difference), dropping the forward-finite term 0 (max), serving clock 2 (max; mean 0.095), production divisor 0, float32 0; the DL rule behaves the same (D2 0, D3 2). Median qvm gap at the top-400 cut 0.0044. This bounds AUDIT_TRAIN TRN-06 (D20) to zero member changes in this window; delisting-heavy history was not measured.

Evidence:
- receipts_prod/members_audit.json (eb8d5da7, device file members_audit.py sha256 7bc0a664): summary.pathK_step_symdiff, pathD_step_symdiff, one_at_a_time_symdiff_vs_P, ntop_cut_gap_qvm; gates V3/V4 (K and D rules reproduce the stored x0910 members 147/147)
- pod_dlw_targets_ext.py (c21683ee) L100
- pod_fea_ext.py (02157bda) L75; members L37-39

Recommended action: Keep TRN-06 open for history; no action for the recent window.

### PROD-12 · qv4h is the same quantity in production and in the A0 replay; the 0.52 log gap recorded in r17 compares a different formula

- **Layer:** MEMBERSHIP / liquidity gate (P3 qv4h)  
- **Status:** VERIFIED_IMMATERIAL · **Severity:** P3 — Resolution: 17 gate-side disagreements in 47,190 name-anchors.  
- **Affects:** future_eval · **Method:** VERIFIED

Production qv4h = expm1(mean log1p(qv5m) over 2016 rows) x 48; A0 uses the same expression on meta qvk. On 47,190 name-anchors |Δlog qv4h| median 5.7e-04, p90 1.5e-03, max 5.7e-03; cost-tier agreement 0.99991; 17 name-anchors fall on different sides of the 2.5e5 gate (the two windows differ by one bar and in float precision; not separated). The r17 formula (arithmetic 4h quote volume) differs from both by |Δlog| median 0.497 (tier agreement 0.784): a Jensen gap between two definitions, not a data difference (G2-A' already showed identical 5m channels).

Evidence:
- shadow_loop_v3.py (e9c98374) L473
- pod_export_bundle_v3.py (c210bac6) L130
- receipts_prod/members_audit.json (eb8d5da7, device file members_audit.py sha256 7bc0a664): summary.QV4H
- docs/PREREG_producer_parity_phase2_oos_2026-09-12.md 收据 1 (r17 |Δlog| 0.52) and AMENDMENT 1 (G2-A' live450 PASS)

Recommended action: Do not use the arithmetic 4h quote-volume formula for the liquidity gate or cost tiers in any replay.

### PROD-20 · The masked model seat is computed on 819 seeded rows scored with the training representation plus 81 producer rows

- **Layer:** SERVING STATE / seat  
- **Status:** OPEN_NOT_MEASURED · **Severity:** P3 — Self-healing over ~4.5 months; the one measured component is small.  
- **Affects:** live_trading, future_eval · **Method:** VERIFIED

leg_returns_live.json keeps 950 rows; the 900-row msharpe window holds 819 rows seeded on 09-05 from the v3 bundle (8d79186b predictions on training features: v0 column 80, rows [E-w, E-1], training members; labels [E, E+47]; anchors 2026-04-06 04:00Z .. 2026-08-30 20:00Z) and 81 producer rows (2026-08-31 00:00Z .. 2026-09-13 08:00Z; {'29ffaf58bcb7': 8, '8d79186b6380': 73}). w3 recomputed from the file equals the 12Z signal to 4 decimals; masked seat w3m [0.382095, 0.0, 0.617905]. The last seeded row leaves the window after 819 scored anchors (projected 2027-01-28 00:00Z). Measured part (T4b §5): re-scoring the seeded rows with v1 column 80 moves the seat +0.0078 and combo target_live L1 by 0.0066 (6 anchors); PROD-01..03 differences (clock, universe) in the seeded rows are not measured.

Evidence:
- receipts_prod/state_seat_ledger_probe.json (97a02d3c): S1
- shadow_loop_v3.py (e9c98374) L459
- uplift_r2_2026-09-13/T4b/RESULT_T4b_v2main_feature_skew_2026-09-13.md §5
- memory seat_seed_v3_deployed_2026_09_05

Recommended action: No live action; any replay that uses the live seat must state the seeded-row mix.

### PROD-21 · The October bundle swap has no seat re-seeding step, and no rule fixes which scoring representation a seed must use

- **Layer:** RETRAIN PROCEDURE / seat  
- **Status:** PENDING_USER_DECISION · **Severity:** P2 — A silent seat mismatch at the next swap is the same class as the 0.19 vs 0.30 gap fixed on 09-05.  
- **Affects:** future_retrain, live_trading · **Method:** VERIFIED

RUNBOOK_monthly_retrain_2026-10 §0★ step 8 (backup, swap, sidecar A2, acceptance, first-anchor check) never seeds leg_returns_live.json; the producer ignores bundle rows while the file holds >= 900 rows, so after a swap the seat keeps describing 8d79186b and the seeded v3 rows for about 150 days. The 09-05 precedent required a user-approved seed.

Evidence:
- docs/RUNBOOK_monthly_retrain_2026-10.md §0★ step 8 and L187 (grep: no 播种/seed/leg_returns_live other than L187)
- shadow_loop_v3.py (e9c98374) L226
- multi_asset/exports/live/seat_seed_v3_2026-09-05/dryrun_seat_seed.py (not referenced by the runbook)
- AUDIT_TRAIN TRN-12

Recommended action: Add an explicit seat step to the swap (seed or not; declared scoring representation and label window; dry run like 09-05) and take the user's word on it with the bundle sha.

### PROD-22 · D17 funding-EMA artefacts in the live producer state are decaying and do not recur

- **Layer:** SERVING STATE / funding EMA (D17)  
- **Status:** VERIFIED_IMMATERIAL · **Severity:** P3 — Resolution: fund z Spearman 0.99996, top decile unchanged.  
- **Affects:** live_trading, future_eval · **Method:** VERIFIED

12 names carry ledger rows whose stored interval differs from the time gap, all before 09-05 12Z ({'1000XECUSDT': 1, 'ACEUSDT': 67, 'BANKUSDT': 103, 'DEXEUSDT': 152, 'EPICUSDT': 1, 'ERAUSDT': 137, 'ESPORTSUSDT': 1, 'GWEIUSDT': 1, 'LABUSDT': 1, 'PARTIUSDT': 1, 'PROMUSDT': 79, 'TUSDT': 1}); none after, over 179,967 adjacent pairs. They come from the 08-16 bundle seed; the running append path derives intervals from time gaps and the seed loads only when rolling.npz is absent. Inherited EMA residual 2.60e-5 at 09-05 16Z, 5.58e-6 at 09-12 08Z (half-life 3 days); fund-leg z Spearman >= 0.99996, top decile unchanged 41/41 anchors (P2 receipts).

Evidence:
- receipts_prod/state_seat_ledger_probe.json (97a02d3c): S2
- shadow_loop_v3.py (e9c98374) L341
- shadow_loop_v3.py (e9c98374) L205
- parity_replay_2026-09-12/phase2/receipts/G2Bpp_inwindow_recursion.json and D17_forensics.json (PREREG_producer_parity_phase2 收据 3, 附 D17 取证)

Recommended action: None for live; producer-path replays keep the 'clean rebuild != live EMA' label until the residual is below 1e-9 (about mid-October). Note that FX-PROD P9 (PROD-40) is a separate, recurring interval defect in the same append path.

### PROD-23 · Panel, splice and October exporter still apply one declared interval to every API-tail funding row

- **Layer:** BUILDERS / funding interval  
- **Status:** OPEN_MEASURED_MATERIAL · **Severity:** P2 — The October splice panel and any bundle seed inherit it; live is exposed only through a state reset from a seed.  
- **Affects:** future_eval, future_retrain · **Method:** VERIFIED (code) / CITED (T5b numbers)

Names whose settlement interval changed inside the API tail get the fetch-time interval on older rows; this fed the D17 rows (08-16 seed) and the x0910 September interval errors, and flows into f_fund_iv, f_fund_ema_v1, rn8/FTRIM and carry in research panels and into any bundle ledger/EMA seed.

Evidence:
- pod_panel_ext.py (db7f0474) L105
- pod_export_bundle_v3.py (c210bac6) L200
- pod_export_bundle_v4.py (42555a37) L220/L230-234, present in pod2 w3_monthly_chain device dir; r6_panel_splice.py (cccc5b6b) L81-91
- uplift_r2_2026-09-13/T5b/RESULT_T5b.md §5.1 (x0910 carry vs ledger, IOST ratio 8.00)
- AUDIT_TRAIN TRN-07; T5d prereg (repairs September cells only)

Recommended action: Derive each row's interval from its own settlement history (gap or per-row declared history), validated against executor settlement records as T5b did; relabel x0910-based September carry/FTRIM readings until T5d lands.

### PROD-24 · FTRIM is served as a z-layer exclusion before demeaning, not a forced exit; residual shorts decay and freeze under the neutral band

- **Layer:** COMBO TARGET / FTRIM as served  
- **Status:** OPEN_MEASURED_MATERIAL · **Severity:** P2 — Carry drag of order 0.1-0.3 bps/anchor on residual shorts; not a risk exposure.  
- **Affects:** live_trading, future_eval · **Method:** VERIFIED (code) / CITED (T5b)

Rule 'pre_zero_rn8_le_-10bp_8h' in both chains since 2026-09-02 12Z (67 anchors): median 8 names per chain (max 16), rn8 coverage min 1.0. rn8 = latest ledger rate x 8 / stored interval, so FX-PROD P9 interval mislabels reach the classification. T5b (61 anchors 09-02..09-12): frozen residual gross 0.33% [0.24%, 0.40%], max age 41 anchors (ONG); frozen-residual carry -0.120 bps/anchor [-0.245, -0.021] (PROVISIONAL: its carry gate is red, PROD-23); all FTRIM residuals +0.115 [-0.080, +0.334] (secondary); residual shorts pay +0.294 [+0.155, +0.478] (post hoc). The executor adds no band freeze.

Evidence:
- combo_stage.py (b5c698f9) L245
- combo_stage.py (b5c698f9) L243
- combo_stage.py (b5c698f9) L92
- receipts_prod/prod_target_checks.json (f8113efe, device file prod_target_checks.py sha256 2bd626fd): FTRIM_served
- uplift_r2_2026-09-13/T5b/RESULT_T5b.md

Recommended action: A forced exit for FTRIM names is a book-behaviour change needing the user's ruling (FX-BOOK P7); re-read after T5d and after FX-PROD P9.

### PROD-25 · EXE-03 confirmed from producer files: 91% of the 12Z 撤名残差 is the producer's own net; the uniform re-demean flips small shorts on 99 of 109 combo anchors

- **Layer:** COMBO TARGET -> EXECUTOR reshape (EXE-03 confirmed)  
- **Status:** PENDING_USER_DECISION · **Severity:** P2 — Structural every-anchor behaviour: the producer writes an un-neutralised book and the executor's uniform shift reverses small opposite-side intents; the alarm misattributes the cause.  
- **Affects:** live_trading, reporting · **Method:** VERIFIED

12Z target_live: net/gross -8.4611%; the 11 popped names +0.7999% (net long); remainder -9.2609% = the alarm's net_before/sizing -9.2609%. Share of net_before from the producer's own net 91.4%, from removing the popped longs 8.6%; the alarm text names only the popped names. Re-executing legs.reshape_after_withhold on the producer vector with the recorded pops reproduces orders target_w in sign for 244/244 names (values x1.0018561 after a later per-name cap on ['PIEVERSEUSDT']). Sign flips short->long 9 (1000CATUSDT, 1000LUNCUSDT, CFXUSDT, ENSOUSDT, NILUSDT, ONGUSDT, SAGAUSDT, SUSDT, ZKUSDT), long->short 0; 8 filled, 376.81 USDT. Across 109 combo anchors the producer book is net short on 107 (median -3.99%, min -9.29%); the re-demean alone (no pops) flips names on 99 anchors (median 3, max 8; flipped unit gross median 2.23e-04).

Evidence:
- receipts_prod/prod_target_checks.json (f8113efe, device file prod_target_checks.py sha256 2bd626fd): EXE03, EXE03_popfree_frequency
- ~/dl_quant_live signal/legs.py (7c0665f8) reshape_after_withhold: w = w - w.mean(); w = w / s
- ~/dl_quant_live scheduler/anchor_loop.py (95e72cb0) L1854-1861 alarm text
- combo_stage.py (b5c698f9) L270
- AUDIT_EXEC EXE-03

Recommended action: Alarm: report producer net and popped-name net separately (FX-EXEC E6). Book: run the side-proportional allocation as a registered experiment (FX-BOOK P8) before any change; measure why the combo book is persistently net short (EMA band freeze, keep-mask exits, cap clipping) before choosing where to neutralise.

### PROD-26 · CHK-01 confirmed (11/11 values); the rise from 17% to 27% is the V2MAIN chain moving away from the king book, not FTRIM or rev24 removal

- **Layer:** COMBO TARGET / counterfactual rewrite (CHK-01 confirmed)  
- **Status:** DOC_STALE · **Severity:** P3 — Producer side has no defect; the template's fixed level is stale (AUDIT_EXEC keeps CHK-01 at P2 for the escalation rule).  
- **Affects:** reporting · **Method:** VERIFIED

Σ|w_live - w_king| / Σ|w_king| (inspect_anchor.py L33-38) matches all 11 of 11 values AUDIT_EXEC quotes. Decomposition by the two chains combo_stage mixes (gate: 0.55·kc + 0.45·fc equals target_live to 0.0e+00): R_kc 0.163 -> 0.163 (flat), R_fc 0.255 -> 0.476; rho_kc_fc 0.9726 -> 0.9146; masked model seat 0.199317 -> 0.382095. Across 109 anchors corr(R, R_fc) 0.933, corr(R, rho_kc_fc) -0.893, corr(R, masked seat) 0.558, corr(R, R_kc) 0.408, corr(R, FTRIM count) -0.470. Mechanism (descriptive): the doubled model seat (09-05 seeding, PROD-20) raised V2MAIN's coefficient in the fc chain while the kc chain stays near the king book.

Evidence:
- receipts_prod/prod_target_checks.json (f8113efe, device file prod_target_checks.py sha256 2bd626fd): CHK01_claims_vs_measured_pct, CHK01_change_0903_to_0913, CHK01_descriptive
- multi_asset/exports/live/pilot_journal/tools/inspect_anchor.py (714792e1) L33-38
- docs/CRON_TEMPLATES_2026-09-04.md:13
- AUDIT_EXEC CHK-01

Recommended action: Replace the fixed 19-20% level with a trailing band and report R_kc/R_fc next to R so a real change in the V2MAIN chain is visible.

### PROD-27 · The combo rewrite lands within 9 s of its hard deadline at worst; a late producer run skips the rewrite with no page

- **Layer:** COMBO LIVE / timing  
- **Status:** OPEN_MEASURED_MATERIAL · **Severity:** P2 — A ~10 s slowdown on the slowest observed anchor would switch that anchor's traded book to the king form; one of the two failure paths raises no page.  
- **Affects:** live_trading · **Method:** VERIFIED

Since combo went live: 110 anchors, 109 traded the combo target, 1 the king form (2026-08-30 00:00Z, king file written at 1467 s). Combo target written median 1307 s after the anchor, p99 1346 s, max 1351 s against the 1360 s bail; minimum margin 9 s, 59 of 109 anchors within 60 s. A combo run that starts late bails with a HIGH page and the executor trades the king form; if the producer finishes after N+22:35 the daemon skips silently (the 08-30 00Z case). The executor reads at N+24.

Evidence:
- receipts_prod/state_combo_timing_probe.json (67654ea5)
- fea171/combo_live_daemon.sh (72f78d1e) L27-29 silent skip branch
- combo_stage.py (b5c698f9) L321
- receipts_prod/runtime_processes.txt (com.hsy.combolive PID 30944)

Recommended action: Page on the daemon's late-skip branch; separately (user word) move the producer offset earlier or widen the deadline consistently with the N+24 read; keep heavy Mac jobs out of N+15..N+25.

### PROD-28 · The running producer and combo daemon execute the on-disk code, bundle and F10 model (verification record)

- **Layer:** PRODUCER RUNTIME / versions  
- **Status:** VERIFIED_IMMATERIAL · **Severity:** P3 — Record only (exact sha, mtime and process start ordering).  
- **Affects:** live_trading · **Method:** VERIFIED

None found. com.hsy.shadowloop PID 10900 started 2026-09-05 12:47:33Z, after shadow_loop_v3.py (e9c98374) was last written 09-04 00:53:42Z; bundle MANIFEST 8/8 matches disk (booster 8d79186b, signal booster_sha on every anchor since 09-01 08Z); combo_stage.py (b5c698f9) is launched fresh each anchor by com.hsy.combolive (PID 30944, started 08-30 05:03Z, daemon file 08-26); fea171/f10_live_s42_np.npz 351ae26b equals the pod2 export; xfer_ref/xfer_syms symbol axes equal config symbols_panel. The pinned feature code runs bitwise equal to the served inputs (G-SREP/G-F10SREP).

Evidence:
- receipts_prod/runtime_processes.txt
- receipts_prod/pod2_provenance.txt (f8_ext/models/f10_live_s42_np.npz 351ae26b)
- receipts_prod/state_seat_ledger_probe.json (97a02d3c): S6
- receipts_prod/parity_king.json (9dbba68b, device file parity_king.py sha256 fad9f3c2): G-SREP
- receipts_prod/parity_f10.json (cdaa197e, device file parity_f10.py sha256 fed8b141): G-F10SREP

Recommended action: None.

### PROD-29 · The sidecar daemon is a second, non-atomic writer of the same combo intermediates

- **Layer:** PRODUCER RUNTIME / second writer  
- **Status:** VERIFIED_IMMATERIAL · **Severity:** P3 — Latent; 0 collisions observed; a collision would most likely fail loud (king fallback with page).  

> **★ 重定级 2026-09-16(lead; 原字节保留, 以本框为准)。** `VERIFIED_IMMATERIAL / P3` **作废**, 改 **DISPUTED → P2**。理由(FX-PROD P12 逐锚普查, 装置 `fx/p12_state_h_census.py`, 收据 `FX_PROD/receipts/p12/P12_CENSUS.json` sha `2bbd9c8c`, 克隆 bdb9e1f):
> 1. **「0 次碰撞」是错的检验。** 没有碰撞不是因为隔离有效, 而是因为**侧车每锚都赢**: `state_H_f10_<A>.npz` 在 **128/129 锚**上的**最后写者**是 `sidecar_blend.py`(`mtime − sidecar finish` 每个可归因行都在 ±1.0 s 内; `mtime − combo finish` 为 +122..+235 s, 中位 **+168 s**)。唯一未归因的一份是 08-26 00Z 的开机手工跑。
> 2. **它不是「第二写者」, 而是某条实盘链状态的唯一有效写者。** `combo_stage` 自己算出的 F-10 链状态**每锚都被丢弃**, A+1 的暖启用的是侧车的重算, 不是产出被交易之书的那一次运行 ⇒ **任何用 `combo_stage` 代码重算该状态的回放都按构造与实盘不同** —— 这正是 P2 测到的 96 名 2.63e-8。
> 3. **时序更差**: 129 锚中 **79 次侧车写入落在执行器首读 N+24:00 之后**(侧车完成中位 N+24:20), 即多数锚上「给下一锚暖启种子的文件」是在当锚的书**已经交易之后**才写的。
> 4. 该文件自称「只读侧车」, 与事实不符 —— 文案须按代码改(与 E6 同规)。
> **未变的部分**: 「侧车写入非原子」与「建议退役或给它自己的输出路径」仍成立; **改变写入行为(谁赢)是书行为**, 需配对回放 + 用户裁定, 已登记由 lead 上交。
- **Affects:** live_trading · **Method:** VERIFIED (code, process list) / CITED (collision count from the fork's log scan)

com.hsy.sidecar (PID 30943) runs sidecar_blend.py (6140790e), which repeats combo_stage.py L1-222 and writes mini/cache.npz, mini/data/dlw_targets.npz, xfer_panel_live.npz, state_H_f10_<A>.npz and target_blend/<A>.json with non-atomic np.savez; combo_stage reads the same paths (state_H_f10 is the fc warm-start fallback). Isolation is timing only: the sidecar sleeps 120 s after a new target_live. 0 overlaps observed in 109 anchors; the sidecar last recomputed the 171 pipeline at 08-30 00Z.

Evidence:
- receipts_prod/runtime_processes.txt (sidecar_daemon.sh 01d75619: sleep 120 / 180)
- ~/wide_shadow/fea171/sidecar_blend.py (6140790e) L123-124, L143, L194, L211
- combo_stage.py (b5c698f9) L180

Recommended action: Retire the sidecar (target_blend has no reader) or give it its own output paths; a production process change needs the user's word.

### PROD-30 · A modified sandbox producer (exec_n6) has been running at N+1 since 09-06 against the live bundle

- **Layer:** PRODUCER RUNTIME / sandbox producer  
- **Status:** PENDING_USER_DECISION · **Severity:** P3 — Isolated state; risk is mistaking its outputs for live and API-budget sharing.  
- **Affects:** future_eval, reporting · **Method:** VERIFIED

PID 50689 runs ~/cc_tmp/exec_n6_sandbox/shadow_loop_v3.py with WIDE_SHADOW_HOME=~/cc_tmp/exec_n6_sandbox and SHADOW_OFFSET_MIN=1 (own lock and state, live bundle read-only, not launchd-managed). It shares the IP's API budget and writes target files that are not the live chain.

Evidence:
- receipts_prod/runtime_processes.txt (ps lstart Sep 6 20:58:03 SGT; env WIDE_SHADOW_HOME, SHADOW_OFFSET_MIN=1)
- docs/PREREG_deploy_exec_n6_2026-09-06.md; STATE.md (conditional GO, swap needs user word)

Recommended action: Stop it or label its outputs when the exec_n6 decision is made.

### PROD-31 · fea171/f10_live_s42.pt next to the served numpy model is the August model, not the checkpoint behind 351ae26b

- **Layer:** MODEL ARTEFACTS / stale copies  
- **Status:** DOC_STALE · **Severity:** P3 — Wrong-copy risk only.  
- **Affects:** future_eval, reporting · **Method:** VERIFIED (sha/mtime) / CITED (trained_through from the fork's read)

~/wide_shadow/fea171/f10_live_s42.pt (d6619801, written 08-24) is the August model (trained_through 08-10 20Z); the served npz 351ae26b comes from pod2 f8_ext/models/f10_live_s42.pt (c983b3e3). combo_stage loads only the npz.

Evidence:
- receipts_prod/runtime_processes.txt (mtimes and sha prefixes)
- combo_stage.py (b5c698f9) L160

Recommended action: Rename the .pt with an _aug suffix or add a note beside it.

### PROD-32 · stop_overlay.py is a reporting shadow on the king-form weights; the served stop is the executor's per_name_stop

- **Layer:** SERVING / stop overlay  
- **Status:** DOC_STALE · **Severity:** P3 — Mislabelled reporting only.  
- **Affects:** reporting · **Method:** VERIFIED

com.hsy.stopoverlay computes its stops on state/weights/<A>.npz (the producer's king-form book), so its held/stopped counts and cf_bps describe a book that is not traded. No executor code reads stop_overlay.json; config/book.json names stop_overlay.py only in the basis note of the wide per-name-stop profile (d30, 2 anchors, 7-day cooloff), which the executor applies after target_live (W9 fix deployed in ef60f85).

Evidence:
- receipts_prod/runtime_processes.txt (grep -rl stop_overlay over live/ scheduler/ signal/ ops/ config/: config/book.json only)
- ~/wide_shadow/stop_overlay.py (d54a2e16) L1-37
- AUDIT_EXEC (EXE-08 running tree ef60f85)

Recommended action: Label or retire stop_overlay; never cite its depths or cf_bps as live.

### PROD-33 · CLAUDE.md says the executor reads at N+23; the executor reads at N+24

- **Layer:** DOCS  
- **Status:** DOC_STALE · **Severity:** P3 — Documentation only.  
- **Affects:** reporting · **Method:** VERIFIED

config/book.json external_book.anchor_offset_min = 24; external_book.py wakes at nominal + offset x 60 s; the 12Z rebalance id A1789302239 started 12:23:59Z.

Evidence:
- receipts_prod/state_combo_timing_probe.json (67654ea5): executor_anchor_offset_min 24
- AUDIT_EXEC DOC-01

Recommended action: Correct the project identity line in CLAUDE.md.

### PROD-34 · The in-service booster 8d79186b was trained on the unclamped builder: 30-day windows of January-2022 training rows wrap to the cache tail (E-0909-A)

- **Layer:** IN-SERVICE MODEL / king training data  
- **Status:** OPEN_NOT_MEASURED · **Severity:** P3 — Early-2022 rows only (anchors before 2022-01-31); fixed for the next export.  
- **Affects:** live_trading · **Method:** VERIFIED (code) / INFERRED (affected-row range)

pod_fea_ext.py (02157bda, the builder of wide_fea_v2ext.npy used by pod_export_bundle_v3.py) takes s_[E - w] with no clamp, so anchors with E < w read the end of the cache (e.g. 2022-01-11 00Z cpos_mean_8640_v -242,695 clipped to -10,000, ranks computed on the garbage). The October builder clamps; the in-service model still contains these rows. Row count and effect on 8d79186b not measured.

Evidence:
- pod_fea_ext.py (02157bda) L48
- October chain builder pod_fea_ext_clamp.py (b9f9c728) L48 (same clock, same float16 store)
- docs/RESULT_holefix_round2_corrected_chain_2026-09-09.md L62 (king_wrap_verify)
- receipts_prod/pod2_provenance.txt (pod_fea_ext.py 02157bda; wide_fea_v2ext_meta.npz 4b1b6047, 09-01 05:33)

Recommended action: No live action; the next export with the clamp builder removes it (keep the clamp statistic gate).

### PROD-35 · The in-service V2MAIN was trained with fund columns set to 0 for names outside today's live 450, and on the pre-holefix cache

- **Layer:** IN-SERVICE MODEL / V2MAIN training data  
- **Status:** OPEN_NOT_MEASURED · **Severity:** P3 — Training-distribution defect of the served model; size unknown; the October chain rebuilds features.  
- **Affects:** live_trading, future_retrain · **Method:** VERIFIED

dlw_ext fea82 (9bc111a4) was built on panel wide_panel_4h_v3splice (c5d10f6a), whose funding columns are empty outside the live 450, so 26.8% of training pairs carry fund_ema = fund_now = 0 (T4b RECEIPT F2); served members always have real values. The same features were built on dlnative_5m_wide829_f16_ext (72eb7849), before the 08-12.. hole repair. Neither effect on the served model is measured.

Evidence:
- receipts_prod/pod2_reports/dlw_ext_results_dlw_features_report.json (panel_sha256 c5d10f6a, cache_sha256 72eb7849, self e86725cc)
- receipts_prod/pod2_provenance.txt (data/wide_panel_4h_v3splice.npz c5d10f6a)
- uplift_r2_2026-09-13/T4b/receipts/RECEIPT_T4b_facts_v2main.json F2_stored_zeros
- AUDIT_DATA batch 2 F2 (devices_data/receipts/AD_F_batch2.json)

Recommended action: Build DL fund columns from the panel that covers every training name (or mask the loss on names without funding) in the next export, and state it in the export gate.

### PROD-36 · Mechanism of the open Phase-1 G-P2 residual found: replay caches shorter than ~37 days put btcv back-fill into the 180-anchor z window

- **Layer:** REPLAY DEVICE / Phase-1 G-P2 residual  
- **Status:** OPEN_MEASURED_MATERIAL · **Severity:** P2 — Explains an open gate of the production-path replay that P2 (now main priority) must close; affects any chain replay that truncates the producer cache.  
- **Affects:** future_eval · **Method:** VERIFIED (feature and score layers) / INFERRED (target layer)

Running the production 171 pipeline with the cache truncated at the Phase-1 replay start (2026-08-03 08:05Z) instead of the producer's 40 days changes only H:btcv_z, H:r4xbtcv, H:r24xbtcv, H:m7xbtcv, H:v7xbtcv, and only while the truncated cache holds <= 213 anchor rows: 2026-09-05 16Z (199 rows) max |Δscore| 3.3e-04, max |Δrank| 0.0075; 2026-09-06 16Z (205 rows) max |Δscore| 1.4e-04, max |Δrank| 0.0025; 2026-09-07 08Z (209 rows) max |Δscore| 7.5e-05, max |Δrank| 0.0050; 2026-09-08 00Z (213 rows) max |Δscore| 7.9e-06, max |Δrank| 0.0000; 2026-09-09 08Z (221 rows) max |Δscore| 0.0e+00, max |Δrank| 0.0000; 2026-09-10 00Z (225 rows) max |Δscore| 0.0e+00, max |Δrank| 0.0000; 2026-09-10 20Z (230 rows) max |Δscore| 0.0e+00, max |Δrank| 0.0000; 2026-09-11 20Z (236 rows) max |Δscore| 0.0e+00, max |Δrank| 0.0000. _btcv_series fills the first 2,016 rows with the first full-window value; the causal z uses the previous 180 anchors, which reach those rows when the cache is shorter than about 37 days. The live producer always holds 40 days (239 rows) and is unaffected; replay chain runs started from a later snapshot are affected on their first days, which matches Phase 1's DL-leg-only, decaying residual (target-level link INFERRED: the combo chain was not re-run).

Evidence:
- combo_stage.py (b5c698f9) L59 (nanstd rows [i-2016, i), first 7 days back-filled)
- f8_higher_order_features.py (2c500c7a) L350, causal z L354
- receipts_prod/parity_f10.json (cdaa197e, device file parity_f10.py sha256 fed8b141): score.FT_vs_FS.per_anchor, pair_stats.phase1_truncation_FT_vs_FS, gates.G-F10SREP (a 20-hour truncation, 234 rows, is bitwise inert)
- multi_asset/exports/research/parity_replay_2026-09-12/RESULT_parity_phase1_2026-09-12.md §2-§3 (G-P2 0/41, residual only in the DL leg, latest anchor exact)

Recommended action: In the replay device, give every scored anchor a full 40-day cache (prepend rows from the bundle tail or pod cache, verified equal on live450 as here) and re-run the Phase-1 chain; G-P2 at 1e-6 should then pass or show a second mechanism.

### PROD-37 · V2MAIN column 80 trained v0 / served v1 and column 81 fill rules (T4b), measured on 17 anchors

- **Layer:** MODEL INPUT / V2MAIN (columns 80-81)  
- **Status:** OPEN_NOT_MEASURED · **Severity:** P3 — Score-layer effect small (Spearman 0.999); book effect unmeasured; the October export reintroduces the split (TRN-05, P2 there).  
- **Affects:** live_trading, future_retrain · **Method:** VERIFIED

fund_ema served vs training: median relative difference 0.500, per-anchor Spearman 0.847. fund_now is equal (0 cells beyond 1e-3) on every anchor except 2026-09-10 08Z, 2026-09-10 16Z, 2026-09-10 20Z, where all training rows are 0 because the x0910 splice panel ends at 2026-09-10 00Z (the TRN-17 pattern); zero shares otherwise equal on both sides (max 0.006). Serving takes columns 80/81 for every name in the producer's EMA state with no 12h freshness mask; only members reach the model and all members were fresh (T4b). Swapping both fund columns to training values: V2MAIN score Spearman 0.9988 (min 0.9915). Historical book effect NOT MEASURED (T4b: no fold checkpoints).

Evidence:
- combo_stage.py (b5c698f9) L141/L145 (v1 EMA, raw rate, all names, no freshness mask)
- panel wide_panel_4h_v3splice (c5d10f6a, receipts_prod/pod2_reports dlw_ext features report) f_fund_ema v0 / f_fund_now; names outside live450 = 0 (T4b RECEIPT F2)
- receipts_prod/parity_f10.json (cdaa197e, device file parity_f10.py sha256 fed8b141): pair_stats.total_FS_vs_T171 fund_ema/fund_now, score_family_substitution fund
- f10_arrays.npz check in this builder (sha 45ae872026c0)
- uplift_r2_2026-09-13/T4b/RESULT_T4b_v2main_feature_skew_2026-09-13.md §0-§4; AUDIT_TRAIN TRN-05, TRN-17

Recommended action: Decide the column-80 caliber for both models at once (PROD-04); give the monthly panel a row for every training anchor (TRN-17).

### PROD-40 · FX-PROD P9: the producer labels short-to-long interval-switch rows by the backward gap and inflates rn 2-4x

- **Layer:** PRODUCER / funding append (cross-reference)  
- **Status:** OPEN_MEASURED_MATERIAL · **Severity:** P2 — As assessed by FX-PROD; cross-referenced so the served-input register is complete.  
- **Affects:** live_trading, future_eval · **Method:** CITED (FX-PROD P9)

Owned by FX-PROD (fix in progress, not re-derived here). It reaches every served consumer of rn: king and V2MAIN column 80 (v1 EMA), the fund leg's base-distribution rank, FTRIM's rn8 classification (PROD-24) and the carry estimate.

Evidence:
- shadow_loop_v3.py (e9c98374) L342
- shadow_loop_v3.py (e9c98374) L344
- combo_stage.py (b5c698f9) L243
- FX-PROD P9 (lead message; docs/fixprogram_2026-09-13/FIXPROGRAM_2026-09-13.md)

Recommended action: Follow FX-PROD P9; after its fix, re-read PROD-24 FTRIM counts and the column-80 contrast.

## 5. Devices, receipts and commands

| Device | sha256 | commits (newest first) |
|---|---|---|
| docs/audit_pipeline_2026-09-13/devices_prod/members/members_stage.py | `95c82ec9a9c11b5b…` | 84e7aa56 d9be5cb4 |
| docs/audit_pipeline_2026-09-13/devices_prod/members/members_stage.sh | `89a0a9a4ca226d91…` | 84e7aa56 d9be5cb4 |
| docs/audit_pipeline_2026-09-13/devices_prod/members/members_audit.py | `7bc0a664158004ed…` | fbab3d22 d9be5cb4 |
| docs/audit_pipeline_2026-09-13/devices_prod/members/members_run_pod2.sh | `6500cbcd7e8c13b2…` | 6ce1b9d5 d9be5cb4 |
| docs/audit_pipeline_2026-09-13/devices_prod/state/state_seat_ledger_probe.py | `892582a7ac0c5f74…` | ebf1ceaa |
| docs/audit_pipeline_2026-09-13/devices_prod/state/state_combo_timing_probe.py | `494354cdf1ef7e61…` | a9c22ac4 |
| docs/audit_pipeline_2026-09-13/devices_prod/parity/parity_x0910_extract.py | `d410a3eb7e567c1d…` | c52af4ce |
| docs/audit_pipeline_2026-09-13/devices_prod/parity/parity_run_pod2.sh | `2e612aa01ec6c31e…` | c52af4ce |
| docs/audit_pipeline_2026-09-13/devices_prod/parity/parity_king.py | `fad9f3c217041b02…` | 3e71e0de |
| docs/audit_pipeline_2026-09-13/devices_prod/parity/parity_f10.py | `fed8b14187cfea29…` | 1127261e a0222c39 d76ed216 |
| docs/audit_pipeline_2026-09-13/devices_prod/parity/prod_target_checks.py | `2bd626fd7b17aeb9…` | 1b02c837 b59fb791 |
| docs/audit_pipeline_2026-09-13/devices_prod/parity/parity_run_mac.sh | `0b15ccbb9b206a1a…` | 3e71e0de |
| docs/audit_pipeline_2026-09-13/devices_prod/parity/pod2_provenance.sh | `3fbed0bb6b8a17fc…` | e9debe97 |
| docs/audit_pipeline_2026-09-13/devices_prod/build/build_audit_prod.py | `8471b88c010413e7…` | b3b34e8d |

Receipts (sha256): `parity_king.json` 9dbba68bab9b…; `parity_king_columns.csv` ef57d271c94e…; `parity_f10.json` cdaa197ed78e…; `parity_f10_columns.csv` dee1047f4e37…; `members_audit.json` eb8d5da70fd9…; `prod_target_checks.json` f8113efe3e20…; `state_seat_ledger_probe.json` 97a02d3cb1bc…; `state_combo_timing_probe.json` 67654ea56ae3…; `parity_x0910_extract.json` 00cc505a057c…; `pod2_provenance.txt` a7b8a4ad8fed….

Verbatim commands: Mac `bash docs/audit_pipeline_2026-09-13/devices_prod/parity/parity_run_mac.sh king|f10|checks`; pod2 `bash /workspace/aud_prod_2026-09-13/parity/device/parity_run_pod2.sh extract` and `bash /workspace/aud_prod_2026-09-13/members/device/members_run_pod2.sh`; state probes `env -i PATH=/usr/bin:/bin HOME=/Users/haosiyu /Users/haosiyu/wide_shadow/venv/bin/python -B <device> PATH,HOME,LC_CTYPE,__CF_USER_TEXT_ENCODING`; provenance `bash docs/audit_pipeline_2026-09-13/devices_prod/parity/pod2_provenance.sh`; this document `env -i PATH=/usr/bin:/bin HOME=/Users/haosiyu /Users/haosiyu/wide_shadow/venv/bin/python -B docs/audit_pipeline_2026-09-13/devices_prod/build/build_audit_prod.py PATH,HOME,LC_CTYPE,__CF_USER_TEXT_ENCODING`.

Failed or superseded runs kept: members_audit run 1 (env refused) and run 2 (stopped, slow assert) on pod2; parity_f10 run 1 (`receipts_prod/parity_f10_run1_d76ed216_FAILED_missing_weights_stdout.log`, no comparison numbers); prod_target_checks run 1 (`prod_target_checks_run1_b59fb791.json`, superseded by the revision that records the target_w ratio).

## 6. Not checked

- Book layer (P&L) of every model-input item: PROD-01/02/03 for 8d79186b and PROD-06/07/08/09 for V2MAIN are measured at the feature and score layers only.
- Parity before 2026-09-05 16Z: served king inputs exist for 47 anchors (09-05 16Z..09-13 08Z) and served V2MAIN inputs are reproduced for 17 overlap anchors (09-05 16Z..09-10 20Z) plus 6 bitwise anchors; one regime, no crash anchors; the 29ffaf58 era (08-16..09-01) not covered.
- V2MAIN column parity against the in-service model's own training rows (dlw_ext / f8_ext, pre-holefix cache, trained through 08-30): the x0910 rows built by the same builders on the holefix2 cache stand in; the ext rows were not compared.
- The fund leg's served inputs (xz_in_base over the exchange base list) against any research panel; the rev24 leg (computed, masked out of combo); the king-form fallback path's parity.
- The row count and model effect of E-0909-A in 8d79186b's training rows (PROD-34) and of the zero fund columns / pre-holefix cache in V2MAIN's (PROD-35).
- FX-PROD P9's truth table (cross-referenced, not re-derived); T5d; T5b numbers (cited).
- Other launchd jobs (c2shadow, universe_shadow, w4liqcapture, depthwatch, regime_dash) beyond confirming they do not write target_live/target_combo; the Telegram paths inside combo_stage.
- Executor internals beyond reading the 12Z anchors/orders rows and legs.py/anchor_loop.py for EXE-03 (aud-exec scope); why PIEVERSEUSDT was capped after the reshape.
- Why the combo book is persistently net short (EMA band freeze, keep-mask exits, cap clipping): the net is measured, its cause is not.
- jpline (not accessed); pod2 GPU (not used).

