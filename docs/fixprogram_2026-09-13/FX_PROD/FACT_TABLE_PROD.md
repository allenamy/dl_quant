> **创建:** 2026-09-13 15:1xZ | **Session:** FX-PROD (fix worker, team-lead dispatch; session b9646a9e) | **状态:** 事实表(P1 / P2 / P5 / P6 / P6-M / P9);每节只追加 | **作废条件:** 生产者 `shadow_loop_v3.py`(e9c98374…)、`fea171/combo_stage.py`(b5c698f9…)、`sidecar_blend.py`(6140790e…)或在役 bundle(MANIFEST af61d597…)换代;所引冻结输入 sha 变化

# FACT TABLE — FX-PROD

Working copy: `/Users/haosiyu/cc_tmp/fx_prod` (git; commit b8917484 = byte-identical live files, sha256 in its message). Line numbers below are of that commit.
Labels: VERIFIED(code) = read in the named file at the named lines; VERIFIED(data) = measured by the named device/receipt; INFERRED = not measured.
Process note: facts P1 §1.1–1.9 and P6 §6.1–6.8 were sent to the lead at 13:3xZ, P9 §9.x at 14:30Z, before the corresponding code commits; this document collects them and was committed after the P1/P6/P2 code commits in the clone (deviation from §0.1 "入库先于代码", disclosed).

## P1 — king column 80 (feature `fund_ema`, X column 76)
| # | fact | receipt | label |
|---|---|---|---|
| 1.1 | Training definition of column 80 = panel `f_fund_ema` (v0): raw rate, wall-clock HL 3d, `acc = first rate; acc += a*(rate-acc)`, `a = 1-0.5**(max(dt,1)/3d)`; value at anchor = state after the last settlement ≤ anchor; stale (anchor − last settlement > 12h) ⇒ NaN; float32 | `retrain_2026-09/pod_panel_ext.py` (db7f0474) L124–133, L153–162 | VERIFIED(code) |
| 1.2 | Feature builder writes `nan_to_num(f_fund_ema)` into column 80, **all 82 columns stored float16** | `retrain_2026-09/pod_fea_ext.py` (02157bda) L61–63, L66, L77–79 | VERIFIED(code) |
| 1.3 | Booster 8d79186b trained on that file (`X = FEA[...].astype(float32)`, fit anchor-year < 2026) | `retrain_2026-09/pod_export_bundle_v3.py` L24–40; T4 RESULT §1 (feature_infos 78/78) | VERIFIED(code+T4 data) |
| 1.4 | Serving: step 4 recursion on `rn = rate*8/iv` (v1); `fe_v[j] = est["acc"]` iff ledger and last settlement ≤ 12h; `FE_ANCH[:, 80] = nan_to_num(fe_v[m])`, float32 | `shadow_loop_v3.py` L336–349, L405–412, L418 | VERIFIED(code) |
| 1.5 | Other consumers of the v1 state stay v1 by design: `base_vals` L417, `fund_z_old` L470, fund leg `xz_in_base` L471; carry L527–528 uses `fn_v`/`iv_v`; combo FTRIM L239–243 uses the ledger last row, not the EMA; `regime_dash.py` reads `aux["ema"]` (dashboard) | code | VERIFIED(code) |
| 1.6 | No v0 state exists anywhere: aux keys {H, base_syms, ema, last_anchor, ledger_tail, prev_close, prev_rec}; bundle has `fund_ema_v1_state.json` only | frozen live aux 09-13 12Z (ae8a1396…); MANIFEST | VERIFIED(data) |
| 1.7 | Live invariants 09-13 12Z: ema names = ledger names = 525; `ema.last_ts == ledger last row` 525/525; ledgers strictly increasing; no rows < 60 s apart | frozen live aux | VERIFIED(data) |
| 1.8 | Old battery pins the defect line verbatim ([9c] `"FE_ANCH[:, 80] = np.nan_to_num(fe_v[m], nan=0)" in src`) and counts `for s in st.live:` == 2 ([9b]) ⇒ fix must be additive | `tests_target_live_output.py` L254–259 | VERIFIED(code) |
| 1.9 | Same-family non-live sites (not changed): `~/wide_shadow/acceptance.py` L116 (08-16 one-off), `fea171/combo_stage_t3c_candidate.py` (not deployed) | grep | VERIFIED(code) |
| 1.10 | Real-shape red: replay at 09-12 12Z reproduces live king weights bitwise; served column 76 ≠ float32(training v0) on 311/400 members, median served/v0 = 2.0 (4h), 5.89 (1h), 1.0 (8h) | `tests_fx_prod.py` P1-R0/R1; `RED_P1_on_b8917484.log` | VERIFIED(data) |
| 1.11 | Full funding history available offline: pod2 `ledger_full.npz` (bea6f575…; zip ∪ fund_aug API, 2020-01-01 → 09-01 02:00Z) ∪ all frozen producer ledgers: 0 rate conflicts; within each name's span the Mac union and pod2 are row-identical | fx_state.full_rows audit | VERIFIED(data) |
| 1.12 | Neighbour not fixed here (P4/P10 with aud-prod): training stores all king columns f16, serving f32 | 1.2 vs 1.4 | VERIFIED(code) |

