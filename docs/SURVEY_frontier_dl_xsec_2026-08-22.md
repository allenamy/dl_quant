# SURVEY — 截面收益预测 DL 前沿机制调研(2023–2026)

> **创建:** 2026-08-22 | **Session:** frontier-survey 子代理(team-lead 指派) | **状态:** 调研完成, 待主线采纳 | **作废条件:** 任一建议臂进入预注册并产生实测 RESULT 后, 对应小节以 RESULT 为准; 外部文献部分 2027 年后需重扫。

## 0. 三句白话总结

1. **外面没有银弹**: 2023–2026 所有严肃的第三方基准(FinTSB / TabReD / QuantBench / TSFM 金融复核)一致复现了我们内部的核心发现 —— 在弱信号截面任务上, **LightGBM 级别的树模型 + 好特征 ≥ 绝大多数新架构**, 时序基础模型零样本迁移到收益预测基本无效。我们不落后于前沿, 我们的"弹药>模型类"结论就是前沿。
2. **真正有机制故事、且没被我们内部证伪的增量方向只有一小撮**: ① 训练目标与 rank-IC 对齐(可微秩损失, 且双端加权直接对症我们实测的 #26 多头尾 rank 缺陷); ② 多 horizon 辅助头(内部 STATE §0 本就列为存活杠杆, 外部证据中等); ③ 市场状态引导的特征门控/市场 token(MASTER, AAAI 2024); ④ 逐锚 in-context 表格回归(TabPFN v2, 天生按锚自适应 regime); ⑤ 月度重训之间的元学习增量适配(DoubleAdapt, KDD 2023)。
3. **加密专属文献反而是负面证据仓库**: 5 分钟级微结构信号在零售费率下净 Sharpe 深负(Frontiers 2026 实测), LOB 文献自己承认"输入质量>再堆一层"(arXiv 2506.05764), carry 拥挤后 2025 年转负 —— 全部与我们内部"出口在执行侧/新息源, 不在 4h 收益模型加深"的结论同向。

---

## 方法与证据分级

- 检索范围: arXiv / AAAI / KDD / ICLR / Nature / SSRN / 从业者博客, 2023-01 至 2026-08。所有断言带来源 URL。
- **证据分级**(全篇标注): **[A]** = 实盘或大样本截面金融 OOS + 成本; **[B]** = 同行评审的截面金融回测(多为 A 股 CSI300/800 日频, 无成本或弱成本); **[C]** = 仅通用基准(ETT/M4/天气)或单资产玩具回测。**[B] 以下不足以单独立臂, 只能作为"值得花一次预算去证伪"的理由。**
- 对照原则: 每轴先对内部 REFUTED/DNR 清单(多种子集成 / 训后技巧 / SSL 微调 / FiLM 择时 / router / 因子交互列 / 语法穷举特征)检查, 凡撞上的直接给跳过理由, 不复述提案。
- 内部锚点(2026-08-22 STATE.md): 宽书 400 名已实盘 1.5×; 目标 rank-IC≥0.07 + 费后 Sharpe≥5; IC 杠杆在模型侧, Sharpe 杠杆在宽度; **存活杠杆清单里已有"多 horizon AUX"与"#26 多头尾反信息"**; 09-01 重训改为对齐窗口简单收益。本调研的建议臂全部瞄准这个重训窗口。

---

## 轴 1 — 截面归纳偏置: 秩损失 / 跨名注意力 / 市场上下文 token

### 1a. 秩损失(learning-to-rank, 让训练目标=评价指标)

**现状与机制。** 主流截面模型仍用逐点回归损失(MSE/Huber), 而评价用 rank-IC —— 目标失配在弱信号下代价最大, 因为回归损失把大部分梯度花在拟合不可预测的幅度上, 排序信息只占残差的一小部分。2024–2026 的修复路线三条:

1. **Lambda 型秩 IC 直接优化**: [LambdaRankIC (arXiv 2605.00501, 2026-05)](https://arxiv.org/abs/2605.00501) 从成对秩交换推出闭式 lambda 梯度, 做成 **XGBoost 自定义目标函数**, 声称在低信噪比、厚尾噪声的模拟下优势最大, 真实数据 OOS 的 rank-IC/ICIR/Sharpe 全面最优(摘要未给具体幅度)。**[B]** 关键卖点: 它是树模型目标函数 —— 可以**零架构改动**直接插进我们的宽书 LGBM zoo。
2. **可微排序作辅助损失**: 数学基础是 [Fast Differentiable Sorting and Ranking (ICML 2020, arXiv 2002.08871)](https://arxiv.org/abs/2002.08871)(把排序做成对 permutahedron 的投影, 从而 Spearman 相关可以直接当损失反传; 白话: "软排序"= 给排序一个可导的近似)。端到端应用: [DSPO 直接排序组合构建](https://www.researchgate.net/publication/380907518_DSPO_An_End-to-End_Framework_for_Direct_Sorted_Portfolio_Construction) 报 NYSE 2023-24 RankIC 10.12%。**[B-]**
3. **双端加权 listwise**: [长短仓专用 listwise 损失 (arXiv 2104.12484)](https://arxiv.org/abs/2104.12484) —— 把损失权重集中在秩列表的**头尾两端**(我们真正交易的部分), 中段松绑。**[B]** 另有系统性横评 [On Evaluating Loss Functions for Stock Ranking (arXiv 2510.14156, CIKM 2025)](https://arxiv.org/abs/2510.14156)(S&P500 + Transformer, 逐点/成对/listwise 全比, 结论在正文——存在这样一份第三方横评本身就是"该轴值得做消融"的证据)与经典 [Poh–Zohren 截面动量 LTR (arXiv 2012.07149)](https://arxiv.org/pdf/2012.07149)、[货币版+自注意力 (arXiv 2105.10019)](https://arxiv.org/pdf/2105.10019)。**[B]**

**与内部约束对照。** 不撞任何 REFUTED 项。**直接对症内部 #26 "多头尾反信息 = 唯一有实测症状的 rank 缺陷"**(STATE §0): 双端加权 listwise 的机制故事恰好是"把训练容量从中段挪到头尾"。风险: 秩损失只动排序不动幅度 → 与我们"IC 是 alpha, β 是量纲"纪律天然相容; 但须防 σŷ 塌缩(秩损失对尺度不敏感, σŷ/σy≥0.02 守卫必须在)。样本算术: n=300–400/锚的 listwise 损失每锚 O(n log n), 免费。

**建议臂(1)**: 宽书 LGBM zoo 腿 → 换 LambdaRankIC 式秩 IC 自定义目标(先) + king 加 λ 加权双端 listwise 辅助损失(后, champion_run.sh 恰一变量) → 门 = S1 ΔrankIC≥+0.003 双种子同号 + Q4 不降 + σŷ 守卫 + S2 净额 G 族。

### 1b. 跨名注意力 / 图结构

**现状。** 我们的 top xattn(+0.004)已经是该家族的落地形态。外部增量主张是**显式关系先验**: 行业/共动图偏置注意力([GRU-PFG, arXiv 2411.18997](https://arxiv.org/pdf/2411.18997); [高阶图注意力, arXiv 2306.15526](https://arxiv.org/pdf/2306.15526)); 加密版 [Learning from Neighbors: Multi-relational Attention for Cryptocurrency Return Prediction (ESWA 2026)](https://www.sciencedirect.com/science/article/abs/pii/S0957417426023845) 在 150 个 Binance 币 2020–2025 上报持续排序改善。**[B-]**(ESWA 层级, 未见成本)。[QuantBench (arXiv 2504.18600)](https://arxiv.org/abs/2504.18600) 把"关系数据建模"列为三大开放方向之一。**[B]**

**对照。** 不撞 REFUTED; 但内部证据链偏冷: 学习式 xattn 已在役, 显式图的增量 = "先验 vs 学习"之差, 在 10k 锚样本下先验可能有价值(样本不足以学出全部 400×400 结构)。加密币的"行业"= L1/L2/DeFi/meme 簇, 内部风险层已有簇结构(cluster breaker)。低成本形态: 给 xattn 加**簇 ID 嵌入或注意力偏置**, 恰一变量。

**建议臂(6, 备选)**: 因子面板已有的簇标签 → xattn 注意力分数加簇内偏置项(或簇 ID 嵌入) → 门 = S1 ΔrankIC≥+0.003, 失败即弃(一次实验预算)。

### 1c. 市场上下文 token / 市场引导门控

**现状与机制。** [MASTER (AAAI 2024, arXiv 2312.15235)](https://arxiv.org/abs/2312.15235)([代码](https://github.com/SJTU-DMTai/MASTER)): 用市场向量(指数收益 + 多窗口收益/成交额的均值方差)经一个 gating 网络**逐特征重加权**输入, 再做"瞬时+跨时"的股内/股间交替注意力; CSI300/800 上超既有 SOTA。**[B]** 机制故事清晰: **特征有效性是市场状态的函数**(如反转因子在挤压周失效——我们 leak_taught_momentum_crutch 记忆里实测过同构现象), 门控让模型按状态选特征, 而不是让一套静态权重跨 regime 摊平。

**对照。** 与 REFUTED 的"naive FiLM 择时"不同: 那是拿 regime 信号去**缩放书**(择时), MASTER 是拿市场状态去**选特征**(条件化), 后者与我们**已在役且有效**的 FiLM regime conditioning 同族。所以增量预期要打折: 我们已有 FiLM, MASTER 的边际是 (a) 市场统计向量作为显式条件输入(我们的 FiLM 条件是什么内部已知, 若未含市场横截面统计则这是真增量) (b) 门控作用在**特征选择**而非仅仿射调制。

**建议臂(3)**: 市场横截面统计向量(等权收益/分散度/成交额分位, 多窗口)→ 作为 FiLM 条件的扩展输入或 xattn 的市场 token → 门 = S1 ΔrankIC≥+0.003 且 Q4 不降(重点看挤压周子样本)。

---

## 轴 2 — 噪声金融序列的编码器(PatchTST / iTransformer / TimesNet / Mamba vs 膨胀卷积)

**现状。** 通用基准上的迭代很热闹: [PatchTST (ICLR 2023)](https://arxiv.org/abs/2211.14730)(把序列切块当 token, 降噪+省算力)、[iTransformer (ICLR 2024)](https://arxiv.org/abs/2310.06625)(把"变量"当 token, 注意力学变量间关系)、[TimesNet](https://arxiv.org/abs/2210.02186)/[FEDformer](https://arxiv.org/abs/2201.12740)(频域)、[ModernTCN (ICLR 2024)](https://openreview.net/forum?id=vpJMJerXHU)(大核卷积, 我们单资产双源 v2 已用过)、Mamba 族([MambaStock](https://arxiv.org/abs/2402.18959)、[FinMamba, arXiv 2502.06707](https://arxiv.org/html/2502.06707v1)、[StockMamba](https://doi.org/10.3390/math14111859) 报 CSI300/800 IC/RankIC 全面小胜且压力期衰减更小)。**但金融截面上的独立横评不支持"编码器类是杠杆"**:

- [FinTSB (arXiv 2502.18834, ICAIF 2025 Workshop 最佳论文)](https://arxiv.org/abs/2502.18834): 统一协议下 **LightGBM IC 0.068 / RankIC 0.088 居首**, 各 DL 家族无一统治所有指标, "预测误差与投资收益几乎不相关", Transformer 族表现分裂。**[B]**
- [DLinear 质疑线 (arXiv 2205.13504)](https://arxiv.org/abs/2205.13504): 线性基线长期打平复杂 Transformer。**[C→B]**
- [LSTM vs GBDT 日内期货 (arXiv 2605.17724)](https://arxiv.org/pdf/2605.17724): 序列结构存在但 GBDT 依旧可比。**[B-]**
- 内部: 方向一终判"树/king/深表格三方等价 ±0.002"; 时序深度已吃满(126h 饱和); 5m 战役 solo↑→ρ↑ catch-22。

**结论。** Mamba/Patch 系的金融证据全部是 **[B-]/[C]**(A 股日频论文工厂密度高, 无成本, 无 Q4 口径), 没有任何一篇给出"在 R²<1% 的截面残差目标上编码器类带来净增量"的证据; 而两份严肃基准(FinTSB、内部三方等价)都说没有。编码器搜索的期望值为负。

**跳过理由(一行)**: 内部三方等价定理 + FinTSB/LGBM 居首 + 时序深度已吃满 ⇒ 编码器类不是杠杆, 任何新架构臂在同弹药下预期 ±0.002 内, 不立臂。

---

## 轴 3 — 预训练 / 时序基础模型(TSFM)

**现状。** Chronos([arXiv 2403.07815](https://arxiv.org/abs/2403.07815))、TimesFM([2310.10688](https://arxiv.org/abs/2310.10688))、Moirai([2402.02592](https://arxiv.org/abs/2402.02592))、MOMENT([2402.03885](https://arxiv.org/abs/2402.03885))等在通用预测上成立, 但**金融收益上的第三方复核一致偏负**:

- [Pretrained TSFM for Financial Return Forecasting (arXiv 2606.27100, 2026-06)](https://arxiv.org/abs/2606.27100): 五只美股, TSFM 虽在任务层面赢神经基线, 但**对随机游走的增益"小而稀疏"**, 统计显著仅 2 例。**[B-]**
- [Re(Visiting) TSFM in Finance (arXiv 2511.18578)](https://arxiv.org/html/2511.18578v1): 大样本日频超额收益, **零样本与微调双双失败, 只有"在金融数据上从零预训练"有实质改善**。**[B]** —— 而"从零金融预训练+浅头=监督冠军"正是我们 2026-08-10 GPU 夜战役的构造性天花板证明, 内部已做过且封卷。
- FinTSB 里 Chronos 变体 IC 0.009–0.017 vs LGBM 0.068。**[B]**
- **[Kronos (arXiv 2508.02739, AAAI 2026)](https://arxiv.org/abs/2508.02739)**([HF 论文页](https://huggingface.co/papers/2508.02739)/[模型权重](https://huggingface.co/NeoQuasar/Kronos-base)): 唯一值得单列的例外 —— 专为 K 线设计的分层离散 tokenizer + 自回归 Transformer, **12B 根 K 线、45 家交易所**(含加密)预训练, 24.7M/102.3M/499.2M 三档; 零样本价格预测 RankIC 比最强 TSFM 高 93%、比最好非预训练基线高 87%, A 股 top-k 回测 AER/IR 最优。**[B]**(注意: 93% 是相对近零基线的相对数; 无加密截面净额证据; 无成本)。

**对照。** 内部 DNR: "SSL 微调 ≈0(110 名宇宙)" + 天花板证明(冻结表征+浅头=全监督冠军 ⇒ 表征不是瓶颈, 4h 锚样本量才是)。Kronos 与内部 SSL 的区别仅在预训练语料大三个数量级、跨市场; 但 Re(Visiting) 的结论(微调也失败, 只有从零金融预训练有用)与内部天花板证明双重压低其先验。**唯一不违反 DNR 的廉价形态**: 把 Kronos **冻结嵌入当特征列**(不是微调、不是换 backbone), 过 LGBM 前置门 —— 一次推理成本, 失败即弃。

**跳过理由(一行)**: 微调/换 backbone 撞内部 DNR 且外部复核(2511.18578/2606.27100)同判无效; 仅留"Kronos 冻结嵌入 → LGBM 特征门 ΔP≥+0.005"一个廉价证伪臂, 优先级末位。

---

## 轴 4 — 表格 DL 与树-DL 混合

**现状。** 三份关键证据:

- **[TabReD (arXiv 2406.19380, ICLR 2025)](https://arxiv.org/abs/2406.19380)**: 8 个工业级带时间漂移的表格集上, **按时间切分后模型排名大洗牌, GBDT + 朴素 MLP 赢, 学术基准上的花哨 DL 失效**。这是对我们场景(时间漂移 + 重特征工程管线)最贴脸的一份外部证据。**[B+]**
- [TabArena (arXiv 2506.16791)](https://arxiv.org/abs/2506.16791): 大预算+集成下 DL(TabM/RealMLP)追平 GBDT, "跨模型集成推进 SOTA" —— 但**集成路线撞内部"禁多种子/训后集成"硬约束**, 且它用的是随机切分(TabReD 恰好证明这会误导)。**[B]**
- **[TabPFN v2 (Nature 2025)](https://www.nature.com/articles/s41586-024-08328-1)**([代码](https://github.com/PriorLabs/TabPFN); [解析 arXiv 2502.17361](https://arxiv.org/pdf/2502.17361); [TabPFN-2.5](https://www.researchgate.net/publication/397555905_TabPFN-25_Advancing_the_State_of_the_Art_in_Tabular_Foundation_Models)): 在 1.3 亿合成任务上预训练的 in-context 学习器(白话: 把训练集当提示词喂进去, **一次前向直接出预测, 不做梯度训练**), 小样本(≤1 万行×500 特征)表格任务 SOTA。金融截面直接证据尚缺(仅[保险定价](https://arxiv.org/pdf/2605.22892)等弱信号场景试水)。**通用[A], 金融[C]**。

**机制故事(为什么值得一臂)。** 我们的截面问题逐锚看恰是 TabPFN 的甜点区: 每锚 n≈300–400 行、90–300 列、信号极弱。把"过去 K 个锚的 (特征,标签) 对 + 当前锚特征"作为 context 喂入 = **每锚免训练重拟合** ⇒ regime 自适应是构造性的(context 滑动即适应), 不经任何重训练周期 —— 这正面回应非平稳性约束, 且与 router/择时(REFUTED)机制完全不同(没有离散状态切换, 只有连续的样本近因性)。风险: 合成先验 vs 加密收益分布的错配; 逐锚推理 × 10k 锚 × walk-forward 的算力(TabPFN 单任务秒级, 可控)。

**树-DL 混合。** 内部已收口(hybrid forest 录取 = 战役唯一双种子幸存者; 分工定理: raw→树, resid→king), 外部蒸馏/混合文献([GRANDE, ICLR 2024](https://arxiv.org/abs/2309.17130) 等)没有超出内部已验证形态的机制。特征条件化序列模型(我们 A2 臂形态)外部对应物即 MASTER 的门控(见轴 1c)。

**建议臂(4)**: 因子列(与 LGBM 同弹药)→ TabPFN v2 逐锚 in-context 截面回归(context = 尾随 K 锚, K∈{60,120,240} 三点)→ 门 = 与同弹药 LGBM 配对比较 ΔrankIC≥0 且 Q4 更稳才算过(它的卖点是稳不是高), 再过 S1/S2。

---

## 轴 5 — 非平稳下的训练(在线/增量/元学习/加权/IRM)

**现状。**

- **增量+元学习**: [DoubleAdapt (KDD 2023, arXiv 2306.09862)](https://arxiv.org/abs/2306.09862)([代码](https://github.com/SJTU-DMTai/DoubleAdapt), [已并入 qlib](https://github.com/microsoft/qlib/pull/1560)): 数据适配器(把增量数据变换到"局部平稳分布")+ 模型适配器(元学习的初始化/学习率), 20 交易日一个增量任务, A 股上超滚动重训基线。**[B]** 后续: [动态适配版 (arXiv 2401.03865)](https://arxiv.org/pdf/2401.03865)。
- **漂移预测**: [DDG-DA (AAAI 2022, arXiv 2201.04038)](https://arxiv.org/abs/2201.04038) 预测数据分布的漂移方向再重加权训练样本。**[B]**
- **重训节奏**: 多篇 walk-forward 研究支持"更频繁重训更好但边际递减"(如 3 月滚动 > 6/12 月, 见 [QuantBench](https://arxiv.org/abs/2504.18600) 与 [Alpha decay walk-forward 实证](https://arxiv.org/html/2512.12924v1)); [The Expected Returns on ML Strategies (AFA)](https://afajof.org/management/viewp.php?n=75544) 证实历史数据陈旧性是 ML 策略衰减主因之一。**[B]** QuantBench 把"持续学习应对分布漂移"列为三大方向之首。
- **Numerai 实践**(与我们同为弱信号截面): era 批训练(=我们的逐锚批)、rank 分箱目标、特征中性化; [Numerai 上的深度增量学习 (arXiv 2303.07925)](https://arxiv.org/pdf/2303.07925)。**[B-, 从业者]**([文档](https://docs.numer.ai/numerai-tournament/scoring/feature-neutral-correlation))
- **IRM/域泛化**: [The Risks of IRM (ICLR 2021, arXiv 2010.05761)](https://arxiv.org/abs/2010.05761) 等证明 IRM 在非线性设定下灾难性失效, DomainBed 上常输 ERM; 金融正面证据为零。**[B, 负面]**

**对照。** 内部已消费一部分: "生产折新鲜度已训待装"(=近因加权的一种)、月度重训 RUNBOOK 已立、rolling_retrain 设计文档 08-14 在案; router/regime 切换 REFUTED(DoubleAdapt 不是 router —— 它不做离散状态判别, 是连续的参数适配, 机制不同)。风险: 元学习二阶优化在 10k 锚上易过拟合验证窗; 必须以"简单近因加权重训"为对照臂, 元学习必须赢过它才算数(外部论文普遍缺这个对照)。

**建议臂(5)**: 09-01 月度重训框架内 → 三臂阶梯: (a) 样本近因半衰期加权(LGBM+DL 都便宜) (b) 重训间隙 DoubleAdapt 式轻量适配(只动末两层+元学习 LR) (c) 对照=现行冷重训 → 门 = 最近两折 ΔrankIC≥+0.003 且 Q4 不降且 (b) 必须赢 (a)。
**跳过(IRM 一行)**: IRM/域泛化在自家基准上都跑输 ERM 且无金融正面证据, 不立臂。

---

## 轴 6 — 损失/目标工程(分布头 / 多任务 / 标签工程 / 弃权)

- **分布头**: 内部已双向定界(pinball 头在 Engine A 有效; QIM 在天花板测试 −0.002)。外部无超出此的截面证据。不再加码。
- **秩+回归多任务**: A 股文献常用 IC 损失+MSE 组合([风险感知多任务排序](https://www.sciencedirect.com/science/article/abs/pii/S0957417426013758); [动量整合多任务](https://arxiv.org/html/2509.10461)), 梯度冲突是已知副作用。**[B-]** 已并入轴 1 建议臂(1)的 λ 加权形态, 不单立。
- **多 horizon 多任务(AUX 头)**: 内部 STATE §0 明列为存活杠杆(与 y24 换标签 DNR 不同 —— 主标签保持 4h, 8h/24h 只做辅助头共享编码器, 起正则作用)。外部机制依据: 多任务作为弱信号正则的通用证据充分, 金融专属为 **[B-]**。**这是内部授权+外部佐证都齐的少数臂之一。**
- **标签工程**: winsorization/±σ clip 内部有地雷在案(d1gate clip 口径); Numerai 的 rank-gaussian 分箱标签是从业者标准做法, 与我们残差标签兼容; [FinTSB](https://arxiv.org/abs/2502.18834) 的"预测误差⊥收益"再次支持秩化标签方向。09-01 重训改简单收益时可顺带测 rank-gaussian 标签变换(恰一变量)。
- **弃权/learning-to-defer**: [When Alpha Breaks (arXiv 2603.13252, 2026-03)](https://arxiv.org/abs/2603.13252) 用 DEUP 认知不确定性做两层门(策略级 trust gate AUROC 0.72 + 仓位级尾帽), 且发现连续反比例 sizing 变差、只有尾部截断有用。**[B]** —— 但其策略级门 = 择时轴(内部五形态全关), 仓位级尾帽 ≈ 我们已在役的 σŷ 守卫+standby 条款; 其"不确定性与 |score| 相关 0.6"恰说明它大半是 σŷ 的回声。
- **"复杂度美德"争议(警示条)**: [Kelly-Malamud-Zhou (JF 2024)](https://www.nber.org/papers/w30217) 声称过参数化提升收益预测, [Nagel 2025 反驳](https://papers.ssrn.com/sol3/papers.cfm?abstract_id=5335012): 所谓增益 = 波动率择时动量的机械伪影 + 两个人为实现选择。**[A 级学术辩论]** ⇒ 任何"加宽加深就有免费午餐"的提案先读 Nagel。

**建议臂(2)**: 冠军编码器 → 加 8h/24h 辅助头(主标签仍 4h 残差, 辅助权重 λ∈{0.1,0.3} 两点)→ 门 = 主头 S1 ΔrankIC≥+0.003 双种子 + Q4 不降(y24 单标签 DNR 不受触碰)。
**跳过(弃权一行)**: 策略级弃权=已关的择时轴, 仓位级=在役 σŷ 守卫已覆盖, 不立臂。

---

## 轴 7 — 加密专属(2024–2026)

- **微结构/LOB**: [Frontiers in Blockchain 2026 微结构 alpha 实测](https://www.frontiersin.org/journals/blockchain/articles/10.3389/fbloc.2026.1811716/full): Binance 现货+永续 6 币分钟级、purged walk-forward —— **LightGBM 在 5m 视界比随机游走差(ΔR² −10.9%, DM −6.8), 全部净 Sharpe 深负**(零售费率), 信号真实但付不起成本; 跨资产迁移呈块对角(同币跨场所迁移好, 跨币差)。**[B, 负面]** [加密 LOB: 输入质量>再堆一层 (arXiv 2506.05764)](https://arxiv.org/pdf/2506.05764) 与 [Deep LOB forecasting 微结构指南 (QF 2025)](https://www.tandfonline.com/doi/full/10.1080/14697688.2025.2522911): 简单模型+好输入可打平深网络。**[B]** ⇒ 全部与内部"书族退役五形态/出口在执行侧"同向; 我们的 LOB 微结构腿设计(docs/DESIGN_lob_microstructure_leg_2026-08-19.md)应继续瞄准**执行层**(maker 成交率/逆选择), 不是 4h 收益标签。
- **截面 ML**: [Machine learning and the cross-section of cryptocurrency returns (IRFA 2024)](https://www.sciencedirect.com/science/article/abs/pii/S1057521924001765): 日频截面 OOS 组合月超额 ~0.6–0.7%。**[B]** [JFQA 加密趋势因子](https://www.cambridge.org/core/journals/journal-of-financial-and-quantitative-analysis/article/trend-factor-for-the-cross-section-of-cryptocurrency-returns/4C1509ACBA33D5DCAF0AC24379148178)。这些确认加密截面可预测, 但因子全是我们 zoo 已有的商品化价量族(内部宽度门第一轮零录取的那批)。
- **carry/funding**: [Cryptocurrency as an Investable Asset Class (arXiv 2510.14435)](https://arxiv.org/abs/2510.14435)(检索摘要引述: carry 全样本 Sharpe 6.45, 2024 降至 4.06, **2025 转负** —— 拥挤度周期与内部"在役 funding 腿=纯 carry / 宽 funding 腿=2025-26 regime 引擎"的两符号发现互为印证); [永续资金费率的机制设计 (arXiv 2506.08573)](https://arxiv.org/pdf/2506.08573)与[资金费率市场两层结构 (Mathematics 2026)](https://www.mdpi.com/2227-7390/14/2/346)提供机制理解, 非 alpha。**[B]** 跨所 funding 内部已 DNR。
- **清算/挤压**: 未找到任何带可信 OOS 的清算级联**预测**论文(现有全是事后描述或 DeFi 场景)。内部的 squeeze 预注册 + 错题集"P1 左尾全是挤压日"仍是该方向的最好证据 —— 这是**内部领先外部**的一块, 数据护城河(自建清算距离面板)值钱但属于新息源战役, 不属本调研立臂范围。
- **LLM/agent 交易论文**(CryptoTrade 类): 全部 **[C]**, 不值一臂。

**跳过理由(一行)**: 外部加密文献要么复述我们已录取的因子(funding/carry), 要么在 5m 视界上净额深负印证我们的执行侧结论 ⇒ 无新机制可立臂; 清算面板归新息源战役。

---

## Top-5 建议臂排名(机制可信度 × 证据质量 × 样本算术适配)

| # | 臂 | 一行规格 (input→mechanism→gate) | 依据强度 | 成本 |
|---|---|---|---|---|
| 1 | **可微秩损失/秩 IC 目标** | 同弹药 → LGBM 换 LambdaRankIC 自定义目标 + king 加双端加权 listwise 辅助损失(λ 一点) → S1 ΔrankIC≥+0.003 双种子 + Q4 + σŷ 守卫 + S2 净额 | 机制★★★(对症 #26 实测缺陷; 目标=指标) 证据[B] | 极低(LGBM 目标函数即插) |
| 2 | **多 horizon AUX 头** | 5m 序列+因子列 → 冠军编码器加 8h/24h 辅助头(主标签 4h 残差不动, λ∈{0.1,0.3}) → 主头 S1+Q4, 不触 y24 DNR | 机制★★★(弱信号正则; 内部已列存活杠杆) 证据[B-]+内部授权 | 低(恰一变量) |
| 3 | **市场引导门控/市场 token** | 市场横截面统计向量(等权收益/分散度/量, 多窗口) → FiLM 条件扩展或 xattn 市场 token(MASTER 式特征门控, 非择时) → S1+Q4(挤压周子样本必报) | 机制★★(特征有效性随市场状态) 证据[B](AAAI 2024) | 低 |
| 4 | **TabPFN v2 逐锚 in-context 截面回归** | 因子列+尾随 K 锚 context → 免训练逐锚重拟合(构造性 regime 自适应) → 与同弹药 LGBM 配对: ΔrankIC≥0 且 Q4 更稳, 再 S1/S2 | 机制★★(逐锚自适应≠router) 证据: 通用[A]/金融[C] | 低(零训练, 推理可控) |
| 5 | **重训间隙元学习增量适配** | 09-01 重训框架 → 阶梯: 近因半衰期加权(a) / DoubleAdapt 式末层适配(b) / 冷重训对照(c) → (b) 必须赢 (a) 且最近两折 ΔrankIC≥+0.003+Q4 | 机制★★(连续适配≠regime 切换) 证据[B](KDD'23) | 中(嵌入既定重训工程) |

**备选 6**: 簇偏置 xattn(一次预算, 失败即弃)。**末位 7**: Kronos 冻结嵌入 → LGBM 特征门 ΔP≥+0.005(一次推理成本; 内部天花板证明压低先验, 仅作廉价证伪)。

**执行纪律提醒**(全部臂适用): champion_run.sh 恰一变量; 预注册 SHA 先于数字; 双口径+净费后+Q4 必报; 排序≠净额(S1 过只是必要条件); 判官脚本当日入库。

---

## 明确不做清单(带外部印证)

| 方向 | 内部受据 | 外部印证 |
|---|---|---|
| 新编码器(Patch/iTransformer/Mamba/频域) | 三方等价定理±0.002; 深度已吃满 | FinTSB: LGBM 居首; TabReD: 时间切分下花哨 DL 失效 |
| TSFM 零样本/微调 | SSL 微调≈0 DNR; 天花板构造证明 | 2511.18578/2606.27100: 零样本+微调双败 |
| 多种子/跨模型集成 | 用户硬约束 | TabArena 的集成增益路线因此不可用 |
| IRM/域泛化 | — | 自家基准输 ERM(2010.05761) |
| 策略级弃权/不确定性择时 | 择时轴五形态全关 | When Alpha Breaks 的门=同一轴; 其仓位级≈在役 σŷ 守卫 |
| 5m 微结构进 4h 书 | 书族退役; 机会毛额≠可捕获 | Frontiers 2026: 净 Sharpe 深负 |
| 过参数化"免费午餐" | 复杂度预算纪律 | Nagel 2025: 伪影 |

## 主要来源索引

轴1: [2605.00501](https://arxiv.org/abs/2605.00501) · [2510.14156](https://arxiv.org/abs/2510.14156) · [2606.08930](https://arxiv.org/html/2606.08930v1)(RankGLU 头改造 CSI300 IC +11.2%, CSI800 不显著) · [2104.12484](https://arxiv.org/abs/2104.12484) · [2002.08871](https://arxiv.org/abs/2002.08871) · [2012.07149](https://arxiv.org/pdf/2012.07149) · [2105.10019](https://arxiv.org/pdf/2105.10019) · [MASTER](https://arxiv.org/abs/2312.15235) · [ESWA 加密 GNN](https://www.sciencedirect.com/science/article/abs/pii/S0957417426023845)
轴2: [FinTSB 2502.18834](https://arxiv.org/abs/2502.18834) · [2205.13504](https://arxiv.org/abs/2205.13504) · [2502.06707](https://arxiv.org/html/2502.06707v1) · [2605.17724](https://arxiv.org/pdf/2605.17724) · [QuantBench 2504.18600](https://arxiv.org/abs/2504.18600)
轴3: [Kronos 2508.02739](https://arxiv.org/abs/2508.02739) · [2511.18578](https://arxiv.org/html/2511.18578v1) · [2606.27100](https://arxiv.org/abs/2606.27100) · [Chronos](https://arxiv.org/abs/2403.07815) · [TimesFM](https://arxiv.org/abs/2310.10688) · [Moirai](https://arxiv.org/abs/2402.02592)
轴4: [TabPFN v2 Nature](https://www.nature.com/articles/s41586-024-08328-1) · [TabReD 2406.19380](https://arxiv.org/abs/2406.19380) · [TabArena 2506.16791](https://arxiv.org/abs/2506.16791) · [2502.17361](https://arxiv.org/pdf/2502.17361) · [GRANDE 2309.17130](https://arxiv.org/abs/2309.17130)
轴5: [DoubleAdapt 2306.09862](https://arxiv.org/abs/2306.09862) · [DDG-DA 2201.04038](https://arxiv.org/abs/2201.04038) · [2303.07925](https://arxiv.org/pdf/2303.07925) · [IRM Risks 2010.05761](https://arxiv.org/abs/2010.05761) · [AFA ML 策略预期收益](https://afajof.org/management/viewp.php?n=75544) · [Numerai FNC](https://docs.numer.ai/numerai-tournament/scoring/feature-neutral-correlation)
轴6: [When Alpha Breaks 2603.13252](https://arxiv.org/abs/2603.13252) · [KMZ JF 2024](https://www.nber.org/papers/w30217) · [Nagel 2025](https://papers.ssrn.com/sol3/papers.cfm?abstract_id=5335012)
轴7: [Frontiers 微结构 2026](https://www.frontiersin.org/journals/blockchain/articles/10.3389/fbloc.2026.1811716/full) · [2506.05764](https://arxiv.org/pdf/2506.05764) · [QF LOB 指南](https://www.tandfonline.com/doi/full/10.1080/14697688.2025.2522911) · [IRFA 加密截面 ML](https://www.sciencedirect.com/science/article/abs/pii/S1057521924001765) · [2510.14435](https://arxiv.org/abs/2510.14435) · [2506.08573](https://arxiv.org/pdf/2506.08573)
