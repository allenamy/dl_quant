# 独立研究员第六轮复审(a99c447e)· 辩证处置 + 第七轮修复 + 开发方法收口

> **创建:** 2026-09-10 09:1xZ | **Session:** https://claude.ai/code/session_01H39k5rgyd43mFMNsaBqzeX | **状态:** 处置已定; 第七轮修复在实盘复审分支落码(未合并未部署), 待研究员第七轮复核; Q6 预注册修订 2 待其复核; 方法论见 `docs/DESIGN_request_fact_model_2026-09-10.md` | **作废条件:** 研究员第七轮复核出具后以其为准
> **复审件:** `.claude/worktrees/codex-independent-20260907/multi_asset/exports/research/codex_round6_review_2026-09-10/`(HANDOFF / RESULT / executor · risk · root · design 分册; 提交 a99c447e)。**被审对象:** 实盘 07929ed, 研究 59eca38d, 主线 6a75946f; 运行树 d040c74。
> **研究员总判:** 实盘 REQUEST_CHANGES(一条剩余漏报 + 一条新增误触发); Q6 修订 1 NEEDS_CLARIFICATION; 研究管线维持参考态。**我方总判: 同意全部。并且承认: 六轮里每轮被抓到承重缺陷, 根因不在单个缺陷, 在我的开发方法 —— 按反例修主路径, 而不是先把状态空间写成表再按表实现、按表测正反两向。第七轮先写表(`DESIGN_request_fact_model`), 再按表改码, 并用原链端到端测。**

---

## §0 六轮复审为什么每次都能抓到(方法论结论, 用户之问)

研究员的三个做法与我的三个缺口一一对应:

| 研究员的做法 | 我此前的缺口 | 六轮里的实例 |
|---|---|---|
| **枚举状态空间再跑原函数**: 事实 × 来源 × 出口的笛卡尔积, 用原 `complete_anchor → RC → PB → WD` 全链注入场所回包, 不跑 helper | 我只在被点名的分支上实现合同(「修反例」) | R4 Q1 已知数量只在 UNKNOWN 分支写; R5-E1 `_still_open` 做了、`unresolved` 没做; R6-§2 `_scan_orders` 把数量和金额一起置 None |
| **每件事实一个字段一个读者, 事实间禁止推导** | 一个字段承担两件证据不同的事 | confirmed 绑金额 ⇒ 终态余量绑金额可读(R5-QA); C 与终态(R4 Q2); pin 键是 symbol(R5) |
| **同一夹具跑两个方向 + 版本配对**(R5 vs R6 同夹具; 漏报与误报都要) | 只断言「反例现在会报」, 不断言「良性格仍 CLEAN」 | R6-§3: 新读者变严 + 旧出口清列 ⇒ 三种拒单 × 持仓不变 6 格误触发, 第五轮同夹具本来正常 |
| **措辞逐字核**(「全部/唯一/原子」都要有覆盖量词域的测试) | 声明超过测试范围 | 「全锚全有或全无」(100 块时 maker 已发); 「−2013 唯一归零路径」; 「只误报不漏报」 |
| **保留失败尝试, 只改夹具不改产品, 复现后再判** | — | 研究员每份分册都保留 attempt01 失败与自纠 |

第七轮起的规则(已写入 DESIGN §4): 先写事实表 → 读者在行发出时最后重算(分支只能改账本) → 每个修复三件测试(反例格 / 同夹具反方向 / 邻格)+ 原链端到端 → 版本配对表 → 量词措辞门。

## §1 两条承重项(接受, P1)

| # | 研究员发现(原链实达) | 真因(VERIFIED) | 第七轮修复(实盘分支 5dc120a) | 证据(`tests_request_identity_unknown.py` 155/155) |
|---|---|---|---|---|
| R6-§2 剩余漏报 | 阶段 B 查单 CANCELED / origQty 10 / executedQty 4, 金额不可读 ⇒ `_scan_orders` `executed_qty = None if unreadable` 抹掉可信 C ⇒ maker 行 known 0 / 带 0–10; 持仓 10 两门 CLEAN | 数量与金额的可读性被同一个 `unreadable` 捆绑 | `_scan_orders` 三件事实三种可读性: `exec_unreadable` / `unreadable`(金额)/ `inconsistent` 各自成列; 缺 executedQty 由同请求 cumQuote/avgPrice 推导并标 `executed_qty_derived` | [40] 单元; **[37] 原链端到端**: 未改的 `complete_anchor`(真实 broker + FakeNet: DELETE −2011 / allOrders 空 / 查单 CANCELED 4 无金额 / userTrades 空)⇒ maker 行 filled_qty 4 / 带 None / 金额 UNKNOWN / 0 次补单 POST; reconcile 持仓 4 CLEAN、10 异常 6 |
| R6-§3 新增误触发 | 明确拒单(−2019/−4400/−1008)成交 0: 读者已算 filled_qty 0, 但 `_n_sent==0` 出口又清掉; R6 严格读者拒绝账本行金额兜底 ⇒ 不可测 ⇒ WD tripped; 三种拒单 × 持仓不变(0、1)共 6 格 | 分支可以改列 ⇒ 出口与读者不一致; 我只测了「反例现在会报」, 没测「良性格仍 CLEAN」 | **读者在 `_order_row` 发出时最后重算六列**(DESIGN §4.1), 分支手写的列一律被账本推翻; 两个「未发」出口不再手写列; 标签与账本不符记 `ledger_label_mismatch` | [42] 单元(分支清 0 ⇒ 行仍 0.0); **[38] 原链端到端**: 三种拒单 × 持仓 0/1 ⇒ 行 filled_qty 0.0、reconcile 无异常、1 次 POST; 正控 EXPIRED 0 ⇒ filled 0 CLEAN |

