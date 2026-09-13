> **创建:** 2026-09-13T13:15:52Z | **Session:** FX-EVAL (K2) session_01BzpuBRGZh8oPvpD8NgqsME | **状态:** 事实表(先于代码; 只读码/预注册/决策文档, 未开任何结果收据) | **作废条件:** 被登记装置或文档改动(逐锚 sha 见 JSON)

# K2 事实表 · 「无差 / 不重要 / 不可区分 / 同亏 / 不劣」类标签谓词

机器版: `FACT_TABLE_K2.json`(每个锚点: 文件:行、原文、guarded sha256、HEAD blob)。由 `k2_fact_table.py` 按原文子串定位(不凭行号记忆), 锚点缺失或不唯一即报错。

## 类别

- **SIG-ONLY-NULL**: a no-difference label issued because a CI contains 0 (or a significance gate failed); no equivalence band
- **POINT-IN-BAND**: a no-difference label issued because a POINT estimate lies inside a band; the band exists but the CI is ignored
- **POINT-ONLY-LINE**: a one-sided 'not material' label issued because a POINT estimate is below a materiality line; the CI is ignored
- **CI-OVERLAP-SAME**: a 'same' label issued because one book's point estimate lies inside the other's CI; no band, not a test of the difference
- **LOSS-WITHOUT-SIGN**: a 'loss' label that does not require the realised mean of the book(s) named to be negative (K1 family)
- **BAND-NOT-GATING**: an equivalence band exists and is computed, but the label it should gate is issued without it
- **PRECEDENCE**: the no-difference branch is evaluated before the direction branches, so it can override a significant (A)/(B)
- **ABSENT-AS-NULL**: a missing statistic (None / no rows) falls through to the 'not material' branch
- **FAILED-GATE-AS-ABSENCE**: a failed detection/admission gate is written up as absence of the effect, without an upper bound below a usefulness line
- **PROSE-EQUIVALENCE**: the device label is honest (UNDECIDED), but a decision document restates it as 'indistinguishable'
- **COMPLIANT**: the label is CI-based against an explicit band or economic line in the direction of the claim
- **OUT-OF-SCOPE**: deterministic tolerance, percentile position, set overlap, admission or descriptive output: not a sampling-based no-difference claim

## 表

