> **创建:** 2026-09-12 13:2xZ | **Session:** https://claude.ai/code/session_01BzpuBRGZh8oPvpD8NgqsME | **状态:** §1–3 事实表+方案 → **§4 RESULT: (a)(b)+(1)(2)(3) = a211ea8, (c) 默认开 = 6013ea6 (用户字 13:19Z), 克隆分支 fix/e0912a-reduce-only-clamp; 未部署; 部署与恢复 = 用户字** | **作废条件:** W6 落地后转收据; 或用户裁定回滚 d040c74

# DESIGN W6: E-0912-A 修复 —— reduce-only 截量不是矛盾, 全退出按持仓张数下单, 局部「未知」不平全书

**一句话**: 三处改动, 每处对应事实链的一环, 每处有会红的测试与旧码红。(a) `binance_broker.submit_identity_mismatch` 加第四态 **clamped**; (b) `binance_executor.plan` 全退出的数量 = 持仓张数; (c) 看门狗 §4-5b 对「场所记录自洽、仅我方读不出」的少数名执行**比例响应**(停开仓 + 告警 + 只处置那几名), 全书平仓保留给真实事件。(a)(b) 是点修; (c) 是书行为改动 ⇒ **需用户裁定**(本文给性质与判据, 不替选)。

## §1 事实表(收据 = ERROR_LEDGER E-0912-A 七条; 行号 = 运行树 918559f)
| # | 事实 | 位置 | 修哪一环 |
|---|---|---|---|
| F1 | 全退出(`target_w=0`, 持有)⇒ 计划 `reduce_only=True` ⇒ 回执 `"reduceOnly": true`(设计如此, 保留) | `anchor_loop.py` L1630, L1930–1932; `binance_executor.plan` L757 | — |
| F2 | 数量 = `round_qty(delta / mid)`; delta 由 `current_notional`(持仓 × mark)得 ⇒ mark ≠ mid 时数量 ≠ 持仓张数(MEME +294 张 = 0.015%; POPCAT +1) | `binance_executor.plan` L774 | (b) |
| F3 | 交易所对 reduceOnly 单 qty > 持仓: 截到持仓, 回执 origQty = 持仓(两名逐张相等), 不报错(-2022 只在无仓/方向错) | 回执 `events.jsonl` 12:47Z 行 submit/resp | (a) |
| F4 | `_ident_check(origQty)` 相对容差 1e-6 ⇒ 「differs from ours」⇒ `inconsistent = "submit identity: …"` 直接 return(不再读 executedQty) | `binance_broker.py` L343, L1487–1491 | (a) |
| F5 | `ledger_inconsistencies` 把任何 `inconsistent` 字符串收为矛盾; `reconcile` 第 5 轮「矛盾最先」⇒ `unquantifiable`; D2 ⇒ `execution_of_unknown_size` 异常 | `binance_executor.py` L163–175; `reconcile.py` L200–203, L455–473 | (a)(c) |
| F6 | §4-5b 状态门 M=1: 最新对账锚任一异常 ⇒ 触发; §4-7 漂移 = `bool(_rec["latest"])` 同一对账 ⇒ 同因两条 | `watchdog.py` L1770–1867, `watchdog_inputs.py` L115 | (c) |
| F7 | 触发 ⇒ 阶梯 halt_opening → flatten_all(255 张 IOC reduce-only, 235,383 USDT, 5.39 bps 滑点 + 5 bps 费 ≈ 245 USDT)→ alert; 异常名合计 1,524 USDT = gross 0.65% | `watchdog/state.json` degradation, `events.jsonl` | (c) |
| F8 | 历史: `differs from ours` 今天前 0 行; 08Z 四类标记 0/0/0/0 ⇒ 首次出现 = 首次「全退出 + mark≠mid」 | `pilot_log/*/orders.jsonl` 扫描 | 测试用真行 |
| F9 | 复审 15 轮 + 电池 132 套无 reduce-only 截量正控; 身份核对三态(absent/malformed/value)缺 clamped | `binance_broker.py` L300–345 docstring; `tests_*` | 新套件 |

