# DESIGN · 请求事实模型: 事实 × 来源 × 出口 的状态表(先于代码; 第七轮起的开发方法)

> **创建:** 2026-09-10 08:4xZ | **Session:** https://claude.ai/code/session_01H39k5rgyd43mFMNsaBqzeX | **状态:** 第七轮实盘分支的实现依据(先写表, 再写码, 每格一测); 研究员六轮复审的方法论收口 | **作废条件:** 研究员对本表给出不同事实划分, 或场所合同变化

## 0. 为什么要有这张表(六轮复审的教训)
六轮里研究员每轮都抓到承重缺陷, 形态只有三种: (1) **同一事实在不同路径有不同写法/读法**(已知数量只在 UNKNOWN 分支写、`_scan_orders` 把数量和金额一起置 None、出口清掉读者已算出的 0); (2) **两件证据不同的事被一个字段捆绑**(confirmed 绑金额、终态绑 state、pin 绑 symbol); (3) **只测修的那一格, 不测邻格与反方向**(修了漏报引入误报: 拒单 6 格误触发)。这三种都不是「想不到」, 而是「没有先把状态空间写出来」。本表把事实、来源、出口枚举成格, 每格先写期望再写码, 每个修复同时加**同格反方向**与**邻格**测试, 并用**原链端到端**(complete_anchor → topup → reconcile → position_break → watchdog)跑, 不只跑 helper。

## 1. 每张请求的独立事实(各自有自己的可读性, 互不推导)
| 事实 | 取值 | 可读性状态 | 来源(优先级从高到低) |
|---|---|---|---|
| 身份 | client id, (symbol, orderId) | 必有(缺 orderId ⇒ 无法归属子成交) | 我方提交记录 → 查单 → allOrders |
| 方向 σ, 请求量 Q | ±, 合约 | 必有 | 我方计划; 场所 origQty 用来核对(不符 ⇒ 非我方记录) |
| 终态 | FILLED/CANCELED/EXPIRED/REJECTED(终); NEW/PARTIALLY_FILLED(开) | 已读 / 未读 | 撤单回包 → 查单 → allOrders → 提交回包; **较新的可靠终态覆盖较旧状态**; 一无所知的请求终态 = 未读(不是 False 也不是 True) |
| 累计已成量 C | 合约 ≥ 0 | 可信(有限 ≥0 且 ≤ Q)/ 缺失 / **矛盾**(负数; 显式 0 但金额 > 0; 子成交同 id 不同量; > Q; 反向) | executedQty(任一来源)→ 同请求 cumQuote/avgPrice 推导(标源)→ 子成交并集(trade id 去重, 单调) |
| 金额 N | USDT | 可读 / 缺失 | cumQuote → avgPrice × C(同请求)→ 子成交 quote 并集 |
| 价格 | USDT/合约 | 可读 / 缺失 | 同请求 N/C; 行级均价只在**全部**已执行请求同时贡献 N 与 C 时写出 |
| 请求状态 | not_sent / rejected / unknown / confirmed | — | not_sent = 未离开进程; rejected = 场所明确拒绝(终态, C=0, N=0); unknown = 送达与否/结果未读; confirmed = 至少读到一项可信事实 |

**禁止的推导**: 金额可读 ⇏ C 可信; 终态 ⇏ C=0; C 未知 ∧ 终态 ⇏ 过去成交为 0; 行级 N/均价 ⇏ 数量(除非同请求); 「allOrders 缺席」⇏ 未成交。

## 2. 每张请求的区间(风控消费的量)
| 状态 | 已执行区间 [C_lo, C_hi] | 未来容量 |
|---|---|---|
| rejected / not_sent | [0, 0] | 0 |
| 终态, C 可信 | [C, C] | 0 |
| 终态, C 缺失(N 可读且同请求价可读 ⇒ 推 C ⇒ 上行) | [0, Q] | 0 |
| 开, C 可信 | [C, Q](历史可能已更多)… 对当前锚 [C, C] + 未来 Q−C | Q−C |
| 开/未知, C 缺失 | [0, Q] | Q |
| 任一矛盾 | 不可测(异常), 腿不关闭 | — |
行级: 已知量 K = Σ C(可信); 带 = Σ 未来容量 ⊕ Σ 历史未知区间(Minkowski); `filled_qty` 只在**全部**已发请求终态且 C 可信时写出(= Σ C), 与金额无关; `filled_notional` 只在全部已发请求金额可读时写出。