## P2 — V2MAIN funding panel
| # | fact | receipt | label |
|---|---|---|---|
| 2.1 | F10 features built by the same `dlw_features.py` (29ae6a98) in training and serving: panel row of the anchor, `nan_to_num`, X float16 | `fea171/dlw_features.py` L71–73, L90–94 | VERIFIED(code) |
| 2.2 | In-service F10 mu/sd match v0-with-zeros on 171/171 columns (v1 off by 143–153% on column 80) | T4b RESULT §0, `RECEIPT_T4b_facts_v2main.json` | VERIFIED(T4b data) |
| 2.3 | Serving panel last row: `fe[-1,j] = aux["ema"][s]["acc"]` (v1), `fn[-1,j] = ledger last rate`; no 12h freshness on either column (training: stale ⇒ NaN ⇒ 0) | `combo_stage.py` L134–146 | VERIFIED(code) |
| 2.4 | History rows 0 do not reach the scored anchor (no fix needed) | T4b GATE ZH | VERIFIED(T4b data) |
| 2.5 | `sidecar_blend.py` L131–143 carries the identical panel block and shares `fea171/mini` + `xfer_panel_live.npz` with combo_stage | code diff (first 200 lines equal modulo header/imports) | VERIFIED(code) |
| 2.6 | Shared cache check compares only the anchor (`need = False` if `dlw_targets.E_ts[-1] >= A`); live logs 09-12 16Z..09-13 12Z: combo builds the pipeline ("② 触发 171 管线重跑"), sidecar reuses (③ at ~1.1 s) ⇒ whichever process builds first decides the other's caliber | `combo_stage.py` L113–118; `combo_live.log`, `sidecar_daemon.log` | VERIFIED(code+logs) |
| 2.7 | Real-shape red at 09-12 12Z: live-identical device reproduces live target_live/target_combo (L∞ 0.0); panel ≠ training v0 on 311/400 members (median 2.0); a real member made stale keeps f_fund_ema −1.30e-05 / f_fund_now 5.0e-05; a v1-built mini cache is reused | `RED_P2_on_b8917484.log` | VERIFIED(data) |

