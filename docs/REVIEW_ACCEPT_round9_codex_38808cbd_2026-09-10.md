# 独立研究员第九轮复审(38808cbd)· 辩证处置 + 第十轮修复

> **创建:** 2026-09-10 12:3xZ | **Session:** https://claude.ai/code/session_01H39k5rgyd43mFMNsaBqzeX | **状态:** 处置已定; 第十轮修复在实盘复审分支落码(未合并未部署), 待研究员第十轮复核; Q6 修订 4 数学已被接受, 进入实现验证阶段(未落码) | **作废条件:** 研究员第十轮复核出具后以其为准
> **复审件:** `.claude/worktrees/codex-independent-20260907/multi_asset/exports/research/codex_round9_review_2026-09-10/`(HANDOFF / RESULT / executor · risk · root · design 分册; 提交 38808cbd; 研究员自报 29 个入口独立复跑)。**被审对象:** 实盘 7b49dec, 研究 f9a86d8e, 主线 0c98b6a8; 运行树 d040c74。
> **研究员总判:** 原五组修复成立; 执行器整包仍 REQUEST_CHANGES(两类承重: 漏报 = 失败读数撤销已读事实; 误报 = 开单下界被升级为最终量); Q6 修订 4 数学通过。**我方总判: 同意全部。两类缺口仍是同一种错的两个面: 第九轮把「记录集合」合并对了, 但 (1) 合并输出只有一个数量, 没有说它是最终总量还是开单快照的下界 —— 读者用「终态 + 有限 C」当精确关闭; (2) 失败出口直接 return, 已读到的事实不进集合。第十轮把请求事实从四件扩成五件(σ / Q / L / T / F), 并让每个 UNKNOWN 出口先折叠手里的记录(DESIGN §3d)。**

---

## §0 一句话

**误报**(R9-QFINAL): POST PARTIALLY_FILLED 20 → GET EXPIRED 缺 C。第九轮合并保留 20 且 terminal=True, 读者写出精确 ±70、带 0; 但终态只证明「不会再成交」, 不证明「结束前只成交了 20」, 第一张最终量 F ∈ [20, 50], 两张合法区间 [70, 100], 合法 ±80 被 5b/5e/WD 报警。**漏报**(R9-FACT-EXIT): k-cancel 已回 CANCELED 4, 随后查单运输耗尽 / −2013 ⇒ 第九轮的异常出口直接 return, 4 退化成 0–10 带, 持仓 10 放行; 结算撤单回 CANCELED 6 后复查失败, 6 丢失退回 4+6; POST 自己的 PARTIALLY_FILLED 4 从不进集合。**修复**: 合并器输出 `executed_qty_final`(只有终态快照或终态后的快照给出的 C 才是最终总量), 一路带到账本 `confirmed_qty_final`; 读者的余量 = F ? 0 : Q − L(终态与否都一样), `filled_qty` 只在全部 F 时写; 子成交只抬下界、永不证明总量(到达 Q 除外); 每个 UNKNOWN 出口先 `_carry` 已有记录; 提交回包是记录集合第一条; status-only 撤单回包只贡献状态且证明存在(之后 −2013 是矛盾不是 ABSENT); 终态快照之间的金额也常量; 措辞更正(终态常量只在终态快照之间)。

没有任何一项影响策略 alpha 或回测数字; 研究员本轮亦未产生新收益结论。

---

## §1 承重缺口(全部接受)