## 3. 出口 × 事实(每格一测; 反方向 = 同夹具持仓不变必须 CLEAN)
| 出口 | 请求状态 | 行应写 | 反方向对照 |
|---|---|---|---|
| 全部送达且读到回包 | confirmed 终态 | filled_qty Σ C, filled Σ N(若全可读) | 持仓 = Σ C 时 CLEAN |
| 回包 PARTIALLY_FILLED/NEW(不该出现于 IOC 但可注入) | confirmed 开 | K=C, 带 Q−C | 持仓 ∈ [C, Q] CLEAN |
| 传输歧义/absent(送达与否未知) | unknown | 带 Q | 持仓 ∈ [0, Q] CLEAN |
| 传输快失败(未送达) | not_sent | 0 | 持仓不变 CLEAN |
| 明确拒绝(任何码, 含 −4400) | rejected | **0(filled_qty 0.0, 不得被出口清掉)** | 持仓不变 CLEAN(第六轮误触发格) |
| 熔断跳过 | not_sent | 0; 且 maker 腿行先写 | 持仓 = maker 成交 CLEAN |
| 预检拒绝 | 未发 | 整锚不发 | — |
| 阶段 B: 匹配终态 | 终态 C 可信 | 覆盖旧 unresolved, 清 pin | 合法补单照旧 |
| 阶段 B: 匹配开 → 撤 → 复查终态 | 终态 | 同上 | 同上 |
| 阶段 B: 撤/复查失败 | 开, C 已读 | K=C, 带 Q−C, 不补单 | 持仓 ∈ [C, Q] CLEAN |
| 阶段 B: 终态但金额不可读 | 终态 C 可信 | **K=C, 带 0**(第六轮漏报格) | 持仓 = C CLEAN, ≠ C 异常 |
| 阶段 B: 满页未匹配 | unknown | 带 Q | — |
| 阶段 B: −2013(仅歧义计划, 显式假设) | absent | 0 | — |

## 3b. 第八轮补格(研究员第七轮 A/B/C/#1)
| 出口 / 来源 | 事实 | 行应写 | 反方向对照 |
|---|---|---|---|
| 提交回包 + 金额补查(同请求两条记录) | 逐字段合并: 缺字段不撤销已有事实; 显式 0 + 终态 = C 0(任一入口); 后读 C 小于先读 / 终态后 NEW = 矛盾 | POST C20 无金额 + GET 无 C ⇒ C 20 保留 | ACK + GET EXPIRED 0 ⇒ C 0 终态(不是带 Q) |
| allOrders 匹配但记录无 status | 不是终态证据 ⇒ 走查单 | 查单失败 ⇒ UNKNOWN | 显式 CANCELED + 身份相符 ⇒ terminal_matched |
| allOrders 匹配但身份不符(origQty / symbol / side / orderId) | 非我方记录 ⇒ UNKNOWN | 不清 pin, 不补单 | — |
| 折叠记到矛盾(负 C / 0 伴正金额) | 该名 UNKNOWN(不入 filled) | maker 行带 `inconsistent`, 读者不可测, 不补单 | 真正 CANCELED 0 ⇒ 补单照旧 |
| 任何账本行 | 金额/均价来自读者(同集合), 未关闭 ⇒ None + 标签改 `filled_amount_unknown` + `ledger_label_mismatch` | 分支手写值一律无效 | 已关闭 ⇒ 读者 Σ 与同集合均价 |

