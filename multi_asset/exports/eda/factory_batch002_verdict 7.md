> **创建:** 2026-07-20 JST | **Session:** fable multi-asset-v2 (0C 独立评分) | **状态:** final | **作废条件:** 书重建 / net-cost 口径变
> 对象: batch_002 4 CANDIDATE (M=275, 新 rng)。独立复算 `exports/eda/batch002_step{1,2}.py`。

# 工厂 batch_002 — 0C 独立评分终判

## 判词: **0 进书** (诚实先验 holds)。**★ 关键发现: I15 (靶心) 有全部好属性 —— 容量原生+跨年稳+因果干净+IC 层加书正 —— 仍净成本死。答案: 容量原生不充分, +0.003 正交 IC 转不成 net-Sharpe。** 低波簇 = 1 腿冗余+容量限+2025 regime dip, 净成本更差。

## 等价性 (你的硬前提, ts 算子) — **全 4 PASS**
独立慢参考 (显式递归 ema + rolling ts_std 走**全历史**, xsec_z 走 **member&CL** = 匹配已修 dsl): inc-IC 与台账**逐值吻合** (c247 .01456/.01457, c248 .01685/.01685, c250 .01718/.01721, c251 .01488/.01487, diff <3e-5), **逐锚 rank-order Spearman = 1.000000**。xsec-归一修复生效 (I15 的 mul-inside-xsec_z 单-xsec_z rank 不变, 无 id101 伪影); ts 向量化正确。

## 逐候选

| id | 公式 | 判 | 依据 |
|---|---|---|---|
| **247 (I15)** | xsec_z(mul(ema(ret_4h,24), neg(rvol_6h))) | **ARCHIVE** | net-cost (§I15) |
| 248/250/251 | neg(xsec_z(ts_std/ema-rvol/ema-\|ret\|)) | **ARCHIVE** | 1 腿+容量+净成本 (§簇) |

## §I15 (247) — 靶心, 最接近的一次, 仍净成本死 ★

I15 有 batch_001 A 组缺的一切:
- **容量原生**: large-DVOL 半 IC **0.0396 ≥ small 0.0337** (信号在**可交易大币**, 非流动性尾)。A 组是反的 (small 0.052 > large 0.034)。
- **跨年稳无衰减**: semester inc-IC 2025H1 .018 / **2025H2 .021 (最强)** —— 2025 是它最好的, 零 non-stationarity。
- **因果干净**: forward-decay {−2 −.47, −1 −.37, **0 +.036**, +1 +.020, +2 +.018} —— 峰 lag0 + 前向缓降 + 负-lag 大负 (reversal, 非泄漏)。
- **IC 层加书正**: lam0.1 Δrank-IC **+0.0033 逐年全正** (.0021-.0044)。distinct from 低波簇 (corr 0.30)。

**★ 但 net-cost decider 死**: 书 net-Sh@1.9 **12.35** → 书+247 **12.19 (−0.16)**; @5.0 8.57→8.47。**+0.0033 rank-IC 不转 net-Sharpe** (换手 0.617→0.623 微升, gross 未净增)。
**⇒ 答你的关键问: 容量原生 ≠ 能转 net-Sharpe。** 症结不(只)是容量 —— **一个弱 (+0.003) 正交因子小权重加到 Sharpe-12 的书上, 结构上净贡献 ~0** (rank-IC 改善在截面中段非 L/S 极端仓; 书已近风险调整最优, 弱第五腿挣不到位置)。**这是 batch_002 最接近的一次** (net-cost 平非强负, 容量/稳定/因果全绿), 但仍 ARCHIVE —— 候选须**挣到** net-Sharpe 增量, 平到略负不够格。(注: 更精的风险模型/优化器**或**能榨出边际, 但那超预注册固定-权重门且加拟合风险; 按门 ARCHIVE。)

## §低波簇 {248,250,251} — 1 腿, 容量限, regime dip, 净成本更差

- **≈1 腿非 3**: 互 |rank-corr| **0.936/0.872/0.843** (齐测已实现波动)。书判最佳一条 (250)。
- **容量受限**: 三者 small-DVOL 半 IC (0.049-0.053) > large (0.031-0.036) —— 信号在流动性尾 (同 A 组死因)。
- **2025 regime dip (你要的 causal 复核)**: 250 semester 2024H2 .017 → **2025H1 .0068 (塌半)** → 2025H2 .015 (部分回)。**非单调 drift、非纯伪影 —— 是 2025H1 特定 regime 已实现波动因子失效, H2 部分恢复。真 non-stationarity 信号 (vol 因子对 regime 敏感), holdout 前危险。**
- **net-cost 更差**: 书+250 net-Sh@1.9 **11.58 (−0.77)** / @5.0 8.11。
⇒ 三重死 (冗余簇 + 容量 + 净成本 + regime 不稳)。ARCHIVE 全簇。

## 给汇报

**batch_002: 0 进书, 但比 batch_001 更有信息量。** I15 是靶向设计的胜利 (容量原生+跨年稳+因果干净, profile 确实比 A 组干净得多) —— **但净成本 decider 揭示更深的墙: 书在结构 Sharpe 12 已近最优, 一个弱正交 IC 增量 (+0.003) 无论多干净/多容量友好, 小权重下不转 net-Sharpe。** ⇒ **工厂要进书, 需要的不是"更干净的弱因子", 是"net-Sharpe-additive 的强因子" (inc-IC 门槛远高于 +0.003, 或需与书低相关的强独立 sleeve)。** 诚实先验 (0 进书) 连续两批 holds; 但 I15 证明靶向 (容量+稳定) 有效——下一步该靶向**净-Sharpe-additive** (强度 + 组合极端仓贡献), 非只 inc-IC/容量。逐候选: 247 ARCHIVE (net-cost, 最接近), 248/250/251 ARCHIVE (簇/容量/regime/net-cost)。

---
**产物:** `exports/eda/batch002_step{1,2}.py` · `/tmp/0c_b2_step{1,2}.json` · `factory_batch002_verdict.md`。