## §2 方案
### (a) clamped 态(`binance_broker.py`)
`_ident_check(rec, "origQty", expected, what)` 前置: 若 `order.reduce_only is True` 且 `resp.reduceOnly is True` 且 `0 < origQty < expected`(同侧、更小)⇒ 返回 **None** 并在 `out["clamped"] = {"ours": expected, "venue": origQty, "why": "reduceOnly clamped to position"}` 记录; `orig_qty` 取回执值(它就是持仓); 后续 executedQty / 子成交按 origQty 为界。**不放宽**: origQty > ours、方向不符、非 reduceOnly 的 origQty 差, 仍是矛盾。容差 1e-6 不动。
### (b) 全退出数量 = 持仓张数(`binance_executor.plan`)
`target == 0 and held != 0` ⇒ `qty = -held_qty`(读回的 `venue_position_qty`, 非 notional/mid), 仍过 `round_qty`; 其余路径不变。效果: F2 差异从源头消失, (a) 成为纵深防御而非主防线。持仓张数缺失(读回无 qty 列)⇒ 退回旧路径并记 `qty_source=notional_over_mid`。
### (c) 比例响应(书行为改动, **用户裁定**)
判据(冻结先于看数): 最新对账锚的 `execution_of_unknown_size` 异常若满足 **全部**: (i) 场所记录自洽(回执 origQty == Σ 子成交, 读回该名持仓与之相容); (ii) 异常名 Σ|intended| ≤ gross 的 **2%** 且名数 ≤ **5**; ⇒ 响应 = 停开仓 + HIGH 告警 + 仅对这些名做 reduce-only 复核(不平其他名); 不满足任一 ⇒ 现行全书阶梯。§4-7 漂移与 §4-5b 共用对账 ⇒ 同一判据。选项: **A** 采用上述 2%/5 名; **B** 仅停开仓+告警, 不自动处置; **C** 维持现行(任一未知 ⇒ 全书)。我方建议 A。
### 测试(全部先红后绿; 旧码红)
`live/tests_reduce_only_clamp.py`(新): T1 真回执(MEME 12Z 行, 逐字)⇒ 新码 `clamped`、`inconsistent` 空、orig_qty 1933692; 旧码 `inconsistent` 非空。T2 origQty > ours 同 reduceOnly ⇒ 仍矛盾。T3 非 reduceOnly 的 origQty 差 ⇒ 仍矛盾。T4 方向错 ⇒ 矛盾。T5 `plan` 全退出: held_qty 1933692 / mark≠mid ⇒ qty == −1933692。T6 读回无 qty ⇒ 退回旧路径且记 `qty_source`。T7 端到端: 12Z 真账本三文件(orders/fills/position_readback)经 `reconcile` ⇒ 新码 MEME/POPCAT `known`(residual 0), `anomalies` 0; 旧码 2 异常(=E-0912-A 复现)。T8 (c) 若采用: 合成 2 名/0.65% 自洽未知 ⇒ 局部响应; 6 名或 3% ⇒ 全书。电池全绿; `gate_coverage` 条目。
### 落地
克隆 `/Users/haosiyu/cc_tmp/exec_w6`(918559f 起); 研究员复审; 用户字 ⇒ 非锚窗 `fetch + merge --ff-only <sha>` ⇒ 首锚验收(RUNBOOK §3 + 新条目: 全退出名 origQty == 持仓, `clamped` 记录数, 四类标记 0)⇒ 用户手动恢复(看门狗 resume 动词按 state.json 说明)。
## §3 不做
不改 1e-6 容差; 不删身份核对(它对「回执不是我们的单」仍是对的); 不回滚 d040c74(等用户字); 不在事故期间落 W1/W2。

## §4 RESULT(W6, 2026-09-12 13:3x–14:4xZ; 克隆 `/Users/haosiyu/cc_tmp/exec_w6`, 分支 `fix/e0912a-reduce-only-clamp`; **未部署, 未 push**; 运行树 `~/dl_quant_live` 与生产者未动; 无网络)
**用户裁定 13:19Z(lead 转述「肯定是彻底修复, 回滚的版本有其他问题」)**: 彻底修复, 不回滚 d040c74; **(c) 默认 ON**(选项 A, 门槛按 §2(c) 冻结)。lead 12Z 深查追加三项: (1) reconcile 必须从账本条目内容重推持久化的矛盾; (2) T9 真 12Z 状态文件 + 恢复路径报告; (3) 阶段 B 告警文案带真实原因。
**提交链**(克隆内, 两个内容提交): `918559f` → `43a93bb` (a)+(b) → **`a211ea8`** (a)+(b)+(1)(2)(3) → **`6013ea6`** (c, 默认 ON)。收据: `docs/receipts/w6_reduce_only_clamp_ab.diff`(= `git diff 918559f a211ea8`, 21 文件, 含 4.3MB 真 12Z 全日夹具), `w6_proportional_response_c.diff`(= `git diff a211ea8 6013ea6`, 7 文件 +702/−6)。部署动词(用户字, 非锚窗): `git -C ~/dl_quant_live fetch /Users/haosiyu/cc_tmp/exec_w6 fix/e0912a-reduce-only-clamp && git -C ~/dl_quant_live merge --ff-only 6013ea6`(取 `a211ea8` = 不含 (c))→ 运行树 `run_acceptance` 实测全绿 → 首锚验收(§4.7)→ 恢复(§4.6)。

