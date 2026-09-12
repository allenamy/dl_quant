> **创建:** 2026-09-12 13:2xZ | **Session:** https://claude.ai/code/session_01BzpuBRGZh8oPvpD8NgqsME | **状态:** §1–3 事实表+方案 → **§4 RESULT: (a)(b)+(1)(2)(3)(6) = `fe97e46`, (c) 默认关 + C1/C2/C3 = `3308cbc` (独立复核 563e3470 后), 克隆分支 fix/e0912a-reduce-only-clamp; 未部署; 部署与恢复 = 用户字** | **作废条件:** W6 落地后转收据; 或用户裁定回滚 d040c74

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

## §4 RESULT(W6, 2026-09-12 13:3x–15:xxZ; 克隆 `/Users/haosiyu/cc_tmp/exec_w6`, 分支 `fix/e0912a-reduce-only-clamp`; **未部署, 未 push, 无网络**; 运行树 `~/dl_quant_live` 与生产者只读)
**裁定与复核的时间线**: ① 用户字 13:19Z(lead 转述「肯定是彻底修复, 回滚的版本有其他问题」): 彻底修复, 不回滚 d040c74; 当时指令 (c) 默认开。② lead 12Z 深查追加 (1)(2)(3)。③ **独立复核 563e3470**(`…/codex_batch_incident_review_2026-09-12/incident/RESULT.md`, 探针复跑 exit 0 → `docs/receipts/w6_review_probe_rerun.log`): **接受 (a)(b) 为根因修复; 以新 P1 阻止 (c) 默认开**(C1/C2/C3); lead 据此指令: **(c) 默认 = False**, (c) 仍作独立提交与受测选项; 追加 4–7。本节记录的是③之后的终态; 13:19Z 的字如实记录于此, 未被改写。
**提交链**(克隆内, 两个内容提交): `918559f` → `43a93bb` (a)+(b) → **`fe97e46`** = (a)(b) + (1)(2)(3)(6) + (4)(7) → **`3308cbc`** = (c) 默认关 + C1/C2/C3。收据: `docs/receipts/w6_reduce_only_clamp_ab.diff`(= `git diff 918559f fe97e46`, 24 文件, 含 4.3MB 真 12Z 全日夹具), `w6_proportional_response_c.diff`(= `git diff fe97e46 3308cbc`, 7 文件 +859/−6)。部署动词(用户字, 非锚窗): `git -C ~/dl_quant_live fetch /Users/haosiyu/cc_tmp/exec_w6 fix/e0912a-reduce-only-clamp && git -C ~/dl_quant_live merge --ff-only 3308cbc`(取 `fe97e46` = 不含 (c) 代码; 两者行为在开关关时相同, 差别只在 (c) 代码与其记录字段)→ 运行树 `run_acceptance` 实测 → 首锚验收(§4.6)→ 恢复(§4.5)。