| # | 研究员发现(原链实达) | 真因 | 第十轮修复(实盘分支 63b51d3) | 证据(`tests_request_identity_unknown.py` 258/258; 旧码上红) |
|---|---|---|---|---|
| R9-QFINAL (P1 误报) | 第一张 POST OPEN 累计 20, GET EXPIRED 缺 C/N/avg, 第二张 50 ⇒ 行精确 ±70 / 带 0, 合法 ±80/90/100 报警(5b ANOMALOUS、5e BREAK、WD True); SELL 对称 | 合并输出没有「完整性类型」: `c_final=20` 与 `c_term=None` 的差别没传下去; `request_remaining` / `ledger_qty_closed` 用 terminal + 有限 C 当精确 | 五件事实: L(`confirmed_qty`, 下界)与 F(`confirmed_qty_final`)分离; `merge_order_records` 输出 `executed_qty_final`(只有终态快照或其后快照的 C 为真), 正典记录 `executedQtyFinal` → 折叠 `executed_qty_final` → 计划 `venue_executed_qty_final` → 账本; 读者: 余量 = F ? 0 : Q−L, 关闭只在全部 F; 缺键旧行按 terminal 读(遗留规则, 新行必写) | [55] 13 格: 合并 5 格; 原补单链 BUY/SELL: known ±70 / 带 30 / filled_qty None, 回读 70/80/100 CLEAN、60/110 异常; 正控终态 20 ⇒ 精确 70、80 异常 10 |
| R9-CHILD-SUPPORT (P1 条件) | 终态但总量未知的请求, 只给一条 child 30 ⇒ 关闭为精确 30 / 行 80 精确; 开单 20 终态 + child 30 被判「超过终态 20」 | `_settle_leg_by_identity` 在 prev_c 缺失时接纳子集为 C, terminal 随即满足读者的精确关闭; 第九轮的「超过终态」保护读的是错误的 finality | 子成交只抬 L, 永不置 F(到达 Q ⇒ F 由容量); 「超过」检查只对 F=真的 C | [55] 5 格: 终态未知 + child 30 ⇒ known 30 / 带 70 / filled_qty None; 开单 20 + child 30 ⇒ 30 无矛盾; F=真 20 + child 10 ⇒ 20 保留; F=真 20 + child 30 ⇒ 矛盾(照旧); child 到 Q ⇒ 100 关闭 |
| R9-FACT-EXIT (P1 漏报) | k-cancel CANCELED 4 → 查单运输耗尽 ⇒ known 0 / 带 10, 持仓 0/4/10 全 CLEAN; 同上 −2013 ⇒ 同; 首撤失败 → page PARTIAL 4 → 结算撤单 CANCELED 6 → 复查失败 ⇒ 4 + 带 6; POST PARTIALLY_FILLED 4 + status-only 撤单 + 稀疏终态查单 ⇒ 0 + 带 10(持仓 0 放行) | `_resolve_open` 把撤单与复查放在同一 try, 复查抛错即 return, 刚读到的 c1 未合并; 查单异常出口不折入 k-cancel 事实; `_records` 不含 POST 回包; status-only 撤单被忽略后凭 −2013 判 ABSENT | `_carry(p, sym, cid, recs, why)`: 每个 UNKNOWN 出口(查单异常 / 满页 / 结算撤单后复查失败 / 未达)先把手里的记录合并成事实; `_resolve_open` 撤单与复查分两个 try; `_records` 以 `known_submit_record` 的提交回包为第一条(身份按「带字段才比对」); status-only 撤单回包只贡献状态(无身份字段者只取 status)且证明存在 ⇒ −2013 是矛盾(不可测), ABSENT 仅在撤单 −2011/失败之后 | [56] 9 格 + [57] 3 格 + [58] 4 格: 原链 k-cancel 4 + 查单耗尽 ⇒ known 4 / 带 0 / filled_qty 4, 回读 4 CLEAN、0/10 异常; −2013 ⇒ 不可测; 结算撤单 6 + 复查失败 ⇒ 6 终值; POST 4 + status-only + 稀疏 ⇒ known 4 / 带 6, 回读 4/10 CLEAN、14 异常、0 不可对账(无 mark, 不放行) |
| 金额 P2(§5) | 终态金额 40→60 同 C20 无矛盾 | 金额没有终态常量 | 终态快照之间金额常量 | [59] 3 格 |
| 措辞 P2(risk §5) | DESIGN §3c 行 2「之前任何不同 C 都矛盾」过宽 | 文案 | 更正为「终态快照之间常量; 之前的开单快照是下界」 | [55] 邻格 OPEN10 → 终态 20 |

