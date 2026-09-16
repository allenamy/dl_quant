> **创建:** 2026-09-16 04:1xZ | **Session:** lead(修复纲领 CFG-04) | **状态:** **FROZEN**(本文入库的 sha 即冻结点; 先于任何臂差读数) | **作废条件:** 原预注册 `docs/PREREG_chase_restart_2026-09-01.md`(sha256 `1a3f433325ae7509a953ea7ccdce6eeba2e3d88211b68d8e486e2dca12234438`)被替换; 或用户对 §C 另有裁定

# AMENDMENT 1(冻结版) to PREREG_chase_restart_2026-09-01 — 分析人口 · 停止计数 · 敏感性

## A. 采纳对象与范围
**本文逐字采纳草案** `docs/fixprogram_2026-09-13/X_COST/DRAFT_AMENDMENT_chase_restart_population_2026-09-13.md`
(sha256 `acdadd871bd8dccb7df4fed209a539ac852bb8b9f8d0710c2716f8f21a5d7eff`)的 **§1 分析人口 · §2 治疗集与配对资格 · §3 停止规则 · §4 读数与敏感性 · §6 收据**, 不作任何修改。草案原文件保持原字节。

**只改分析人口与冻结停止规则如何计锚**; **不改**: 干预(ARM_WEIGHTS 0.5/0.5, salt v2)· 估计量(锚内配对 E[H−X], 锚簇自举 CI95)· H 与 X 的定义 · 三个预注册子组 · 停止规则本身(n*₂ = 100 个实验锚 或 30 天, 先到为准)。

**要点复述(便于执行, 以草案原文为准)**: 单位 = (锚 a, 名 s) 且 s ∈ `chase_experiment.randomised_over`;
锚级排除 X-A1 非 in_sample · X-A2 `opening_halted` · X-A3 REBUILD(ρ_pre < 0.50, ρ_pre 由 attempt-1 maker 首行的 `prev_w` 求和) · X-A4 非本锚 `rebalance_id`(FLATTEN 批);
名级排除 X-N1 退出名(`target_w == 0.0`) · X-N2 受约束名(`clamped_after_reshape.names ∪ forced_flat_names ∪ external_book.held_exit`) · X-N2b(从 `anchor_runs.log` phase-A 行解析 `untradable_held.reduced`, 次级来源, 缺行则标 unobservable 并保留该锚)。
全部排除只用「臂门运行之前已固定」的信息, 故臂的可交换性保持。n*₂ 计**可配对锚**, 30 天日历钟 09-01 16Z → 10-01 16Z, 停机不延长; 停止点读数一次, 同时并印修正前(按 `in_sample`)的计数。

## B. lead 的已读数声明(冻结时必须给, 与 CFG-06 同规)
草案 §0 的起草者声明: 未按臂也未合并计算过 H, 未计算过 X, 未加载任何价格 / 中价 / markout 字段; 只看过 X-COST 的成本侧逐臂名义、费用与计数(原 PREREG 明确允许「监控只看成本上界与臂平衡」)。

**lead 于 2026-09-16 04:0xZ 复核(只读, `grep chase_arm` 全仓 + 逐装置读码)**:
- 09-01 16Z 之后**未发现任何 H−X(臂差结果)读数**。已见的逐臂量只有三类, 全部落在原 PREREG 允许的「成本上界与臂平衡」内:
  1. 每锚深查 / 飞行日志: `chase 87 / no_chase 81 / chase_forced 16`(臂平衡计数)与治疗集行数、残差名义(如 09-11 04Z「治疗集 = skipped_no_chase_arm 16 行 / 残差 1,212U」)。
  2. X-COST `RESULT_X_COST.md`: chase 实验臂对 taker 份额的贡献 +4.3531 pp、chase_forced +2.4401 pp、以及 09-13 12Z 重建锚 no_chase 缺口 6,979 USDT = gross 3.0%(成本侧)。**按独立复审 FXR-DOC-2 的更正, 这两个 pp 是「已成交桶份额」, 不是关实验后的反事实。**
  3. T5b `devices/t5b_exec.py:156` 只用 `has_no_chase` 作布尔特征, 无结果量。
- **结论: 草案 §0 的声明在 lead 复核下成立**, 停止规则与 W 窗不动(与 CFG-06 不同, CFG-06 的同类声明已被推翻)。

**前向盲态(立即生效, 与 CFG-06 冻结版 AMENDMENT 1 同一条)**: 到停止点读数产出前, 每锚深查与飞行日志**只报臂平衡与成本上界**, **不得报任何逐臂结果量**(逐臂成交价差 / markout / 净成本 / H 或 X 的任何形式)。

## C. 随包上交用户的裁定项(lead 不代为决定; 草案 §5 的三选项)
从空仓重建的锚上, 执行器目前仍然随机化。09-13 12Z 上 no_chase 臂把 **6,979 USDT(gross 的 3.0%)** 留到下一锚未成交; 倾斜中止守卫没有触发, 因为它测的是 no_chase 臂的**净额**而不是毛额。本修订只把这类锚移出**分析**, 代码仍在那里付未成交毛额的代价却产不出可用证据。

| 选项 | 内容 |
|---|---|
| (a) | 把 REBUILD 作为 `plan_experiment` 的第四个 `excluded_because` 理由(重建锚上所有名都追单) |
| (b) | 维持现状(继续随机化) |
| (c) | 只排除 RESUME, 保留 STEP_UP |

**独立复审(9f6384fb §8-1)的建议, 随包一并上交**: 「**保留原随机对照在其原来定义的常态调仓人口; 把重建锚单列新层 / 暂停纳入原主判。若运营上需要更快建立敞口, 应成为明确的重建策略, 不能根据重建后的已知收益择臂。止损 / 保护性退出按已经批准的退出合同, 不能跟 alpha 实验人口混在一起。**」——该建议对应 (a) 或 (c) 作为**运营策略**决定, 而不是把它当成实验臂的选择; lead 不替用户选。

**lead 的补充事实(给用户决策用, 不含臂差)**: 09-01 16Z 以来符合 X-A3 的非停机重建锚共 4 个(09-03 16Z STEP_UP ρ 0.257 入金 · 09-07 04Z RESUME ρ 0 · 09-10 00Z RESUME ρ 0 · 09-13 12Z RESUME ρ 0), 相对 100 个可配对锚的目标计数占比很小 ⇒ **无论选哪个选项, 对 n*₂ 的进度影响都不大, 差别在于那 4 个锚上是否继续付未成交毛额的代价**。

## D. 与 E4/R2′ 的交接(逐字沿用草案)
从 FX-EXEC 的 E4/R2′ 移除上线的第一个锚起(其部署收据点名该锚), 代码内的排除为准; 读数仍对每个锚施加 X-N1/X-N2, 并对交接后的锚断言「被 X-N1/X-N2 移除的单位都不在 `randomised_over` 内」, 不符即逐个列出并排除, 永不静默接受。
**已知缺口 G1**(clamp 的 `reduced` 名与场所上限 reduce-only 名不写账本)与对 E4/R2′ 的请求(在订单行写逐名 `reduce_only` 标志, 或在 `chase_experiment` 里写 `reduce_only_names`)一并保留。
