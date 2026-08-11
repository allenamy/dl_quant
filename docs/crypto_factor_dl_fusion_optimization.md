# 4h Crypto Cross-Sectional Alpha：因子、DL模型与融合框架优化建议

## 1. 核心结论

当前 `king` 模型在 raw return 上 RankIC 约 **0.06**，在残差目标上约 **0.048**，说明时序主干和跨资产建模已经捕捉到了相当强的横截面信息。现在不应把主要精力放在简单扩大模型容量，而应优先解决三个结构性问题：

1. **排序目标与收益幅度目标被压在同一个输出头里，导致排序很好但极值被压平。**
2. **逐时点残差化过度消除了可预测的幅度，并给标签额外注入了横截面回归噪声。**
3. **固定比例混合多个异质因子，正在用弱腿和慢腿稀释强模型，而不是提取真正的增量信息。**

推荐的总体方向是：

> 将当前单一预测问题重构为“可解释基线因子收益 + DL增量残差 + 尾部分布 + 预测不确定性”的分解式模型；因子融合改用严格样本外的 residual stacking 或约束型 meta learner，而不是固定分数加权。

---

## 2. 当前方案中值得保留的部分

以下原则应继续保留：

- Point-in-time 成员宇宙与因果特征；
- 使用非重叠 4h 标签进行正式评估；
- 所有币共享时序主干；
- 先做单币时序编码，再做横截面交互；
- 直接优化 RankIC，而不是只用 MSE 预测低信噪比收益；
- 强调增量预测能力、换手、成本和真实执行；
- 将模型排序、组合风险与执行分层处理。

直接优化 RankIC 的方向是合理的。当前主要问题不在主干模型，而在监督目标、输出头、残差化和融合方式。

---

## 3. 需要纠正的几个关键判断

### 3.1 Huber 与排序损失并非天然共线

即使 Huber 与 LambdaRankIC 使用同一个标签，两者的梯度也可能：

- 同向；
- 近似正交；
- 直接冲突。

Huber 优化点预测误差，排序损失优化资产之间的顺序和相对位置。固定使用：

\[
0.7L_{\text{rank}}+0.3L_{\text{Huber}}+0.1L_{\text{pinball}}
\]

不代表多任务已经被合理平衡。

建议训练时记录：

\[
\cos(g_{\text{rank}},g_{\text{mag}})
=
\frac{g_{\text{rank}}\cdot g_{\text{mag}}}
{\lVert g_{\text{rank}}\rVert\lVert g_{\text{mag}}\rVert}
\]

并比较：

- 固定损失权重；
- GradNorm；
- PCGrad；
- CAGrad。

选择标准必须是样本外 RankIC、tail spread 和净 PnL，而不是训练 loss。

---

### 3.2 残差标签正交，不代表预测值样本外正交

每个时点的真实残差满足：

\[
X_t^\top YR_t\approx0
\]

但不能推出：

\[
X_t^\top\hat YR_t=0
\]

样本外预测仍可能重新带有：

- Beta；
- Size；
- Momentum；
- Funding；
- Liquidity；
- 非线性基线因子暴露。

因此应直接监控预测值因子暴露：

\[
\hat b_t
=
(X_t^\top X_t+\lambda I)^{-1}X_t^\top\hat y_t
\]

若残差头确实要求中性，可增加：

\[
L_{\text{neutral}}
=
\left\|
X_t^\top\hat\epsilon_t
\right\|_2^2
\]

不能只依赖标签残差化。

---

### 3.3 名义样本量不等于有效独立样本量

`110 × 6 × 365` 不能直接视为 24 万次独立下注。

原因包括：

- 币之间共享 BTC、Altcoin、流动性、动量和行业因子；
- 相邻 4h 周期存在时间依赖；
- 极端行情中相关性明显上升；
- PnL 可能集中在少量币或少量 regime。

正式显著性评估应使用：

- 日或周 block bootstrap；
- 时间聚类标准误；
- 横截面与时间双向聚类；
- regime 级别留出；
- 逐月、逐季度汇总后再计算 Sharpe 与 t 值。

---

