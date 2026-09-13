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
