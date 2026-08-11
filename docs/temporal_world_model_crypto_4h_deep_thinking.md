# 从自回归预测到时序世界模型
## 对传统量化范式的质疑、未来建模方向，以及在 110 币 4h 永续合约 Long–Short 策略中的落地思考

> **文档定位**
>
> 本文不是对原文章的宣传性复述，而是一份供量化研究团队深入讨论的技术思考稿。全文严格区分三层内容：
>
> 1. **文章提出了什么；**
> 2. **这些观点哪些成立、哪些存在夸张或概念混淆；**
> 3. **对于当前 110 个加密货币永续合约、每 4 小时更新一次的横截面 Long–Short 组合，哪些方向值得通过严格实验验证。**

---

## 1. 执行摘要

原文章最重要的质疑可以概括为：

> 许多传统时间序列模型把预测对象视为一个近似封闭系统，试图从“自身过去”递推“自身未来”；但现实市场是一个由外部驱动、跨资产传导、潜在状态、制度约束和参与者行为共同推动的动态系统。因此，下一代模型不应只学习 \(y_{t-L:t}\rightarrow y_{t+H}\)，而应学习“整个系统的状态如何在外部驱动下演化”。

这个方向具有价值，但必须避免四种误读：

1. **自回归不等于单变量。** 现代量化模型可以包含多资产、多模态和外生变量。
2. **Transformer 并非不能建模时间。** 更准确地说，它缺少连续动力学、稳定状态转移和长记忆方面的强结构先验。
3. **预测关系不等于经济因果。** lead–lag、partial correlation、PCMCI 或 Granger 关系通常只能称为条件预测关系。
4. **换成 S5、LRU、Koopman 或 Neural Operator 不会自动产生 alpha。** 标签、资产池、成本、组合构建、执行和验证方法往往比编码器名称更重要。

对于当前项目，最值得吸收的不是“世界模型”这个标签，而是以下范式变化：

- 从逐币绝对收益预测，转向 **global–sector–asset 三层状态建模**；
- 从 raw 4h return，转向 **market/sector residual return 与横截面 rank**；
- 将 funding、basis、OI、liquidation、mark/index deviation、spot–perp divergence 视为系统驱动；
- 从静态全连接特征交互，转向 **动态、稀疏、带滞后的跨资产 predictive driver graph**；
- 从单点预测，转向 **均值、风险、不确定性、成本和 funding 的联合决策**；
- 从每 4 小时机械全量换仓，转向 **机会强度、风险暴露和交易成本驱动的连续仓位调整**。

建议研究优先级：

\[
\boxed{
\text{Label / Universe}
>
\text{Perpetual Drivers}
>
\text{State Decomposition}
>
\text{Portfolio / Execution}
>
\text{Dynamic Graph}
>
\text{S5 / LRU}
>
\text{Koopman / Neural Operator}
}
\]

---

# 2. 原文章的核心世界观

## 2.1 时间序列不只是“换一种 token 的语言模型”

文章首先质疑一种常见类比：只要把价格、传感器值或其他连续变量离散化为 token，就可以直接复制语言模型的范式。

文章认为，语言序列与真实世界时间序列存在重要差异：

- 时间间隔具有物理或经济含义；
- 1 分钟、1 小时、4 小时、1 天并不是单纯的位置差异；
- 系统存在惯性、衰减、周期、振荡、冲击响应和稳定性；
- 真实系统受外部输入推动，而不是只由自身观测历史闭环决定；
- 相同的数值变化，在不同时间尺度和不同 regime 下含义不同。

因此，文章认为时间序列模型需要显式或隐式表示：

\[
\text{state transition}
+
\text{external forcing}
+
\text{time scale}
+
\text{system constraints}
\]

### 批判性判断

这部分方向正确，但“语言是空间、时间序列才是真正时间”之类的表达偏绝对。语言也具有顺序、递归和长期依赖；Transformer 也可以加入时间差编码、相对位置、多尺度输入和时间感知 attention。

更准确的表述是：

> 通用序列模型可以拟合时间数据，但如果没有动力学先验，它需要从有限样本中重新学习衰减、周期、稳定性和不同时间尺度，样本效率与 OOD 稳定性可能较差。

---

## 2.2 “自身过去预测自身未来”是不充分的世界假设

传统形式常被写为：

\[
\hat y_{t+H}=f(y_{t-L:t})
\]

现代深度模型通常已经扩展为：

\[
\hat y_{t+H}=f(X_{t-L:t})
\]

其中 \(X\) 可以包含目标自身历史、其他资产和大量外生变量。

文章真正质疑的不是是否加入了更多特征，而是模型是否仍然把问题理解为一个静态 supervised mapping：

- 当前系统处于什么潜在状态？
- 哪些变量正在驱动哪些变量？
- 驱动关系是否随 regime 改变？
- 冲击如何传播、衰减和反转？
- 哪些状态会跨多个时间尺度持续？

