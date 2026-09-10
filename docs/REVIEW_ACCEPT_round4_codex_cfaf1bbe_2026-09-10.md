# 独立研究员第四轮复审(cfaf1bbe)· 辩证处置 + 第五轮修复

> **创建:** 2026-09-10 05:5xZ | **Session:** https://claude.ai/code/session_01H39k5rgyd43mFMNsaBqzeX | **状态:** 处置已定; 第五轮修复在两条复审分支落码(未合并未部署), 待研究员第五轮复核 | **作废条件:** 研究员第五轮复核出具后以其为准; 合并/部署另按验收裁定
> **复审件:** `.claude/worktrees/codex-independent-20260907/multi_asset/exports/research/codex_round4_review_2026-09-10/`(HANDOFF / RESULT / risk · executor · pipeline · account 分册 + root 复执行; 提交 cfaf1bbe)。**被审对象:** 实盘 0d30095, 研究 bc8b3772, 运行树 d040c74(只读核验不变)。
> **研究员总判:** REQUEST_CHANGES — 有实质修复, 执行数量与请求终态、熔断记账、候选资格仍有可复跑反例。**我方总判: 同意, 五类阻断全部成立, 且全部是第四轮「按反例修主路径、未按合同修所有路径」留下的。**

---

## §0 一句话

第四轮把研究员的数量合同实现在了被点名的分支上, 没有实现在**所有**分支上: 全成功路径的行仍写「名义 + 末单均价」, reconcile 就拿它们算数量(50@1 + 50@2 = 100 张被读成 150/2 = 75 张, 持仓 75 两门 CLEAN); 一笔子成交就把请求置成 confirmed 并把上界归零(先看到 10 就关腿, 后来 80 因为 `filled_notional is not None` 被屏蔽); 矛盾检查藏在「仍有未知」分支里, 最后一张关闭后绕开; 阶段 B 查单只核 client id 不核 status(NEW/PARTIALLY_FILLED 仍补单); E-0910-A 熔断在循环顶部 `continue`, 后名已成交的 maker 行被跳过(合法 100 读成未授权 BREAK)。研究员的两个方向都复现了: **漏报**(75/150 通过)与**误报**(80 读成异常、合法 100 判 BREAK), 共因是「进入公式的请求状态、已知数量和账本行不完整或被另一口径替换」—— 我同意这个诊断胜过任何阈值调整。

**第五轮的形状**: 请求生命周期分离「累计已成量 C」与「是否终态」; 每张请求记场所 executedQty/status; 子成交只抬 C(按 trade id 去重、单调), 终态只由场所状态或 C 达 Q; 行的数量/名义/均价全部经**同一个账本读者**; reconcile **先查矛盾**再按 `filled_qty` 取量; 阶段 B 对场所显示仍开的单**先撤后查**, 仍开 ⇒ UNKNOWN; 熔断**先记 maker 腿再拒补单**; clamp 先校验全部名的 target/held。没有任何一项影响策略 alpha 或回测数字(研究员本轮亦未产生新收益结论; 30 书 SHA 不变)。

---

## §1 风险数量(risk 分册 Q1–Q7)

