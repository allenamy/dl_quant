# ARM-N1b (多关系跨资产注意力, 4h/YR4B) — 0C 独立评分 verdict (gate v2 首臂)

> **创建:** 2026-07-15 JST | **Session:** fable multi-asset-v2 (0C scorer) | **状态:** final | **作废条件:** 若 N1b 以不同 horizon(12-24h)或可证更低 king-corr 的表征重做则重评
> 对象: `train/wideA_n1b_multirel_c1` (panel md5 `6c44238b`, ts 逐字节对齐 king, member 一致, 32ch, horizon 4, fold 分数 test-rows-only=严格 OOS, 4 fold te=2023-2026; +16,775 参数 vs Conformer-ref 255,238 = +6.6%). 目标 YR4B = 全书残差(残差化 on king+S2 OOS).

## 判词: **存档 N1b — 死因 = 换皮(reskin), 非弱**

信号真实(增量 +0.016 显著, dyn 0.918, 因果 leak-clean)但**在 king 的 basin 里**: pred-corr vs king 0.378 越过 gate(i) 的 0.36 资格线, book-corr 0.547 比 S1 还高, 进书显著 HURT。**不同架构复现了 S1 的结局** —— 4h 同 horizon 上, 架构新颖 ≠ 下注新颖。

## 门牌 scorecard (gate v2)

| 门 | 判据 | 结果 | 结论 |
|---|---|---|---|
| a 书-正交增量 | ≥+0.003 逐年符号 + CI 排除0 | +0.0162 CI[.0139,.0186] 4/4年正 | **PASS** |
| b pred-corr king & S2 | 都 <0.7 | king 0.378 / S2 0.247 | pass(底线) |
| **(i) 架构资格线** | **pred-corr vs king ≤0.36** | **0.378** (逐年 .355/.447/.304/.436, 3/4 越线) | **★FAIL** |
| (ii) 复杂度预算 | params:sample 健康 + vs Conformer | +6.6% 参数, samples ~2190×100×4/fold, ratio«1:100 | PASS(非失败轴) |
| (d) dyn + 泄漏 | dyn≥0.5 + 因果 | dyn 0.918; forward-decay 因果签名 | PASS |
| **(c) 书级边际 (DECIDER)** | 五腿装配显著改善 | book-corr 0.547, 进书 w0.05 **−0.242 CI[−.357,−.137] 显著负**, 单调恶化 | **★FAIL** |

## 1. 书-正交增量 (a) — 真实

- 目标 YR4B 正交性核验: corr(YR4B,king)=+0.017, corr(YR4B,S2)=+0.015 (都~0, king+S2 已干净移除); **corr(YR4B,YR4)=0.966** → king+S2 只吃 4h baseline-残差 ~3.4% 维度(近满维, 同 S1 的 0.989 量级), 增量空间几乎完整。
- 增量 pooled **+0.0162** (day-block boot CI[.0139,.0186] 排除0), 逐年 [+.0147/+.0142/+.0144/+.0271] 全正。与 S1 的 +0.0181 同量级。信号是真的。

## 2. pred-corr vs king & S2 (b) + ★架构资格线 (i)

- pred-corr vs king **0.378** (逐年 .355/.447/.304/.436), vs S2 0.247。
- (b) 冗余底线 <0.7: PASS。**(i) 架构资格线 ≤0.36: FAIL** —— 0.378 越线, 3/4 年在 0.36-0.45。
- ★ 机理判读: 目标 YR4B 已移除 king, 一个**真正不同归纳偏置**的范式其残差预测对 king 应显著 <0.36; N1b 落在 **S1(同-arch 4h 再挖, pred-corr 0.36)的同一带** → 多关系跨资产注意力**没有产生不同的下注, 而是重学了 king 的截面结构** = 换皮再挖。4h 的跨资产 alpha 就住在 king 的 basin 里。

## 3. 零初始化门 alpha/λ_k — 结构被用(但小), 非"模型自证无增量"