文章因此主张从“预测目标值”转向“建模系统状态演化”。

---

## 2.3 Temporal World Model 的抽象形式

一个实用的时序世界模型可以写成受控动态系统：

\[
z_{t+\Delta t}
=
F_{\theta}
\left(
 z_t, u_t, G_t, \Delta t
\right)
+
\epsilon_t
\]

\[
x_t=H_\theta(z_t)+\eta_t
\]

其中：

- \(z_t\)：不可直接观测的系统潜在状态；
- \(u_t\)：外部驱动或 forcing variables；
- \(G_t\)：变量之间随时间变化的关系图；
- \(\Delta t\)：真实时间间隔；
- \(F_\theta\)：状态转移；
- \(H_\theta\)：潜在状态到观测变量的映射；
- \(\epsilon_t,\eta_t\)：过程噪声和观测噪声。

这与经典 state-space model 并不矛盾。所谓“新范式”主要是把以下模块统一起来：

1. 大规模非线性表示学习；
2. 动态变量关系发现；
3. 多时间尺度状态转移；
4. 外生变量建模；
5. 不确定性估计；
6. 预测到决策的闭环。

---

## 2.4 文章指向的技术方向

文章讨论或暗示了以下技术：

- S4/S5 等结构化状态空间模型；
- LRU 等线性递归单元；
- Mamba 类选择性状态空间模型；
- Koopman operator；
- Neural Operator；
- 动态因果发现与变量图；
- 频域、谱域和连续动力学；
- 面向真实系统演化的 foundation model。

这些方法的共同目标不是简单扩大参数量，而是通过状态、转移、驱动、稳定性和时间尺度等结构，减少纯黑箱相关性拟合的负担。

---

# 3. 对传统量化自回归范式的系统性质疑

## 3.1 先澄清“自回归”的不同含义

### 狭义单变量自回归

\[
y_t=\sum_{k=1}^{p}\phi_k y_{t-k}+\epsilon_t
\]

### 多变量或带外生变量的自回归

\[
y_t
=
\sum_{k=1}^{p}A_kX_{t-k}
+
BU_t
+
\epsilon_t
\]

### 深度序列预测

\[
\hat y_{t+H}=f_\theta(X_{t-L:t})
\]

其中 \(f_\theta\) 可以是 Transformer、Conformer、RNN、TCN 或 MLP。

因此，真正需要被挑战的并不是 autoregressive connection 本身，而是更深层的假设：

> 数据生成机制能否被稳定地压缩成一个从固定历史窗口到未来标签的静态映射。

---

## 3.2 质疑一：封闭系统假设

某个 altcoin 的过去上涨，可能不是因为“自己的上涨会自我延续”，而是因为：

- BTC 先上涨；
- 板块 leader 先上涨；
- funding、OI 和杠杆需求发生变化；
- 某交易所现货率先价格发现；
- 做市商库存重新平衡；
- liquidation cascade；
- 宏观风险偏好变化。

模型可能观察到：

\[
\text{past return}
\rightarrow
\text{future return}
\]

但真实机制可能是：

\[
\text{common driver}
\rightarrow
\begin{cases}
\text{past return}\cr
\text{future return}
\end{cases}
\]

一旦驱动机制、传导速度或市场结构改变，表面自回归关系就可能失效。

### 对当前项目的含义

110 个币不应被视为 110 个独立预测问题。模型必须区分：

- 全市场共同冲击；
- 板块或 cluster 轮动；
- 个币 idiosyncratic alpha。

---

## 3.3 质疑二：静态相关性不能表示状态转移

一个特征和未来收益相关，不代表模型知道：

- 它是否真正领先；
- 是否只是共同因子的结果；
- 在何种 regime 下有效；
- 作用滞后和半衰期；
- 是否会发生符号反转。

例如，高 funding 可能意味着：

- 趋势强，未来继续上涨；
- 多头拥挤，未来反转；
- 只是 BTC 上涨带来的共同现象。

静态模型可能学习到三种状态的平均关系，但平均关系可能在任何具体状态下都不够准确。

世界模型思路要求条件化于潜在状态：

\[
P(y_{t+H}\mid X_t,z_t,r_t)
\]

其中 \(z_t\) 或 \(r_t\) 代表当前系统状态或 regime。

---

## 3.4 质疑三：有限窗口难以自然表达多尺度长记忆

市场同时存在：

- 几分钟的冲击；
- 几小时的趋势或反转；
- 数天的资金轮动；
- 数周的 crowding；
- 更长的流动性和宏观 regime。

单一采样频率和固定窗口难以同时表达这些过程。Transformer/Conformer 可以扩大上下文，但会受到计算复杂度、长序列噪声、位置编码和有限训练样本的约束。

状态空间模型的潜在优势是：