| # | 研究员发现(真实 producer → RC/PB/WD) | 我方复核 | 判定 | 第五轮修复(实盘分支 `review/b0a573a1-executor` b840ed9) | 证据(套件 `tests_request_identity_unknown.py`) |
|---|---|---|---|---|---|
| Q1 (P1) | 50@1 + 50@2 全成功: 账本 confirmed_qty [50,50], 行却 `filled_notional 150 / avg_fill_px 2 / filled_known_qty None` ⇒ RC 150/2 = **75**; 最后一张按身份关闭后 known_qty 100 却读成 150 | **VERIFIED**(第四轮 b 只在 `_unknown` 分支写 known_qty; 均价取末单 `_d.avg_fill_px`) | **接受, P1**。「EXACT BY CONSTRUCTION」只对同一请求成立, 我把它跨集合继承了 | 每张请求记 `confirmed_qty` = 场所 executedQty(非名义/均价); 新 `ledger_row_columns` 是**所有路径唯一读者**: `filled_qty` = Σ executedQty(腿关闭时), `avg_fill_px` = 同集合 Σ名义/Σ数量; reconcile `_exec_qty` 先取 `filled_qty`, 再 `filled_known_qty`, 名义/均价只剩旧行回退且校验价格有限为正 | [21]: 两价成交 ⇒ filled 150 / **filled_qty 100** / avg 1.5; 场所 100 CLEAN, 75 异常 |
| Q2 (P1) | 请求 100 首见 child 10 即关闭(filled 10); 更全 80 再来不更新; PARTIALLY_FILLED 10/50 被标 confirmed 丢掉余量 40; 一个 orderId 20 张就把 50 请求终结 | **VERIFIED** | **接受, P1**。`confirmed` 同时承担「知道一部分」和「不会再成交」两件证据不同的事 | 请求增加 `terminal`/`status`/`trade_qty{tid}`: 子成交只抬 C, **不设终态**; 终态只由场所 status ∈ {FILLED, CANCELED, EXPIRED, REJECTED} 或 C ≥ Q; `request_remaining` = 0(拒绝/未发/终态) / |Q|(一无所知) / |Q|−|C|(仍开); 腿只在全部已发请求终态且自洽时关闭; `apply_commission_to_rows` 对有账本的行**每次归属都重跑结算**(不再被 `filled_notional is not None` 屏蔽); 未读到回包的请求 `terminal=False` | [22]: child 10 ⇒ known 10 / 带 90 / 仍 UNKNOWN; 场所 80 解释、120 异常; 10+70 ⇒ C 80; 达 100 才关腿。PARTIALLY_FILLED 10/50 + 未知 50 ⇒ known 10 / 带 90 |
| Q3 (P1) | 最后一张 unknown 用 60 关闭(请求 50): 标了 inconsistent 但 fn=110 写出, RC 在 `fn is None ∧ 有 unknown` 分支里才查矛盾 ⇒ 110 CLEAN; 全成功回包 60/50 未查; child qty NaN 经 fn/avg 得有限 100 | **VERIFIED** | **接受, P1** | `_exec_qty` **第一行**查 `ledger_inconsistent`(先于 known/bounded/structural); 矛盾腿永不关闭(`closed = … and not inc`); 生产者侧(回包 executedQty > origQty)与结算侧(超量/反向/非有限/quote≠qty×price)都记矛盾 | [23]: 60 关 50 ⇒ 不关腿、不可测(100/110 皆异常); 回包 60/50 ⇒ 不写 filled 110; child NaN ⇒ 不可测; SELL child 对 BUY 请求 ⇒ 矛盾 |
| Q4 (P2) | 同 trade id 重放累计(20+20+20=60); 较小后续子集把 known 40 降到 10 | **VERIFIED** | **接受** | 每请求 `trade_qty{trade_id}` 集合: 去重、C = Σ 并集(单调不降); 生产者读数大于子集时保留 | [24]: [t1,t1,t2] ⇒ 40; 再给 [t1] ⇒ 仍 40 |
| Q5 (R7 组合) | cap=NaN∧held=NaN / cap=NaN∧target=NaN / 无 cap∧target=NaN / target=None: 校验被 cap 早退绕过或 `or 0` 掩盖 ⇒ planner ValueError/TypeError | **VERIFIED**(第四轮只在 cap 有效后校验) | **接受, P2** | `clamp_venue_cap` **先**对全部名校验 target/held(raw None 亦无效), 再进 cap 逻辑; 调用方对 held 无效的名一律弹出 | [27]: 四种组合全部进 `invalid`, 无截断 |
| Q6 / §2.4 | latest-only 基准: 已解释 50、观察 80 的残差 30 在下一锚以观察 80 为新基准消失, 两门 CLEAN | **VERIFIED**(旧消费方式, 非第四轮引入; 研究员亦如此定性) | **接受为未闭合, 不称 fail-closed**。我第四轮「只可能误报不会漏报」的说法**撤回**: 单条带不重复花掉(研究员穷举 20,301 对证实)但历史残差可被新基准吞掉 | **未落码**。预注册 `docs/PREREG_reconcile_carry_forward_unexplained_2026-09-10.md`: 未解释余额 E_s 与未决请求集 P_s 跨窗延续, 只由可归属成交/显式记账/签字更正解决; 需账本副本 41 天回放 + 用户字 | — |
| Q7 (legacy) | 无 known_qty 的旧 bounded 行 known_notional/avg NaN 仍算有限 | **VERIFIED** | **接受** | `_exec_qty` fn/avg 路径校验 fn 与 px 有限、px > 0 | [17] 既有 + fn 路径校验 |

