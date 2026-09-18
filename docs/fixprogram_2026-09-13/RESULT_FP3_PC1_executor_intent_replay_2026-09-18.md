# FP3 P-C1 结果: 执行器书层作为纯函数, 在三个状态完整的新锚上**逐名、逐请求精确重现** — 2026-09-18

> **创建:** 2026-09-18 07:5xZ | **Session:** b9646a9e(主研究员) | **状态:** 出数(三锚精确; 历史锚未做; P-C2/P-C3 未做) | **作废条件:** 执行器记录格式或书层代码变更(树 409ea16)
> **合同:** `DESIGN_FP3_PC_executor_book_layer_2026-09-18.md` v3(第九轮复审后)。**装置:** `FP3_devices/pc/pc1_intent_replay.py` v7(只读; 同码 import `scheduler.anchor_loop.apply_withhold_and_reshape`、`live.binance_executor.RebalanceExecutor.plan`、`SymbolFilters.round_qty`、`external_book.below_min_notional`; 与生产树零接触)。**收据:** `FP3_receipts/PC1_<A>_v7.json`(A = 1789675200 / 1789689600 / 1789704000)。

## 1. 输入(全部是执行器在决策时写下的记录; 不用 daily_nav、known_gaps、target_gross/gross_mult 反推)
| 量 | 来源 |
|---|---|
| 交易前权益、定规模毛额 | `anchor_runs.log` phase_A 行 `sizing.nav / sizing.gross`(04Z: 115,439.26 / 230,878.51) |
| 目标权重 | `target_live/<A>.json`(P-B 可重现)÷ anchors 行 `external_book.gross_norm` |
| 扣留集(决策时) | phase_A `untradable_names`(4)+ external_book `held_exit`(7)+ `meta_excluded`(0)+ 逐名止损**冷却**集(`per_name_stop.json` 里「设置时刻 ≤ 锚 < 到期」的名, 6)+ 小额 `below_min_notional`(1) ⇒ 14 = phase_A `n_untradable_withheld` |
| 场所上限钳 | phase_A `venue_cap_clamp.capped`(BUSDT: cap 2,000 × (1 − margin 0.02) = 1,960; 规则复算与记录 `target_after` 相等) |
| 交易前持仓(名义) | orders 行 `prev_w × target_gross`(执行器自己的 `state.positions` 估值; 我用 00Z 回读名义额重估会差 ≤ 330 USDT/名——正是复审第 4 点第三条) |
| 交易前持仓(张数) | 上一锚 `position_readback.venue_position_qty`(plan 的 held_qty) |
| 决策价 | orders 行 `mid_at_anchor` |
| 验收对象 | orders 行 `request_ledger[0].qty`(有账本的请求)/ `intended_notional`(−5022 post-only 拒单无账本)/ `terminal_reason`(跳过) |

## 2. 结果(三锚)
| 锚 | 阶段 A: 整形报告(净/整形前毛额/整形后毛额/最大单名移动) | 阶段 A: 整形+上限钳后目标 vs 记录 target_w×gross | 阶段 B: 请求 |
|---|---|---|---|
| 09-17 20Z | **逐位相同**(−19,508.0684 / 229,386.7383 / 236,135.23 / 0.0834) | **241/241** 在一步之内, max |Δ| 0.0000 USDT | **179/179**: qty 精确 134, 拒单 intended_notional 精确 45, 跳过原因相同 62 |
| 09-18 00Z | 逐位相同(−18,714.9176 / 228,928.0049 / 235,466.04 / 0.0800) | **243/243**, 0.0000 | **190/190**: 141 / 49 / 53 |
| 09-18 04Z | 逐位相同(−17,733.4077 / 224,507.0308 / 230,878.51 / 0.0771) | **243/243**, 0.0000 | **227/227**: 163 / 64 / 16 |
不设「一手」容差: 数量按 step 取整后**相等**, 方向相等, 阶段 = 首请求(attempt 0)。

