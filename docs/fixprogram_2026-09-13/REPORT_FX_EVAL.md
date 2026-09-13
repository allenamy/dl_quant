> **创建:** 2026-09-13 14:4xZ | **Session:** FX-EVAL (K2), teammate of team-lead | **状态:** 交付待独立研究员复审; 重标为提案, 未改任何 RESULT 原文 | **作废条件:** 冻结 δ 表 `DELTA_TABLE_K2.json`(sha ad6af207…)被改动; 被重标收据或被抽取的旧谓词源码改动(逐文件 sha 见各 JSON)

# REPORT FX-EVAL · K2「无差 / 不重要 / 不可区分 / 同亏」类标签没有经济等价带

纲领: `FIXPROGRAM_2026-09-13.md` §1 K2(来源: 独立研究员第四轮 `REVIEW_round4_code_and_research_2026-09-13.md` §4.3、research `RESULT.md` §6、记忆 `noninferiority_rule_is_not_noninferiority_proof`)。全部产物在 `docs/fixprogram_2026-09-13/FX_EVAL/` 与 `multi_asset/exports/research/common/`。

## 0 结论

1. **缺陷成立且成族**: 在役研究线里 14 个标签谓词在区间含 0、点估计落带内、或门没过时就发出「无差 / 不重要 / 同亏 / 无效应」类判词; 另有 12 个邻近谓词合规或不在此族(§2)。
2. **修法**: 共享模块 `equivalence_labels.py`: δ 必须带单位、经济理由和来源, 且没有默认值; 只有整个区间落在 ±δ 内才发 EQUIVALENT(TOST, 边界严格); 区间整体在带外才发 NOT EQUIVALENT; 其余一律 INCONCLUSIVE。方向判词 (A)/(B) 与 judge_v4 逐字相同(2000 组随机对照 0 处不一致)。含 LOSS 的判词要求所指的书实现均值 < 0。
3. **红 → 绿**: 旧码在 61 个合成格上红 19 格, 恰好等于声明的误判集, 0 崩溃; 新模块 84/84 通过; 17 个变异体全部被杀死(§4–§6)。
4. **重标(提案)**: 347 行, 全部原链复现门通过。结果层要点(§7):
   - T4 由 NOT MATERIAL 改为 **INCONCLUSIVE**。
   - T5c/T5d 价格与净额的「策略自身亏损」改为 **共同亏损、差异不可判**。
   - T8 FAIL 附带的「不能预测」改为 **未检出、有用性未排除**; 其中 NET 四格的有用性已排除。
   - T2 两个臂的「低于分辨率」撤回。
   - T5b 次级读数「重要」撤回。
   - 四份决策文档里六处「(C) 不可区分」改为 **(C) INCONCLUSIVE**。
   - T4 与 v4 固定席位的判词**取决于 δ**: δ = 0.25 时会变成等价, 已列入敏感性。

## 1 问题

「CI 含 0」「点估计在带内」「门没过」都不能证明两者相同或差异可忽略。等价必须是整个区间落在事先声明的经济带内。复审的两个直接例子:
- T4 的 NOT MATERIAL 只由显著性门生成。
- T5c 的 `readings` 在两本都盈利且完全相同的输入上仍写「策略自身亏损」。

## 2 事实表(C1 `adeda8e7`, 13:19:25Z; 先于代码, 只读码 / 预注册 / 决策文档, 未开任何结果收据)

`FACT_TABLE_K2.md/json`(装置 `k2_fact_table.py`): 26 行 · 62 个原文锚点。锚点按子串定位, 缺失或不唯一即报错, 每个锚点带 guarded sha。

| 类别 | 行 |
|---|---|
| SIG-ONLY-NULL(区间含 0 ⇒ 无差 / 无效应) | F01 T4 · F09 T1 H1 · F11 T1 H5 |
| POINT-IN-BAND / POINT-ONLY-LINE(点估计落带或低于线) | F04/F05 T5b · F06 T5 附录 · F07 T2 BELOW-RESOLUTION · F10 T1 H3 NO-DROP · F22 P2 S2 |
| CI-OVERLAP-SAME + LOSS-WITHOUT-SIGN | F02 T5c |
| BAND-NOT-GATING(带已算, 却不管标签) | F03 T5d(δ 0.25 算成 `equiv`, 但「策略自身亏损」由 `same` 发) |
| PRECEDENCE(无差分支先于方向分支) | F22 P2 `p2_s2_lib.py:375` |
| ABSENT-AS-NULL(统计量缺失 ⇒ 不重要) | F05 T5b Q3 |
| FAILED-GATE-AS-ABSENCE | F16 T8 · F18 L2 |
| PROSE-EQUIVALENCE(装置诚实, 文档改写成不可区分) | F21 judge_v4 → 四份文档 |
| COMPLIANT / OUT-OF-SCOPE | F08 T3 · F12 T1 H4 · F23/F24 R22 · F13/F14/F15/F17/F19/F20/F25/F26 |

