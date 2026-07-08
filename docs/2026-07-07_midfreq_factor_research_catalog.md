# 中频 crypto 横截面因子调研目录（业界+学界）

> **创建:** 2026-07-07 | **分支:** multi-asset-v2 | **状态:** reference | 用于 multi-asset v2 因子设计。
> web 调研，带来源。几个 PDF 付费墙 → 具体小数需核原文，定性结论多源交叉印证。

## 三条过滤事实（决定一切）
1. **Horizon 错配**: 几乎所有*文献记录*的 crypto 横截面溢价是**周-月**效应（动量 2wk、size/reversal/value/MAX 周、low-vol 2-3mo）。在 1h 跑它们不会加速 alpha,只加速成本。**只有三族天然活在小时尺度**: (a) funding/basis/positioning carry (8h 时钟,高自相关), (b) 累积订单流/波动状态变量, (c) 短窗相对动量。
2. **Universe 错配**: 经典 crypto 溢价(Liu-Tsyvinski-Wu C-4)排序*数千*币、**微市值/流动性驱动**。在 14 大市值 perp 上,size/流动性/MAX/idio-vol/日反转 **基本消失** —— 且**日反转在大币上翻成动量**(IRFA 2021)。
3. **成本地板**: Binance USDT-perp ≈ **2bps maker / 5bps taker** 单边。1h 再平衡下每天 ~1-5% 拖累。**持续性(低换手)是必要条件** —— 正是为什么慢衍生品因子(非快微结构)是杠杆。

## Cat 1 — 商品化横截面因子（多为周-月、大币上消失）
- **横截面动量**: 2wk +2.6%/wk(t=3.89) 稳,12/24wk 不显著; ML 说 1-day lagged return 是最强预测子。1h 上只有"大币间短窗相对动量"在 horizon 内。
- **短期反转**: 周反转 +2.77%/wk; **流动性条件: 日反转只在流动性差的币,大币显示日动量**; 盘中反转 R² 仅 0.6-1%。
- **低波动/idio-vol**: 符号随市场成熟翻转,近期 2-3mo formation 有;C-4 里 raw VOL 不显著。regime 依赖。
- **size/流动性(Amihud)**: 广样本巨大但 post-2020 衰减,**14 大币上近零 dispersion,结构上不适用**。
- **beta/BAB/MAX**: 纯 β 不定价;**MAX/lottery** low-MAX 减 high-MAX >+1.5%/wk,但小币/周时钟。
- **下行风险/偏度**: 下行风险=正溢价,偏度=负预测子;噪声大,与 MAX/idio-vol 共线。

## Cat 2 — crypto 衍生品因子（★ 主力杠杆）
- **★2.1 funding-rate carry / positioning-reversion(prime lever)**: 每 8h 排序 14 币 funding, **空高 funding(拥挤多头付费)/多低或负 funding(拥挤空头付你)**。机理: funding≈杠杆持仓/拥挤度直读,持续高=过度拥挤易 squeeze/反转。横截面天然、机械慢(8h stamp 高自相关)。证据: "funding sentiment"因子 2020-2026 **1% 显著**(SSRN 6818558); 实盘净费 **funding-only Sharpe 0.96**,与动量组合 1.27,换手 9.6%/wk,费拖 1.8pp/yr,分散化(DD −35%→−27%)(Artemis)。★差异化: **delta-neutral harvest 重度商品化+2025 转负 Sharpe;横截面 funding-as-crowding 做方向 alpha 不拥挤、2026 仍 1% 显著。** 净成本: **所有因子里最佳**(8h refresh 低换手延迟容忍,清成本地板)。**用作 8h 边界刷新、跨 1h bar carry 的慢 tilt,别每 1h 重交易。**
- **2.2 basis/期限结构**: perp basis≡funding;真期限结构需**季度合约**(calendar basis,roll yield)。basis 是最强横截面预测子(≈329%/yr vs 动量 89%/yr),edge 日>周>月。**季度期限结构真差异化但需现在没接的 dated-futures 数据。**
- **2.3 OI 动态**: ΔOI/OI、OI×价格背离、OI/vol。**学术支撑最弱**(无干净 standalone 横截面因子);价值在**交互**(ΔOI×funding, ΔOI×价格符号)。4-8h overlay,过自己 Ridge ΔP≥+0.003 门。
- **★2.4 多空持仓比(Binance top-trader vs global)**: 每币归一 fade 极值,**top-trader 减 global 背离**。机理: global/retail 反向(极值散户错)、top-trader 跟(鲸)。**folklore 商品化但干净无泄漏横截面实现真差异化**(几无干净发表证据,高研究上行)。~hourly 更新,中等持续 → **1h-4h 好 fit**。必须自验(Ridge walk-forward + shuffle-future null)。
- **2.5 liquidations**: 快、爆发、**延迟敏感 —— 正好是不想要的**;1h 已实现。**用作 state/regime GATE,不是因子。**
- **2.6 perp-spot premium**: 只有慢(funding 相关)分量净成本可交易;快反转需 maker fill。**注意: spot 动量预测 premium(R²>50%),非 premium 预测未来 spot return。**

