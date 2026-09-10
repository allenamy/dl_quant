# 独立研究员第五轮复审(ce7b3cf4)· 辩证处置 + 第六轮修复

> **创建:** 2026-09-10 08:0xZ | **Session:** https://claude.ai/code/session_01H39k5rgyd43mFMNsaBqzeX | **状态:** 处置已定; 第六轮修复在实盘复审分支落码(未合并未部署), 待研究员第六轮复核; 研究管线第五轮已被研究员收口(仍参考态) | **作废条件:** 研究员第六轮复核出具后以其为准; 合并/部署另按验收裁定
> **复审件:** `.claude/worktrees/codex-independent-20260907/multi_asset/exports/research/codex_round5_review_2026-09-10/`(HANDOFF / RESULT / executor · risk · pipeline · account 分册 + root 复跑; 提交 ce7b3cf4)。**被审对象:** 实盘 b840ed9, 研究 d6c26f31(含 0cc16a85), 主线 f1e9a11a; 运行树 d040c74。
> **研究员总判:** 实盘 REQUEST_CHANGES(两条承重漏报可达); 研究管线修复可收口(参考态)。**我方总判: 同意两个判决。两条承重问题都是第五轮「请求生命周期」合同没有实现到底 —— 终态、已知数量、计价完整性三件事仍被同一个字段状态绑在一起。**

---

## §0 一句话

第五轮把「累计已成量 C」与「终态」分开了, 但两处又把它们缠回去: (1) `complete_anchor` 把 k-cancel 的 `unresolved` **无条件**并回 UNKNOWN 集, 于是阶段 B 里已经用撤单 + 查单证明 CANCELED/成交 4 的请求, 仍被当作「仍开」写成 known 4 + 带 6, 持仓 10 通过风控; (2) `request_remaining` 只对「终态 ∧ state=confirmed」归零余量, 而 state=confirmed 要求**金额**可读 —— 于是 EXPIRED/成交 20 但金额不可读的请求(C 可信, 终态)仍贡献 30 的带, 持仓 100 通过风控; 反过来 C=Q 而金额未知被判不可测。研究员的定性我接受: 数量检查必须先于计价, 终态且 C 可信的请求区间是 [C, C], 金额缺失另报。第六轮按这个合同重做, 并把边界项(缺 executedQty 当零、账本行回退到名义/子集均价、bounded 读者不验价、同 id 矛盾覆盖、撤单失败丢已读事实、`-3c99` 假设)一并关闭。

没有任何一项影响策略 alpha 或回测数字; 研究员本轮亦未产生新收益结论。

---

## §1 两条承重项(全部接受, P1)

| # | 研究员发现(原 `complete_anchor` / 原 broker → RC/PB/WD 实达) | 我方复核 | 第六轮修复(实盘分支 `review/b0a573a1-executor` 07929ed) | 证据(`tests_request_identity_unknown.py` 136/136) |
|---|---|---|---|---|
| R5-E1 | 首次撤单失败 → allOrders PARTIALLY_FILLED 4 → 结算再撤成功、查单 CANCELED/4 → `found` 且无 unknown, 但 `anchor_loop.py:2162–2163` 无条件并回旧 `cancels.unresolved` ⇒ maker 行 terminal=False / known 4 / 带 6; 持仓 10 两门 CLEAN; 原 pin 仍在 | **VERIFIED**(第五轮我写的两行) | `_unres0 − _found` 才进 UNKNOWN(按请求身份让较新的可靠终态覆盖旧撤单未决); 已确认终态的名清除撤单 pin(`stuck_orders.clear`, 带证据文字); `apply_fill_details` 把折叠的终态性 `venue_terminal` 传到计划, UNKNOWN 路径的 maker 行请求 `terminal` 取自它 ⇒ 终态 ∧ C 可信 ⇒ 带 0 | [29]: 终态折叠 + C 4 ⇒ known_qty 4 / 带 None / filled_qty 4; 持仓 4 CLEAN、10 异常 6; 仍开 + C 4 ⇒ 带 6(正控); wiring 断言 |
| R5-QA | EXPIRED 执行 20/50 金额不可读 + FILLED 50: 账本 terminal=True / C 20 但 state=unknown ⇒ `request_remaining` 不归零 ⇒ known 70 + 带 30; 持仓 100 CLEAN。反向: C=Q=50 金额未知 ⇒ filled_qty/fn 皆 None ⇒ 不可测 | **VERIFIED**(第五轮 `if terminal and st == "confirmed"`) | `request_remaining`: **C 可信 ⇒ 终态则 0, 否则 Q−|C|; C 未知 ⇒ |Q|(终态与否都不能推出过去成交为 0)**; 新 `ledger_qty_closed`: 全部已发请求终态且 C 可信 ⇒ `filled_qty` = Σ C(金额可否读无关), 金额未知另留 `filled_notional=None` + `filled_amount_unknown` | [30]: 20(无金额)+50 ⇒ filled_qty 70 / 带 None; 持仓 70 CLEAN、100 异常 30; C=Q 金额未知 ⇒ filled_qty 100 已知 |

## §2 边界项(全部接受)

