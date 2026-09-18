> ⚠ **作废横幅(2026-09-18 09:1xZ, 独立复审第十一轮 R11-PC1 后; v10 出数见 §7)**: 本件 v7/v9 的「三新锚逐名逐请求精确 / 历史 72/73 精确」**撤回为局部诊断**——
> ① 验收对象不是生产路径: v9 算出了 `plans_A`(从决策时记录复现的生产路径)却用它对**记录的 `orders.target_w`** 重建的 `plans_B` 去核请求, 验的是「给定已记录目标时计划器算术一致」;
> ② 只取每名首行、只看 `request_ledger[0]`: 复审把四张请求的 client_id 全改成 FOREIGN、类型全改错, v9 仍报 4/4 精确; 追加一张 qty=999999 的补单, 仍 4/4; 同毛额下把 A 25→26、B 25→24, 书层「一步之内」4/4 且请求 4/4(生产路径真值是 25);
> ③ 四条拒单无账本时按名义意图相等记 `requests_exact`(实测数量条目 0);
> ④ 书层容差是「一手或 1 USDT」, `reshape_bitwise` 只比了 `net_before`/`gross_before` 两个数(把 `net_after=50` / `gross_after=999` 的变异判成 True);
> ⑤ 历史锚 import 当前生产树而 `executor_tree=409ea16` 是硬写, 缺上一锚 phase_C 时默认空止损集, 冷却交叉核读错时间带恒为 None。
> **v1–v6 正文与 §2/§6 表格原字节保留, 只作历史**; 「09-06→09-12 16Z 的差由老执行器版本导致」保留为**假设**, v10 按锚检出对应版本后重跑(见 §7)。

> ⚠ **第二道作废横幅(2026-09-18 10:2xZ, 独立复审第十二轮 R12-P1 后; v11 出数见 §8)**: §7 的「33 锚可测全对」**撤回**——
> 其中 **09-12 20Z、09-13 00Z / 04Z / 08Z 四锚一次数量比较都没有做**: 那四锚是停机锚, 每一行 `terminal_reason=blocked_by_halt` 且 `request_ledger` 为空, 合计 **966 张计划零测量**, v10 仍报 `all_measurable_exact=True`。
> 另六个反例在同一绿基线上都得 `complete_parity=True`: ① 同一条 maker 行的**第二个**账本条目(合法前缀、阶段 99、数量 999999)——v10 只读 `request_ledger[0]`; ② maker 账本数量符号与方向相反——v10 比的是 `abs()`; ③ 清空一张 maker 账本并设未知终态; ④ 删掉全部补单行; ⑤ 补单应 buy 15 却 sell −15 且 `reduce_only=True`——v10 从不核补单方向; ⑥ 补单 15 写成 16(step 1)——v10 留了整整一手容差。
> §7 的表与判词**原字节保留, 只作历史**; v11 用两个封闭人口 + 平衡恒等式重写验收(见 §8)。

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


---

## 7. v10: 生产路径为唯一上游 + 完整请求人口 + 按锚冻结版本(2026-09-18 09:1xZ)

**装置** `FP3_devices/pc/pc1_intent_replay.py` v10(sha256 `4d8dfad3fc2b367e…`; 前身 v9 存 `FP3_devices/pc/archive/pc1_intent_replay_v9.py`), 运行器 `pc1_history.py` v2, 测试 `FP3_devices/pc/tests_pc1_v10.py` **18/18 ALL PASS**(绿基线先断言, 然后复审四个反例逐个红)。