## Cat 3 — 微结构→中频聚合（瞬时死于 1h,只有慢对象存活）
- **★3.1 累积/积分净签名订单流(per-asset 归一,多小时 lookback)**: **喂累积签名流(继承 Hurst≈0.7 长记忆),不是瞬时 OFI(2min 死)**。瞬时 OFI 同期 R²0.40 但 1-step 预测 R²0.031/DA53%/Sharpe0.12 不可交易;trade-sign 长记忆(metaorder splitting);crypto order-flow→return 周回归持续。差异化=累积窗+横截面归一+多档积分。成本敏感(需 maker)。
- **3.2 VPIN/毒性**: 预测**波动非方向**,分-1h;**用作横截面毒性 rank 的 conditioning/risk gate**(下调毒性上升的币)。
- **★3.3 RV 期限结构/半方差/签名跳(最持续族)**: HAR;半方差 RS⁻/RS⁺;签名跳 RS⁺−RS⁻。**负半方差预测未来波动强,1天-3月**。RV level=风险/sizing(便宜极持续);方向内容在**横截面签名跳/半方差 skew**(慢够 1h 但个体弱)。
- **3.4 Amihud/Kyle-λ 时均**: 慢持续特征,大币 dispersion 小;**用作组合构造的冲击成本权重(size∝1/impact),非信号**。
- **衰减图(存活到 1h)**: 瞬时 OFI→否(秒-2min); 跨资产 lagged OFI→否(1 天没); **累积签名流→是(边际,成本敏感)**; VPIN→是(conditioning); RV/HAR→是(风险); **签名跳/半方差→是**; Amihud/λ→是(冲击权重弱)。

## Cat 4 — ML/DL 因子构造（14 资产 R²<1% 成本主导 → 便宜 loss 侧+预训练 > 堆容量）
- **4.1 非线性因子挖掘(GKX/条件autoencoder/Chen-Pelger-Zhu/复杂性优势)**: NN/树 ~翻倍线性 OOS 但仍 sub-1% R²;**无套利-loss + 条件-beta 是可迁移杠杆**;autoencoder 潜因子在 14 资产薄(要数百)。
- **4.2 自监督/表示学习**: 对比 embedding 降对冲组合波动 23.8→19.1%;**契合你数据不对称(海量无标签 1s vs 弱 y_600 标签)—— 自监督预训练 Conformer stem 再 fine-tune**;VAE 防 posterior/σ 塌缩。
- **4.3 符号/遗传公式化 alpha(AlphaGen/AutoAlpha/Alpha-GPT)**: 开源重度 fork **找的公式拥挤**;差异化只在私有算子集(盘口/成交流算子)+universe;**RL reward-hack 样本内 IC**,每个必过 Ridge walk-forward+shuffle-null 再上 DL。
- **4.4 gradient boosting 组合**: 因子表上 **GBDT≥深网**;crypto 上 **OLS 常胜树&NN**(最简方法赢);**LightGBM 是 DL 必须打败的诚实基线,且常打不过 —— 永远报告它**。
- **4.5 图/关系模型**: 14 节点太少低 ROI;你的 cross-asset attention 已是软全连接图;你自己历史: 空间精修穷尽 P≈0.033,时间深度胜空间图。
- **★4.6 learning-to-rank loss(最便宜高价值)**: LambdaMART Sharpe 2.156 vs MLP-回归 0.265;**LambdaRankIC 直接优化 rank-IC=部署指标,~零加参 低过拟合**;注意 anti-pattern #15(rank-loss REPLACE 致 val→test drift,作 AUX w≤0.1 除非过 walk-forward)。
- **4.7 诚实 caveat**: 因子动物园复现危机(~60% anomaly t<1.96);ML 放大 p-hacking;**一个泄漏控制的 crypto 微结构研究: LightGBM OOS R²=−10.94%、净 Sharpe −50(spot)/−17(futures) 费后 124-204× 日换手,alpha 集中低波动/趋势 regime(+8.2% calm vs −14.3% stress)—— 外部验证你的成本地板+regime 依赖结论。**