### 4.1 改了什么(file:line @ 6013ea6; 事实 F# 见 §1)
| 环 | 位置 | 改动 |
|---|---|---|
| (a) 一条规则 | `live/binance_broker.py` L336 `_record_says_reduce_only`, **L342 `reduce_only_clamp()`** | 第四态 clamped 唯一裁定: 我方 reduce_only ∧ 记录 reduceOnly true ∧ origQty 有限 ∧ 0<origQty<ours 超出 1e-6 ⇒ `{ours, venue, why}`; 其余(高于 ours / 记录未标 / 我方非 RO / 0·缺·畸形)⇒ None ⇒ 原 1e-6 比较, 仍矛盾 |
| (a) 三道门 + 直接读者 | `binance_broker.py` L376 `_ident_check(…, reduce_only, clamp_out)`, L400 `submit_identity_mismatch`, L424 `requery_identity_mismatch`, L1548–1558/L1611 `last_fill_details` | 命中 ⇒ None + `clamp_out`; `out["clamped"]`, `orig_qty`=回执值(=持仓), 不置 `inconsistent`; 方向门在前不动; 三态 docstring 改四态 |
| (a) 结算门(**真事故路径**) | `live/venue_fills.py` L172 `_valid`, L192 `_valid_present`, L250 `_merged`, L281 `_clamp_of` | 同一规则; canon.origQty=场所值 + `clamped` 流入 details。只修 broker 不修此处 ⇒ 下一道门以「record origQty differs」复发(T7 逐链验) |
| (a) 容量 | `live/binance_executor.py` L47, **L92 `_req_qty()`**(qty_venue 否则 qty)→ `_final_known`/`request_remaining`/`ledger_totals`/`ledger_inconsistencies`/子成交闭合 L2058·L2087; L266 `_clamp_cols`; L1091 `submit_maker` 记 `venue_clamped`; L1560 `apply_fill_details`; L1679/L1785 请求行 `clamped`+`qty_venue` | executedQty/子成交以 origQty 为界; `qty` 仍=我方所发 |
| (b) 数量源 + 接线 | `binance_executor.py` L750 `plan(…, held_qty=None)`, L811–826; L2283 行带 `qty_source`; `scheduler/anchor_loop.py` L1095/L1109 `self._held_qty`(同一 `account_snapshot`.positions_contracts, 仅本锚), L1940 `plan(..., held_qty=…)` | 全退出 = `round_qty(−held)`, `qty_source=venue_position_qty`; 无张数/符号不合 ⇒ 旧路径 + `notional_over_mid` + note; `plan(` 调用行首字节不变 |
| **(1) 持久化矛盾重推** | `live/reconcile.py` L97 `_is_identity_origqty_kind`, L104 `_ORIGQTY_PAIR`, **L107 `_clamp_rederived(r, why)`**, **L137 `_rederive_ledger(o)`**, `_exec_qty` 首段 | 不信旗标: 请求级 `inconsistent` 为身份门 origQty 值比较 且 串内两数 0<venue<ours(场所要得更少; 高于 ours 仍矛盾)∧ |confirmed| ≤ venue ≤ |qty|(ours==该请求 qty)∧ Σtrade_qty==|confirmed| ∧ 同侧 ⇒ 已知量=confirmed_qty; 其他一切(more than requested / side / non-finite / malformed / 子成交不合 / 无账本 / 串无两数)仍 unquantifiable, why 带首条仍立矛盾 |
| **(3) 告警文案** | `scheduler/anchor_loop.py` `complete_anchor` 「阶段 B 歧义 maker 结算」 | 「(满页或查询失败: …)」→「— 逐名原因: SYM: <结算报告 why 或 fold inconsistent 前 120 字>」; 无原因者标明 |
| (c) 判据(冻结) | `live/reconcile.py` 常量 2%/5 名, `_venue_consistency`, `_gross_ref`, `unknown_size_local_eligibility`, D2 异常行 `venue_consistent`+`intended_usdt`, 返回 `unknown_size_local` + `latest_if_local_response`(`latest` 不变) | (i) 每已发请求 Σ子成交==|confirmed|≤容量, 读回==上锚持仓+已知(尘埃内); (ii) 名数≤5 ∧ Σ|intended|≤2%×锚 `target_gross`(无 anchors 行 ⇒ 不合格 → 全书) |
| (c) 开关+响应 | `live/watchdog.py` **`UNKNOWN_SIZE_LOCAL_RESPONSE = True`**(用户字 13:19Z; False=选项 C 受测分支), evaluate §4-5b 分区/状态 `LOCAL`/`local_responses`, `_local_response()`, `run()` `elif` | 开关开且合格 ⇒ 出触发表; 停开仓 → 重读场所仅复核这些名(超尘埃未解释部分 reduce-only 补平 + 写 protective_flatten 行/读回)→ ALARM.log HIGH; 不平其他名, 不设账户 reduce-only 键; state.json `kind=local_response` 带 `tripped_at`(anchor_loop 0b 跨进程续停开仓); trip 优先 |
| (c) §4-7 同判据 | `live/watchdog_inputs.py` L119–125 | 同一开关读 `latest_if_local_response`; 行加 `drift_local_response` |
| (c) 旧钉重述 | `live/tests_position_break_blindspot.py` L231 | 原「§4-5b 无 execution_of_unknown_size 豁免」(源码字符串缺席)按裁定重述: 唯一豁免 = reconcile 分区 + 具名开关(默认开, 2%/5 冻结), 触发表仍 `_latest`; 守卫未删 |
| 注册 | `run_acceptance.sh` L167/L170; `ops/gate_coverage.py` L186/L187 | 两新套件 + 盲区自述 |