| id | 线 | 谓词(文件:行) | 标签 | 统计量 / CI | 等价带 | 类别 | 已提交结果 | 重标 |
|---|---|---|---|---|---|---|---|---|
| F01 | T4 | `uplift_r2_2026-09-13/T4/devices/t4_judge.py:67`<br>`uplift_r2_2026-09-13/T4/devices/t4_judge.py:144`<br>`uplift_r2_2026-09-13/T4/devices/t4_judge.py:147`<br>`uplift_r2_2026-09-13/T4/devices/t4_judge.py:150`<br>`uplift_r2_2026-09-13/T4/PREREG_T4_king_feature_skew_2026-09-13.md:59` | MATERIAL; NOT MATERIAL (at this resolution) | (A) book Δg(K1−K0) mean, C0 base, KING_LIVE window, seeds 42 & 2027; (B) ΔIC(K1−K0) mean, KING_LIVE / CI95 UTC-day block bootstrap NB 2000 (r18 boot) | none (the CI half-width is reported as 'resolution') | SIG-ONLY-NULL | `uplift_r2_2026-09-13/T4/receipts/RECEIPT_T4_judge.json` | yes: D1 on (A), D4 on (B), joint rule R-T4 |
| F02 | T5c | `uplift_r2_2026-09-13/T5c/devices/t5c_bridge.py:206`<br>`uplift_r2_2026-09-13/T5c/devices/t5c_bridge.py:207`<br>`uplift_r2_2026-09-13/T5c/PREREG_T5c_september_replay_vs_deployed_2026-09-13.md:69` | STRATEGY'S OWN LOSS (king chain); DEPLOYMENT DIFFERENCE; SAME DIRECTION WITH A GAP; UNDECIDABLE | D_K, R_K window means and paired mean(D_K − R_K), per outcome (price/carry/cost/net), per seed / CI95 UTC-day block bootstrap B 2000 (k 81 levels, k 87 diff) | none; no sign requirement for 'LOSS' | CI-OVERLAP-SAME, LOSS-WITHOUT-SIGN | `uplift_r2_2026-09-13/T5c/receipts/pod2/RECEIPT_T5c_bridge.json` | yes: shared-loss rule R-LOSS with D1 |
| F03 | T5d (in flight, K1 owner) | `uplift_r2_2026-09-13/T5d/devices/t5d_bridge.py:69`<br>`uplift_r2_2026-09-13/T5d/devices/t5d_bridge.py:73`<br>`uplift_r2_2026-09-13/T5d/devices/t5d_bridge.py:77`<br>`uplift_r2_2026-09-13/T5d/PREREG_T5d_iv_corrected_replay_2026-09-13.md:54` | STRATEGY'S OWN LOSS (king chain, target layer); BOTH LOST, DEPLOYMENT GAP; BOTH LOST, UNDECIDABLE; NOT A SHARED LOSS (...); SAME LEVEL | as F02 on three calibers (T5C / FIX / REG) / CI95 UTC-day block bootstrap B 2000 | δ = 0.25 bps/anchor (PREREG_T5d §6.2), computed as `equiv` but the OWN-LOSS / SAME LEVEL labels are gated by `same` (CI overlap), not by `equiv` | BAND-NOT-GATING | — | no (no complete committed result; K1 owner) — reported to lead |
| F04 | T5b Q1 | `uplift_r2_2026-09-13/T5b/devices/t5b_q1.py:248`<br>`uplift_r2_2026-09-13/T5b/SPEC_T5b.md:62` | FROZEN-RESIDUAL-MATERIAL; NOT MATERIAL | mean over W1 of C_FROZ carry (positive = paid), bps/anchor/unit gross / CI95 UTC-day block (k 501) reported, not used by the label | one-sided line 0.05 applied to the point estimate | POINT-ONLY-LINE | `uplift_r2_2026-09-13/T5b/receipts/RECEIPT_T5b_q1.json` | yes: one-sided rule R-LINE with D8 |
| F05 | T5b Q3 | `uplift_r2_2026-09-13/T5b/devices/t5b_exec.py:332`<br>`uplift_r2_2026-09-13/T5b/SPEC_T5b.md:122` | EXECUTOR-ADDED-FREEZE-MATERIAL; NOT MATERIAL | mean of GAP_EXECFREEZE over W1 ∩ NORMAL anchors, bps/anchor/unit gross / CI95 UTC-day block (k 601) reported, not used by the label | one-sided line 0.05 on the point estimate; mean None ⇒ NOT MATERIAL | POINT-ONLY-LINE, ABSENT-AS-NULL | `uplift_r2_2026-09-13/T5b/receipts/RECEIPT_T5b_exec.json` | yes: R-LINE with D8 |
| F06 | T5 ADDENDUM 1 | `uplift_r2_2026-09-13/T5/devices/t5_addendum_h2b.py:93`<br>`uplift_r2_2026-09-13/T5/devices/t5_addendum_h2b.py:94`<br>`uplift_r2_2026-09-13/T5/ADDENDUM_1_SPEC_T5_2026-09-13.md:9` | NEGLIGIBLE; SMALL; NOT NEGLIGIBLE | Shapley φ_K1 share of the deployed−replay carry gap, per seed / CI95 (boot_ratio k 58) stored beside the point; label reads the point only | \|share\| ≤ 0.05 (ADDENDUM_1_SPEC L9) on the point | POINT-IN-BAND | `uplift_r2_2026-09-13/T5/receipts/pod2/RECEIPT_T5_addendum1_h2b.json` | yes: R-EQ with D5 |
| F07 | T2 | `uplift_r2_2026-09-13/T2/devices/t2_judge.py:82`<br>`uplift_r2_2026-09-13/T2/devices/t2_judge.py:163`<br>`uplift_r2_2026-09-13/T2/devices/t2_judge.py:160`<br>`uplift_r2_2026-09-13/T2/PREREG_T2_carry_net_sizing_2026-09-13.md:127` | PROMOTE-candidate; REJECT; UNDECIDED (fails: ...); flag BELOW-RESOLUTION; maxDD/HALT 'not worse' (point, declared decision rule) | paired Δg(arm − A0/NW) W_ALPHA mean per seed; tail maxDD/HALT single-path points / CI95 UTC-day block (and CI99-K) | verdict: none needed (UNDECIDED is not an equivalence claim); flag BELOW-RESOLUTION = \|Δg\| < 0.23 on the point | POINT-IN-BAND | `uplift_r2_2026-09-13/T2/receipts/RECEIPT_T2_judge.json` | yes: equivalence axis R-EQ with D1 beside the unchanged verdict; BELOW-RESOLUTION re-read |
| F08 | T3 | `uplift_r2_2026-09-13/T3/devices/t3_passive_rev.py:263`<br>`uplift_r2_2026-09-13/T3/devices/t3_passive_rev.py:265` | PASS; FAIL; UNDECIDABLE | c_eff bps per unit turnover / CI95 day block | economic line 1.6 bps: PASS ⇔ CI upper < 1.6, FAIL ⇔ CI lower > 1.6 | COMPLIANT | `uplift_r2_2026-09-13/T3/receipts/PASSIVE_REV.json` | no label change possible (CI-based threshold test; UNDECIDABLE ≡ INCONCLUSIVE); value checked mechanically |
| F09 | T1 H1/H1fuel | `uplift_r2_2026-09-13/T1/devices/t1_judge.py:304`<br>`uplift_r2_2026-09-13/T1/devices/t1_judge.py:310`<br>`uplift_r2_2026-09-13/T1/PREREG_T1_edge_diagnosis_2026-09-13.md:110` | EXPLAINS; DOES-NOT-EXPLAIN; UNDECIDED; aggregate SURVIVES / FALSIFIED / NOT DECIDABLE | MIX (mix term) and D_T (price drop), bps/anchor; ratio MIX/D_T point / Bonferroni verdict interval vci (family K) | DOES-NOT-EXPLAIN ⇔ D_T vci_hi < 0 ∧ (MIX vci ∋ 0 ∨ MIX/D_T < 0.25 on points) | SIG-ONLY-NULL, POINT-IN-BAND | `uplift_r2_2026-09-13/T1/receipts/pod2/RECEIPT_T1_judge.json` | yes: R-T1H1 with D6 |
| F10 | T1 H3 | `uplift_r2_2026-09-13/T1/devices/t1_judge.py:419`<br>`uplift_r2_2026-09-13/T1/devices/t1_judge.py:426`<br>`uplift_r2_2026-09-13/T1/PREREG_T1_edge_diagnosis_2026-09-13.md:132` | HALF-LIFE; LEVEL; NO-DROP; UNDECIDED; aggregate SURVIVES / FALSIFIED / NOT DECIDABLE | ΔE1 (late-lag edge change) against 0.25·\|E1_H1\| / verdict interval vci (unused by NO-DROP) | NO-DROP ⇔ ΔE1 point ≥ −0.25·\|E1_H1\| | POINT-IN-BAND | `uplift_r2_2026-09-13/T1/receipts/pod2/RECEIPT_T1_judge.json` | yes: R-T1H3 with D6 |
| F11 | T1 H5 | `uplift_r2_2026-09-13/T1/devices/t1_judge.py:360`<br>`uplift_r2_2026-09-13/T1/PREREG_T1_edge_diagnosis_2026-09-13.md:146` | SURVIVES (different mechanisms); FALSIFIED (same mechanism); NOT DECIDABLE | Δπ and Δσs (LIVE − 2023) on D2 / REAL / REAL scaled; \|c1 difference\| / verdict interval vci | FALSIFIED ⇔ \|c1d\| ≤ 0.20 ∧ all six vci ∋ 0 ∧ \|points\| ≤ 0.25·\|reference points\| | SIG-ONLY-NULL, POINT-IN-BAND | `uplift_r2_2026-09-13/T1/receipts/pod2/RECEIPT_T1_judge.json` | yes: R-T1H5 with D6 |
| F12 | T1 H4 | `uplift_r2_2026-09-13/T1/devices/t1_judge.py:324` | SURVIVES; FALSIFIED; NOT DECIDABLE | ρ = price/carry compensation ratio vs half the H1 ratio / verdict interval vci | FALSIFIED ⇔ vci_lo ≥ 0.5·ρ_H1 on all three live instruments (one-sided, CI-based) | COMPLIANT | `uplift_r2_2026-09-13/T1/receipts/pod2/RECEIPT_T1_judge.json` | no (compliant; reference ρ_H1 at its point — declared boundary) |
| F13 | T1 H2 | `uplift_r2_2026-09-13/T1/devices/t1_h2.py:110` | FALSIFIED; SURVIVES; NOT DECIDABLE | row-level equality of recorded vs snapped intervals / none (deterministic) | explicit tolerance (all mismatches zero; relative diff ≤ 1e-3) | OUT-OF-SCOPE | `uplift_r2_2026-09-13/T1/receipts/RECEIPT_T1_h2.json` | no (deterministic tolerance) |
| F14 | T1 position / addendum | `uplift_r2_2026-09-13/T1/devices/t1_judge.py:402`<br>`uplift_r2_2026-09-13/T1/devices/t1_add_pod.py:228` | ANOMALOUS; WITHIN RANGE GIVEN STATE; INTERMEDIATE; ANOMALOUS-LOW; WITHIN RANGE | percentile of the live-window mean among historical window means / none (position in a reference distribution) | explicit percentile cut-offs 0.025 / 0.10 | OUT-OF-SCOPE | `uplift_r2_2026-09-13/T1/receipts/pod2/RECEIPT_T1_judge.json`<br>`uplift_r2_2026-09-13/T1/receipts/pod2/RECEIPT_T1_addendum1.json` | no (not a two-sample contrast; the reading already carries window-sampling variability) |
| F15 | T5 | `uplift_r2_2026-09-13/T5/devices/t5_bridge.py:426` | SAME NAMES; PARTIAL; DIFFERENT NAMES | M1 = loss share of August cohort names (full population, no resampling) / none | explicit cut-offs 0.5 / 0.2 on a deterministic ratio | OUT-OF-SCOPE | `uplift_r2_2026-09-13/T5/receipts/pod2/RECEIPT_T5_bridge.json` | no (deterministic descriptor) |
| F16 | T8 | `uplift_r2_2026-09-13/T8/devices/t8_judge.py:33`<br>`uplift_r2_2026-09-13/T8/devices/t8_judge.py:96`<br>`uplift_r2_2026-09-13/T8/PREREG_T8.md:195` | PASS; UNDECIDED; FAIL; INVALID | pooled OOS r per model × target × seed (NET / LONG / SHORT) / CI95 k=0 and k=9 per cell (C3) | usefulness line r ≥ 0.03 (C1) is required to PASS; FAIL does not require r's CI upper < 0.03 | FAILED-GATE-AS-ABSENCE | `uplift_r2_2026-09-13/T8/receipts/pod2/RECEIPT_T8_judge.json`<br>`uplift_r2_2026-09-13/T8/receipts/pod2/RECEIPT_T8_fit.json` | yes: one-sided R-LINE with D7 (per cell), aggregated by T8 §8 shape |
| F17 | T4 live / T4b | `uplift_r2_2026-09-13/T4/devices/t4_live_judge.py:3`<br>`uplift_r2_2026-09-13/T4b/devices/t4b_live_judge.py:4` | (descriptive only); gate PASS/FAIL (bitwise / tolerance) | per-anchor deltas; bitwise equality / descriptive / none | n/a | OUT-OF-SCOPE | — | no |
| F18 | L2 | `uplift_r3_2026-09-13/L2/devices/l2_b_common.py:292`<br>`uplift_r3_2026-09-13/L2/devices/l2_b_common.py:294`<br>`uplift_r3_2026-09-13/L2/devices/l2_b_judge.py:133` | PASS; FAIL + fail_label DIRECTION-ABSENT / UNSTABLE / NOT-BEYOND-FUNDING / VARIANCE / NULL / SHIFT / PRECONDITION | G (top-decile minus population), dG vs BASE, per model × target × seed / CI (boot_ci) per statistic | none: DIRECTION-ABSENT ⇐ ¬(G < 0 ∧ G_ci upper < 0); NOT-BEYOND-FUNDING ⇐ ¬(dG < 0 ∧ dG_ci upper < 0) | FAILED-GATE-AS-ABSENCE | — | no committed judge result yet — red test + adoption before the L2 judge runs |
| F19 | L4 | `uplift_r3_2026-09-13/L4/devices/l4_run.py:477`<br>`uplift_r3_2026-09-13/L4/devices/l4_run.py:391` | PASS; FAIL; NOT PASS (multiplicity) | admission rule P0–P3 per arm; nested selection / circular 30-day block CI (P2a/P2b) | admission: FAIL = no arm PASS_unadj (not an equivalence claim); P3 ρ ≤ 0.30 applied to point estimates (adjacent family) | OUT-OF-SCOPE | `uplift_r3_2026-09-13/L4/receipts/pod2/RECEIPT_L4_run.json` | labels: no; RESULT prose checked for equivalence wording after the δ freeze (D2/D3) |
| F20 | L4b | `uplift_r3_2026-09-13/L4b/devices/l4b_marks.py:464`<br>`uplift_r3_2026-09-13/L4b/devices/l4b_marks.py:453` | survives / no arm survives | admission rule per arm / circular block CI | admission; P3 ρ ≤ 0.30 on points (adjacent) | OUT-OF-SCOPE | `uplift_r3_2026-09-13/L4b/receipts/pod2/RECEIPT_L4b_marks.json` | labels: no; prose checked after the δ freeze |
| F21 | v4 chain | `retrain_2026-09/v4_chain_2026-09-09/judge_v4.py:346`<br>`docs/RESULT_v4_chain_retrain_quantify_2026-09-09.md:10`<br>`docs/STATUS_three_questions_2026-09-12.md:128`<br>`docs/RULINGS_requested_2026-09-12.md:14`<br>`docs/RUNBOOK_monthly_retrain_2026-10.md:45` | (A) PROMOTE / (A) INFO; (B) REJECT; (C) UNDECIDED (device) → '(C) 不可区分' (documents) | paired Δg(arm − base), frozen window, per seat × seed / CI95 UTC-day block bootstrap 2000 | device: none needed ((C) never 'non-inferior'); documents: none (read as indistinguishable) | PROSE-EQUIVALENCE | `retrain_2026-09/v4_chain_2026-09-09/receipts/JUDGE_v4.json`<br>`retrain_2026-09/v4_chain_2026-09-09/receipts/JUDGE_v4_g3_s2027.json`<br>`retrain_2026-09/v4_chain_2026-09-09/receipts/JUDGE_v4e_hardened.json`<br>`retrain_2026-09/v4_chain_2026-09-09/receipts/JUDGE_v4e_informational.json` | yes: equivalence axis R-EQ with D1 on every contrast; document readings re-stated |
| F22 | P2 S2 (in flight) | `parity_replay_2026-09-12/phase2/devices/p2_s2_lib.py:375`<br>`docs/PREREG_producer_parity_phase2_oos_2026-09-12.md:271`<br>`uplift_r2_2026-09-13/T2/PREREG_T2_carry_net_sizing_2026-09-13.md:10` | (C) indistinguishable (\|Δg\| < 0.23); (A); (B); (C) UNDECIDED | paired Δg per contrast × window, both seeds / CI95 k=0 (k=9 re-read) | \|Δg\| < 0.23 on the POINT of either seed, evaluated before (A)/(B); 0.23 is the r15/r18 bootstrap resolution, not an economic band | POINT-IN-BAND, PRECEDENCE | — | no committed S2 table yet — red test + adoption before p2_s2_tables runs |
| F23 | R22 v1 (superseded) | `parity_replay_2026-09-12/devices/materiality_probe.py:307` | FIT-STRICT; FIT; PARTIALLY-FIT; UNFIT | U_mean = \|mean\| + CI half-width / CI95 day block | explicit (0.002 / 0.00667 / 0.2); defect in the CI bound (\|m\|+half-width) already corrected by v2 (reviewer 0158f5d1) | COMPLIANT | — | no (superseded; retained byte-identical) |
| F24 | R22 v2 | `parity_replay_2026-09-12/devices/materiality_probe_v2.py:253` | BASELINE-RESIDUAL-FAR-BELOW-0.02-0.6-SCALE; …-COMPARABLE-TO-…; …-ABOVE-… | mean Δg, U_endpoint = max(\|lo\|, \|hi\|) / CI95 day block | U ≤ 0.02/3 (closed boundary) — a TOST-shaped statement | COMPLIANT | `parity_replay_2026-09-12/RESULT_materiality_2026-09-13.md` | no (compliant); boundary convention noted (closed ≤ vs module strict <) |
| F25 | P2 G2 gates | `parity_replay_2026-09-12/phase2/devices/p2_g2c_judge.py:41` | gate PASS / RED | L∞ of weights / targets / none (deterministic) | explicit tolerance 1e-6 | OUT-OF-SCOPE | `parity_replay_2026-09-12/phase2/receipts/G2C_verdict.json` | no (deterministic; K3 owns its anchor binding) |
| F26 | v4 chain tests | `retrain_2026-09/v4_chain_2026-09-09/tests_pipeline_gates.py:545` | assertion on '(C) UNDECIDED' | n/a / n/a | n/a | OUT-OF-SCOPE | — | no; any adoption that renames (C) must update this assertion in the same change |

