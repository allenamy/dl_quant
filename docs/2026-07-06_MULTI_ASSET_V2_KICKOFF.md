# 多资产 v2 — 中频横截面 long-short 创新因子 · 启动计划

> **创建:** 2026-07-06 | **分支:** multi-asset-v2 | **状态:** in-progress (Phase-0) | **作废条件:** 被后续里程碑取代
> **前置:** 单资产 y_600 已收口(`docs/2026-07-06_SINGLE_ASSET_PERP_Y600_CLOSEOUT.md`);方法论/工具/Run1 底盘复用(`run1_reference_package`)。

## 0. 北极星（与用户 brainstorm 明确）

**做 14 币 USDT-perp 的中频(1h 起)横截面 long-short,以"净成本可交易"为北极星。走杂交路线: DL/ML + 跨领域知识构建创新因子(edge 所在) + 稳健横截面组合 + 显式成本控制。**

- **路线判定**：因子为核 + DL 增强 > 纯端到端 DL（单资产实测端到端撞天花板+难交易；中频横截面因子范式更可靠/主流/可归因/可控成本）。
- **edge 定义（可量化）**：**创新因子在"商品化因子基线"之上的 增量正交 IC + 净成本组合贡献。** 传统因子无壁垒;我们只投资"正交增量"。
- **北极星指标**：横截面 long-short 净成本 Sharpe / IC-IR(主) + 增量正交 IC(因子验收)。
- **horizon**：1h 起(+2h 稳健性)。

## 1. 因子弹药（按 差异化×可行性）
1. **1s 微结构 → 中频因子**(最硬数据 edge;复用单资产时序编码器作因子构造器): OBI 持续性/成交尺寸漂移/盘口补充速度/Kyle-λ 趋势/1s 实现波动期限结构。
2. **跨资产网络/关系**: lead-lag、订单流溢出、横截面背离、BTC-beta 残差。**★BTC 高精度 Tardis 25 档作 alt 的领先驱动**(诚实: 单资产 lagged BTC→alt 600s 弱~0.02,需 guard-first 早测 1h+微结构状态版)。
3. **自监督表示学习**(3 年无标签 1s 预训练 → embedding 即因子;门槛高别人少做)。
4. **跨领域**: 信息论(熵/互信息)、Hawkes 点过程、频域/小波(因果)、变点/regime。
5. **funding/OI**(y180 唯一未测 IC 杠杆): funding 差分、OI 动量、funding×微结构交互、分粒度。

## 2. 因子研究流水线（每个候选过五关，防低 SNR 过拟合）
1. 横截面 IC + IC-IR;
2. **增量正交 IC**(基线残差上,横截面,OOS —— 同事残差思路,但组合用联合重拟合非裸加);
3. 正交性/相关矩阵(去冗余);
4. walk-forward 门(Ridge/浅模型,ΔIC≥阈值才入库);
5. 净成本组合贡献(day-1 判)。
**创新因子先过 Ridge 门再上 DL;gated + 双人验证。**

## 3. 复用的方法论铁律（单资产带来）
- IC 是 alpha / β 是量纲;口径纪律(clean/dense/clip/raw-y);净成本回测判可交易;guard-first + 预注册 kill 门 + 双人验证 + gated flag;容量匹配信号 + 加通道惩罚 + Ridge-before-DL。

## 4. Phase-0（地基,多 CPU/Ridge 不烧 GPU）
- **★ GO/NO-GO 门**: 1h 横截面 long-short 商品化基线,净成本可交易吗?(y180 说 180s 不可交易;1h 待实测;不可交易→换更长 horizon)。
- 步骤: ① 盘点复用现有 infra ② 14 币 1s→1h 面板(as-of 无泄漏)+ BTC Tardis 25 档接入 ③ 商品化因子基线 + 横截面 Ridge → 基线净成本 Sharpe + 残差 ④ 因子工厂评分器(五关) ⑤ beta-projection 底板 + BTC→alt lead-lag 早探。

## ★ Phase-0a 结果 (2026-07-07): NO-GO on 快微结构基线 —— 但诊断重定向方向

**1h 横截面 long-short 快微结构基线 NOT 净成本可交易**: break-even **0.408 bps/side**, 每档水下(连 maker~1)。1h xsec rank-IC +0.0066 / IR 1.15(真实但薄, ~10× 低于 10min 的 0.0744)。

**三诊断(决定性)**:
1. 6× 换手摊薄救不了: 1h IC 小 ~10× 抵消 6× 成本节省有余 → 成本主导(同 y180);
2. EMA 平滑反更差: 1h 信号无可平滑持续性(一周期,混陈旧权重反号)→ 逼满换手;
3. **★ "1h→延迟容忍"假设证伪: 1h alpha 3min 衰减 50%/6min 80%, 同 y600. 延迟容忍是"特征"属性非"目标 horizon"属性 —— 慢目标配快特征照样延迟敏感.**