## §2 边界项(接受)

| # | 研究员发现 | 第七轮修复 | 证据 |
|---|---|---|---|
| R6-QB 残留(P1 防御) | 负 executedQty / 显式 0 伴正 cumQuote 仍经 `<=0` 当真零 | decoder 与折叠均记 `inconsistent`(负数、NaN、0 伴正金额), 请求 `inconsistent` ⇒ 腿不可测 | [39]: −50 ⇒ inconsistent; 0 伴 100 ⇒ inconsistent; 矛盾请求 ⇒ 腿不可测 |
| R6-P2(P2) | allOrders 直接终态 CANCELED 4 的请求不进 found ⇒ 旧 pin 留、补单被抑制 | settle 返回 `terminal_matched`; `complete_anchor` 用 found ∪ terminal_matched 覆盖 unresolved 与清 pin | [41] |
| R6-MARK | 数量已知 70 但无可用 mark 时 5b 只 PARTIAL、5e CLEAN | **未改**: 不可定价时的动作合同需单独预注册(研究员亦不主张擅改阈值); 登记 | — |
| 主方自报 pin 身份 | found 是 symbol 集; 当前不变量(一名一计划; requote 更新同一计划)下可接受, 前提写清 | DESIGN §1 已写前提; 同名双计划已 ⇒ UNKNOWN | — |
| 「终态 C 未知一律不可测」措辞过强 | 研究员 14 格显示不是每种终态未知行都被拒量化 | 措辞改为: 终态 C 未知 ⇒ 历史区间 [C_lo, Q] 保留; 读者对无数量证据的账本行不可测 | DESIGN §2 |

## §3 Q6 修订 2(研究员 D1–D4, 接受, 待其复核)
`PREREG_reconcile_carry_forward_unexplained` §1b: 每张请求维护**已执行量可行区间** Xᵢ(t)(出生前 [0,0]; 无证据 [0,Q]; 可信下界 [C,Q]; 终态 C 可信 [C,C]; **终态 C 未知保持 [C_lo,Q]**); 单调(证据只增, 真实累计不减); **两种余量分开**(未来容量 Q−xᵢ⁻ 只对未终态请求; 历史未知 xᵢ⁺−xᵢ⁻; 隐含归属只进可行集不进 K); **联合约束** = 存在单调可行向量满足每锚的和约束(逐锚区间传播判定; 单 BUY100 双读数联合可行集 = {0 ≤ first ≤ second ≤ 100} 5,151 对, 点时 clip 的 10,201 对里多出的 5,050 对全是不可归属的下降轨迹); 当前净暴露距离与历史审计未决**分列**; 迟到证据收窄同一请求并整条重算, 在线收据保留; **同截面重启**(Q₀ 与各请求 xᵢ(t₀) 同截面, K 只计切点后增量, 反控 180 ⇒ e = 80 而非 0)。验收判据追加 5b–5e(核解集不核计数、80→90 合法、80→10 审计未决、终态后 90 不可解释、切点反控)。未落码。

## §4 研究管线
维持第五轮参考态收口; 本轮无改动(167 份源同 SHA); 物理 BUNDLE_export 门未建, 正式候选未开放。

## §5 我方承认的新错误(第六轮引入)
1. `_scan_orders` 用一个 `unreadable` 同时决定数量与金额的 None —— 「三件事实」我在 executor 里做了, 在折叠里没做。
2. 严格读者 + 旧出口手写列 ⇒ 良性拒单误触发: 只测了漏报方向。
3. 「终态 C 未知一律不可测」说过头。
4. decoder 的 `<= 0` 把负数和「0 伴正金额」当零。
5. (电池环境)复审工作树的 `state/` 是陈旧副本: 第五轮 `tests_daily_summary`、第七轮 `tests_alarm_digest` 都因副本超龄而红(后者按其设计「不可观测 = 红」, 不改它); 本轮从运行树刷新 `notify_audit.jsonl` 副本(只读审计日志)后重跑。**规则**: 复审分支跑电池前刷新工作树的 state 副本(只读拷贝), 并在交接里写明副本时间; 陈旧副本上的绿对依赖状态的套件什么都没证明。

## §6 状态

| 件 | 提交 | 电池 | 状态 |
|---|---|---|---|
| 实盘分支 第七轮 | `review/b0a573a1-executor` **5dc120a** | 132/132 全绿(首跑 tests_alarm_digest 因陈旧副本红, 刷新副本后重跑) | 已推送, 待复核 |
| 研究分支 | 59eca38d(参考态)+ HANDOFF §EXECUTOR 第七轮 | — | — |
| 研究主线 | 本文 + DESIGN 事实表 + PREREG 修订 2 + journal/STATE | — | — |

**未闭合(明写)**: Q6 落码与回放(先过修订 2 复核); 不可定价数量的动作合同(R6-MARK); −2013 终局性(假设); 跨进程同秒平仓 id; M5 再封存; income 缺行/币种换算; 物理 BUNDLE_export 门; 52 行写回等部署。协议不变: 第七轮复核 → 分别合并 → 部署另裁; 运行树 d040c74 零接触(VERIFIED)。

## §7 数字标签
研究员列数字 = 其复算(VERIFIED by them); 套件/电池计数 VERIFIED(本机); 5,151 / 10,201 / 5,050 / 2,601 / 2,550 来自其 design 分册(VERIFIED by them, 我方未重新枚举); 其余为规则。
