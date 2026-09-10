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
| 2 | 终态后再读到不同的可信 C | **终态常量**(第十轮更正措辞, 研究员 risk §5): **终态快照之间**的可信 C 必须相等; 终态之前的开单快照 C 只是下界, 可以小于 C_T(开→终态增长合法), 大于 C_T 则是「累计量下降」矛盾; 终态但 C 未知 → 后补 C 允许; 累计金额同样不减, 终态快照之间的金额也必须相等 | POST EXPIRED C20 + GET EXPIRED C30 ⇒ inconsistent ⇒ 请求不可测; 第二单 50 后行 `ledger_inconsistent`, 回读 80 异常(不再 CLEAN) | POST EXPIRED C20 + GET EXPIRED C20 ⇒ 70 关闭 | OPEN C10 → EXPIRED C20 ⇒ 关闭(合法增长); 终态 C20 之后无 status 的 C30 ⇒ 矛盾; 同 updateTime 终态 20/30 ⇒ 矛盾; EXPIRED 无 C → C30 ⇒ 30(补齐); 子成交并集 > 终态 C ⇒ 矛盾(账本 `_settle_leg_by_identity`, 首读保留) |
| 3 | 撤单回包 | DELETE 回包**带执行字段**(executedQty / cumQuote / avgPrice 之一)即为该请求的一条记录, 过身份门后进入合并(k-cancel 的与阶段 B 结算撤单的都算); 无执行字段的回包不进合并(无可注入; 状态只由查单定) | k-cancel CANCELED C4/N4 + allOrders 空 + 查单终态缺 C/N ⇒ C4 N4 ⇒ 补 6, maker 行 4 / 补单行 6; 回读 10 CLEAN, 14 异常 4 | k-cancel C4 + 查单 C4 ⇒ 补 6(已有正控) | k-cancel C4 + 查单终态 C6 ⇒ 终态常量矛盾 ⇒ UNKNOWN 不补; allOrders 未达(读失败)但 k-cancel C4 ⇒ UNKNOWN maker 行 known 4 / 带 0(终态), 不补单; k-cancel 带事实后查单 −2013 ⇒ 矛盾(不是 absent) |
| 3b | 稀疏终态记录(缺 executedQty 且缺 cumQuote) | 数量不可读 **且** 金额不可读, 不是「未成交 0」; cumQuote 显式 0 只在旁边有显式 executedQty 0 时才是金额 0 | `_scan_orders` ⇒ executed None / filled_notional None ⇒ 该名 UNKNOWN | 显式 0/0 ⇒ 测得零(照旧) | executedQty 缺 + cumQuote 显式 0 ⇒ 金额不可读(保守) |
| 4 | 身份不合法的记录 | **身份门作用于事实**: 我方 cid 下的记录身份不符(symbol / side 缺或不符 / origQty 非有限或 ≠ Q / orderId ≠ ACK 的 orderId)⇒ 该请求 `inconsistent(identity)` ⇒ 不可测; 其 C / 终态 / 金额一律不入账本; 折叠里缺 side 的成交行 = 矛盾(不再当 SELL) | allOrders origQty 5 ≠ Q10, C4 CANCELED ⇒ UNKNOWN 且 maker 行 `ledger_inconsistent`(不是 confirmed 4 / terminal), 回读 4 与 10 皆异常, 不补单 | 身份相符 C4 CANCELED ⇒ terminal_matched, 行 4 | side 缺 ⇒ 不符(不再折成 −4 补 14); origQty NaN / Inf ⇒ 不符; ACK orderId 101 而记录 997 ⇒ 不符; 查单来源同判 |
| 6 | 金额补查(`last_fill_details` 的 GET) | 补查记录也过身份门(研究员 risk §5, R7 已记 P2 边界): clientOrderId / symbol / orderId / origQty / side 与提交回包相符 —— 记录带该字段才比对, 不带不算证据; 不符 ⇒ `inconsistent(identity)`, 请求不可测 | 补查返回 orderId 9999 的 FILLED 50 ⇒ 行 `ledger_inconsistent`, 回读 70/100 皆拒 | 同身份 ⇒ 照旧合并(C20, N40 终值) | 不带身份字段的记录 ⇒ 照旧合并(无证据不发明) |
| 5 | partial 出口 | 矛盾与事实同行: `_keep_partial` 带整个折叠(inconsistent / derived / amount_unreadable), 且 partial 也经记录集合合并 | 查单 PARTIALLY_FILLED C0/N4 + 撤失败 ⇒ partial 带 inconsistent ⇒ maker 行 `ledger_inconsistent`, RC 不可测(与 page 来源同判) | 查单 PARTIALLY_FILLED C4/N4 ⇒ known 4 / 带 6(照旧 [35]) | page 与 query 同事实同判(两来源一致性断言) |

