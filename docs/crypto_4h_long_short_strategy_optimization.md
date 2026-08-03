# 4h Crypto 横截面 Long–Short 实盘策略优化框架

> **适用背景**：约 110 个币；每 4 小时刷新横截面信号；Long–Short、目标 Dollar Neutral；当前等金额建仓；先挂 Maker，15 分钟后由 Taker 补足；Maker 成交率约 60%–90%；目标是提高实盘净 Alpha、稳定性和容量，而不是单独追求 Maker Rate 或回测收益。

## 1. 核心判断：当前瓶颈已从“预测”转向“组合—执行映射”

Rank IC 约 0.11 若在严格样本外和真实成本后仍成立，信号本身已足够强。当前更可能损失收益的环节是：

1. **等金额不等风险**：少数高波动币主导 PnL，横截面分散在经济上失效；
2. **Dollar Neutral 不等于 Beta Neutral**：目标组合名义中性，但市场因子、主题和流动性因子仍可能严重偏移；
3. **每 4 小时“重新建仓”割裂了仓位连续性**：模型只看到新目标，未计入旧仓位、翻向成本与未完成风险；
4. **15 分钟纯等待后一次性 Taker**：把动态执行问题压缩成错误的二元决策，忽略队列、盘口、Alpha 衰减和组合失衡；
5. **固定杠杆放大所有缺陷**：执行器和 sizing 未稳定前，提高杠杆只是同比放大成本、残余 Beta 和尾部风险。

因此，策略应被统一描述为：

\[
\max_{w,\,a_{0:T}}
\underbrace{\hat\alpha^\top w}_{\text{预期 Alpha}}
-
\underbrace{\lambda_r w^\top\Sigma w}_{\text{组合风险}}
-
\underbrace{C(a_{0:T},\Delta w)}_{\text{真实执行成本}}
-
\underbrace{\lambda_{to}\|w-w_{current}\|_1}_{\text{换手与翻向成本}}
-
\underbrace{P_{neutrality}(w)}_{\text{净敞口、Beta、因子偏移}}
\]

这里的关键是：**目标仓位和执行路径必须联合考虑，而不是模型先给一个理想组合，执行器再被迫无条件完成。**

---

## 2. 三个时间尺度必须分离

当前 4h 信号周期和 15 分钟执行窗口并不意味着执行器只能在两个时点行动。应明确三个时钟：

- **Signal Clock：4h**——刷新横截面 Alpha；
- **Portfolio Clock：4h + 状态连续**——基于新信号、旧持仓、风险和成本生成新目标；
- **Execution Clock：事件驱动或 5–15 秒**——在 Maker、撤单重挂、部分 Taker、继续等待和放弃之间动态选择。

最重要的改造是：**4 小时只刷新信息，不应每次把组合视为从零开始；15 分钟只是最晚决策点，不应是静默等待时间。**

---

## 3. Sizing：从等金额升级为 Alpha × 风险 × 可执行性

### 3.1 为什么等金额是当前最明显的结构性缺陷

等金额意味着每个币承担相同 Notional，却不承担相同风险。若两个币 4h 波动率分别为 1% 和 8%，相同金额下，后者的单周期 PnL 风险约为前者的 8 倍。最终看似交易 110 个币，真实组合可能只是押注少数高波动币。

“组合盈利 2 bps，但最大盈利币贡献 3 bps”单次出现并不异常；若在滚动窗口内长期存在，则说明：

- PnL 与风险贡献高度集中；
- 其余币的 Alpha 被成本系统性吞噬；或
- 模型排序只在极端尾部有效，广泛建仓反而稀释收益。

必须长期监控：`ex-top-1 / ex-top-5 PnL`、Top-1/5 风险贡献、各波动分桶与流动性分桶的净收益。

### 3.2 第一版推荐：温和波动率缩放，而非纯 inverse-vol

建议原始目标权重采用：

\[
u_i=
\frac{f(\text{rank}_i)\cdot confidence_i}
{\tilde\sigma_i^{\gamma}}
\cdot LQ_i
\cdot EX_i
\]

其中：

- \(f(rank_i)\)：连续 Rank 强度，不只是入选/不入选；
- \(\tilde\sigma_i\)：winsorize 后的 4h 预测波动率；
- \(\gamma\)：波动缩放强度；
- \(LQ_i\)：流动性折扣；
- \(EX_i\)：可执行性折扣。

