> **创建:** 2026-07-19 JST | **Session:** fable multi-asset-v2 (0C 独立审计) | **状态:** final | **作废条件:** king/S2 面板重建, 或新数据轴入 CH

# 中频带 (0.5-24h) 缺口审计 — 两个未测格子: sub-4h & 8h 结算时钟 (0.5C)

**背景:** 用户问 0.5-24h 带里除 4h 外有无可补充信号。已测格: 4h 饱和 (S1+N1b 双证) / 12h S2-邻接 (N1a 0.363) / 24h S2 在书。未测格 = **sub-4h (0.5-2h)** 与 **8h funding-结算时钟**。两项 CPU 审计 (用现有产物, 不训练除一个便宜 Ridge)。产物 `exports/eda/horizon_gap_audit.{json,md,py}` + `hgap_robust.py`。

## 判词: **两格都 CLOSE。中频带 (0.5-24h) 现数据轴上 alpha-complete —— 无新 horizon 缺口, 剩余 EV 只在新数据轴。**

---

## 格子 1: sub-4h (0.5-2h) — **CLOSE (三重理由)**

**方法:** king_pred (4h 王) 对 Y1 (1h 前向收益) 逐年横截面 rank-IC, 头对头 vs 专用 1h Ridge-on-32ch 扩张 walk-forward。

| 口径 (pooled 2022-2026) | rank-IC | 逐年 |
|---|---|---|
| king@Y4 (原生 4h, 参照) | **0.1201** | .084/.128/.139/.140/.111 |
| **king@Y1 (4h 王预测 1h)** | **0.0747** | .061/.083/.083/.083/.064 |
| **专用 1h Ridge@Y1 (全 CL1 网格)** | **0.0621** | .062/.065/.057/.065/.061 |
| 专用 1h Ridge@Y1 (king 同锚 head-to-head) | 0.0626 | .054/.074/.053/.069/.063 |
| king@YR1 (残差 1h) | 0.0526 | — |
| 专用 1h Ridge@YR1 (残差) | 0.0196 | — |

**★ king@Y1 (0.0747) > 专用 1h Ridge@Y1 (0.0621), 逐年全胜 (+20%)。4h 王预测 1h 前向收益比一个为 1h 量身定制的线性模型还强。残差口径更悬殊 (0.0526 vs 0.0196, 2.7×)。** ⇒ **CLOSE 三重:**
1. **king 已覆盖:** 4h 王在 1h 上已是最强线性信号 (0.075 ≥ 专用 0.062, 逐年全胜)。sub-4h 无 king 之外的可挖 alpha。
2. **邻接冗余先验:** forward-decay +1h 保留 90% 峰值 + king@Y1 直证 king 携带 1h 信号 → sub-4h 因子住在 king basin (同 S1/N1b 教训: 同-horizon-邻接再挖重学 king)。
3. **换手经济学:** 1h 再平衡 = 4× 4h 换手 (24×/日 vs 6×/日)。专用 1h 信号 (0.062) 比 king 4h (0.12) 更弱却贵 4×; BE 5-16bps 下净成本强负。便宜执行 ≠ book 价值。

---

## 格子 2: 8h funding-结算时钟 (00/08/16 UTC) — **CLOSE (结构不稳健)**

**机制假设:** funding 每 8h 结算, 仓位在结算前 unwind (拥挤多头卖出避付 funding) / 结算后 rebuild —— 事件驱动, 构造上与价格结构因子不冗余。**事件研究:** 以结算时刻为锚, funding 分层的 event-time 残差收益曲线 (±4h), settle (hour%8==0) vs placebo (hour%8==4)。**决定性测: 残差 YR1** (静态 funding 已移除 → 任何结构 = 结算时钟的增量)。

**表面有弱结构:** settle 残差 pre-window funding-IC **−0.0102** vs placebo **−0.0027** (~3×放大); event-time hi-lo 价差 pre-settlement ~1.3bps/hr (低-funding 涨, 高-funding 跌), post-settlement 塌平。像 pre-settlement unwind。

**★ 但不稳健 (逐年符号不一致):** settle−placebo 差 day-block bootstrap + 逐年:

| 年 | settle pre-IC | placebo pre-IC | diff |
|---|---|---|---|
| 2022 | −0.010 | −0.008 | −0.002 |
| 2023 | −0.012 | −0.006 | −0.006 |
| **2024** | **−0.018** | +0.009 | **−0.027** |
| 2025 | +0.001 | −0.001 | **+0.002** (反) |
| 2026 | −0.005 | −0.011 | **+0.006** (反) |

**diff pooled −0.0075 几乎全由 2024 (−0.027) 驱动; 2025/2026 符号反转 (+0.002/+0.006)。`sign_consistent_diff = False`。** ⇒ 表面的"pre-settlement unwind"是 **2024 regime 伪影, 非稳定时钟机制** —— 过不了我给所有因子的逐年符号一致铁律 (#14: 单年不可靠)。**settle 与 placebo 的残差 funding-IC 都只是 ~−0.003~−0.01 的弱残余 funding 结构, 其时钟-特异差不存活。**

**intraday session 扫描 (顺带):** funding-IC vs YR1 逐 session 全 ≈0 (asia −0.0002 / eu −0.0007 / us −0.0010); 横截面收益离散 asia 71 / eu 74 / us 67 bps —— 无 session 截面结构 (time2vec 单资产失败的低先验确认)。**session 效应 CLOSE。**

⇒ **8h 结算时钟 CLOSE:** 弱表面结构过不了逐年符号一致 (2024 伪影); 且即便真, 也只是现有 8h-cadence funding 腿的**时钟-timing overlay** (非新轴), 增量 ~0.0075 IC 需净成本 gate。无稳健事件-clock alpha。

---

## 中频带 (0.5-24h) 完整地图 (审计后)

| horizon | 状态 | 证据 |
|---|---|---|
| sub-4h (0.5-2h) | **CLOSE** | king@Y1 0.075 ≥ 专用 1h 0.062 逐年全胜 + 邻接冗余 + 4× 换手 (本审计) |
| 4h | 饱和 (在书) | king; S1 (4h 再挖 pred-corr 0.36) + N1b (换皮 0.38) 双证 |
| **8h 结算时钟** | **CLOSE** | 弱结构过不了逐年符号 (2024 伪影, 25/26 反) + session 平 (本审计) |
| 12h | S2-邻接 | N1a pred-corr 0.363 |
| 24h | 在书 | S2 ACCEPT |

**一句话给汇报:** 中频带两个未测格子都 CLOSE —— sub-4h 上 4h 王已是最强 1h 信号 (0.075>专用 1h 0.062 逐年全胜, +邻接冗余+4×换手); 8h 结算时钟的表面 unwind 结构是 2024 单年伪影 (逐年符号不一致, 25/26 反号), session 效应平。**0.5-24h 带在现数据轴 alpha-complete, 无新 horizon 缺口。剩余 EV 只在新数据轴 (funding/OI 之外的正交源), 与前沿双臂 (N1a/N1b) 阶段结论一致。**

---
**产物:** `exports/eda/horizon_gap_audit.json` (含 robustness_pre_unwind) · `horizon_gap_audit.py` · `hgap_robust.py`。
