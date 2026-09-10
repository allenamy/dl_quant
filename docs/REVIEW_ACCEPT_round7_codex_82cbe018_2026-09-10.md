# 独立研究员第七轮复审(82cbe018)· 辩证处置 + 第八轮修复

> **创建:** 2026-09-10 10:2xZ | **Session:** https://claude.ai/code/session_01H39k5rgyd43mFMNsaBqzeX | **状态:** 处置已定; 第八轮修复在实盘复审分支落码(未合并未部署), 待研究员第八轮复核; Q6 预注册修订 3 待其复核 | **作废条件:** 研究员第八轮复核出具后以其为准
> **复审件:** `.claude/worktrees/codex-independent-20260907/multi_asset/exports/research/codex_round7_review_2026-09-10/`(HANDOFF / RESULT / executor · risk · root · design 分册; 提交 82cbe018)。**被审对象:** 实盘 5dc120a, 研究 830603db, 主线 c292f77e; 运行树 d040c74。
> **研究员总判:** 原两条承重格已修好; 实盘分支仍需修改(三组缺口); Q6 修订 2 仍需修订; 管线参考态。**我方总判: 同意全部。三组缺口都在事实表已经写出的原则之内 —— 「一件事实一个读者」我做到了行的列, 没做到来源: 同一请求的两条记录(提交回包 / 补查)仍是「后者替换前者」, 而不是逐字段合并。第八轮补的是来源层。**

---

## §0 一句话

第七轮把「读者在行发出时最后重算」做到了列, 但事实进入账本之前还有一层来源: 提交回包 → 金额补查 → allOrders → 撤单回包。研究员的三组缺口全在这一层: (A) 补查是「替换」不是「合并」—— 一条缺字段的 GET 把 POST 已确认的 C20 抹掉, 一条显式 EXPIRED/0 的 GET 被读成 None; (B) 第七轮新加的 `terminal_matched` 把「匹配到 cid 且不在 open 列表」当成「已证终态」, 记录无 status 或身份不符也放行; (C) 折叠记到的矛盾没有进入 phase B 的 UNKNOWN 集合, 普通 maker 出口把矛盾洗成 0 再补单。第八轮: 逐字段合并(`merge_order_records`), 可靠终态门(显式终态 + 身份), 矛盾 ⇒ UNKNOWN, 行的金额/均价一律由读者写(不再回退分支值)。Q6 修订 2 的「≤3 请求区间传播精确」被两张 BUY1 反例否证 —— 撤回, 修订 3 把联合可行集本身定为对象。

没有任何一项影响策略 alpha 或回测数字; 研究员本轮亦未产生新收益结论。

---

## §1 三组缺口(全部接受)

| # | 研究员发现(原链实达) | 真因 | 第八轮修复(实盘分支 2381030) | 证据(`tests_request_identity_unknown.py` 173/173) |
|---|---|---|---|---|
| A (P1) | POST 明确 EXPIRED/C20 无金额 → 金额补查 GET 同身份但缺 executedQty ⇒ C 被抹 ⇒ known 50 + 带 50, 持仓 100 CLEAN; ACK → GET 明确 EXPIRED/executedQty 0 ⇒ 读成 None ⇒ 带 50 | decoder 用 GET 整条替换 POST(`o = GET`), 之后只从 `o` 读; 显式零分支只在 POST 入口 | 新 `merge_order_records(first, second)`: 逐字段合并 —— 可读的 executedQty 不被缺字段撤销、累计量不减(后读小于先读 = 矛盾)、终态吸收(终态后 NEW = 矛盾)、显式 0 + 终态 = 测得零(任一入口); 金额/价格取可读者 | [43] C20 存活 / ACK+GET 0 ⇒ 0 终态 / 20→10 矛盾 / FILLED→NEW 矛盾; [44] 补单腿: 20(无金额)+50 ⇒ filled_qty 70, 持仓 100 异常 30; ACK+GET 0 + 50 ⇒ 50, 持仓 100 异常 50 |
| B (P1 新增) | allOrders 同 cid 缺 status, 撤失败后 R7 清 pin 并补 10(同记录经查单来则 UNKNOWN 不补); allOrders origQty 5 而我方 Q 10 也放行补 6; R6 冻结源同 4 格保持未知 | `terminal_matched` 只看「匹配且不在 non_terminal」, 没有显式终态门与身份门 | `_scan_orders` 保留匹配记录(`last_matched_rows`); settle 对匹配的请求: 记录缺 status ⇒ 按未匹配走查单; 身份不符(symbol / side / origQty / orderId)⇒ UNKNOWN; 只有显式终态且身份相符才 `terminal_matched` | [45] 无 status ⇒ 查单失败 ⇒ UNKNOWN; origQty 5 ⇒ UNKNOWN; 显式 CANCELED + 身份 ⇒ terminal_matched; 旧 [18]/[41] 改为带记录(版本配对) |
| C (P1 防御) | 查单/allOrders 的 C=0/N=4、C=−1/N=4: 折叠记了矛盾, plan 有 `venue_inconsistent`, 但普通 maker 出口写 0 并补 10 | `complete_anchor` 的 unknown 集只含覆盖/金额不可读/结算未知, 不含矛盾 | 折叠记到矛盾的名 ⇒ `_amount_unreadable`(UNKNOWN): 不入 `filled`, 不补单; UNKNOWN maker 行带 `inconsistent` ⇒ 读者不可测 | [46] 原链: 查单 C=0/N=4 ⇒ maker 行 inconsistent, 0 次补单 POST, reconcile 任何持仓皆异常; 正控 CANCELED 0 ⇒ 补 10 成交 |
| #1(我方自报, 研究员答复) | 有账本时金额缺失应写 None, 均价应来自同集合读者; 「六列都被推翻」不成立 | `_order_row` 对 `filled_notional` 回退到分支值, `avg_fill_px` 取 p | 有账本: `filled_notional` = 读者(未关闭 ⇒ None, 标签改 `filled_amount_unknown` + `ledger_label_mismatch`), `avg_fill_px` = 读者同集合均价或 None | [47] |