### 4.2 测试(先红后绿; 旧码 = 同一文件跑在干净 worktree: (a)(b)(1)(3) 对 `918559f` `/Users/haosiyu/cc_tmp/exec_w6_old`; (c) 对 `a211ea8` `/Users/haosiyu/cc_tmp/exec_w6_a`)
| 套件 | 新码 | 旧码 | 收据 |
|---|---|---|---|
| `live/tests_reduce_only_clamp.py` T1–T7 + T7-ctl + **T7-persisted(12 格, 8 反例)** + **T3-alarm** + **T9a/b**(真 12Z 行逐字夹具; 真全日六表 `pilot_log/20260912`) | **70/70** | **32/70 rc=1**: T1/T5/T6/T7/T7-persisted/T3-alarm/T9 红; T2/T3/T4 与持久行反例两版皆矛盾 | `w6_tests_reduce_only_clamp_new.log`, `w6_oldcode_red.log` |
| ↳ T7 端到端 | 真链 `plan→submit_maker→complete_anchor`(FakeNet: POST=真回执逐字, DELETE=-2011, allOrders=回执+真子成交**重建**终态记录, userTrades=真子成交)→ `reconcile` vs 真 08Z/12Z 读回: 0 异常, 两名 residual 0, 请求行 `qty −1933986`+`qty_venue −1933692`+`clamped`; MEME 残差 −0.058U ⇒ `partial_expired`+补单 `skipped_min_notional`; POPCAT 残差恰 0 ⇒ `filled` 无补单行 | 旧码同链 2×execution_of_unknown_size | |
| ↳ **T7-persisted(1)** | 真持久 12Z 行(仍带旧旗标+串)经新 `reconcile` ⇒ **0 异常, 两名 known −1933692/−10434 残差 0**; 8 反例(子成交缺 / \|confirmed\|>\|qty\| / more-than-requested / side / malformed / 反侧 / qty_venue 低于 confirmed / 无账本 / **串内 venue 高于 ours** / 串 ours≠请求 qty / 串无两数)全 unquantifiable | 旧码 2 异常 | |
| ↳ T7-ctl | origQty=ours×1.001 突变 ⇒ 两版仍 2 异常。发现: +1 张在 MEME 1.93M 上 = 0.5e-6 落在既有 1e-6 容差内(两版同, 未动) | | |
| ↳ **T3-alarm(3)** | 突变链告警含「逐名原因」+ 两名 + `origQty … differs from ours`, 不含「满页或查询失败」 | 旧文案 ⇒ 红 | |
| ↳ **T9(2)** | 真 12Z 全日: **截至 12:47:37Z trip 的账本**(12Z 读回在, 梯子读回/行不在)⇒ 5b **CLEAN** n0 @12Z, §4-7 CLEAN, 未 trip, 无 blind, history 0; **现状**(12:50:01Z 梯子读回=最新锚, 255 protective_flatten 行)⇒ 5b CLEAN, history 0 | 旧码: 截至 trip ⇒ **ANOMALOUS 2 + DRIFT, tripped**; 现状 ⇒ CLEAN 但 history 2 | |
| `live/tests_unknown_size_local_response.py` T8.0–T8.H | **38/38** | **1/38 rc=1**(对 a211ea8: 无开关/无分区; 唯 T8.A2 开关关=全书阶梯两版同) | `w6_tests_unknown_size_local_response_new.log`, `w6_oldcode_red_c.log` |
| ↳ 夹具与数字 | **(1) 之后 (c) 的对象** = 真行把持久化串的场所数改成 ours×1.001(场所要得更多, (1) 不重推, 而场所记录自洽); T8.0 另钉原样真行经 (1) ⇒ 0 异常。2 名 Σ\|intended\| 1524.32 USDT = 0.647% of 235,497.44 ⇒ 合格; 开关 True(默认)⇒ 不 trip, 停开仓, 复核两名(0=0 无单), ALARM HIGH, §4-7 False; 开关 False(选项 C)⇒ trip 全书阶梯(持仓 mock 三名皆平); 6 名 / 3.2% / 读回 20,000 张(10.5U)未解释 / 子成交缺 / 另类异常 / 无 anchors 行 / 并存 §4-5a ⇒ 全书; 5,000 张=2.6U 尘埃内仍自洽; 复核发现 MEME 持 100,000 张(52.5U)⇒ 只平 MEME(sell 100000 RO), 写 1 行+读回, OTHERUSDT 不动 | | |
| `tests_position_break_blindspot` | 重述后绿 | 电池 #2(开关关的 f3ff7b3)上唯一非环境红 = 该钉 | `w6_battery_20260912T135619Z_c.log` |

