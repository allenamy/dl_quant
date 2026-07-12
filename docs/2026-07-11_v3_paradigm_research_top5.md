# v3 范式调研 Top-5（2024-26 前沿, 三重验证+评级）

> **创建:** 2026-07-11 | **状态:** final (调研结论, 赛马臂待执行) | 完整版含全部来源见调研 agent 输出; 本文为决策摘要。
> 评级: A=真实 OOS 金融结果 / B=纯 benchmark / C=无证据。~90% 文献为 pre-cost 日频 A 股短窗; 独立迁移测试(CN→US)显示 headline 缩水 3.4× = 正确先验。**没有任何文献评估我们真正的门(增量正交 rank-IC over carry 基线) —— 一切须过自家漏斗。**

## TOP-5 赛马臂（按 EV 排序）

| # | 范式 | 预注册假设 | 成本 |
|---|---|---|---|
| 1 | **公式化 alpha 工厂**(AlphaGen/AlphaForge 系, 正交性写进 mining reward; 可选 LLM 提议器+受限 DSL+确定性评估器) | ≤20 条幸存公式的集合在 4h/24h 加 ≥+0.005 正交 rank-IC, per-fold 符号一致, maker 净成本正 | ~1-2 周工程; 单次 mining 数小时 |
| 2 | **in-context 截面预测器**(FinPFN/TabPFN-v2: 以近期(特征,收益)对为上下文, 无需重训练地逐步更新映射) —— **直击我们最痛的 regime 漂移**(适应靠条件而非权重) | 漂移月胜冻结 Conformer ≥+0.003 pooled rank-IC + 跨月 IC 方差降 ≥30% | 数天(现成代码) |
| 3 | **市场引导截面注意力/低秩混合**(先 StockMixer 瓶颈=学习式多因子去β, 再 MASTER 式 BTC-状态门控注意力) | 同参数预算下加 ≥+0.003 rank-IC 且胜 LightGBM+邻居特征; 动态相关边>静态簇边 | 数天(scaffold 已有) |
| 4 | **分位场隐含均值头**(Baruník, A 级: 37 分位隐含均值显著胜直接均值 —— 重尾下的稳健估计) | 隐含均值 vs 点头 +≥0.002 rank-IC + 逐月 IC 离散降; 尾分位交易无增益(预注册 null) | 数小时(我们已跑 pinball) |
| 5 | **线性 IPCA/RP-PCA 条件因子脚手架**(K=3-5; crypto 先例: Bianchi-Babiak N≈250 日频 IPCA 3 因子 预测 R² 2.9%) | IPCA 残差动量/反转 +≥0.002 正交 rank-IC; K=8≤K=4(过拟合检) | 数小时(CPU, pip 可装) |

## 明确不入场（省下的实验槽 = 收益）
- **TSFM 时序基础模型**: 两项独立 A 级 null(零样本 R² −1.4~−2.8%; 微调多数更差; 冻结 embedding 唯一直接测试为负);
- **★ Mamba/xLSTM/RWKV 骨干换装**: 零 A 级金融证据; 旗舰论文口径灌水(SAMBA IC 0.45=pooled 回归口径); 数据规模论证指向**更小**模型(TTM 0.8-5M 参数级) —— **"不要为骨干换装花一个实验槽"**(可插拔 harness 保留, 但臂从骨干换装转向 top-5 范式);
- KAN(MLP 平手+噪声脆弱+walk-forward 遗忘更重); 端到端组合网(尺度膨胀病理=我们 IC-vs-β 教训的重发现; **偷两个 trick**: γ=0.5×真实成本的 shrunk-cost 训练 + SoftMin 最差窗惩罚); 扩散/生成头(FinTSB: 全败给 GBDT); flow matching(零证据); 密集静态图; hourly lead-lag 网络(净成本证据只活在 ≤10min, 与我们 600s 测量一致)。

## 深度 VAE 因子族警示
Avramov et al.(Mgmt Sci, A 级): 非线性 DL alpha 剔除微盘/困境股后损失 48-94%; **线性 IPCA 在"好交易"子集上仅温和退化** —— 我们的 110 液态 perp 恰是"剔除后"的 universe → 线性 IPCA 优先于深度 VAE 族。FinTSB 独立重评: FactorVAE IC −0.004。K≤6 铁律(三源一致)。

## 交叉警示
IC 口径混乱(pooled/per-ts/per-stock-TS 不可跨论文比较); LLM-mining 必配 MemGuard 污染诊断; 公式工厂的多重检验纪律在我们(预注册 reward/幸存上限/fold 符号)。
