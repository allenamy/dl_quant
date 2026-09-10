# 独立研究员第十轮复审(f79dc8cd)· 辩证处置 + 第十一轮修复

> **创建:** 2026-09-10 14:2xZ | **Session:** https://claude.ai/code/session_01H39k5rgyd43mFMNsaBqzeX | **状态:** 处置已定; 第十一轮修复在实盘复审分支落码(未合并未部署), 待研究员第十一轮复核; Q6 修订 4 保持接受(未落码) | **作废条件:** 研究员第十一轮复核出具后以其为准
> **复审件:** `.claude/worktrees/codex-independent-20260907/multi_asset/exports/research/codex_round10_review_2026-09-10/`(HANDOFF / RESULT / executor · risk · root 分册; 提交 f79dc8cd; 研究员自报 29 个入口 + 69 条合同检查独立复跑)。**被审对象:** 实盘 63b51d3, 研究 262714b9, 主线 ae352170; 运行树 d040c74。
> **研究员总判:** 原反例已修复; 实盘分支仍需修改(三项: 普通 maker 路径误报 / 异常回包出口漏报 / 子成交消费者失配); 三条自报逐条答复; Q6 修订 4 保持接受; 管线参考态。**我方总判: 同意全部, 含三条自报答复(旧行缺 F 按 terminal 读的理由不成立; IOC 无 status 置 F 是假设; POST 身份被回包 CID 决定)。三项仍是第十轮那种错的第三个面: F 带到了账本, 但没有贯穿每个读者 —— 普通 maker 行没有账本, 读者仍用 N/avg; 金额没有自己的完整性; 「每个出口」又漏了一个。**

---

## §0 一句话

**误报**(R10-MAKER-F): maker OPEN C4/N4 → 终态只有 N6。合并器正确保留 C4 且 F=假, 却用最终 N6 除以旧下界 C4 造出 avg 1.5(不属于任何快照); 普通 maker 行没有账本, RC 用 N/avg 读成精确 4, 加补单 4 ⇒ 精确 8, 合法 10 被判残差 +2、PB BREAK、WD 触发。**漏报**(R10-NONOBJECT-CARRY): 查单答 JSON list 的出口没有 `_carry`, 已读 CANCELED 4 退化成 0–10。**失配**(R10-CHILD-CONSUMER): 子成交子集 30 把 `confirmed_notional` 写成 30, 金额关闭 ⇒ `filled_notional` 80; RC 因 N 非 None 跳过正确的 known 80 / 带 20, 落入「账本行无确定数量 ⇒ 不可测」, 合法 80/90/100 报警。**修复**: 合并器均价回退只在 C 为终值时; 有场所事实的 maker 行一律带账本(数量列由读者写); 非对象出口 `_carry`; 金额有自己的完整性(`confirmed_notional_final`: 子集只写 `_lower`, 金额关闭与均价都要求终值); RC 账本行有带就走带分支; `_final_known` 不再回退 terminal(缺键 / None 皆非终值; L 到 Q 按容量终值); 补单回包无 status 不终态不 F; 提交记录按我方发送的 client_id 绑定。

没有任何一项影响策略 alpha 或回测数字; 研究员本轮亦未产生新收益结论。

---

## §1 三项 + 三条自报(全部接受)