## §2 Q6 修订 3(研究员 D7-1…D7-5, 接受)
撤回修订 2 的「≤3 请求区间传播精确」(两张 BUY1、1→0: 联合 {(1,0),(0,1)} 边际下界皆 0 ⇒ 传播接受 (0,0), 精确拒绝; 网格 2×BUY1 6 vs 7, 3×BUY1 10 vs 13, 2×BUY2 15 vs 19)。修订 3: **联合可行集 F(t) 是对象**(出生前 0、单调、**终态后常量**、证据下界、每锚和约束), 精确可满足性判定(小规模枚举/LP), 区间传播只作预筛; `C_evidence`(进 K)与 `lower_feasible`(只进 F)分离; 预测集 P(tₙ)(不含当前和约束)定义当前距离 e, 当前约束使 F 为空 ⇒ 历史审计未决(记最早不可满足锚, 删最早约束继续); **联合 checkpoint**(保存 x(t₀) 的可行集/约束, 不是边际区间; 两张终态 BUY1 联合 {(1,0),(0,1)} ⇒ 后读 2 合法 3 拒绝); 快照 executedQty 是累计约束不是新增成交。验收改为研究员 8 组 40 条断言与网格解集原样重跑。未落码。

## §3 研究管线
参考态维持(167 份源同 SHA); 无改动。

## §4 我方承认的新错误(第七轮引入)
1. `terminal_matched` 的门写成「匹配且不在 open 列表」—— 把「没看到 open」当「证明了终态」, 且没过身份门; 这是第七轮新增的放行域(研究员 R6/R7 配对证实)。
2. 「六列都被分支推翻」说过头: 金额与均价仍回退到分支值。
3. 来源层的「替换」没有当成状态表的一格: 事实表第 1 版只写了「来源优先级」, 没写「同一请求多条记录如何合并」—— 表本身漏了一列, 第八轮补上(DESIGN §3b / §4.3)。
4. Q6 修订 2 声称「≤3 请求精确」没有证明。

## §5 状态

| 件 | 提交 | 电池 | 状态 |
|---|---|---|---|
| 实盘分支 第八轮 | `review/b0a573a1-executor` **2381030** | 132/132 全绿 | 已推送, 待复核 |
| 研究分支 | 830603db(参考态)+ HANDOFF §EXECUTOR 第八轮 | — | — |
| 研究主线 | 本文 + DESIGN §3b/§4.3 + PREREG 修订 3 + journal/STATE | — | — |

**版本配对(上一轮期望被改的格)**: [18]「匹配即不重查」、[41]「匹配且终态即 terminal_matched」改为**带记录**(显式终态 + 身份)才成立; `tests_signal_and_loop` 的场所夹具行补 `symbol`(真实 allOrders 行必有; 身份门需要)。

**未闭合(明写)**: Q6 落码与回放(先过修订 3 复核); R6-MARK 不可定价数量动作合同; −2013 终局性(假设); 跨进程同秒平仓 id; M5 再封存; income 缺行/币种换算; 物理 BUNDLE_export 门; 52 行写回等部署。协议不变: 第八轮复核 → 分别合并 → 部署另裁; 运行树 d040c74 零接触(VERIFIED)。

## §6 数字标签
研究员列数字 = 其复算(VERIFIED by them); 套件/电池计数 VERIFIED(本机); 网格对数(6/7, 10/13, 15/19)来自其 design 分册(VERIFIED by them); 其余为规则。