## P5 — seat king-leg history
| # | fact | receipt | label |
|---|---|---|---|
| 5.1 | Seat = msharpe over LR[-900:], LR = bundle `leg_returns.npz` rows + `leg_returns_live.json` (950 kept); combo masks rev24 | `shadow_loop_v3.py` L223–239, L455–462; `combo_stage.py` L228–229 | VERIFIED(code) |
| 5.2 | 09-05 seeding: king column for scoring anchors ≤ 08-30 20Z (917 rows) ← v3 bundle leg returns (exporter formula; `slow_pred_pinned` = 8d79186b on v0 features, OOS for 2026); 33 live rows 08-31 00Z..09-05 08Z untouched | `docs/PREREG_deploy_seat_seed_v3_2026-09-05.md` §1, §3 | VERIFIED(doc+receipt) |
| 5.3 | Frozen live file (09-13 12Z) = seeded file rows [48:950] + 48 appended rows, bitwise for all three legs; live-appended scoring anchors 08-31 00Z..09-13 08Z = 81, contiguous; seeded rows remaining 869 | frozen `leg_returns_live.json` (962d65d3…) vs `seat_seed_v3_2026-09-05/leg_returns_live.seeded_v3.json` | VERIFIED(data) |
| 5.4 | The 81 live rows are v1-scored; the 8 rows for scoring anchors 08-31 00Z..09-01 04Z were scored by booster 29ffaf58 (bundle switch served from 09-01 08Z) | STATE §1 (v3 bundle 09-01); score log | VERIFIED(doc) / booster per row INFERRED from the switch time |
| 5.5 | Seeded rows are model-caliber consistent with P1 (8d79186b, v0, OOS) but use the exporter's LR formula (research member set, rank among finite-y4 names, panel y4), not the producer's step-6 formula | `pod_export_bundle_v3.py` L96–106 vs `shadow_loop_v3.py` L424–439 | VERIFIED(code) |
| 5.6 | The 08-16 bundle cache tail (07-07 00:05 → 08-16 00:00) equals the producer snapshot cache on its overlap (3,648 rows × live450 × 7): 0 support and 0 value differences | P5 splice check | VERIFIED(data) |

## P6 — bundle bootstrap
| # | fact | receipt | label |
|---|---|---|---|
| 6.1 | Bootstrap branch loads `ledger_tail = seed rows[-400:]` with stored iv and `ema = fund_ema_v1_state.json`; no consistency check | `shadow_loop_v3.py` L198–205 | VERIFIED(code) |
| 6.2 | Stored-iv consumers: fetch skip `exp_iv` L324–325 (last row), `iv_v` carry log L411 (last row), combo FTRIM `rn8` L239–243 (last row), replay inversions (all rows) | code | VERIFIED(code) |
| 6.3 | Exporters label iv by zip `funding_interval_hours` → fund_aug `intervals` dict (current interval at pull time, applied to every API row) → gap | `pod_export_shadow_bundle.py` L168–207; `pod_export_bundle_v3.py` L199–215 | VERIFIED(code) |
| 6.4 | 08-16 seed (b233a072): 12 names / 545 rows stored ≠ backward gap. Exact EMA impact at seed end of the rows the exact rules repair: PROM −2.75e-3, ACE −5.08e-4, DEXE −3.45e-4, ERA −2.01e-4, BANK −1.15e-4 | `seed_rederive` on the real file | VERIFIED(data) |
| 6.5 | The 7 single July rows of that list (ESPORTS 07-29 20Z, T 07-25 04Z, GWEI 07-22 12Z, EPIC, LAB, PARTI, 1000XEC) are 1h→4h switch rows whose **zip-declared interval is 4 = stored**; the backward gap is wrong there (GWEI zip: 11:00 iv 1 rate 1.25e-05; 12:00 iv 4 rate 5.000e-05) | pod2 `wide_multisrc/funding/{GWEI,ESPORTS}USDT/2026-07.zip` | VERIFIED(data) |
| 6.6 | In-service v3 seed (85f1a1db): EMA `last_ts` = 08-31 00:00Z for 448/450 names while the seed runs to 09-01 00:00Z (exporter `EMA_STATE_JSON` override L225–230) | real files | VERIFIED(data+code) |
| 6.7 | In-service v3 seed labels ONG 08-25 08Z 2.0 (3h gap) with rate 5.000e-05 = 4h interest leg; its exported EMA absorbed the row (exact impact 6.0e-7 at seed end) | `seed_rederive` | VERIFIED(data) |
| 6.8 | Running append path labels every row by backward gap (L341–342) — see P9 | code | VERIFIED(code) |