**更正派工描述一处**: 「judge_v4 的 (C) indistinguishable 0.23 规则」不在 `judge_v4.py` 里。judge_v4 的 (C) 是 UNDECIDED, 注明 never non-inferior, 装置本身是诚实的。0.23「不可区分」出自 P2 预注册 L29/A6.7 与 `p2_s2_lib.py:375`, 其中 0.23 是 r15/r18 的自举分辨率, 不是经济带。把 v4 的 (C) 写成「不可区分」的是决策文档(F21)。

第二层(只列不重标): 已关闭纲领 `uplift_2026-09-11` / `retrain_2026-09` 中同族词 38 处(如 `r17_judge.py:229` CLOSES、`r21_bridge.py:380` INDISTINGUISHABLE、`judge_seat2.py:270`「不变差」); 知识库文字 72 份文件 154 行。

## 3 δ 表(冻结: `DELTA_TABLE_K2.json` sha **ad6af2075ca71ed756be26bbe7759761f981add24f02581de41c3f014643dea6**, 13:19:08Z)

| key | 统计量 | δ | 依据(来源锚点见表) |
|---|---|---|---|
| D1 | 书层 Δg, bps/4h 锚/单位 gross(及价格 / carry / 成本分量) | **0.05** | 纲领 L155 与 SPEC_T5b L62/L122 的「≥0.05 = 实质」线(T5b 数字之前); 脚本换算: A0 W_ALPHA 净额 0.6342 的 7.9%, 约 +0.10 年化夏普, 2.19% NAV/年 @2×; 是 T2 结构性天花板 0.11 的一半; 落在 R22 题面 [0.02, 0.60] 内 |
| D2 | ΔSharpe(年化) | 0.10 | D1 按 A0 σ 换算 |
| D3 | NAV 口径 @2× | 0.10 | 2 × D1 |
| D4 | ΔIC(截面秩 IC) | **0.003** | 正典 king 分数层 IC 0.063 的约 5%; 与 #29 增量 alpha 线 +0.003 一致; **不是书层经济量**(IC→书层映射已被证伪两次) |
| D5 | Shapley 份额 | 0.05 | T5 附录自带带宽; **非可证事先声明**(与收据同一提交 39ec7c1e) |
| D6 | T1 相对线 | 0.25 | T1 预注册 L110/L132/L146; 由作用于点估计改为作用于判决区间, 参照取保守端 |
| D7 | T8 池化 r | 0.03 | T8 C1 线(项目可感知门 \|corr\| ≥ 0.03); 单边, 要求 k0 与 k9 上界都 < 0.03 |
| D8 | T5b carry(正 = 付) | 0.05 | 同 D1, 单边 |
| D9/D10 | R22 / T3 | 0.02/3 · 1.6 | 只作合规复算 |

敏感性(不定标签): D1 ∈ {0.02, 0.25}, D4 ∈ {0.0015, 0.006}, D7 ∈ {0.015, 0.06}, 等。规则 18 条(R-EQ / R-LINE / R-SEEDS / R-DIR / R-LOSS / R-T4 / R-T1H1·H3·H5 / R-T8 / R-T5B / R-T5ADD / R-T2 / R-V4 / R-COMPLY / R-PROSE / R-ABSENT / R-CI)写在同一 JSON 里。

**非盲声明**: 冻结前我已从 STATE、纲领指针、复审报告、派工消息和偶然的 grep 输出看到 T4、T5c、T5b、T5 附录、T3、T2、T8、v4、R22、T1 的部分数字, 逐条列在 JSON `exposure` 里。**与判词直接相关的一处**: T4 上端 +0.063/+0.065 在冻结时已知。D1 取纲领级 0.05 线(早于 T5d 的 0.25 带); 0.25 会把 T4 判成等价, 两者都放在敏感性里, 依赖关系是可见的。恢复后又看到 T5d 提交信息与记忆索引里的数字(冻结之后), **δ 与规则未改一字**(文件 sha 仍为 ad6af207)。