**研究员对我方三条自报的答复及处理**: (1) 最终 C 已知、金额未知时不补 = 登记的保守动作合同 ✓(不改); (2) status-only DELETE: 本轮改为「只贡献状态、证明存在」(不再被凭 −2013 判 ABSENT); (3) 无 ACK 不豁免其他身份事实 ✓(已如此; 时窗核对未做, 登记)。研究员另指出 R8 夹具「兄弟腿 5 + 查单腿 3 应折成 8」与「先 CANCELED 后 PARTIAL 应为矛盾」两处旧期望更正 —— 同意, 均为第九轮行为的正确后果。

## §2 Q6 修订 4
研究员 design 分册 `ACCEPT_DESIGN_REV4`: 顺时序准入等价于「可满足子集中按锚时间字典序最大的保留向量」, 确定、非全局最大基数; 迟到重建按「全依赖前缀」读法(不是只重算 `anchor ≥ event_time`); 硬事实矛盾保持不可测。可进入实现与独立回归; 41 天回放在实现审查之后。**本轮无预注册改动**; 实现待另排(先过执行器收口)。

## §3 研究管线
参考态维持; 无改动。

## §4 我方承认的新错误(第九轮引入或遗留)
1. 合并器算对了 c_term 与 c_final 的区别, 却只输出一个数 —— 「一件事实一个字段」在这里漏了「完整性类型」这一件事实。
2. 第九轮的「终态常量」保护读的是 `terminal + 有限 C`, 把开单下界当最终量 —— 新保护规则把上游的错误 finality 传导成了误报。
3. 成功路径修了, 失败出口没修: `_resolve_open` 同一 try、查单异常出口、满页出口都直接 return; 「每个出口丢了哪件事实」的自审(方法记忆第六条)没有做到「每个」。
4. `_records` 漏了记录集合里最早的一条: POST 自己的回包。
5. status-only 撤单回包被当成「无可注入」而整条忽略, 忽略了它证明「存在」这件事实。
6. DESIGN §3c 行 2 措辞过宽(「之前任何不同 C」)。

## §5 状态

| 件 | 提交 | 电池 | 状态 |
|---|---|---|---|
| 实盘分支 第十轮 | `review/b0a573a1-executor` **63b51d3** | 132/132 全绿(notify_audit 副本 12:33Z 刷新) | 已推送, 待复核 |
| 研究分支 | f9a86d8e → HANDOFF §EXECUTOR 第十轮 | — | — |
| 研究主线 | 本文 + DESIGN §3d / §4.11–4.12 + journal/STATE | — | — |

**版本配对(上一轮期望被改的格)**: 假 broker 的 `last_fill_details` 夹具(6 处)、手写折叠/计划夹具([29])补 `executed_qty_final` / `venue_executed_qty_final`(真实生产者现在必写); [49] 夹具 `confirmed_qty_final=True`(它模拟的是场所终态 C 20); `_chain` 可注入提交记录(同进程生产时 broker.actions 天然存在); 内部「absent 0」与「nothing executed 0」字典标 final。其余 224 项原样保留。

**未闭合(明写)**: Q6 实现与回放; 同快照内 C×avg 与 N 一致性(容差待场所精度); 已知路径 maker 行仍无账本(数量由同快照 N/avg 读); 时窗核对; R6-MARK; −2013 终局性(假设); 跨进程同秒平仓 id; M5 再封存; income 缺行/币种换算; 物理 BUNDLE_export 门; 52 行写回等部署。协议不变: 第十轮复核 → 分别合并 → 部署另裁; 运行树 d040c74 零接触(VERIFIED)。

## §6 数字标签
研究员列数字(20/50/70/80/4/6/10/14, 29 入口)= 其复算(VERIFIED by them); 套件/电池计数与旧码红格计数 VERIFIED(本机); 其余为规则。