**战略重定向(诊断指向)**: 问题不在 horizon 在"特征太快"。**可交易中频横截面 alpha 更可能在 慢/持续因子(多小时动量、funding/OI 差分、basis、regime),非快微结构。** 张力: 我们数据 edge 是快微结构,但可交易信号要慢持续因子(相对更商品化)。→ edge 三候选: ① 微结构累积成慢信号(慢 positioning/liquidity regime, DL 学慢 state) ② **funding/OI 差分(y180 唯一未测 IC 杠杆, 天然慢/持续/延迟容忍 —— 可能最对)** ③ 微结构作执行择时叠慢 alpha 之上。**下一测(待用户方向确认): 慢持续因子基线(多小时动量/反转/波动 + funding/OI)1h 净成本 GO/NO-GO.**

## ★ Phase-0b 结果 (2026-07-07): B 慢价格因子 = NULL(印证研究), A 无数据阻塞

**B(慢价格因子基线) = NULL/NEGATIVE**: pooled xsec ridge rank-IC −0.005 / IR −0.80(n=2760, 因果验证 leak-free, 真 null 非泄漏)。逐因子: 动量全负(mom_4h −0.010→72h −0.024, **1h 大币是横截面反转非动量**), rev_1h/3h 弱正(+0.013/+0.014), vol/beta/等 max|standalone|~0.028, **符号跨 fold 不稳→组合 anti-generalize**。→ 印证研究预警(慢价格因子 14 大币消失/微市值驱动)。**B 残差≈0 → A 因子的增量正交 IC ≈ standalone IC(干净基线)。B 是打靶对象非赌注。**
**A 前置 = 无数据阻塞(good)**: funding/OI/positioning 数据全历史可得(data.binance.vision BULK 归档, 非 30 天 REST 限)。BTC metrics 2023-02→2026-06(覆盖面板): OI/top-trader 持仓比/账户比/global 账户比/taker vol 比; funding 全历史。→ funding-carry + positioning-divergence 在 2024-06..2025-09 可建。0B 自主推进: 扩 2 dump 脚本到 14 币 → 对齐(funding 8h/metrics 5m ffill≤t)→ 建 2 因子(因果+shuffle-null)→ 报 standalone IC。**A = 真赌注,决定性数字在路上。**

## ★ Phase-0b/A 结果 (2026-07-08): funding 杠杆 REAL, positioning NULL —— 净成本 gate 待定

**A funding 因子(leak-clean: ffill≤t sentinel PASS, 覆盖~1.00, shuffle-null done):**
- ★ **funding_ema(24h 平滑 funding): standalone IC −0.0186, z=−2.50, 3 fold 符号一致(−0.0035/−0.0373/−0.0150)** —— 负=crowding-reversion(高 funding→低未来收益)= 论点成立每 fold。**赢家。**
- funding_carry(raw): −0.0173, z=−2.89, 噪(fold0≈0); EMA 平滑帮(8h 高自相关)。
- toptrader_pos: −0.0156, z=−1.97(边缘), 符号一致。
- **NULL: global_account(z=−0.74 bias 调后 null); pos_divergence(−0.0043, z=−0.27, 符号翻→NULL, 大币上失败-catalog 已预警自验); oi_mom/taker_ratio NULL。** 组合 7 因子 ridge +0.005/IR 0.87。
**诚实 caveat: ① shuffle-null 均值非零(14 资产持续因子小样本横截面 bias)→ z vs 经验 null 才是诚实显著性(funding_ema/carry 过, global/pos_div 不过); ② regime 依赖(fold1-heavy −0.04 vs fold0≈0)。**
**关键洞察: |IC|~0.017 幅度温和(似 fast-micro 0.0066, ~4× 干净于 B 的符号不稳噪声), 但 funding 的差异化在 净成本-via-低换手(8h stamp+24h EMA→延迟容忍)。★真 GO/NO-GO = funding_ema-only L/S 净成本 gate(纯低换手杠杆, 排除 null 因子的快换手污染): 能否清成本(fast-micro BE 0.408/慢价格 null 都不过)。0C gate-e 待定。**

## 5. 约束（继承）
src/ 单资产代码只读;新代码 multi_asset/;share data + btcusdt_copy 只读(mode="r");本地改码 rsync server 训练;无泄漏;单 GPU 串行 GPU exclusivity;kill-gate 不放松;推理零 regime 后验切换。