- 递归压缩长历史；
- 用谱结构表示不同衰减速度；
- 对周期、振荡和长期依赖引入归纳偏置。

但这种结构优势必须通过 OOS 实验验证，不能直接等同于更高 alpha。

---

## 3.5 质疑四：非平稳性是机制变化，而不只是噪声

Crypto 永续市场中的以下因素会持续变化：

- 市场参与者结构；
- 交易所份额；
- 合约上线与下架；
- 手续费和 VIP 结构；
- 做市深度；
- funding 规则；
- 杠杆和强平机制；
- 叙事板块；
- BTC 对 alt 的传导；
- 市场有效性。

因此，模型需要的不只是 regularization，还需要：

- regime representation；
- dynamic relation；
- rolling recalibration；
- uncertainty/OOD detection；
- exposure scaling。

世界模型的实际价值之一，是把非平稳性从“误差项”提升为“待建模的状态”。

---

## 3.6 质疑五：点预测与真实交易目标错位

监督模型通常优化：

\[
L(\hat y_{i,t},y_{i,t})
\]

但真实目标是：

\[
\text{Net PnL}
=
\text{Cross-sectional alpha}
-
\text{fees}
-
\text{slippage}
+
\text{funding}
-
\text{risk losses}
\]

因此，更低的 MSE 不一定对应：

- 更高 RankIC；
- 更高 long–short spread；
- 更低 turnover；
- 更高 net Sharpe；
- 更小 drawdown；
- 更好的容量。

对于横截面组合，模型更应该关注：

- residual return；
- pairwise order；
- cross-sectional rank；
- top–bottom separation；
- uncertainty-adjusted alpha。

---

## 3.7 质疑六：点预测掩盖不确定性

传统模型常只输出：

\[
\hat y_{i,t}
\]

但相同预测值在不同 regime 下可信度完全不同。系统还应估计：

- aleatoric uncertainty；
- epistemic uncertainty；
- ensemble disagreement；
- OOD distance；
- regime confidence。

这些信息应该直接进入：

- 单币仓位；
- gross exposure；
- no-trade band；
- 风险预算；
- long/short 非对称控制。

---

# 4. 对原文章的必要保留意见

## 4.1 “Transformer 不理解时间”是过度表述

Transformer 可以通过 positional encoding、relative position、time-delta embedding、causal masking 和多尺度输入学习时间结构。

更准确的问题是：

> 它能否以足够高的样本效率、数值稳定性和 OOD 泛化能力学到正确动力学。

因此，不能把讨论简化为：

\[
\text{Transformer bad}
\quad\text{vs}\quad
\text{SSM good}
\]

所有比较都应在相同输入、参数量、训练预算和验证协议下完成。

---

## 4.2 S5/LRU 不天然优于 Conformer

S5/LRU 的潜在优势：

- 长序列复杂度较低；
- 长记忆；
- 稳定状态递推；
- 对衰减和振荡模式有较好先验。

Conformer 的优势：

- 局部卷积模式；
- 非线性 attention；
- 对短期冲击和复杂交互更灵活；
- 工程成熟度通常更高。

更合理的方向可能是多尺度融合：

```text
短周期局部流：Conformer / TCN
中长周期状态流：S5 / LRU
跨资产关系流：Sparse Graph Attention
全市场慢变量：Regime Encoder
```

---

## 4.3 预测图不等于因果图

如果 PCMCI、Granger 或 lagged mutual information 得到：

\[
X_{j,t-\tau}\rightarrow X_{i,t}
\]

它最多说明：在给定控制变量和样本条件下，\(X_j\) 的过去包含对 \(X_i\) 的增量预测信息。

市场中仍可能存在：

- 未观测共同原因；
- 同步价格发现；
- 交易所时钟误差；
- 流动性差异；
- 数据延迟；
- 选择偏差；
- regime-dependent confounding。

因此，建议统一使用：

- predictive driver；
- conditional lead–lag；
- dynamic dependency；

而不是未经验证的 economic causality。

---

## 4.4 新范式不能替代回测纪律

任何模型都无法修复：

- survivorship bias；
- 使用未来资产池；
- funding 结算错误；
- 合约上线前历史；
- 训练验证污染；
- 重叠标签显著性高估；
- 不现实的 slippage；
- 只在目标仓位上中性、实际成交不中性；
- 大规模试验后的 selection bias。

如果这些问题没有解决，架构升级只会让错误回测更复杂、更难审计。

---

# 5. 针对 110 币、4h 永续 Long–Short 的任务重定义

## 5.1 从独立逐币预测转向分层横截面预测

不充分的任务定义：

\[
X_{i,t-L:t}\rightarrow r_{i,t:t+4h}
\]

更合理的任务定义：

\[
\text{Global market state}
\rightarrow
\text{Sector state}
\rightarrow
\text{Asset relative state}
\rightarrow
\text{4h cross-sectional ordering}
\]