## 同一词表扫描但无该族标签的目录

- `multi_asset/exports/research/uplift_r2_2026-09-13/T6/devices`: PBO / DSR / nested statistics; no no-difference label (reviewer R4-R2..R4-R4 cover its reading issues)(词表命中 0 行)
- `multi_asset/exports/research/uplift_r2_2026-09-13/T7/devices`: data feasibility only; no return statistic(词表命中 0 行)
- `multi_asset/exports/research/uplift_r3_2026-09-13/L3/devices`: data feasibility only; no return statistic(词表命中 0 行)

## 第二层: 已关闭纲领中的同族词(只列出, 本项不重标; 见报告「未证边界」)

词表: `NOT.?MATERIAL|INDISTINGUISH|indistinguish|NEGLIGIBLE|negligible|NON.?INFERIOR|non.?inferior|NOT.?WORSE|not.?worse|SAME.?LOSS|OWN LOSS|SAME LEVEL|SAME NAMES|DOES-NOT-EXPLAIN|NO-DROP|WITHIN RANGE|DIRECTION-ABSENT|NOT-BEYOND|\"CLOSES\"|不可区分|不劣|追平|持平|可忽略`

| 文件:行 | 原文(截 200) |
|---|---|
| `uplift_2026-09-11/infra2/judge_v4.PROPOSED.py:5` | (A) point>0 and CI lower>0 on both; (B) CI upper<0 on both; (C) otherwise UNDECIDED (never 'non-inferior'). Levels: full-cycle yearly table (negative years explicit, |
| `uplift_2026-09-11/infra2/judge_v4.PROPOSED.py:325` | print("\n== VERDICTS (frozen §4: (A) both seeds point>0 & CI lower>0; (B) both CI upper<0; (C) otherwise UNDECIDED = '未过否决线', never '不劣') ==") |
| `uplift_2026-09-11/r14_estimand/devices/r14_flip.py:110` | "drift is measured separately in RECEIPT_r14_intent and is indistinguishable from zero."} |
| `uplift_2026-09-11/r17_fill_pricing/devices/r17_judge.py:229` | elif all(abs(c[s]["dg"]) < RES_BPS for s in SEEDS): v = "CLOSES" |
| `uplift_2026-09-11/r11_costtruth/scripts/r11_reprice.py:81` | print(f"  Sharpe in SE units: {SR_NEW/SE_SR:.3f}  -> {'INDISTINGUISHABLE FROM ZERO' if SR_NEW < 2*SE_SR else 'still > 2 SE'}") |
| `uplift_2026-09-11/r16_asym_band/devices/analyze16.py:224` | V[xm] = {"a_dg_pos_both": ca, "b_bonf_s42_and_ci_s2027": cb, "c_beats_3_nulls_both": cc, "d_tail_not_worse": cd, "e_lambda_sign_stable": ce, "f_construction_X4_lt_X0": constr, "verdict": verdict} |
| `uplift_2026-09-11/r21_nulls_costbridge/devices/r21_bridge.py:380` | ruling = "REPLAY_OVERCHARGES_vs_OWN_REFERENCE" if lo > 0 else ("REPLAY_UNDERCHARGES_vs_OWN_REFERENCE" if hi < 0 else "INDISTINGUISHABLE") |
| `retrain_2026-09/jp_regime_arms_judge.py:1` | """跨regime战役统一判官 @jpline: 各臂(seat_*/band_*) vs 基线 canonpred_s42(msharpe, 无trim): 2023+ ΔNet 块自举CI / 分年净&夏普 / ES5 / 最坏五分位 / 急跌锚净 / 换手变化。判据(冻结见 PREREG_xregime_2026-09-02): ΔNet CI下界>0 且 逐年无 <-0.3 且 ES5  |
| `retrain_2026-09/jp_universe_judge.py:1` | """宇宙 A/B 判官 @jpline(PREREG addendum §B 判据逐字): U1/U2 vs U0 — ΔNet CI>0 双种子 / ES5 不劣化>10% / 负档空头暴露增幅<=50%; 另报最坏五分位与 U∞ 参照。""" |
| `retrain_2026-09/w10_ftrim_band.py:33` | _CFG = {"FTRIM_MODE": FTRIM_MODE, "FTRIM_LO": FTRIM_LO, "FTRIM_HI": FTRIM_HI, "FTRIM_STAGE": FTRIM_STAGE,  # E-0902-B: 频带键此前缺席自报, 臂产物与基线 config 不可区分 |
| `retrain_2026-09/w10_side_band.py:36` | _CFG = {"W3FIX": W3FIX, "SIDE_KAPPA": SIDE_KAPPA, "FTRIM_MODE": FTRIM_MODE, "FTRIM_LO": FTRIM_LO, "FTRIM_HI": FTRIM_HI, "FTRIM_STAGE": FTRIM_STAGE,  # E-0902-B: 频带键此前缺席自报, 臂产物与基线 config 不可区分 |
| `retrain_2026-09/dl_trainfrac_2026-09-07/scripts/judge_trainfrac.py:108` | # ── §4.3 non-inferiority leg, CORRECT form (E-0907-F): judge CI lower > -delta ── |
| `retrain_2026-09/dl_trainfrac_2026-09-07/scripts/judge_trainfrac.py:109` | p(f"\n## TF-5 · §4.3 non-inferiority vs yearly_s42 — **proper test at δ={DELTA} (E-0907-F): pass ⇔ CI lower > −δ**") |
| `retrain_2026-09/dl_trainfrac_2026-09-07/scripts/judge_trainfrac.py:120` | O["reading"]["non_inferiority"] = ni |
| `retrain_2026-09/seat_round2_2026-09-05/judge_seat2.py:15` | else 不变差 (not-worse) iff all four cells CI95 upper > 0 AND (#cells with point estimate >= 0) >= 3 AND all four cells maxDD(2025->26) <= 1.10 × maxDD_B0(2025->26); |
| `retrain_2026-09/seat_round2_2026-09-05/judge_seat2.py:269` | notworse = all(c["CI_upper>0"] for c in cs) and sum(c["point>=0"] for c in cs) >= 3 and all(c["maxDD<=B0*1.10"] for c in cs) |
| `retrain_2026-09/seat_round2_2026-09-05/judge_seat2.py:270` | v = "REJECT" if reject else ("ADMIT-candidate" if admit else ("不变差" if notworse else "UNDECIDED")) |
| `retrain_2026-09/seat_round2_2026-09-05/judge_seat2.py:292` | OUT["best"] = {"arm": None, "rule": "no ADMIT candidate; 不变差 arms listed in mechanism (PREREG table) order, NOT recommended for deployment", "notworse_arms": nw} |
| `retrain_2026-09/dl_costdose_2026-09-08/scripts/judge_costdose.py:156` | O["reading"]["non_inferiority"]=ni |
| `retrain_2026-09/dl_monthly_wf_2026-09-05/judge_dl.py:9` | Frozen comparison (lead): "monthly not worse than yearly" ⇔ 2025->26 CI95 upper of Δg > 0 AND ΔIC (2025->26<=cut, ic_monthly.py) ≥ 0. No admission decision. |
| `retrain_2026-09/dl_monthly_wf_2026-09-05/judge_dl.py:90` | c["monthly_not_worse_than_yearly"] = bool(c["book_CI95_upper>0"] and c["ic_delta>=0"]) if (d and ic) else None |
| `retrain_2026-09/dl_monthly_wf_2026-09-05/judge_dl.py:92` | print(f"\n===== FROZEN COMPARISON [{T}] 'monthly not worse than yearly' = 2025->26 CI95 upper > 0 AND ΔIC >= 0: " + (f"book Δg {d['mean']:+.4f} [{d['lo']:+.4f},{d['hi']:+.4f}] upper>0={c['book_CI95_up |
| `retrain_2026-09/dl_monthly_wf_2026-09-05/judge_dl.py:93` | + (f"ΔIC {ic['mean']:+.4f} ± {ic['se_anchor']:.4f} CI [{ic['ci95_dayblock'][0]:+.4f},{ic['ci95_dayblock'][1]:+.4f}] >=0={c['ic_delta>=0']}; " if ic else "IC n/a; ") + f"⇒ {c['monthly_not_worse_than_ye |
| `retrain_2026-09/dl_monthly_wf_2026-09-05/render_report.py:93` | P("\n## T8 · Frozen comparison (lead's rule: 'monthly not worse than yearly' ⇔ 2025→26 CI95 upper of Δ(net_ex per gross) > 0 AND ΔIC ≥ 0; no admission decision)") |
| `retrain_2026-09/dl_monthly_wf_2026-09-05/render_report.py:94` | P("\| variant \| book Δg 2025→26 [CI95] (spliced, primary) \| upper>0 \| pure-file sensitivity Δg [CI95] \| ΔIC 2025→26 ± s.e. [CI95] \| ΔIC≥0 \| not worse \|"); P("\|---\|---\|---\|---\|---\|---\|---\|") |
| `retrain_2026-09/dl_monthly_wf_2026-09-05/render_report.py:100` | P(f"\| {t} \| {sd} \| {c['book_CI95_upper>0']} \| {sdp} \| {sic} \| {c['ic_delta>=0']} \| **{c['monthly_not_worse_than_yearly']}** \|") |
| `retrain_2026-09/v4_chain_2026-09-09/judge_v4.py:5` | (A) point>0 and CI lower>0 on both; (B) CI upper<0 on both; (C) otherwise UNDECIDED (never 'non-inferior'). Levels: full-cycle yearly table (negative years explicit, |
| `retrain_2026-09/v4_chain_2026-09-09/judge_v4.py:335` | print("\n== VERDICTS (frozen §4: (A) both seeds point>0 & CI lower>0; (B) both CI upper<0; (C) otherwise UNDECIDED = '未过否决线', never '不劣') ==") |
| `retrain_2026-09/v4_chain_2026-09-09/judge_v4.r1_23c2cda7.py:5` | (A) point>0 and CI lower>0 on both; (B) CI upper<0 on both; (C) otherwise UNDECIDED (never 'non-inferior'). Levels: full-cycle yearly table (negative years explicit, |
| `retrain_2026-09/v4_chain_2026-09-09/judge_v4.r1_23c2cda7.py:82` | print("\n== VERDICTS (frozen §4: (A) both seeds point>0 & CI lower>0; (B) both CI upper<0; (C) otherwise UNDECIDED = '未过否决线', never '不劣') ==") |
| `retrain_2026-09/v4_chain_2026-09-09/judge_v4.r2_17b562fd.py:5` | (A) point>0 and CI lower>0 on both; (B) CI upper<0 on both; (C) otherwise UNDECIDED (never 'non-inferior'). Levels: full-cycle yearly table (negative years explicit, |
| `retrain_2026-09/v4_chain_2026-09-09/judge_v4.r2_17b562fd.py:82` | print("\n== VERDICTS (frozen §4: (A) both seeds point>0 & CI lower>0; (B) both CI upper<0; (C) otherwise UNDECIDED = '未过否决线', never '不劣') ==") |
| `retrain_2026-09/v4_chain_2026-09-09/judge_v4.r3_8b2c13b7.py:5` | (A) point>0 and CI lower>0 on both; (B) CI upper<0 on both; (C) otherwise UNDECIDED (never 'non-inferior'). Levels: full-cycle yearly table (negative years explicit, |
| `retrain_2026-09/v4_chain_2026-09-09/judge_v4.r3_8b2c13b7.py:94` | print("\n== VERDICTS (frozen §4: (A) both seeds point>0 & CI lower>0; (B) both CI upper<0; (C) otherwise UNDECIDED = '未过否决线', never '不劣') ==") |
| `retrain_2026-09/v4_chain_2026-09-09/judge_v4.r4_7f1aa5d6.py:5` | (A) point>0 and CI lower>0 on both; (B) CI upper<0 on both; (C) otherwise UNDECIDED (never 'non-inferior'). Levels: full-cycle yearly table (negative years explicit, |
| `retrain_2026-09/v4_chain_2026-09-09/judge_v4.r4_7f1aa5d6.py:315` | print("\n== VERDICTS (frozen §4: (A) both seeds point>0 & CI lower>0; (B) both CI upper<0; (C) otherwise UNDECIDED = '未过否决线', never '不劣') ==") |
| `retrain_2026-09/v4_chain_2026-09-09/judge_v4.r5_f6850dc3.py:5` | (A) point>0 and CI lower>0 on both; (B) CI upper<0 on both; (C) otherwise UNDECIDED (never 'non-inferior'). Levels: full-cycle yearly table (negative years explicit, |
| `retrain_2026-09/v4_chain_2026-09-09/judge_v4.r5_f6850dc3.py:322` | print("\n== VERDICTS (frozen §4: (A) both seeds point>0 & CI lower>0; (B) both CI upper<0; (C) otherwise UNDECIDED = '未过否决线', never '不劣') ==") |

## 知识库文字中的同族词(计数; K4 / aud-kb 范围, 本项只把 F21 的四处决策文档列为重标对象)

| 文件 | 命中行数 |
|---|---|
| `docs/2026-06-28_FINAL_y600_deliverable.md` | 12 |
| `STATE.md` | 10 |
| `docs/ERROR_LEDGER_2026-08-20.md` | 8 |
| `docs/ONBOARDING_independent_researcher_2026-09-06.md` | 6 |
| `docs/PREREG_xregime_2026-09-02.md` | 6 |
| `docs/RESULT_dl_monthly_walkforward_2026-09-05.md` | 6 |
| `docs/2026-07-02_phase1_findings_appendix.md` | 5 |
| `docs/PREREG_watchdog_cond2_resume_semantics_2026-09-06.md` | 5 |
| `docs/PREREG_producer_parity_phase2_oos_2026-09-12.md` | 4 |
| `docs/RESULT_dl_monthly_gate_2026-09-05.md` | 4 |
| `docs/RESULT_king_window_ftrim_cap_2026-09-07.md` | 4 |
| `docs/2026-07-02_fable_regime_breakthrough.md` | 3 |
| `docs/2026-07-27_FACTOR_MINING_COMPLETE_SPEC.md` | 3 |
| `docs/DESIGN_integrated_and_shorthorizon_2026-08-15.md` | 3 |
| `docs/DESIGN_wide_replay_P3_2026-08-16.md` | 3 |
| `docs/FACTOR_MINING_COMPLETE_SPEC.md` | 3 |
| `docs/REVIEW_codex_onboarding_2026-09-07.md` | 3 |
| `docs/AUDIT_live_vs_replay_2026-09-04.md` | 2 |
| `docs/DESIGN_optimization_path_2026-08-21.md` | 2 |
| `docs/HANDOFF_round4_review_request_2026-09-13.md` | 2 |
| `docs/PREREG_deploy_seat_seed_oos_2026-09-04.md` | 2 |
| `docs/PREREG_retrain_addendum_v2main_2026-09-01.md` | 2 |
| `docs/RESULT_giveback_attribution_live_2026-09-06.md` | 2 |
| `docs/RESULT_king_clip_label_ablation_2026-09-08.md` | 2 |
| `docs/RESULT_v4_chain_retrain_quantify_2026-09-09.md` | 2 |
| `docs/REVIEW_caliber_final_2026-09-04.md` | 2 |
| `docs/STATUS_three_questions_2026-09-12.md` | 2 |
| `docs/SURVEY_arch_modules_2026-08-24.md` | 2 |
| `docs/2026-07-14_crossasset_dualarm_technical_design.md` | 1 |
| `docs/2026-07-15_PROJECT_COMPLETE_PRIMER.md` | 1 |
| `docs/CANDIDATE_wide_v2main_norev24_2026-08-26.md` | 1 |
| `docs/DESIGN_L3_conformer_2026-08-24.md` | 1 |
| `docs/DESIGN_rolling_retrain_2026-08-14.md` | 1 |
| `docs/HANDOFF_round3_b0a573a1_closure_2026-09-10.md` | 1 |
| `docs/HANDOFF_v4_and_live_diag_for_codex_review_2026-09-09.md` | 1 |
| `docs/HANDOFF_v4_pipeline_code_review_2026-09-09.md` | 1 |
| `docs/INCIDENT_daily_loss_trip_2026-08-21.md` | 1 |
| `docs/MULTI_ASSET_Y180_CONCLUDED_MILESTONE_2026_06_15.md` | 1 |
| `docs/PREREG_blend_recompute_2026-08-25.md` | 1 |
| `docs/PREREG_caliber_program_king_clamp_raw_target_2026-09-09.md` | 1 |
| `docs/PREREG_demean_fix_2026-08-25.md` | 1 |
| `docs/PREREG_deploy_dl_recipe_2026-10.md` | 1 |
| `docs/PREREG_deploy_modulation_2026-09-04.md` | 1 |
| `docs/PREREG_deploy_rolling_king_2026-09-05.md` | 1 |
| `docs/PREREG_deploy_universe_2026-09-04.md` | 1 |
| `docs/PREREG_fusion_2026-09-04.md` | 1 |
| `docs/PREREG_holefix_and_window_extension_2026-09-08.md` | 1 |
| `docs/PREREG_king_clip_label_ablation_2026-09-08.md` | 1 |
| `docs/PREREG_king_convexity_2026-09-04.md` | 1 |
| `docs/PREREG_king_window_ftrim_cap_2026-09-07.md` | 1 |
| `docs/PREREG_l1_softmin_2026-09-02.md` | 1 |
| `docs/PREREG_l1ss_shortside_objective_2026-09-02.md` | 1 |
| `docs/PREREG_legs_factors_2026-09-04.md` | 1 |
| `docs/PREREG_legweight_2026-08-25.md` | 1 |
| `docs/PREREG_parity_materiality_2026-09-13.md` | 1 |
| `docs/PREREG_seat_round2_dl_seat_and_net_2026-09-05.md` | 1 |
| `docs/PREREG_universe_dyn_2026-09-04.md` | 1 |
| `docs/PREREG_v4_chain_retrain_quantify_2026-09-09.md` | 1 |
| `docs/REPORT_code_and_research_2026-09-13.md` | 1 |
| `docs/RESULT_dl_full_gradient_window_2026-09-07.md` | 1 |
| `docs/RESULT_live_form_health_check_2026-09-05.md` | 1 |
| `docs/RESULT_rolling_king_monthly_2026-09-05.md` | 1 |
| `docs/REVIEW_codex_early_batch_2026-09-08.md` | 1 |
| `docs/REVIEW_f10_blend_deployment_2026-08-23.md` | 1 |
| `docs/REVIEW_next_edge_brief_2026-09-02.md` | 1 |
| `docs/RULINGS_requested_2026-09-12.md` | 1 |
| `docs/RUNBOOK_deploy_batch1_2026-08-04.md` | 1 |
| `docs/RUNBOOK_monthly_retrain_2026-10.md` | 1 |
| `docs/SURVEY_frontier_dl_xsec_2026-08-22.md` | 1 |
| `docs/TEAM_PROTOCOL.md` | 1 |
| `docs/Y600_V5_SINGH_ALPHA0_HUBER_DESIGN.md` | 1 |
| `docs/v2_autonomous_overnight_2026_06_24.md` | 1 |