## 4(续). 第九轮的结构性保证
8. **记录集合是对象**: 每张请求的记录集合 R(POST / DELETE / allOrders / GET, 按观察顺序)只经一个合并器 `merge_order_records(*R)`; 派生在记录内(`_snapshot`), 合并按事实(累计量与累计金额不减、终态常量、终态吸收); 身份门(`_valid`)在合并之前作用于**每条**记录; 折叠 `_scan_orders` 只吃合并后的正典记录(每 cid 一条), 且结算内的折叠不写回匹配缓存。
9. **无事实字段的记录不进合并**: 只有状态没有执行字段的回包(夹具形状)不能注入也不能撤销任何事实; 状态由查单定。
10. **`known_order_id` 只有一个实现**(broker 拥有 actions): 执行器的 `_order_id_for` 与结算的身份门读同一个函数。

## 3d. 第十轮补格(研究员第九轮 R9-QFINAL / R9-FACT-EXIT / R9-CHILD-SUPPORT): 事实的「完整性类型」与失败出口
第九轮把记录集合合并对了, 但两处又是同一种错: (1) 合并输出只有一个 `executed_qty`, 没有说它是**最终总量**还是**开单快照的下界** —— 读者用 `terminal + 有限 C` 当作精确关闭, 开单快照的 20 被升级成最终 20(合法 80 报警); (2) 失败出口(查询异常 / −2013 / 结算撤单后查询失败)直接 return, 已读到的撤单事实、POST 自己的执行字段不进集合(可靠 4 退化成 0–10 带)。每张请求的事实从四项变五项: σ、Q、**L(累计下界)**、T(终态)、**F(最终总量已证明)**。

| 事实 | 字段 | 规则 |
|---|---|---|
| L 累计下界 | `confirmed_qty`(带号) | 任一快照的可信 C、子成交并集; 单调不减; 最终快照的 C 就是 L 且 F=真 |
| F 最终总量已证明 | `confirmed_qty_final` | 只有三种来源为真: 终态快照(或终态之后的快照)给出的 C; L 到达 Q(容量); 拒绝/未发(0)。子成交并集**永不**单独给出 F(子集不能证明全集); 缺该键的旧行按 `terminal` 读(遗留规则, 新写行必写) |
| 区间 | 读者 | rejected/not_sent [0,0]; F ⇒ [C,C], 余量 0; 否则 [L, Q], 余量 Q−L(**终态与否都一样**: 终态只把未来新增容量归零, 不消灭过去的未知量); L 未知 ⇒ [0,Q] |
| 关闭 | `filled_qty` | 每张已发请求都 F 才写(不再是 terminal + 有限 C) |

