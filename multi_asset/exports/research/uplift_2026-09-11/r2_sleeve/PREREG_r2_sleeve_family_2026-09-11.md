> **创建:** 2026-09-11 | **Session:** session_01H39k5rgyd43mFMNsaBqzeX | **状态:** 冻结于任何 sleeve 数字之前 | **作废条件:** GATE P 非逐位, 或 GATE A(5m↔面板因果对齐)不通过

# PREREG · Round-2 SLEEVE FAMILY — K 声明与判据冻结

## GATE P (device)
w10_sleeve.py sha256 b88e35a46b93d712... 全旋钮默认 ⇒ 复现归档 V4_A0_{dyn,fix}_s{42,2027} 的
d30_n2_c42_rec 与 d30_n2_c42_W **逐位**。不过则本轮全部作废。

## GATE A (alignment, 新增 — round 1 没有做)
5m 缓存的哪些行在锚 E 处是因果可见的, 必须用 **重建面板 Y4** 证明, 不得按文件名/索引推断
(E-0825-H/G)。判据: 某个偏移下 median|Y4_rebuilt − Y4_panel| < 1e-5 且 corr > 0.999。

## K 声明 (在看任何数字之前)
本轮录取候选 = **K = 16** 个特征族, 每族 = 一个原始特征 → 逐锚截面秩 → 对在役 fund 腿分
(rank(f_fund_ema_v1)) 逐锚截面正交化 → 站立书 (LEGS=001 PHI=0 FTRIM=off FEMAT_NPZ=注入)。

**Group L — 对 round 1 未滞后即判死的族施加 LAG-1 修正 (8)**
L1 f_tbf_24h · L2 f_rev_24h · L3 f_vol_7d · L4 f_range_24h · L5 f_cpos_24h · L6 f_volq_ratio ·
L7 f_mom_30d · L8 f_fund_iv
机理: Amihud 从 CI 含 0 变成 CI 排除 0 的唯一改动就是把窗口提前一个锚结束。round 1 的 S7 谱显示
amihud k=−1 (+0.0237) ≫ k=0 (+0.0096) —— 同期 bar 污染。TBF 被 round 1 以同一形态(k=−1 30×)判死。

**Group N — 5m 缓存新造微结构/路径特征, 窗口 24h 且在 E 的前一个锚结束 (8)**
N1 ROLL 有效价差 2·sqrt(max(0,−cov(r5,r5₋₁))) · N2 VR 方差比 · N3 RSKEW 已实现偏度 ·
N4 JUMP 最大 5m 波动占已实现方差比 · N5 DSEMI 下行半方差占比 · N6 ILLQTR 非流动性创新
(amihud24h − amihud7d) · N7 QVTR 成交额创新 · N8 CNTSZ 笔数/单笔额背离
机理: 这些是 bar 可算但 4h 面板没有的量; RM1(下行半方差)在 08-11 新信息战役过 S1 死于 S2 换手,
是旧口径; ROLL/VR/JUMP/RSKEW 从未在本书上测过。

同族的未滞后对照臂与剂量臂**不计入 K**(它们是同一族的剂量点, 不是新赌注)。

## 判据 (冻结)
读数 g = net_ex/gross_total, bps/锚/gross。全周期 = 2022-01-31→2026-08-31 (n=10039, 装置原生轴)。
自举 = UTC 日块 2000 重采样, rng default_rng([20260905,k])。

| 门 | 内容 |
|---|---|
| S1 | 站立全周期 Sharpe ≥ **1.50** |
| S2 | 逐年符号 ≥ **4/5** 年为正 |
| S3 | **\|corr 对 A0 全周期\| ≤ 0.25** |
| S4 | **carry_ex/net_ex ≤ 0.40** (超过即属已关闭的 carry 轴, 不是 alpha) |
| S5 | 两个安慰剂都 ≤ 0: (a) 逐锚打乱特征 (b) 对打乱秩做同一正交化算子 |
| S6 | 自举 CI95 下界 > 0 **且** Bonferroni K=16 下界 > 0 |
| S7 | 前/后向秩 IC: **\|ic(k=−1)\| ≤ 2×ic(k=0)** 且 k=0 为正 |
| S8 | (仅对通过者) 混入书内的配对 Δ vs A0, 全周期 CI95 |

**ADMITTED** = S1–S7 全过。**NEAR_MISS** = S1–S5,S7 过但 S6 的 Bonferroni 下界含 0。
**REJECTED** = 其余。

## AMENDMENT 1 (写在任何 sleeve 数字之前) — 符号选择的多重性怎么算
每个特征有 ± 两个方向。装置层面翻转分数符号 ⇒ 仓位翻转 ⇒ `pnl_ex`/`carry_ex` 精确反号,
`cost_ex` 近似不变 ⇒ `g(−) ≈ −g(+)`。因此 **"两个符号里挑好的" 在统计上等价于一次双边检验**,
而自举 CI95 本来就是双边的。⇒ **K 仍然 = 16 个特征族**, 不是 32 个符号臂。
执行上: 先只跑 `+` 号臂, 均值为负的族再跑 `−` 号臂取其读数; 区间一律按双边报。

## AMENDMENT 2 — 阳性对照 (不计入 K)
`XSL_ORTHLAG` (round 1 的 Amihud 滞后正交化 sleeve) 在我自己的树里重跑一遍, 必须复现
round 1 读数, 否则本轮管线作废。
