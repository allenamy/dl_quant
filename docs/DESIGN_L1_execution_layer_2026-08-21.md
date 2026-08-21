> **创建:** 2026-08-21 | **Session:** 护城河推进(执行线) | **状态:** 基线已跑: 经济子集 AUC 0.59, G1 不过 ⇒ 退化为分档经验表; 建模需盘口状态(见 RESULT §O) | **作废条件:** 基线 AUC<0.60 且经济换算 <+0.3 bps/锚 ⇒ 关闭 L1(转纯经验规则)

# L1 执行层设计: p(fill) / markout 预测 → 挂单价位·尺寸决策

## 0. 为什么是它(受据)
maker 滑点实测为负(−2.23 bps, 近乎免费)= 执行是现有护城河; 宽书 P3: 薄币成交率决定净夏普 **1.27(b)vs 2.32(a)** = 一个夏普点的选择权; LOB 三线里 L1 EV 最高; 全宇宙 LOB 采购待定 ⇒ **先用自有实盘数据**(无需采购)。

## 1. 数据(已在手, 2026-08-01→08-21, 21 天)
- `orders.jsonl` 19,259 笔: placement_arm/eps, spread_at_submit_bps, mid_at_submit, mid_at_anchor, intended_notional, filled_notional, avg_fill_px, first/last_fill_ts, cancel_ts, terminal_reason, order_type(maker 13,758 / topup_taker 5,080 / protective_flatten 398), attempt_idx, fee。
- `fills.jsonl` 9,258 行 → 去重 6,953 trade_id(★合并不丢弃: markout 只在回填副本); 2,305 行带 `mid_at_fill_plus_60s`。
- `position_readback` 标记价/数量; 5m 面板: qv 流动性档、短窗波动/振幅(因果)。
- 薄币探针 events.jsonl(482 状态, base/xl 两臂): 外推到 K400 薄尾的独立样本。

## 2. 目标与特征(全部因果, ≤挂单时刻)
**目标**: (a) 全成交 1{filled/intended ≥0.99}; (b) 成交分数; (c) 成交条件 markout_60s(有利为正)。
**特征**: spread_at_submit_bps; placement_eps(挂单离 mid 的偏移); 名义/ADV 与流动性档(qv4h 三档); 挂单前位移 (mid_submit/mid_anchor−1) 及其与 side 的同向性(逆势挂单 vs 顺势); 时段(UTC 小时 sin/cos); 近 24h 波动与振幅; funding 符号×side; attempt_idx; symbol 固定效应(仅 ≥50 单的名字)。
**禁止**: 任何挂单后信息; markout 只作目标不作特征。

## 3. 模型与验证(判据冻结, 先于看数)
- 基线: 逻辑回归(标准化) vs LGBM 小树; **按日滚动 CV**(训练日 < 测试日, 至少 7 天训练, 10 天测试), 报 AUC / Brier / 校准(十分位); 子集: maker 单 only, 分流动性档。
- **门 G1**: OOS AUC ≥ 0.60 且按日稳定(≥7/10 测试日 AUC>0.55) —— 否则 p(fill) 不可建模, L1 退化为"分档经验成交率表"。
- **门 G2(经济换算)**: 用校准后的 p(fill|eps,档) 做 eps 决策(每名每单选 eps 最大化 E[fill]×edge − 不成交残差 taker 成本), 离线反事实 ≥ **+0.3 bps/锚** 才进第二阶段(否则收益不足以冒结构改动)。
- **门 G3**: markout 模型 OOS Spearman ≥ 0.10 才进入尺寸决策; 不过则 L1 只管 eps 不管尺寸。
- 泄漏自检: 乱序 eps 空值、按日 embargo、特征时间戳重导。

## 4. 用途(按阶段)
① eps 每名每锚自适应(替代全局 ε-bandit 常数); ② 尺寸: 低 p(fill) 名字降低目标调整量(执行可行性感知再平衡, 与 RB 同向不冲突); ③ 宽书 λ 快层预算与成本情景(a/b/c)的数据化选择; ④ 探针薄尾外推。
## 5. 首跑(基线判官 l1_fill_baseline.py)见 RESULT 追加。