| # | 来源 / 出口 | 事实规则 | 行应写(反例格) | 反方向(同夹具) | 邻格 |
|---|---|---|---|---|---|
| 1 | 开单快照 C20 → 终态快照缺 C(R9-QFINAL) | L=20, T=真, F=假 ⇒ [20,50] | 加第二张 50 ⇒ known 70 / 带 30 / filled_qty None; 回读 70–100 CLEAN, 60 与 110 异常; SELL 对称 | 终态快照 C20 → 终态缺 C ⇒ F=真 ⇒ 70 精确, 80 异常 10 | OPEN10 → 终态 20 ⇒ 20 F; 终态缺 C → 之后 C30 ⇒ 30 F; 开单 20 且终态 + 子成交 30 ⇒ L=30(不是「超过终态 20」矛盾) |
| 2 | 终态而 C 未知 + 子成交子集(R9-CHILD-SUPPORT) | 子成交只抬 L, F 仍假 | 终态未知 C + child 30 + 第二张 50 ⇒ known 80 / 带 20; 回读 80/90/100 CLEAN, 70 异常 | F=真 C20 + child 10 子集 ⇒ 保留 20 | F=真 C20 + child 30 ⇒ 矛盾(照旧); child 到达 Q ⇒ F=真(容量) |
| 3 | 结算撤单成功后查询失败(R9-FACT-EXIT) | 撤单回包已读到的事实在查询失败时仍进集合 | 首撤失败 → page PARTIAL 4 → 结算撤单 CANCELED 6 → 查询失败 ⇒ known 6 / 带 0(F), 不补; 回读 6 CLEAN, 10 异常 4 | 查询成功 CANCELED 6 ⇒ maker 6, 补 4, 回读 10 CLEAN, 14 异常 4 | 撤单本身失败 ⇒ 之前的 partial 4 保留(已有) |
| 4 | 查单异常(运输耗尽 / 满页)时已有 k-cancel 事实 | 每个 UNKNOWN 出口都先把手里的记录合并成事实(`_carry`) | k-cancel CANCELED 4/4 → 查单运输失败 ⇒ UNKNOWN 行 known 4 / 带 0 / filled_qty 4; 回读 4 CLEAN, 0 与 10 异常 | 无任何记录 ⇒ 带 10(照旧) | 满页同判 |
| 5 | k-cancel 带事实后 −2013 | 矛盾 ⇒ 不可测(不是 ABSENT, 不是带) | 回读 0/4/10 皆异常 | 撤单 −2011 + 查单 −2013 ⇒ ABSENT(照旧) | status-only 撤单回包(有 CANCELED 无执行字段) + −2013 ⇒ 矛盾不可测(第九轮曾判 ABSENT 0 并补 10 —— 「存在」也是它携带的事实) |
| 6 | POST 自己的执行字段 | 提交回包(broker 动作里的记录)是集合的第一条记录; 身份按「带字段才比对」(它是我方按 cid 记录的回包); status-only 撤单回包只贡献状态 | POST PARTIALLY_FILLED C4/N4 + status-only 撤单 + 稀疏终态查单 ⇒ L=4, F=假 ⇒ known 4 / 带 6; 回读 4 与 10 CLEAN, 0 与 14 异常 | 无 POST 事实 ⇒ 带 10 | 无 ACK(歧义 POST)+ 身份完整的查单 ID999 C4 ⇒ 接受(已有) |
| 7 | 终态快照之间的金额 | 金额也是终态常量: 两个终态快照 N40 / N60 ⇒ 矛盾 | 行不可测 | N40 / N40 ⇒ 照旧 | 开单 N20 → 终态 N40 ⇒ 合法 |

**登记未做**: 同快照内 C×avg 与 N 的一致性(容差由场所精度定, 不擅定阈值); 已知路径 maker 行(金额可读)仍无账本, 数量由 N/avg 读(同快照时合法).

## 4(续). 第十轮的结构性保证
11. **完整性类型随事实走**: 合并器输出 `executed_qty_final`, 正典记录携带 `executedQtyFinal`, 折叠输出 `executed_qty_final`, 计划 `venue_executed_qty_final`, 账本 `confirmed_qty_final`; 读者只认这一个键, 不从 `terminal` 推。
12. **每个 UNKNOWN 出口先合并已有记录**: `_carry(p, sym, cid, recs)` 是所有失败出口的唯一入口; 新增出口必须经过它(措辞门: 「每个」指向 [56]–[58] 覆盖的出口清单: 查单异常 / −2013 / 满页 / 结算撤单后查询失败 / 未达).

## 3e. 第十一轮补格(研究员第十轮 R10-MAKER-F / R10-NONOBJECT-CARRY / R10-CHILD-CONSUMER + 三条自报答复): 完整性类型要贯穿每个读者, 金额与数量各自证明
第十轮把 F 带到了账本, 但 (1) 普通 maker 行(金额可读)没有账本, 读者仍用 N/avg 读数量, 而合并器又用最终 N 除以旧下界 L 造出一个不属于任何快照的均价; (2) 「每个出口」又漏了一个(查单答非对象); (3) 金额关闭没有自己的完整性 —— 子成交子集的金额把 `filled_notional` 关闭, 数量读者又以「N 是否 None」决定是否看数量带。三条自报答复: 旧行缺 F 按 terminal 读的理由不成立(实盘 40 日 67,588 行无一带账本); IOC 无 status 置 F 是假设(wire 是 MARKET+RESULT, 无 timeInForce); POST 身份绑定被回包的 CID 决定(应按我方发送的 CID 选记录, 再核回包字段)。

