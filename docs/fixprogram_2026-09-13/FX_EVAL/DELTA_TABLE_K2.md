> **创建:** 2026-09-13T13:18:40Z | **Session:** FX-EVAL (K2) session_01BzpuBRGZh8oPvpD8NgqsME | **状态:** 冻结(sha 见 DELTA_TABLE_K2_FREEZE.txt; 先于本项打开任何受影响结果收据) | **作废条件:** 只能以带日期的 AMENDMENT 另立并先记 sha

# K2 δ 表与机械重标规则

机器版 `DELTA_TABLE_K2.json`(含每个来源的文件:行、原文、sha、首次入库提交、该行最后提交)。

## 换算(脚本算, 输入 = T2 PREREG L38 的 A0 基线事实)

```
{
 "inputs": {
  "g_A0_WALPHA_s42_bps": 0.6341957,
  "sharpe_A0_WALPHA_s42": 1.2912234,
  "anchors_per_year": 2190,
  "gross_over_nav": 2.0,
  "sigma_g_bps": 22.984971130967786
 },
 "D1": {
  "share_of_A0_WALPHA_net": 0.07884001736372542,
  "annualised_sharpe": 0.10180007527644859,
  "nav_pct_per_year_at_gross2": 2.19
 },
 "T2_ceiling_0p11": {
  "share_of_A0_WALPHA_net": 0.17344803820019591,
  "annualised_sharpe": 0.22396016560818688,
  "nav_pct_per_year_at_gross2": 4.8180000000000005
 },
 "R22_EFF_LO_0p02": {
  "share_of_A0_WALPHA_net": 0.03153600694549017,
  "annualised_sharpe": 0.04072003011057943,
  "nav_pct_per_year_at_gross2": 0.8760000000000001
 },
 "T5d_band_0p25": {
  "share_of_A0_WALPHA_net": 0.3942000868186271,
  "annualised_sharpe": 0.5090003763822429,
  "nav_pct_per_year_at_gross2": 10.95
 },
 "T2_resolution_0p23": {
  "share_of_A0_WALPHA_net": 0.3626640798731369,
  "annualised_sharpe": 0.4682803462716635,
  "nav_pct_per_year_at_gross2": 10.074000000000002
 }
}
```

## δ

