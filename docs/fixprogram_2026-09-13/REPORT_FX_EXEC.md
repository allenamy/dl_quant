> **创建:** 2026-09-13 15:3xZ(lead 转录) | **Session:** FX-EXEC(teammate fx-exec)撰文 / lead 落盘 | **状态:** 逐项进行中 — E2/E3/E4/E9 已提交(克隆分支 fix/known-issues-2026-09-13), 全电池待队列完成后在最终头上跑; 未部署 | **作废条件:** 克隆分支任一提交被改写; 或本文基底 ef60f85 以外的运行树被部署
> **落盘说明**: 子代理 Write 工具返回「Subagents should return findings as text, not write report files. Include this content in your final response instead.」(FX-EXEC 15:2xZ 报原文; 目标路径 `/Users/haosiyu/cc_tmp/fx_exec_work/stage_research/FX_EXEC/REPORT_FX_EXEC.md`)—— 该约定要求子代理以文本交回、由主会话落盘。本文件由 lead **逐字转录** FX-EXEC 的两条消息(E2–E4 段 ≈15:1xZ; E9 段 ≈15:3xZ), 未改任何事实、数字或措辞; E9 段按原文英文保留。

# REPORT · FX-EXEC · 执行器已知问题修复

规程 = FIXPROGRAM §0。克隆 /Users/haosiyu/cc_tmp/fx_exec(--no-hardlinks, ef60f85, 分支 fix/known-issues-2026-09-13); ~/dl_quant_live 只读; 无 .env / 凭据 / 账户调用。单套件一律用电池解释器与环境 `FX_EXEC/receipts/common/run1.sh`(. ops/pyenv.sh + /usr/bin/python3 3.9.6; 日志头记 HEAD / 脏计数 / 套件 sha, 尾记 rc)。AST 逐字核对器 `common/ast_keep_check.py`(旧文件每个 check(...) 与 assert 的源码段按序出现在新文件), 结果 `common/ast_keep_check_E2_E3_E4.log`(四份 lost 0)。真账本事实取只读副本 cc_tmp/fx_exec_census(13:04:09Z orders/anchors/readback/anchor_runs.log/per_name_stop.json; events.jsonl 13:24:46Z), 逐文件 sha `common/census_copy_sha256.txt`。

## 提交链
| 项 | 提交 | 父 | diff | sha256 |
|---|---|---|---|---|
| E2=EXE-05 | 62945341c56dc8de41a89176f94a3ba69727b7f2 | ef60f85 | docs/receipts/fx_exec_E2.diff | de7a4dd7c13fd473d664a802eeb2f9bad61bea02f9dd4b0a548ebafb096f4969 |
| E3=EXE-06 | c28c0a776b246fb3b0f654f3a94ac5068bacc775 + 82fcc160c7d2c5242ea9f4654ec38710b242ee35 | 6294534 | fx_exec_E3.diff (= git diff 6294534 82fcc16) | 29c1e7e1b7591c2fbbd17968131a9ce3c0499dfd109307e8509cd4e6afe0f268 |
| E4=EXE-02 | 3a641c3e7e1b6e351cec3f0a987e3fcd22ae54bc | 82fcc16 | fx_exec_E4.diff | 529b588c4fde2f4b618a109fc0c74da38fdda32b8c22f0decf801e24098df265 |
| E9=ALM-04 | a21797d | 3a641c3 | fx_exec_E9.diff (= git diff 3a641c3 a21797d) | 76f4c2ca1df44c1f642eb46f4135f7eaa3635b8218cb60c35ce85f369482694e |

研究仓收据提交: 3600d99e(E2–E4, 104 文件)· 81e24fdd(E9, 22 文件)。

## E2 = EXE-05 · broker 直接 GET 补查读路采用结算链的请求级容量冲突合同
### 问题
复审 R4 §2.2: last_fill_details 在 POST 缺金额时 GET 补查, 身份门拿 GET origQty 比 POST 回包 origQty。研究员反例 Qs10 BUY RO; POST cap8/C4/cumQuote null/PARTIALLY_FILLED; GET cap6/C6/CANCELED ⇒ clamped venue 8 + executed_qty 6 + executed_qty_final True, 无 capacity_conflict; 结算链 _merged(R3-A1)判具名冲突。反序 6→8 直读是身份矛盾、链是容量冲突。
### 事实表(@ef60f85)
F1 补查仅在 POST 缺 cumQuote/avgPrice 时(binance_broker.py L1600)。F2 补查门 origQty 参照 = POST 值, 缺才用我方数量(L440; 函数 L427)⇒ GET6<POST8 当「截量的截量」放行, GET8>POST6 判矛盾。F3 out["clamped"] 保留 POST 的 {10,8}(L1552–1562, L1613–1614)。F4 merge 从 CANCELED 快照给 executed_qty_final True(L1625, L1634)。F5 补单腿消费: _fin1 = terminal ∧ executed_qty_final ⇒ confirmed_qty_final(binance_executor.py L1928, L1947)⇒ 请求在 C6 关闭。F6 目标合同 = venue_fills.py L259–275 / L304–309(逐条对 Qs 判身份; 带身份且 origQty 为值者逐条比首条 1e-6; 不一致 ⇒ capacityConflict{why,sent=Qs,records}, canon=Qs, 无 clamped, 非终局, 非身份矛盾)。F7 退出行(L954)与 flatten_all._exec(broker L1805)只读金额/均价/时间。F8 真账本: 补单请求账本自 09-12 起 150 个, 0 个 re-query 矛盾; 旧码 8→6 静默放行不留痕(E2/e2_fact_census)。
### 旧码红
同测试文件放 ef60f85: 110/120 rc1, 0 崩溃, 10 红格恰为缺陷格(明细 = 研究员输出逐字: clamped{10,8}/final True/orig_qty 8; 反序 re-query identity 矛盾; 真 MEME 回包两向; 1e-6 边; 门本身; PARITY 5 格分歧; 补单链 filled_qty 6; reconcile 合法 8 读成 20U 残差)。E2/fx_exec_E2_red_ef60f85.log。
### 修
binance_broker.capacity_conflict(records, sent) 与 _merged 同式(CAPACITY_CONFLICT_WHY 同文本; _merged 未改, PARITY 逐格钉等); requery_identity_mismatch 参照改为我方所发 Qs(订单无数量才回退 POST 值; 高于 Qs 仍矛盾); last_fill_details 判为我方后调用, 冲突 ⇒ 撤 clamped、具名 capacity_conflict、orig_qty=Qs、executed_qty_final False; topup 把 _d1 冲突具名写入请求账本(_req_qty 以 Qs 为界, _final_known 不认任何生产者旗)。
### 测试(tests_reduce_only_clamp [T13] 19 格)
研究员反例逐字 + orig_qty 为界; 反序; 真 12Z MEME 回包正反 + 一致正控; 6 邻格(8/8、>Qs、非 RO、GET 无 origQty、POST 无 origQty、无身份回包); 1e-6 边; 门本身; PARITY(9 对, 判决与理由文本全等); 原链(真 topup() → 请求账本 → reconcile: 空10→空2 在 [6,10] 0 异常, →多1 仍异常)+ 链正控; flatten_all 邻格。6294534 干净头 120/120 rc0; 原 91 check AST 保留。邻格 13 套 rc0; tests_reject_topup rc1 两格读账本, 与 ef60f85 逐字同红, 交全电池真 state 裁决。
### 未证
1 场所是否发过这样一对记录: 未观测, 旧码不留痕, 频率不可测。2 一致截量时补单账本仍不写 qty_venue(带按 Qs, 失败向宽)。3 直读门只比在场字段, 结算 _valid 要求 orderId/side/origQty 在场 —— 缺席严格度差异未统一。4 退出行/flatten_all 不记冲突; 冲突不单独分页。5「无改单动词」仍是前提(T12 静态格)。

## E3 = EXE-06 · 损坏事件日志 = 具名 NOT OBSERVABLE, 失败关闭
### 问题
复审 R4 §2.2 末格: 事件行为 JSON 数组时 _flatten_action_orders 抛 AttributeError, 以异常结束, 无具名结论。
### 事实表(@ef60f85)
F1 json.loads 后 ev.get("ts") 在只捕 ValueError/TypeError 的 try 里(tests_disposition_matrix.py L687–689)⇒ 顶层数组/数字/null 抛出。F2 actions 迭代在 try 外; _mark_recorded_failures 迭代 orders/failed(L691, L697–711)⇒ 数字 TypeError、_exec 列表 AttributeError。F3 非 JSON 与 ts 坏行 continue 静默跳过 ⇒ 若是平仓记录且账本侧该批也缺, 两侧同空, 完整性格照绿。F4 R3-A2 承重格对保留批次重跑 _reconcile_flatten(L1219)⇒ 无可读记录 KeyError / 联接键读不出 ValueError。F5 同族: ops/rejudge_ledger_rows._rows/submit_records(L53–56, L67–83)对损坏行抛出, 收据不写。F6 写者 watchdog.py L2538。F7 真日志 15 行全是写者形状, 10 条 flatten_all。
### 旧码红(外部突变: 13:04Z 副本上逐行损坏, 每次还原核 sha)
ef60f85 套件(sha 874b354a)12 突变: 8 异常退出(数组×2/数字/null/actions 数字/orders 数字/_exec 列表/failed-client_id 批 attempt_idx 'x' ValueError); 4 静默全绿 rc0 68/68(非 JSON 行、ts 坏行、非对象 action、以及「平仓记录行非 JSON 且该批 105 行账本也删」—— 一整批从两侧同时消失照绿)。收据工具新格首格在 6294534 明细 AttributeError(另两格为新字段/新辅助函数格)。E3/e3_ext_mutants*_OLD.log, mutants/。
### 修
_flatten_event_log(path) ⇒ (actions, unreadable): 一次读; 非 JSON/顶层非对象/ts 非 evaluated_utc/actions 非列表或含非对象/flatten_all orders|failed 非列表、order 非对象或 _exec 非对象/读取抛出 —— 按行号具名, 不贡献动作; _flatten_action_orders 合同不变。完整性格状态表为每条不可读行加 NOT_OBSERVABLE 条目(原格条件逐字不改)。逐批对账 try/except ⇒ 具名 NOT_OBSERVABLE; R3-A2 承重格改读主循环 _flat_state(82fcc16 跟进)。收据工具 _event_lines 具名不可读行; 收据 events_unreadable/events_fully_readable; 交叉核对加 events_fully_readable。
### 测试
matrix 新 4 格(真日志逐行可读、十种损坏形态合成红能力、正控、两侧同失); 13:04Z 副本 72/72 rc0(fx_exec_E3_green_disposition_ledger_82fcc16.log)。82fcc16 同 12 突变 12/12 rc1、0 崩溃、点名 events.jsonl line N / reconciling this batch raised ValueError(e3_ext_mutants_FINAL_82fcc16.log); c28c0a7 曾留 1 崩溃(F4), 82fcc16 修掉(e3_ext_mutants2_NEW.log 留档)。clamp T10-E3 3 格: 6294534 120/123 rc1, 82fcc16 123/123。AST matrix 56/56、clamp 111/111。结构邻格 5 套 rc0。
### 未证
1 读不回损坏行原内容; 两侧同失批次只以不可读行出现。2 事件日志整行丢失仍不可见(无第二来源)。3 后备只包事件侧; 账本侧损坏行在本文件其他段落未普查。4 执行器其他 JSONL 读者不在范围。

