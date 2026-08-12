# 引擎全历史回放 — 0C 独立复核

> **创建:** 2026-07-15 JST | **Session:** fable multi-asset-v2 (0C) | **状态:** final | **作废条件:** 引擎组件/腿构成/权重变更
> 复核对象: `engine/replay_fullhist.py` → `engine_fullhist_replay.json`。独立重算脚本 `engine_replay_review.py`(重实现 netting-loop P&L, 驱动引擎自身 leg_signals/C5, 自带换手/P&L/Sharpe 口径 + C5/C6 消融)。

## 判词: **表可复现, 组件工作正常。但三条诚实校正必须随表引用: (1) 引擎 headline Sharpe 的主导杠杆是 C5 funding 方差控制(+2.6 avg), 不是 king alpha —— 去掉 C5 引擎跌到 5.3 < book_assembly 7.1; (2) C5 的收益是分母(方差)非分子(alpha), FTX 日在 funding_ema 口径下已被 EMA 平滑, C5 的真价值是全年方差控制非那一天; (3) 这是结构口径 Sharpe, 部署要叠 maker-fill 栈, 会显著折损。**

## Task 1 — 复算核对 + 逐组件归因

**★ 复现成功:** 独立重算(9821 anchors)得逐年 net Sharpe **[2022 6.87 / 2023 7.34 / 2024 9.21 / 2025 11.97 / 2026 3.89]**, 与 0B JSON [6.88/7.34/9.19/11.84/3.96] 逐格吻合(rounding 级差, 来自 disp-ref 校准的浮点)。hedge 11.9% / gross 872 / net 767 / save 197.9bps 全复现。**表不是 bug。**

**逐组件归因(net Sharpe, equal-year avg):**

| 变体 | 2022 | 2023 | 2024 | 2025 | 2026 | avg |
|---|---|---|---|---|---|---|
| FULL (C5+C6) = 出货表 | 6.87 | 7.34 | 9.21 | 11.97 | 3.89 | **7.86** |
| 去 C6(用 gross 换手成本) | 6.63 | 7.12 | 8.99 | 11.67 | 3.72 | 7.63 |
| **去 C5**(plain funding z) | 5.49 | 4.48 | 6.37 | 8.84 | 1.34 | **5.30** |
| (对照) book_assembly_4leg | — | — | — | — | — | ~7.1 |

- **★ C5 funding 风控 = 主导杠杆: +1.4~+3.1 net Sharpe/yr (avg +2.56)。去掉 C5, 引擎 avg 5.30 < book_assembly 7.1。** 引擎能追平/超过 book_assembly **全靠 C5**。
- **★★ C5 的收益是分母(方差)不是分子(alpha) —— 已机制验证:** funding_ema 腿 z-score + L1 加权在**无 winsor 时会集中到离群币**(单名 L1 权重 mean 0.137 / p99 0.41 / **max 0.49** —— 一个币占 funding 腿 49%!); C5 winsor(±4)+name_cap(0.15)+disp-gate(122 天触发)把单名压到 ≤0.18, **funding 腿 P&L 波动降 44%(std 0.0021→0.0015)**。降 funding 方差 → 降书方差 → 抬 Sharpe。**C5 是 funding_ema 腿的必需卫生(否则腿不可交易), 非可选 alpha 增强。**
- **★ "winsor 会削 2022/2023 强 funding 年 alpha 吗? —— 不会, 因为这口径下 funding 没 alpha 可削。** funding 腿逐年均值 P&L −0.05~−0.22(全年近零/微负, 是方差型分散腿非 alpha 腿), C5 在 2022(+1.71)/2023(+3.35)的 GROSS Sharpe 也是**改善**。没有 funding alpha 被削, 只有方差被控。
- **C6 净额: +0.17~+0.30 net Sharpe/yr (avg +0.23)**, 来自 197.9bps/yr 成本节省。真实、一致、如预期地 modest。
- **★ isotonic (C3) + pos_cap 不在回放 P&L 路径里(代码确认): `netting.run` 用 `leg_signals` 从不调 `target_position`。对表零影响。** 且 isotonic 单调 → rank-IC 不变, 本就不改 rank-Sharpe。回放持仓 = z-加权未校准(非 rank-加权, 非 magnitude-校准)。vol_gate exposure_mult 钉死 1.0(执行战术 only, 符合我尾部结论)。

