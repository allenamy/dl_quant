# FP3 D 设计: 独立现金核账引擎(生命周期, 08-01 至今)

> **创建:** 2026-09-17 16:3xZ | **Session:** b9646a9e(主研究员) | **状态:** 设计(事实表已备, 装置未写) | **作废条件:** 账本字段语义与本文 §1 不符; 或独立研究员否决 §3 判据
> **目的:** 回答「成本预估真实吗」与「实盘到底赚/亏了多少、钱去哪了」——用**只读**账本重建逐锚仓位与现金, 与场所真值(仓位回读、日 NAV、收入流水)逐项对账, 不用任何策略层数字。

## 1. 事实表(收据 `FP3_receipts/LEDGER_CENSUS_2026-09-17.json`, 账本 `dl_quant_live/state/live/pilot_log/<day>/`)
| 账本 | 行数(48 天) | 关键字段 | 陷阱 |
|---|---|---|---|
| fills.jsonl | 116,400 行 / **50,977 个 trade_id** | trade_id, symbol, side, fill_px, fill_notional, commission, commission_asset, fill_ts, anchor_ts, venue_maker_flag, supersedes_trade_id, backfilled_utc | 65,423 行是标记回填的重复(同 trade_id 多行): **按 trade_id 取最新一行**(backfilled_utc 最大), 不得求和 |
| orders.jsonl | 89,158 | intended_notional, filled_qty/notional, avg_fill_px, mid_at_anchor, mid_at_submit, fee_all_usdt, fee_assets, placement_arm, order_type | 成交额 `filled_notional_source` 有已知/未知之分(`filled_unknown_*`) |
| funding.jsonl | 41,428 | settlement_ts, symbol, funding_rate, funding_paid, position_notional_at_settlement, funding_interval_h | 2 行 interval 来源 UNKNOWN; position_read_age 可达 3 h(结算时仓位是**回读推算**, 非场所结算行) |
| position_readback.jsonl | 57,060 | anchor_ts, symbol, venue_position_qty/notional, source(`fapi/v3/account@post_anchor`), read_ts | 场所真值, 每锚锚后一次 |
| daily_nav.jsonl | 282 | nav, wallet_balance, margin_balance, unrealised_pnl, realised_pnl(= /fapi/v1/income 当日 REALIZED_PNL+COMMISSION+FUNDING_FEE), realised_by_type_asset, external_flow_usdt | realised 为**场所 income 流水**, 是第二真值; BNB 计价手续费另列 |
| anchors.jsonl | 281 | venue_gross_usdt, venue_net_usdt, realized_gross, target_gross, external_book.{json_sha,weights_sha,f10_sha} | 非净序列(回填/重跑行), 按 anchor_ts 桶取最后一行 |

手续费资产: USDT 63,742 行 / **BNB 52,658 行** ⇒ 现金口径必须把 BNB 手续费换算成 USDT(orders.fee_all_usdt 已含换算; 引擎复算用成交时刻 BNBUSDT 中价并与 fee_all_usdt 对账)。

## 2. 引擎(只读, 逐日可重跑, 自报输入 sha)
1. **成交去重** → 逐名逐锚净成交 qty/notional/手续费(USDT 化)。
2. **仓位重建**: pos_t(name) = Σ 成交 qty 到 t; 与 `position_readback` 锚后真值逐名逐锚比: 差 = 未记账成交(拒单后实际成交、手工平仓、强平)。判据: |Δqty|·px ≤ 1 USDT 视为一致; 不一致逐名列出并对到 orders 的 `filled_unknown_*`。
3. **现金分解**(逐锚): 已实现盈亏(按重建仓位 + 成交价, 加权平均成本法) + 手续费 + 资金费(funding.jsonl 逐结算) + 未实现变动(锚后 mark)。
4. **与场所对账**: (a) 日: Σ 逐锚 = daily_nav.realised_by_type(三类各自对), 允差 = 场所 income 与本地 fill 时间戳跨日归属; (b) NAV 走: nav_d = nav_{d−1} + realised_d + Δunrealised_d + external_flow_d, 残差逐日列出; (c) 资金费: funding.jsonl 日和 vs income FUNDING_FEE 日和(已知 position_read_age 偏差 ⇒ 预期有残差, 量化它)。
5. **真实成本表**(用户问题 3): 逐锚 手续费 bps/成交额, 滑点 = (avg_fill_px − mid_at_anchor)·方向 bps, maker 占比, 换手 = Σ|成交额|/(2·NAV); 与回放的 COSTB 档(≈2.2 bps, maker 0.85)并排 ⇒ 成本低估倍数。

## 3. 输出与判据
- 收据 `FP3_receipts/CASH_RECON_<from>_<to>.json`: 逐日残差表 + 逐锚成本表 + 未记账成交名单; VERDICT = RECONCILED 仅当 (a)(b) 全日残差 < max(2 USDT, 0.5 bp·NAV) 且未记账成交为空; 否则 PARTIAL 并具名。
- 不改任何账本; 修补账本仍走既有「副本过看门狗」纪律。
- 与 FP2-8 数字的接口: 回放成本假设 vs 真实成本表 ⇒ 给出「同一换手下的净额修正」, 只作限定不改判决。

## 4. 顺序与 ETA
装置 + 夹具(去重/换算/仓位重建各一负控)1 天; 真实跑 + 残差归因 1 天; 与 F(K3 细化)共用成本表。