**建议从 \(\gamma=0.5\) 开始，与 \(0\) 和 \(1\) 做严格 OOS 对照。**

- \(\gamma=0\)：当前近似等金额；
- \(\gamma=0.5\)：降低高波动币支配性，同时保留其高 Alpha；
- \(\gamma=1\)：inverse-vol，风险更均衡，但可能过度集中至低波动、高相关的大币；
- 不建议直接使用 \(1/\sigma^2\)，估计误差和仓位极化都过强。

Inverse-vol 只使用边际波动率，不考虑相关性；Equal-Risk-Contribution 才使用完整协方差结构。因此 inverse-vol 应作为稳健基线，而非终局优化器。[1][2]

### 3.3 流动性与执行折扣必须进入目标权重

建议至少包含：

- 目标订单 / 前 N 档深度；
- 历史 15 分钟 Maker 完成率；
- Taker 全成本（fee + half spread + impact）；
- Maker 成交后的 5s/30s/1min markout；
- Long↔Short flip 的预计完成时间。

可定义翻向残余风险：

\[
TR_i=|\Delta w_i|\cdot\sigma_i\cdot(1-\hat p^{fill}_{i,15m})
\]

高波动、低成交率、需要从 Long 直接翻至 Short 的币，应被额外降权，而不是只靠执行器在最后承担风险。

### 3.4 Long 和 Short 分侧归一化

若目标 Gross Leverage 为 4×，则建议：

\[
\sum_{i\in Long}w_i=+2,
\qquad
\sum_{i\in Short}w_i=-2
\]

分侧归一化可保持 Dollar Neutral，但还需单独约束 Beta 和因子暴露。

### 3.5 避免 Rank Cliff 与无效翻向

不要每次把 Top/Bottom 集合完全重置。建议加入：

- **连续权重函数**：Rank 越极端，仓位越高；边界附近仓位自然接近 0；
- **Hysteresis / Buffer Zone**：进入和退出使用不同阈值；
- **Turnover Penalty**：只有新 Alpha 超过交易成本和风险收益门槛时才大幅调整；
- **Flip Penalty**：Long→Short 的成本不是平仓成本，而是约两倍目标 Notional 的交易量。

目标仓位应是“从当前持仓出发的最优下一步”，而不是每 4 小时重新生成一个与历史无关的理想组合。

---

## 4. Dollar Neutral、Beta Neutral 与执行过程中的临时对冲

### 4.1 Dollar Neutral 只控制名义金额

\[
\sum_i w_i\approx0
\]

它不保证：

\[
\sum_i w_i\beta_i\approx0
\]

例如 Long 侧多为高 Beta 小币，Short 侧多为低 Beta 大币，即使两边各 2× Notional，组合仍可能显著净多市场因子。

### 4.2 推荐使用低秩 Crypto 因子模型

不建议直接依赖噪声很高的 110×110 全协方差矩阵。可先使用：

\[
r_i=\alpha_i+
\beta_{BTC,i}r_{BTC}+
\beta_{ALT,i}r_{ALT}+
\beta_{MOM,i}r_{MOM}+
\epsilon_i
\]

最小可行版本只需：

- BTC/全市场因子；
- Altcoin 相对 BTC 因子；
- 流动性或 Size 因子；
- 必要的主题桶（Meme、AI、L1、DeFi 等）。

对 Beta 使用稳健滚动回归和 shrinkage，避免短窗口估计跳变。组合约束建议按优先级设置：

1. Net Notional；
2. BTC/Market Beta；
3. Alt Beta；
4. 主题/行业风险；
5. 单币与流动性集中度。

### 4.3 Neutrality 必须约束实际成交仓位，而不仅是目标仓位

Maker 成交具有随机性。若 Long 完成 85%、Short 仅完成 40%，目标虽中性，实际组合已经暴露显著净多风险。

更优做法不是立即用 Taker 强行完成所有低流动性 Short，而是：

> **用 BTC/ETH 或高流动性指数永续做临时 Bridge Hedge，先中和实际 Beta，再随着目标腿成交逐步解除。**

这样可以把两个问题分开：

- 用最便宜、最液态的工具控制组合方向风险；
- 用更耐心的 Maker 执行获取各币横截面 Alpha。

这通常比“为保持 Dollar Neutral 而对所有未成交币无差别 Taker”更经济。

---

## 5. 动态执行：用价值比较替代 15 分钟纯等待

