# FP3 P-C 设计 v2: 执行器书层作为纯函数(决策前可见状态 → 逐名下单意图)— 2026-09-18

> **创建:** 2026-09-18 06:0xZ; **v2 06:4xZ**(按独立复审第八轮 38e77212 三处缺口重写; v1 原字节在 git 517b7a5d) | **Session:** b9646a9e(主研究员) | **状态:** 设计(生产步骤顺序已按原代码核实; 装置未写) | **作废条件:** 执行器书层代码路径变更; 复审否决 §3
> **v1 的三处错误(复审指出, 已用生产原函数核实)**: ① 步骤顺序写反——生产是**先**扣留/止损集与小额过滤、**后**整形(v1 写成先整形后小额), 反例: 本应剔除的小多头经去均值变成可交易空头; ② 验收对象错——anchors 行没有逐名目标, 只有哈希与总额, 且「差一个最小名义」的容差会放过「该平 100 只平 95.1」; ③ 决策前状态缺证——daily_nav 是交易后快照; 止损冷却名单不在锚级记录里; 张数、估值、下单价必须分开。

## 1. 生产代码里的书层顺序(执行器树 409ea16, `scheduler/anchor_loop.py`, 只读核实)
| 步 | 位置 | 输入 | 输出 |
|---|---|---|---|
| 1 目标向量 | L1870 `EXT.target_vector(external, symbols)` | target_live/<A>.json | w(执行器符号表) |
| 2 定规模 | L1978 `_size_book(target_leverage=gross_mult)` | **决策时权益** eq、gross_mult 2.0、sigma_ladder g(缺省 1.0) | 目标名义 = w/gross_norm × eq × gross_mult; anchors 行 `target_gross` = eq × gross_mult × g |
| 3 扣留集 | L1832–1841 `PNS.active_sets(PNS.load_state(), now)` + `_universe_gate`(不可交易、场所元数据排除) | 逐名止损 stop/cooldown 集、不可交易集 | 撤名(pop)清单 |
| 4 小额过滤 | L2028 `EXT.below_min_notional(target, floors, min_notional_mult)` | 场所 min_notional × 倍数 | `_ext_dust`(skipped_min_notional) |
| 5 整形 | L2042 `apply_withhold_and_reshape` → L414 `LG.reshape_after_withhold(vec, sizing_gross, redemean, rescale, floors_usdt, strict=True)` | 撤名后的向量 + floors | 去均值 + 毛额恢复后的向量(报告 names_crossed_floor) |
| 6 意图 | 订单构造(maker / chase 分臂) | 决策前持仓(张数 × 决策价) | 逐名 `intended_notional`(orders.jsonl 每单一行, 含 target_w / prev_w / mid_at_anchor / price_submit / terminal_reason) |

## 2. 纯函数合同(v2)
`intent(A, target_file, eq_decision, pos_qty_pre, mid_at_anchor, floors, stop_sets, withheld, cfg) → {intended_notional[name], skipped[name→reason], reshape_report, gross_target, gross_intent}`
- **执行器自己记录的决策前量, 逐项来源**: `eq_decision` = anchors 行 `target_gross / (gross_mult × g)`(执行器定规模用的权益, **不是** daily_nav 的交易后快照); `mid_at_anchor` = orders 行逐名字段(决策价, 与 `price_submit` 分开); `pos_qty_pre` = 上一锚 `position_readback`(张数)在期间无 fills/保护平仓/人工更正时直接用, 有事件按 fills 推进张数, 推不出 ⇒ `UNAVAILABLE_STATE`(不猜); `prev_w` = orders 行字段(执行器自己算的决策前权重, 用作 pos_qty_pre × mid 的**核对**, 不作输入); `floors` = `exchange_info_cache.json`(min_notional / step / tick; 历史锚用当时快照, 无快照 ⇒ 标缺证); `stop_sets` = 决策时 stop/cooldown 名单——phase_C 只记 `cooldown_n` 与 counters, anchors 行的承载字段见 §4 待核, **无名单的锚标 `UNAVAILABLE_STOPSET`**, 不用当前 `per_name_stop.json` 倒推; `withheld` = anchors 行 `known_gaps.names` 与 external_book 的排除记录。
- **顺序与生产一致**: 定规模 → 扣留/止损集撤名 → 小额过滤 → 整形(带 floors) → 张数取整(step)→ 意图名义。同码: `signal.legs.reshape_after_withhold`, `live.external_book.{target_vector,below_min_notional}`, `live.per_name_stop.active_sets` 直接 import; 编排复制自 anchor_loop 并附行号对照表。
- **锚后回读只验输出**: 意图 vs 实际(fills / anchors realized_gross)之差归执行层, 不回灌。

## 3. 判据(v2)
- **P-C1 逐名意图重现**: 验收对象 = `orders.jsonl` 逐名 `intended_notional`(含 `skipped_min_notional` / `skipped_no_chase_arm` 等终态行); 容差 = **场所张数步长 × 决策价**(取整误差), 不是一个最小名义; 每个不等的名归因到 §1 的某一步或标缺证; 目标 0 不可归因差异。
- **P-C2 层分解**: 09-06 / 09-09 / 09-12 止损日与 09-16/17: 生产者目标 → 意图 → 实际三列(毛额、净额、逐名), 止损/撤名/整形/小额各自贡献。
- **P-C3 反事实(只读)**: 同一函数下, 逐名止损分母改「相对开仓价」、「两锚确认 → 一锚」的意图差与回放记账影响(完整组合对照)。研究, 部署走预注册 + 用户字。
- **顺序**: 先在**状态完整的新锚**(09-18 04Z 起, 逐锚有 orders 逐名行 + readback + phase_C)上过 P-C1, 再向历史回补; 缺状态的历史锚只报缺证, 不为它无限重跑。

## 4. 待核与工作量
- 待核: anchors 行承载止损集的字段名(L1839 注释「anchors 行的 per_name_stop 字段承载」, 首次读 04Z 行未见同名键; 可能在 `external_book` 子键或 `known_gaps`); sigma_ladder g 的逐锚记录位置。
- 工作量: 对照表 + 纯函数 0.5 d; P-C1 新锚(4–6 锚)0.25 d; 历史回补 + P-C2 0.5 d; P-C3 0.5 d; 独立复审。