## 4. 结构性保证(不靠人记得)
1. **读者在行发出时最后一次重算**: `_order_row` 看到 `request_ledger` 就用 `ledger_row_columns` 覆盖六个数量/金额列 —— 任何分支手写的列都被账本推翻; 分支只允许改账本, 不允许改列。
2. **矛盾先于分类**: 读者第一行; 生产者(decoder / 折叠 / 子成交)各自记矛盾, 不猜。
3. **可读性分离 + 来源合并**: `_scan_orders` 与 decoder 对 C、N、价各出各的 None; 一项不可读不抹另一项; 同一请求的多条记录(提交回包 / 补查 / allOrders / 撤单回包)逐字段合并(`merge_order_records`), 缺字段不撤销已有事实, 终态吸收, 累计量不减。
4. **较新覆盖较旧, 按身份**: 终态来源比较由 (symbol, cid) 决定, 不由 symbol 集合决定; 覆盖时同步清 pin。
5. **每个修复三件测试**: 反例格 + 同夹具反方向(持仓不变 CLEAN) + 邻格(同事实在其它出口); 加**原链端到端**(complete_anchor → RC/PB/WD)至少各一。
6. **版本配对**: 交接里列出「上一轮期望被改的格」与原因; 研究员的旧夹具原样重跑, 翻转按预期/非预期分列。
7. **措辞门**: 「全部/唯一/从不/原子」必须指向一条覆盖该量词域的测试; 否则不写。

## 3c. 第九轮补格(研究员第八轮 R8-MERGE / R8-TERMINAL / R8-CANCEL / R8-IDENTITY / R8-PARTIAL): 「记录集合」层
第八轮把「来源合并」写成两条记录的逐字段合并, 但字段合并不是事实合并: (1) 派生(N/avg、avg×C)跨了记录 —— 两个快照的字段被当成一个截面; (2) 「累计量不减」只写了下降方向, 没写终态常量; (3) 撤单回包没进记录集合; (4) 身份门只拦动作(补单), 没拦事实(入账); (5) partial 出口挑字段而不是带整个折叠。表的对象改为**每张请求的记录集合 R**(提交回包 / 撤单回包 / allOrders 行 / 查单记录, 按观察顺序), 一个合并器, 派生只在记录内, 合并按事实。