限价执行的核心权衡是成交概率、逆向选择和未成交机会成本；最新研究也将最优被动执行描述为一系列动态报价调整，而不是固定报价后等待终点。[3] 队列位置、盘口失衡和延迟都会影响 Maker 的真实价值；在预计价格向不利方向移动时，主动订单通常更合理。[4][5]

### 5.1 每次决策只比较四个动作

对剩余仓位 \(R_i(t)\)，计算：

- `KEEP`：保留当前 Maker 和队列位置；
- `REPRICE`：撤单并以更激进的 Post-Only 重新排队；
- `TAKE_PARTIAL`：Taker 一部分，剩余继续 Maker；
- `SKIP/REDUCE`：放弃负经济价值的剩余目标。

核心不是 Maker/Taker 标签，而是比较边际期望价值：

\[
EV_{take}=
\alpha^{remain}_i
-C^{taker}_i(Q)
+\Delta RiskRelief_i
\]

\[
EV_{maker}=
P^{fill}_i
\left(
\alpha^{postfill}_i
+rebate_i
-AS_i
\right)
-(1-P^{fill}_i)MissedAlpha_i
\]

其中 \(AS_i\) 是 Maker 成交后的预期不利 markout。**Maker fee 为负，不代表 Maker 的经济成本为负。**

### 5.2 两个分数比一个复杂 Urgency Score 更清晰

建议分别建模：

1. **Trade Edge**：剩余 Alpha 是否值得成交；
2. **Passive Quality**：当前 Maker 是否值得继续排队。

| Trade Edge | Passive Quality | 动作 |
|---|---|---|
| 低/负 | 高 | 只保留少量 Maker，允许不完成 |
| 低/负 | 低 | 撤单、降目标或放弃 |
| 高 | 高 | Maker / Reprice，必要时小比例 Taker |
| 高 | 低 | Partial Taker 或 Full Taker |

这比简单设定“第 15 分钟全部 Taker”稳健得多。

### 5.3 最均衡的时间策略：动态完成曲线

为每个币定义 0–1 的 urgency \(u_i\)，由以下信息决定：

- Rank/Alpha 强度与置信度；
- Alpha decay；
- 当前完成缺口；
- Taker 全成本；
- Maker fill probability；
- queue ahead 与订单流；
- 短期 microprice / order-flow 是否向不利方向移动；
- 实际 Net/Beta/主题风险的改善价值。

用一条连续目标完成曲线，而不是固定时间表：

\[
F_i^*(t)=\left(\frac{t}{T}\right)^{p_i},
\qquad
p_i=1.8-1.4u_i
\]

- 高 urgency：\(p_i<1\)，前置成交；
- 低 urgency：\(p_i>1\)，耐心后置；
- 实际完成率显著落后于 \(F_i^*(t)\) 时，逐级从 KEEP → REPRICE → PARTIAL TAKE 升级。

### 5.4 一个可直接上线的 15 分钟状态机

**0–3 分钟：被动探索，但不是静默等待**

- 分批挂单，避免一次暴露全部目标；
- 保留好队列，只有 Passive Quality 明显恶化才撤单；
- 极强、快速衰减 Alpha 可 Taker 10%–20%。

**3–8 分钟：动态重挂与小比例补单**

- 根据 fill probability 和 queue value 决定是否追到 touch；
- 若完成率落后、Trade Edge 显著为正，Taker 剩余量的 15%–30%；
- Maker markout 恶化时应撤单，而不是为了 Maker Rate 继续接刀。

**8–12 分钟：组合感知的混合执行**

- 对强 Alpha、低成本或能显著修复 Beta 的订单，再 Taker 20%–40%；
- 对弱 Alpha、高成本币继续 Maker 或直接降目标；
- 用 Bridge Hedge 修复组合风险，而不是强迫所有单币同步完成。

**12–15 分钟：终点价值判断**

- `EV_take > 0` 且风险需要：完成剩余仓位；
- `EV_take <= 0`、`EV_maker > 0`：允许继续短暂 Maker；
- 两者均非正：撤单并接受 Tracking Error；
- **不再默认 100% completion。**

### 5.5 先做可解释模型，再考虑 RL

第一阶段只需要三个监督模型：

- `P(fill within Δt)`；
- `Expected post-fill markout`；
- `Taker impact(Q)`。

然后由显式 EV 规则决策。端到端 RL 只有在事件级模拟器、队列重放和市场冲击模型可信后才值得尝试；否则很容易学习模拟器漏洞。已有研究表明，RL 可联合配置 market/limit orders，但其价值高度依赖环境与成本模型的真实性。[6]