| 事实 | 字段 | 规则 |
|---|---|---|
| N 的完整性 | `confirmed_notional_final` | 只有终态快照(或终态后快照)给出的 N、或子成交集合到达 Q 才为真; 子集的 N 只写 `confirmed_notional_lower`; 金额关闭(`filled_notional`)要求每张已发请求 N 已知且 N 为终值 |
| F 的来源 | `confirmed_qty_final` | 显式为真, 或 L 到达 Q(容量: 区间退化为点); 缺键 / None 一律不是终值(无遗留人口需要保护) |
| 均价 | 读者 | 只在每张贡献请求 C 与 N 都是终值时写; 合并器不得用终值 N 除以下界 L |
| 普通 maker 行 | `request_ledger` | 凡 apply_fill_details 给过场所事实的 maker 行都带账本(L / F / T / N / N_final); 数量列由读者写, 不再由 N/avg 推 |
| 数量读者(RC) | 带分支 | 账本行有带就走带分支, 与 N 是否 None 无关 |
| 提交回包身份 | broker 动作 | 按我方发送的 client_id 选记录; 回包声称别的 CID ⇒ orderId 不可信(None), 现字段门判「回包记在别的 id 下」 |
| 补单请求终态 | 显式 status | 无 status 的回包不因本地 tif 名而终态; F 只在显式终态且合并器判终值 |

| # | 来源 / 出口 | 反例格 | 反方向 | 邻格 |
|---|---|---|---|---|
| 1 | maker OPEN C4/N4 → 终态只有 N6 | 合并 avg None(不再 6/4); maker 行账本 L4 / F 假 / N6 终值 ⇒ known 4 / 带 6 / filled_notional 6; 补 4 ⇒ 总量 [8, 14]: 10 与 14 CLEAN, 6 与 16 异常 | 终态 C6/N6/avg1 ⇒ maker 6 精确, 补 4, 10 CLEAN、14 异常 4 | 同快照 N/avg 派生照旧 |
| 2 | 查单答非对象(list) | `_carry` ⇒ known 4 / 带 0 / filled_qty 4; 回读 4 CLEAN, 0/10 异常 | 查单答 CANCELED 4 对象 ⇒ found, 补 6 | 出口清单: 查单异常 / −2013 / 满页 / 非对象 / 结算撤单后复查失败 / 未达 |
| 3 | 终态未知 C + 子成交子集 30(+50) | `confirmed_notional` 不写(`_lower` 30), filled_notional None, 标签 filled_amount_unknown; known 80 / 带 20; RC 80/90/100 CLEAN, 70/110 异常 | 子集到达 Q ⇒ F 与 N 皆终值, 关闭 | 手写账本行 N80 已知 + 带 20 ⇒ RC 走带分支 |
| 4 | 缺 F 键的账本 | terminal + C6 无键 ⇒ 不是终值: 带 4, filled_qty None; None 同 | 显式 True ⇒ 关闭 | C=Q ⇒ 容量终值(区间退化为点) |
| 5 | 补单回包无 status | C20 无 status + GET 失败 + 50 ⇒ known 70 / 带 30(不再精确 70) | EXPIRED ⇒ 精确 70 | NEW ⇒ 带 30 |
| 6 | 回包声称别的 CID | 发 A, 回包 CID=B/101 ⇒ lookup(B) 无, lookup(A) 的 orderId 不可信, 现字段门 ⇒ 不可测 | 回包 CID=A ⇒ 101 | 回包无 CID ⇒ 按发送 id 记 |

**仍登记**: R6-MARK(无 mark 的「不可对账」不触发 halt, 动作合同另议); 同快照 C×avg 与 N 一致性; `_seen_syms > 1` 与 settle 整体异常的出口不带事实(设计如此, 明写)。

## 4(续). 第十一轮的结构性保证
13. **每个读者都只认完整性字段**: `_final_known` 不再有 terminal 回退; 均价、金额关闭、数量关闭三者各自要求自己的终值证明; RC 的带分支不看 N。
14. **有场所事实的 maker 行一律带账本**(`_venue_facts` 标记由 apply_fill_details 写), N/avg 读法只剩没有任何场所事实的行(DRY_RUN / 注入 fills)。