## 4 红证据(C2 `efc2412a`, 13:31:07Z)

- `k2_legacy_predicates.py` 从设备文件按 AST 逐字抽取 13 段现行谓词: T4、T5c、T5b×2、T5 附录、T2、P2、T1 H1/H3/H5、T8、L2、judge_v4。设备只解析、不执行顶层。每段钉 sha, 源码一改即报 LegacySourceChanged。
- `tests_equivalence_labels.py --impl legacy`: 55 格中 **19 红 = 声明误判集**, 36 绿, 0 崩溃(`receipts/red_legacy_C2.log`, rc=1)。例:
  - CI [−0.030, +0.063] → NOT MATERIAL。
  - 两本每锚 +10…+20 → 「STRATEGY'S OWN LOSS」。
  - +0.20 [+0.10, +0.30] 两种子 → P2 先判「(C) indistinguishable」, 盖掉了 (A)。
  - 统计量缺失 → NOT MATERIAL。
  - T8 格 r 0.02、上界 0.05 → FAIL(读作「不能预测」)。
  - L2 G 上界 +0.05 → DIRECTION-ABSENT。
  - T1 MIX 区间含 0 → DOES-NOT-EXPLAIN / 聚合 FALSIFIED。
  - 另有反向误判一格: 显著但在带内(+0.010 [+0.004, +0.016])→ MATERIAL。
- 我的错误一处(日志留档 `red_legacy_run1_TESTDESIGN_ERROR_X09n3.log`): X09n3 真值设错。H3 的 LEVEL 聚合是区间确立的证伪, 不是误判; 改正后重跑。

## 5 修法(C3 `f0cfe770`, 14:13:38Z)

- `multi_asset/exports/research/common/equivalence_labels.py`:
  - `Margin(*, delta, unit, justification≥20 字符, source)` 与 `Interval(*, point, lo, hi, level)`, 都是仅关键字参数且无默认值; NaN / inf / lo>hi 直接拒绝。
  - `equivalence` 按 R-EQ; `one_sided` 按 R-LINE; `aggregate` 要求每个成员同标签, 不许混合两种判法, 冲突时标 seed_conflict。
  - `direction_v4` 与 `v4_label`: (A)/(B) 不变, 只拆 (C)。
  - `shared_loss_reading` 与 `loss_label_admissible` 执行 LOSS 须负的规则。
- `FX_EVAL/k2_rules.py`: 冻结规则的组合。T1 H1 带宽用 |D_T| 的最小可信值(并集界); T1 H5 参照取 CI95 近 0 端; T8 需 k0 与 k9 同时排除; L2 未声明带宽时只能写 NOT ESTABLISHED。
- 只加代码, 未改任何现有设备或结果文件。

## 6 测试 · 邻格 · AST · 变异(C3)

- module 模式 **84/84** rc=0(`green_module_C3.log`, 起止 sha 相同); legacy 复跑 61 格, 红集仍是那 19 格(`red_legacy_C3_rerun.log`)。
- 邻格: 每个误判至少 3 个邻格; C3 新增 6 格(T4 书带内但 IC 带外、T5c 回放亏部署赢、T5b 下端恰在线上、L2 两个边界、v4 一种子显著一种子宽)。原链见 §7 的 G-REPRO。
- AST 核(`k2_ast_retention_check.py`, `ast_retention_C3.log`): C2 断言节点 144 个保留, 改动恰 2 处。两处都是我在首轮 green 时发现的**测试作者错误**(`green_module_run1_TESTDESIGN_ERRORS.log`): 分类器把 `no gap detected` 当成 `gap detected`; M06 末例 lo 恰在线上, 严格边界下 INCONCLUSIVE 才对。新增 17 个节点。
- 变异(`k2_mutation_run.py`): 17 个替换, 对照 84/84。首轮 12 杀、5 存活(`mutation_run1_5_survivors.log`), 分别是:
  - 方向判定去掉 point>0
  - T1H1 带宽改用点估计
  - T8 只看 k0
  - T1H5 参照改用点估计
  - T5 附录单种子即判不可忽略

  补 M17–M21 后次轮 **17/17 全杀**(`mutation_run2.log`)。

## 7 原链与重标(C4 `d0b087db`, 14:31:37Z; 提案)