### 4.3 电池(克隆; 无 .env / 无 state/live 按规则)
- **#1 @43a93bb (a)+(b)**: `w6_battery_20260912T133946Z.log` **126/133**; 7 红全环境: `tests_env_loading`(无 .env), `tests_unseal_rehearsal_halt`(56/57, 唯一红「fidelity vs the real LIVE tree」自报 NOT OBSERVABLE), `tests_reject_topup` / `tests_disposition_matrix` / `tests_alarm_digest` / `tests_daily_summary` / `tests_break_split_wiring`(读真账本/告警史)— 五套在 918559f 同环境逐格同红(`w6_battery_red_suites_on_918559f.log`, 每套 `identical FAIL set: YES`)。
- **#2 @4395dd8 ((c) 开关关, 裁定前)**: `w6_battery_20260912T135619Z_c.log` 126/134; 上述 7 + `tests_position_break_blindspot`(旧钉, 已按裁定重述)。
- **#3 @6013ea6 最终链**: <<BATTERY3_PENDING>>

### 4.4 sha256 → `docs/receipts/w6_sha256_changed_files.txt`(@6013ea6, 25 文件 + 10 基线@918559f)。

### 4.5 恢复路径报告((2), 只读; **未在运行树跑脚本**)
`ops/resume_from_trip.sh` 检查: ①`LIVE_MODE`(默认 DRY_RUN ⇒ 必须 `LIVE_MODE=LIVE`), 所问模式未 trip 而他模式 trip ⇒ 拒; ②`_seeded_by_rehearsal` 标记 ⇒ 路由到 unseed 工具(本 trip 无); ③**硬门**: 复制整棵 pilot_log(43 日)→ `WI.collect`(含公网探针 = 网络)+ `WD.run(MockBroker)` ⇒ `conditions_blind` 非空 或 `tripped` ⇒ 拒(`partial` 不查); `--check` 到此止; ④真跑: 隔离 state.json → 删 → 隔离+删 `harvest_ema.json` → 验无 halt/reduce-only 状态。
复现(无探针, `venue_events=[]`, 43 日真树副本, `w6_resume_gate_replica_{new,old}.log`): **现状**(最新对账锚 = 12:50:01Z 梯子读回)⇒ 新码 blind [] / tripped False / 5b CLEAN / §4-7 CLEAN / partial [cond2_day_loss, cond4_drawdown]; **旧码亦同**(history 17 vs 新 15)— 即**今天的硬门两版都过, 阻门的不是 5b/§4-7**; 截至 trip 的视图: 旧码 ANOMALOUS 2 + DRIFT tripped, 新码 CLEAN(截断跨日删了早前梯子行 ⇒ history 1352/1354 为截断伪影, 状态门只读最新锚)。**其他可能阻门**: (i) 探针时公网不通 ⇒ §4-5a outage ⇒ 拒(瞬时); (ii) `LIVE_MODE` 未设; (iii) 复位后首锚若再遇「全退出 + mark≠mid」, 旧码复发 ⇒ **先部署再恢复**; (iv) `set_reduce_only` 是**本地状态位**(`binance_broker.py` L1840 docstring: 场所端 reduce-only 是 key/账户设置, futures API 不可切换, 由 submit() 本地强制; `enforced: local`)— 恢复脚本删 state.json 即清; 若操作员当时曾**手动**切了场所端 key 设置, 需手动翻回(脚本不查, 本文不能证)。
两条补单腿 `skipped_unknown_fill` 的原因: maker 因身份门 UNKNOWN ⇒ `_amount_unreadable` ⇒ `unknown` 集 ⇒ topup 对未知名写 `skipped_unknown_fill`(不能从假 0 补单); 新码 T7: MEME 残差 −0.058U ⇒ `skipped_min_notional`(未发), POPCAT 残差恰 0 ⇒ `filled` 无补单腿 — 即按截量已知量定尺, 残差≈0 ⇒ 无补单。