## E4 = EXE-02 · 已停名出场: from_partial 不进任何追单路径, from_reject 转换保留, 留存告警
### lead 裁定 R2′(逐字)
> Reasoning: specific beats general. The per-name stop clause (PREREG cf40ea21, activated 0bcc089 on 08-20) explicitly names its exit policy for stopped names: maker placement, policy A, no chase. The 09-01 chase restart (PREREG_chase_restart 1a3f4333, 8b7a61e) changed ARM_WEIGHTS for the randomised experiment on the general rebalance population and never mentions stopped or flatten_only names. Folding stop exits into that experiment contaminates the experiment's population and breaks the clause text.
> A from_reject IOC conversion is different. A post-only order refused with -5022 would have executed at our own limit, so converting that residual to IOC at the same limit is not a chase: no later price improvement is sought. The conversion also existed when the clause was activated and was never exempted, so the clause as adopted included it.

★ 前提更正(FX-EXEC 报, lead §4.2 接受并裁定 (a)): 「IOC at the same limit」与代码不符 —— 补单单体无价(binance_executor.py L1885), submit 按 "LIMIT" if price else "MARKET"(binance_broker.py L1498)⇒ from_reject 转换是无价 MARKET reduce-only, 仅补单时刻点差门 MAX_CROSS_BPS 25(L308)。已停持仓名 from_reject 成交相对原 maker 限价(+不利): PROMUSDT 08-26 00Z +155.8 / BTRUSDT 08-31 16Z +48.3 / 09-01 04Z −240.7 / MAGMAUSDT 09-02 08Z −42.9 / XANUSDT 09-08 16Z +71.7(2,137U)/ 20Z −0.8 bps。裁定 (a) 保留(08-20 批准「走既有 flatten_only 通道 — 零新执行形态」, 政策 A 下该通道已有 MARKET 转换); (c) 原限价 IOC 另立设计候选; docstring/告警文案并入 E6。
### 事实表
F1 条款 cf40ea21 §1「flatten_only: 目标归零, maker-only 出场, 政策 A 不追 —— 不是市价平仓, 零新执行形态」; per_name_stop.py L7–9。F2 政策 A = 08-10 用户裁定全不追(chase_policy.py L134–141, 164285b)。F3 09-01 用户裁定重启 {0,1}→{0.5,0.5}, 随机域 = C skip 集, 未提已停/flatten_only(PREREG_chase_restart sha 1a3f4333, 8b7a61e, STATE [09-01 14:3xZ])⇒ 规程停手报 lead ⇒ R2′。F4 通道: force_flat → flatten_only → RO GTX maker → topup(): from_partial 进追单框架(C 强制/随机臂/回退人人追), from_reject 转换; 两者都无价 MARKET RO(binance_executor.py L1582–1627, L1863, L1885; anchor_loop.py L2367)。F5 版本: 5879149(08-01 桶)· 55e941d(08-02 框架)· 164285b(08-10 政策 A)· 0bcc089(08-20 激活, topup 无任何豁免, 已读源)· 8b7a61e(09-01)· W9(ef60f85 接入被钉多头)。F6 普查 08-20..09-13 12Z 157 个已停且持仓实例: 政策 A 期 taker 发出 3(全 from_reject); 重启后 4(3 from_reject + LSKUSDT 09-12 12Z from_partial chase +253.7 bps)+ 2 no_chase 扣下(E4/e4_fact_census)。F7 人口: 重启后 70 锚 8,868 次分配中已停名 11 次 = 0.124%(chase 5/no_chase 6); 政策 A 期 6,386 中 10 次 = 0.157%(全 no_chase)(E4/e4_population_census)。F8 真锚 09-12 12Z A1789215839: 人口 192 全随机(C fill 空, 书净 −167.52 在 1.5% 带内), LSK=chase; 计划期止损集 = 08Z phase_C {IOSTUSDT, LSKUSDT}(IOST add_blocked 无残差)。F9 skipped_no_chase_arm 是实验处理组终态(chase_readout / check_chase_first_anchor 计数), 已停名不得复用。
### 旧码红
同测试+夹具放 82fcc16 与 ef60f85: 70 PASS/8 FAIL rc1, 0 崩溃: E4-1 LSK 仍 chase 人口 192; E4-3 真 192 名走真 topup(), LSK 发出(submit_ts、arm chase); E4-5 无留存报告; E4-6 无处置格; E4-8 SSS 照追; E4-C1 DRY_RUN run_anchor→complete_anchor 原链 SSS 发 1 张 submit_dry_run; E4-C2 无告警/字段; E4-S 无 stop_names。
### 修
chase_policy.plan_experiment(exclude=): 名单在 C 与抽签之前离开人口, 记录 excluded_before_assignment; 其余抽签只哈希名字不变。topup(stop_names=): _plan_chase_experiment 以 exclude 传入(不计入 others); 已停名 from_partial 残差在点差门与地板门之后、臂门之前写 skipped_stop_maker_only(不发、无 arm); from_reject 分支不动; stop_exit_report 点名本锚未发出的已停名(地板尘埃除外)。complete_anchor 以 _pns_sets["stop"](不含冷却)传入; 有留存 ⇒ HIGH 告警(名/终态/残差/政策), 阶段 B 输出 stop_exit_carried。新终态 skipped_stop_maker_only 进 pilot_log.TERMINAL_REASONS + order_disposition GAP 格。
### 测试(tests_per_name_stop [E4] 13 格; 夹具 live/tests_fixtures/e4_stop_exit + build_fixture.py + MANIFEST)
E4-F 夹具有效性; E4-1 排除(192→191 只移 LSK); E4-2 其余 191 名臂逐位不变、no_chase 净额不变、复算通过; E4-3a 执行器层有效性(真 192 名驱动真 topup() 的记录 == 实盘记录); E4-3 红格(LSK 拒绝追单 skipped_stop_maker_only 85.77049032U 不发); E4-4 其余行与发出集合不变; E4-5 留存报告; E4-6 schema/处置/缺口账本; E4-7 保留(真 PROMUSDT 08-26 00Z、BTRUSDT 08-31 16Z from_reject 各发 1 张 RO, 不进留存); E4-8 冷却名/普通名不受影响; E4-C1/C2 原链(DRY_RUN 外部书: 已停持仓多头 SSS 不发 + HIGH 告警 + stop_exit_carried); E4-S 静态。3a641c3 干净头 78/0 rc0; 原 41 check AST 保留。邻格 19 套 rc0; tests_reject_topup 同 E2 账本红; tests_entrypoint_wiring 首跑子进程超时(与 E3 突变并发), 复跑 1 格「sleep LOG was read」红, ef60f85 逐格同红(读克隆过期 nosleep 状态), 交全电池真 state 裁决。
### 未证
1 留存 maker 出场是否成交: 场所侧未验; 可能锚复一锚不成交(每锚告警、永不追)。2 from_reject 仍是无价 MARKET(裁定 (a)), 可比原限价差 +155.8 bps。3 止损集取计划期; 阶段 C 新触发的名下一锚起豁免。4 per_name_stop.py docstring 与触发告警「⇒ flatten_only(maker 出场, 不追)」未改, 按 §4.2 并入 E6。5 DRY_RUN 入口类套件在克隆执行真 run_anchor, 读场所公开行情(klines/funding)并写克隆 state/(无凭据无下单), 历次克隆电池同此; 已 git checkout -- state 还原, 提交一律显式 pathspec。〔lead 已要求在后续段落列明所调公开端点。〕

## E9 = ALM-04 · false NO_PRODUCER from the artifact check (原文英文)
Committed, receipts committed, not deployed.