## 3f. 第十二轮补格(研究员第十一轮 R11-POST-READER / R11-CANONICAL-L0 + 三条金额 P2 + 两条表示 P2): 每个读者只认完整性字段 —— 用全表收口, 不再靠下一轮反例
| # | 来源 / 出口 | 事实规则 | 反例格 | 反方向 | 邻格 |
|---|---|---|---|---|---|
| 1 | 提交回包直接读者(`last_fill_details`) | 回包先按我方发送的 order 核身份(cid / symbol / side / origQty, 带字段才比对); 不符 ⇒ `inconsistent(identity)`, 其 C/N 一律不入账, **不补查**(0 次 GET); 通过后补查只按发送的 cid | 发 A, 回包声称 B/C4/N4 ⇒ 请求不可测(曾: 4 记入 A, 回读 4 CLEAN); 回包声称 B 且缺金额 ⇒ 先判身份不符, 不补查(曾: 按 B 补查并接受 B) | 回包 cid=A ⇒ 4 照旧 | 回包无 cid ⇒ 按发送 id 记(照旧) |
| 2 | 合并后的正典记录 C=0 是下界 | 「显式 0 伴正金额 = 矛盾」只对**精确** 0(原始同快照记录; 或 F=真)成立; F=假 的 0 是下界, 与任何金额相容 | POST NEW C0/N0 → status-only 撤单 → 终态 GET 只有 N4 ⇒ L0 / F 假 / N4 终值 ⇒ known 0 / 带 10 / 金额 4, 补 6 ⇒ 总量 [6,16]: 10 与 16 CLEAN, 4 与 18 异常(曾: 判矛盾, 不补, 回读 4 触发) | 原始同快照 C0/N4 ⇒ 仍矛盾(照旧 [40][46]) | 终态 GET 带 C4/N4/avg1 ⇒ 精确 4, 补 6, 10 CLEAN、14 异常 |
| 3 | 子成交与终值金额 | 终值 N 也常量: 集合完整时 n_child ≠ 已有终值 N ⇒ 矛盾(保留场所 N); 子集 N 不得超过终值 N; 去重表只增不减 —— 同 trade id 再来一次缺 quote 不撤销已记 quote, 之后不同 quote 仍是冲突 | F 真 C20/N40 + 子集完整 N60 ⇒ 矛盾, N 仍 40(曾: N 改 110); quote 40 → 缺 → 60 ⇒ 冲突(曾: 擦成 None 再收 60) | N40 ⇒ 照旧 | 子集 N 超终值 N ⇒ 矛盾 |
| 4 | 手续费归属的后置写者 | 有账本的行: `filled_notional` / `avg_fill_px` 只由读者写; 子成交经 `_settle_leg_by_identity`(尊重 F / N_final); 子集 vwap 写到独立字段 `avg_fill_px_children`, 不冒充整单均价 | maker L4 / 带 6 / N6 终值 + 子集 4@1 ⇒ 行 avg 仍 None, `avg_fill_px_children` 1.0(曾: avg 补成 1, M1 完整性假→真) | C 终值 + 集合完整 ⇒ 读者写均价 | 无账本旧行 ⇒ 后置写者照旧(兼容) |
| 5 | UNKNOWN 出口只有 N 没 C | 金额与数量各自入账: N 终值 + C 缺 ⇒ `confirmed_notional` 4 / `_final` 真, `confirmed_qty` None | 终态撤单回包 N4 无 C/avg + 查单失败 ⇒ 行 known_notional 4, 数量 [0,10](曾: N 丢失) | 同源查单成功 ⇒ 补 6 | — |
| 6 | 账本请求 confirmed 而 C 为 None(**合同选择, 本轮登记**) | 读成区间 [0, Q]: 已知量 0 + 带 Q(与失败出口的表示统一), 不再返回 None ⇒ 不可测; 「金额已知而数量未知」是带, 不是坏值 | 普通 maker 账本 N4 终值 / C None + 补 6 ⇒ known 6 / 带 10 ⇒ 6–16 CLEAN, 4 与 18 异常(曾: RC 不可量化, 5b 触发) | — | 金额未知且 C 未知 ⇒ 带 Q(照旧) |
| 7 | 明确零(absent / nothing executed) | 零金额也带终值位 `filled_notional_final` | CANCELED C0/N0 ⇒ 行金额 0.0(曾 None) | — | — |
| 措辞 | `_final_known` 文档 / 旧 IOC 注释 | 「无遗留人口」收紧为「08-01..09-09 窗口 40 日 67,588 行无账本行」; 删除「IOC 无 status 即终态」旧注释 | — | — | — |