## §2 执行器(executor 分册 E4)

| # | 研究员发现 | 我方复核 | 判定 | 第五轮修复 | 证据 |
|---|---|---|---|---|---|
| E4-P1 | 原 `complete_anchor` 全链: 撤单失败 + 查单 NEW 0 仍补 10; PARTIALLY_FILLED 4/10 仍补 6; allOrders 匹配 NEW 0 跳过新 helper 仍补 10; 满 1000 页里有该 NEW 0 亦补 | **VERIFIED**(`settle_ambiguous_legs` 见 matched 即 skip 且在满页门之前; 查单只核 cid; `unknown` 不含 cancel unresolved) | **接受, P1**。「知道目前成交多少」≠「该请求已终止」; 这不依赖 −2013 争论 | `_scan_orders` 读 status, 记 `non_terminal` cids(0 成交的 NEW 也返回记录, 不再 None); `settle_ambiguous_legs`: 匹配且非终态 ⇒ **先 `cancel_order` 再查单**, 终态 ⇒ 其事实, 仍开/撤单失败 ⇒ UNKNOWN; 查单核对 **symbol / clientOrderId / orderId 存在 / side / origQty**; 已确认(非歧义)单缺席 allOrders 也按 id 结算(满页 ⇒ UNKNOWN; −2013 对已确认单 = 矛盾 ⇒ UNKNOWN); 同名两计划 ⇒ UNKNOWN(不 last-wins); `complete_anchor`: `unknown |= 仍开的名 − 结算为终态的名 |= cancels.unresolved` | [25]: 匹配 NEW + 撤失败 ⇒ UNKNOWN; PARTIALLY_FILLED 4 + 撤成功 + 复查 CANCELED 4 ⇒ FOUND 4(正控); 复查仍 PARTIALLY_FILLED ⇒ UNKNOWN; 查单 NEW 0 ⇒ 撤后仍失败 ⇒ UNKNOWN; 错 symbol/side/origQty/无 orderId 四例 ⇒ UNKNOWN; 已确认单 −2013 ⇒ UNKNOWN 非 absent; 同名两计划 ⇒ UNKNOWN |
| −2013 边界 | 15 分钟后单次 −2013 = 从未接受, 无官方 SLA 亦无实测 | 同意 | **接受为显式假设**(业务政策, 非数学保证) | 仅对 `submit_ambiguous` 的计划在非满页 + −2013 时判 absent, 报告文字标明「venue-consistency assumption」; 对已确认单的 −2013 一律 UNKNOWN | HANDOFF 第五轮 §未闭合 |
| E4-P2A | `flatten_exec_from_trades` 仍 `by_oid[int(oid)]`, BTC/ETH 同 77 只剩后者(漏恢复) | **VERIFIED** | **接受, P2** | 键 (symbol, orderId) | [28]: 两名皆恢复 |
| E4-P2B | `_flatten_seq` 是实例属性, 同进程两 broker 同秒同名同 id | **VERIFIED** | **接受, P2** | 模块级 `itertools.count`(进程级); 跨进程同秒仍未闭合(明写) | [28]: 两实例 id 不同 |
| E4-P2C | 传输未知的平仓单写成 `submitted_rejected`(VenueTransportError ⊂ VenueError), 恢复器排除 rejected; `client_id_dropped` 不入行; maker/requote 仍 `[:36]` | **VERIFIED** | **接受, P2** | `flatten_all`: 传输失败 ⇒ `execution_unknown`(submitted 且非 rejected, order_id 不借用前单); 看门狗行类 `filled_amount_unknown`; `client_id_dropped` 入行; `submit_maker` **预检**全部名最长 id(`-3c99`)超 36 即在任何 POST 前抛错(全有或全无) | [28] |
| 一计划多请求 | `_details.update` 按 symbol last-wins | 同意(正常人口一名一计划) | **接受为硬约束** | 同名两计划 ⇒ UNKNOWN(见上) | [25] |

## §3 熔断与账本(account 分册)