`k2_relabel.py`: 只读 60 个输入, guarded 读并记 sha; 先用 `k2_materialize.py` 把被 iCloud 驱逐的文件 `brctl download` 回来。
- 每族先过 **G-REPRO**(C2 钉住的逐字旧谓词在存储数字上复现存储标签): T4 / T2 / T5c / T5d / T5b / T5 附录 / T1 / T8 / v4 **全过**。T3、R22 v2 合规复算过; v4 文档所引数字与 `JUDGE_v4.json` 逐项相符(G-PROSE-NUMBERS)。
- 347 行: **WITHDRAWN 126 · REFINED 36 · UNCHANGED 180 · NO_CLAIM 4 · NOT_RELABELLABLE 1**。全表见 `RELABEL_TABLE_K2.md/json`。

**结果层判词变化**(单位 bps/4h 锚/单位 gross; 区间为各装置自己的 CI95 或判决区间):

| 结果 | 原 → 新(提案) | 数字 | δ 依赖 |
|---|---|---|---|
| T4 king 第 80 列(C0, KING_LIVE) | NOT MATERIAL → **INCONCLUSIVE** | 书 Δg s42 +0.0181 [−0.0299, **+0.0625**], s2027 +0.0161 [−0.0332, **+0.0645**] 上端 > 0.05; ΔIC −0.000101 [−0.000272, +0.000070] 在 ±0.003 内 | D1 = 0.25 时为 NOT MATERIAL |
| T4 NW(只报) | 同上 → INCONCLUSIVE | +0.0215 [−0.0225, +0.0631] / +0.0052 [−0.0482, +0.0547] | — |
| T5c KA 价格(两种子) | STRATEGY'S OWN LOSS → **SHARED LOSS, DIFFERENCE INCONCLUSIVE** | D_K −5.9617, R_K −4.7622 / −5.0654(均为负); D−R −1.1996 [−4.1863, +1.5949] / −0.8964 [−3.8669, +1.8074] | 0.02 与 0.25 下都不变 |
| T5c KA 净额 | 同上 | D_K −7.2255, R_K −5.8700 / −6.1742; D−R −1.3556 [−4.3455, +1.4347] / −1.0513 [−4.0539, +1.7055] | 不变 |
| T5c KA carry | 「策略自身亏损」→ **INCONCLUSIVE**(carry 不用亏损措辞) | D−R +0.1803 [−0.2222, +0.6349] / +0.1790 [−0.2259, +0.6343] | — |
| T5c KA 成本 | DEPLOYMENT DIFFERENCE → **SAME LEVEL(±0.05 内); 差异已检出** | −0.0243 [−0.0383, −0.0109] / −0.0240 [−0.0381, −0.0103] | — |
| T5c KA 去 09-06、KB、KB 去 09-06 | 同样的四种变化(48 行) | 见表 | — |
| T5d(冻结后入库 e73f50e6; 同一冻结规则) T5C/FIX/REG/REG 去 09-06 × KA/KB | 价格与净额「策略自身亏损(target layer)」→ **SHARED LOSS, DIFFERENCE INCONCLUSIVE**; carry「SAME LEVEL」→ **INCONCLUSIVE**; 成本「DEPLOYMENT GAP」→ **±0.05 内且已检出** | REG KA 价格 −1.1304 [−4.1473, +1.7090] / −0.8045 [−3.7879, +1.9324]; 净额 −1.5562 [−4.7395, +1.3784] / −1.2290 [−4.3709, +1.6655]; carry +0.4495 [−0.1266, +1.1338] / +0.4480 [−0.1277, +1.1334]; 成本 −0.0238 [−0.0376, −0.0103] / −0.0235 [−0.0374, −0.0099] | 用 T5d 自己的 0.25 也不变 |
| T5b Q1 次级 tl_RES / kc_RES / fc_RES | FROZEN-RESIDUAL-MATERIAL(PROVISIONAL)→ **INCONCLUSIVE**(PROVISIONAL) | +0.1149 [−0.0798, +0.3338] · +0.1290 [−0.0591, +0.3553] · +0.0953 [−0.1063, +0.3164] | — |
| T5b Q1 主读数 tl_FROZ | NOT MATERIAL → **不变, 现由区间确立** | −0.1199 [−0.2448, −0.0206] 上端 < 0.05 | — |
| T5b Q3 主读数 | NOT MATERIAL → **不变, 区间确立** | −0.0305 [−0.0800, +0.0043] | — |
| T5 附录 H2b 代理 | NEGLIGIBLE → **不变, 区间确立** | 份额 +0.000048 [−0.000283, +0.000583] / +0.000027 [−0.000307, +0.000565] | — |
| T2 Ns(对 A0 / NW) | 旗标 BELOW-RESOLUTION(「不可区分」)→ **撤回; 轴 INCONCLUSIVE**; 判词 UNDECIDED 不变 | 对 A0 +0.1693 [−0.4206, +0.7419] / +0.1857 [−0.4164, +0.7564] | — |
| T2 SK(对 A0 / NW) | 同上 | 对 A0 −0.0267 [−0.2432, +0.1909] / −0.0232 [−0.2361, +0.1829] | D1 = 0.25 时对 A0 为 EQUIVALENT |
| T8 总判 FAIL | 冻结后果句「不能预测」→ **FAIL: 未检出, 有用性未排除**。NET 四格有用性已排除(k0/k9 上界 ≤ 0.0163); LONG/SHORT 六格未排除 | L_LONG r 0.0252 [+0.0015, +0.0484] / 0.0288 [+0.0050, +0.0529]; R_LONG 0.0212 [−0.0032, +0.0457] / 0.0215 [−0.0025, +0.0459]; L_SHORT 0.0190 [−0.0031, +0.0418] / 0.0222 [−0.0009, +0.0453](k0; k9 相近) | D7 = 0.06 时「排除」成立 |
| T1 | H1 / H1fuel / H3 / H4 / H5 判词**全部不变**(NOT DECIDABLE); 补充格 H3 f10_s42 / f10_s2027 由 NO-DROP → **UNDECIDED** | ΔE1 +25.15 判决区间 [−32.21, +82.52], 线 −0.25×23.80; +38.29 [−12.62, +89.20], 线 −0.25×16.17 | — |
| judge_v4 四份收据 | 装置判词**不变**: 冻结窗 60 行 + 延展窗 60 行, (C) UNDECIDED ≡ (C) INCONCLUSIVE, 无一变为 EQUIVALENT | — | — |
| v4 决策文档六处「(C) 不可区分」 | → **(C) INCONCLUSIVE**(两席位): RESULT_v4_chain L10、L72; STATUS_three_questions L63、L128; **RULINGS_requested R-8(L14, 十月重训方案 B 的代价描述)**; RUNBOOK_2026-10 L45 | A1−A0 动态 +0.0605 [−0.1683, +0.2874] / +0.0478 [−0.1708, +0.2704]; 固定 +0.0047 [−0.0764, +0.0869] / −0.0102 [−0.1017, +0.0877] | D1 = 0.25 时固定席位为 (C) EQUIVALENT |
| T3、R22 v2 | 合规, 不变 | T3 c_eff 1.13 [−15.87, +24.74] UNDECIDABLE; R22 CI95 [−0.00166, +0.00126] 在 ±0.00667 内 | — |
| L4 / L4b | 录取判词, 不是等价主张; 冻结词表在两份 RESULT 中 0 命中。补充扫描: L4 L16「ρ to A0 ≈ 0」没有冻结 δ ⇒ **NOT RE-LABELLABLE** | — | — |
| P2 S2 / L2 | 尚无已提交结果; 其谓词在红测中误判(X07 / X12) | — | 须在首跑前采用 |

