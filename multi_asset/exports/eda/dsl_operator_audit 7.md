> **创建:** 2026-07-20 JST | **Session:** fable multi-asset-v2 (0C 独立审计) | **状态:** final | **作废条件:** DSL 算子集/操作数/评估口径变更, 或 factory_prereg 修订
> 审对象: `factory/DSL_DESIGN.md` (0B)。配套预注册: `exports/eda/factory_prereg.md` (0C 锁定)。

# DSL 算子集泄漏面审 + 两项统计裁定 (0C)

## 判词: **算子集 PASS (结构因果闭环成立), 附 5 条实现-闭合条件。两项统计裁定见 §B。**

---

## A. 逐算子泄漏面审

**★ 结构因果闭环成立 (核心):** 20 个算子全部只引用 `{t}` / `[t−n,t]` / `(−∞,t]` —— **不存在任何引用 t+k 的算子**。故只要 (i) 操作数白名单严格为因果 CH/legs/常数, (ii) 窗参为常数集 `{1,3,4,6,12,24,72}` 且 ≥1, 则**每个表达式树因果 by construction**。parser 的"结构强制 trailing"闭环 **成立**。逐算子窗口边界声明 (ts_delta [t−n,t] / ts_mean-std-rank-corr-min-max-decay_linear [t−n+1,t] / ema (−∞,t] / xsec {t} / pointwise {t}) 全部 ≤t, 无越界。excluded 表 (forward/centered 窗、t+k、group-by-future、raw log/div) 正确且对本算子集完备。

**★ 上游通道因果性实测 confirmed (DSL 抓不住的面, 我替它查了):** `ret_{1,4,12,24}h[t]` vs 各自**前向** `Y{1,4,24}[t]` 横截面 rank-IC = **−0.047 / −0.045 / −0.044 / −0.038** (全 ~−0.04, 若前向泄漏应 ~1.0)。mom_4h/rvol_24h 同量级。⇒ **通道是 trailing 特征非前向目标, 无上游泄漏。** (副产: 小负号 = 1h/4h 反转, 契合 king residual-reversal。)

### 5 条实现-闭合条件 (必须实现保证, 非仅文档声明):

1. **trailing rolling 代码强制**: eval 必须用 `.rolling(n)` trailing, **禁 `center=True`**; 窗口须结束于 t (含)。加单测: 单调合成序列上 centered vs trailing 必不同 → 断言用 trailing。(文档声明 ≠ 实现保证, 这是最易回归的洞。)
2. **div/zscore/xsec_z 数值边界**: 指定 div-guard 的 eps; `|b|<eps` 或 std=0 → **返回 NaN (非 inf, 非 0)**; **NaN cell 从逐锚 IC 排除 (非 0-填充)** —— 0-填充会注入虚假横截面结构制造假 IC (correctness 门非泄漏, 但能伪造信号)。
3. **★ 稀疏 leg 列上的时序算子 (king/s2)**: king/s2 只在 CL4/CL24 锚有限 (每 4h/24h), 故 `ts_mean(king,6)` 在 6 个**小时**bar 上多数 NaN → min-periods 须按 leg 原生 cadence, 或**时序算子作用于锚-网格 (resample) 非小时网格**, 或**禁 leg 上时序算子** (只许 leg 进 pointwise/xsec/conditional = 设计意图的"组合腿"空间)。非泄漏, 是可靠性 (多数-NaN 窗给退化/不稳因子值)。**建议: leg 只进 §17-20 组合空间; 时序算子仅作用于 dense CH 通道。**
4. **ts_rank/ts_corr 退化方差 → NaN → 排除** (已声明): 确认 NaN 传到 IC-排除, 非 0。
5. **新通道入操作数集须重过 trailing-check** (预注册前置): DSL 因果但**假设操作数因果**; 任何新通道入白名单前须过 §A 的 "corr(通道, 前向目标) « 1" 检验 (factory_prereg §11 边界)。

**其余 (log1p_safe sign·log(1+|x|) domain-safe ✓ / power sign·|x|^p p∈{.5,1,2} overflow-guard ✓ / where cond 结构因果 ✓)** 无泄漏面, 通过。

---

## B. 两项统计裁定 (协议管辖)