| # | 研究员发现 | 我方复核 | 判定 | 处置 |
|---|---|---|---|---|
| A1 (P1) | topup 循环顶部遇 `_venue_lock` 即 `skipped_venue_lock` + continue, 位于 maker 行之前 ⇒ 后名已成 100 或未决 100 的 maker 行丢失; 原 reconcile 读成未授权 100, position_break BREAK; 无熔断对照 CLEAN | **VERIFIED**(3ff5e00 我写的顺序) | **接受, P1**。「先决定后记账」 | 循环重排: UNKNOWN 名先写带请求带的 maker 行, 已知名先写 filled/partial_expired 的 maker 行, **然后**才是熔断 ⇒ `skipped_venue_lock` 补单行 | [26]: AUSDT −4400 后, BUSDT maker 60/100 保留 `partial_expired` 60 + 补单 skipped_venue_lock; CUSDT UNKNOWN 保留带 100 的 maker 行 + skipped_venue_lock; 场所 +60 CLEAN; n_skipped 2 |
| A2 | 52 行 reconstructed 全过 schema, 整份 Sep09 M1/M3/M4/M5 加行前后不变; 12Z 仍 0 orders(未部署) | 同意 | **VERIFIED**(研究员数) | 写回仍等分支部署。**P2 未闭合**: `pilot_metrics` M5 对同锚存在 anchors 行的 reconstructed 行 `float(target_w)` 会 TypeError(当前 12Z 无 anchors 行故不触发) ⇒ 冻结模块再封存候选, 登记 |
| A3 | 平仓 3,095 fills 已在本地账本, 费 116.37847565, 逐名对齐 9.1e−13; gate `abs(abs(fee)−abs(income))` 把反号 income 也放过 | 同意 | **接受(P2 防卫)** | 工具门改有符号恒等式 `abs(fee + income) < 0.01`(研究主线本提交); 实测残差 3.5e−7 通过、反号 income 拒绝 |

## §4 管线(pipeline 分册; 并行代理实施于研究分支)

| # | 研究员发现 | 判定 | 第五轮修复(研究分支 `review/b0a573a1-pipeline` bc8b3772 → **0cc16a85**, 并行代理; `tests_pipeline_gates` 117 → **151/151** 本地 + pod2 151/151) |
|---|---|---|---|
| P1 候选资格由调用者选门 | 真实 G2_closure PASS / STEP1 降 profile / 未登记门名经 JUDGE_ELIGIBILITY 各产 4 个 PROMOTE | **接受** | 归档内冻结 `ELIGIBILITY_CONTRACT.json`: 逐门批准源码 sha(G2/STEP1/STEP2 = 归档门文件; **BUNDLE_export = 空**, 物理门不存在), 逐臂 candidacy_gate=BUNDLE_export + 书绑定; 判官从自身目录读合同(无 env 覆盖), `JUDGE_ELIGIBILITY` 只作定位 {arm:{receipt, inputs}}, 调用者给出的 gate/self_sha/profile 与合同冲突即拒; `require` 拒绝不在批准表的源 sha、拒绝无合同的受管门 |
| P1 map key 未绑定经济工件 | receipt.arm=A1e 改 key 为 A1 ⇒ 6 PROMOTE; 收据冻结后替换书序列仍 4 PROMOTE | **接受** | receipt.gate == 合同门, receipt.arm == 被判臂, 判官自行把该臂四份评分书文件的 sha 加入必报输入(BUNDLE_export 必报 7 → 11) |
| 门源码 pin 只证「与磁盘一致」 | 本地改门重跑产新收据, 运行时 sha 自洽 ⇒ 链 DONE | **接受** | 运行时 sha 还须 ∈ 合同批准表; 合同本身入 sha 清单, 判官记录合同 sha |
| P2 严格 schema 不完整 | gross −1 / +inf、W NaN、symbols 反序、缺 cols/symbols 仍 4 PROMOTE | **接受** | `JUDGE_REQUIRE_W=1`(别名 `JUDGE_STRICT_BOOK=1`): cols/symbols 必需、W 有限、各臂 symbols 轴相同 ⇒ rc 2; 任一模式下冻结窗 gross_total 有限且 > 0 |

