# 前沿 v4 调研（25-26 增补）+ 双臂设计定稿

> **创建:** 2026-07-14 23:50 JST | **Session:** fable multi-asset-v2 autonomous | **状态:** final (设计定稿, 臂结果落 leaderboard) | **作废条件:** 双臂判决落地后由结果段取代
> 交叉引用: 基线调研 `docs/2026-07-11_v3_paradigm_research_top5.md`; 验收门 `exports/eda/suppl_factor_gate_prereg.md` §v2 (server); 阶段背景 `docs/2026-07-12_ENGINE_A_FINAL_MILESTONE.md` §五b

## 调研判决（research-frontier-v4, web 三重验证）

**两条真新线索 + 确认三条不做。** 关键新主题: 不是换骨干, 而是**把"跨资产结构"的学习信号变密** —— 方向 (alpha) 低 SNR, 但**共动 (co-movement) 高 SNR**, 用未来共动做显式监督能学出单层隐式注意力学不出的结构 (含一个 A 级 crypto OOS: 多关系注意力, 六币 2020-2025, IC 0.071, Sharpe 2.25)。

**不做清单 (7/11 判断全部维持):** PFN/in-context (上下文 ≤10k 行/无 online 更新/大数据不如 CatBoost, 硬限制未松动 — **推翻了我们的默认候选 ARM-N1=FinPFN, 省最重适配工程**); SSM-attention 杂交 (全 benchmark 级零 A 级 crypto); TTA (证据是预测误差非 alpha, 定位生产侧); LLM-DSL 因子挖掘 (A 级但属已有公式工厂家族, 其"约束 DSL+确定性评估+append-only 失败轨迹"纪律可并入现 miner)。

## 双臂定稿

**ARM-N2 (LambdaRankIC): 前置核查塌缩 → ARCHIVE 不跑 (2026-07-14 深夜)。** 0B 读现实现: `losses/xsec_residual_loss.py::lambda_rank_ic` **逐字就是 arXiv 2605.00501 的位移加权闭式** (w_ij = 12·|r̂ⱼ−r̂ᵢ|·|ỹᵢ−ỹⱼ|/n(n²−1), docstring 引同篇 Lin 2026), **且已是王座 primary loss (权重 1.0)**; aux 加权版 (w 0.1-0.3) = DLv2 L1 臂已测 REJECT。**N2 无处可加。侧记: 王座 loss 独立收敛于 2026 前沿 — 验证性发现。前置核查纪律拦下冗余臂, 省 1-2 天。**

**顶替第二臂 = ARM-N1b 多关系跨资产注意力** (调研 #1 的另一实现, A 级 crypto OOS 佐证): 单头 xattn → K 条关系边 (独立注意力通道 + 门控混合), 增量参数 ≤50k 硬顶。与 N1a 共享"结构信号变密"主题、归纳偏置不同 (表征预训练 vs 关系通道展宽), 互为对照。关系边诱导方案 (无显式图) 待设计文档: 滚动相关分桶 / 特征子空间 / 可学习分组。

**ARM-N1 (长线, 4-6 天): 未来共动 soft-contrastive 预训练跨资产编码器。** 用未来窗已实现相关做对比目标预训练 encoder 结构, fine-tune 到 YR4B。走**预训练**路线不走 aux 头 (aux-MTL 轴已关)。泄漏纪律: 逐 fold 预训练, 共动标签未来窗完全落在训练窗内; 0C forward-decay 因果测强制。设计文档先行再动手。

**基建:** YR4B/YR24B = 全书残差目标 (YR 对 king+S2 OOS pred 面板残差化) — "基于当前的残差"的严格实现; 稀疏约束 (pred 面板只在锚点, 交集 ~220k cells) 待 checkpoints 勘察定加密与否; mixer/新架构参数硬顶 ≤50k。验收 = 0C v2 门 (四腿书基准 + 归纳偏置差异实证 pred-corr≤0.36 + in-context 泄漏专项 + horizon 限 4-24h + "0 进书合法"诚实先验)。

## 结果段 (2026-07-15 滚动)

**N1b (多关系注意力) = ARCHIVE, 死因=换皮 (0C `arm_n1b_verdict`):** book-正交增量 +0.0162 真实 (CI[.0139,.0186], 4/4 年正), 零初始化门自白=结构确实被用 (alpha 训到 −0.099, λ 非零), forward-decay 因果签名教科书级 — **但 pred-corr vs king 0.378 越 0.36 资格线 (gate-v2 (i) 首次生效判死), book-corr 0.547 比 S1 更冗余, 进书逐权重显著负 (w0.05 −0.24)。★教条二次证明 (S1 同-arch + N1b 异-arch, 同死于 4h): 饱和 horizon 上换架构不换 basin — 横向 (horizon+执行) 多样性才是进书门槛, 架构新颖度不是。**

**N1a 先验下调后条件执行:** horizon 改 **12h** (king-4h 与 S2-24h 之间无人区) + **fold0 pred-corr≤0.36 早筛** (过线才跑全 battery)。这是本阶段最后一臂。

**N1a (共动对比预训练, 12h) = 早筛撤臂 (2026-07-15, 0C `arm_n1a_screen`):** 预训练本身成功 (loss 2.22× 单调降, encoder 学到共动结构), fold0 增量 +0.0271 (三臂最高) — **pred-corr vs king 0.294 PASS (12h 移动成功逃出 king basin, 横向多样性论点验证) 但 vs S2 = 0.363 越 0.36 线 (仅 +0.003, 1 SE 内) → 尊重预注册撤臂, 不事后移门**。[4h,24h] 带已被 king+S2 夹满, 带内无干净空档 (12h→8h 近 king / →16h 近 S2 / >24h breadth 饥饿)。

## ★ 阶段终局 (2026-07-15): 前沿双臂 = 0 进书 — "0 是合法结论"兑现

N2 塌缩 (王座 loss 已在 2026 前沿) / N1b 换皮 (king-冗余) / N1a S2-邻接冗余。**三个死法共同指向: 四腿书在现数据轴上 ALPHA-COMPLETE — 残差空间的可预测部分已被现有腿覆盖满 (快端 king 4h, 慢端 S2 24h, 中间被邻接吃掉, 更慢 breadth 饥饿)。剩余增量 EV 只在新数据轴 (现面板之外的正交信息源), 不在架构/loss/horizon。** 王座 loss 独立收敛于 2026 前沿 = 本轮调研的验证性副产品。
