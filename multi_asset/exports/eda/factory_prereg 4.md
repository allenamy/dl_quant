> **创建:** 2026-07-19 JST | **Session:** fable multi-asset-v2 (0C 独立审计/预注册) | **状态:** final (pre-registration, 幂等锁定 —— 在任何公式被评估之前冻结) | **作废条件:** 书 (king/S2/四腿) 重建, YR4B/YR24B target 重建, DSL 算子集重大变更 (需重审泄漏面), 或 holdout 年封存策略变更

# LLM-DSL 公式工厂 — 反多重检验协议 (预注册, 0C)

**威胁模型 (为什么这份文档最承重).** 公式工厂 = LLM 在约束 DSL 里生成成百上千条候选公式 + 确定性评估器打分。**其头号杀手不是没有信号, 是多重检验 (data-snooping)** —— 评估 M 条公式, 即便全是噪声, 期望有 M·α 条"显著"; M=10,000 且逐条 α=0.05 → ~500 条假发现; 即便逐条 z≥3 (α≈0.00135) → ~13 条假阳性。**今年 A 级 crypto 因子发表多数死于此 (挑出 max-of-M 报告, 不校正多重性)。** 本协议使工厂**统计诚实**: 每条公式的显著门随累计评估数收紧, holdout 封存防迭代偷看, append-only 台账使"试到过为止"不可能。**门在任何公式被评估之前锁定; 任何"因结果调门" = 违反预注册, 作废另起。**

---

## ★ 核心 reframe (整份协议的支点)

**suppl-v2 的 +0.003 书-正交增量门是为 N~5 条机制设计的手工候选校准的 —— 那里多重性可忽略。对一个评估数千条机器生成公式的工厂, +0.003 远在噪声地板之下。** 逐条 IC 的 SE (day-block bootstrap, 3 选择年 ~6000 ts) ≈ 0.002; mining M 条公式的 FWER-校正门是:

| 累计 M | z*(M) FWER | 需要的增量-IC (SE≈0.002 示意) |
|---|---|---|
| 50 | 3.09 | ~0.0062 |
| 100 | 3.29 | ~0.0066 |
| 1,000 | 3.89 | ~0.0078 |
| 10,000 | 4.42 | ~0.0088 |
| 100,000 | 4.89 | ~0.0098 |

**⇒ 工厂的幸存门不是 +0.003, 是 ~0.007-0.009 增量-IC (随 M 上升)。** +0.003 在 10,000 条里是纯噪声 (会有几十条靠运气达到 0.003-0.008)。**这是本协议存在的全部理由: 把为少数手工候选校准的门, 换成为大规模机器搜索校准的、随 M 收紧的门。** (SE 须逐公式 day-block bootstrap, 上表 0.002 只是示意标定。)

---

## 1. 评估目标与功劳口径