### 4.1 改了什么(file:line @ 3308cbc; 事实 F# 见 §1)
| 环 | 位置 | 改动 |
|---|---|---|
| (a) 一条规则 | `live/binance_broker.py` `_record_says_reduce_only`, **`reduce_only_clamp()`** | 第四态 clamped 唯一裁定: 我方 reduce_only ∧ 记录 reduceOnly true ∧ origQty 有限 ∧ 0<Qv<Qs 超出 1e-6 ⇒ `{ours: Qs, venue: Qv, why}`; 其余(Qv>Qs / 记录未标 / 我方非 RO / 0·缺·畸形)⇒ None ⇒ 原 1e-6 比较, 仍矛盾 |
| (a) 三道门 + 直接读者 | `binance_broker.py` `_ident_check(…, reduce_only, clamp_out)`, `submit_identity_mismatch`, `requery_identity_mismatch`, `last_fill_details` | 命中 ⇒ None + `clamp_out`; `out["clamped"]`, `orig_qty`=回执 Qv, 不置 `inconsistent`; 方向门在前不动 |
| (a) 结算门(**真事故路径**) | `live/venue_fills.py` `_valid`, `_valid_present`, `_merged`, `_clamp_of` | 同一规则; canon.origQty=Qv + `clamped` 流入 details。只修 broker 不修此处 ⇒ 下一道门以「record origQty differs」复发(T7 逐链验) |
| (a) 容量 | `live/binance_executor.py` **`_req_qty()`**(qty_venue=Qv 否则 qty=Qs)→ `_final_known`/`request_remaining`/`ledger_totals`/`ledger_inconsistencies`/子成交闭合两处; `_clamp_cols`; `submit_maker` 记 `venue_clamped`; `apply_fill_details`; 请求行 `clamped`+`qty_venue` | executedQty/子成交以 Qv 为界; `qty` 仍=Qs |
| (b) 数量源 + 接线 | `binance_executor.py` `plan(…, held_qty=None)`; `_order_row` 带 `qty_source`; `scheduler/anchor_loop.py` `self._held_qty`(同一 `account_snapshot`.positions_contracts, 仅本锚), `plan(..., held_qty=…)` | 全退出 = `round_qty(−held)`, `qty_source=venue_position_qty`; 无张数/符号不合 ⇒ 旧路径 + `notional_over_mid` + note |
| **(1) 持久化矛盾重推** | `live/reconcile.py` `_is_identity_origqty_kind`, `_ORIGQTY_PAIR`, **`_clamp_rederived(r, why)`**, **`_rederive_ledger(o)`**, `_exec_qty` 首段 | 不信旗标: 请求级 `inconsistent` 为身份门 origQty 值比较 且 串内两数 0<Qv<Qs ∧ |C| ≤ Qv ≤ |Qs|(Qs==该请求 qty)∧ Σtrade_qty==|C| ∧ 同侧 ⇒ 已知量=C; 其他一切仍 unquantifiable, why 带首条仍立矛盾。**读时重推, 不改账本** |
| **(2) 只读重判收据工具** | **`ops/rejudge_ledger_rows.py --check`**(新) | 逐行按原始证据重判: `events.jsonl` POST 回执(Qv/reduceOnly/side/orderId)、当日 fills 的 trade_id 与请求 trade_qty 键、前后读回; 六项交叉核对; 看门狗在**副本**上的 5b/§4-7 推导写入收据; 列出 `resume_from_trip.sh` 仍会查的步骤; 不改账本不清旗标不碰 state/watchdog。真树只读收据: `docs/receipts/w6_rejudge_20260912_receipt.json`(2 行重判 known, 2/2 交叉核对全真, 副本 5b CLEAN / §4-7 CLEAN) |
| **(3) 告警文案** | `scheduler/anchor_loop.py` `complete_anchor` | 「(满页或查询失败: …)」→「— 逐名原因: SYM: <结算报告 why 或 fold inconsistent 前 120 字>」; 无原因者标明 |
| **(6) 保护性平仓成交/费用** | `venue_fills.order_legs_from_venue(client_ids=, leg=)`, `attribute_trades`(protective_flatten 桶), `fill_rows_from_trades`; `ops/backfill_fills.py` `find_gaps`(kind/client_ids/n_order_rows_fee_unmeasured)+ flatten 批精确联接 | 255 行 fee_paid None / 0 fills 行的根因: 平仓 client id 为 `F<utc>-SYM-n`, 无 `<rid>-` 前缀 ⇒ B26b 回填重建不出腿。现按批次自家 client_id 精确联接; 测得佣金落 fills 行; 订单行不改写(append-only)。**LIVE 实跑未做**(`LIVE_MODE=LIVE python3 ops/backfill_fills.py --day 20260912 [--apply]`, 需凭据 = 操作员步骤); 梯子路径本身未加网络调用 |
| (4) 命名 | broker / venue_fills / executor 注释 | Qs(所发)/Qv(场所接受 origQty)/L(下界)/F(已证最终); Qv 两次等于持仓是观察不是定义 |
| (7) 合成标注 | `tests_reduce_only_clamp.py` `_terminal_record` | T7 的 allOrders 终态记录标 SYNTHETIC(POST + 真子成交重建, 非保存原文) |
| (c) 判据(政策) | `live/reconcile.py` 常量 2%/5 名, **`_is_evidenced_clamp_kind`**, `_venue_consistency`(C1), `_gross_ref`(有限), `unknown_size_local_eligibility`, D2 行 `venue_consistent`+`intended_usdt`, 返回 `unknown_size_local` + `latest_if_local_response` | **C1**: 任一请求 `inconsistent` / 行级 `ledger_inconsistent` 非「有凭据 clamp 种类」(origQty 文本 ∧ 同侧 ∧ |C|≤|Q| ∧ Σ子成交==|C|)⇒ 不自洽; row.known 必须 == Σ 有符号 C; gross 有限且 >0(+Inf/NaN ⇒ 不合格); **C3**: 2%/5 名 = 事故后政策阈值(0.65%/2 名/245U 已知), 非「看数前冻结」 |
| (c) 开关+响应 | `live/watchdog.py` **`UNKNOWN_SIZE_LOCAL_RESPONSE = False`**, evaluate 分区/`LOCAL`/`local_responses`, `_local_response()`(C2), `run()` `elif` | 开关开且合格 ⇒ 出触发表; 停开仓 → 仅复核这些名: **C2** 只对与持仓同号的未解释部分按 sign(held)×min(|diff|,|held|) 发 reduce-only(持仓少于账本解释 ⇒ `not_handled` 记录, 不下买单), 写 protective_flatten 行+读回 → ALARM.log HIGH(含 not_handled 名数); 不平其他名, 不设账户 reduce-only 键; state.json `kind=local_response` 带 `tripped_at`; trip 优先 |
| (c) §4-7 同判据 | `live/watchdog_inputs.py` | 同一开关读 `latest_if_local_response`; 行加 `drift_local_response` |
| (c) 旧钉重述 | `live/tests_position_break_blindspot.py` L231 | 「无 execution_of_unknown_size 豁免」(源码字符串缺席)→「唯一豁免 = reconcile 分区 + 具名开关, **默认关**, 政策 2%/5」; 守卫未删 |
| 注册 | `run_acceptance.sh`; `ops/gate_coverage.py` SUITE_SCOPE | 三新套件 + 盲区自述 |