组合收益是：

\[
R^{LS}_{t:t+4h}
=
\sum_i w_{i,t}r_{i,t:t+4h}
\]

因此模型需要回答：

1. 未来 4h 的共同市场冲击是什么？
2. 哪些板块或 cluster 将相对占优？
3. 板块内部哪些币具有 idiosyncratic outperformance？

---

## 5.2 标签体系从 raw return 升级为 residual target

### 原始收益

\[
r^{4h}_{i,t}
=
\log\frac{P_{i,t+4h}}{P_{i,t}}
\]

原始收益可保留为辅助任务，但不建议作为唯一主标签。

### Market residual

\[
y^{mktres}_{i,t}
=
r^{4h}_{i,t}
-
\beta^{mkt}_{i,t}r^{4h}_{mkt,t}
\]

市场因子可以是 BTC、BTC+ETH、流动性加权市场组合、第一主成分或动态多因子组合。

### Market + sector residual

\[
y^{res}_{i,t}
=
r^{4h}_{i,t}
-
\beta^{mkt}_{i,t}r^{4h}_{mkt,t}
-
\sum_k\beta^{sector,k}_{i,t}r^{4h}_{sector,k,t}
\]

### 横截面 rank

\[
y^{rank}_{i,t}
=
\operatorname{rank}_{i\in U_t}(y^{res}_{i,t})
\]

### 风险调整收益

\[
y^{risk}_{i,t}
=
\frac{y^{res}_{i,t}}{\hat\sigma^{4h}_{i,t}+\epsilon}
\]

### 推荐多任务目标

\[
L
=
\lambda_1L_{rank}
+
\lambda_2L_{residual}
+
\lambda_3L_{direction}
+
\lambda_4L_{future\ vol}
+
\lambda_5L_{tail\ risk}
\]

重点不是公式复杂度，而是让训练目标与最终 long–short 决策一致。

---

# 6. 三层市场状态表示

## 6.1 Global Market State

全市场状态应包括：

- BTC、ETH 趋势与波动；
- 市场 breadth；
- 横截面 dispersion；
- 平均 correlation；
- aggregate volume、OI 和 funding；
- liquidation imbalance；
- risk-on / risk-off；
- alt relative strength；
- 市场流动性；
- 周末、时段和宏观事件状态。

可以抽象为：

\[
z_t^{market}
=
[
\text{trend},
\text{volatility},
\text{liquidity},
\text{crowding},
\text{correlation},
\text{risk appetite}
]
\]

---

## 6.2 Sector / Cluster State

建议同时使用两类板块：

### 静态经济语义分类

例如 L1、L2、DeFi、Meme、AI、Gaming、RWA、Exchange token。

### 动态统计聚类

根据滚动窗口内的 residual correlation、lead–lag、beta、funding/OI 同步性和 liquidity profile 构建。

板块层需要学习：

- leader–follower；
- 板块资金流；
- 板块 crowding；
- 板块内部 dispersion；
- 大币到小币的传导；
- 板块状态持续性。

---

## 6.3 Asset-Specific State

个币状态应包括：

- 自身趋势和反转；
- volume 与 volatility；
- relative strength；
- OI change；
- funding；
- basis；
- mark/index spread；
- spot–perp divergence；
- liquidation；
- 相对流动性；
- 相对板块 leader 的滞后；
- listing age 和合约结构。

个币层的目标是解释剩余的 idiosyncratic component，而不是重复学习市场共同方向。

---

# 7. 永续合约变量应被视为系统驱动

永续合约净收益包括：

\[
\text{Net PnL}
=
\text{Price PnL}
+
\text{Funding PnL}
-
\text{Fees}
-
\text{Slippage}
-
\text{Impact}
\]

## 7.1 Funding

Funding 同时是：

1. 持仓成本或收益；
2. crowding 指标；
3. 趋势或反转的条件变量。

高正 funding 可能对应趋势延续，也可能对应拥挤反转，必须在 regime 条件下解释。

## 7.2 Open Interest

OI 绝对值通常不如以下组合有意义：

- \(\Delta OI\)；
- price–OI joint state；
- OI / volume；
- OI / market cap；
- OI 与 funding 联合变化。

典型状态：

- price up + OI up：新杠杆推动；
- price up + OI down：空头回补；
- price down + OI up：新空头进入；
- price down + OI down：多头去杠杆。

## 7.3 Basis 与 Spot–Perp Divergence

这些变量可以反映：

- 杠杆需求；
- 价格发现方向；
- 套利约束；
- 交易所间资金流；
- 短期失衡。

## 7.4 Liquidation

Liquidation 既可能造成短期延续，也可能形成 overshoot 后反转。需要结合 OI、BTC 状态、流动性和 spread 判断。

---