| # | 研究员发现(原链实达) | 真因 | 第十一轮修复(实盘分支 6705bb3) | 证据(`tests_request_identity_unknown.py` 279/279; 旧码上红) |
|---|---|---|---|---|
| R10-MAKER-F (P1 误报) | maker Q10 POST PARTIALLY_FILLED C4/N4/avg1 → status-only 撤单 → 终态 GET 只有 N6 ⇒ avg 1.5 ⇒ 普通 maker 无账本 ⇒ RC 精确 4 + 补 4 = 8; 回读 10/12/14 全 BREAK | `merge_order_records` 的 `n_final / c_final` 回退不看 C 是否终值; 普通 maker 行没有 `request_ledger`, `_exec_qty` 用旧 N/avg 规则 | 均价回退只在 `c_final_known`; `apply_fill_details` 标 `_venue_facts`, 有场所事实的 maker 行带账本(L / F / T / N / N_final), 读者写数量列; `ledger_row_columns` 的均价要求每张贡献请求 C 与 N 皆终值 | [60] 5 格: 合并 avg None; 原链 maker 行账本 known 4 / 带 6 / 金额 6 / 价 None, 补 4, 回读 8/10/14 CLEAN、6/16 异常; 正控 C6/N6/avg1 ⇒ 精确 6, 10 CLEAN、14 异常 4 |
| R10-NONOBJECT-CARRY (P1 漏报) | 已有 CANCELED C4/N4, 查单答 JSON list ⇒ known 0 / 带 10, 回读 0/4/10 全 CLEAN | 第十轮的 `_carry` 漏了「查单答非对象」出口 | 该出口也 `_carry` | [61] 4 格: 原链 ⇒ known 4 / 带 0 / filled_qty 4, 回读 4 CLEAN、0/10 异常; 正控对象 ⇒ 4 + 补 6 |
| R10-CHILD-CONSUMER (条件性 P1) | 终态未知 C + child 30(+50): 数量列 known 80 / 带 20 正确, 但 `filled_notional` 80 关闭; RC 因 N 非 None 跳过带 ⇒ 不可测 ⇒ 5b ANOMALOUS、WD True | `ledger_closed` 不要求金额集合完整; `_exec_qty` 只在 `filled_notional is None` 时进带分支 | 金额有自己的完整性: 子集只写 `confirmed_notional_lower`(到达 Q 或与终值集相等才写 `confirmed_notional` + `_final`), `ledger_closed` 要求 `confirmed_notional_final`; RC 账本行有带就走带分支, 与 N 无关 | [62] 5 格: 子集 30 ⇒ 金额不关闭(标签 filled_amount_unknown), known 30 / 带 70, RC 30/80/100 CLEAN、20/110 异常; 手写行 N80 + 带 20 ⇒ 读者走带; 子集到 Q ⇒ 数量与金额皆终值 |
| 自报 1(旧行缺 F 按 terminal) | 实盘 40 日 67,588 行无一带 `request_ledger` ⇒ 无遗留人口; 缺键与显式 None 都走回退 | 回退是「缺键 ⇒ 假设」 | `_final_known` 只认显式真或 L 到达 Q(容量); 缺键 / None 皆非终值 | [63] 4 格 + 版本配对 [47] |
| 自报 2(IOC 无 status 置 F) | wire 是 MARKET + RESULT, 无 timeInForce; 合成 C20 无 status + GET 失败 + 50 ⇒ 精确 ±70, ±80 误报 | 本地 tif 名当作 wire 合同 | 补单请求终态只来自显式 status; 无 status ⇒ 不终态不 F | [64]: known 70 / 带 30, 80 CLEAN |
| 自报 3(POST 身份按回包 CID) | 发 A, 回包声称 CID=B/101 ⇒ lookup(B) 返回 A 的记录, 现字段门通过, orderId 101 | 匹配键是「回包 CID 或我方 id」, 回包决定归属 | `_submit_action_for` 按我方发送的 `order.client_id` 选记录; 回包声称别的 CID ⇒ `known_order_id` None, 现字段门判「回包记在别的 id 下」⇒ 不可测 | [65] 3 格 |

**研究员 §5 边界**: C=Q 但来源仍 OPEN/稀疏 ⇒ 区间退化为点, 部分路径仍 F 假 ⇒ 本轮按容量规则置终值(`_final_known` 的第二条)。R6-MARK(无 mark 的「不可对账」不触发 halt)维持为动作合同未闭合项, 本轮不改。

## §2 Q6
修订 4 保持接受; 本轮无预注册改动; 实现 + 独立回归 + 41 天回放另排。

## §3 研究管线
参考态维持(168 路径 167 不变); 无改动。

## §4 我方承认的新错误(第十轮遗留)
1. F 带到了账本却没贯穿每个读者: 普通 maker 行是没有账本的读者, 合并器均价回退是没有看 F 的读者, RC 的带分支是被 N 挡住的读者 —— 「一件事实一个读者」在这里应读作「每个读者都只认完整性字段」。
2. 金额没有自己的完整性 —— 第十轮只给了数量 F, 子成交子集的金额照旧关闭。
3. 「每个出口」清单又漏一个(非对象回包); 出口清单必须写成显式枚举并逐个测(§4.12 已写, 但清单本身不全)。
4. 三条自报都被研究员用证据推翻: 遗留人口不存在; IOC 终态是假设; 身份绑定让回包决定归属。自报时说「假设」不等于验证过。

## §5 状态

| 件 | 提交 | 电池 | 状态 |
|---|---|---|---|
| 实盘分支 第十一轮 | `review/b0a573a1-executor` **6705bb3** | 132/132 全绿(notify_audit 副本 13:59Z 刷新) | 已推送, 待复核 |
| 研究分支 | 262714b9 → HANDOFF §EXECUTOR 第十一轮 | — | — |
| 研究主线 | 本文 + DESIGN §3e / §4.13–4.14 + journal/STATE | — | — |

**版本配对(上一轮期望被改的格)**: [47] 手写「已关闭账本」夹具显式 `confirmed_qty_final` / `confirmed_notional_final`(终值必须声明, 不再从 terminal 推); 其余 258 项原样保留。

**未闭合(明写)**: Q6 实现与回放; 同快照内 C×avg 与 N 一致性; 时窗核对; R6-MARK 动作合同; `_seen_syms > 1` 与 settle 整体异常两个出口不带事实(设计如此); −2013 终局性(假设); 跨进程同秒平仓 id; M5 再封存; income 缺行/币种换算; 物理 BUNDLE_export 门; 52 行写回等部署。协议不变: 第十一轮复核 → 分别合并 → 部署另裁; 运行树 d040c74 零接触(VERIFIED)。

## §6 数字标签
研究员列数字(4/6/8/10/14, 30/80, 40 日 / 67,588 行, 29 入口 / 69 检查)= 其复算(VERIFIED by them); 套件/电池计数与旧码红格计数 VERIFIED(本机); 其余为规则。