## Task 2 — C6 口径对齐裁定

- **0B 的 11.9% / 197.9bps 在引擎面板上精确复现**(cadence-hold on 4h 网格)。我早先的 **86-179bps / 5.4-8% 是在 book_assembly 代理面板上**(megacap raw funding / wide DVOL30 / s2-24h)—— 那是**不同的、非出货**的 funding/size 构造。差异 = 面板 + cadence 模型, 非任一方错误。
- **★ 部署口径 = 0B 的:** 在 king 4h 执行网格上重新净额; 每条慢腿按其 cadence(funding 8h / s2 24h / size daily)re-signal, 订单在下一个 4h anchor 提交; 只交易 Δnet。在**出货的引擎面板**上 = **11.9% / 197.9 bps/yr**。**此数 supersede 我的代理 86-179**(那是 proxy 预览)。两者各自面板都对, 引擎数出货。
- 规格注: 0B 用 hour-index 取模定 cadence, 合法(wide_dl_full 是无缺口逐时网格 48168)。

## Task 3 — FTX 日重演 (C5 存在意义)

- 引擎口径(funding_ema, z+L1), **2022-11-09(6 anchors)书 P&L: C5off −0.023 → C5on −0.015(降 ~35%)**, funding 腿 −0.022 → −0.010(**减半**)。
- **★ 关键 caliber 校正:** 那个 **−18σ / −4.11 事件是在 book_assembly 的 megacap-RAW funding 口径**下。**引擎用 funding_ema(24h-EMA), 把 FTX 尖峰预平滑掉了** → 在出货口径下 FTX 日本就温和(−0.023), 不是 −4。所以 **C5 的 FTX-专项收益 modest, 因为 EMA 已吸收了那天的大部分尖峰; C5 的真价值是全年广谱方差控制(+2.6 Sharpe/yr), 不是那一天。** 组件被立项的理由(FTX −18)是 caliber-依赖的, 在出货口径里已被 EMA 大部分吸收 —— 但 C5 仍必需(理由变成: 治 funding_ema 的离群集中), 只是"存在意义"的叙事要从"救 FTX 那天"改为"控 funding 全年方差"。

## Task 4 — 诚实边界 (可引用定位判词)

**这张表 = "引擎结构口径": 日 Sharpe × √365, 高 breadth 4h 市场中性书, 只扣显性 1.9bps, 无 maker-fill 滑点/逆选择/排队/冲击/容量。它是信号质量上界, 不是可部署 Sharpe。**

可引用一句:
> **"引擎全历史 7-12 Sharpe 是结构口径(frictionless-除 1.9bps, 日频×√365, 市场中性), 是信号质量的上界而非部署净值 Sharpe。部署口径需叠 maker-fill 执行栈(tick-验证的逆选择 markout 平静 −1/压力 −3.2/崩盘 −5.3bps、fill-rate<1、排队、冲击、容量), 会实质折损; 且该 Sharpe 重度依赖 C5 对 funding 腿的方差控制。对标业界时对标研究/信号级 Sharpe, 不对标扣全成本的基金净值 Sharpe。"**

补充建议(非 blocker): 引擎的 funding 腿构造(funding_ema + z + L1)比 book_assembly 的(megacap raw + rank)更依赖激进 winsor 才可交易; 可考虑改用 rank 加权(天然有界, 免离群集中)或 book_assembly 的 megacap-raw funding 构造, 减少对 C5 的依赖。
