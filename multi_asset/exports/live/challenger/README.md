# Challenger 双轨 (腿权重) — 预注册判据

> **创建:** 2026-07-25 JST | **Session:** multi-asset-v2 (0B) | **状态:** live (随 run_daily 每日跑)
> **作废条件:** 权重方案变更; 或达成下方任一裁决条件后
> ⚠ **判据在见到任何影子数据之前冻结。见到结果后不得修改本文件的判据段。**

## 为什么有这条轨

0C 的腿权重复审: **king=0.30 是被支配的选择** —— king→0.50 在同口径下 Sharpe 10.16→12.58, 年化/gross 120%→172%, 且**最差年 / 最差月 / 最大回撤 / 负日占比同时改善**。五重证伪全扛住 (逐年 5/5、bootstrap CI [+2.21,+3.44] 排 0、walk-forward 自 2023 起年年选 king-重配、成本 0-12bps 无交叉、king IC 罚到只剩 30% 时最优仍是 0.50)。

**但那五条全是回测。** 0C 自己标出的唯一缺口: **权重层面没有任何真正的样本外验证。只有 shadow 能关掉它。**

## 配置

| 轨 | king | s2 | funding | size |
|---|---|---|---|---|
| **champion** (pilot 起步仍用这套) | 0.30 | 0.10 | 0.30 | 0.30 |
| **challenger** | **0.50** | 0.17 | 0.17 | 0.16 |

**同一信号、同一锚点、同一执行假设 (maker-fill: fill-rate 0.51, 成本 1.9bps 平静 / 2.9bps 压力, 按 BTC rvol>18bps/min 判定), 只有腿权重不同** ⇒ 差异可完全归因于权重。

**四条腿全留** —— 0C 的结论是三条各自 ~0 的腿彼此互补, 合计贡献 +2 Sharpe。这里调的是配比, 不是删腿。

## ★ 预注册判据 (冻结)

**(a) 日 P&L 方向** — `criterion_a_daily_pnl_direction`
胜率 (challenger 日净值 > champion 的天数占比)、累计净值、日频 Sharpe。
> 支持切换: 胜率持续 >0.55 **且**累计差为正。反对: 胜率 <0.45。

**(b) rank-IC 差** — `criterion_b_rank_ic`
逐锚 `challenger_ic − champion_ic` 的均值与 t 值; 另有 C4 `RetrainTrigger` (margin 0.003, persist 20) 的切换信号计数。
> 支持切换: 平均 ΔIC > 0 且 t > 2。反对: ΔIC < 0。

**(c) funding 腿压力日尾部** — `criterion_c_funding_leg_stress_tail`
0C 发现**全书最肥的左尾是 funding 腿自己造的** (FTX 日 solo-funding −0.98% ≈ 全书 −0.94%)。challenger 持有更少 funding (0.17 vs 0.30), **理应在这条尾巴上受伤更小**。
> 支持切换: 在 funding 腿最差 5% 的锚点上 challenger 净值优于 champion。**若不优于, 这是反对重配的证据** —— 因为那意味着 king 的集中带来了新的尾部风险。

**裁决**: 三条判据同向 + 至少 60 个交易日样本, 才提请切换。**不满足则维持 champion。**

## 纪律

- **不改 canonical**, 不改 pilot 默认权重 —— **pilot 起步仍用 champion**, 等影子对照方向一致再谈切换。
- 本模块是**加法**: 独立文件 + `run_daily.sh` 里的**非致命步骤**, 失败不会影响 champion 主链。
- 口径: **影子 paper P&L, 不是基金净值**。两轨共用同一执行模型, 所以**有意义的是差值, 不是任一绝对水平**。

## 一个已知交互

challenger 换手 +39% (1457→2027)。这使 **`exports/eda/min_notional_band.md` 的 band 分析对 challenger 更重要**: 实测 band 削换手对高换手配置的相对收益更大 —— 在 8.34bps 成本下 challenger 的最优 band 值 **+1.41 Sharpe** vs champion 的 +0.85。**若最终走 taker 路径, band 会进一步放大 king-重配的优势。**

## 产物

```
exports/live/challenger/
  positions/positions_YYYYMMDD_HH.json   challenger 仓位 (schema 与 champion 完全一致)
  pnl_daily.csv                          两轨逐日净值 + 累计
  compare.json                           三条判据的全部数字
  daily_report.md                        当日一页纸
```
