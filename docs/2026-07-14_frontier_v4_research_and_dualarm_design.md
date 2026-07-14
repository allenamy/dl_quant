# 前沿 v4 调研（25-26 增补）+ 双臂设计定稿

> **创建:** 2026-07-14 23:50 JST | **Session:** fable multi-asset-v2 autonomous | **状态:** final (设计定稿, 臂结果落 leaderboard) | **作废条件:** 双臂判决落地后由结果段取代
> 交叉引用: 基线调研 `docs/2026-07-11_v3_paradigm_research_top5.md`; 验收门 `exports/eda/suppl_factor_gate_prereg.md` §v2 (server); 阶段背景 `docs/2026-07-12_ENGINE_A_FINAL_MILESTONE.md` §五b

## 调研判决（research-frontier-v4, web 三重验证）

**两条真新线索 + 确认三条不做。** 关键新主题: 不是换骨干, 而是**把"跨资产结构"的学习信号变密** —— 方向 (alpha) 低 SNR, 但**共动 (co-movement) 高 SNR**, 用未来共动做显式监督能学出单层隐式注意力学不出的结构 (含一个 A 级 crypto OOS: 多关系注意力, 六币 2020-2025, IC 0.071, Sharpe 2.25)。

**不做清单 (7/11 判断全部维持):** PFN/in-context (上下文 ≤10k 行/无 online 更新/大数据不如 CatBoost, 硬限制未松动 — **推翻了我们的默认候选 ARM-N1=FinPFN, 省最重适配工程**); SSM-attention 杂交 (全 benchmark 级零 A 级 crypto); TTA (证据是预测误差非 alpha, 定位生产侧); LLM-DSL 因子挖掘 (A 级但属已有公式工厂家族, 其"约束 DSL+确定性评估+append-only 失败轨迹"纪律可并入现 miner)。

## 双臂定稿

**ARM-N2 (先跑, 1-2 天): 位移加权 listwise LambdaRankIC 损失臂。** 闭式 lambda 梯度直接优化截面 Spearman (arXiv 2605.00501), 低 SNR 下 train-test gap 显著小于 MSE = 对 anti-pattern #15 的针对性反证据 (旧失败是朴素 pairwise 式)。前置核查: 现 stage2b lambda_rank_ic 若已是位移加权 → 塌缩为已测存档。AUX w≤0.1 起 (#15 纪律), YR4B 目标。

**ARM-N1 (长线, 4-6 天): 未来共动 soft-contrastive 预训练跨资产编码器。** 用未来窗已实现相关做对比目标预训练 encoder 结构, fine-tune 到 YR4B。走**预训练**路线不走 aux 头 (aux-MTL 轴已关)。泄漏纪律: 逐 fold 预训练, 共动标签未来窗完全落在训练窗内; 0C forward-decay 因果测强制。设计文档先行再动手。

**基建:** YR4B/YR24B = 全书残差目标 (YR 对 king+S2 OOS pred 面板残差化) — "基于当前的残差"的严格实现; 稀疏约束 (pred 面板只在锚点, 交集 ~220k cells) 待 checkpoints 勘察定加密与否; mixer/新架构参数硬顶 ≤50k。验收 = 0C v2 门 (四腿书基准 + 归纳偏置差异实证 pred-corr≤0.36 + in-context 泄漏专项 + horizon 限 4-24h + "0 进书合法"诚实先验)。