---

## 6. 动态杠杆：4×为中枢，但必须由风险和执行质量决定

### 6.1 杠杆定义

Gross 4× 表示：

- Long 2×；
- Short 2×；
- Net Notional 约 0；
- 总名义仓位为 Equity 的 4 倍。

对该 4h 策略，较合理的长期运行框架是：

- **常态中枢：Gross 4×**；
- **正常动态区间：3×–5×**；
- **压力状态：2×–3×**；
- **5×–6×仅限低波动、深度充足、Neutrality 与执行质量稳定的状态**；
- 8×以上不宜成为常态。

### 6.2 杠杆应从 1×组合风险反推

\[
L^{vol}_t=
\frac{\sigma_{target}}
{\hat\sigma_{portfolio,1x,t}}
\]

最终杠杆建议：

\[
L_t=
clip\left(
L^{vol}_t
\cdot m_{alpha}
\cdot m_{liq}
\cdot m_{exec}
\cdot m_{neutral}
\cdot m_{stress},
L_{min},L_{max}
\right)
\]

各乘子含义：

- \(m_{alpha}\)：IC、Top-Bottom spread 与 decay 的稳定性；
- \(m_{liq}\)：深度、spread、可平仓时间；
- \(m_{exec}\)：Maker markout、Taker cost、完成率；
- \(m_{neutral}\)：实际 Beta/Net 偏移程度；
- \(m_{stress}\)：BTC 波动、币间相关性、跳跃和交易所风险。

波动管理有可能改善风险调整后收益，但并非对所有策略都稳定有效，因此必须看自身 OOS 和真实执行结果，而不能机械地“低波加杠杆、高波降杠杆”。[7][8]

### 6.3 波动率估计应避免虚假平静

建议组合风险取以下估计的较大值或稳健组合：

- 短窗 EWMA；
- 中窗 realized volatility；
- 因子模型预测波动；
- 压力相关性下的 stress volatility；
- 近期 worst-4h / Expected Shortfall。

杠杆不应因短期波动暂时下降而迅速上升；加杠杆应慢，降杠杆应快。

### 6.4 Funding 与保证金应进入杠杆成本

永续资金费率由多空持仓之间周期性支付，并随合约溢价变化；高 Gross 下即使净方向中性，Long 与 Short 的 Funding 也未必抵消。[9] 杠杆上限还应考虑：

- 压力行情下的 margin headroom；
- 多交易所/单交易所集中；
- ADL、下架和交易暂停；
- 抵押品与持仓同跌的 wrong-way risk。

---

## 7. 统一的目标组合优化器

中期终局建议不是手工叠加规则，而是每 4 小时求解带现实约束的目标组合：

\[
\max_w
\quad
\hat\alpha^\top w
-
\lambda_r w^\top\Sigma w
-
\lambda_c\sum_i
\left[
 c_i|w_i-w_i^{current}|
+\eta_i|w_i-w_i^{current}|^{3/2}
\right]
-
\lambda_{flip}\sum_i TR_i
\]

约束至少包括：

\[
\|w\|_1=L_t,
\qquad
\mathbf 1^\top w=0,
\qquad
\beta^\top w\approx0
\]

以及：

- 单币权重上限；
- 主题/行业上限；
- 流动性参与率上限；
- Long、Short 分侧 Gross；
- 预期 15 分钟未完成风险；
- Funding 与借贷成本；
- 实际交易所 Position Limit。

**重要顺序**：先形成稳健、连续、可执行的目标组合，再由执行器决定路径；执行器可以返回“该目标不值得完整执行”，并反馈给下一轮优化器。

---

## 8. 评价体系：不要再以 Maker Rate 或 Completion Rate 为主指标

### 8.1 PnL 必须分解

每个币、每个周期至少分为：

- Signal PnL；
- Sizing PnL；
- Timing / delay PnL；
- Maker rebate / fee；
- Maker post-fill markout；
- Taker fee + spread + impact；
- Funding；
- Residual-position / neutrality drift PnL。

### 8.2 核心 KPI

1. **Net Alpha after all costs**；
2. Implementation Shortfall vs arrival mid；
3. Maker fill rate 与 Maker economic cost 分开统计；
4. Taker cost / gross alpha；
5. Missed Alpha；
6. 15 分钟目标完成曲线；
7. 实际 Net/Beta/因子偏移的时间积分；
8. Flip loss 与 residual-position loss；
9. ex-top-1 / ex-top-5 PnL；
10. Worst 4h、Expected Shortfall、最大回撤；
11. 容量曲线：资金扩大后净 Alpha 如何衰减。