| key | 统计量族 | 单位 | δ | 用法 | 理由 | 敏感性(不定标签) |
|---|---|---|---|---|---|---|
| D1 | book_dg | bps / 4h anchor / unit gross (g = net_ex / gross_total; paired Δg or a component of it: price, carry, cost) | 0.05 | two-sided R-EQ unless the rule states one-sided R-LINE | (1) the programme's own pre-declared materiality line for book-level effects in this unit (PROGRAM_uplift_r2 L155, written when T5b was dispatched; SPEC_T5b L62 / L122 frozen before any T5b number) · (2) economic size (scripted, CONV.D1): 7.9 % of the A0 W_ALPHA mean net 0.6341957; +0.10 annualised Sharpe at A0's σ; 2.19 % NAV per year at gross 2.0 · (3) half of the T2 frozen ceiling for an entire carry-sizing redesign (0.11 bps ⇒ ≤ +0.2 Sharpe, T2 PREREG L10): a difference below half of what the programme's largest plausible structural uplift could buy is not decision-relevant · (4) inside the strategy-change scale the replay instrument was built to judge, [0.02, 0.60] bps (PREREG_parity_materiality L15) · (5) NOT the source: T4 RESULT quotes '±0.05 bps/锚' as its CI half-width (a resolution, result-derived); the coincidence is recorded, the line above is the source | [0.02, 0.25] |
| D2 | book_dsharpe | annualised Sharpe (per-anchor Sharpe × √2190) | 0.1 | two-sided R-EQ | (1) D1 converted at A0 W_ALPHA σ (CONV.D1.annualised_sharpe = 0.1018, rounded to 2 dp) · (2) used only where a document asserts ΔSharpe equivalence (L4 / L4b prose check, P2 ΔSharpe if ever labelled) | [0.041, 0.509] |
| D3 | nav_dg_2x | bps / 4h anchor of NAV at gross 2.0 | 0.1 | two-sided R-EQ | (1) D1 × gross 2.0 (constant_leverage_2.00); for series already levered (L4b multiplies A0 g by 2.0) | [0.04, 0.5] |
| D4 | score_dic | rank-IC (per-anchor cross-sectional Spearman, window mean over anchors) | 0.003 | two-sided R-EQ | (1) ≈ 5 % (4.8 %) of the canonical wide-450 king score-layer IC 0.063 raw (PREREG_leg_ablation L6): a one-twentieth change in the king's ranking skill · (2) equals the project's standing minimum incremental-alpha line (#29: an added channel must earn ≥ +0.003; DLv2 acceptance prereg L55) · (3) NOT book-economic: the IC→book mapping is refuted twice (PREREG_leg_ablation L58 §4.3), so an EQUIVALENT at D4 is a score-scale statement and cannot by itself carry 'NOT MATERIAL' for the book | [0.0015, 0.006] |
| D5 | share_of_gap | fraction of the deployed − replay gap attributed by Shapley (dimensionless) | 0.05 | two-sided R-EQ; NOT NEGLIGIBLE established ⇔ CI beyond ±0.20 | (1) the addendum's own declared negligibility band \|share\| ≤ 0.05 (and ≥ 0.20 'not negligible'), now applied to the CI instead of the point · (2) DISCLOSED: the spec line was committed in the same commit as its receipt (39ec7c1e) — it is not provably pre-declared; it is the only declared band for this unit | [0.025, 0.1] |
| D6 | t1_relative | fraction of the T1 reference level (dimensionless) | 0.25 | rules R-T1H1 (one-sided), R-T1H3 (one-sided), R-T1H5 (two-sided) | (1) T1's own pre-registered relative lines (H1 ratio 0.25, H3 NO-DROP 0.25, H5 0.25), frozen before any T1 number; K2 changes only the object they are applied to (verdict interval instead of point) and makes the reference conservative where the receipt stores its interval | [0.125, 0.5] |
| D7 | t8_useful_r | pooled out-of-sample Pearson r (T8 §6) | 0.03 | one-sided R-LINE: usefulness excluded ⇔ CI95 upper < 0.03 under k=0 and k=9 | (1) T8's own frozen usefulness line C1 (r ≥ 0.03), inherited from the project's perceptibility gate \|corr\| ≥ 0.03 (adaptive_turnover_family_closed, quoted in PREREG_T8 L16) · (2) the frozen FAIL consequence ('cannot predict at this resolution') is an absence claim; it needs r < 0.03 to be excluded from above, which a failed C1/C3 does not establish | [0.015, 0.06] |
| D8 | t5b_carry_line | bps / 4h anchor / unit gross, positive = carry paid | 0.05 | one-sided R-LINE, material side = upper (paid ≥ 0.05) | (1) identical to D1 and to SPEC_T5b's own frozen line; K2 applies it to the CI95 upper instead of the point | [0.02, 0.25] |
| D9 | r22_scale_far | bps / 4h anchor / unit gross | 0.00666667 | compliance recomputation only (closed boundary ≤ as frozen) | (1) R22 v2 frozen SCALE_FAR = EFF_LO / 3 | [] |
| D10 | t3_cost_line | bps per unit turnover | 1.6 | compliance recomputation only | (1) T3 frozen gate (PROGRAM §2 T3 / AMENDMENT 1 item 3) | [] |

### 来源锚点

- D1 ← `multi_asset/exports/research/uplift_r2_2026-09-13/PROGRAM_uplift_r2_2026-09-13.md:155` (首次入库 eca56ac6 2026-09-13T12:50:06+08:00; 该行最后提交 eb9939df 2026-09-13T07:42:15Z): - 派 **T5b**(只读): Q1 FTRIM 置零不强平 + EMA 0.1 + 带宽冻结残余空头的数量/gross/付出 carry(读法先冻结: 均值 ≥ 0.05 bps/锚/gross = 实质); Q2 执行器止损是否对八月队列触发及持仓对目标; Q3 执行器是否另有冻结。P2 已被告知把执行器逐名止损
- D1 ← `multi_asset/exports/research/uplift_r2_2026-09-13/T5b/SPEC_T5b.md:62` (首次入库 eaa08cd9 2026-09-13T16:08:15+08:00; 该行最后提交 eaa08cd9 2026-09-13T08:08:15Z): - **FROZEN-RESIDUAL-MATERIAL ⇔ X̄ ≥ 0.05; 否则 NOT MATERIAL。**
- D1 ← `multi_asset/exports/research/uplift_r2_2026-09-13/T5b/SPEC_T5b.md:122` (首次入库 eaa08cd9 2026-09-13T16:08:15+08:00; 该行最后提交 eaa08cd9 2026-09-13T08:08:15Z): - **Ȳ = W1 ∩ NORMAL 锚上 `GAP_EXECFREEZE(A)` 的均值。EXECUTOR-ADDED-FREEZE-MATERIAL ⇔ Ȳ ≥ 0.05 bps / 锚 / 单位 gross; 否则 NOT MATERIAL。** CI k = 601。
- D1 ← `multi_asset/exports/research/uplift_r2_2026-09-13/T2/PREREG_T2_carry_net_sizing_2026-09-13.md:38` (首次入库 42a59c30 2026-09-13T14:02:41+08:00; 该行最后提交 42a59c30 2026-09-13T06:02:41Z): Baseline facts carried from r15/r18 (VERIFIED there; re-asserted by the T2 judge): A0 s42 W_ALPHA g **0.6341957**, Sharpe **1.2912234**, matched turnover **0.05
- D1 ← `multi_asset/exports/research/uplift_r2_2026-09-13/T2/PREREG_T2_carry_net_sizing_2026-09-13.md:10` (首次入库 42a59c30 2026-09-13T14:02:41+08:00; 该行最后提交 42a59c30 2026-09-13T06:02:41Z): **Ceiling, frozen before any number (program P5).** Uncompensated carry ≈ 0.480 × 0.23 ≈ **0.11 bps/anchor/unit gross ⇒ ≤ +0.2 Sharpe**. A Δg point estimate abo
- D1 ← `docs/PREREG_parity_materiality_2026-09-13.md:15` (首次入库 9383ee21 2026-09-13T08:31:24+08:00; 该行最后提交 9383ee21 2026-09-13T00:31:24Z): > **把回放当作线上书的替身去测一个 0.02–0.6 bps/锚 的策略改动时, 装置自身的偏差会不会污染判决?**
- D1 ← `multi_asset/exports/research/uplift_r2_2026-09-13/T5d/PREREG_T5d_iv_corrected_replay_2026-09-13.md:54` (首次入库 a230a5f2 2026-09-13T20:18:12+08:00; 该行最后提交 a230a5f2 2026-09-13T12:18:12Z): - **经济等价带** δ = 0.25 bps/锚(A0 全周期净额 +0.6342 的约 40%; 更大的差对这本书有经济意义)。
- D4 ← `docs/PREREG_leg_ablation_2026-08-26.md:6` (首次入库 10ac9031 2026-08-26T02:27:03+08:00; 该行最后提交 10ac9031 2026-08-25T18:27:03Z): ① funding 腿(当前权重 0.653)是否仍有效? king(LGBM 弹药)与 rev24 是否都正向? ② 满配 171 列的 LGBM 分数 IC 更高(0.082 raw/0.065 resid vs king 0.063/0.048), 为何不能替换 king? ③ V2MAIN 加入后能否证明整书提
- D4 ← `docs/2026-07-09_DLv2_acceptance_protocol_prereg.md:55` (首次入库 9328d3f5 2026-07-09T13:01:44+08:00; 该行最后提交 9328d3f5 2026-07-09T05:01:44Z): - **Channel-addition penalty (#29):** each added input/channel ≈ −0.013 unless it earns ≥ +0.003 net alpha → default net-negative. The bar is incremental-over-b
- D4 ← `docs/PREREG_leg_ablation_2026-08-26.md:58` (首次入库 10ac9031 2026-08-26T02:27:03+08:00; 该行最后提交 28d5cb7f 2026-08-25T19:04:23Z): - **判据 §4.3 触发**: LGBM-K171 的分数 IC 是 V2MAIN 的 **≈4×**(逐年 0.095/0.085/0.085/0.082 vs 0.056/0.040/0.022/0.021), 但换进书里 φ0.45 **−0.026**、φ1.0 **−0.184**, 而 IC 低 4 倍
- D5 ← `multi_asset/exports/research/uplift_r2_2026-09-13/T5/ADDENDUM_1_SPEC_T5_2026-09-13.md:9` (首次入库 39ec7c1e 2026-09-13T15:39:48+08:00; 该行最后提交 39ec7c1e 2026-09-13T07:39:48Z): - **读法(描述)**: \|φ_K1 占比\| ≤ 0.05 ⇒「H2b 对本窗建模 carry 差的代理贡献可忽略」; ≥ 0.20 ⇒「不可忽略」; 其余「小」。**限定**: 这是回放 king 模型(2026 年 = 8d79186b)在 v1 馈入下的变化, 不是窗内实际服务的 29ffaf58; 不能替代主
- D6 ← `multi_asset/exports/research/uplift_r2_2026-09-13/T1/PREREG_T1_edge_diagnosis_2026-09-13.md:110` (首次入库 320396f1 2026-09-13T14:16:23+08:00; 该行最后提交 320396f1 2026-09-13T06:16:23Z): - 单格判定(S, T): **EXPLAINS** ⇔ D_T 判决区间上界 < 0 且 MIX 判决区间上界 < 0 且 MIX/D_T ≥ 0.5; **DOES-NOT-EXPLAIN** ⇔ D_T 判决区间上界 < 0 且(MIX 判决区间含 0 或 MIX/D_T < 0.25); 其余(含 D_T 不显
- D6 ← `multi_asset/exports/research/uplift_r2_2026-09-13/T1/PREREG_T1_edge_diagnosis_2026-09-13.md:132` (首次入库 320396f1 2026-09-13T14:16:23+08:00; 该行最后提交 320396f1 2026-09-13T06:16:23Z): - 单格: **HALF-LIFE** ⇔ ΔE1 判决区间上界 < 0 且 E0_T ≥ 0.75·E0_H1 且 ΔE0 判决区间含 0(晚段边没了、早段边还在)。**LEVEL** ⇔ ΔE0 判决区间上界 < 0 且 (E0_T/E0_H1) ≤ (E1_T/E1_H1) + 0.25(早段跌得不比晚段少 = 
- D6 ← `multi_asset/exports/research/uplift_r2_2026-09-13/T1/PREREG_T1_edge_diagnosis_2026-09-13.md:146` (首次入库 320396f1 2026-09-13T14:16:23+08:00; 该行最后提交 320396f1 2026-09-13T06:16:23Z): - **H5 存活(不同)** ⇔ \|c1 差\| ≥ 0.50 且(Δπ 在 D2 与 REAL 上判决区间都不含 0, 或 Δσs 在 D2 与 REAL 上判决区间都不含 0)。**H5 证伪(相同)** ⇔ \|c1 差\| ≤ 0.20 且四个判决区间都含 0 且 \|Δπ\| ≤ 0.25\|π_2023\|、\|Δσs\|
- D7 ← `multi_asset/exports/research/uplift_r2_2026-09-13/T8/PREREG_T8.md:184` (首次入库 844cd412 2026-09-13T17:59:38+08:00; 该行最后提交 844cd412 2026-09-13T09:59:38Z): - C1: `r_pool ≥ 0.03`
- D7 ← `multi_asset/exports/research/uplift_r2_2026-09-13/T8/PREREG_T8.md:195` (首次入库 844cd412 2026-09-13T17:59:38+08:00; 该行最后提交 844cd412 2026-09-13T09:59:38Z): **后果(冻结)**: FAIL ⇒ 「在本分辨率下, 这组锚时状态(§4)与这个模型家族(§5)不能预测下一锚书收益; 建立在这组状态上的监控 / 调节层是装饰」—— 限定于本状态集、本家族、本分辨率, 不是普遍不可能。PASS ⇒ 只开 S2 预注册, 范围限于过门的目标; 不产生书行为提案; S2 必须处理 §9
- D9 ← `multi_asset/exports/research/parity_replay_2026-09-12/devices/materiality_probe_v2.py:93` (首次入库 23b0084c 2026-09-13T09:31:10+08:00; 该行最后提交 23b0084c 2026-09-13T01:31:10Z): SCALE_FAR = EFF_LO / 3.0          # 0.0066667  "far below the 0.02-0.6 scale"
- D10 ← `multi_asset/exports/research/uplift_r2_2026-09-13/T3/devices/t3_passive_rev.py:19` (首次入库 a2cb8e4d 2026-09-13T13:52:28+08:00; 该行最后提交 a2cb8e4d 2026-09-13T05:52:28Z): GATE_BPS = 1.6                                                      # PROGRAM §2 T3 / AMENDMENT 1 item 3 (P6: 1.6036)

## 规则

- **R-EQ**: two-sided, per interval [lo, hi] at two-sided level c: EQUIVALENT ⇔ −δ < lo ∧ hi < δ (TOST at α = (1−c)/2 per side; with c = 0.95 that is α = 0.025, stricter than the usual 90 % CI TOST); NOT EQUIVALENT ⇔ lo ≥ δ ∨ hi ≤ −δ; INCONCLUSIVE otherwise. Non-finite lo/hi, lo > hi, δ ≤ 0 or non-finite ⇒ error, never a label.
- **R-LINE**: one-sided materiality line L, material side 'upper': BELOW LINE (not material, established) ⇔ hi < L; AT/ABOVE LINE (material, established) ⇔ lo ≥ L; INCONCLUSIVE otherwise. Side 'lower' mirrors.
- **R-SEEDS**: a rule that needs several intervals jointly (seeds, cells): aggregate EQUIVALENT / BELOW ⇔ every member is; NOT EQUIVALENT / AT-ABOVE ⇔ every member is; else INCONCLUSIVE, with seed_conflict flagged when both extremes occur.
- **R-DIR**: direction labels are the device's own frozen rule recomputed verbatim and never changed; in the judge_v4 / P2 shape (A) ⇔ all seeds point > 0 ∧ lo > 0, (B) ⇔ all seeds hi < 0, else (C); (C) is split by R-SEEDS∘R-EQ into (C) EQUIVALENT / (C) INCONCLUSIVE / (C) NOT EQUIVALENT, and no no-difference branch may be evaluated before (A)/(B).
- **R-LOSS**: a label containing LOSS may name a book only if that book's realised window mean (the stored point) is < 0. Shared-loss reading on return outcomes (price, net): both realised means < 0, then the paired difference by R-SEEDS∘R-EQ(D1): EQUIVALENT ⇒ 'SHARED LOSS, DIFFERENCE EQUIVALENT WITHIN ±δ' (the only form that may be read as 'the strategy's own loss'); NOT EQUIVALENT ⇒ 'SHARED LOSS, MATERIAL DIFFERENCE'; INCONCLUSIVE ⇒ 'SHARED LOSS, DIFFERENCE INCONCLUSIVE'; otherwise 'NOT A SHARED LOSS (<who> lost)'. Carry and cost outcomes get R-EQ only, never loss wording.
- **R-T4**: NOT MATERIAL ⇔ book (A) R-SEEDS∘R-EQ(Δg CI95, D1) = EQUIVALENT ∧ (B) R-EQ(ΔIC CI95, D4) = EQUIVALENT; MATERIAL (established) ⇔ book aggregate NOT EQUIVALENT ∨ ΔIC NOT EQUIVALENT; otherwise INCONCLUSIVE. The book-only reading is reported beside; the stored significance flags condA/condB are reported unchanged.
- **R-T1H1**: DOES-NOT-EXPLAIN (established) ⇔ D_T vci_hi < 0 ∧ MIX vci_lo > −0.25·|D_T vci_hi| (union bound: |D_T| ≥ |vci_hi| and MIX > −0.25·|vci_hi| ⇒ MIX/D_T < 0.25); EXPLAINS as frozen; else UNDECIDED; H1 aggregates by T1's own rule.
- **R-T1H3**: HALF-LIFE and LEVEL as frozen; NO-DROP (established) ⇔ ΔE1 vci_lo > −0.25·|E1_H1| with E1_H1 at its stored point (no interval stored ⇒ the reference uncertainty is ignored: declared non-conservative); else UNDECIDED; H3 aggregates by T1's own rule.
- **R-T1H5**: FALSIFIED (same mechanism, established) ⇔ |c1 difference| ≤ 0.20 ∧ each of the six contrasts (Δπ, Δσs on D2 / REAL / REAL scaled) has R-EQ(vci, 0.25·m) = EQUIVALENT where m = min(|lo|, |hi|) of the stored CI95 of its 2023 reference if that CI excludes 0 (otherwise not establishable); SURVIVES as frozen; else NOT DECIDABLE.
- **R-T8**: T8 verdicts unchanged. Per cell (model ∈ {R, L} × target ∈ {NET, LONG, SHORT} × seed): usefulness excluded ⇔ pooled r CI95 upper < 0.03 under both k=0 and k=9. The frozen FAIL consequence sentence is licensed only if every cell has usefulness excluded; otherwise the FAIL reads 'failed to detect; usefulness not excluded'.
- **R-T5B**: R-LINE with L = 0.05 (upper = paid) on each reading's stored CI95; mean or CI absent ⇒ NOT RE-LABELLABLE (statistic absent).
- **R-T5ADD**: per seed: NEGLIGIBLE (established) ⇔ R-EQ(share CI95, 0.05) = EQUIVALENT; NOT NEGLIGIBLE (established) ⇔ share CI95 lower ≥ 0.20 ∨ upper ≤ −0.20; else INCONCLUSIVE; seeds by R-SEEDS.
- **R-T2**: verdicts unchanged; per arm × base: R-SEEDS∘R-EQ(W_ALPHA Δg CI95, D1); the BELOW-RESOLUTION flag is re-read as that axis.
- **R-V4**: every JUDGE_v4 receipt: per (contrast, seat) R-DIR recomputed from the stored per-seed delta / ci95 must reproduce the stored verdict prefix; (C) split by R-SEEDS∘R-EQ(ci95, D1); extended-window contrasts likewise (secondary).
- **R-COMPLY**: T3: PASS/FAIL/UNDECIDABLE recomputed from the stored CI and 1.6; R22 v2: scale statement recomputed from the stored U_endpoint; any mismatch is reported.
- **R-PROSE**: after the freeze: committed RESULT text of L4 / L4b and the four decision documents of F21 are searched with the fact-table vocabulary; each hit asserting equivalence of a sampled statistic is re-read with the matching D row; admission statements are recorded as such.
- **R-ABSENT**: a field the rule needs that is absent from the receipt ⇒ NOT RE-LABELLABLE (field absent: <path>); never a default, never skipped silently.
- **R-CI**: the interval used is always the one the frozen rule used for its own label (T4 ci95; T2 W_ALPHA ci95; T1 vci; T8 ci95_k0 and ci95_k9; T5c CI95 k81 levels / k87 difference; v4 ci95; T5b CI95; T5 addendum share CI95); percentile bootstrap intervals are taken as stored, never recomputed.

## 冻结前已看到的数字(非盲; 如实列出)

- T4: book Δg +0.0181 [−0.030, +0.063] / +0.0161 [−0.033, +0.065], ΔIC −0.000101 [−0.000272, +0.000070], '±0.05 resolution' — STATE.md 07:4xZ, PROGRAM_uplift_r2 L158, dispatch message
- T5c: D_K −5.9617, R_K −4.7622 / −5.0654, D−R −1.1996 [−4.1863, +1.5949] / −0.8964 [−3.8669, +1.8074]; net −7.23 vs −5.87 / −6.17 — reviewer REVIEW_round4 §4.1, STATE.md
- T5b: frozen-residual carry −0.120 [−0.245, −0.021] 'NOT MATERIAL (PROVISIONAL)' — PROGRAM_uplift_r2 L171 (grep output)
- T5 addendum: s42 +0.00006 [−0.00041, +0.00055], 0.005 %, NEGLIGIBLE; s2027 +0.00003, 0.003 % — RESULT_T5 L162–163 (incidental grep output)
- T3: c_eff +1.13 [−15.87, +24.74] UNDECIDABLE — STATE.md, memory index
- T2: arm Δg points κ* −0.30 / σ-bins +0.17 / seat −0.03, all UNDECIDED — STATE.md 06:1xZ
- T8: 'r ≈ 0, hit rate = base rate', verdict FAIL; AMENDMENT_1 c_N table (incidental grep output)
- v4 chain: A1−A0 dyn +0.061 [−0.168, +0.287] / +0.048 [−0.171, +0.270], fix +0.005 [−0.076, +0.087] / −0.010 [−0.102, +0.088], (C) — RESULT_v4_chain L10 (incidental grep output)
- R22 v2: mean −0.000146, CI95 [−0.00166, +0.00126] — STATE.md, memory
- T1: H1/H3/H4/H5 NOT DECIDABLE; H3 ΔE1 −135.9 [−257, −15]; H5 72.9 % vs 6.7 %; 'mix explains at most 18 %' — PROGRAM_uplift_r2 L103 (grep output)
- L2 / L4 / L4b / P2 S2: no result number seen
- decision-relevant: T4's stored upper ends (+0.063 / +0.065) were known when D1 was frozen; D1 = 0.05 (PROGRAM L155 line) makes T4 INCONCLUSIVE while the T5d band 0.25 would make it EQUIVALENT. D1 is taken from the programme-level line that predates the T5d band; both are shown as sensitivity so the dependence is visible, not hidden