| # | 来源 / 出口 | 事实规则 | 行应写(反例格) | 反方向(同夹具) | 邻格 |
|---|---|---|---|---|---|
| 1 | 同一请求两条记录: 金额在旧记录, 均价在新记录 | **派生只在同一记录内**: C_r ← executedQty_r, 否则 N_r/avg_r(同记录); N_r ← cumQuote_r, 否则 avg_r×C_r(同记录); 跨记录一律不派生。金额只在来自终态快照(终态吸收: 终态之后的每个快照都是终态快照)或来自 C_r = C_final 的快照时才是**终值**; 否则只是下界(`cum_quote_lower`), 行的金额 None | POST PARTIALLY_FILLED N40 + GET EXPIRED avg3 ⇒ C 未知(不是 13.33), N 非终值, 终态 ⇒ 请求区间 [0, Q]; 第二单 50 ⇒ 行 known 50 / 带 50 / filled_qty None; 回读 80 CLEAN(不再报警), 110 与 40 异常 | 同一记录 N40/avg2 ⇒ C20 派生(照旧, 标源) | POST N40/avg2(派生 C20, 开)+ GET EXPIRED C20 ⇒ 一致, N40 终值(C 相等); POST N40 开 + GET EXPIRED C30 无 N ⇒ C30 关闭数量, N 未知(40 只是下界), 行金额 None |
| 2 | 终态后再读到不同的可信 C | **终态常量**: 任一终态记录的可信 C_T 之后(或之前)的任何可信 C_r ≠ C_T ⇒ 矛盾(不择大不择先); 终态但 C 未知 → 后补 C 允许; 开→终态的增长合法; 累计金额同样不减 | POST EXPIRED C20 + GET EXPIRED C30 ⇒ inconsistent ⇒ 请求不可测; 第二单 50 后行 `ledger_inconsistent`, 回读 80 异常(不再 CLEAN) | POST EXPIRED C20 + GET EXPIRED C20 ⇒ 70 关闭 | OPEN C10 → EXPIRED C20 ⇒ 关闭(合法增长); 终态 C20 之后无 status 的 C30 ⇒ 矛盾; 同 updateTime 终态 20/30 ⇒ 矛盾; EXPIRED 无 C → C30 ⇒ 30(补齐); 子成交并集 > 终态 C ⇒ 矛盾(账本 `_settle_leg_by_identity`, 首读保留) |
| 3 | 撤单回包 | DELETE 回包**带执行字段**(executedQty / cumQuote / avgPrice 之一)即为该请求的一条记录, 过身份门后进入合并(k-cancel 的与阶段 B 结算撤单的都算); 无执行字段的回包不进合并(无可注入; 状态只由查单定) | k-cancel CANCELED C4/N4 + allOrders 空 + 查单终态缺 C/N ⇒ C4 N4 ⇒ 补 6, maker 行 4 / 补单行 6; 回读 10 CLEAN, 14 异常 4 | k-cancel C4 + 查单 C4 ⇒ 补 6(已有正控) | k-cancel C4 + 查单终态 C6 ⇒ 终态常量矛盾 ⇒ UNKNOWN 不补; allOrders 未达(读失败)但 k-cancel C4 ⇒ UNKNOWN maker 行 known 4 / 带 0(终态), 不补单; k-cancel 带事实后查单 −2013 ⇒ 矛盾(不是 absent) |
| 3b | 稀疏终态记录(缺 executedQty 且缺 cumQuote) | 数量不可读 **且** 金额不可读, 不是「未成交 0」; cumQuote 显式 0 只在旁边有显式 executedQty 0 时才是金额 0 | `_scan_orders` ⇒ executed None / filled_notional None ⇒ 该名 UNKNOWN | 显式 0/0 ⇒ 测得零(照旧) | executedQty 缺 + cumQuote 显式 0 ⇒ 金额不可读(保守) |
| 4 | 身份不合法的记录 | **身份门作用于事实**: 我方 cid 下的记录身份不符(symbol / side 缺或不符 / origQty 非有限或 ≠ Q / orderId ≠ ACK 的 orderId)⇒ 该请求 `inconsistent(identity)` ⇒ 不可测; 其 C / 终态 / 金额一律不入账本; 折叠里缺 side 的成交行 = 矛盾(不再当 SELL) | allOrders origQty 5 ≠ Q10, C4 CANCELED ⇒ UNKNOWN 且 maker 行 `ledger_inconsistent`(不是 confirmed 4 / terminal), 回读 4 与 10 皆异常, 不补单 | 身份相符 C4 CANCELED ⇒ terminal_matched, 行 4 | side 缺 ⇒ 不符(不再折成 −4 补 14); origQty NaN / Inf ⇒ 不符; ACK orderId 101 而记录 997 ⇒ 不符; 查单来源同判 |
| 6 | 金额补查(`last_fill_details` 的 GET) | 补查记录也过身份门(研究员 risk §5, R7 已记 P2 边界): clientOrderId / symbol / orderId / origQty / side 与提交回包相符 —— 记录带该字段才比对, 不带不算证据; 不符 ⇒ `inconsistent(identity)`, 请求不可测 | 补查返回 orderId 9999 的 FILLED 50 ⇒ 行 `ledger_inconsistent`, 回读 70/100 皆拒 | 同身份 ⇒ 照旧合并(C20, N40 终值) | 不带身份字段的记录 ⇒ 照旧合并(无证据不发明) |
| 5 | partial 出口 | 矛盾与事实同行: `_keep_partial` 带整个折叠(inconsistent / derived / amount_unreadable), 且 partial 也经记录集合合并 | 查单 PARTIALLY_FILLED C0/N4 + 撤失败 ⇒ partial 带 inconsistent ⇒ maker 行 `ledger_inconsistent`, RC 不可测(与 page 来源同判) | 查单 PARTIALLY_FILLED C4/N4 ⇒ known 4 / 带 6(照旧 [35]) | page 与 query 同事实同判(两来源一致性断言) |

## 4(续). 第九轮的结构性保证
8. **记录集合是对象**: 每张请求的记录集合 R(POST / DELETE / allOrders / GET, 按观察顺序)只经一个合并器 `merge_order_records(*R)`; 派生在记录内(`_snapshot`), 合并按事实(累计量与累计金额不减、终态常量、终态吸收); 身份门(`_valid`)在合并之前作用于**每条**记录; 折叠 `_scan_orders` 只吃合并后的正典记录(每 cid 一条), 且结算内的折叠不写回匹配缓存。
9. **无事实字段的记录不进合并**: 只有状态没有执行字段的回包(夹具形状)不能注入也不能撤销任何事实; 状态由查单定。
10. **`known_order_id` 只有一个实现**(broker 拥有 actions): 执行器的 `_order_id_for` 与结算的身份门读同一个函数。