- **目标 = YR4B (全书残差, 4h) + YR24B (24h)** —— 候选公式对四腿书 (funding / king / SIZE / S2) 残差的 walk-forward **增量**。**只挣书外的钱** (承 suppl-v2: 功劳按书-正交增量算, 非公式自身原始 IC)。产物 `exports/eda/yr4b_yr24b_report.json` (0B verify md5+ts 对齐)。
- **双 horizon 4h/24h** —— 带内 horizon 已测满 (`horizon_gap_audit.md`: sub-4h/8h-clock 都 CLOSE, 4h/12h/24h 已占)。**故公式因子的价值不在新 horizon, 在"离散/条件结构"** (更好的截面 spread / 尾部 / regime-state 条件化), 在 4h/24h 两个已知甜点上找书外增量。这是**公式设计先验**, 但**判据仍是诚实的书-正交增量-IC** (不为"条件结构"叙事放宽门)。
- **增量-IC 计算 (逐公式)**: 公式 f 产出逐 (t,asset) 值 → 逐 ts 横截面 rank-IC(f_t, YR{4,24}B_t), 均值。等价于控四腿书后的偏相关 (目标已 ⊥ 书)。CL4/CL24 clean 网格 (stride≥horizon, #2)。raw (vs Y) 与残差 (vs YRB) 双报。

---

## 2. ★ 多重检验纪律 (成败所在)

### 2.1 选择窗 vs holdout 封存 (2.c)
- **选择窗 = 2022-2025** (king/S2 OOS 覆盖内)。逐公式增量-IC 在**扩张 walk-forward 测试年 2023/2024/2025** (train 起 2022) 上算 + 逐年符号一致。
- **★ HOLDOUT = 2026H1 (1085 ts), 封存。任何公式评估、LLM 反馈、门调参都不许碰 2026。** 只在**工厂终止后、对最终幸存者集开封一次**。**开封 = 定稿: 幸存者在 2026 上过则进书流程, 不过则死 —— 禁止"在 2026 上看一眼再改公式再测" (开封即消耗, 无第二次迭代)。** 开封时对 K 个幸存者再加最终多重性校正 (holdout 显著要求 α/K)。
- **LLM 防火墙**: LLM 提案循环**本身是多重检验放大器** —— LLM 看 append-only 失败轨迹并迭代 = 对选择集 (2023-2025) 的 data-snooping。允许 (它在选择集上优化), **但 (i) 它提的每条公式都计入累计 M** (2.5 的 FWER 分母), **(ii) LLM 永不接触 holdout (2026) 任何读数**。LLM 迭代次数越多, M 越大, 门越高 —— 迭代不是免费的。

### 2.2 逐批经验 null (2.a) —— 两个 null
每批 N 条真公式, 配套两个同规模经验 null (勿信理论高斯 z: 金融 IC 重尾+自相关, 理论 z 高估显著):

1. **★ shuffle-eval null (主显著 null, 标签块置换):** 用**同一批真公式**对**按天-块置换的 YR{H}B** 打分 (打断 公式→未来收益 的预测链, 保横截面结构与日内自相关)。得到的增量-IC 分布 = 这些公式**靠运气**能拿的分。天-块置换 (非 iid shuffle) 保 intraday 自相关 → 正确的 null 方差。**这是真 null 假设 (公式无预测链) 且自动 complexity-matched (同公式)。**
2. **random-formula null (语法-偏置标定):** 从 DSL 语法按**同深度/算子数分布**随机抽 N 条公式, 对**真 YR{H}B** 打分。分布 = "同语法无设计意图公式"的 IC。防语法本身偏向 spurious fit。真公式须超过它。

### 2.3 幸存门 (2.b) —— Reality-Check max-null (主) + Bonferroni z*(M) (交叉核)
- **★ 主门 = White Reality-Check / Romano-Wolf max-统计经验 null (data-snooping-robust 的既定方法):** 反复生成"同批规模的 null 批", 每批取**最大**增量-IC, 得 **max-of-null 分布**; 一条公式显著 ⟺ 其增量-IC 超过 max-null 分布的 **(1−α_family) 分位** (α_family=0.05)。**此法自动吃掉多重性与公式间相关性** (同语法公式高度相关, Bonferroni 会过度校正; max-null 用实际 DSL-抽样公式, 抓有效独立检验数)。Romano-Wolf stepdown 逐步剔除已显著者重估余下, 提升 power。
- **交叉核 = Bonferroni-Šidák z*(M_max) 固定门** (§核心 reframe 表): **z*(M) = Φ⁻¹(1 − α_family/M), M 用预注册的 M_max (全campaign 预算), 非当前累计** —— 固定门 (不漂移)、事前已知、不可 early-stop 游戏。survivor 须同时过 max-null 分位 **且** z ≥ z*(M_max)。二者取严。
- **增量-IC 门的 SE**: 逐公式 **day-block bootstrap (3000×, 块=自然日)** 得增量-IC 的 SE 与 95%CI; z = 增量-IC / SE。CI 须排除 0 且 z 过 §2.3 门。

### 2.4 符号一致预筛 (便宜强过滤)
- 公式须**逐选择年 (2023/2024/2025) 增量-IC 符号一致** (符号在首选择年锁定, 后续年须持同号)。spurious 公式极少跨 3 regime 符号一致 → 廉价砍绝大多数噪声, 且把显著检验变单侧 (符号已锁)。**未过符号一致 = 直接死 (不进 z 门)。**

### 2.5 幸存者上限 + FWER-over-campaign (2.b)
- **每批**: 仅保留 (增量-IC top-k) **且** (过 §2.3 双门) 的公式。**k 硬上限 = 每批 ≤ 3** (防批内灌水)。
- **campaign 级**: 预注册 **M_max = 10,000** 公式总预算 (含所有批、所有 LLM 迭代)。z*(M_max=10000)=**4.42**。**所有幸存者用 z*(M_max) 判 —— 控整 campaign 的 FWER≤0.05, 与停在哪批无关 (不可通过早停降 M 来放宽)。**
- **累计 M = append-only 台账的单调计数** (§2.7)。这是 FWER 分母的唯一真值来源 —— 使"藏起失败尝试让幸存者显得更显著"不可能。

### 2.6 holdout 开封协议 (见 2.1) —— 一次性, 定稿
最终幸存者集 (过全部选择门) → **2026H1 开封一次**: 报增量-IC + day-block CI + 逐 (2026H1) 符号。**过 = 进 §3 书门; 不过 = 死。开封后禁改公式重测。** K 个幸存者同开 → 每个 holdout 门 α/K (Bonferroni on 幸存者数)。

### 2.7 append-only 评估台账 (2.d)
`exports/eda/factory_ledger.jsonl` —— **每条被评估公式一行, 追加写, 不可删改** (理想 hash-chain: 每行含前行 hash)。字段:
`{eval_id (单调↑=累计M), batch_id, ts_logged, formula_str, ast_md5, depth, n_ops, incIC_YR4B_by_year{}, incIC_YR24B_by_year{}, boot_ci, shuffle_null_z, randformula_null_pctile, realitycheck_pass, sign_consistent, pred_corr_king, pred_corr_s2, dyn_share, death_cause, survived_bool}`。
- **death_cause 枚举**: sign_flip / below_realitycheck / below_zstar / pred_corr_redundant / dyn_share_low / complexity_cap / leakage_flag / book_marginal_fail / holdout_fail。
- **台账是防"试到过为止"的核心装置**: cumulative eval_id = §2.5 的 M; 每条尝试 (含 LLM 每次迭代、含被秒杀的) 都留痕 → 显著门用真实 M, 不能选择性上报。**审计时: 台账行数 == 声称的 M; 任何"未入账的评估" = 协议违反。**

### 2.8 PBO / CSCV 工厂-健康诊断 (Bailey et al.)
- 定期跑 **Combinatorially-Symmetric Cross-Validation**: 选择期切 S 组对称 train/test 划分, 看 IS-最优公式是否 OOS ≥ 中位; **PBO = IS-best 在 OOS 跑输中位的划分占比**。**PBO > 0.5 = 工厂在过拟合 (IS-最优是运气) → 红旗, 收紧门或关停。** 这是 campaign 级健康表, 非逐公式门。

---

## 3. 进书门 (幸存者 → 既有 suppl-v2 + 电池)

过 §2 全部的幸存者 (稀) 走 **suppl-v2 五门** (`suppl_factor_gate_prereg.md`): (a) 书-正交增量 + 逐年符号 + bootstrap CI; (b) pred-corr vs king&S2 <0.7 (理想<0.4); (c) 五腿 value-blend improve-rule (book-marginal, 终判); (d) dyn-share≥0.5 + 泄漏审计; (e) 净成本不抹增量。再过 **acceptance_battery** (九门 + 冻结阈值 `acceptance_thresholds_0C_frozen.json`)。**§2 是"这条公式非噪声"的统计资格; §3 是"进书有净价值"的经济资格 —— 两关都过才部署。**

---

## 4. DSL 算子集泄漏审计 (0C 职责; 0B 提算子集后逐算子审)

**每个算子须过泄漏审计 + 复杂度上限, 未过的算子逐出 DSL:**
- **时序算子窗口边界 (最要紧):** `ts_corr(x,y,w)` / `ts_rank(x,w)` / `ts_mean/std/delta/argmax/decay_linear(x,w)` 在时刻 t 只许用 **[t−w+1, t]** (含 t, 不含未来)。审: 实现是否有 off-by-one 越界到 t+1; `ts_rank` 是否用了含未来的排名; 任何 centered-window (对称窗含未来) = 泄漏, 逐出。
- **隐式未来函数:** 任何全样本统计做归一 (full-sample mean/std/quantile 的 z-score/winsor/clip) = 泄漏 → 必须 rolling/expanding causal。审: 归一化、标准化、分位裁剪的统计是否 ≤t。
- **横截面算子** (`cs_rank/cs_demean/cs_scale/cs_winsor`): 只用同-t 截面 → 无时间泄漏 (同期特征对未来目标, 合规)。审: 是否误混入跨-t 信息。
- **target 邻近泄漏:** 特征窗口不得触及 [t, t+H] 目标窗; 审 DSL→eval 的 t 对齐。
- **复杂度上限 (防过拟合怪兽):** **公式深度 ≤ 6, 算子数 ≤ 12** (预注册 cap; 深公式有效 DOF 高、易拟合噪声)。random-formula null 须在**同深度/算子数**抽样 (complexity-matched)。超 cap = 不评。
- **审计产出:** 每算子 `exports/eda/dsl_operator_audit.md` 一行判 PASS/REJECT + 泄漏面结论; 任一 REJECT 算子留在集里 = 全工厂结果不可信。

---

## 5. KPI 与终止条件 (预注册, 防凑数)

- **成功定义:** ≥1 条公式过 §2 全链 (符号一致 + Reality-Check + z*(M_max) + bootstrap CI 排 0) **且** §3 书门 + 电池 **且** holdout 2026H1 开封确认 (增量-IC 显著同号)。**拉伸目标:** 该公式书-marginal 五腿改善 net-cost 正、worst-year 保护。
- **★ 终止/关停 (硬):** 达 **M_max=10,000** 累计评估、**0 holdout-确认幸存者** → **关停 + 存档**。或 **PBO>0.5 持续** (§2.8 过拟合红旗) → 关停。或计算预算耗尽。
- **★ 诚实先验 (预注册, 与前沿双臂 N1a/N1b 同款):** 现数据轴 (价格/funding 结构) 上书已近 alpha-complete (horizon-gap + 前沿双臂双证)。**DSL 工厂在现特征轴上大概率 0 真幸存者 —— 0 幸存是合法且有价值的科学结论** (证明"公式化重组现有特征"无书外增量, 剩余 EV 只在新数据轴)。**禁止为凑幸存者降门 / 放宽 M / 二次开封 holdout。** 工厂的价值一半在"证伪": 用统计-诚实的大规模搜索封死"我们只是没试够公式组合"这个借口。
- **成功也要谦逊:** 即便 1-2 条过 holdout, winner's-curse 使选择-IC 上偏; **holdout-IC (非选择-IC) 才是诚实估计**; 部署幅度走事后校准 (β 铁律)。

---

## 6. 本协议抓不住的东西 (诚实边界)

1. **特征轴泄漏 (上游):** 协议审 DSL 算子 + eval ≤t, 但**输入特征 (CH 32ch) 本身的构建**若有发布-延迟泄漏 (如 funding/OI 用了结算后值), forward-decay 抓粗的、慢特征小步泄漏可存活。补: CH 构建的 point-in-time 审计 (已在 wide_dl 建时做, 新特征入轴须重审)。
2. **holdout 单次性的脆弱:** 2026H1 只 1085 ts、单半年单 regime —— holdout 确认是**必要非充分**, 一个 regime 的 OOS 不保证未来。补: 上线后 online IC monitor + 定期重-benchmark (电池滚动跑)。
3. **DSL 表达力盲区:** 工厂只搜 DSL 能表达的; 真 alpha 若需 DSL 外的结构 (跨资产注意力/新数据轴), 0 幸存不证"无 alpha", 只证"此 DSL 在此特征轴无书外增量"。补: 结论措辞须限定到 (DSL, 特征轴)。
4. **执行侧:** 全为信号-质量门; 净值退化 (maker-fill<1/逆选择) 靠 §3 净成本 + live pilot, 非本协议。

---
**依赖产物:** YR4B/YR24B target (0B 建, 0C verify) · king_pred/s2_pred OOS 面板 (2022-2026H1) · `suppl_factor_gate_prereg.md` (v2 五门) · `acceptance_battery_SPEC.md` + 冻结阈值 · `horizon_gap_audit.md` (带饱和 → 公式价值在离散/条件)。
**0C 交付本预注册; 0B 建工厂架构 (DSL 解析/评估管线/失败台账/提案循环) 须逐条对齐 §2 (选择/holdout/null/门/台账) + §4 算子审 + §5 终止; 算子集就绪后 0C 逐算子泄漏审 → `dsl_operator_audit.md`。**

---

> **追加:** 2026-07-20 | **状态:** final (§2.3 修订 — bootstrap rng 方案 + rng-sensitive 带) | 依据 `factory_rng_signoff.md` (0C 终签)

## §2.3-addendum bootstrap rng 方案 (batch_002+ 冻结)

- **rng 全部派生自冻结常量 `RNG_BASE_SEED=20260720`** (ledger.py, 同 M_MAX/BONFERRONI_Z; **campaign 冻结, 见结果后改 = 后门, 禁改**)。非 run 参数。
- **Stage-0 (并行): 每公式 rng = `default_rng([RNG_BASE_SEED, int(ast_md5,16)])`** —— key 在**公式内容哈希非批位置** → 顺序无关+不可 game。批重排须 byte-identical (机器验)。
- **Stage-1 max-null (串行): 单一共享 rng = `default_rng([RNG_BASE_SEED, STAGE1_NULL_TAG])`** —— 每 repeat 一个共享 day-block 置换应用到全 survivor 再 max-over-survivor (联合多重性结构; per-formula rng 会破坏它, 禁)。
- **nboot ≥ 3000** (bootstrap SE « z-门余量)。
- **★ rng-sensitive 带**: 幸存门 z ≥ z\*(M_max)=4.42。**z ∈ [4.42, 4.86] (=z\*(M_max) 到 z\*(2·M_max) 双侧) 的公式标 `rng_sensitive` —— 该带内 verdict 须用更高 nboot (≥10000) 复核, 且 rng 方案任何变更须对该带公式重跑确认零 flip。** 依据: 稳健 survivor 应大幅跨过 4.42 (batch_001 z 10-17), ~1% rng 噪声对其无关; 只有边界公式 rng-敏感, 而边界公式本就该多疑。