### 7.1 五处改法
1. **唯一上游 = `plans_A`**: 从决策时记录复现的生产路径(phase_A sizing / target_live ÷ gross_norm / 扣留集 / 场所上限钳 / 上一锚回读张数)一路算到计划, 记录的 `target_w` 只作**书层比对对象**, 不再参与请求核对。
2. **完整请求人口**: 按 (rebalance_id, symbol) 取**全部**订单行, 按 `client_id = <rid>-<SYM>-<attempt>` 归类为首单(-1)、重挂(-2)、补单(-3/-3c<n>); 逐条核身份、方向、类型、reduce-only 与按步取整后的数量; 身份对不上 / 多出的补单 / 分类不了的行 ⇒ `unexplained_request:<why>`。补单按执行器自己的规则复算: `residual = delta_notional − 已知成交额`, `qty = round_qty(residual / mid_at_anchor)`, 跳过条件 `qty == 0 或 |residual| < floor 或 |qty|·mid < floor`, `skipped_no_chase_arm` 必须与 `anchors.chase_experiment.arm_assigned` 的抽臂一致, `skipped_stop_maker_only` 必须该名在止损集内。
3. **拒单单列**: −5022 post-only 拒单按构造没有请求账本 ⇒ `R1_reject_no_qty_evidence`(**不计入精确**), 其 `intended_notional` 与复现 delta 是否一致作为 `intent_consistent` 并排报告。因此新增两个判词: `all_measurable_exact`(可测的全对)与 `complete_parity`(还要求零拒单、书层精确、整形报告全键相等)。
4. **书层与整形无容差**: 书层 |Δ| ≤ 1e−6 USDT(取消一手/1 USDT); 整形报告**逐键**比对记录里的全部 22 个键, 浮点求和次序噪声单列为 `equal_within_1e-9` 而不是判等。
5. **按锚冻结版本**: 从生产 `~/dl_quant_live` 的 `git reflog HEAD` 建部署时间线, 取该锚 phase_A 运行时刻之前最后一次 HEAD 变动, `git archive` 导出到沙箱后 import(只读, 不碰生产树); 函数签名按版本适配(`force_flat` / `held_qty` 在老树上不存在)。

### 7.2 结果(50 锚, 09-10 00Z → 09-18 04Z)
| 类 | 锚数 |
|---|---|
| OK(书层逐名精确 **且** 可测请求全对) | **33** |
| REFUSED `UNAVAILABLE_REQUEST_LEDGER_SCHEMA`(09-10 00Z → 09-12 04Z) | 14 |
| REFUSED `TREE_LACKS_FORCE_FLAT_WITH_STOPS`(09-12 08/12/16Z) | 3 |

- 33 个 OK 锚覆盖**七个执行器版本**(918559f 4 / ef60f85 22 / 6661ea3 2 / 6e177c4 1 / 58256ed 1 / d858c36 2 / 409ea16 1): 书层全部逐名精确(max |Δ| 0.0000 USDT), 整形报告 33/33 在 1e−9 内, 首单 **4,385 条精确、0 条不符**, 另有 1,747 条 −5022 拒单只有名义意图证据, 补单 6,128/7,098 条与规则一致。
- **`complete_parity` = 0/33**: 每个真实锚都有 −5022 拒单, 按构造没有数量证据, 所以「完整平价」在当前记录格式下**不可达**——这不是失败, 是记录的边界, 装置把它写成两个判词而不是一个。
- **旧锚的版本差不再是假设也不再是结论**: 09-12 04Z 及更早的订单行**根本没有 `request_ledger` 键**(逐请求账本是 09-12 的执行器才有的), 装置对这 14 锚**拒测**; 09-12 08/12/16Z 的树没有 `force_flat` 参数而当锚有止损名, 也拒测。v9 报的「09-06→09-12 16Z 书层不精确、由老版本导致」因此**收回**: 那一段在 v10 的口径下是**缺证**, 不是已归因的版本差。

### 7.3 还没做
- 09-10 前的锚需要另一套验收对象(无请求账本), 未设计;
- 过滤器用当前 `exchange_info_cache.json`(33 锚全部标 `filters_assumed_current`), 历史快照未归档;
- 意图 → 成交(拒单/部分成交/追单的生命周期)仍属 D/I, 本件只到「下单意图」。


---

## 8. v11: 两个封闭人口 + 平衡恒等式(2026-09-18 10:2xZ, 复审第十二轮 R12-P1)