## 4. “排序好，但极值被打平”的诊断框架

首先区分两种情况。

### 4.1 只是全局尺度偏小

如果：

\[
\hat y_i=c\cdot y_i,\qquad c\ll1
\]

排序与尾部形状都正确，只是整体缩小，那么只需要 OOF 校准：

\[
\hat y_i^{cal}=a+b\hat y_i
\]

无需重训主模型。

### 4.2 尾部形状真正被压平

更危险的情况是：

- 中间 80% 排序正确；
- 极端上涨和下跌只被预测为轻微偏离；
- 预测分布尾部明显薄于真实分布；
- 单一线性 rescale 无法恢复真实极值。

建议立即生成以下诊断。

#### 预测分桶曲线

将预测分成 20 个横截面桶，计算：

\[
E[Y\mid \hat y\in bucket_k]
\]

观察最高和最低几个桶是否继续单调扩张。

#### 条件校准斜率

分别在：

- 中间 80%；
- Top 10%；
- Bottom 10%；
- Top/Bottom 2%；

拟合真实收益对预测值的斜率。

#### Tail Recall

检查真实 Top 5% 和 Bottom 5% 的资产，有多少进入预测对应尾部。

#### 线性与非线性校准对比

比较：

- Linear calibration；
- Isotonic regression；
- Monotonic spline。

若非线性校准显著优于线性，说明问题是形状压平，而非简单尺度偏小。

---

## 5. 幅度塌缩的主要原因

### 5.1 RankIC 目标对尺度不敏感

只要排序不变：

\[
\hat y,\quad0.1\hat y,\quad0.001\hat y
\]

RankIC 相同。

当排序损失占主要权重时，模型没有足够动力恢复真实收益幅度。

### 5.2 残差目标天然更接近零，且噪声更高

每个时点只有约 110 个币，却要估计多个高度相关的基线因子收益。若 ridge 很弱，残差化容易：

- 过拟合当期横截面噪声；
- 消除原本可预测的幅度；
- 注入不稳定的回归误差；
- 让模型最安全的幅度预测回到零附近。

### 5.3 Huber 与中央分位数鼓励向中心收缩

在低信噪比条件下，条件均值与中位数本来就接近零。提高 Huber 权重不一定能恢复极端值，反而可能损害排序。

### 5.4 当前 QIM 对尾部监督仍可能不足

若分位点过于均匀、尾部点少、分布损失权重低，则 q01/q99 的有效训练信号仍然很弱。

---

## 6. 推荐的 DL 模型重构

### 6.1 分解式建模

将最终收益分解为：

\[
Y_{i,t}
=
F_{i,t}^\top b_t
+
\epsilon_{i,t}
\]

其中：

- \(F_{i,t}\)：Funding、Size、Momentum、Beta 等可解释基线因子；
- \(b_t\)：当前市场状态下的因子收益；
- \(\epsilon_{i,t}\)：基线无法解释的增量残差。

模型分别预测：

\[
\hat b_t=g_{\text{factor}}(M_t)
\]

\[
\hat\epsilon_{i,t}
=
g_{\text{res}}(h_{i,t},H_t)
\]

最终：

\[
\hat Y_{i,t}
=
F_{i,t}^\top\hat b_t+\hat\epsilon_{i,t}
\]

这一设计优于将 raw return 完全残差化，因为：

1. 不会永久丢失可预测的基线因子收益；
2. 基线因子收益可以随 regime 变化；
3. 残差头仍可显式约束中性；
4. raw 与 residual 可以同时监督；
5. 最终输出天然适合进入组合，而非事后固定比例拼接。

---

### 6.2 推荐的四类输出头

#### 头一：Residual Rank Head

\[
s^{res}_{i,t}
\]

优化 residual RankIC，捕捉基线因子之外的增量排序。

#### 头二：Raw Rank Head

\[
s^{raw}_{i,t}
\]

优化 raw return RankIC，保留基线因子与非线性交互的总预测力。

#### 头三：Distribution / Magnitude Head

使用尾部更密集的非均匀分位数：

