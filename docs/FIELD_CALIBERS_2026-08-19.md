> **创建:** 2026-08-19 17:0xZ | **Session:** 6737834a | **状态:** 活文档 — 任何钱口径字段【首次引用前】先查此表, 表里没有的先读生产代码再补行 | **作废条件:** 字段生产代码变更

# 钱口径字段词典(net_over_equity 误读事故的结构性堵漏)

| 字段(表) | 生产处 | 口径(逐字/摘要) | 合法用途 | 禁止 |
|---|---|---|---|---|
| net_over_equity / net_over_gross (anchors) | scheduler/anchor_loop.py:76 neutrality_from_snapshot | **净敞口快照**=场所持仓带号名义和÷权益; "a SNAPSHOT, not a P&L" | 中性度监控 | **当盈亏引用(08-19 事故)** |
| equity_delta_since_prev (daily_nav) | anchor_loop.py:2137 | eq−prev_nav; "P&L ONLY IF 无出入金" — 条件随行携带于 external_flow_usdt | 与 external_flow=0 联用=逐锚真盈亏 | 不核 external_flow 直接当盈亏 |
| external_flow_usdt (daily_nav) | 同上 | /fapi/v1/income TRANSFER since 00:00Z | 出入金排除 | — |
| nav (daily_nav) | 同上 | totalWalletBalance+totalUnrealizedProfit (/fapi/v3/account) | 权益标记、停机线基准 | — |
| funding_paid (funding) | live/binance_funding.py:198 | 场所 income 行原值; **正=入账(收), 负=出账(付)**; §3f 符号自检在案 | 资金费现金流 | 反号表述("付"须对应负值) |
| position_notional_at_settlement (funding) | 同上:196 | 自家读回记录, "never derived from paid"(防符号自证) | 资金费定价 | 用 paid/rate 反推 |
| realized_gross (anchors) | order-derived (realized_gross_source 字段自述) | 已实现毛敞口(非盈亏) | 规模跟踪、入金 resize 侦测 | 当盈亏 |
| gross_bps/net_bps/carry_bps/cost_bps (shadow_log score) | wide_shadow/shadow_loop.py:307-328 | 上一锚仓位×y4 结算; Δ==4h 守卫; **已独立重算验真(08-19: −9.48 vs −9.21)** | 影子逐锚盈亏 | — |
| val/idx/members (shadow weights npz) | shadow_loop 存档 | 持仓权重向量(NAV 份额), Σ\|w\|≈gross_pos | 持仓重建、独立验真 | — |
| placement_eps / placement_arm (orders) | live/binance_executor.py:1438 | eps=配置回声常量 0.1; arm=赌博机实抽样 | 赌博机健康=看 arm 分布 | 用 eps 判活性 |

**流程铁律**(memory measuring_a_misunderstood_quantity 第五例): ① 字段首引先查本表, 无则读生产代码+行内 caliber 再补行; ② 机制与数字吻合只是线索, 验证必须第二台独立仪器; ③ 盈亏断言唯一合法源 = daily_nav(equity_delta+external_flow 联用)或已验真的 score 行。

## equity_delta_since_prev(daily_nav.jsonl)— 2026-08-21 第六例误读后补录
**语义 = 当前权益 − 前一日最后一行权益 = 当日累计**(anchor_loop.py:2175, prev=_prev_nav 跨日取 rows[-1])。同日多行是"当日进度快照", **绝不可把同日各行相加**(会双重计数)。日总额 = 当日最后一行; 逐锚差 = 相邻行之差。误读后果实例: 08-20 真实日亏 −174.7(−1.08%), 我按行相加报了 −376→−612(夸大 2-3.5×)。realised_pnl 字段(/fapi/v1/income)才是日实现盈亏权威源。
- [待查 2026-08-21] orders.jsonl fee_all_usdt: 21天 maker 合计 1,830U / taker 525U 对名义隐含 127/155bps, 量纲不可信(费率表 2/5bps); 未定前禁止用于成本核算