### 4.2 测试(先红后绿; 旧码 = 同一文件跑在干净 worktree)
| 套件 | 新码 | 旧码 | 收据 |
|---|---|---|---|
| `live/tests_reduce_only_clamp.py` T1–T7 + T7-ctl + T7-persisted(12) + T3-alarm + T9a/b + **T10**(重判收据工具 5 格) | **75/75** | 918559f `/Users/haosiyu/cc_tmp/exec_w6_old`: **32/70 后 Traceback rc=1**(T1/T5/T6/T7/T7-persisted/T3-alarm/T9 红; 至 T10 `ModuleNotFoundError: rejudge_ledger_rows` — 旧树无此工具, 即红) | `w6_tests_reduce_only_clamp_new.log`, `w6_oldcode_red.log` |
| ↳ T7 端到端 | 真链 `plan→submit_maker→complete_anchor`(FakeNet: POST=真回执逐字, DELETE=-2011, allOrders=**SYNTHETIC** 终态记录(POST+真子成交重建), userTrades=真子成交)→ `reconcile` vs 真 08Z/12Z 读回: 0 异常, 两名 residual 0, 请求行 `qty −1933986`(Qs)+`qty_venue −1933692`(Qv)+`clamped`; MEME 残差 −0.058U ⇒ `partial_expired`+补单 `skipped_min_notional`; POPCAT 残差恰 0 ⇒ `filled` 无补单行 | 旧码同链 2×execution_of_unknown_size | |
| ↳ T7-persisted(1) | 真持久 12Z 行(旧旗标+串)经新 `reconcile` ⇒ 0 异常, 两名 known; 11 反例(子成交缺 / \|C\|>\|Q\| / more-than-requested / side / malformed / 反侧 / qty_venue 低于 C / 无账本 / **串内 Qv 高于 Qs** / 串 Qs≠请求 qty / 串无两数)全 unquantifiable | 旧码 2 异常 | |
| ↳ T7-ctl | origQty=ours×1.001 ⇒ 两版仍 2 异常。发现: +1 张在 MEME 1.93M 上 = 0.5e-6 落在既有 1e-6 容差内(两版同, 未动) | | |
| ↳ T3-alarm(3) | 突变链告警含「逐名原因」+ 两名 + `origQty … differs from ours`, 不含旧文案 | 旧文案 ⇒ 红 | |
| ↳ T9(2) | 真 12Z 全日: **截至 12:47:37Z trip**(12Z 读回在, 梯子读回/行不在)⇒ 5b **CLEAN** n0 @12Z, §4-7 CLEAN, 未 trip, 无 blind, history 0; **现状**(12:50:01Z 梯子读回=最新锚)⇒ 5b CLEAN, history 0 | 旧码: 截至 trip ⇒ **ANOMALOUS 2 + DRIFT tripped**; 现状 ⇒ CLEAN, history 2 | |
| ↳ T10(2) | `rejudge_day` 夹具+POST 证据: 2 行 known, 交叉核对 2/2 全真(串 Qv==POST origQty, POST reduceOnly ∧ 我方 RO, Qv<Qs, 子成交全在当日 fills, Σ子成交==C, 读回后==前+C), 副本 5b/§4-7 CLEAN, 夹具文件 mtime 不变; 无 POST 证据 ⇒ 交叉核对 0 真(缺证≠过); POST origQty 改 1933000 ⇒ 该名交叉核对假 | 旧树无模块 | |
| `live/tests_flatten_fee_backfill.py` [A]–[E](6) | **13/13** | 918559f: **4/11 后 Traceback rc=1**(`KeyError: 'protective_flatten'` — 旧 attribute_trades 无该腿桶) | `w6_tests_flatten_fee_backfill_new.log`, `w6_oldcode_red_backfill.log` |
| ↳ 数字 | 真日: FLATTEN 批 255 执行 / 255 缺 fills / 255 client_id / 255 行费未测; 合成 3 名 4 子成交: 报告 3 腿 4 行 1 外来未归属 不写; apply 写 4 fills 行(protective_flatten, 真 trade_id, 逐笔佣金 0.20/0.5/0.7); 再 apply 0 行; 外来 id ⇒ 0 腿 警告 不写; 常规批前缀路径与 maker/topup 桶不变 | | |
| `live/tests_unknown_size_local_response.py` T8.0–T8.R–T8.H | **50/50** | fe97e46(无 (c)) `/Users/haosiyu/cc_tmp/exec_w6_a`: **1/40 后 Traceback rc=1**(`AttributeError: reconcile._is_evidenced_clamp_kind`) | `w6_tests_unknown_size_local_response_new.log`, `w6_oldcode_red_c.log` |
| ↳ 夹具与数字 | (1) 之后 (c) 的对象 = 真行把持久化串的场所数改成 ours×1.001((1) 不重推而场所记录自洽); T8.0 钉原样真行经 (1) ⇒ 0 异常, **开关默认 False**; 2 名 1524.32 USDT = 0.647% of 235,497.44 ⇒ 合格; 开关 False ⇒ trip 全书阶梯; 开关 True ⇒ 停开仓+复核+HIGH, §4-7 False; 6 名 / 3.2% / 读回 20,000 张未解释 / 子成交缺 / 另类异常 / 无 anchors 行 / 并存 §4-5a ⇒ 全书; **T8.R(复核格)**: Q10/C4+外来 orderId 矛盾 ⇒ 不自洽不合格(复核前: 合格); known 9≠ΣC 4 ⇒ 不自洽(复核前: 自洽), known 4 对照自洽; gross +Inf/NaN ⇒ 不合格(复核前: 比例 0 接受); C2: 多头 1000/期望 5000 ⇒ not_handled 无单(复核前: BUY reduceOnly); 5000/1000 ⇒ sell 4000; 空头 −3000/−1000 ⇒ buy 2000; −3000/−9000 ⇒ not_handled; 50/0 ⇒ sell 50 | | |
| `tests_position_break_blindspot` | 重述后绿 | 电池 #2(开关关的 f3ff7b3)上唯一非环境红 = 该钉 | `w6_battery_20260912T135619Z_c.log` |