**装置** `FP3_devices/pc/pc1_intent_replay.py` v11(sha256 `6986c3f9d705d9af…`; 前身 v10 存 `FP3_devices/pc/archive/pc1_intent_replay_v10.py`), 运行器 `pc1_history.py` v3, 测试 `FP3_devices/pc/tests_pc1_v11.py` **26/26 ALL PASS**。
**红控**: 同一套测试以 `PC1_DEV=archive/pc1_intent_replay_v10.py` 跑在前身上, §[8] 的八格**全部转红**——这套测试是有鉴别力的, 不是为凑绿加的格。

### 8.1 验收对象改成两个封闭人口
| 人口 | 类 | 说明 |
|---|---|---|
| **计划**(`plans_A` 每一条) | `MEASURED_EQUAL` / `MEASURED_DIFFERENT` / `MISSING_REQUEST` / `UNMEASURABLE:<原因>` / `SKIP_VERIFIED` / `SKIP_MISMATCH` / `SKIP_NO_ROW` | 每条计划**恰好**落一类 |
| **请求**(每一条 `request_ledger` 条目) | `EXPLAINED` / `UNEXPLAINED:<原因>` | 每个条目**恰好**落一类 |

收据里的 `population_identity` 同时报两边的平衡(`plans_balance` / `requests_balance`); 任何东西落在类之外就不平衡。

### 8.2 六处逐条改法
1. **零测量不再等于精确**: `all_measurable_exact` 现在**要求 `n_quantity_comparisons > 0`**。
2. **每一个账本条目都比**, 不只 `request_ledger[0]`; 按 `client_id` 联接。
3. **阶段号只认执行器能铸的** 1 / 2 / 3 / 3c<n>(`client_id_for`), 其余是 `UNEXPLAINED:attempt_index_not_mintable`。
4. **数量带号比较**(v10 用 `abs()`), 补单逐块核**方向**与 **reduce_only**。
5. **取消一手容差**: 按 step 取整后必须相等(1e−9)。
6. **残差 ≥ 1e−9 却没有补单行**是 `MISSING_REQUEST`——执行器只在 `|residual| < 1e-9` 时省略该行(`binance_executor.topup` L1826), 这条边界写进了规则。

### 8.3 重跑历史(51 锚, 09-10 00Z → 09-18 08Z)
| 类 | 锚数 |
|---|---|
| OK 且书层逐名精确、可测全对 | **30** |
| **OK 但零数量测量**(09-12 20Z / 09-13 00Z / 04Z / 08Z) | **4** |
| REFUSED `UNAVAILABLE_REQUEST_LEDGER_SCHEMA` | 14 |
| REFUSED `TREE_LACKS_FORCE_FLAT_WITH_STOPS` | 3 |

计划人口合计: `MEASURED_EQUAL` **6,334** · `SKIP_VERIFIED` **1,096** · `UNMEASURABLE:not_sent:blocked_by_halt` **966** · `MEASURED_DIFFERENT` **0** · `MISSING_REQUEST` **0**。
数量比较 **6,599 次, 相等 6,599 次**; 两个人口恒等式在 **34/34** 个可运行锚上都平衡; 首单 4,525 条精确、**0 条不符**, 另 1,809 条 −5022 拒单只有名义意图证据。

**那 966 张计划是什么**: 四个停机锚(执行器 918559f)上每一行都是 `blocked_by_halt`、账本为空——什么都没发出, 也就什么都没测。v11 把它们记成 `UNMEASURABLE:not_sent:blocked_by_halt`, 四锚的 `all_measurable_exact` 全部为 **False**。复审说的「这不是 966 笔真实成交, 也不证明 966 张全下达」成立。

### 8.4 还没做
- 09-10 前的 14 锚没有逐请求账本, 仍拒测; 3 锚老树缺 `force_flat` 参数, 仍拒测。
- `complete_parity` 在全部 34 个可运行锚上仍是 **0**: 真实锚都带 −5022 拒单(按构造无数量证据), 且停机锚有不可测计划。这是记录的边界, 不是通过。
- 补单**分块数**(`split_for_market`)只记录不判词; 历史 `exchange_info_cache` 快照未归档, 34 锚全部标 `filters_assumed_current`。
- 部署时间线仍按生产 `git reflog HEAD` 推断(复审第十二轮第 3 问判「无法判定历史成立」), 未用 `safe_commit` 前后文件 sha 佐证。