### (1) 挖矿期 leg-冗余 pred-corr 上限 0.7 — **CONFIRM 0.7, 不收紧。定位为省算力 triage。**
- **依据成立**: 评分目标 YR4B 本就 king+S2-正交 → 重学腿的公式在 YR4B 上**增量-IC 自动 ~0** → **增量-IC 门才是真过滤器**, pred-corr 只是跳过评估显然近重复的**廉价早退**。
- **不收紧 (关键)**: 中-corr 公式可携真正交增量 —— **已进书的 S2 对 king 仅 0.22 corr**, 但一个 0.4-0.6-corr 的公式仍可能有真残差 (corr 与增量非完美反相关)。**收到 0.4 会误剪 S2-型因子。** 0.7 (甚至更松) 正确, 因增量-IC + 书级 decider 兜底。
- **补一条**: pred-corr 除对四腿, **还须对已 ACCEPT 的工厂因子** (工厂内互查去重, 防批间近重复自我繁殖)。书级 decider 仍在 suppl-v2 五腿 improve-rule。

### (2) 批内 BH-FDR q=0.10 — **★ 仅 triage, 绝非幸存门。层级写死。**
**统计要害: BH-FDR 控假发现*比例* (容许幸存中 ~10% 假阳); 我的幸存门控 FWER (任一假阳的*概率*, campaign 级)。FDR 严格性 ⊊ FWER。用 BH 当幸存门 = 放进 ~10% 假因子 = 协议要防的 p-hacking 本身。** 故 BH 只能**预筛**, 永不**裁定**。层级 (写进 §5/§6/§7):

- **Stage-0 TRIAGE (廉价, 逐批)**: 批内 BH q=0.10 → 剔明显噪声省算力。BH-过 → 进 Stage-1; BH-挂 → ledger REJECT(triage)。**非发现声明。**
- **Stage-1 幸存门 (锁定协议 factory_prereg §2.3)**: **Reality-Check/Romano-Wolf max-null 分位 (主) 且 Bonferroni z\*(M_max=10000)=4.42 (交叉核) 双门** + 逐年符号一致 + day-block CI 排 0。**双门全过 = SURVIVOR。**
- **Stage-2**: 幸存 → suppl-v2 五门 → acceptance battery。**Stage-3**: holdout 2026 开封一次。

**★★ 两把防-gaming 锁 (必须写死):**
- **(i) ledger 的 `verdict=CANDIDATE` 只由 Stage-1 (FWER 双门) 给, 绝不由 Stage-0 (BH) 给。** `fdr_q` 字段是 triage 元数据, **永不能提升为 CANDIDATE**。
- **(ii) ★ Bonferroni/Reality-Check 的分母 = 累计 M (含所有 BH-剔除的公式), 非 BH-幸存后的计数。** 否则 BH 成了**缩小多重性分母**的后门 (把剔除的公式藏出 FWER 计数 = gaming)。**ledger 单调累计-id 喂 z\*(M_max); BH triage 不减 M。**

**设计需改的措辞**: §1 "(b) FDR/Bonferroni correction over each batch" **混淆了 FDR 与幸存门** —— 须拆为: 逐批 BH = triage; **campaign 级 FWER (z\*(M_max) + Reality-Check over 累计 M) = 幸存门**。§1/§5 目前**未提 Reality-Check/Romano-Wolf** (我锁定协议的主门) —— 须显式引 factory_prereg §2.3, 别让"per-batch FDR"顶替 campaign-FWER。

---

## 与工程裁定 (lead 已裁) 的一致性
- (3) K=100 + 100 条逐批 null: 与 §2.2 逐批经验 null 一致 ✓ (null 规模=批规模)。**注: K=100/批不改 z\*(M_max) 用 campaign 预算 M_max=10000 的固定门** (per-batch K 只定逐批 BH triage 与逐批 null 规模, 不定 FWER 分母)。
- (4) 移除预排 xsr_* 通道逼显式 xsec_rank: **同意** ✓ (免琐碎冗余提案; 移除后操作数 = 生因子 + 4 腿 + 常数)。

**其余设计与 factory_prereg 对齐** (append-only ledger / depth≤6 ops≤12 / YR4B 目标 / shuffle-future + forward-decay 双 leak-screen / day-block CI / 逐年符号)。**算子集与管线 GO 实现, 附 §A 5 条闭合条件 + §B(2) 层级写死。**

---
**产物:** 本审 `exports/eda/dsl_operator_audit.md` · 上游通道因果实测 (inline)。