### 4.3 电池(全部克隆, 无 .env 按规则; 关键差异 = **有无复制运行树 `state/live` 账本**)
W1/W2/E1 的克隆把运行树 `state/live`(43 日账本)整棵复制进克隆, 本克隆最初没有 — 五套读账本的套件(`glob(state/live/pilot_log/*/orders.jsonl)`)因此红。两类环境都留有收据:
- 无账本: #1 `w6_battery_20260912T133946Z.log` @43a93bb 126/133; #2 `…T135619Z_c.log` @4395dd8 126/134(+ blindspot 旧钉); #3 `…T141746Z_final.log` @6013ea6; 七红在 918559f 同环境逐格同红(`w6_battery_red_suites_on_918559f.log`)。
- **有账本(与 W1/W2/E1 同环境; 干净 worktree + rsync `state/live`)**: **#5 对照 = 918559f** `w6_battery_20260912T142241Z_918559f_ledger.log`: 4 红 = `tests_env_loading`, `tests_disposition_matrix`, `tests_alarm_digest`, `tests_break_split_wiring`; #4 = 6013ea6(复核前 (c) 默认开)`…T142237Z_final_ledger.log`: 3 红(前三); **#6 = 13e44f2(复核后第一版)** `…T144605Z_final2_ledger.log`: **5 红** = 前三 + **`tests_state_root`, `tests_rehearsal_anchor` — 我方回归**, 均由新工具 `ops/rejudge_ledger_rows.py` 引起: (i) state_root 扫 ops/ 的逐模式路径字面量, 工具 docstring/收据文案含 `state/watchdog` 字样 ⇒ 改措辞(不含字面路径); (ii) rehearsal_anchor 要求每个引用 `rebalance_id` 的文件登记为计数点或豁免 ⇒ 登记豁免(只读 receipt, 不铸不计不写)。两处修后本地绿(→ fe97e46/3308cbc); **#7 = 3308cbc 终链** `w6_battery_*_final3_ledger.log`: **3 红 = `tests_env_loading`, `tests_disposition_matrix`, `tests_alarm_digest`(`w6_battery_20260912T155231Z_final3_ledger.log`; 132/135 绿)— 与干净 918559f 对照逐字同红(`w6_red_suites_ledger_compare.log`, 每套 `FAIL lines identical: True`); 对照多出的 `tests_break_split_wiring` 红在本链为绿(第 4 条)。两处我方回归已消。
- **逐套红证明**(有账本, 终链 vs 干净 918559f; per-suite 日志 `docs/receipts/w6_per_suite_logs/{pristine_918559f_ledger,final_3308cbc_ledger}/<suite>.log`; 比对 `w6_red_suites_ledger_compare.log`):
  1. `tests_env_loading` — 格:「ops/ic_monitor.py / redeliver_alarms.py / unseed_rehearsal_halt.py / scheduler/run_anchor.py populates TELEGRAM_* on import」(10/14)。因: 克隆无 `.env`(lead 规则)。两树逐字同红 ⇒ 环境。
  2. `tests_disposition_matrix` — 格:「EVERY steady trading anchor's INVOLUNTARY gap is small …」与「halted/trading SEPARATION … max steady traded involuntary **1524** vs min halted 4169」。因: **今日账本事实** — 12Z 锚 MEME+POPCAT 两行 `filled_amount_unknown` 合计 1,524 USDT 被尺子计为稳态交易锚的非自愿缺口, 超出该套件的界(该尺子读 terminal_reason, 与 (1) 的读时重推无关; 09-12 07:xxZ 该套件在真账本 48/48 时尚无此锚)。两树逐字同红 ⇒ 账本事实, 非本改动; 修尺子是另一件事(不在本范围)。
  3. `tests_alarm_digest` — 格:「last-24h push discipline — only 0 readable alarms in 24h — NOT OBSERVABLE, not a pass」。因: 该套件读近 24h 告警审计, 复制的 `state/live` 下不含可读的近 24h 记录(套件自报 NOT OBSERVABLE)。两树逐字同红 ⇒ 环境。
  4. `tests_break_split_wiring` — **仅干净 918559f 红**: 格:「on a healthy tree `split_alarm` returns None…」(`WD.split_alarm(WD.evaluate(LIVE, …))`)。机制(两树同一账本副本上实测): §4-5e 的 `latest` 锚 = 12Z 换仓锚 1789215841.9(梯子读回不是换仓锚); 旧码分解得 `n_unauth_unmeasurable 2`(MEME/POPCAT unknown-size 行)⇒ `unmeasurable_alarm True` ⇒ 页面「UNAUTH_UNMEASURABLE on 2 name(s)」⇒ 非 None ⇒ 红; 新码 (1) 读时重推 ⇒ `n_unauth_unmeasurable 0` ⇒ None ⇒ 绿。不是抖动: **本修复把一条账本事实红修绿**, 是 (1) 的直接效果。
  W1/W2 当时「只有一红」而干净 918559f 今有四红: 差别是今日账本(trip/flatten/两行 unknown)与 24h 告警窗, 不是代码。

