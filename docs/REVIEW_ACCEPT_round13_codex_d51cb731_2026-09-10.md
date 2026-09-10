# 独立研究员第十三轮复审(d51cb731)· 辩证处置 + 第十四轮修复

> **创建:** 2026-09-10 22:2xZ | **Session:** https://claude.ai/code/session_01H39k5rgyd43mFMNsaBqzeX | **状态:** 处置已定; 第十四轮修复在实盘复审分支落码(未合并未部署), 待研究员第十四轮复核 | **作废条件:** 研究员第十四轮复核出具后以其为准
> **复审件:** `.claude/worktrees/codex-independent-20260907/multi_asset/exports/research/codex_round13_review_2026-09-11/`(HANDOFF / executor · risk · root 分册; 提交 d51cb731; 研究员自报 17 个入口 + 1,833 项核验)。**被审对象:** 实盘 5f2dd75, 研究 93df8e53, 主线 2f71ce50; 运行树 d040c74。
> **研究员总判:** 第十三轮四条 P2 修复成立; **未确认新的 P1**; 剩三条边界(orderId 解析 / 费用未测显示零成本 / 三处口径说明与代码不符)。**我方总判(用户字「辩证分析」): 三条全真; 前两条改码(小), 第三条改文档并顺手改 caliber 文案。**

---

## §0 一句话

第十三轮把「畸形」定义成了四态, 但 orderId 这一格用的还是 `int(raw)`: 小数被截、±Inf 抛 OverflowError 穿出 complete_anchor、没有可比值时畸形被跳过。成本诊断把「已定价」当成「已测」, `fee_paid or 0` 又把费未测当免费 —— 与「未测 ≠ 零」同一条原则的第三个读者。三处口径说明写得比代码好听(「旧键语义不变」「M1/M4/M5 None 不参与」「子集金额不关闭」), 研究员按码逐一纠正。第十四轮: `order_id_value` 无损整数一个实现贯穿全部读者; 已测 = 价与费皆已测, 分三桶报覆盖率; 口径按码重写。

没有任何一项影响策略 alpha 或回测数字; 研究员本轮亦未产生新收益结论。

---

## §1 三条边界(全部接受, 全部修)

| # | 研究员发现(合成响应) | 真因(读码 VERIFIED) | 第十四轮修复(实盘分支 82f1a6c → c22ae49) | 证据(`tests_request_identity_unknown.py` 357/357(含第十四轮 b [79]); 旧码上红) |
|---|---|---|---|---|
| R13-ID-INTEGER / ID-MALFORMED (P2) | ACK 102, GET 102.75(数值)被截成 102 接受 ⇒ 补单 C2 入账、总量 6 CLEAN; GET Infinity ⇒ OverflowError 穿出 complete_anchor; POST 缺 orderId + GET "badid" ⇒ 判畸形却因无 expected 跳过 | `identity_field` 用 `int(raw)` 只捕 TypeError/ValueError; `_ident_check` 在 expected None 时先返回; `known_order_id` / `_oid_of` / 结算 `_valid` / 子成交联接与归属键各自 `int()` | `order_id_value(raw)`(无损整数: int / 整值浮点 / 数字串; 小数 / NaN / ±Inf / 文本 / 空串 / bool = 畸形)+ `order_id_int`(抛 ValueError)一个实现贯穿全部读者; `_ident_check` 畸形先于 expected 判断; 联接中的畸形 id 计入 `child_order_id_malformed` | [76] 17 格: 单元 11 态; 补单链 102.75 / Infinity ⇒ 不崩、请求不可测; "badid" 无 ACK ⇒ 不可测; 整值 102.0 ⇒ 接受; 子成交 8140.75 不联接且计数 |
| R13-COST-COMPLETENESS (P2, 测量层) | 费用归属写 `fee_paid=None` 后, `neutrality_price` / `collect` 仍 0 bps(M1 正确标不完整); NaN / 负 avg 或 mid 被 truthy 当已定价 | `fee_paid or 0`; `if px and mid` | 已测 = 有限正 avg 与 mid **且** fee 已知; 三桶(未定价 / 费未知 / 已测)计数与名义, bps 只按已测, 覆盖率分名义与计数; 无已测 ⇒ None; 逐锚打印补已测名义; 汇总按已测名义 | [77] 8 格: fee None ⇒ bps None / 费未知 6; fee 0.06 ⇒ 100 bps; 混合 ⇒ 100 bps 只按已测 6, 覆盖 0.5; NaN / 负 / Inf 价或中价 ⇒ 未定价; `collect` 同 |
| 口径三处 | (a) 「新增键不改旧键含义」错: 分母已由全部名义改为已测名义(研究员例 5300 → 10100 bps); (b) 「M1/M4/M5 None 不参与」错: M1 缺 N/avg 排除、缺 fee 标不完整; **M4 缺 N 按 0 计入 realized 换手**; M5 缺 intended/N 计 unknown; (c) §3g.1 反方向「金额不关闭 / lower 30」错: 已有终值 N40 时子集 N30 不撤销终值, 行照旧关闭; (d) API_SEMANTICS「官方页面示例含 cumQuote/avgPrice」错: 复开页面未列 | 文档比代码好听 | `measured_over` / `caliber` 明写分母已改; DESIGN §5 按码写 M1/M4/M5; §3g.1 反方向更正; API_SEMANTICS 改为「复开页面未列 cumQuote/avgPrice, 历史来源仅为本仓代码注释, 未取得正式 required 清单」; `chase_readout` 拒绝态逐锚打印补已测名义 | — |