独立手算核对: T4 上端 0.0625 > 0.05 ⇒ 不等价; ΔIC 区间在 ±0.003 内; T5c 差区间跨 ±0.05; v4 动态 [−0.168, +0.287] 跨带; T8 L_LONG k0 上界 0.0484 ≥ 0.03。以上与装置输出一致。

## 8 采用规则(提议给 §0, 由 lead 应用; 我未改纲领文件, 以免与 lead 的并发编辑冲突)

> **8. 无差类判词只由等价带发出**: 任何「无差 / 不重要 / 不可区分 / 同亏 / 不劣 / 无效应 / 不能预测」判词, 必须由 `multi_asset/exports/research/common/equivalence_labels.py`(或逐字等价实现且过 `tests_equivalence_labels.py`)发出, 条件是区间整体落在事先冻结(先记 sha, 后看数字)的 ±δ 内; δ 带单位、经济理由与来源。CI 含 0、点估计在带内、门未过, 只能写 INCONCLUSIVE / NOT ESTABLISHED。含 LOSS 的判词要求所指的书实现均值 < 0。(A)/(B) 方向词不变, 无差分支不得先于方向分支求值。在飞装置出表前采用: P2 `p2_s2_lib.verdict`、L2 失败标签、T5d 的 OWN-LOSS 门(改由 `equiv` 把关)。既有结论按 `RELABEL_TABLE_K2` 提案, 由 lead 复审后更正; 同一单位在同一纲领内只用一个 δ(当前 D1 0.05 与 T5d 0.25 并存, 须裁一)。

