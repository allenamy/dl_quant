# FP3 P-C 设计: 执行器书层作为纯函数(决策前可见状态 → 下单意图) — 2026-09-18

> **创建:** 2026-09-18 06:0xZ | **Session:** b9646a9e(主研究员) | **状态:** 设计(入口已定位; 装置未写) | **作废条件:** 执行器书层代码路径变更; 复审否决 §3 判据
> **回答**: 复审 r7 §7-2 / r7b §7-2 / r7c: 「目标经过实际限额、止损、冷却、舍入等规则后究竟形成什么下单意图; 规划只能用决策前可见持仓, 不能拿锚后回读初始化」。P-B 给了生产者目标(近似重现); P-C 把**执行器**这一层也变成可回放的纯函数, 才能把「实盘 21 天 3 次止损 vs 回放 1,523 天 1 次」分到层。

## 1. 生产代码里的书层(执行器树 409ea16, 只读)
| 步 | 位置 | 输入 | 输出 |
|---|---|---|---|
| 1 目标向量 | `scheduler/anchor_loop.py` L1870 `EXT.target_vector(external, symbols)` | 生产者 target_live/<A>.json(P-B 已可重现) | w(829 轴对齐到执行器符号表) |
| 2 定规模 | L1978 `_size_book(target_leverage=external["gross_mult"])` | NAV(决策前账户权益)、gross_mult 2.0、sigma_ladder g(失效安全 1.0) | 目标名义 = w/gross_norm × NAV × gross_mult |
| 3 场所扣留 + 整形 | L414 `LG.reshape_after_withhold(vec, sizing_gross=g, redemean, rescale, floors_usdt)`(蓝本 `signal/legs.py` L124) | 不可交易/元数据排除名(`venue_meta_exclusions`)、逐名止损集(`per_name_stop.active_sets(state, now)`)、冷却集 | 去均值 + 毛额恢复后的向量(★ 这一步把被止损名钉住——在案) |
| 4 最小名义 | L2028 `EXT.below_min_notional(target, floors, min_notional_mult)` | 场所 min_notional × 倍数 | 跳过名单(`skipped_min_notional`) |
| 5 场所上限钳 | L2323 `venue_cap_clamp` | 场所逐名上限、杠杆档 | 钳后名义 |
| 6 意图 | 订单构造(maker / chase 分臂, 分配规则 `sha256('{seed}|chase_arm_v2|{symbol}')`) | 决策前持仓(上一锚锚后回读, 期间无事件时) | 逐名意图差额 → 订单 |

## 2. 纯函数合同
`intent(A, target_w, nav_pre, pos_pre, mids_pre, exinfo_pre, stop_state_pre, cfg) → {intent_notional_by_name, skipped:{reason}, withheld:{reason}, reshape_report, gross_target, gross_intent}`
- **全部输入必须是决策前可见的**: `pos_pre` = 上一锚锚后回读**仅当**期间无成交/保护性平仓/人工更正(用 fills/orders/anchors 账本判定; 有事件则按事件推进状态, 推不出的标 `UNAVAILABLE_STATE`); `nav_pre` = 该锚开始时的权益(daily_nav/anchors 记录里锚开始的 NAV, 不是锚后); `stop_state_pre` = `per_name_stop.json` 在该锚决策前的快照(现只有当前文件 ⇒ 历史锚需从 anchors.jsonl 的 stop 计数字段重建, 重建不出的标缺证)。
- **锚后回读只用于验证输出**: 意图 vs 实际(anchors.jsonl 的 realized_gross、fills)之差归执行层(拒单/部分成交/追单/保护平仓), 不回灌。
- 同码: 直接 import 执行器模块(`signal.legs.reshape_after_withhold`, `live.external_book.target_vector/below_min_notional`, `live.per_name_stop.evaluate/active_sets`), 不重写; 只把 anchor_loop 里的编排复制成一个无副作用的函数(带源码行号对照表, 复审可逐行核)。

## 3. 判据
- **P-C1 同锚重现**: 09-13 起(有完整 anchors/orders/fills 的锚)逐锚: |意图名义 − anchors.jsonl 记录的目标名义| ≤ 该名最小名义; 不等的名逐一归因到 §1 的某一步或标缺证。目标 = 0 不可归因差异(与 P-B 同标准; 达不到就报近似重现 + 未认证)。
- **P-C2 层分解**: 对 09-06 / 09-09 / 09-12 三个止损日与 09-16/17 反转: 生产者目标 → 意图 → 实际 三列的毛额、净额、逐名差; 回答「止损/平仓/整形各贡献多少」。
- **P-C3 反事实(只读, 不改生产)**: 同一意图函数下, 逐名止损分母改为「相对开仓价」(独立研究员 4.3 指出现分母是当前名义 ⇒ 空头需 +42.9%)与「两锚确认 → 一锚」两个变体的意图差, 用回放记账估影响(带完整组合对照, 不单看止损名)。这是研究, 部署要走预注册 + 用户字。

## 4. 工作量与顺序
1. 读 anchor_loop 编排(L1860–2340)写对照表 0.25 d; 2. 纯函数 + 决策前状态重建(有事件锚的推进规则)0.5 d; 3. P-C1 逐锚跑 + 归因 0.25 d; 4. P-C2/P-C3 0.5 d; 5. 独立复审。
不依赖只读凭证(用本地账本; 缺成交的 8 桶平仓日标缺证)。与 Q6 影子实现并行: Q6 用的是同一份决策前状态重建, 先做 P-C 的状态重建再做 Q6 的 E_s。