\[
\tau\in
\{
0.01,0.025,0.05,0.10,0.20,
0.35,0.50,
0.65,0.80,0.90,0.95,0.975,0.99
\}
\]

输出：

- 条件均值；
- 条件中位数；
- 分布宽度；
- 上下行 tail expectation；
- 偏度代理；
- 预测不确定性。

不要再让 q50 同时承担排序和幅度职责。

#### 头四：Tail Event Head

分别预测：

\[
P(Y>Q_{0.9}),\qquad P(Y<Q_{0.1})
\]

以及：

\[
E[Y\mid Y>Q_{0.9}]
\]

\[
E[Y\mid Y<Q_{0.1}]
\]

将尾部问题拆成：

> 是否进入尾部 × 进入尾部后的条件幅度。

---

### 6.3 推荐总损失

\[
\begin{aligned}
L=&\;
\lambda_1L_{\text{RankIC,res}}
+\lambda_2L_{\text{RankIC,raw}}\\
&+\lambda_3L_{\text{distribution}}
+\lambda_4L_{\text{tail-cls}}
+\lambda_5L_{\text{tail-mag}}\\
&+\lambda_6L_{\text{neutral}}
+\lambda_7L_{\text{turnover}}
\end{aligned}
\]

建议：

- 每项损失单独记录梯度范数；
- 记录任务间梯度余弦；
- 第一版使用 GradNorm；
- 冲突明显时再测试 PCGrad/CAGrad；
- 选择标准使用 OOF RankIC、尾部收益差、净 Sharpe 与成本。

---

## 7. 标签体系优化

### 7.1 Raw 与 Residual 双头，不应二选一

建议严格比较以下四组：

| 模型 | 训练目标 | 主要评估 |
|---|---|---|
| A | Raw return | Raw RankIC |
| B | Residual return | Residual RankIC |
| C | Raw return，预测后中性化 | Residual RankIC |
| D | Raw + Residual 双头 | 两套 RankIC 与净 PnL |

最关键的是 C：

> 将 raw 模型的 OOF 预测事后对基线因子做横截面残差化，再与 residual target 计算 RankIC。

如果其 residual RankIC 达到或超过 0.048，则直接训练高噪声残差标签未必必要。

---

### 7.2 残差化要加强收缩与稳健性

建议比较：

- 更强固定 ridge；
- CV 选择 ridge；
- 时间平滑的因子收益；
- Robust Huber 横截面回归；
- Inverse-volatility WLS；
- 对高波动、低流动性币降低回归权重。

目标不是每个时点机械 100% 正交，而是获得稳定、可预测、与最终组合约束一致的残差。

---

### 7.3 风险标准化标签

若最终仓位会做 volatility scaling，则模型目标应与持仓目标对齐：

\[
Z_{i,t}
=
\frac{YR_{i,t}}
{\hat\sigma_{i,t}^{\gamma}}
\]

其中：

\[
\gamma\in\{0.5,1.0\}
\]

模型预测每单位风险的残差收益，再恢复 bps 尺度：

\[
\hat\alpha_{i,t}
=
\hat Z_{i,t}\hat\sigma_{i,t}^{\gamma}
\]

可以缓解：

- 高波动币支配标签；
- 极端样本主导排序损失；
- 模型目标与 sizing 不一致；
- 信号翻转时高波动币残留风险。

---

### 7.4 多 Horizon 监督

同时构造：

\[
Y^{1h},Y^{2h},Y^{4h},Y^{8h}
\]

并学习：

\[
Y^{proxy}
=
\sum_\delta\lambda_\delta Y^\delta
\]

外层仍以真实 4h 目标验证。

第一版可先使用多头预测：

- 1h：快速兑现；
- 2h：中短期；
- 4h：主目标；
- 8h：慢因子与持续性。

随后在严格 OOF 结果上学习稳定组合。

---

## 8. 模型架构优化建议

### 8.1 主干不宜盲目扩大

当前两层 Conformer、hidden size 64、7 天窗口，在 110 币、低信噪比条件下已具备足够容量。

更高 ROI 的改造在于表示分解与输出头，而不是继续加深加宽。