# 8. 动态跨资产驱动图

## 8.1 图结构的价值

110 个资产的两两关系规模并不大，dense attention 在计算上可行。图结构的价值主要不是降计算量，而是引入：

- 稀疏性；
- 层级；
- 滞后；
- 稳定性；
- 条件依赖；
- regime conditioning。

## 8.2 推荐三级图

### Global-to-Asset

例如 BTC → high-beta alt、ETH → smart-contract sector、aggregate liquidation → crowded assets。

### Sector Graph

例如 sector leader → follower、large-cap → small-cap、spot leader → perp follower。

### Sparse Asset-to-Asset Graph

每个币仅保留 top-k 驱动资产及其 lag：

\[
h'_{i,t}
=
h_{i,t}
+
\sum_{j\in\mathcal N_i(t)}
\sum_\tau
g_{j\rightarrow i,\tau,t}W_\tau h_{j,t-\tau}
\]

## 8.3 不应直接在全部 raw feature 上穷举图

推荐三阶段：

1. **Feature-family compression**：将每币特征压缩为 return、volatility、liquidity、funding/basis、OI/leverage、liquidation、cross-venue 等状态族。
2. **Predictive screening**：使用 lagged partial RankIC、Elastic Net、stability selection、conditional mutual information 等筛选候选边。
3. **Reduced graph discovery**：在缩减后的节点和 lag 上使用 PCMCI、rolling conditional regression 或 graph attention。

## 8.4 必须包含的对照组

至少比较：

1. target-only；
2. all-assets dense attention；
3. static correlation graph；
4. rolling predictive graph；
5. regime-conditioned graph；
6. random graph；
7. shuffled-edge graph；
8. 相同边数但随机 lag 的图。

如果动态图不比 dense attention 或随机稀疏图好，就不能证明模型发现了有价值的驱动结构。

---

# 9. S5、LRU、Conformer 与多尺度建模

## 9.1 为什么 4h horizon 让 SSM 更值得验证

若输入使用 5 分钟、15 分钟、1 小时等多尺度历史，序列长度可能达到数千步。此时 S5/LRU 的长记忆和线性复杂度具有现实价值。

但更长上下文不等于更多有效信息。应先验证：

- 不同 lookback 的边际信息；
- 信号半衰期；
- 采样频率；
- 长周期变量是否可由更简单的 regime encoder 表示。

## 9.2 推荐多尺度架构

```text
┌─────────────────────────────────────────────────────┐
│                    Point-in-time data                 │
├─────────────────────────────────────────────────────┤
│  Short stream     │  Medium stream   │  Slow stream │
│  5m/15m           │  1h/4h           │  1d/regime   │
│  Conformer/TCN    │  S5/LRU           │  SSM/MLP     │
└──────────────┬──────────────┬──────────────┬─────────┘
               └──────────────┼──────────────┘
                              ▼
                   Global–Sector–Asset states
                              │
                              ▼
                   Dynamic sparse driver graph
                              │
                              ▼
                Residual / rank / vol / uncertainty
                              │
                              ▼
                 Cost-aware portfolio optimization
```

## 9.3 架构成功标准

不能只看 validation loss，应至少要求：

- mean RankIC 提升；
- RankIC ICIR 提升；
- top–bottom spread 提升；
- net Sharpe 提升；
- turnover 不显著恶化；
- 多年份和多 regime 稳定；
- 大币与小币贡献不过度集中；
- 删除极端窗口后仍然有效；
- 相同参数量和训练预算下优于 baseline。

---

# 10. 择时在 4h Long–Short 中的正确位置

## 10.1 大盘方向择时不是第一优先级

当组合满足 dollar neutral、BTC beta neutral 和 sector exposure control 时，主要收益来自相对强弱，而非 BTC 涨跌。

因此，不建议把系统变成“先预测 BTC 方向，再决定是否做横截面”的 hard gate。

## 10.2 横截面机会择时最重要

不是每个 4h 窗口都具有相同的横截面可预测性。可定义：

\[
q_t^{opportunity}
=
f(
\text{signal spread},
\text{confidence},
\text{predicted dispersion},
\text{correlation},
\text{liquidity}
)
\]

高机会环境通常具有：

- 预测 score dispersion 较大；
- 未来横截面 dispersion 较高；
- sector rotation 清晰；
- ensemble 一致；
- 市场共同相关较低；
- leader–follower 稳定；
- 流动性良好。

## 10.3 风险暴露择时

建议连续调整 gross：

\[
G_t
=
G_0
\cdot
\frac{\sigma_{target}}{\hat\sigma_{p,t}}
\cdot
c_t
\]

高 correlation、高 liquidation、高 spread 或模型 OOD 时降仓，通常比 binary on/off 更稳健。

## 10.4 交易择时

每 4 小时生成新预测，不代表每次都应完全换仓。交易应满足：