### 4.6 首锚验收条目(§2「落地」)
全退出名 `qty_source=venue_position_qty` 且回执 origQty == 我方 qty(`clamped` 记录数预期 0, (a) 退居纵深); 四类标记 0; `execution_of_unknown_size` 0; 阶段 B 告警若有 UNKNOWN 名须带「逐名原因」; 5b 明细 `local_response{switch: true}`。

### 4.7 未能验证 / 边界
1. 真 allOrders 记录未入账本: T7 终态记录由真回执身份字段 + 真子成交 Σ 重建。
2. 「场所对超量 reduceOnly 单一律截量而非拒绝」: 09-12 两名观测 + 文档化, 假设一般; 未在 testnet/真场所复演。
3. (1) 的重推依赖持久化串的格式(`origQty <v> differs from ours <q>`, 身份门原文); 格式变 ⇒ 不重推(失败关向矛盾), 记录在案。
4. (c) `tripped_at` 复用: 局部响应写 `tripped_at` 借 anchor_loop 0b 续停开仓; 其他读 state.json 的工具(resume 脚本硬门以 `tripped`/blind 判, kind 无关; `verify_reshape_anchor` / `unseed_rehearsal_halt` 路由 / `tests_halt_verdict_states`)对 `kind=local_response` 的解释**未审**; 默认已开 ⇒ **部署前审**。
5. (c) 复核用 MockBroker; 真 `flatten_all` 对差额张数的分块/取整未在此链跑; 2%/5 名政策数, 看数前冻结。
6. `_req_qty` 只在请求行带 `qty_venue` 时生效; 两来源皆缺 ⇒ 带宽比真容量宽 0.015%。
7. 电池三轮均在克隆; 运行树全绿由部署时 `run_acceptance` 实测, 本文不替。
8. `tests_reduce_only_clamp.py` 文件头 docstring 列 T1–T7, 未追加 T7-persisted/T3-alarm/T9 条目(格自述, 见 §4.2); 修 docstring 会改 a211ea8 sha, 未做。
9. 恢复复现无公网探针(`WI.collect` 含 `public_path_alive()`), 用 `venue_events=[]` 替。