---

### 8.2 三路径时序编码

#### Slow / Trend Branch

- 24h–168h Momentum；
- Funding EMA；
- Size；
- Beta；
- Liquidity State；
- 中长期 Volatility。

#### Fast / Fluctuation Branch

- 1h–8h Momentum/Reversal；
- 近期 Volume Change；
- Intraday Dispersion；
- 短期 Cross-sectional Breadth。

#### Shock / Idiosyncratic Branch

- Max Return；
- Jump Variation；
- Liquidation；
- Abnormal Volume；
- Funding/Basis Shock；
- 极端 Spread 或流动性异常。

其中：

- Slow branch 可使用更强跨资产交互；
- Fast branch 使用短卷积或短 attention；
- Shock branch 应更多保留单币局部信息，避免噪声扩散。

---

### 8.3 横截面 Attention 改为稀疏或结构化

全连接 110 币 attention 容易传播低流动性币噪声和局部异常。

建议比较：

1. 全连接 attention；
2. Top-K rolling residual-correlation 邻居；
3. Sector/Theme 分组 attention；
4. BTC、ETH、Alt Breadth、Funding Dispersion 等市场 factor tokens；
5. 稀疏动态邻居 attention。

---

### 8.4 优先优化输出 Head

可测试受限残差式 gating：

\[
s_i
=
w_0^\top h_i
+
\tanh(w_g^\top h_i)
\cdot
w_1^\top h_i
\]

它保留稳定线性排序路径，只允许有限非线性修正，通常比扩大主干更低风险。

---

## 9. 因子构建升级

### 9.1 Derivatives Positioning

优先补充：

- Open Interest level/change；
- Price × OI 四象限；
- Perp-spot basis；
- Funding term structure；
- 跨交易所 funding dispersion；
- Liquidation imbalance；
- Long/short positioning；
- Top trader positioning；
- OI-adjusted turnover。

### 9.2 Microstructure 与可交易性

- Trade imbalance；
- Aggressive buy/sell volume；
- Spread；
- Depth slope；
- Microprice；
- Order-book imbalance；
- Cancel rate；
- 短期 maker markout；
- Size/depth ratio。

需要明确区分：

- Alpha feature；
- Execution feature。

不是所有微观结构特征都应进入 4h 方向模型。

### 9.3 Tail 与 Jump

- Realized semivariance；
- Bipower variation；
- Jump variation；
- Realized skewness；
- Extreme-return frequency；
- Drawdown speed；
- Liquidation-adjusted jump；
- Upside/downside tail index。

这是解决极值被打平最值得补充的一类输入。

### 9.4 Cross-sectional Market State

- Return dispersion；
- Funding dispersion；
- Beta dispersion；
- Breadth；
- BTC dominance proxy；
- High-beta minus low-beta spread；
- Meme/AI/L1 等主题因子收益；
- Cross-sectional correlation level。

这类特征主要用于：

- 判断当前哪类因子有效；
- 决定是否信任 cross-asset interaction；
- 调整融合权重；
- 调整杠杆和风险预算。

---

## 10. 因子筛选从独立 IC 升级为条件增量

新因子不能因为单独 RankIC 为正就进入系统。

建议依次评估：

1. 单因子 RankIC；
2. 对 king 预测残差后的 incremental IC；
3. 对当前完整组合预测残差后的 incremental IC；
4. 加入后的净 PnL；
5. 换手与 maker rate 变化；
6. 不同 regime 下符号稳定性；
7. 是否依赖少数极端币；
8. 与已有腿的预测与 PnL 相关性。

录用条件应是：

\[
\Delta U
=
\Delta E[PnL]
-
\lambda\Delta Risk
-
\kappa\Delta Cost
>0
\]

而不是仅仅：

\[
IC_k>0
\]

---

## 11. 为什么多因子融合后 RankIC 下降

### 11.1 弱腿稀释 King

若 king 的 raw RankIC 约 0.06，而其他腿只有 0.01–0.03，则它们只有在足够低相关、方向稳定且真正提供增量时才值得加入。

低相关不代表适合进入统一 score。