\[
\Delta\hat\alpha
>
\text{fee}
+
\text{slippage}
+
\text{funding impact}
+
\text{uncertainty buffer}
\]

应验证：

- no-trade band；
- ranking hysteresis；
- partial rebalance；
- turnover penalty；
- minimum expected edge；
- maker/taker expected-value execution。

择时更应该决定“换不换、换多少”，而不是“本期是否完全开仓”。

## 10.5 Long 与 Short 风险不完全对称

Short 侧具有 squeeze、极端负 funding、低流动性和跳涨风险。可以分别估计：

\[
q_t^{long},\qquad q_t^{short}
\]

允许两侧风险预算不同，并用 BTC、ETH 或高流动性指数合约做临时 bridge hedge。

---

# 11. 从预测到组合决策

建议组合层直接优化：

\[
\max_w
\quad
\hat\alpha_t^\top w
-
\lambda_r w^\top\Sigma_t w
-
\lambda_{turn}\|w-w_{t-1}\|_1
-
\widehat C_t(w,w_{t-1})
+
\widehat F_t^\top w
\]

其中：

- \(\hat\alpha_t\)：预测 residual alpha；
- \(\Sigma_t\)：动态风险矩阵；
- \(\widehat C_t\)：fee、spread、slippage 和 impact；
- \(\widehat F_t\)：预期 funding contribution；
- \(w_{t-1}\)：当前持仓。

约束可包括：

- dollar neutral；
- BTC beta neutral；
- sector neutral；
- 单币仓位上限；
- liquidity/capacity；
- gross leverage；
- turnover budget；
- funding exposure；
- short concentration；
- actual-fill neutrality。

特别需要强调：

> 中性约束应在实际成交仓位上监控，而不仅是目标仓位。

若部分低流动性订单暂时无法完成，可以使用 BTC/ETH 或高流动性合约作为 bridge hedge，而不是无条件使用 taker 完成所有订单。

---

# 12. 数据、资产池与标签风险

## 12.1 Point-in-time universe

必须使用当时真实可交易的资产池：

\[
U_t=
\{\text{contracts tradable at time }t\}
\]

不能使用今天仍存活的 110 个币回看全部历史。需要记录：

- listing/delisting time；
- contract status；
- tick size；
- min notional；
- historical volume；
- spread/depth；
- funding rule；
- 当时交易所可用性。

## 12.2 4h 标签重叠

若每小时预测未来 4h，则相邻标签高度重叠，导致有效样本数高估和 fold 泄漏。

应使用：

- purged walk-forward；
- 至少覆盖 label horizon 的 purge；
- embargo；
- block bootstrap；
- HAC/Newey–West 风格相关性修正；
- 非重叠样本 sanity check。

若策略严格每 4h 预测一次，问题较小，但 fold 边界仍需 purge。

## 12.3 Funding 与执行时间对齐

必须明确：

- 开仓、关仓和 funding settlement 的时点；
- 使用 announcement funding 还是 realized funding；
- 多交易所 funding 时钟；
- mark price 与成交价；
- funding cash flow 的归属。

任何将未来 realized funding 作为开仓特征的做法都会产生泄漏。

---

# 13. 推荐实验路线

## P0：最高优先级

### P0-1 标签重构

比较：

- raw 4h return；
- cross-sectional demeaned return；
- BTC/ETH residual；
- PC1 residual；
- market + sector residual；
- residual rank；
- volatility-scaled residual rank。

### P0-2 三层状态拆解

比较：

- per-asset only；
- asset + global；
- asset + global + sector；
- global + sector + asset + perpetual state。

### P0-3 永续变量增量价值

分组消融：funding、OI、basis、liquidation、mark/index、spot–perp 和 aggregate derivatives state。

### P0-4 成本感知与 no-trade

比较：

- full rebalance；
- turnover penalty；
- no-trade band；
- partial rebalance；
- funding-aware rebalance；
- maker/taker expected-value execution。

### P0-5 Point-in-time 审计

审计资产池、delisting、listing age、funding、fee tier、spread 和 actual fills。

---

## P1：高价值模型实验

### P1-1 动态稀疏图

比较 no graph、dense attention、static graph、rolling graph、regime-conditioned graph 和 random/shuffled graph。

### P1-2 S5/LRU challenger

在相同条件下比较 Conformer、S5、LRU、TCN、Conformer+S5，以及 local encoder + global state encoder。

### P1-3 Opportunity/Risk Timing

先做连续 scaling：

- volatility targeting；
- signal spread scaling；
- ensemble confidence；
- correlation/liquidation risk scaling；
- long/short asymmetric scaling。

暂不优先做 binary on/off meta-model。

---

## P2：研究型探索

### P2-1 Koopman latent dynamics

在压缩后的 market/sector state 上学习：

\[
z_{t+1}\approx Kz_t
\]