## 9 未证边界

1. **δ 不是盲选**(§3)。T4、T2 SK、v4 固定席位、T8 的新判词随 δ 翻转, 已列在敏感性里; 这不是对这些结论的经济判断, 只是在冻结线下的读数。
2. D4 只是分数层尺度, 不是书层经济量; D5 不可证事先声明; T1 H3 NO-DROP 的参照 E1_H1 取点估计(不保守); T1 判决区间的置信水平由存储的 z 反推。
3. 区间一律取装置存的百分位自举区间, 不重估; 数百行重标不做族错误率控制, 每行只是读数, 不是新检验。原结果若自身有误(如 T5c 的 IV 问题), 重标照样继承。
4. T5d 的 G-REPRO 所用谓词在运行时按 AST 抽取, 并把 sha 记入收据(6f2af298…); 它没有在 C2 预先钉住。T5d 属 K1 项, 本表对它只是提案。
5. 重标首轮出结果后, 我改了渲染与分类: 保留装置自身的「差异已检出」旗标、PROVISIONAL 后缀归类、状态词。**判定未变**: 首轮打印的 165 行在去掉检出后缀后与终版 0 处不同(首轮与两次迭代日志均留档)。
6. 第二层 38 处(已关闭纲领)与知识库 154 行文字未重标(K4 / aud-kb 范围); L4「ρ≈0」因无相关系数 δ 未重标。
7. 模块尚未被任何设备采用; P2 S2 与 L2 的修正是别人的冻结设备, 本项只给红测与采用规则。
8. 变异测试 17 个, 不穷尽; property 测试的随机生成器曾让一个变异体存活(lo>0 蕴含 point>0), 已补定点格, 但生成器的覆盖面仍有限。
9. 基建: Mac 盘 98% 满, iCloud 在本项进行中驱逐了已提交的 δ 表、模块、设备与收据。guarded 读两次拒读; `brctl download` 取回后全部 sha 与提交一致, 但驱逐随时可能再发生。

## 10 提交链与复跑

| 提交 | UTC | 内容 |
|---|---|---|
| `adeda8e7` | 13:19:25Z | C1 事实表 + δ 表冻结(8 文件) |
| `efc2412a` | 13:31:07Z | C2 红先: 旧谓词抽取 + 55 格测试 + 红日志(5 文件) |
| `f0cfe770` | 14:13:38Z | C3 模块 + 规则 + 邻格 + AST + 变异(13 文件) |
| `d0b087db` | 14:31:37Z | C4 重标表 + 装置 + 日志(7 文件) |
| (本提交) | — | C5 报告 + 两份渲染迭代日志 + 合并 diff `docs/receipts/fx_eval_k2_C1_C4.diff`(sha 7c9d959c…) |

```sh
cd /Users/haosiyu/Desktop/quant_research
python3 docs/fixprogram_2026-09-13/FX_EVAL/k2_materialize.py 240                                         # 先把被驱逐的输入取回
python3 -B multi_asset/exports/research/common/tests_equivalence_labels.py --impl legacy                 # 期望 rc=1, 红集 == 声明 19 格
python3 -B multi_asset/exports/research/common/tests_equivalence_labels.py --impl module                 # 期望 84/84 rc=0
python3 -B docs/fixprogram_2026-09-13/FX_EVAL/k2_ast_retention_check.py                                  # 期望 changed=2 expected=2 PASS
python3 -B docs/fixprogram_2026-09-13/FX_EVAL/k2_mutation_run.py <scratch_dir>                           # 期望 17/17 killed, control pass(约 2.5 分钟)
python3 -B docs/fixprogram_2026-09-13/FX_EVAL/k2_relabel.py                                              # 期望 gates_pass=True, 347 行
```

## 11 过程自述

- 13:34Z 会话额度中断。当时 C3 已写完模块与规则、module 模式首轮 73/73, 但尚未留日志、未提交。恢复后(14:03Z)**重做**全部 C3 步骤: 模块小重构(`kind` 字段、损失守卫先转 list)、两轮测试、AST 核、变异, 然后提交; C4、C5 是新做的。
- 一次提交因 zsh 不分词 `$P` 失败(`git add` 报 fatal, 没有提交任何东西, 已核对暂存区), 改用字面路径后提交。
- 未使用子代理; 未碰 pod2 / GPU / 实盘; 锚窗外运行。