### 11.2 不同因子预测的是不同经济对象

- King：4h residual；
- S2：24h residual；
- Funding：拥挤与反转；
- Size：慢速风险溢价。

简单 rank、z-score、L1 normalize 后固定相加，相当于假设它们：

- 量纲一致；
- 置信度一致；
- horizon 一致；
- 当前有效性一致。

这个假设不成立。

### 11.3 Rank 转换抹掉强弱信息

所有腿先 rank 或 z-score 后再按固定 gross 分配，会让：

- 强腿；
- 弱腿；
- 当前没有 edge 的腿；

都获得预设权重，从而系统性稀释 king。

### 11.4 Raw 与 Residual 口径混杂

King 预测 residual，但 funding 与 size 又是残差化过程中被扣除的部分。正确形式应是：

\[
\hat Y
=
\widehat{\text{baseline component}}
+
\widehat{\text{residual component}}
\]

而不是固定 0.3/0.3/0.3/0.1 的分数拼接。

---

## 12. 推荐的因子融合方式

### 12.1 第一选择：OOF Residual Stacking

流程：

1. 获取严格 walk-forward OOF 的 king 预测；
2. 用 king 解释目标；
3. 在 king 残差上评估 funding；
4. 加入 funding 后继续计算残差；
5. 再评估 size、S2 和其他因子；
6. 每条腿只有在 OOF 上提供稳定增量时才加入。

形式：

\[
r^{(0)}=Y
\]

\[
r^{(1)}=r^{(0)}-\hat Y_{\text{king}}
\]

\[
r^{(2)}=r^{(1)}-\hat Y_{\text{funding}}
\]

依次进行。

核心问题不是某条腿单独有没有 IC，而是它是否在已有系统之后仍然提供增量。

---

### 12.2 第二选择：约束型 Meta Learner

使用全部 OOF leg prediction 学习：

\[
\hat Y_t
=
\sum_k w_{k,t}s_{k,t}
\]

约束：

\[
w_k\ge0
\]

\[
\sum_k w_k=1
\]

\[
w_k\le w_{max}
\]

并加入：

\[
\eta\lVert w-w_0\rVert^2
\]

\[
\kappa\lVert w_t-w_{t-1}\rVert_1
\]

含义是：

- 向简单先验收缩；
- 限制权重集中；
- 限制时间变化；
- 纳入换手和成本。

第一版推荐：

- Constrained Ridge；
- Non-negative Elastic Net；
- Shallow Gated Linear Model。

不建议直接使用复杂 Transformer 融合少数因子腿。

---

### 12.3 Slow Factor 更适合独立 Sleeve

建议分别形成：

- 4h King Sleeve；
- 24h S2 Sleeve；
- Funding Sleeve；
- Size Sleeve。

最终：

\[
w_t^{book}
=
w_t^{king}
+
w_t^{funding}
+
w_t^{size}
+
w_t^{s2}
\]

每个 sleeve 分别控制：

- Gross；
- Vol target；
- Turnover；
- Beta；
- Capacity；
- Execution urgency。

这样可以保留慢腿的低换手与分散化价值，同时不破坏 king 的排序。

---

### 12.4 动态 Gate 要克制

Gate 可以使用：

- 市场波动；
- 横截面 dispersion；
- 平均相关性；
- Funding dispersion；
- Liquidity；
- Trend strength；
- 最近 OOF residual IC。

但应加入：

- Bayesian/Kalman shrinkage；
- 权重变化上限；
- 最低持有周期；
- 只有在显著 regime 差异下动作；
- 固定权重始终作为 benchmark。

---

## 13. 将预测不确定性纳入排序与 Sizing

同样预测值不代表同样可靠。

不确定性可来自：

- Quantile width；
- Model ensemble variance；
- Seed variance；
- Rolling OOF residual scale；
- Regime uncertainty；
- Asset-specific historical error；
- 数据缺失与流动性质量。

构造稳健 edge：

\[
edge_i
=
\operatorname{sign}(\hat\mu_i)
\left(
|\hat\mu_i|-\kappa u_i
\right)_+
\]