## Cat 5 — 跨资产/网络（★薄,需补搜）
- **5.1 BTC/ETH→alt lead-lag**: **同期 beta 巨大**(ETH 0.84,avg alt ~0.70)→ **beta-projection floor ~0.045/alt 白送**;但 **lagged 600s 弱~0.02**,是模型要转的 alpha。跨币 lead-lag L/S 存活成本(Bristol JEDC 2024)但**大币上多被套利掉 —— 当开放实证问题逐资产测,别假设**。
- **5.2 横截面 dispersion**: 高 dispersion=idio regime 横截面 bet 付钱;作 conditioning/sizing 变量,便宜。
- **5.3 sector/cluster**: sector 相对动量;14 币 sector 小(2-4 名)统计力有限;主要作 neutralization。
- **5.4 correlation-network 中心性**: 慢,延迟容忍但 alpha 未证。

## ★ TOP 推荐（persistence × 差异化 × 证据强度）
1. **★横截面 funding 作 crowding/positioning-reversion tilt** —— prime lever。8h 边界刷新跨 1h carry。慢/延迟容忍/清成本;2026 仍 1% 显著 Sharpe~0.96 分散化。差异化: 方向-信号用法不拥挤(delta-neutral harvest 已死)。
2. **Binance top-trader-vs-global 持仓背离(per coin)** —— 差异化伴侣。几无干净发表=上行;hourly 中等持续 1h-4h;与 funding 正交(count vs price)。必自验。
3. **累积/积分净签名订单流(per-asset 归一,多小时)** —— 把微结构带到 1h 的正确方式(继承 Hurst0.7),非瞬时 OFI。成本敏感需 maker。
4. **LambdaRankIC loss(14 币横截面)** —— 最便宜 DL 杠杆,优化部署指标 rank-IC,~零加参。作 AUX w≤0.1。
5. **签名跳/半方差不对称作横截面方向因子 + RV level 作风险/sizing**。
6. **自监督预训练时序编码器**(无标签 1s → fine-tune),利用数据不对称。
7. **BTC/ETH beta-projection floor 作 neutralizer**(模型只学残差 alpha);β 因果 rolling;lagged 效应逐资产先测。
8. **regime gating overlay(非因子): 横截面 dispersion + VPIN 毒性 rank + liquidation 级联 flag** —— dispersion 高/毒性低加仓,级联时降杠杆。

**去优先级**: delta-neutral funding harvest(商品化 2025 负 Sharpe); size/流动性/MAX/idio-vol/low-vol(微市值驱动,14 大币消失,错 horizon); 瞬时 OFI 作方向信号(分钟死); 显式 GNN(节点太少); RL 挖公式动物园(拥挤+OOS 衰减); liquidations 作平滑因子(仅事件)。

**验证纪律**: 两个最强因果衍生品结果发现 basis/premium 被动量预测更干净(非预测未来收益),edge 日→月衰减 → 任何 funding→return 声称在 8h-日验证严格 per-fold 符号一致,别假设月持续。每个净成本源都印证: 快微结构 1h 被费毁,只低换手(funding/positioning/vol-state)存活。