**COMMIT CHAIN**
- Executor clone /Users/haosiyu/cc_tmp/fx_exec, branch fix/known-issues-2026-09-13: ef60f85 → 6294534 (E2) → c28c0a7, 82fcc16 (E3) → 3a641c3 (E4) → a21797d (E9).
- a21797d changes 8 paths, checked with `git show --name-only`: ops/assert_anchor_artifacts.py; live/tests_artifact_assertions.py; ops/gate_coverage.py; live/tests_fixtures/e9_constant_columns/{build_fixture.py, MANIFEST.json, orders_20260913_00Z_halted.jsonl, orders_20260913_to_12Z_subset.jsonl, history_20260912_subset.jsonl, live_alarm_lines.txt}.
- Research repo commit 81e24fdd (branch research/book-uplift-2026-09-11), explicit pathspec, 22 files: docs/receipts/fx_exec_E9.diff = `git diff 3a641c3 a21797d`, sha256 76f4c2ca1df44c1f642eb46f4135f7eaa3635b8218cb60c35ce85f369482694e; docs/receipts/fx_exec_SHA256SUMS (now 4 diffs); docs/fixprogram_2026-09-13/FX_EXEC/receipts/E9/ (19 files plus SHA256SUMS). t6_sha_guard check gives 0 mismatches on both sums files.

**FACTS (before code)**
1. Two live pages came from the check: 12:46:59Z, 12Z anchor: NO_PRODUCER=['filled_unknown_qty','filled_unknown_residual']. 00:39:51Z, halted 00Z anchor: eleven columns = fee_all_usdt, fee_assets, filled_known_notional, filled_known_qty, filled_qty, filled_unknown_qty, filled_unknown_residual, request_ledger, requote_arm, requote_p, spread_at_submit_bps; plus fills.* NO_PRODUCER.
2. Cause, in check_artifacts: a column constant all day went to NO_PRODUCER unless it was STRUCTURAL, proven by history in EVENT_DEPENDENT, or in FILL_DEPENDENT with zero fills. Some writers run only when an event happens (an unknown remainder in the request ledger; a submitted leg; a submitted or filled leg off DRY_RUN; a -5022 post-only reject). None of these had a model of that event, and a day on which nothing was sent had no excuse at all.
3. This is also a mask. Pages are de-duplicated by finding set, so while a false finding stands, a real loss of one of these writers would read "findings unchanged".
4. The premise is checked on real rows (receipt e9_reader_vs_row.log): the executor's own reader `ledger_row_columns(request_ledger)` matches the persisted columns on all 704 real rows that carry a ledger (09-12 and 09-13 up to 12Z), with 0 mismatches. On 09-13 no row's ledger implies an unknown remainder (0 of 263). On 09-12, 2 rows did, and those columns were filled in.
5. The 09-13 day copy was taken read-only from ~/dl_quant_live/state; its sha256 is on file in day20260913_copy_sha256.txt.

**FIX (ops/assert_anchor_artifacts.py only)**
- EVENT_TRIGGERS maps 11 columns to their trigger event, written as a predicate over one persisted row and taken from the writer's own condition: ledger columns ask `ledger_row_columns`; request_ledger: a submitted top-up leg, or a submitted maker leg off DRY_RUN; spread: a submitted leg off DRY_RUN; fees: a filled leg off DRY_RUN; requote_*: a from_reject row or a venue_reject with -5022.
- If a column is constant and no row carried its event (with no unknown row), it is EVENT_NOT_YET, and the why says "did not occur on any of N rows".
- If any row carried the event, or any row cannot be judged, it stays NO_PRODUCER. The why names the count of rows that carried it and the count that could not be judged. If the reader cannot be imported, it also names the import error.
- A no-trade day means rows exist, no row has submit_ts and no row has a nonzero fill. On such a day, FILL_DEPENDENT ∪ EVENT_TRIGGERS columns are MODE_EXPLAINED, and so is an empty fills table. The why lists the terminal reasons.
- A column not in the map is unchanged and is still NO_PRODUCER.
- The new branches sit after the STRUCTURAL, history-proven and FILL_DEPENDENT branches, so none of those states changes label.

**TESTS: live/tests_artifact_assertions.py [E9], 8 new cells**
- E9-F: the fixture is valid. The 4-row verbatim subset reproduces the whole day's profile to 12Z (1,258 rows). The 00Z file is that anchor's 243 rows, all unsent. The live alarm lines are on file.
- E9-1 (red on old code): the real 12Z day gives EVENT_NOT_YET for filled_unknown_*, NO_PRODUCER is empty, ok.
- E9-2 (red on old code): the real halted 00Z day gives MODE_EXPLAINED with "no leg left the process" for all eleven columns and fills.*; NO_PRODUCER is empty.
- E9-2b (neighbour): the same day keeps attempt_idx/cancel_ts/order_type EVENT_NOT_YET and rebalance_id UNDETERMINED.
- Must stay red (red on both versions): E9-3 one real top-up row whose ledger now leaves an unknown remainder → both columns NO_PRODUCER. E9-4 a column nothing writes (checked by AST over live/scheduler/ops/signal) → NO_PRODUCER. E9-5 the halted day plus one submitted leg with no recorded spread → no longer a no-trade day, so spread_at_submit_bps is NO_PRODUCER. E9-6 the ledger reader cannot be imported → filled_unknown_* stay NO_PRODUCER. A failure to look is never EVENT_NOT_YET.