## 5. 事实 × 读者 全表(第十二轮; 交研究员按表核, 不再按反例核)
每张请求(`request_ledger` 元素)的事实字段与它们的**全部**读者。规则: 读者只认本表列出的字段; 新增字段时本表加一列, 每个读者要么读它要么在此声明不需要。

| 事实 | 字段 | 生产者 | 读者(必须尊重的规则) |
|---|---|---|---|
| σ, Q | `qty`(带号) | 补单腿 / UNKNOWN maker 行 / 普通 maker 行(有场所事实) | `request_remaining`(Q−L); `ledger_inconsistencies`(超量 / 反向); `_final_known`(容量: L≥Q ⇒ F) |
| L 累计下界 | `confirmed_qty`(带号) | 合并器 `executed_qty` → 折叠 → 计划 `venue_executed_qty` → 行; 补单腿 `_ex1`; 子成交并集 | `request_remaining`(F ? 0 : Q−L); `ledger_known_qty`(Σ L; C None 的 confirmed 请求算 0 + 带 Q — 第十二轮); `ledger_qty_closed`; `ledger_row_columns` 均价(需 F); `_settle_leg_by_identity`(单调; F 时常量); `ledger_inconsistencies` |
| F 最终总量已证明 | `confirmed_qty_final` | 合并器 `executed_qty_final`(终态快照)→ `executedQtyFinal` → 折叠 → `venue_executed_qty_final` → 行; 子成交到达 Q; 补单腿 `_fin1`(显式终态 + 合并终值) | `_final_known`(显式真或容量; **无 terminal 回退**); `request_remaining`; `ledger_qty_closed`; 均价; `_settle_leg_by_identity`(F 时 child > C ⇒ 矛盾) |
| T 终态 | `terminal` | 显式 status(补单腿); 折叠 `non_terminal` 为空且非 partial(maker 行) | `ledger_closed`(金额关闭需 T); `_settle_leg_by_identity`(exhaustion 置 T) — **不再**用于推 F |
| N 金额 | `confirmed_notional`(带号) | 合并器 `cum_quote`(只在终值)→ 折叠 `filled_notional` → `filled` 字典 → 行; 补单腿 `_one`; 子成交集合完整时 | `ledger_totals`(已知金额); `ledger_closed`; 均价; `ledger_inconsistencies`(非有限) |
| N 完整性 | `confirmed_notional_final` / `confirmed_notional_lower` | 合并器 `cum_quote_final` → `cumQuoteFinal` → 折叠 `filled_notional_final` → `venue_notional_final` → 行; 补单腿(合并只发终值 ⇒ 真); 子成交(完整 ⇒ 真, 子集 ⇒ `_lower`) | `ledger_closed`(需真); 均价(需真); `_settle_leg_by_identity`(真时 N 常量, 子集不超) |
| 身份 | `client_id`, `order_id` | 发送的 cid; `known_order_id`(按发送 id 绑定, 回包声称别 id ⇒ None) | `_settle_leg_by_identity`(按 orderId 联接子成交); 结算身份门 `_valid` / `_valid_present`; **提交回包直接读者 `last_fill_details`(第十二轮加门)** |
| 矛盾 | `inconsistent` | 合并器(记录内 / 记录间) / 折叠 / 身份门 / 子成交(重复 id 不同量、超终值、反向) | `ledger_inconsistencies` → `ledger_row_columns.ledger_inconsistent` → RC 第一行「不可测」 |
| 去重证据 | `trade_qty[tid]`, `trade_quote[tid]` | `_settle_leg_by_identity` | 同函数(只增不减 — 第十二轮: 缺 quote 不撤销已记 quote) |

行级列(`_order_row` 由 `ledger_row_columns` 一次写出)与它们的读者:

| 行列 | 读者 |
|---|---|
| `filled_qty`(全部 F 时 Σ L) | `reconcile._exec_qty`(known) |
| `filled_known_qty` / `filled_unknown_qty` | `reconcile._exec_qty`(bounded; **有带就走带, 与 N 无关** — 第十一轮) |
| `filled_notional`(全部 T+N+N_final) | `pilot_metrics`(冻结, **实际读法, 第十四轮据码核对**): M1 缺 N/avg 的行排除, 缺 fee 的行保留 N 并标 `measurement_complete=False`; M3 读金额; **M4 缺 N 的行按 realized 换手 0 计入**(`float(N or 0.0)`; 目标换手与锚数不受影响, M4 门读目标换手); **M5** 缺 intended/N 的行计入 `n_short_unknown` 不算 shortfall, 目标 vs 场所仓位比较照做 —— 不能统称「None 不参与」· `daily_summary` · `watchdog`(平仓行)· `first_anchor_review` / `score_post_fix`(报表)· `anchor_loop`(账本、`neutrality_price` 分母)· `chase_readout.collect`(分母)· RC 仅无账本旧行 |
| `avg_fill_px`(每张 C 与 N 皆终值) | **数量读取**: RC 仅无账本旧行(`_exec_qty` N/avg)与 `_unknown_interval` 旧金额带后备(账本行必写 `filled_unknown_qty`, 不走此后备); **残差计价**: RC `_usable_mark` 候选之一(None ⇒ 退到回读 notional/qty 等候选, 不伪造); **成本报表**: `pilot_metrics` M1(滑点; 冻结)· `scheduler/anchor_loop.neutrality_price` · `ops/chase_readout.collect` · `ops/daily_summary` · `ops/score_post_fix` · `ops/first_anchor_review` —— 第十三轮起: 无均价的成交进「未定价」分子分母之外, 分母只含已定价成交, 覆盖率(n_priced / n, 未定价金额)与 bps 同报, 无已定价成交 ⇒ bps None 而非 0; **后置写者只写 `avg_fill_px_children`**(第十二轮) |
| `ledger_inconsistent` | `reconcile._exec_qty` 第一行 |
| `terminal_reason`(`filled` ⇔ 金额关闭, 否则 `filled_amount_unknown`) | `pilot_metrics`(完整性)· `watchdog` · 报表 |

## 3g. 第十三轮补格(研究员第十二轮四条 P2 + 措辞): 下界比较不等全集; 坏值不因邻字段缺失免检; 身份字段可读性四态跨来源一致; 未定价成本不是零成本
| # | 来源 / 出口 | 事实规则 | 反例格 | 反方向 | 邻格 |
|---|---|---|---|---|---|
| 1 | 子成交金额下界(R12-PARTIAL-N) | 已知金额下界 = Σ 有 quote 的孩子; 与终值 N 的「不超」比较用下界(不要求所有孩子都有金额); 「等于终值」的关闭判断才要求全集 | F 真 C20/N40 + 孩子 5/N50 + 孩子 5/N 缺 ⇒ 下界 50 > 40 ⇒ 矛盾(曾: n_child None 跳过检查, 行 N90 读 70 CLEAN) | 孩子 5/N30 + 5/N 缺 ⇒ 下界 30 ≤ 40, 无矛盾, **已有终值 N40 保留、金额照旧关闭**(第十四轮更正措辞: 子集不撤销终值; 只有没有终值时才写 `_lower`) | 全集 N40 ⇒ 关闭照旧 |
| 2 | 账本非有限金额(R12-N-FINITE) | 坏值不因另一字段缺失而免检: `ledger_inconsistencies` 先查 N 有限性再看 C 是否缺 | C None / N NaN ⇒ 矛盾 ⇒ 行不可测(曾: C 缺提前 continue, 按数量带通过) | C None / N 4 ⇒ 区间 [0,Q] 照旧 | C 坏 / Q 坏 照旧矛盾 |
| 3 | 身份字段四态(R12-ID-SHAPE) | 每个身份字段: **缺键或 None** = 不是证据(跳过); **空串 / 不可解析 / 非有限** = 畸形 ⇒ 不符; **有值** = 比对。三处门(提交回包 / 补查记录 / 结算的提交记录)同一实现 `identity_field`; 完整记录门 `_valid`(allOrders / 查单)仍要求字段齐全 | 提交回包 origQty=NaN ⇒ 不符(曾: 不可解析被跳过 ⇒ 补 6 精确); 空 side ⇒ 三处门一致判不符 | 缺 origQty ⇒ 按发送量记(照旧) | 补查记录 origQty="Infinity" ⇒ 不符 |
| 4 | 成本报表覆盖(R12-COST-COVERAGE) | 无均价的成交不进 bps 的分子分母; 报「已定价 n / 全部 n、未定价金额」; 无已定价成交 ⇒ bps None(不是 0); 名称改为 measured-over-priced | N6 / C 与 avg 未知 ⇒ `neutrality_price` bps None, n_fills_priced 0, unpriced_notional 6(曾 0 bps); `chase_readout` 同 | N6/C3/avg2, mid 1 ⇒ 10000 bps(正控; 夹具尺度) | 一半已定价 ⇒ bps 只按已定价一半, 覆盖率 0.5 |
| 措辞 | DESIGN §3f.1 / `request_remaining` 注释 / API_SEMANTICS 行 44 / §5 avg 读者 | 「按 A 补查」改「先拒不补查」; 删 R5-QC 旧注释; 官方承诺 / 我方兼容政策 / 实际观测三分开写; avg 读者列全(数量读取 / 残差计价 / 成本报表) | — | — | — |