### 8.3 回放与上线验证

- 使用真实 L2/L3（若可得）、逐笔成交与自身订单日志重放；
- 明确模拟 queue ahead、部分成交、撤单延迟和价格触及但未成交；
- 先 shadow 计算新目标与动作，不下单；
- 再按币种或资本分桶逐步放量；
- 任何新版本同时报告“理想目标 PnL”和“实际成交 PnL”，防止模型与执行相互掩盖问题。

---

## 9. 推荐的逐层优化顺序

### Priority 0：先补齐可观测性

没有 fill probability、queue、markout、单币成本和实际 Beta 路径，就无法判断是 Alpha、sizing 还是执行失效。

### Priority 1：修正等金额 sizing

上线 `rank strength / sqrt(vol)`，加入 vol winsorization、单币 cap、流动性与 15 分钟可执行性折扣；同时监控 ex-top-1/5 与风险贡献。

### Priority 2：加入仓位连续性

目标函数显式使用 `current_position`，加入 turnover、flip 和 residual-risk penalty，取消每 4 小时“从零重建”的隐含假设。

### Priority 3：替换 15 分钟静默等待

上线事件驱动状态机和 Partial Taker；允许 skip；以 Trade Edge × Passive Quality 决策，而不是固定 deadline。

### Priority 4：实际 Beta Neutral + Bridge Hedge

目标和实际成交仓位都实时测量 Beta；腿间失衡时优先用高流动性合约临时对冲。

### Priority 5：最后再动态放大杠杆

以 Gross 4×为中枢，根据真实 1×波动、执行质量、流动性和压力风险动态缩放。**杠杆优化必须晚于 sizing 和 execution，否则只是把结构性错误放大。**

### Priority 6：模型化执行，RL 作为最后一层

先训练 fill、markout、impact 三模型；只有在仿真器能准确复现实盘成交分布后，再评估 RL 是否提供增量。

---

## 10. 最终建议

当前策略最值得采用的整体方案是：

> **连续 Rank Alpha + 温和波动率缩放 + 流动性/翻向折扣生成目标仓位；用低秩因子模型实现 Dollar 与 Beta 双中性；执行层每 5–15 秒比较 KEEP、REPRICE、PARTIAL TAKE、SKIP，并用高流动性 Bridge Hedge 管理腿间临时失衡；Gross 4×作为中枢，由真实组合波动、执行质量和压力风险动态调整。**

三个最重要的原则：

1. **不追求最高 Maker Rate，追求 Maker 后的净经济价值；**
2. **不追求每期 100% 完成，追求剩余 Alpha 大于边际成本；**
3. **不靠更高杠杆修复收益，先确保每一单位风险和每一笔交易都值得承担。**

---

## References

[1] Noguer i Alonso, *The Mathematics of Heuristic Portfolio Optimization*, 2026. https://arxiv.org/abs/2606.12612  
[2] Choi et al., *Diversified Reward-Risk Parity in Portfolio Construction*, 2021. https://arxiv.org/abs/2106.09055  
[3] Barzykin et al., *Optimal Execution with Passive Market Impact*, 2026. https://arxiv.org/abs/2607.28323  
[4] Gonzalez & Schervish, *Instantaneous Order Impact and High-Frequency Strategy Optimization in Limit Order Books*, 2017. https://arxiv.org/abs/1707.01167  
[5] Lehalle & Mounjid, *Limit Order Strategic Placement with Adverse Selection Risk and the Role of Latency*, 2016. https://arxiv.org/abs/1610.00261  
[6] Cheridito et al., *Reinforcement Learning for Trade Execution with Market and Limit Orders*, 2025/2026 revision. https://arxiv.org/abs/2507.06345  
[7] Moreira & Muir, *Volatility-Managed Portfolios*, Journal of Finance / SSRN. https://papers.ssrn.com/sol3/papers.cfm?abstract_id=2659431  
[8] Cederburg et al., *On the Performance of Volatility-Managed Portfolios*. https://papers.ssrn.com/sol3/papers.cfm?abstract_id=3357038  
[9] Binance, *Introduction to Binance Futures Funding Rates*. https://www.binance.com/en/support/faq/detail/360033525031