**RED / GREEN / AST / NEIGHBOURS**
- The suite at a21797d run against old checker code, on both 3a641c3 and ef60f85: rc=1, with exactly E9-1 and E9-2 failing on assertion content, not on a crash or a missing fixture. At head: ALL PASS, rc=0.
- AST: old check sites 11, new 19, lost 0, added 8 (ast_keep_check_E9.log; the baseline file's sha equals `git show 3a641c3:live/tests_artifact_assertions.py`).
- Neighbour suites at head, all rc=0: gate_coverage, tests_imports, tests_rehearsal_anchor, tests_signal_and_loop, tests_state_root, tests_static_names.
- Whole-day reproduction on the real 09-13 copy (e9_repro_fullday_*): old code: 00Z, 04Z and 08Z (A1789259039 / A1789273440 / A1789287840) each give ok=False with the same eleven columns plus fills.* NO_PRODUCER, the same as the live alarm. New code: all four anchors give ok=True and NO_PRODUCER=[]. At 12Z the only EVENT_NOT_YET columns are filled_unknown_*; 00/04/08Z are MODE_EXPLAINED.
- Fixture trees old vs new: e9_fixture_trees_*.

**BOUNDARIES / NOT PROVEN**
- EVENT_TRIGGERS is a hand-built map. Its predicates copy the writer's condition as of a21797d. If a writer's condition changes later, the map can go stale in the permissive direction for those 11 columns. Only the ledger predicates call writer code. The submitted/filled/-5022 predicates are copies, and no test pins them against binance_executor.
- On a no-trade day the check cannot see a lost submit-side writer. Such a day carries no information about one, and that is now named in the why instead of paged.
- DRY_RUN/TESTNET mode trees were not re-run separately beyond the existing "summary line exists" cell in the green log.
- The live alarm_episode dedup was not touched.

## 队列
E10(LED-06)→ ALM-03 → OPS-01b → E5(EXE-07)→ E6(含 EXE-03 告警归因、止损 docstring/告警改写)→ E7 → 全电池(最终头、真 state 副本、非锚窗)→ 叠加 diff fx_exec_stack.diff。

## E10 = LED-06 · ledger notary (clone 6523440, parent a21797d; 原文英文, lead 逐字转录 16:3xZ)
Committed in the clone as 6523440, 58 paths, checked with `git show --name-only`. Not deployed. Research-repo receipts staged, committed after 16:50Z. Diff: docs/receipts/fx_exec_E10.diff = `git diff --binary a21797d 6523440`, sha256 5cb3d56fdc2b46b0d3c2f5744839319f7a4f561a6d00aeef0e009d04f990632f.

**FACTS** (read-only census of ~/dl_quant_live/state/live/pilot_log against all 43 manifests in ~/Desktop/quant_research/ledger_notary; receipt e10_live_census.log)
- F1 (a) The old contract was one whole-file sha256 per file. 301 files: 259 unchanged, 42 grown. Every grown file is fills.jsonl, and every growth is a pure append at a newline boundary, with 0 bytes changed inside the notarized bytes. All appended lines parse. Appended rows carry backfilled_utc, except on 09-09: 3,095 of 6,199 rows have none, carry rebuilt_from_venue (FLATTEN-20260909T164536Z, the 09-09 repair), and none duplicates a notarized (trade_id, symbol, rid). Under the old contract, 42 of 43 days read as "altered".
- F2 (b) notary.log shows 13 runs (08-31..09-12). Each printed "7 files notarized", then `git add` failed with rc 128 "fatal: Unable to read current working directory: Operation not permitted" and a traceback.
- F3 Chain census: 08-01 is GENESIS, 08-02..08-30 are LINKED (29), and 08-31..09-12 are 13 BREAKs, each with prev=GENESIS although a predecessor exists. All 13 are untracked in the research repo. Mechanism: `glob` swallows the listing error, so it returns [] and the code writes GENESIS, while creating a file by its full path still succeeds. Reproduced in a sandbox: on a mode-0300 directory, glob returns [], os.listdir raises PermissionError, and a create succeeds. The launchd/TCC refusal itself is not reproduced: loading a launchd job is out of bounds. `log show` for 09-13 00:11:58–00:12:10Z returned no entries.
- F4 (c) The commit went to whichever branch was checked out, and the push was hardcoded to `origin multi-asset-v2` with check=False, printing "committed+pushed" regardless. The research repo is currently on research/book-uplift-2026-09-11.
- F5 (d) `glob("*")` notarized every file in the day directory. `git add ledger_notary` plus a commit with no pathspec would sweep any unrelated staged research file into a "notary:" commit.
- F6 Two more same-family defects: the old code hashed a file, then called getsize, so bytes and sha could describe different byte ranges under a concurrent append; `open(out,"w")` silently rewrote an existing manifest, chaining it to itself.
- F7 The E1 receipt checkpoints are notarized 1,357,906 → pre_e1 1,364,944 → post_e1 3,504,070. The live 09-12 fills.jsonl is currently 3,504,070 bytes.

**FIX** (ops/notarize_ledgers.py; config/ledger_notary.json)
- Manifest v2 records only pilot_log.SCHEMA tables, as `{bytes, sha256, tail_excluded_bytes}`; bytes and sha cover one read cut at the last newline; other files are listed in not_notarized; missing tables in absent_tables.
- Listing failure (notary directory or day directory) means rc 2, a HIGH alarm, and no manifest written.
- GENESIS is written only with `--genesis` into an empty directory. An existing manifest is never rewritten: existence check plus an O_EXCL write. A day earlier than the chain tip is refused.
- Append checkpoints: each run records `appends` (day, file, before = last checkpoint, after = current, n_lines, reason, device sha256) for every earlier day that grew. A changed prefix, truncation or partial-line append is recorded in integrity_findings, still committed, and gives rc 2 plus an alarm.
- git: refuses if no branch is configured, or if the checked-out branch differs from the configured one; `add -- <paths>`, `commit -- <paths>`, then verifies HEAD names exactly those paths; pushes `<remote> <branch>` only if push_remote is set; every rc is checked, and every failure raises a HIGH alarm carrying git's own line; .env is loaded at import except for `verify` (tests_env_loading population).
- verify_tree (`notarize_ledgers.py verify`) is read-only. File verdicts: EXACT / APPENDED (segments with n_lines and attested_by) / TAMPERED / TRUNCATED / MISSING / PARTIAL_LINE_APPEND. Amendment verdicts: VERIFIED / MISMATCH / ORPHAN / UNREADABLE; reads both the new `append_amendment` record and the legacy E1 shape. Chain verdicts: GENESIS / LINKED / BREAK. rc: 0 all good; 1 a file or amendment is bad; 3 files and amendments good but chain broken; 2 unreadable.
- Amendment API: `amendment_record` / `write_amendment` (day, table, before/after bytes+sha, reason, device path+sha).
- Config keeps the original author's intent explicit: branch multi-asset-v2, push_remote origin. **Deployment decision:** with the repo on another branch, and TCC blocking git under launchd, the deployed job will page HIGH every day until one of these happens: the repo is on that branch and TCC is resolved, the notary moves out of the Desktop repo, or the config changes.
- The 13 existing GENESIS manifests are not rewritten. Committing them as they are is a research-side decision; their only timestamp would be the commit date.

**VERIFIER ON THE LIVE TREE** (read-only; e10_verify_live_readonly.json at head 6523440)
- rc 3: files_ok and amendments_ok true, 259 EXACT and 42 APPENDED. Per-day segment line counts match the independent census exactly.
- 09-12 fills.jsonl splits into two segments, both attested by the E1 receipt (VERIFIED): 1,357,906→1,364,944 (12 rows) and 1,364,944→3,504,070 (3,656 rows).
- The 13 chain breaks are named. So the verifier accepts today's 09-12 state plus the amendment receipt, and it does not hide the history.

**TESTS**: live/tests_ledger_notary.py, 36 cells. Sandbox: temp ledger, temp git repo plus a local bare remote, and a fake git that fails exactly as logged; alarms go to a temp audit with LIVE_ALARM_SUPPRESS. The old code runs as a byte copy with only its two path constants rewritten (the harness checks each rewrite matches exactly once). The research repo's ledger_notary is untouched: still 43 files, 13 untracked, same mtimes.
- Writer cells: W0 neighbour normal run; W1 unlistable directory gives no GENESIS, rc≠0, alarm; W2 git fails like launchd, the alarm carries the fatal line and 未提交; W2b the manifest is still written; W3 push failure alarms and never prints "pushed"; W4 branch mismatch means no commit; W5 pathspec only, another staged file stays staged; W6/W6b SCHEMA-only with not_notarized and absent_tables; W7 no rewrite; W7b the write is exclusive under a race; W8 GENESIS only with the flag; W9 append checkpoint; W10 past-day tamper is recorded and alarms; W11 a mid-append file is notarized to its newline and later verifies as APPENDED; W12 every alarm is tier A (policy PUSH).
- Verifier cells: V1 markout-style append via PilotLogger is consistent; V2–V5 neighbours (prefix change, change plus append, truncation, partial line) none accepted; V6/V6b/V6c amendment VERIFIED / MISMATCH / ORPHAN; V7 chain BREAK named, rc 3.
- Real-data cells (fixture live/tests_fixtures/e10_notary: the seven real 09-12 files gzipped, all 43 real manifests, the E1 receipt, byte copies with sha in MANIFEST.json): R-F fixture validity; R1 accepted with the two E1-attested segments; R2 the 13 breaks named, rc 3; R3 without the receipt, still APPENDED, one unattested segment of 3,668 rows; R4 one hex digit of post_e1 changed gives MISMATCH; R5 neighbour one byte changed at offset 1,000 is not accepted.

**RED / GREEN / MUTANTS / NEIGHBOURS**
- Old code: the same suite at a21797d and at ef60f85 gives rc 1, 23 FAIL = exactly the 23 OLD-CODE-RED cells, and 13 OK = H0–H3, W0, W2b, W6a, V2–V5, R-F, R5. No traceback in the harness. W1 old: rc 0, prev GENESIS, "nothing to commit" plus "warning: could not open directory" — the launchd failure, silent. W2 old: CalledProcessError traceback, no alarm.
- Green: ALL PASS at the worktree and at head 6523440 (dirty 0), 36/36.
- Mutants, 15, one property each: before W7b existed, 14 killed; M11 (manifest opened "w") survived, because the existence check already refuses and the O_EXCL write was untested; W7b added, M11 then killed by W7b. A full 15-mutant re-run at head goes into the receipts after 16:50Z.
- pyflakes clean on both new files.
- Neighbours at the worktree: gate_coverage, tests_static_names, tests_imports, tests_markout_import, tests_pilot_log, tests_ops_flag_safety all rc 0.
- tests_env_loading is rc 1 on both a21797d and head (known clone red, no .env). Head adds exactly one red cell of the same kind, "ops/notarize_ledgers.py populates TELEGRAM_*". e10_env_probe with a FAKE .env in a temp tree: notarize_ledgers populates TELEGRAM_* on import (1), matching the ic_monitor control (1); it does not for `verify` (0), nor with no .env (0).

**INCIDENT (FX-EXEC's own, recorded)**
- tests_acceptance_entrypoints was launched as a neighbour without reading it first; it runs the whole battery. It ran 82 suites on the dirty clone from 15:53:53Z until its process tree was killed at ~16:04Z, before the 16:15 window. Its results are not used anywhere. The tracked state/ files it modified were restored with `git checkout -- state`, and its 82 state/acceptance logs were deleted. The full battery at the end covers that suite. 〔lead 注: 该次运行含 DRY_RUN 公开行情 GET, 发生在电池窗口规则发布之前(规则 16:0xZ)。〕

**BOUNDARIES / NOT PROVEN**
- The TCC refusal is not fixed and not reproduced; the new code only makes it loud.
- An unattested append is accepted by construction. The verifier names it but cannot say the rows are true.
- The last manifest in the chain has no successor, so it is protected only by its git commit. verify does not check commit or remote state, so it does not flag untracked manifests.
- The first deployed run will write one large `appends` list: 42 files have grown since their manifest entries.
- The job reads all notarized days each run: about 150 MB today, about 2 s measured.

**NEXT**: ALM-03 (39a0055) and OPS-01b (a12a78a) also committed in the clone; report sections follow. Receipts for all three go to the research repo after 16:50Z.

## ALM-03 = W5, option A · commit 39a0055 (parent 6523440), 13 paths (原文英文, lead 逐字转录)
Not deployed; receipts committed after 16:50Z. Diff: docs/receipts/fx_exec_ALM03.diff = `git diff --binary 6523440 39a0055`, sha256 326b052d705a273e767cf36d06d8a881b03934b22a3b2897c2f619efd249d031

**FACTS**
1. Step 9 (run_anchor L772–787) called check_factor_health.run(). That function ssh-reads the jpline report, retired since 08-06. The live factor_health_last.json says report_unreachable, decay_judged false. Its episode has been open since 09-04 12:45Z.
2. Assertion #9 was `decay_judged or _fh_absent`. Since 08-06 it has passed on every anchor.
3. #55 ic_monitor has written ic_monitor_evals.jsonl since W1, which is ef60f85 (commit time 2026-09-13T12:04:14Z). The live evals ledger did not exist when the fixture was built; its first row is due 09-14 01:30Z. W1's census already carries newest_row_anchor_ts separately from frontier_ts, so §5-2 needed no change to #55.
4. #55's own check() on the real ic_monitor.jsonl (228 rows, last anchor 09-12T08Z): 09-14 01:30Z INCOMPLETE (r24 missing 9 anchors because of the 09-12 flatten); 09-05 01:30Z OK, judged. Scanning 08-15..09-14 at 01:30Z gives no ALERT or DECIDE. The live log's 09-09/09-10 DECIDE lines came from code before W1's freshness gate.

**FIX**
- New ops/check_rank_monitor_input.py, named per §5-3. It checks the input health of the position-rank monitor and issues no decay verdict. 10 states — ok: JUDGED; NOT_JUDGED (INCOMPLETE with census windows); INFO known gap, not paged: LEDGER_ABSENT_IN_GRACE; HIGH: LEDGER_ABSENT (after the fixed grace 2026-09-14T18:04:14Z), LEDGER_UNREADABLE, SHAPE, EVAL_STALE (>26 h), UNSTAMPED, DATA_LAG_CONTRADICTION (judged but newest anchor lags frontier by more than 2 anchors), NOT_JUDGED_WITHOUT_CENSUS.
- Only HIGH states page, per §5-5. The episode key is a stable sentence naming the evaluation, never an age. The text is tier A and matches no alarm_policy rule (an earlier state name "…UNEXPLAINED" matched the book/venue-disagreement rule, so it was renamed).
- Step 9 now calls RMI.run. The failure branch is HIGH (used to be INFO; that ruling was about a research box and this check reads a local file).
- #9 evaluates #55's ledger at check time using the same evaluator (not step 9's state file, because #9 runs before step 9 in the same anchor). Pass: JUDGED; NOT_JUDGED with census; absence before the fixed grace (named gap). Everything else fails.
- check_factor_health.py: RETIRED paragraph added and __main__ refuses to run (exit 2, no ssh). All other bytes unchanged.
- tests_imports production list: check_factor_health replaced by check_rank_monitor_input (drift check required this; a data list, not an assertion).
- gate_coverage: tests_factor_health and tests_frontier_staleness entries now say they pin a retired evaluator. New entry for tests_rank_monitor_input.

**TESTS** · live/tests_rank_monitor_input.py, 19 cells
- Harness: each behavioural cell drives the module that run_anchor's step 9 actually imports (read from its source), in a sandbox, then runs #9 on the same sandbox. On old code, `fetch` returns None (the observed state); nothing is contacted. Eval rows come from #55's own check() plus append_eval on the real ledger. Fixture live/tests_fixtures/alm03_rank_monitor holds byte copies with sha of ic_monitor.jsonl, factor_health_last.json, the factor_health episode, and the live head/time.
- F0–F2 fixture and facts. Red on old code: A1 real situation after grace → #9 fails naming LEDGER_ABSENT (old #9 passed); A2 real 09-14 INCOMPLETE → NOT_JUDGED with "r24: 9 expected anchors missing", no page, #9 passes; A3 real 09-05 OK → JUDGED, frontier 09-04T20Z, observed 09-04T20Z, lag 0; A4 EVAL_STALE pages once, next anchor does not re-page; A5 fixed grace (same grace_until at 09-13 16Z and 09-14 18:00Z; at 18:05Z LEDGER_ABSENT); A6 DECIDE (R24_P1 moved to 0.5) → JUDGED, not paged; A7 / A7b INCOMPLETE without census, or with empty windows → HIGH; A8 truncated last row → UNREADABLE; A9 UNSTAMPED (R24_P5=None); A10 lag 3 → contradiction; A11 all 7 pages are tier A with no rule matched; A12 no subprocess ran, step-9 module imports nothing networked; S1 constants equal #55's (EVALS, GRID_S, MAX_MISSING r24); S2 W1 time equals ef60f85 +08:00 converted to Z; S3 step 9 imports the new module, no runtime importer of check_factor_health remains.

**RED / GREEN / MUTANTS / NEIGHBOURS**
- Old code (6523440 and ef60f85): 16 FAIL, exactly the old-red cells; 3 OK (F0–F2); 0 tracebacks. A1 old detail: #9 {ok True, "upstream ABSENT by ruling… not a regression"}. Other old cells: no source field; the only page is INFO UNREACHABLE.
- Green: 19/19, at head dirty 0.
- Mutants: 11 of 11 killed in the final run (alm03_mutants.log). First run, disclosed: M1 (grace reset each run) and M10 (step 9 back to CFH): expectation lists wrongly included A1; they were killed by A5 and by A2/A12/S3; A1 is about #9, independent of step 9; lists corrected. M5 was an equivalent mutant (a redundant clause) and survived; replaced with "drop the non-empty-windows clause", cell A7b added, killed.
- Neighbours, all rc 0: tests_factor_health, tests_frontier_staleness, tests_book_weights_effective, tests_alert_tiers_live, tests_artifact_assertions, tests_imports, tests_static_names, gate_coverage, tests_ic_monitor. Existing suites' check() and assert statements unchanged; tests_imports has none (list diff on file).
- tests_entrypoint_wiring actually runs step 9; heavy, runs after 16:50Z or in the battery.

**OPTION A COST, AS DECLARED**: the retired evaluator stays under test (4 suites plus red_capability mutants 6/7). 〔lead: 删除 RETIRED 路径并改指四个套件 = 登记为需复审给 §0 例外的后续项。〕

**BOUNDARIES**: the eval rows are check() run by the suite, not rows #55 wrote under launchd; ALERT/DECIDE/UNSTAMPED shapes need one #55 constant moved; it cannot see whether #55's launchd job is loaded, only whether its ledger moves; the grace is anchored on W1's commit time, not the actual deploy time.

## OPS-01b · commit a12a78a (parent 39a0055), 5 paths (原文英文, lead 逐字转录)
Diff: docs/receipts/fx_exec_OPS01b.diff sha256 8be588e1514d1f5719e1c924480609d63044a9d0bb872f1222ceae93f4c1840e

**FACTS**
- anchor_loop (L1762–1780 at ef60f85) imported sigma_ladder in external mode. When the file was accepted with g=0.5, it sized at NAV×gross_mult×0.5 and raised only an INFO alarm. A rejected file also raised INFO.
- sigma_ladder.DEFAULT_PATH falls back to ~/dl_quant_live/state when LIVE_STATE_ROOT is unset, so test processes were sized by the live tree's file. No such file exists on live now.
- tests_sigma_ladder pins only the module (evaluate/load), not the wiring.

**FIX**
- External sizing is always `_size_book(target_leverage=(external["gross_mult"] if _is_ext else None), …)` (already the default call; the S4 static text in tests_external_book is unchanged).
- `_bw["gross_ladder"]` records reason "retired_not_read (OPS-01b…)".
- anchor_loop no longer imports sigma_ladder. live/sigma_ladder.py stays.
- tests_imports: sigma_ladder removed from the production list (drift check).
- gate_coverage: tests_sigma_ladder entry says it pins a retired evaluator. New entry for tests_gross_ladder_retired.

**TESTS** · live/tests_gross_ladder_retired.py, 6 cells. Harness: a real external-book DRY_RUN anchor (the tests_external_book [L] harness, copied), with LIVE_STATE_ROOT set before any import. F0 the ladder path is inside the sandbox; F1 the fixture file is ACCEPTED at g=0.5 by the ladder's own load(); O1 neighbour no file → gross 10,000; O2 (red on old) a fresh accepted g=0.5 file → gross still 10,000, target W8×10,000 bitwise, no σ_fund alarm, record says retired_not_read; O3 (red on old) a rejected file raises no "被拒" INFO; S1 (red on old) no runtime module imports sigma_ladder.

**RESULTS**: old code (39a0055 and ef60f85): O2 gross 5000.0 with leverage_source "external_book.gross_mult×ladder(0.5)" and INFO "σ_fund 阶梯低档"; O3 INFO "被拒(sha_mismatch)"; S1 names scheduler/anchor_loop.py; 3 FAIL, 3 OK, 0 tracebacks. Green: 6/6 at head. Mutant "record line dropped" → O2 red; a full revert is the old code itself. Neighbours, all rc 0: gate_coverage, tests_imports, tests_static_names, tests_sigma_ladder, tests_external_book, tests_signal_and_loop, tests_per_name_stop, tests_guard_calibers. Boundaries: the internal path never read the ladder and is not exercised here; another future exposure multiplier would not be caught; the launchd state is OPS-01's receipt.

Unrelated observation: pyflakes reports `undefined name 'List'` at anchor_loop L2390, pre-existing at ef60f85 L2381, harmless under `from __future__ import annotations`, not touched.

NEXT: E5 = EXE-07.

## E5 = EXE-07 · origQty reasons (clone b8581f5 + 4058b85 text follow-up, parent a12a78a; 原文英文, lead 逐字转录)
Not deployed. Diff: docs/receipts/fx_exec_E5.diff = `git diff a12a78a 4058b85`, sha256 90a2cd3ea806f91fd64a4455ad654f61b4b69edbd7ada269618b6165bd17d501. Receipts staged in FX_EXEC/receipts/E5, committed together with E10, ALM-03 and OPS-01b after the E10 mutant re-run. Spec: take every origQty reason, fail closed on any inconsistency, add red tests.

**FACTS** (ef60f85 = a12a78a for these files)
- F1. `_clamp_rederived` checks that every ";"-separated reason is the origQty kind (C6), then takes both numbers from the first pair in the whole string (`_ORIGQTY_PAIR.search`). The disposition ruler's `_clamp_known` does the same.
- F2. Measured on the old code: the writer's own "; " joiner fails closed only by accident. The `ours` group `(\S+)` swallows the ";", so "1933986.0;" does not parse. The accident does not cover a " ; " joiner (the joiner the C6 fixture itself uses) or two comparisons with no ";" between them. In both cases the old code re-derives from the first pair and ignores a second reason naming a different accepted capacity (the R3-A1/E2 conflict); the verdict then depends on reason order.
- F3. `_rederive_ledger` drops every origQty-kind row-level entry whose client id was re-derived, whatever the entry says. The ruler's `_row_rejudged` does the same.
- F4. Same-family defect found while writing E5: the writer copies each request string into the row as `str(inconsistent)[:120]` (binance_executor L194). If a single reason is longer than 120 characters, the copy loses "differs from ours"; the old kind test then leaves the writer's own copy of a re-derived request standing, and the row reads as a false "unquantifiable" that depends only on string length (the protective-false-positive family of E-0912-A). Real strings today are 105 characters (MEME) and shorter (POPCAT); none has crossed 120.
- F5. Census, read-only across 44 days (e5_fact_census.log): 949 rows carry a request ledger; 2 request-level contradiction strings (the E-0912-A MEME and POPCAT rows), both single-reason with one pair each, both row-level entries equal their request's `[:120]` copy; no multi-pair string exists. Conclusion: no real row changes verdict.

**FIX** (conservative; never widens re-derivation beyond the validated single-reason shape)
- `reconcile._origqty_pairs(why)` parses each reason on its own, so no joiner can leak into a number. It returns a pair only when every reason is the origQty kind and holds exactly one finite pair; otherwise None.
- `_clamp_rederived` G1: re-derive only when the string is exactly one reason with exactly one pair. Several comparisons stand, whether agreeing or conflicting, in any order or joiner, glued or not.
- `_rederive_ledger`: a row-level entry is dropped iff its client id was re-derived and `why == str(request.inconsistent)[:120]`. No kind test is applied to the copy (fixes F4).
- Ruler (tests_disposition_matrix): the same two rules, written in-body in `_clamp_known` and `_row_rejudged`; no new module-level names (respects the independent researcher's `pure()` probe).
- ops/rejudge_ledger_rows.py: `evidence.string_pairs` lists every pair parsed per reason; string_Qv and string_Qs named only when exactly one pair; new cross_check field `string_has_exactly_one_pair` feeds `all`.
- gate_coverage: E5 sentence added to the tests_reduce_only_clamp and tests_disposition_matrix entries. 4058b85 only removes a doubled period.

**TESTS**
- tests_reduce_only_clamp [T14], 11 cells, on the real 12Z MEME row with one reason added: F fixture; E5-1 neighbour ("; " conflict stands on both versions; the old code stands only because of the ";" accident); red on old code: E5-2 " ; " conflict stands; E5-3 both orders give the same verdict; E5-4 glued comparisons stand; E5-5 a repeated comparison stands with either joiner; E5-6 a row-level entry naming a different contradiction stands and names itself; E5-7 a single reason over 120 characters re-derives and its truncated row copy is dropped; E5-9 the rejudge tool lists both pairs, string_Qv None, has_exactly_one_pair False, `all` False, row unquantifiable; neighbours E5-8 (C6 foreign join and a lone non-origQty reason still stand), E5-10 (the real day through the tool still gives both rows known with every cross-check true).
- tests_disposition_matrix [G7-E5], 5 cells: red on old E5-R1 (the ruler re-judges none of 6 multi-comparison shapes), E5-R3 (row entry with a different string), E5-R3b (long single reason); neighbours E5-R2 (single real comparison, −1015.1883), E5-R4 (ruler equals runtime-final on all 7 shapes, including single and single_long).

**RED / GREEN / AST / MUTANTS / NEIGHBOURS**
- Red on a12a78a: tests_reduce_only_clamp 127/134, exactly E5-2/3/4/5/6/7/9 fail, 0 tracebacks. tests_disposition_matrix with the OLD ruler plus the new E5 cells: 3 fail (R1/R3/R3b), 0 tracebacks; old detail `{'conflict_spaced': True, 'glued': True, 'duplicate_spaced': True, …}` re-judged.
- Green: tests_reduce_only_clamp 134/134 at head 4058b85, dirty 0.
- tests_disposition_matrix on a real-ledger copy (fx_exec_ledger state, 83M pilot_log): a12a78a 72/72; 4058b85 77/77; every non-E5 cell identical. The clone's tiny tracked state gives 10 ledger-dependent failures, not E5 cells.
- AST: tests_reduce_only_clamp 114 → 125 sites, lost 0; tests_disposition_matrix 60 → 65, lost 0 (the ruler's function bodies changed, as that suite's code under test).
- Mutants 8 of 8 killed: runtime M1–M5 (several pairs accepted, whole-string first pair, row equality dropped, kind test restored, rejudge first pair); ruler M6–M8. The first ruler-mutant run crashed on an empty ledger in the temp tree before reaching the E5 cells; re-run with only the subtrees the suite reads (pilot_log orders/anchors plus watchdog events, copied from the ledger worktree, not live): all 3 killed (e5_mutants_dm.log).
- Neighbours all rc 0: gate_coverage, tests_reconcile_qty_caliber, tests_request_identity_unknown, tests_residual_vector, tests_ghost_rows, tests_watchdog.

**BOUNDARIES**: not proven that the writer never emits a multi-comparison or over-120-character string, only that none exists and that none would be re-derived, respectively that the long one is no longer misread. A legitimate multi-record clamp with agreeing capacities now stands (deliberate, conservative; the current writer records clamps as the fourth state and writes no string for them). The ruler and the runtime are still two implementations; E5-R4 pins parity only on the E5 shapes.

**NEXT**: E10 mutant re-run at head; ALM-03 tests_entrypoint_wiring neighbour (DRY_RUN run_anchor; battery window rule applies); research-repo receipts commit for E10, ALM-03, OPS-01b and E5; then E6.

## E6 · alarm and doc texts = code (clone 2210596 + 719d8e7, parent 4058b85; 原文英文, lead 逐字转录)
Three alarm and doc texts that did not match the code (clamp-alarm source, stop-exit wording, EXE-03 attribution) now do. Not deployed. Research repo: diff docs/receipts/fx_exec_E6.diff (sha256 6a6dbc9fb26bb0fc42a9d193151b36e7b2dcbae8bccb357c39b263219ec661f8); receipts commit eb1566a0 (FX_EXEC/receipts/E6, t6 check 0 mismatches). 719d8e7 = follow-up: the gate_coverage edit had not applied in the first commit.

**FACTS** (all read-only on live)
- A. The held-withheld page blamed the venue for every name. At 09-13 16Z (A1789316640) it read: "7 held name(s) are withheld by the venue (maxNotionalValue=0)". The anchor row's recorded sources are external held_exit (CLO, EVAA, KSM, NOT, US) and external dust below 2×minNotional (ENSO, ZK). No zero-cap is recorded. 125 such lines exist in notify_audit, all filed B_EXPECTED. Seven sources feed `_untradable`: universe status, venue zero-cap, per-name stop, cooldown, external meta, held-exit and dust.
- B. The stop-exit descriptions were wrong or had no stated scope. The per_name_stop docstring said "maker-only 出场 … 政策 A 不追" and the trigger event said "flatten_only(maker 出场, 不追)". What the code does: a refused maker is converted at top-up to MARKET reduce-only, behind MAX_CROSS_BPS=25 and the min-notional floor (E4-7; PROM 08-26 / BTR 08-31); only a partially-filled maker's residual is not chased (E4). FX-EXEC's own E4 texts (STOP_EXIT_POLICY and the carried-residual page) said "maker-only" without scope.
- C. EXE-03: the 撤名残差 page wrote "由 N 个撤下的名字造成". net_before = producer book net − removed names' net. Real 08Z (A1789287840): producer −18,511.19 and removed +1,964.62, giving −20,475.81.

**FIX**
- anchor_loop, alarm text: `WITHHELD_SOURCE_LABELS` plus `held_withheld_alarm_text(clamp, sources)`: each held name is listed under every source that recorded it; a held name with no recorded source is listed as "来源未记录", never defaulted to the venue; the text keeps "reduce-only from here", so it stays tier B. run_anchor records `_untradable_sources` at each of the seven union sites. `_universe_gate` now also returns `withheld_status_names` and `withheld_zero_cap_names`.
- anchor_loop, reshape: `apply_withhold_and_reshape` records `net_producer_usdt`, `net_removed_usdt`, `n_removed` and `removed_names`, with net_before = producer − removed. `reshape_residual_alarm_text` keeps the "撤名残差" head, so it stays tier C.
- binance_executor: STOP_EXIT_POLICY now sits after MAX_CROSS_BPS and takes the number from it. It still contains "maker-only" as E4-5 requires, now scoped to the partial residual.
- per_name_stop: docstring 动作 section and trigger event rewritten; parameters, trigger logic and cooldown logic unchanged. Trigger tier unchanged. The complete_anchor carried-residual page is rewritten and reads MAX_CROSS_BPS from binance_executor.
- Not changed: the chase-policy behaviour. EXE-03's per-side scaling remains a registered-experiment question (P8).

**TESTS** · tests_per_name_stop [E6], 13 cells. Fixture e6_withheld_sources, built read-only from the 16Z anchor row, per_name_stop.json, the notify_audit alarm row and the clamped names' orders.
- E6-F fixture validity.
- Red on old: E6-A1 / A1b the real 16Z sources are attributed correctly, no maxNotionalValue=0, unheld cooldown names absent, still tier B; E6-A2 a name with two sources is listed under both, an unrecorded source is named; E6-A3 in the W9 DRY_RUN chain, the page that actually fires puts SSS under 逐名止损已停; E6-A4 a second DRY_RUN external anchor puts held YYY under held-exit and SSS under stop; E6-A5 a stub LIVE universe gate reports HALT under status and ZCAP under zero-cap; E6-B1 text equals code (docstring, trigger event, STOP_EXIT_POLICY and carried page all state maker-first, refused maker converts to 市价/MARKET reduce-only, the "25" read from MAX_CROSS_BPS, partial residual not chased; none contains the unscoped claims; the same cell checks MAX_CROSS_BPS==25, E4-7 sent reduce-only, and E4-3 LSK skipped_stop_maker_only); E6-C1 real 08Z net_producer / net_removed with the identity holding to ≤1e-6; E6-C2 the text states both figures, no "造成", tier C; E6-C3 in the W9 chain the page that actually fires uses the new text.
- Neighbours (green on both): E6-B2 (trigger tier matches the ef60f85 text), E6-B3 (carried page still tier A and still carries E4-C2's "maker-only" and SSSUSDT).

**RESULTS**: red on 4058b85: 10 FAIL, exactly the old-red cells, 0 tracebacks (examples: A3 old "1 held name(s) are withheld by the venue…"; C3 old "撤名残差 -1111.11 … 由 1 个撤下…"). Green: 91/91 at head, dirty 0. AST: 54 → 67 cells, 0 lost. Mutants: 9/9 killed (M6 was first built wrongly — it deleted a variable and crashed with NameError; rebuilt as "producer net computed after the pop" and killed by C1/C2, e6_mutants_M6_rerun.log). Neighbour suites, all rc 0: tests_book_reshape, tests_venue_cap_clamp, tests_neutral_band, tests_external_book, tests_binance_executor, tests_alert_tiers_live, tests_imports, tests_static_names, gate_coverage, tests_signal_and_loop, tests_universe_guard.

**BOUNDARIES**: a future untradable source added without a label will show as 来源未记录; alarm_policy's rule name for that page still reads "held name withheld by venue" (policy table left alone); the 25 in the per_name_stop texts is a copy, caught by B1 if the constant changes (STOP_EXIT_POLICY and the carried page read the constant directly); coordination: per_name_stop.py L6–9 and L130 rewritten, hunks sent to fx-exec2.

**NEXT**: E7, then the stacked diff and the full battery.

## E7 · two W2-registered reader defects (clone d4ed6b6, parent 719d8e7; 原文英文, lead 逐字转录)
Diff: docs/receipts/fx_exec_E7.diff sha256 f33b38fec64a16714c604dac5e7e46f670a34726f35bf0f35832f15b56fd9eb8. Receipts: research commit 43bf3430 (FX_EXEC/receipts/E7; t6 check 0 mismatches). Nothing is deployed.

**FACTS** (read-only census, e7_fact_census.log)
- (a) daily_summary.main set `nav = [rows with nav_ts >= since] or nav_all[-1:]`. When the window held no nav row, the account section printed the ledger's newest row, whatever its age, and the header counted it as "1 nav row(s)". Old-code red output: wallet 5,080 / equity 5,100 shown for a window that began 58 minutes after that row. The live ledger has 259 nav rows with a max gap of 8.13 h, so under the default 24 h window this happens only on stale state copies or short custom windows.
- (b) first_anchor_review §3b summed target_w only where `target_w is not None`. A name with None dropped out silently, and a NaN printed as nan. The partial sum was printed as "INTENT net … over the N names that got rows", and VENUE minus INTENT was computed from it. Old-code red output: "INTENT net +90.00 … over the 1 names" with a difference of −190; for NaN "+nan USDT". The live ledger has 77,874 order rows and none has a None or non-finite target_w. The schema allows it: target_w is required but not in not_null.

**FIX**
- (a) Only nav rows inside the window are used. With none, `account_facts` reports NOT OBSERVABLE, and the header prints "★ 窗口内没有 daily_nav 行: 账本最新一行 nav_ts=<UTC> 在窗口之前(<h>), 未使用 …".
- (b) A name counts as known if any of its rows has a finite target_w. If any name has none, the block prints "INTENT net UNKNOWN — k of n name(s) have no finite target_w: [names]"; the partial sum is shown but labelled NOT the intent net, and VENUE minus INTENT is not formed. The all-finite output is byte-identical to before; the REVERSE cell still passes.
- gate_coverage: blind spots (h) and (i) are marked FIXED by E7.

**TESTS**
- tests_daily_summary [E7-a], running the entry point on a temp ledger with --since 09:00Z against nav rows at 08:01/08:02Z: E7-a0 runs; E7-a1 (old red) account NOT OBSERVABLE, no equity line, header shows 0 nav rows; E7-a2 (old red) the page names the 08:02Z row as before the window and not used; E7-a3 neighbour: a window containing nav rows prints its account with no out-of-window line.
- Consequence: four existing [B3] cells — Q1, Q3, the sight-boundary line and the rotation line — used to pass only because of the stale-row fallback (the clone's state has no nav row within 24 h). After the fix they failed on correct behaviour. They were made conditional the same way as Q2 already in that file: the check calls are unchanged (AST-verified), and on 0 nav rows they print a declared SKIP. Added cell E7-a4 asserts the NOT OBSERVABLE account in that case. In the battery with a real state copy they will be exercised.
- tests_readers_three_bucket [E7-b], using the round-4 temp-ledger harness through first_anchor_review: E7-b1 (old red) target_w None gives UNKNOWN, "1 of 2", names FFFUSDT, no difference; E7-b2 (old red) NaN gives the same, and no "nan" appears; E7-b3 neighbour: a name whose maker row carries target_w while its second row has None counts as known; output is the all-finite block.

**RESULTS**: red on 719d8e7: tests_daily_summary fails exactly E7-a1 and E7-a2; tests_readers_three_bucket fails exactly E7-b1 and E7-b2; 0 tracebacks. Green at head: tests_daily_summary ALL PASS (102 checks, 10 declared SKIP, ledger-dependent); tests_readers_three_bucket ALL PASS (75 checks, 3 SKIP). AST: tests_daily_summary 108 → 113 check sites, 0 lost; tests_readers_three_bucket 73 → 76, 0 lost. Mutants 4/4 killed (fallback restored, out-of-window line dropped, NaN counted as known, partial sum printed as intent). Neighbours rc 0: tests_review_anchor_scoping, tests_rehearsal_anchor, tests_fills_supersede, tests_imports, tests_static_names, gate_coverage. tests_reject_topup rc 1, identical cell-for-cell on ef60f85 (ledger-dependent in the clone, already known).

**BOUNDARIES**: both are capability fixes; neither shape occurs in the live ledger today. The [B3] account-text promises are proven only where the window holds a nav row. 〔lead 注: [B3] 四格改为条件 SKIP 是对既有测试的执行条件改动(检查调用逐字未变), 列入复审关注项。〕

**QUEUE** (lead 裁定): NEW-02 attempt_idx + gate_coverage 重复条目 → 完整电池(BATTERY.lock, 19:15Z 前启动)→ EXE-04 (Q6) 作为单独项, 其后再跑电池。

---
## 事故 · 电池在窗口之外运行(2026-09-16 03:16:25–03:18:49Z; FX-EXEC 自报; lead 逐字转录并保留原文)

**什么**: 为做 gate_coverage 那项的邻格, 我跑了 `live/tests_acceptance_entrypoints.py`。该套件在其第 85–90 行 **两次 `bash run_acceptance.sh`** 以逐字节比较两个入口 —— 于是它跑了**整套电池**, 含 `tests_entrypoint_wiring`。**我在运行之前没有读它调用了什么。这是我的错误**: lead 给的电池规则点名的是 `run_acceptance.sh`, 而我没有检查一个套件是否**传递地**到达它。

**窗口**: 起 2026-09-16T03:16:25Z(运行器日志戳), 03:18:49Z 被我 kill, 约 2m24s。00Z 锚允许的窗是 01:05Z..03:15Z ⇒ **我在窗口关闭 85 秒后开始**(我先报的「约 70 秒 / ~1m10s」是估计不是测量; 精确重算: 03:16:25Z 距锚 11,785 s, 限 11,700 s ⇒ **85 s**。收据已带实测值并把原估计标注为估计)。**锁没有被持有。**

**出去了什么**: 只有未签名的公共行情 GET。证据是克隆内 DRY_RUN run_anchor 写出的状态: `exchange_info_cache.json` 03:17:59Z · `funding_last_pull.json` 03:18:00Z · `panel_cache/funding.npz` 03:17:47Z · `panel_cache/klines_1h.npz` 03:17:11Z。**我给不出请求权重数** —— `tests_entrypoint_wiring` 自己的日志是 0 字节(03:17Z 建立, 运行中被 kill, stdout 仍在缓冲)⇒ 该计数在我这侧无上界。由那些文件推出的端点为 exchangeInfo、funding/premiumIndex、klines。我 kill 时**第二次 run_acceptance 也已经启动**。

**没有发生什么**(从树上断言, 非假设): 克隆内无 `.env`; `BINANCE_API_KEY` 未设; `LIVE_MODE` 未设 ⇒ 代码默认 DRY_RUN 生效; `state/pilot_log/20260916/` 只含 `_schema.json` —— **orders.jsonl 与 fills.jsonl 均不存在**, 所以没有下单也没有撤单。`~/dl_quant_live` 与 `~/wide_shadow` 未被触碰。

**清理**: 删除 `state/acceptance/20260916T031625Z_*` 与 `state/pilot_log/20260916/`; `git checkout -- state`(现 0 个被跟踪状态文件为脏)。**我故意没有跑 `git clean -- state`** —— 它会删掉套件要读的既有未跟踪真实状态副本(`state/live/pilot_log/202608*`、rate_timeline、fixtures)。收据: `/Users/haosiyu/cc_tmp/fx_exec_work/new02/INCIDENT_battery_outside_window_20260916T0316Z.log`, 随我的收据一起提交。

**我要做的改变**: 今后不跑任何套件之前, 先 grep 它的 subprocess / bash 调用。具体说, **`tests_acceptance_entrypoints` 与 `run_acceptance.sh` 同属「只在电池窗口内」**, 我建议把这条明确写进电池规则, 因为规则原文只点名了运行器。我正在把新写的 gate_coverage 格移出该套件, 放进不 shell-out 的套件, 以便随时可跑。

**另需单独指出**: 我继承这个克隆时**树并不干净** —— `state/` 有约 20 个被修改的跟踪文件与大量未跟踪件, 时间戳 2026-09-13T18:01Z, 即上一轮电池的残留。现在被跟踪文件已干净。

### lead 处置(FIXPROGRAM §14.1)
- **风险核(03:21Z, 只读)**: 04Z 锚尚未开始, GET 距锚起点 42 分钟, 场所权重窗为 1 分钟 ⇒ 已完全衰减; 00Z 锚峰值 847/2400 ⇒ **对下一锚无实际影响**。不改变违规性质; 04Z 锚跑完后由 lead 核 `rate_budget` 与 −1003/−4400 计数补进本收据。
- **规则按传递闭包重述(全体, 立即生效)**: 任何**直接或间接**执行 `run_acceptance.sh` 或发出任何场所请求的套件, 一律受窗口(N+65min..N+3h15m)+ `BATTERY.lock` 约束; 跑套件前先 grep 其 `subprocess` / `bash` / `os.system` / `requests`; 判不准即当作受约束。已知传递到达者: `live/tests_acceptance_entrypoints.py`。新写的 gate_coverage 类格放进不 shell-out 的套件。
- **两条处置纪律记为先例**: ① 立即上报且在继续工作之前上报; ② **故意不跑 `git clean -- state`**(会删掉套件要读的既有未跟踪真实状态副本)。
- **继承树不干净单独立格**: 要求给出被改文件清单、是否影响任何已交付的红/绿判定(逐项)、还原后的树 sha; 任何依赖该残留的格必须重跑。

---
## NEW-02 · `venue_fills.py:1179` 平仓成交行的 attempt_idx(克隆 6d11ba38; lead 逐字转录 2026-09-16 04:0xZ)

**哪一侧是对的: 订单侧。** 两张表对该列的定义相同 —— pilot_log SCHEMA 在两边都把 `attempt_idx` 设为 not_null, 因为它是「我们自己的」; 一条阶梯行的含义是**第几次阶梯尝试**(`watchdog.py:2390`、`tests_flatten_rows.py:30`, 在真实的 07-26 触发上断言 103/103/2); 一张被重挂的 maker 带 2 而 `order_type` 仍是 "maker"(`binance_executor.py:1307`)。**成交写者是从腿类型 INFERRED 出来的** —— `1 if otype == "maker" else 2` —— 这个代理在三处失效。

**真实数据**(只读副本, 逐文件 sha 在收据里): 09-12 平仓 = **255 条订单行全为 attempt 1, 7,312 条成交行全为 attempt 2** ⇒ 按 (rebalance_id, symbol, order_type, attempt_idx) 的 orders↔fills 连接 **7,312/7,312 全失败**。09-09 = 243 条订单行 attempt 1, 6,190 条成交行 attempt 1, 0 失败 —— 因为那批来自**另一个写者**(`pilot_journal/tools/backfill_flatten_fills_20260909.py:85` 在调用同一个函数之后把 attempt_idx 覆写为 1)。所以**两个写者都硬编码**; 它们一直看起来对, 只是因为**实盘历史上每一次阶梯都在第一次尝试就成功**(8 个平仓日订单行 1,708/1,708 全在 attempt 1)。

**按 attempt_idx 连接或分桶的读者 —— 完整普查在事实表**。执行器侧: **成交表的读者没有一个用它**(m2_markout 按 order_type 分桶; 去重/collapse 键是 trade_id; `assert_anchor_artifacts` 的逐列恒定性只查 ORDERS, 对 fills 只到表级)。**确实使用它的** —— m3_fill_rate、reject_rate、score_post_fix、`anchor_loop:855`、处置矩阵的 (symbol, side, attempt_idx) 连接 —— **全都读 ORDERS**, 所以都不受影响; 而处置矩阵那条连接**正是修复必须落在成交写者而不是订单侧的原因**。研究侧有两个装置按该键连接 orders→fills 且**确实被咬**: `retrain_2026-09/health_check_2026-09-05/calib/markout_diag.py:16,24`(平仓成交丢 `spread_at_submit_bps`)与 `calib/cost_calib.py:118,120`(平仓成交的 BNB 费变得不可归属, 被计入 `nofee`)。**markout_diag 的已发布窗是 08-26..09-05, 其中不含整书平仓, 所以没有已发布数字会变; 缺陷在代码里。** `export_fills_for_markout.py` 与 `survey_keys.py` 传播该列。

**我差点掉进去的坑, 也是「显然的修法」为什么错**: 一个 REBALANCE client id 以尝试次数结尾, 而一个 FLATTEN id 以 `next(_FLATTEN_SEQ)` 结尾 —— **一个进程级计数器**。在真实的 12Z 批上那些后缀是 **255 个互异值 1..255**, 对应 255 条**全为 attempt 1** 的订单行。**解析后缀会比缺陷本身更糟。** 这条现在是一格对着真实夹具断言的测试。

**修复: attempt 随腿走。** `attempt_from_client_id()` 只解析 `{rebalance_id}-{symbol}-<digits>` 这个精确形状(一个 flatten id 按构造解析失败; 36 字符的 id 被拒, 因为铸造时的 `[:36]` 会把 `-12` 变成 `-1`); `submitted_order_legs` 与 `order_legs_from_venue` 逐腿盖上 attempt_idx; 对平仓批由调用方提供 `{client_id: attempt_idx}`, 从该批**自己的订单行**读出(`find_gaps` 产出它, `backfill_batch` 传递); `attribute_trades` 像带 `leg` 一样带着它; `fill_rows_from_trades` 优先用它。一条解析不出来的平仓腿**仍然得到它的行**(成交是事实), 取树的未知尝试默认值 1, **并在行上带具名的 `attempt_idx_source`** —— 不是 2(那条规则不适用), 也不是静默的 1。这也**按构造**修好了那个潜伏的第二处: 一条被重挂的 maker 腿现在给出 2。该处从未触发过(两天的重挂 maker 行成交量都是 0)。

**证据**: 旧码 11 个红格 / 28 格中 17 格 / **0 个 traceback**; 修后 28/28 rc=0; 突变体 9/9 被抓且逐字节还原; 20 个邻居套件 rc=0; AST 13 处旧检查点逐字保留, 新增 12 处。**一个突变体(去掉 isdigit 守卫)第一轮没被抓到** —— `int(" 12")` 与 `int("+12")` 都是 12, 所以只有 try/except 会吞掉一个不是我们铸造的尾巴; 补了那一格重跑, 现在抓到。

**未做, 交给 lead**: 已落盘的那 7,312 行**没有被重写**。成交表只追加, 重写实盘账本属 LED-04 修订记录同族, 而我对实盘只读。在修订记录存在之前, 按该键连接的读者仍会漏掉那 7,312 行。(**lead 裁定**: 登记 **LED-09**, 与 LED-03/04/05 一同在复审时执行; 两个研究装置另登记为 **RES-01** 另派。)

---
## gate_coverage 重复键(克隆 4a29646d; lead 逐字转录)

`SUITE_SCOPE` 在**连续两行**上都写了 `"tests_external_book"`。存活的是当前文本(宇宙内归一化、宇宙列表缺陷、shadow_loop_v3、七个盲区); 被丢弃的是它的前宇宙前身(w/gross_norm、shadow_loop_v2、六个)。我删掉了陈旧的那条, 并**证明这次删除是运行期无操作**: `GATE_STEPS`、`RUNNER_BOUNDARIES`、`SUITE_SCOPE` 在删除前后哈希完全相同(SUITE_SCOPE 138 → 138)。**这正是关键 —— 字典字面量里的重复键由解析器消解**, 所以 `len()` 是对的、键是在的、`verify()` 的「每个套件都有边界陈述」通过, 连 `tests_external_book` 自己的 S7(`'"tests_external_book":' in gc`)也通过。**这次损失没有运行期签名; 只有文本能作证。**

所以断言必须在**源码层**: `duplicate_literal_keys()` 用 ast 读文件并扫描**每一个**字典字面量(`GATE_STEPS` 形状相同、同样沉默), 报出每个重复常量键及其**全部**行号; `verify()` 在内容检查之前消费它。`verify(self_path=)` 接受一个夹具路径, 于是**接线**由「指向一个植入了重复键的文件」来断言, 而不是靠 grep 源码 —— **改名不能让它变成哑的**。新格 S7b/S7c/S7d 放在 `tests_external_book` 里, 因为被重复的那条陈述正是该套件自己的, 而且该套件**不 shell-out**。

**写这个检查时发现了检查自己的 bug**: `sorted()` 对混合 int/str 键会抛 TypeError, 即**本该报告问题的东西反而会崩掉门**。S7c 的夹具各植入一个, 抓到了; 用 `key=str` 修好。

**证据**: 重复键在场时门 rc=1 并点名两行, 套件恰好红在 S7b(126 格中 1 格, 0 traceback); 删除后门 rc=0(9 步 / 138 套件), 套件 ALL PASS 126; 突变体 6/6 被抓; 邻居 tests_imports / tests_guard_reach / tests_rehearsal_anchor / tests_harvest_ema 全 rc=0; AST 102 处旧检查点保留, 新增 3 处。

**提交链**: `48e9938 → 6d11ba38`(NEW-02, 3 路径)`→ 4a29646d`(gate_coverage, 2 路径)。研究仓 `1764b1c9`, 74 个文件, 显式 pathspec, 用 `git show --name-only` 核过。差分 `docs/receipts/fx_exec_NEW02.diff` sha256 `0b462a1f…` · `docs/receipts/fx_exec_GATECOV.diff` sha256 `a13dfbb3…`; `fx_exec_SHA256SUMS` 12 行 `shasum -c` 全 OK, 0 FAILED, 无 e3b0c442。