研究员 harness 原样重跑(`receipts/researcher_round4_cases_rerun_after_r5.json`): 42 例不变; **11 例按预期翻转**(G2 冒用 4→0, STEP1 降级 4→0, 未登记门 4→0, A1e→A1 改标 6→0, 换书 4→0, 负/无限 gross、非有限 W、反序 symbols、缺 cols/symbols → rc 2); 3 例其正控读 0 PROMOTE **是设计**(合同未批准任何 BUNDLE_export 源; 允许路径由我方以批准归档导出器的合同副本在测试中证明); 7 例是其 harness 只拷 .py/.sh、译后装置无合同 ⇒ fail-closed(需其更新 harness 携带合同并重算批准 sha)。**未闭合**: 物理 BUNDLE_export 门仍未建(真实判官运行仍参考态); 合同可被有写权者改(缓解 = sha 清单 + 判官记录合同 sha); 默认模式仍 rec-only(除 gross>0); 15 旧收据无 self_sha; pod2 旧 schema 门不变。自报: 首跑 2 红(测试顺序/夹具, 产品未动); r5-1/r5-2 拆分为事后拆分(终态文件与 151 测试版逐字节相同, 中间 143 态未单独运行); 收据 JSON 首版误读 trust14 字典, r5-3 修正后再推送。

## §5 研究员「下一轮最小验收」五点 → 我方回应
1. 逐请求合约数量为权威输入, 所有路径共用读者 —— **已做**(`ledger_row_columns`; 名义/均价不再重构数量)。
2. 区分累计已成量与终态; NEW/PARTIALLY_FILLED/cancel unresolved 保留未决上界; 未知不因有 child 消失 —— **已做**。
3. 每个出口先记录已发生/可能发生的请求再决定新增 —— **已做**(熔断重排; UNKNOWN 名 maker 行带 C 与余量)。
4. 判官内明确每臂的必要门/profile/批准源码/全输入/评分书 SHA —— 研究分支第五轮(§4)。
5. 回归覆盖状态笛卡尔组合 —— 套件 [21]–[28] 覆盖: 买卖 × 一/多请求 × 同/异价 × 终态/活跃/未知 × 零/部分/完整 child × 去重 × 熔断前后; **跨锚**与**分页饱和 × 增量**两轴由 PREREG(Q6)与既有 [18] 满页保护覆盖, 跨锚未落码(明写)。

## §6 我方承认的新错误(第四轮引入)
1. 「一个量两个读者」: 已知数量只在 UNKNOWN 分支写出, 成功路径仍用旧列。
2. 用一笔子成交断言请求结束; 又用 `filled_notional is not None` 屏蔽后续结算。
3. 矛盾检查放在分支里而非读者入口。
4. 熔断写在记账之前(3ff5e00 的顺序是我定的)。
5. 查单只核 cid; 「−2013 是唯一 UNKNOWN→0 路径」的表述不准确(NEW 0 也归零) —— 撤回该表述。
6. 「系统层只可能误报不会漏报」—— 撤回(Q6)。
7. 夹具把「allOrders 缺席」当「未成交」建模; 场所合同是列出全部含 CANCELED 0 的单 —— 改夹具, 不放宽规则。
8. (电池)`tests_daily_summary` 两条 prose 断言按全日 nav 行数判「可检」而工具按 24h 窗渲染 —— 状态副本一旦超过 24h 就假红(本轮首跑 NOT GREEN); 改为按工具自报窗内行数, 不可检打 NOT EXERCISED。旧写法意味着此前在陈旧副本上的绿对这两条什么都没证明。

## §7 第五轮提交与状态

| 件 | 提交 | 电池 | 状态 |
|---|---|---|---|
| 实盘分支 第五轮 | `review/b0a573a1-executor` **b840ed9** | 132/132 全绿(首跑 2 红 = 电池自身缺陷, 见 §6-8; 修后重跑) | 已推送, 待复核 |
| 研究分支 第五轮(管线) | `review/b0a573a1-pipeline` f0c84502…0cc16a85(4 提交) | 151/151 本地 + pod2 | 待复核 |
| 研究主线 | 本文 + `PREREG_reconcile_carry_forward_unexplained_2026-09-10.md` + 平仓工具门符号 | — | — |

**协议不变**: 研究员第五轮复核 → 两仓分别合并 → 部署另裁。运行树 d040c74 零接触(VERIFIED)。**未闭合(明写)**: 跨读数 E_s/P_s 延续(预注册); −2013 终局性(假设); 跨进程同秒平仓 id; M5 对 reconstructed 行的再封存; income 缺行恢复与币种换算; 物理 BUNDLE_export 门。

## §8 数字标签
研究员列数字 = 其复算(VERIFIED by them); 套件计数与电池 VERIFIED(本机); 3.5e−7 VERIFIED(本机算术); 「M5 TypeError」INFERRED(研究员合成例, 我方未复跑)。