- checkpoint(fold0): **multirel.alpha = −0.0986** (零初始化, 学到 −0.099, 非≈0), **multirel.lam = [0.054, −0.058, −0.093]** (三时间尺度桶边, 小但非零), Wq/Wk/Wv/gate 权重正常训练(std~0.09)。
- 判读: **结构确实被使用**(alpha≠0, lam≠0) → 不是干净的"模型说多关系无增量"负结论; 而是多关系结构**产出了真实但小的信号**(与 +0.016 增量一致)。alpha 负号 = 减性(把多关系 message 反向掺入, 契合 forward-decay 的 reversal 味)。**关键: 死因不在"结构没被学", 而在"学到的结构信号与 king 冗余"。**

## 4. 五腿 improve-rule + breadth / dyn / 泄漏 / 净成本

- **dyn-share 0.918** (static 仅 +0.0014) — 强动态, 非静态 tilt。PASS。
- **forward-window-decay 因果测** (强制项): IC(pred_t, Yraw_{t+k·4h}) = {−8h: −0.049, **−4h: −0.277**, **0: +0.068**, +4h: +0.031, +8h: +0.022}。**lag=0 峰 + 前向平滑衰减 + 负-lag 强负** = 教科书因果签名(买近期 loser 的 reversal, lookahead 的**反面**)。多关系的滚动相关桶边是 ≤t 因果, **无泄漏**。
- **breadth**: 4h 高频(2190 锚/年 × ~100 币), breadth 充足 —— 但独立净 Sharpe 仅 **0.52**(4h 高换手吃成本, 残差信号 0.016 撑不起独立书; raw 4h IC 0.068 那是被移除的 king)。
- **(c) 书级边际 DECIDER**: n1b↔king **book-corr 0.547** (> S1 的 0.477 —— 比 S1 更冗余); improve-rule Sn(0.52) > ρ·S4(2.61) = **False**; 进书混合逐权重**显著负**: w0.05 −0.242 CI[−.357,−.137] / w0.10 −0.559 / w0.15 −0.945 / w0.20 −1.388, 单调恶化, worst-month 也恶化。**加 N1b 显著 HURT 四腿书** —— S1 pattern, 更严重。

## 判词 + N1a 先验更新

**存档 N1b。死因 = 换皮(reskin), 非弱。** 这是本阶段第二次证明**横向多样性(horizon + 执行)才是补充因子进书的门槛, 架构新颖度不是**: S1(同-arch 4h 再挖)与 N1b(多关系注意力 4h)—— 两个不同架构在**同一 4h horizon** 上都重学 king 的下注(pred-corr 0.36/0.38, book-corr 0.48/0.55), 都进书 HURT。**在饱和 horizon 上, 换架构不换 basin。**

**★ N1a 先验更新 (你要的 fork):** N1b 的结论**不是**"结构变密路线在 fine-tune 端无增量" —— 而是 **"有真实增量(+0.016)但与 king 冗余"**。死因是**冗余/换皮, 非信号缺失**。这对 N1a(预训练端)的含义:
- 多关系跨资产**结构**在 4h 确实携带真实增量, 但其下注住在 king basin(pred-corr 0.38)。N1a 换的是**怎么学表征**(自监督 vs 监督结构模块), **不换 4h 跨资产 alpha 住在哪**(king 已占)。若 N1a fine-tune 到 4h 目标, 大概率落回同一 king-相关 basin。
- ⇒ **N1a 先验 LOWERED(非中性)**。N1b 的换皮死是"跨资产结构路线(无论 fine-tune 注入还是预训练)在 4h 产 king-冗余下注"的证据。
- **仍值得测的条件(二选一): (a) N1a 跑不同 horizon(12-24h, 远离 king; 但那里 S2 在, gate(b) 收紧), 慢跨资产 premia 或许非 king-冗余; (b) 有具体理由证明其预训练表征显著更低 king-corr(如训练目标与 next-return 本质不同)。** 否则**在 4h 跑 N1a 低先验**——预计又一次换皮。
- **建议: 若跑 N1a, 先用便宜的 fold0 pred-corr≤0.36 早筛(全 battery 前), 且优先 12-24h 目标。** 不要在 4h 跑 N1a 期望逃出 king basin。

**阶段账(gate v2):** N1b = 首个前沿臂, 存档(换皮)。前沿双臂门的**架构资格线(i)首次生效并判死一臂** —— 证明该门抓得住"新架构但旧 basin"。四腿书维持不变。