## 3. 归因阶梯(v1 → v7, 每一步都是复审第四点里的一条)
v1 0/224: 漏 `held_exit`; 交易前持仓用回读名义额重估 ⇒ 差 20–40%。v2 26/227: 用执行器记录的 `prev_w`, 但归一毛额用了定规模毛额 ⇒ 统一 0.19% 偏差。v3 163/163: 归一毛额改 `target_gross`(钳后 Σ|target|)⇒ 有账本的请求全对; 整形前毛额仍差 6,371(少弹 3 名)。v4: 冷却集入扣留 ⇒ 整形报告逐位相同, 242/243。v5: 拒单按 intended_notional; v6/v7: 场所上限钳 cap × (1 − margin) ⇒ 243/243。

## 4. 证明了什么 / 没证明什么
- 证明: 在树 409ea16 上, 给定执行器决策时写下的输入, **从生产者目标到逐请求下单意图的书层是可精确重现的纯函数**(POP → RESHAPE → CLAMP → 上限钳 → 小额 → 取整), 三个新锚零不可归因差异。执行器层不再是黑盒: 层分解(P-C2)与反事实(P-C3)有了可用的函数。
- 没证明: 意图 → 成交的执行层(拒单/部分成交/追单)——那是 fills 与账本的事, 属 D/I; 历史锚(冷却集与止损集在历史锚上只能靠 `per_name_stop.json` 未被覆盖的条目, phase_C 的 `cooldown_n` 可交叉核数, 名单核不到则标缺证); 09-06/09-09/09-12 三个止损日的层分解(P-C2)与止损分母/确认次数反事实(P-C3)。
- 限制: 上限钳用的是记录里的 cap 与 margin(复算规则与 `target_after` 相等), 没有从杠杆档快照独立算 cap——每锚没有档位快照。

## 5. 下一步
P-C1 再跑 08Z(本日后续锚自动成为新样本); 历史回补从 09-13 起逐锚(phase_A 行存在的锚), 冷却集核不到名单的锚标缺证; P-C2 三止损日分解; P-C3 反事实(只读)。

## 6. 历史回补(装置 v9; `FP3_receipts/PC1_HISTORY_0906_0918_2026-09-18.json`, 74 锚 09-06 00Z → 09-18 04Z)
- v8/v9 修了两处输入解析(第九轮复审第四点的延伸): phase_A `untradable_names` 是 **dict**{popped, flatten_only, add_blocked, reduced}(v7 按 list 取成了键名, 三个新锚被冷却集重建与 held_exit 盖住才没露馅); 决策时**止损集** = 上一锚 phase_C 的 `stopped`(09-17 08Z 的 ONE); 冷却集重建降为交叉核数(与 phase_C `cooldown_n` 对照), 输入以记录为准。
- **结果**: 73/74 锚有决策记录(09-09 12Z 无 phase_A); 请求段(阶段 B)**72/73 精确**(例外 09-12 12Z 215/219, 整书假阳性平仓 E-0912-A 当锚); 书层段(阶段 A)**09-12 20Z 起 33 锚全部精确**(整形报告逐位相同, 目标全部一步之内, max |Δ| 0.0000); **09-06 00Z → 09-12 16Z 不精确**(每锚 5–62 名在一步之内, max 13–98 USDT; 09-08 08Z 前 anchors 行无整形记录)——那段运行的是更老的执行器树(d040c74 / b681ca5, 书层代码在 09-13/09-17 的部署里改过), 装置 import 的是当前树; 要精确复现须按锚检出对应版本(与 P-B 的版本时间线同一课), 未做。
- 读法: 从 09-12 20Z 起, 「生产者目标 → 执行器逐请求意图」在现行代码下是零不可归因差异的纯函数; 更早的锚, 请求段可复现、书层段留版本差(具名, 未归因)。