### 4.4 sha256 → `docs/receipts/w6_sha256_changed_files.txt`(@3308cbc, 变更文件 + 全日夹具拼接哈希 + 918559f 基线)。

### 4.5 恢复路径报告((2), 只读; **未在运行树跑脚本**)
`ops/resume_from_trip.sh`: ① `LIVE_MODE`(默认 DRY_RUN ⇒ 必 `LIVE_MODE=LIVE`), 所问模式未 trip 而他模式 trip ⇒ 拒; ② `_seeded_by_rehearsal` ⇒ 路由 unseed 工具(本 trip 无); ③ **硬门**: 复制整棵 pilot_log(43 日)→ `WI.collect`(含公网探针=网络)+ `WD.run(MockBroker)` ⇒ `conditions_blind` 非空 或 `tripped` ⇒ 拒(`partial` 不查); `--check` 到此止; ④ 真跑: 隔离 state.json → 删 → 隔离+删 `harvest_ema.json` → 验无 halt/reduce-only 状态。
复现(无探针, 43 日真树副本, `w6_resume_gate_replica_{new,old}.log`; 真日只读重判收据 `w6_rejudge_20260912_receipt.json`): **现状**(最新对账锚 = 12:50:01Z 梯子读回)⇒ 新码 blind [] / tripped False / 5b CLEAN / §4-7 CLEAN / partial [cond2_day_loss, cond4_drawdown]; **旧码亦同**(history 17 vs 新 15)— 今天的硬门两版都过, 阻门的不是 5b/§4-7; 截至 trip 的视图: 旧码 ANOMALOUS 2 + DRIFT tripped, 新码 CLEAN(跨日截断删了早前梯子行 ⇒ history 1352/1354 为截断伪影)。**其他可能阻门**: (i) 探针时公网不通 ⇒ §4-5a outage ⇒ 拒(瞬时); (ii) `LIVE_MODE` 未设; (iii) 复位后首锚若再遇「全退出 + mark≠mid」, 旧码复发 ⇒ **先部署再恢复**; (iv) `set_reduce_only` 是本地状态位(`binance_broker.py` docstring: 场所端 key 设置 futures API 不可切, submit() 本地强制)— 恢复脚本删 state.json 即清; 若操作员当时手动切了场所端 key, 需手动翻回(脚本不查)。
两条补单腿 `skipped_unknown_fill`: maker 因身份门 UNKNOWN ⇒ `_amount_unreadable` ⇒ topup 对未知名不能从假 0 补单; 新码 T7: MEME 残差 −0.058U ⇒ `skipped_min_notional`, POPCAT 残差恰 0 ⇒ 无补单腿 — 按截量已知量定尺, 残差≈0 ⇒ 无补单。