**边界(研究员裁, 我方接受)**: [0, Q] 是合法请求的**保守数量范围**, 不是价格 / 金额事实的精确可行集(正金额排除精确 0、限价可给更高下界 —— 当前合同未用), 也不代表 Q6 已完成。

## 3h. 第十四轮补格(研究员第十三轮: R13-ID-INTEGER / ID-MALFORMED / R13-COST-COMPLETENESS + 口径三处): 无损整数; 畸形不依赖可比值; 已测 = 价与费都已测
| # | 来源 / 出口 | 事实规则 | 反例格 | 反方向 | 邻格 |
|---|---|---|---|---|---|
| 1 | orderId 解析(所有读者: `identity_field` / `known_order_id` / 结算 `_valid` / 子成交联接) | orderId 必须是**无损整数**: 整数或整值浮点/字符串; 小数、NaN、±Inf、文本 ⇒ 畸形(`order_id_value(raw)` 一个实现, 捕 Overflow); 畸形判定**不依赖有没有可比较的 expected** | GET orderId 102.75(数值)对 ACK 102 ⇒ 不再截成 102 接受, 判畸形 ⇒ 请求不可测; GET Infinity ⇒ 不再 OverflowError 穿出 complete_anchor, 判畸形; POST 缺 orderId + GET "badid" ⇒ 畸形(曾: 无 expected 跳过) | 整值 "102" / 102.0 ⇒ 接受 | 子成交 order_id 102.75 ⇒ 不联接(畸形计入 inconsistent 不静默) |
| 2 | 成本诊断的「已测」(`neutrality_price` / `chase_readout.collect`) | 一条成交**已测** ⇔ 价可用(有限正 avg 与 mid)**且**费已知(fee_paid 非 None 且有限); bps 只按已测成交; 分别报「未定价」「费未知」计数与名义; 覆盖率分「名义」与「计数」两种; 无已测 ⇒ None | N6/avg1/mid1 但 fee None ⇒ bps None, n_fee_unknown 1(曾: fee or 0 ⇒ 0 bps; M1 已正确标不完整) | fee 0.06 已知 ⇒ 100 bps | NaN / 负 avg 或 mid ⇒ 归未定价(曾: truthy 当已定价, 出 NaN/负 bps); 价零 ⇒ 未定价(照旧) |
| 口径 | 文档 | (a) 「新增键不改旧键含义」错: `measured_taker_bps_same_side` 分母由全部名义改为已测名义, 混合成交场景数值改变(研究员例 5300 → 10100 bps), `caliber` 文案同改; (b) 冻结 M1/M4/M5 的 None 读法按码写(见 §5); (c) §3g.1 反方向: 已有终值 N40 时子集 N30 不撤销终值, 行照旧关闭; (d) API_SEMANTICS: 官方页面(本次复开)示例**未列** cumQuote/avgPrice, 历史版本来源 = 代码注释 07-26 观测, 未取得正式 required 集合; (e) `chase_readout` 拒绝态逐锚打印补已测名义与覆盖率 | — | — | — |