最终 sizing：

\[
w_i
\propto
\frac{edge_i}
{\sigma_i^\gamma}
\times liquidity_i
\times executability_i
\]

其中 \(u_i\) 为预测不确定性。

---

## 14. 推荐评估体系

### 14.1 预测层

- Raw RankIC；
- Residual RankIC；
- Partial RankIC；
- Pearson IC；
- Weighted RankIC；
- Top/Bottom 5%、10%、20% spread；
- Tail recall；
- Decile monotonicity；
- Calibration slope；
- \(\sigma_{\hat y}/\sigma_y\)；
- Factor exposure。

### 14.2 组合层

- Ex-top-1 PnL；
- Ex-top-5 PnL；
- Top-1/Top-5 contribution concentration；
- Single-name risk contribution；
- Beta/sector/liquidity exposure；
- Turnover；
- Signal-flip loss；
- Maker/Taker 分层 PnL；
- Cost-adjusted Sharpe；
- Worst 4h / Worst day；
- Expected Shortfall。

### 14.3 稳定性

- 年度；
- 月度；
- High/Low volatility；
- Trend/Reversal；
- High/Low funding dispersion；
- High/Low liquidity；
- BTC crash/rally；
- 新币/老币；
- 各流动性分桶。

---

## 15. 实施优先级

### P0：确认幅度问题的真实形态

立即完成：

1. 明确 0.003 是预测标准差比例、校准 beta，还是实际 bps；
2. 分桶校准；
3. 尾部校准；
4. Linear 与 isotonic 比较；
5. 检查 sigma gate 是否有效；
6. 记录各 loss 梯度范数与余弦；
7. 比较 raw 模型事后中性化与专门 residual 模型。

---

### P1：最高 ROI 改造

1. 保留当前 Conformer 主干；
2. 拆分 raw rank、residual rank、distribution、tail 四个 head；
3. 使用风险标准化标签；
4. 增加尾部分位数；
5. 使用 OOF calibration；
6. 因子融合改为 OOF residual stacking；
7. King 与慢因子分 sleeve；
8. 使用 volatility、liquidity、executability sizing。

---

### P2：结构优化

1. Trend / Fluctuation / Shock 多路径；
2. 稀疏 cross-asset attention；
3. 1h/2h/4h/8h 多 horizon；
4. 小型 regime gate；
5. 受限 gating 输出 head；
6. Turnover-aware portfolio loss。

---

### P3：前沿 Challenger

- VQ 离散市场结构；
- Structure-conditioned MoE；
- Future-aligned contrastive representation；
- Uncertainty-aware dynamic routing；
- End-to-end differentiable portfolio construction。

这些方向适合作为 challenger，不宜在简单结构尚未验证前直接替换生产系统。

---

## 16. 最终推荐架构

整体重构为：

\[
\boxed{
\text{Raw factor component}
+
\text{DL residual component}
+
\text{Tail distribution}
+
\text{Uncertainty}
}
\]

模型负责：

- 谁会跑赢；
- 为什么跑赢；
- 可能跑赢多少；
- 这个判断有多可靠。

组合层负责：

- 风险标准化；
- 波动率与流动性缩放；
- 因子中性；
- 换手与执行成本；
- 动态 gross 与风险预算。

融合层只接受严格 OOF 的增量证据。

---

## 17. 最值得优先验证的两个实验

### 实验一：Raw 模型事后中性化

训练 raw return 模型，然后将其 OOF 预测做横截面因子中性化，比较：

\[
RankIC(\hat Y_{\text{raw-neutralized}},YR)
\]

是否达到或超过 0.048。

若成立，应停止将 residual label 作为唯一 king 目标，转向 raw + residual 双头。

### 实验二：尾部分布拆头

保留当前排序头，将幅度与尾部独立建模：

- Distribution head；
- Tail probability head；
- Tail conditional magnitude head；
- OOF monotonic calibration。

如果 tail spread、极端收益 recall 和 ex-top-1 PnL 明显改善，而 RankIC 不下降，即说明当前瓶颈确实是输出目标和幅度建模，而非主干表示能力。