## P6-M — live state D17 residual
| # | fact | receipt | label |
|---|---|---|---|
| M.1 | An independent full-history rebuild with the producer's stored labels reproduces the frozen live v1 EMA **bitwise for 525/525 names**; stored labels agree across all frozen producer ledgers (0 conflicts) | `migrations/fund_label_ema_correction.py --classes NONE --control` | VERIFIED(data) |
| M.2 | D17 rows still absorbed by the live v1 EMA: 533 rows / 5 names; exact correction now (09-13 12Z): PROM −4.096e-06 (5.12% of acc), ERA −3.00e-07 (0.88%), BANK −1.72e-07 (0.43%), DEXE −5.14e-07 (0.10%), ACE −7.57e-07 (0.03%) | same tool `--classes D17` | VERIFIED(data) |
| M.3 | Corrected state equals the rebuild with corrected labels, max |d| 1.3e-18 over 525 names | same | VERIFIED(data) |

## P9 — settlement interval labelling (live append path)
| # | fact | receipt | label |
|---|---|---|---|
| 9.1 | The exchange-declared interval of a settlement is the schedule in force at the settlement; at schedule changes the backward gap and a fundingInfo read after the settlement can both disagree with it | zip census over 2020–2026-07 (1,538 transition rows: zip = backward regime 889, = forward regime 647) | VERIFIED(data) |
| 9.2 | Exact rules on full zip history (used by P6/P6-M): steady 2,521,513/2,521,515 (XAG/XAU 2026-01-30 16Z exchange anomaly), interest signature 1,111/1,111, cap |rate|=0.02 4h/8h→1h 194/194, last 1h row before a 2–3h gap 92/92. Below 100%: gap 3h into longer 40/41, gap 2h into longer 52/62 | `fx/p9_declared_interval_table.py` receipt V1 | VERIFIED(data) |
| 9.3 | Rule evaluation on 2.52M zip rows (producer timing model; fundingInfo model = declared interval of the next settlement after the read): backward gap (today) final 1047 / at-anchor 1032 / FTRIM flips 58 / EMA cells >1% 73,484; fundingInfo for the latest row 491 / 476 / 16 / 47,656; executor 3-point median retro 283 / 476 / 16 / 10,814 | pod2 `/workspace/fx_prod_p9/P9_rule_eval.json` (5865c62c…) | VERIFIED(data, model stated) |
| 9.4 | Executor records `pilot_log/<day>/funding.jsonl` (36,280 rows, 08-01..09-12): `funding_interval_h` = /fapi/v1/fundingInfo read at pull time, applied to every settlement of that pull (labels short-schedule rows of a batch pulled after a switch with the new interval) | `~/dl_quant_live/live/binance_funding.py` L355–383, L545–550; records | VERIFIED(code+data) |
| 9.5 | Producer-appended transition rows since 08-16 in live names: ONG 08-25 08Z (declared 4, interest signature; stored 2.0), ZKC 09-02 20Z and SOPH 09-11 12Z (likely 4 at 40/41; stored 2.0 ∉ {1, 4}), COTI 08-31 20Z / T 09-06 00Z / SKR 09-07 20Z (unresolved: back 1h fwd 4h, history 74:50) | `P9_declared_interval_table…csv.gz` (b797c85f…) | VERIFIED(data) |
| 9.6 | Producer cold-start first-row default `iv = 8.0` mislabels 62 first rows (61 base names at 07-26 08Z, GRVT 07-31 12Z; zip-declared 4); exact live EMA impact ≤ 3.7e-9 now | correction tool `--classes P9` | VERIFIED(data) |
| 9.7 | aud-train (d): splice, panel builder and exporter apply `AUG_IV.get(s)`; the loader-side guard (P6 `seed_rederive`) repairs and refuses dict-labelled steady runs; the three builder call sites are chain-owned (registered back to lead) | AUDIT_TRAIN (7e1ecf9a); P6 R1 | VERIFIED(code) |