而不是直接对所有 raw feature 使用 Koopman。

### P2-2 Regime-conditioned Koopman

\[
z_{t+1}\approx K_{r_t}z_t
\]

检验不同 regime 是否对应不同转移算子。

### P2-3 Neural Operator

仅当需要跨采样频率泛化、连续时间响应，并且简单 SSM 已被证明不足时再提高优先级。

---

# 14. 验证协议

## 14.1 Walk-forward 内必须重新估计

每个 fold 内完成：

- feature normalization；
- universe construction；
- graph estimation；
- sector clustering；
- beta/residual label estimation；
- hyperparameter selection；
- uncertainty calibration。

使用全样本估计图、聚类、PCA、beta 或标准化都会产生泄漏风险。

## 14.2 核心指标

### 预测层

- Pearson IC；
- RankIC；
- ICIR；
- pairwise accuracy；
- top–bottom monotonicity；
- calibration；
- uncertainty–error monotonicity。

### 组合层

- gross/net return；
- gross/net Sharpe；
- Sortino；
- maximum drawdown；
- turnover；
- fee/alpha ratio；
- funding contribution；
- long/short 分侧 PnL；
- beta/sector exposure；
- capacity；
- realized slippage。

### 稳定性

按年份、bull/bear/sideway、high/low vol、high/low correlation、weekday/weekend、UTC block、流动性层级、sector 和 listing age 分组。

## 14.3 必须报告的稳健性检查

- 删除最好 5–10 个窗口后的表现；
- ex-top-1 / ex-top-5 币种贡献；
- 最差 fold；
- seed variance；
- 不同成本和 delay；
- 不同 liquidity constraint；
- 不同 funding 处理；
- 不同持仓数量；
- 不同 gross exposure；
- actual fill 与 target portfolio 的差异。

## 14.4 多重试验和研究者自由度

应维护完整 experiment ledger，并使用：

- untouched OOS test；
- nested validation；
- Deflated Sharpe Ratio；
- White’s Reality Check 或类似方法；
- candidate count；
- 预注册关键实验假设。

不能只汇报最终胜出的模型。

---

# 15. 关键失败模式

## 15.1 图模型只是在增加搜索空间

动态图表现更好可能只是因为参数更多、候选特征更多、超参数搜索更广。必须进行 matched-capacity 和 matched-search-budget 对比。

## 15.2 模型学到 beta 或流动性，而不是 alpha

若高分资产长期是高 beta、高 volatility、低 liquidity 或新上市小币，策略可能只是在承担未定价风险。

需要检查：

- beta-neutral residual；
- volatility/liquidity bucket；
- listing-age bucket；
- risk contribution；
- tail loss。

## 15.3 动态图过于不稳定

应评估：

- edge survival rate；
- top-k overlap；
- regime consistency；
- lag stability；
- 与随机图差异；
- 关系变化是否领先于业绩变化。

## 15.4 择时模型样本太少

币级样本量约为 \(T\times N\)，而组合级择时样本只有 \(T\)。直接预测“下一期策略是否赚钱”的 meta-model 很容易过拟合。

更稳健的做法是预测中间量：

- future dispersion；
- portfolio risk；
- transaction cost；
- model disagreement；
- liquidity stress；

再转化为 exposure scaling。

## 15.5 世界模型变成不可证伪的大系统

若系统同时加入多尺度、图、regime、SSM、多任务和复杂组合层，提升将难以归因。

必须坚持模块化：

1. 每个模块有明确假设；
2. 有单独对照组；
3. 有预期影响指标；
4. 有失败标准；
5. 可以独立移除。

---

# 16. 推荐的最终系统蓝图

```text
                         ┌──────────────────────┐
                         │ Point-in-time universe│
                         └──────────┬───────────┘
                                    │
          ┌─────────────────────────┼─────────────────────────┐
          │                         │                         │
          ▼                         ▼                         ▼
 Global market features     Sector/cluster features   Per-asset perp features
 BTC/ETH, breadth, corr      rotation, leader state    price, vol, OI, funding
 dispersion, liquidity      crowding, dispersion      basis, liquidation
          │                         │                         │
          ▼                         ▼                         ▼
 Global state encoder       Sector state encoder      Asset temporal encoder
   SSM / small model          graph/SSM/attention      Conformer + S5/LRU
          │                         │                         │
          └─────────────────────────┼─────────────────────────┘
                                    ▼
                     Dynamic predictive driver graph
                                    │
                                    ▼
                         Multi-task prediction heads
                    residual / rank / vol / tail / uncertainty
                                    │
                                    ▼
                       Opportunity & risk state estimator
                                    │
                                    ▼
                       Cost/funding-aware optimizer
                                    │
                                    ▼
                    Dynamic execution and actual-fill hedge
```

该结构的核心不是模型更大，而是完成四个分解：