**研究员对我方三条自报的裁量(接受)**: (1) 缺键/null 皆无证据可作本地兼容政策, 但只能依赖我方已发送的身份, 不证明响应完整; (2) 「旧键语义不变」不同意 —— 已按上表更正; (3) `gate` / `load_nstar` 未改, 但不能推论「所有判读不变」—— 已定价/未定价两锚的方差样本 2 → 1, 打印与可用统计变了; N* 未重算, 分臂/判官未改。

## §2 Q6 / 管线
数学接受不变(字节相同); 实现与回放另排。管线参考态不变。

## §3 我方承认的新错误
1. 四态定义了却在 orderId 这一格没用上(仍 `int()`); 「一个实现」没贯穿 `known_order_id` / `_oid_of` / 联接键。
2. 「已定价」≠「已测」: 费用是成本的一半, `fee or 0` 与「未测 ≠ 零」原则冲突 —— 上一轮修分母时只看了价格。
3. 三处口径写得比代码好听: 「语义不变」「None 不参与」「金额不关闭」都没按码核; 自报要写「观测到 / 未观测到」而不是把期望当事实。

## §4 状态

| 件 | 提交 | 电池 | 状态 |
|---|---|---|---|
| 实盘分支 第十四轮 | `review/b0a573a1-executor` **82f1a6c → c22ae49** | 132/132 全绿(notify_audit 副本 22:56Z 刷新) | 已推送, 待复核 |
| 研究分支 | 93df8e53 → HANDOFF §EXECUTOR 第十四轮 | — | — |
| 研究主线 | 本文 + DESIGN §3h / §3g.1 与 §5 更正 + journal/STATE | — | — |

**版本配对(上一轮期望被改的格)**: 无(第十三轮 325 项原样保留; `tests_neutrality_price` 15/15 原样 —— 其夹具带费与价, 属「已测」)。

**未闭合(明写)**: R6-MARK 动作合同; 同快照内 C×avg 与 N 一致性; 时窗核对; 非 USDT 费未换算时同属「费未知」(本轮未做币种换算治理); Q6 实现与回放; 无场所事实 maker 行走旧读法(来源前提); `_seen_syms > 1` 与 settle 整体异常出口; −2013 终局性(假设); 跨进程同秒平仓 id; M5 再封存; income 缺行/币种换算; 物理 BUNDLE_export 门; 52 行写回等部署。协议不变: 第十四轮复核 → 分别合并 → 部署另裁; 运行树 d040c74 零接触(VERIFIED)。

## §5 数字标签
研究员列数字(102 / 102.75, 5300 → 10100 bps, 17 入口 / 1,833 核验)= 其复算(VERIFIED by them); 套件/电池计数与旧码红格计数 VERIFIED(本机); 其余为规则。