| # | 研究员发现 | 判定 | 第六轮修复 | 证据 |
|---|---|---|---|---|
| R5-QB (P1 防御) | decoder 把终态**缺失/null** executedQty 经 `or 0` 当明确零, 即使同请求 cumQuote 100 / avgPrice 2 ⇒ 总量 50 | 接受 | 只有**明确**的 `"0"` 才是零; 缺失时落到同请求 cumQuote/avgPrice 恒等式推导(标 `executed_qty_source`), 都读不到 ⇒ None | [31] |
| R5-QC (P1 防御) | 首请求金额 100 而数量/均价不可读, 第二请求 50@1 ⇒ closed 仍 True, 总金额 150 搭配子集均价 1 ⇒ RC 150 | 接受。「一个量一个读者」在 reconcile 侧没有做到底 | 账本行的均价只在**每个**已执行请求同时贡献金额与数量时写出; reconcile 对账本行**拒绝**名义/均价回退(quantity 只来自 `filled_qty`/`filled_known_qty`, 否则不可测); 同请求 n/avg 推导保留在生产者(研究员第 1 点) | [32]: filled 150 / filled_qty None / avg None ⇒ 不可测 |
| R5-QD (P1 旧行) | 旧 bounded 行 fn=None / known 50 / avg NaN ⇒ NaN 残差两门 CLEAN | 接受。Q7 只修了 fn 非空路径 | bounded 读者校验价格有限且 > 0 | [33] |
| R5-QE (P2) | 同 trade id 的 qty 由 20 改 50、价 2 改 3 被覆盖不记矛盾 | 接受 | 同 id 不同 qty/quote ⇒ `inconsistent`, 首次读数保留 | [34] |
| R5-E2 (P2) | 查单已给 PARTIAL 4, 撤失败却保留 known 0 / 带 10 | 接受 | 结算返回 `partial`(已读到的执行量 + 仍开标记), `complete_anchor` 并入 details(是事实不是结算) ⇒ maker 行 known 4 / 带 6 | [35] |
| ID 边界 | `-3c99` 假设: 100 块时 maker 已发 1 才在补单被拒 | 接受 | 预检按每个计划的**真实块数**(`split_for_market(|qty|, cap, step)`)算最长 id | [36] |
| 研究员对我方自报四点的答复 | (1) 同请求 n/avg 回退可有条件保留 (2) 二次撤单方向对但状态结算不完整 (3) 完全未知 IOC 仍未决合理 (4) 预检有真实边界 | 全部接受 | (1) 保留在生产者、拒绝在读者; (2) 本轮 R5-E1; (3) C 未知 ⇒ |Q| 已按此; (4) 本轮 ID 边界 | — |

## §3 Q6 预注册(接受方向, 先修数学)

研究员指出 §1.1 的字面递推对迟到证据得 −50、及时到达得 +30, 而正确净未解释均为 +30。**接受并已修订**(`docs/PREREG_reconcile_carry_forward_unexplained_2026-09-10.md` 修订 1): 双时钟(事件时间 / 观察时间), E_s 改为**累计恒等式**(以启动/重启边界回读为起点重算, 迟到证据收窄同一请求、从不产生第二份执行), 启动/重启边界与历史审计分离, §3.2 加终态 C80、§3.3 明确 first/second 为持仓水平且核解集而非计数(两种错合同计数恰都 5151)。仍未落码; 需研究员对修订 1 复核 + 用户字 + 41 天副本回放。

## §4 研究管线

研究员接受第五轮资格合同修复(冻结 ELIGIBILITY_CONTRACT、逐臂书绑定、严格 schema、批准源码检查; 根独立复跑正式空表 0 / 测试 strict 正控 4 / 真 G2 冒用 0 / 换书 0)。**仍为参考态**: 物理 BUNDLE_export 门未实现, 正式候选资格未开放, 无任何真实候选被认证。本轮研究分支无新改动。

## §5 我方承认的新错误(第五轮引入)
1. 「较新的可靠终态覆盖旧未决」只做了 `_still_open`, 没做 `cancels.unresolved`; pin 也没清 —— 同一个「按请求身份结算」我只实现了一半。
2. 把「金额可读」当成「C 可信」的前提: `state=confirmed` 绑定金额, 余量归零又绑定 state ⇒ 数量授权依赖计价完整性。
3. 「−3c99」是我的假设, 不是计划的事实。
4. 读者侧仍留着名义/均价回退, 与「一个量一个读者」自相矛盾。
5. 第五轮说「预检保证全锚全有或全无」超出了它能保证的范围(100 块时 maker 已发)。

## §6 状态

| 件 | 提交 | 电池 | 状态 |
|---|---|---|---|
| 实盘分支 第六轮 | `review/b0a573a1-executor` **07929ed** | 132/132 全绿 | 已推送, 待复核 |
| 研究分支 | d6c26f31(第五轮, 研究员已收口) | 151/151 | 参考态 |
| 研究主线 | 本文 + PREREG 修订 1 + journal/STATE | — | — |

**未闭合(明写)**: Q6 落码与 41 天回放(先过修订 1 复核); −2013 终局性(显式假设); 跨进程同秒平仓 id; M5 对 reconstructed 行再封存; income 缺行/币种换算; 物理 BUNDLE_export 门; 52 行 orders 写回仍等部署。协议不变: 研究员第六轮复核 → 分别合并 → 部署另裁。运行树 d040c74 零接触(VERIFIED)。

## §7 数字标签
研究员列数字 = 其复算(VERIFIED by them); 套件/电池计数 VERIFIED(本机); 其余为规则。