1. 共同市场变化与相对 alpha 分离；
2. 长期状态与短期冲击分离；
3. 预测均值与不确定性分离；
4. 预测、仓位和执行成本统一。

---

# 17. 团队重点讨论问题

## 当前瓶颈

1. 当前瓶颈究竟是标签噪声、状态缺失、模型容量、成本，还是回测偏差？
2. 当前模型的 alpha 来自 market beta、sector beta，还是 idiosyncratic ranking？
3. RankIC 在哪些 regime、币种和 liquidity bucket 中失效？
4. 组合亏损主要来自预测错误，还是换手、滑点、funding 和成交不完整？

## 世界模型

5. 哪些变量可以定义为“状态”，哪些只是观测？
6. 哪些外部驱动具有明确经济或微观结构含义？
7. 我们需要完整生成式世界模型，还是更简单的分层判别模型？
8. 动态图是否提供 dense attention 之外的增量价值？
9. 状态转移是否比静态 supervised mapping 更稳定？

## 择时

10. 是否存在可重复的横截面 opportunity regime？
11. timing 提升是否只是通过降低平均 exposure 获得？
12. 是否保留足够 gross PnL？
13. long 和 short 两侧是否需要不同风险预算？
14. timing 是否更应该用于换仓，而不是策略开关？

## 验证

15. residual、cluster、graph 是否全部在 fold 内估计？
16. 资产池是否严格 point-in-time？
17. 是否正确处理 4h 重叠标签？
18. 是否记录全部实验次数和候选搜索空间？
19. 提升是否跨年份、regime 和流动性层级存在？
20. 复杂模型是否在相同预算下优于简单 baseline？

---

# 18. 开源资源与参考方向

| 方向 | 项目/论文 | 适合用途 | 注意事项 |
|---|---|---|---|
| Abel 工作流 | `Abel-ai-lab/predict-anything` | 策略研究、图驱动搜索、实验审计思路 | 公开仓库主要是研究工作流，并非完整 TWM 底层实现 |
| PCMCI | `jakobrunge/tigramite` | 条件 lead–lag、PCMCI/PCMCI+ | 不宜直接在全部高维 raw feature 上运行 |
| S5 | `lindermanlab/S5` | 长序列状态空间编码 | 需评估 JAX 迁移和工程成本 |
| S4 | `state-spaces/s4` | 结构化状态空间基线 | 可作为 SSM 对照 |
| LRU | Linear Recurrent Unit 论文及社区实现 | 轻量长记忆 challenger | 社区实现质量不一 |
| Causal Discovery | `py-why/causal-learn` | 因果发现实验 | 金融观测数据难满足严格因果假设 |
| Koopman | `dynamicslab/pykoopman` | latent state 上的 Koopman 实验 | 建议先用于 market/sector state |
| Neural Operator | `neuraloperator/neuraloperator` | 连续算子研究 | 当前优先级较低 |

对 Abel 公开内容应保持谨慎：公开仓库可帮助理解“搜索外部驱动、构建图、审计策略实验”的工作流，但不能据此认定文章描述的完整 TWM、S5/LRU 或金融世界模型已经公开并可直接复现。

---

# 19. 最终判断

原文章最值得吸收的，不是某个新模型名称，而是问题定义的重构：

> 金融市场不是由目标变量自身历史闭环决定的序列，而是一个具有共同状态、跨资产传导、外生驱动、制度约束和决策成本的动态系统。

但它最容易被误用的地方，是把这个正确的系统观直接等同于：

- 因果图一定优于相关性模型；
- SSM 一定优于 Transformer；
- 世界模型一定优于 supervised prediction；
- 更宏大的建模目标一定带来更高收益。

对于 110 币、4h 永续 Long–Short，更合理的新范式不是直接训练一个“预测整个 Crypto 世界”的巨大生成模型，而是建立可证伪的分层系统：

\[
\boxed{
\text{Global state}
\rightarrow
\text{Sector state}
\rightarrow
\text{Asset residual alpha}
\rightarrow
\text{Uncertainty-aware ranking}
\rightarrow
\text{Cost-aware portfolio}
}
\]

是否真正进入新范式，不应由概念先进程度决定，而应由以下证据决定：

1. 在严格 point-in-time、purged walk-forward 下稳定提升；
2. 提升存在于多个市场状态，而不是单一行情；
3. net Sharpe、drawdown、turnover 和容量同步改善；
4. 动态图、SSM 和 timing 各自具有可归因的增量价值；
5. 复杂度增加没有被搜索宽度、样本泄漏和成本低估解释。

因此，团队真正应追求的不是“从传统模型切换到世界模型”这一标签，而是：

> **从单目标、静态、相关性驱动的预测器，升级为分层、动态、外生驱动、带不确定性并与组合决策闭环的系统。**

这才是文章对当前项目最有价值、也最可验证的启发。