### 4.6 首锚验收条目
全退出名 `qty_source=venue_position_qty` 且回执 origQty == 我方 qty(`clamped` 记录数预期 0); 四类标记 0; `execution_of_unknown_size` 0; 阶段 B 告警若有 UNKNOWN 名须带「逐名原因」; 5b 明细 `local_response{switch: false}`。之后(操作员, 需凭据): `LIVE_MODE=LIVE python3 ops/backfill_fills.py --day 20260912`(先报告后 `--apply`)补 255 笔平仓的 fills 行与佣金。

### 4.7 未能验证 / 边界
1. 真 allOrders 记录未入账本: T7 终态记录为 SYNTHETIC(POST + 真子成交重建), 形状是我方的。
2. 「场所对超量 reduceOnly 单一律截量而非拒绝」: 两名观测 + 文档化(复核 §4 指出官方文档未证一般性), 假设一般; 未在 testnet/真场所复演。
3. (1) 依赖持久化串格式(`origQty <Qv> differs from ours <Qs>`); 格式变 ⇒ 不重推(失败关向矛盾)。(2) 的收据工具以 POST 回执独立交叉核对, 与串无关。
4. (c) 默认关; `tripped_at` 复用与 `kind=local_response` 对其他 state.json 读者的影响未审; C1 之后 (c) 的合格集只剩「非 clamp 种类但场所记录自洽」的窄形(T8 夹具即此形), 复核 C2 所列「多行同名/跨锚未决/残留挂单」等联合事实未实现(Q6)— 若日后要开, 需新裁定 + 上述项。
5. (c) 复核用 MockBroker; 真 `flatten_all` 分块/取整未在此链跑。
6. (6) 只做了回填运行器与测试; **LIVE 实跑未做**(需凭据); 梯子路径未加实时费用查询; 订单行 fee_paid 仍 None(append-only), 汇总费用的读者若只读订单行仍会低估平仓成本。
7. 电池六轮均在克隆; 运行树全绿由部署时 `run_acceptance` 实测。有账本电池的三红(env/disposition_matrix/alarm_digest)在部署后的运行树上预期同样存在(前者需 .env 即绿; 后两者为账本事实/24h 窗), 非本改动引入。
8. 三个旧码收据以 Traceback 结尾(旧树缺模块/属性/桶), 即红; 未再为旧码防崩。
9. 恢复复现无公网探针(`WI.collect` 含 `public_path_alive()`), 用 `venue_events=[]` 替。
10. 复核 §4 对新正控目录(V1/F3/F8 过度概括、V8 终态 [L,Q]、V11 STP、V9 身份混合)的批评针对 HANDOFF 目录, 不在本节改; 本节代码不主张 V1/F3 的一般性(见 2)。
