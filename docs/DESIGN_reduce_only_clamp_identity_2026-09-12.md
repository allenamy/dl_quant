> **创建:** 2026-09-12 13:2xZ | **更新:** 2026-09-13 00:3xZ(W8 §5)· 01:5xZ(W8 §6)· 03:xxZ(W8 §6.6–6.7 + lead 裁定入 §5.5) | **Session:** https://claude.ai/code/session_01BzpuBRGZh8oPvpD8NgqsME | **状态:** §1–3 事实表+方案 → **§4 RESULT: (a)(b)+(1)(2)(3)(6), (c) 默认关 + C1/C2/C3** → **§5 尺子第七次重标定(lead 已接受, 研究仓 4442f6d5)** → **§6 C4–C8 收紧(独立研究员 0158f5d1 §3.A: C 是累计下界, F 才是量)+ §6.6 `[G7]`#2 改到 C/F 合同 + §6.7 全历史平仓费用回填提案(待裁定, 未执行)。当前链: (a)(b) = `5feea3e`(= `bea37cf` C4–C8 + `[G7]`#2 合同), (c) = `595de41` (= 原 (c) cherry-pick 到其上, 内容逐字未变); 分支 `fix/e0912a-reduce-only-clamp` → `595de41`; 备份分支 `w8-backup-pre-recal7` = `3308cbc`, `w8-backup-pre-c4fix` = `8e8510c`。§4/§5/§6.1–6.5 正文里的 sha 都是当时的头, 保留不改写; **部署动词请用 §6.8 的 sha**。未部署; 部署、恢复与回填 = 用户字** | **作废条件:** 落地后转收据; 或用户裁定回滚 d040c74

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

## §5 尺子第七次重标定(W8, 2026-09-13; **测试文件 only, 零运行时改动**)

> 起因: 在 `fe97e46` / `3308cbc` 上把运行树 `state/` 整棵复制进克隆后, `live/tests_disposition_matrix.py`
> 两格真账本断言红 —— 不是代码退化, 是**账本长出了三种断言外的新形态**(§4.3 第 2 条已预告「修尺子是另一件事」)。
> 红挡住 `safe_commit` 的电池全绿门, 所以必须按事实重标。**方法与第六次同**: 拆开事实 → 独立成类 →
> 断言关系 → 再加一条「新尺在真账本上承重」的证明。**放宽阈值 / 删断言 / 把锚移出人口, 一次都没有。**

### 5.1 事实表(全部第一手; 账本快照 2026-09-13T00:04:34Z 复制自 `~/dl_quant_live/state`, 44 日 / 76,101 orders 行 / 253 anchors 行)

| # | 事实 | 在哪测的 | 后果 | 新类 | 断言 |
|---|---|---|---|---|---|
| F1 | 12Z 锚 **A1789215839**(anchor_ts 1789215841.923763)的非自愿缺口 = **1,524.3211 USDT**, 逐 USDT 等于两行 `filled_amount_unknown` 的意图和(MEME 1,015.24631076 + POPCAT 509.07486 = **1,524.3212**) | `state/live/pilot_log/20260912/orders.jsonl`; `OD.gaps` 同一残差算术(`filled_notional` 未写 ⇒ 残差 = intended) | 稳态 200U 尺红 + halted/trading 分离尺红(两格) | — | — |
| F2 | 这两笔在**场所记录里完全可知**: 回执 origQty == `confirmed_qty`(MEME −1,933,692 / POPCAT −10,434), Σ 子成交 `trade_qty` == \|confirmed_qty\| **逐张相等**(560266+782806+590620 / 8433+2001), Σ `trade_quote` = 1,015.1883 / 509.07486, 本锚读回 0 | 行内 `request_ledger`(第一手); 只读重判收据 `docs/receipts/w6_rejudge_20260912_receipt.json`(2 行 known, 6 项交叉核对 2/2 全真) | 「未知」是**我方身份门 1e-6 容差的读数错误**(E-0912-A ④), 不是事实 ⇒ 按事实重判量 | **① 重判 KNOWN** | `_clamp_known` 六道门 |
| F3 | 重判后残差: MEME **−0.05801076**, POPCAT **恰 0** ⇒ 该锚非自愿缺口 **0.058 USDT** | 测试运行时从 `request_ledger` 重算(不写死) | 回到 200U 线内, 阈值未动 | ① | `[G7]` 第 1 格(双向) |
| F4 | 全账本 `filled_amount_unknown` **只有这 2 行**; 带 `ledger_inconsistent` 的只有这 2 行; 含 "differs from ours" 的只有这 2 行 | 44 日 76,101 行全扫 | 类今天只有 1 个成员 —— 所以按**结构**选(串 + 请求账本内容), 不按名字/计数 | ① | 反控六条 |
| F5 | 本文件独立实现的截量判据与运行时 `reconcile._clamp_rederived` 在**全账本 441 个带请求账本的行**上逐请求一致(2 个 clamped) | 测试运行时对账(`import reconcile`) | 尺子与书对「已知」同义; 两者若分家 ⇒ 红 | ① | `[G7]` 第 2 格 |
| F6 | 12:47:37Z 看门狗阶梯在 **12Z 锚的区间内**平了全书: **255 行** `protective_flatten`, rid `FLATTEN-20260912T124737Z`, Σ\|filled_notional\| = **235,382.55 USDT**, 终态**全 `filled`**, **255/255 行 `fee_paid` 为 None** | orders.jsonl 逐行 | 这批执行不属于任何锚的缺口账本 | **② TRIP-FLATTENED** | `[E]` 三格 |
| F7 | 全账本这样的批次共 **10 个 / 1,708 行 / 738,216.00 USDT / 1,704 行费未测**; 每批 Σ\|filled\| 与其所在锚的 `realized_gross` 相对差 ≤ **0.11%**(全书被平掉, 不是一小片) | 全扫 + `anchors.jsonl` | 类不是一次性形态, 有 10 个成员 | ② | Σ\|filled\| 在所在锚 realized 的 10% 带内 |
| F8 | 这 10 个 rid **不在 `anchors.jsonl` 里**(0/253), 于是既不进 `_halted` 也不进 `_traded` ⇒ **把这 1,708 行整批删掉, `[E]` 读到的每个 `gross_usdt` / `n_named` 一位不变** | 测试运行时重算整个 `[E]` | **盲区**: 73.8 万 USDT 的真实执行, 本文件此前**一条断言都读不到** | ② | `[G7]` 第 5 格(盲区被**实测**, 不是被声明) |
| F9 | 12Z 锚**自己的单确实成交了**(重判后非自愿 0.058) | F3 | ⇒ 该锚**不移出稳态人口**: 把它豁免掉会是放宽, 不是重标定 | ② | `[G7]` 第 1 格末句断言 `_rj_anchors ⊆ _steady_ids` |
| F10 | 停机锚 **16/16** 的真实形态: 终态词汇只有 `blocked_by_halt` / `skipped_min_notional`, `submit_ts` **0 个**, 成交 **0 笔**, 且 Σ\|intended\| **== anchors 行的 `target_gross`**(全部 16 个偏差 < 0.01 USDT) | 全扫 + anchors 行 | 原断言只有「整书缺口 > 1000U」—— 一条交易得很差的锚也能过的绝对界 | **③ HALTED-NO-SUBMIT** | 形态格 + 恒等式格 |
| F11 | 把这 16 个停机锚**当交易锚读**, 非自愿缺口 **4,169 – 235,320 USDT**, 每一个都远超 200U | 测试运行时用同一拆分算术重算 | 停机类是承重的, 不是分类装饰 | ③ | `[G7]` 第 4 格 |
| F12 | 16Z **A1789230240**(245 行 = 243 `blocked_by_halt` + 2 `skipped_min_notional`, target 235,335.37)与 20Z **A1789244640**(target 235,286.47)正是这个形态 —— 今天新增的两个 | orders + anchors | 尺子没把它们读成「巨额非自愿缺口的交易锚」(它们本来就落在 `_halted`, 但此前只被那条绝对界描述) | ③ | 同上, 逐锚点名 |
| F13 | `protective_flatten` 行 **1,704/1,708 `fee_paid` 为 None**(另 4 行是 08-05 那批的真 0.0)。`fee or 0` 的读法会在 235,382.55 USDT 的 IOC taker 执行上打印 **0.00 USDT 成本** | 全扫 | 费用三态纪律(与 `fee_paid` / `filled_notional` 同一条)必须贯到这个类 | ② | `[E]` 费用格(任一行未测 ⇒ 本批 `fee_usdt = None`)+ `[G7]` 第 6 格(夹具: None 与 0.0 分桶) |
| F14 | ★ **费用盲区覆盖全部历史保护性平仓, 不只是 09-12 那 255 行 / 235,383 USDT**(lead 09-13 要求写明): 订单层 **10 批 / 1,708 行 / 738,216.00 USDT / 1,704 行 `fee_paid` 为 None**。按**佣金实际所在的层**再分(`fills` 行才带佣金, 订单行 append-only 永不改写): **(a)** 09-09 `FLATTEN-20260909T164536Z` 243 行 / 232,756.97 USDT —— **fills 层已测**: 3,095 笔唯一成交(账本里各写了两遍: 一遍 `rebuilt_from_venue`, 一遍 `backfilled_utc`, `collapse_supersedes` 后 3,095), 243 名全覆盖, 佣金全在, 币种 **BNB + USDT 混合**(原始合计 116.3785 **不是** USDT 数); **(b)** 09-12 255 行 / 235,382.55 USDT —— 未测, 但**现工具可归属**(255 个 `client_id`); **(c)** 其余 **8 批 / 1,210 行 / 270,076.47 USDT**(08-01 / 08-02 / 08-05×2 / 08-21×2 / 08-26 / 09-06)—— 未测, 且**现工具无法归属**: 09-10(`d73b1b0`)之前的 `flatten_all` 下单**不发 client id**(订单 dict 只有 symbol/side/quantity/reduce_only/tif), 账本行也没有 order id, 而 `order_legs_from_venue` 在 `client_ids` 为空时退回 `FLATTEN-<ts>-` 前缀匹配 ⇒ 0 条腿 ⇒ 工具拒写 | orders + fills 全扫; `find_gaps` 离线纯函数逐日跑(不建 broker); `git show d73b1b0^:live/binance_broker.py` `flatten_all` | 「用凭据跑一遍回填」**关不掉 8/10 批**; 真正可补的只有 09-12; 09-09 已在 fills 层测过 | ② | `[E]` 费用格措辞更正(见 §6.6): 它读**订单层**, 回填后计数**不会下降** —— 原文「回填后 `fee_usdt` 变成数字」**是我写错的** |

### 5.2 改了什么(`live/tests_disposition_matrix.py`, 零运行时文件改动)

| 环 | 位置 | 改动 |
|---|---|---|
| ① 判据 | `_ORIGQTY_PAIR` / `_fin` / `_clamp_known` / `_is_origqty_kind` / `_row_rejudged` | 六道门: 身份门 origQty **值比较**文本 ∧ 串内 0 < Qv < Qs ∧ 串里的 Qs == 该请求自己的 `qty` ∧ 同侧 ∧ \|confirmed\| ≤ min(Qv, \|qty\|) ∧ Σ 子成交 `trade_qty` == \|confirmed\| ∧ 子成交 `trade_quote` 齐全有限。整行判据更严: 行内**每个**请求都要被解释, 行级 `ledger_inconsistent` 每条都要指向已重判的 client_id, 否则整行不重判(**失败一律关向「未知」**) |
| ① 接线 | `_all_rj`(重判副本, 只改 `filled_notional`)/ `_by` 用它 / `_by_raw` + `_split_raw` 保留重判前的同一算术 | 终态字符串不改, 行仍是 GAP 行 —— 变的只是**量**。`[A]` 的闭世界检查读 `terminal_reason`, 不受影响 |
| ② 选取 | `_flat_rows` / `_flat_rids`(`order_type == "protective_flatten"`)→ `_traded` 的排除条件 | 原来只有 `str(r).startswith("FLATTEN")` 一条**按名字**的过滤(E-0825-H)。现按行的结构选, 并断言三个读法(结构 / 名字前缀 / 不在 anchors.jsonl)在全账本重合 |
| ② 事实 | `_containing_anchor` / `_fee_states` / `_flat_batches` / `_flat_facts` | 每批: 行数、是否全成交、Σ\|filled\|、所在锚与其 realized、费用三态 |
| ③ 形态 | `_HALT_REASONS` / `_halt_shape` / `_halt_shapes` | 终态词汇、提交数、成交数、Σ\|intended\| |
| ③/① 装置 | `_as_traded` / `_rc_disagree` / `_REQ_OK` / `_NEG`(6 条反控)/ `_by_nf` / `_blind_same` | `[G7]` 六格的全部输入在断言前算好, 断言只做比较 |
| 顺序 | `_row_by_rid` 提前到 `_halt_flag` 同一循环(原定义在 resize 段, 被 ③ 提前用到), 原处删除 | 无语义变化 |

### 5.3 承重与红能力

**新增 11 格**(`[E]` 5 格 + `[G7]` 6 格), 套件 **48 → 59 格**, 真账本 **ALL PASS**。

**「没有放宽」是机械核对过的, 不是自称**: 把修前红日志与修后绿日志的**断言名逐条集合比对** —— 旧 48 条 **一条不少**地出现在新 59 条里(`LOST = 0`), 新增恰好 11 条。全文件的删除行只有 **6 行**, 全部是结构行(docstring 收尾 / `_by` 初始化与赋值 / `_traded` 过滤器那一行**被加严**成三个合取项 / `_row_by_rid` 定义位置前移), **没有一条断言、没有一个阈值(200 / 0.25 / 1% / 5% / 0.5×)被动过**。

| 突变(临时副本, 跑完即还原) | 打掉的是什么 | 预期红 | 实测 |
|---|---|---|---|
| **M1** `_row_rejudged` 直接 `return None` | ① 重判整体失效 | 稳态格 + 分离格 + `[G7]`#1 | **3 红, 全在预期格** |
| **M2** 去掉 `_clamp_known` 的同侧门 | 反侧的 confirmed 也被当截量 | `[G7]`#3 | **1 红** |
| **M3** `_fee_states` 改成 `sum(fee or 0)` | 费用三态并成一态 | `[E]` 费用格 + `[G7]`#6 | **2 红** |
| **M4** `_halt_shape` 的 `intended_usdt` 改读 `filled_notional` | 停机恒等式量换错 | `[E]` 停机恒等式格 | **1 红** |
| **M5** `_flat_rows` 选 `topup_taker` | 平仓类选错腿 | TRIP-FLATTENED 两格(+ 稳态格: `_traded` 被清空 ⇒ `_tr_split` 空 ⇒ 假) | **3 红** |
| **M6** 去掉 `Σ子成交 == \|C\|` 的门 | 「子成交没有定下量」也算已知 | `[G7]`#3 | **1 红** |

**旧码红(iv)**: 重标定**前**的同一文件(sha256 `bf0da6a1310b4926ae0717cbba4ad9b6223811b024d2a6653f5970e7746e3066`, 在 `918559f` / `fe97e46` / `3308cbc` 三个 sha 上**逐字节相同**)跑在**同一个**账本快照上 ⇒ **2 格红**, 正是 §4.3 第 2 条预告的那两格。

**第三条独立对账**(不在套件里, 手工做并记于此): 本文件的重判规则在全账本上重判出的行集合 =
`{(A1789215839, MEMEUSDT, maker), (A1789215839, POPCATUSDT, maker)}`, 与 W6 只读收据
`docs/receipts/w6_rejudge_20260912_receipt.json` 的 `read_time_verdict.kind == "known"` 行集合**完全相同**
(收据: 2 行 known, 6 项交叉核对 2/2 全真)。已知成交额 −1015.1883 / −509.07486, 残差 −0.05801076 / 0.0。

### 5.4 收据

| 件 | 值 |
|---|---|
| 账本快照 | `2026-09-13T00:04:34Z` `rsync -a ~/dl_quant_live/state/ <worktree>/state/`(**只读复制**, 无 `.env`); 44 日 / 76,101 orders 行 / 253 anchors 行 / 16 停机锚 / 10 个平仓批次 |
| 工作区 | `git -C /Users/haosiyu/cc_tmp/exec_w6 worktree add --detach /Users/haosiyu/cc_tmp/w8_ledger_fe97e46 fe97e46` |
| 重标定提交(**新 (a)(b) 头**) | **`c4ec4641fd95869c8a4cb8fe7c028ccfb709b82f`**(在 `fe97e46` 之上的**新**提交, 未 amend `fe97e46`; 只动 `live/tests_disposition_matrix.py`, +379 −6) |
| (c) 重新落在其上 | `3308cbc` cherry-pick ⇒ **`8e8510cc581a50c5bfab88b349d3f5b9261440d7`**; 分支 `fix/e0912a-reduce-only-clamp` 指向它; 备份分支 `w8-backup-pre-recal7` = 旧 `3308cbc`。`git diff 3308cbc 8e8510c` **只有** `live/tests_disposition_matrix.py` 一个文件 ⇒ (c) 的内容逐字未变 |
| `w6_reduce_only_clamp_ab.diff` | 重生成 = `git diff 918559f c4ec464`; **26 文件 / +8,658 −46**(原 25 文件 / +8,279 −40, 差值恰为本文件 +379 −6); sha256 **`24b6513e0dc041b29c2d20a8a74c30f8c463584447ea56ea949ae11efd4c5940`**(旧 `cdf370469d84d29d…`) |
| `w6_proportional_response_c.diff` | 重生成 = `git diff c4ec464 8e8510c`; 7 文件 / +859 −6; sha256 **`9f1375989342fe2f465062091a5bb05e0be0e7320ceadd9837c04cf582bb4653`** —— 与重生成前**逐字节相同**(底座动了, 内容没动) |
| 套件 修后(绿) | `docs/receipts/w8_disposition_recal7_after_green.log` — **ALL PASS (59 checks)**, rc 0 |
| 套件 修前(红) | `docs/receipts/w8_disposition_recal7_before_red.log` = `…_oldfile_on_new_ledger_red.log` — **2 FAIL (48 checks)**, rc 1(两文件同一次运行, 因为旧文件在三个 sha 上逐字节相同) |
| 突变 | `docs/receipts/w8_disposition_recal7_mutants.log` — 六个突变各自红在预期格 |
| 电池(**全量**, 新 (a)(b) 头 + 同一账本快照) | `bash run_acceptance.sh` @ `c4ec464`, stamp `20260913T010348Z`: **134 套 / 133 绿 / 1 红**。唯一红 = **`tests_env_loading`**(10/14; 四格全是「`ops/ic_monitor.py` / `ops/redeliver_alarms.py` / `ops/unseed_rehearsal_halt.py` / `scheduler/run_anchor.py` populates TELEGRAM_* on import」)—— 克隆无 `.env`(lead 规则), **环境红, 不是代码红**。`tests_disposition_matrix` rc 0 / ALL PASS 59; `tests_reduce_only_clamp` 与 `tests_flatten_fee_backfill` 均 rc 0。日志 `docs/receipts/w8_disposition_recal7_battery_c4ec464_ledger.log` |
| 电池(**全量**, **分支尖端 `8e8510c`** = (c) 在 (a)(b) 之上, 同一账本快照) | stamp `20260913T012821Z`: **135 套 / 134 绿 / 1 红**, 唯一红仍是 `tests_env_loading`。(c) 的 `tests_unknown_size_local_response` rc 0, `tests_position_break_blindspot` rc 0, `tests_disposition_matrix` rc 0, `tests_reduce_only_clamp` / `tests_flatten_fee_backfill` rc 0 —— 部署动词要用的那个 sha 上全量跑过。日志 `docs/receipts/w8_disposition_recal7_battery_8e8510c_ledger.log` |
| 电池 **对照**(干净 `918559f` + **逐字节相同**的账本快照) | **132 套 / 130 绿 / 2 红** = `tests_env_loading` + **`tests_disposition_matrix`** —— 后者就是 (iv) 的旧码红, 在电池层面又证了一遍。少 2 套是因为 (a)(b) 新增了 `tests_reduce_only_clamp` 与 `tests_flatten_fee_backfill`。**§4.3 当时的另外两红(`tests_alarm_digest` / `tests_break_split_wiring`)在本快照上两棵树都绿** —— 差别是**账本**(本快照含近 24h 可读告警; 最新对账锚已是 20Z 停机锚, 不再是 12Z 那个锚), 不是代码。日志 `docs/receipts/w8_disposition_recal7_battery_918559f_control.log` |
| 运行时影响 | **零** —— 本次只改 `live/tests_disposition_matrix.py`(+379 −6); 运行树 `~/dl_quant_live` 与生产者 `~/wide_shadow` 全程只读(只 `rsync -a` **出**账本, 没有写回), 无网络、无场所/Telegram 调用。**一处如实说明**: 全量电池里的 `tests_env_loading` 会在**干净子进程里 import**(不是运行)`ops/ic_monitor.py` 等四个模块来检查它们是否在 import 时装载 TELEGRAM_* —— 那是该套件的断言本身; `ic_monitor.py` 有 `if __name__ == "__main__"` 守卫, 模块层只绑常量并指向**克隆自己的** `state/`, 对运行树零接触。除此之外没有以任何形式调用过 `ops/ic_monitor.py` |

### 5.5 与 lead 规格的一处**刻意差异**(**已裁定: 接受**, 见本节末)

lead 的 (ii) 写的是「TRIP-FLATTENED 是**那个锚**的新类, 因为看门狗平仓让它**既不是普通稳态交易锚也不是停机锚**」。
**我把类做在了平仓批次上, 并且没有把 12Z 锚移出稳态人口。** 理由是事实:
- 重判后(①)该锚**自己的单**非自愿缺口 = **0.058 USDT**, 它按自身成绩就在 200U 线内 —— 把它豁免掉
  是**放宽**(多一个免检锚), 不是重标定, 直接违反规格 (v);
- 真正**没有任何断言读到**的, 是平仓批次那 255 行 / 235,382.55 USDT(全账本 10 批 / 1,708 行 / 73.8 万 USDT),
  §5.1 F8 用「删掉它们 `[E]` 一位不变」把这件事**实测**出来了。类做在批次上, 才对得上没被读到的那件事。

所以这一格是**净增断言 + 零豁免**。若 lead 仍要「该锚移出稳态人口」, 那是一次独立裁定, 我不替选;
真做的话改一行(`_steady_ids` 再排除 `_trip_anchors`), 但那会让 `[G7]`#1 的末句断言(`_rj_anchors ⊆ _steady_ids`)失效, 需要同时重写。

> **★ lead 裁定(2026-09-13, 转述原字)**: 「**这处刻意差异接受, 而且是更好的设计。** 把 TRIP-FLATTENED 放在平仓**批次**上、
> 12Z 锚留在稳态人口是对的: 重判后那个锚按自身成绩过 200U 线, 豁免它在规则 (v) 下就是放宽。你的盲区证明
> (删掉批次 `[E]` 一位不变)正是我要的承重证据。」—— 本节不再是待裁定项。重标定 #7 已入研究仓 `4442f6d5`。

### 5.6 未能验证 / 边界

1. **`[G7]`#2 把尺子绑在了运行时上**: 本文件 `import reconcile` 并与 `_clamp_rederived` 逐请求对账。
   若日后 `reconcile` 重构掉那个私有函数, 这格会红 —— 那是**要的**(尺子与书对「已知」不再同义就该有人看),
   但它意味着本测试文件从此对 `live/reconcile.py` 有依赖。已在代码注释里写明。
2. **两条规则有一处刻意不同**: 我方额外要求子成交 `trade_quote` 齐全可读(说得出张数说不出金额, 仍算读不出),
   `reconcile._clamp_rederived` 只定张数。今天账本上两者判出的请求集合相同; 若将来出现「有 trade_qty 无
   trade_quote」的截量行, `[G7]`#2 会红, 届时要按事实裁定是谁更对, **不要直接放宽**。
3. **平仓费用回填是操作员未做步骤**(F14): 断言的是「尺子报告它未测」, 不是「它永远未测」。
   ~~回填后 `fee_usdt` 变数字~~ —— **更正(09-13)**: 回填把佣金写进 `fills` 行, 订单行 append-only 永不改写,
   `[E]` 费用格读订单层, 所以回填后它**照样**报未测、照样绿(蕴含式成立), 但**不会**因为费用被补回而变化。
   尺子若要看到补回的费用, 需要另读 fills 层 —— 那是一次新的重标定, 未做。`[G7]`#6 是夹具格不受账本影响。
   **操作员命令的提案见 §6.7**(全历史, 待 lead 裁定, 未执行)。
4. **`_containing_anchor` 用「anchor_ts ≤ 批次 ts 的最后一个 anchors 行」定区间**, 不是真正的区间上界;
   今天 10 批全部落在交易锚里且 Σ|filled| 与该锚 realized 差 ≤0.11%, 所以这个近似在账本上被验证过 ——
   但它在「平仓发生在下一个锚行写出之后」这种边界上没有正控。
5. **账本是活的**: 本次所有数字都是 2026-09-13T00:04:34Z 快照上重算的, 套件本身**每次运行都重算**
   (规格 (v): readers recompute at emission), 文中的数只是那一刻的读数。16Z / 20Z 两个停机锚是 09-12 12:47Z
   跳闸后新长出来的; 再多几个同形态的停机锚不会让任何一格变红。
6. **本节不碰 §4 的任何结论**, §4 的文件在本次改动里一行未动。两个头都跑了全量电池: (a)(b) 头 `c4ec464`
   **134 套 133 绿**, 分支尖端 `8e8510c` **135 套 134 绿**, 两次唯一红都是 `tests_env_loading`;
   §4 的三套新套件在 `8e8510c` 上全部 rc 0。
7. **收据有一次重做**: 第一版重标定提交是 `f0072fc`, 我在自查时发现文件里两处注释写「五条反控」而代码是
   六条(正是本文件开头警告的那类「注释与它旁边的代码说反话」), 于是修注释 + 折行并 **amend 我自己那个
   提交** ⇒ `c4ec464`, 然后**重跑**了套件、六个突变与全量电池(不靠 sha 推断, E-0826-B)。
   lead 在 `aedcd824` 已入库的四份日志里, `..._after_green.log` 与 `..._mutants.log` 是 `f0072fc` 那一版,
   工作树里已被 `c4ec464` 的新版覆盖(状态 M), **请重新 commit**; 另两份(旧码红)未变。

## §6 C4–C8 收紧: C 是累计下界, F 才是量(W8, 2026-09-13; 独立研究员 `0158f5d1` §3.A + 专项 `codex_followup_code_review_2026-09-13`)

> **一句话**: §2 (a) 的截量类是对的, §4 (1) 的「从账本内容重推」也是对的 —— 错在**重推出来的 C 被当成了 F**。
> 场所接受 8、目前成交 4、单子还开着时, 新码报「精确成交 4」; 实际成交 6 同样合法, 却被完整 `reconcile` 读成
> 20 USDT 的数量残差。**这是保护性误报, 与 E-0912-A 同族、方向相反**。另有四处证据绑定不足(C5–C8)。
> 修法原则(lead 转述研究员): **只从结构化的原始请求/回包取证, 绝不用诊断串的正则授权; 精确已知只在
> 【证明终局】时给出, 否则老老实实回到区间 [C, Qv]。**

### 6.1 事实表(反例全部第一手复跑; 收据 = 研究员 `incident/COUNTEREXAMPLES.json` + `incident/ROOT_PARTIAL_STATES.json`)

| # | 事实 | 在哪测的 | 后果 | 修法 | 断言 |
|---|---|---|---|---|---|
| G1 | `_clamp_rederived` 只核 \|C\| ≤ Qv 与 Σ子成交 == C 就返回 C, `_exec_qty` 直接把它加进 known —— 而同一段代码的**非截量**分支是有终局门的(`confirmed_qty_final` 或 \|C\| ≥ \|qty\|) | `live/reconcile.py` 旧 `_clamp_rederived` / `_exec_qty` 截量块 | 截量分支比它旁边的分支**更松**, 少了终局这一条 | **C4** | — |
| G2 | 反例(研究员完整 `reconcile` 实跑): Qs=10 / Qv=8 / C=4 / 一个子成交 4 / `terminal=False` / `confirmed_qty_final=False` ⇒ 旧码 `_exec_qty` = `("known", 4)` | 我方 c4ec464 上逐字复现, `state ∈ {unknown, pending, confirmed}` 三种写法全中 | 下界被当成最终量 | C4 | T11 第 1 格 |
| G3 | 承重格: 实际成交 **6** 在经核容量 [4, 8] 内, 完全合法 —— 旧码在 mark=10 上报 `quantity_residual` **20 USDT**(`unexplained_frac` 0.33) | 同上; 研究员 `ROOT_PARTIAL_STATES.json` 三态各一份 | **保护性误报**: 同一条阶梯再误杀一次 | C4 | T11 第 2 格 |
| G4 | 合法减仓方向同样中: 先持空 8, BUY reduce-only 累计成交 6, 剩空 2 —— 不是「从平仓位凭空开 RO」的畸形夹具 | 研究员根代理追加; 我方复跑 | 反例不是畸形输入, 是统一数量合同**明确承认的合法状态** | C4 | T11 第 3 格 |
| G5 | 真实 12Z 两行 \|C\| == Qv(1,933,692 / 10,434 逐张相等)—— **容量闭合**: 场所只接受了这么多, 全成交了, 没有别的量还能来 | 真账本 `request_ledger` | 真实正控**不靠** `confirmed_qty_final`, 靠容量闭合 ⇒ 修 C4 不会毁掉它 | C4 | T11 第 5、11 格 |
| G6 | 生产者写的 `filled_unknown_qty` = \|Qs\| − \|C\| = 6 —— 那是**我们要的**减已确认, 不是**场所接受的**减已确认(应为 Qv − \|C\| = 4) | `_unknown_interval` 读该列 | 读回 10(超出场所接受的 8)本应是异常, 旧带 6 会放过 | C4 余带 | T11 第 6、7 格 |
| G7 | 显式 `reduce_only: False` 的合成请求仍被重判为 known —— 重判只读了诊断串与数量, 没读过任何 reduceOnly 证据 | 我方复现(旧码 `known 4.0`) | **不能把「origQty 变小」一律说成合法截量** | **C5** | T11 第 8 格 |
| G8 | 真实 12Z 的 `request_ledger` **没有 reduce_only 这一列**(键: client_id/qty/notional_est/state/confirmed_qty/terminal/confirmed_qty_final/inconsistent/order_id/trade_qty/trade_quote/settled_by/confirmed_notional_lower) | 真账本逐行 | ⇒ C5 只能做成三态: 显式 False 拒, **缺席保持缺席**(真实两行靠 G5 过) | C5 | `_reduce_only_evidence` 三态断言 |
| G9 | 写者用 `"; ".join(...)` 拼接一折的多条矛盾 | `live/binance_executor.py` L1679 / L1785 | 「截量理由 + 外来 orderId 理由」是**本系统产得出的串**, 子串判定会把它读成纯截量 | **C6** | T11 第 9 格 |
| G10 | `sum()` 里有 NaN ⇒ 和为 NaN, 而 `abs(NaN − 4) > 1e-9` 是 **False** ⇒ 「子成交定下这个量」这道门**通过** | 我方复现(旧码 `known 4.0`) | 失败方向错了: 读不出应该关向矛盾 | **C7** | T11 第 10 格 |
| G11 | 子成交 `{-1, +5}` 和也是 4 —— 尺子侧(W8 `_clamp_known`)逐个用了 `_fin` 所以挡住 NaN, 但**没挡负数** | 我方复现 | 子成交量是成交尺寸, 永远非负; 抵消不是成交史 | C7 | T11 第 10 格 + 尺子反控 |
| G12 | 尺子侧 `_clamp_known` 用子成交**报价**当已知成交额; 请求若自报 `confirmed_notional_final=True` 而 `confirmed_notional` 与报价和不符, 旧码取报价 | 研究员 C8 | 金额矛盾不该因为数量缩了就被盖掉 | **C8** | 尺子反控 + 正控 |
| G13 | W8 尺子的重判**只会缩小缺口**(把 1,524 缩到 0.058), 所以它的门必须至少和 `reconcile` 一样严 | 方向分析 | 同一条 C/F 纪律必须两边一致 | C4–C8 同步 | 尺子 11 反控 + 3 正控 |

### 6.2 改了什么

| 环 | 位置 | 改动 |
|---|---|---|
| C4 判据 | `live/reconcile.py` **`_clamp_rederived`** | 返回值从 `Optional[float]` 改为 `{"C", "Qv", "final"}`。`final = (terminal ∧ confirmed_qty_final) ∨ (\|C\| == Qv)`。六道门按序: G1 kind(C6)/ G2 RO(C5)/ G3 容量(`qty_venue` 与串必须**同一个读数**)/ G4 同侧与上界 / G5 子成交(C7)/ G6 终局(C4) |
| C4 消费 | `_exec_qty` 截量块 | 非终局的截量 ⇒ `_all = False`, **不进 known**, 落回行自己的 known + 余带(`bounded`)—— 与重判出现之前逐字一致, 不产生残差告警 |
| C4 余带 | 新 **`_clamp_capacity_band`** + `_unknown_interval` | 行内每个已发请求都是可重推截量时, 余带 = Σ(Qv − \|C\|); 只用于 `min()` **收窄**, 描述不了的行保持原带 ⇒ 永远不会放宽 |
| C5 | 新 **`_reduce_only_evidence`** | 三态, 只读结构化字段(`reduce_only` / `reduceOnly` / `venue_reduce_only` / `resp_reduce_only`) |
| C6 | 新 **`_origqty_reasons`** | 按 `;` 拆开, **每一条**都必须是 origQty 值比较 |
| C7 | 新 **`_child_qty_sum`** | 逐个 `_fin` 且非负, 求和**之前**就关闭 |
| 命名 | `_rederive_ledger` | `known` 的值从裸数量变成结构化裁定; 局部名 `c` → `ev`, docstring 写明「三个读者只按键索引, 唯一取值的读者必须先看 `final`」(E-0905 同族: 同一函数体内换了来源的名字必须换名) |
| C4–C8 尺子侧 | `live/tests_disposition_matrix.py` `_clamp_known` | 同六道门 + C8 金额一致门。**新门全部写在函数体内**, 不引新的模块级常量或辅助函数名 —— 研究员的 `pure()` 探针按名字抽取本文件的七个函数, 新名字会让他们的回归跑不起来 |

### 6.3 测试与红能力

| 件 | 新码 | 旧码(`c4ec464`) |
|---|---|---|
| `live/tests_reduce_only_clamp.py` **[T11] 12 格** | **87/87 ALL PASS**(原 75 格全部保留) | **3 格红后 `AttributeError: module 'reconcile' has no attribute '_clamp_capacity_band'`** ⇒ 即红 |
| `live/tests_disposition_matrix.py` | **60/60 ALL PASS**; 反控 6 → **11** 条, 另加 **3** 条正控(把每条反例拿掉的那一个字段还原, 同一请求必须**重新被接受**且数字分毫不差 —— 一条「一律拒绝」的规则会骗过反控格) | 同样 60/60(新门写在测试文件内, 真账本上没有 C4–C8 形态的行) |
| 研究员**自己的** harness + **自己的**冻结反例(`probe_followup.pure` AST 抽取 + `COUNTEREXAMPLES.json`) | **10/10 过** | **9/10 红** |
| 逐条复现(旧码 → 新码) | C4 三态 `known 4` → `bounded 4`(读回 6 的异常 1 → **0**); C5/C6/C7a/C7b `known 4` → `unquantifiable`; 容量闭合正控 `known 8` → `known 8` **不变** | |
| 真实正控 | 两行仍 `known` −1,933,692 / −10,434, `final=True` 由**容量闭合**给出; T9 看门狗 §4-5b **CLEAN**、§4-7 CLEAN; 真 09-12 全日 `reconcile` **0 异常** | |

### 6.4 收据

| 件 | 值 |
|---|---|
| 新 (a)(b) 头 | **`bea37cf79bcee3cb9b370270a92e44229b051ea2`**(在 `c4ec464` 之上的新提交; 3 文件 +343 −35) |
| (c) 重接 | **`69a24bb0710c0f2c2d6c72fce6cc7ae351ec2079`**; 分支 `fix/e0912a-reduce-only-clamp` 指向它; 备份 `w8-backup-pre-c4fix` = 旧 `8e8510c`。`git diff 8e8510c 69a24bb` **只有我这三个文件** ⇒ (c) 自身内容逐字未变 |
| `w6_reduce_only_clamp_ab.diff` | `git diff 918559f bea37cf`; **26 文件 / +8,966 −46**; sha256 **`fd9ac31a185c84436f3ab6c8475c4c1bdb3c31a74f12c1a91abb6bb665425c9b`**(上一版 `24b6513e…`) |
| `w6_proportional_response_c.diff` | `git diff bea37cf 69a24bb`; 7 文件 / +859 −6; sha256 **`15d29d99faad2f1ad5597a89da1c1686ca94d2d94adc24c6ab1a4e4327912d5c`**(上一版 `9f137598…`)。**内容没变, 变的是上下文行** —— (c) 也改 `reconcile.py`, 我这轮改了它的邻行 |
| 电池 (a)(b) 头 | `bash run_acceptance.sh` @ `bea37cf`, stamp `20260913T020214Z`: **134 套 / 133 绿 / 1 红** = `tests_env_loading`(克隆无 `.env`, 环境红)。`tests_reduce_only_clamp` 87/87, `tests_disposition_matrix` 60/60, `tests_watchdog` / `tests_binance_executor` / `tests_flatten_fee_backfill` 均 rc 0。日志 `docs/receipts/w8_c4_battery_bea37cf_ledger.log` |
| 电池 分支尖端 | 同一快照 @ `69a24bb`, stamp `20260913T021838Z`: **135 套 / 134 绿 / 1 红** = `tests_env_loading`。(c) 的 `tests_unknown_size_local_response` 与 `tests_position_break_blindspot` 在新的 (a)(b) 之上仍 rc 0。日志 `docs/receipts/w8_c4_battery_69a24bb_ledger.log` |
| 套件与回归收据 | `w8_c4_clamp_finality_new_green.log`(87/87)· `w8_c4_clamp_finality_oldcode_red.log`(旧码红 + 五个缺陷逐条复现与修后对照)· `w8_c4_reviewer_probe_regression.log` + `.py`(研究员 harness 喂研究员反例: 修后 10/10, 修前 9/10 红) |
| 账本 | 与 §5 同一份只读快照 `2026-09-13T00:04:34Z` |
| 运行时 | 运行树 `~/dl_quant_live` 全程只读(HEAD 仍 `918559f`), 无网络, 无场所/Telegram 调用, 未提交研究仓 |

### 6.5 未修 / 已知项(**不在本轮范围**, 按 lead 的字记录)

1. **C9 —— (c) 的 `_between` 顺序依赖(OFF, 不修)**: `live/reconcile.py` `_between` 对未知名用 `unknown.setdefault(symbol, …)`, **每名只保留第一行**; 后面的 `_venue_consistency` 只看那一行。研究员的完整反例: 同名同读回区间, 第一行意图 10 / C 4 / origQty 型矛盾(Qv 11 > Qs 10, 因此 (a)(b) **不**重推), 第二行意图 1000 / C 0 / **外来 orderId**。第一行较早 ⇒ `local.eligible=True`, 第二行的矛盾根本没进局部证据; **只交换两行先后** ⇒ `eligible=False`。同一组联合事实因排序改变风险动作。开关 `UNKNOWN_SIZE_LOCAL_RESPONSE` 默认 `False`, 隔离了这个局部动作; **它不隔离 (a)(b) 的内容重判**(那部分已由本节修完)。重开 (c) 之前必须先关掉 C9 与研究员的 Q6 联合上界。
2. **(c) 的 `_is_evidenced_clamp_kind` 仍带 C6/C7 形态**: 它回答的是「场所自己的记录是否自洽」而不是「量是多少」, 且 (c) 的夹具**故意**钉住一条「(1) 不重推、但记录自洽」的形态(串里 Qv 高于 Qs)。本轮没有动它 —— 它是 (c) 的代码, (c) 默认关且本轮不改。重开 (c) 时与 C9 一起处理。
3. **`ops/rejudge_ledger_rows.py` 的六项 `cross_check` 只是收据, 不是 runtime 门**(研究员另证: 喂错 side / 外来 cid 但六格吻合的合成输入仍得 `all=True`)。真实两行的身份另由原始 POST 独立核过。本轮未改该工具。
4. **余带收窄的边界**: `_clamp_capacity_band` 只在**行内每个已发请求都是可重推截量**时给出容量; 混合行(一条截量 + 一条普通未决)不给容量, 保持生产者原带。这是保守失败, 不是漏纳, 但也意味着混合行上「超出场所接受容量」仍不会被抓。
5. **研究员对 W8 尺子(§5)的两条观察, 本轮未改, 请裁定**:
   (i) TRIP-FLATTENED 的「Σ\|filled\| 在所在锚 realized 的 10% 带内」**证明不了批次齐全**: 100 条各 1U 的完整平仓删掉 5 条,
   95U 仍落在 100U 的 10% 带内, 该格照绿。它验证的是「记录里的批次大致覆盖整书」, 不是「逐笔齐全、全书归零」;
   后者需要独立的预期订单/持仓人口或平仓后回读为 0 的硬断言。
   (ii) **§5 那一格的注释说错了**(我的): 注释称「批次哪天改名仍会落进这个类」, 但断言要求结构集合 = FLATTEN 前缀集合 =
   不在 anchors.jsonl 的集合, 所以**改名会让该格变红**, 不是静默纳入。失败方向是保守的(红, 不是漏), 但注释与代码说反话,
   正是本文件开头警告的那类错。没在本轮改, 是为了不让交付的头再换一次 sha 而没有对应的电池; 修它只动注释。
6. **未做**: 没有执行 `resume_from_trip.sh`, 没有回填平仓费用(仍是操作员步骤), 没有部署。

### 6.6 追加(lead 09-13 字): `[G7]` 第 2 格改到 C/F 合同, 不许放宽 —— 提交 `5feea3e`(测试文件 only)

| # | 事实 | 在哪测的 | 后果 | 改法 |
|---|---|---|---|---|
| H1 | 原格比的是**键**: 尺子接受的请求集合 == `reconcile._rederive_ledger` 的 `known` **全部键** | `tests_disposition_matrix.py` `[G7]` 装置 | C4 之后两个集合**定义不同**: `known` 里有开着的截量(`final=False`), 尺子只收终局的 | 逐请求比 |
| H2 | 今天账本 441 个带请求账本的行: **2 个终局裁定 / 0 个开着的** | 测试运行时重算 | 原格在真账本上**碰巧**绿 | 加两分支夹具 |
| H3 | 合成演示: 研究员的开着 C4 夹具在**修后**运行时上 —— 尺子拒、运行时 `{C 4, Qv 8, final False}`, 原格报 **DISAGREE**(两边其实都对); 新合同格 agree | `/tmp` 演示, 两个运行时各跑一遍 | 原格会在账本出现第一个开着的截量时**假红** | — |
| H4 | 同一演示在**修前**运行时(`c4ec464`, 返回裸数 4.0 = 声称终局)上: 新合同格 **DISAGREE** | 同上 | 新合同格能分辨「正确运行时」与「把 C 提升成 F 的运行时」; 原格两个都报分歧, 分辨不了 | 裸数裁定读作「终局」 |

**新合同**(逐请求): 尺子接受 ⇔ 运行时裁定为**证明终局**, 且两边接受时已确认量相同; 开着的截量两边都拒。
另加三个合同夹具(研究员的开着 C4 / 容量闭合 / terminal+final), 要求终局 ≥ 1 且开着 ≥ 1 —— 否则「开着两边都拒」
这半条合同从来没被执行过。格数不变(60/60): 这格是**被加严**, 不是新增。

**红能力**(同一快照, 收据 `w8_g72_contract_mutants.log`):

| 突变 | 预期 | 实测 |
|---|---|---|
| A 修后运行时 + 尺子 `_clamp_known` 去掉终局门 | 本格红 | **本格红**(另负控格红) |
| B **修前**运行时 `c4ec464` + 新测试文件 | 本格红 | **仅本格红** |
| C 修前运行时 + 本格只查账本、不查夹具 | 绿(证明夹具才承重) | **绿** |

另: `[E]` 平仓费用格的措辞**我写错过** —— 原文「由操作员回填关闭」。回填落在 fills 行, 订单行不改, 该格读订单层,
回填后计数不会下降。已改为如实描述(见 §5 F14 更正)。

### 6.7 操作员命令提案: 全历史平仓费用回填(**待 lead 裁定, 未执行, 未以任何模式跑过**)

**先说结论**: 按现有 `ops/backfill_fills.py`, 「全历史跑一遍」**只能真正补回 09-12 一批**(255 行 / 235,382.55 USDT)。
09-09 那批 fills 层已测, 不需要。其余 **8 批 / 1,210 行 / 270,076.47 USDT 现工具补不回**: 当年下单没发 client id,
账本行也没有 order id, 工具重建出 0 条腿后按设计拒写。所以下面的命令是**测量 + 补 09-12**, 不是「关闭历史盲区」。

**工具事实**(读源码, `5feea3e`): 只接受单个 `--day YYYYMMDD` 与 `--apply`; `LIVE_MODE` 默认 **TESTNET**(读的是 testnet 的 pilot_log 根);
「只报告」模式**不是离线的** —— `find_gaps` 一旦找到缺口, `run()` 就 `BinanceBroker(mode).arm()` 并对每个缺口调
`allOrders` / `userTrades`, 只是不写盘; 两个查询都只带 `startTime`, 本仓 `docs/API_SEMANTICS.md` 没有记录这种查询能回溯多远
(`ops/gate_coverage.py` 明写这是盲区)⇒ **报告本身就是那次测量**。

**离线预判**(`find_gaps` 纯函数逐日跑在只读快照上, 未建 broker):

| 日目录 | 平仓批次 | 缺 fills 的名 | client id | 预判 |
|---|---|---|---|---|
| 20260801 | `FLATTEN-20260801T201827Z` | 105/105 | 0 | 0 条腿 ⇒ 拒写 |
| 20260802 | `FLATTEN-20260802T041821Z` | 83/83 | 0 | 0 条腿 ⇒ 拒写; **同一次运行还会查普通调仓批 `A1785657675`(缺 22 名)** |
| 20260805 | `…T001853Z` / `…T121829Z` | 108/108 · 102/102 | 0 · 0 | 拒写 · 拒写 |
| 20260821 | `…T121630Z` / `…T201600Z` | 108/108 · 102/102 | 0 · 0 | 拒写 · 拒写 |
| 20260826 | `FLATTEN-20260826T124702Z` | 334/334 | 0 | 拒写 |
| 20260906 | `FLATTEN-20260906T084608Z` | 268/268 | 0 | 拒写 |
| 20260909 | — | 无缺口(fills 已有 3,095 笔唯一成交) | 0 | 无事可做 |
| 20260912 | `FLATTEN-20260912T124737Z` | 255/255 | **255** | **可归属**(若场所仍回得出) |

**提案命令**(在运行树跑, 那里有凭据; 解释器与电池同一个 `/usr/bin/python3`):

```bash
# 第 1 步 —— 全历史报告(会用凭据读场所, 不写盘)。先读报告, 再决定第 2 步。
cd ~/dl_quant_live
mkdir -p ~/backfill_reports_20260913
for d in 20260801 20260802 20260805 20260821 20260826 20260906 20260909 20260912; do
  LIVE_MODE=LIVE /usr/bin/python3 ops/backfill_fills.py --day "$d" \
    > ~/backfill_reports_20260913/report_"$d".json
done

# 第 2 步 —— 只对报告里「n_legs_rebuilt_from_venue > 0、无 warning、symbols_unreached 为空」的日子 --apply。
# 按离线预判, 这只会是 09-12:
LIVE_MODE=LIVE /usr/bin/python3 ops/backfill_fills.py --day 20260912 --apply \
  > ~/backfill_reports_20260913/apply_20260912.json

# 第 3 步 —— 幂等复核: 再报告一次 09-12, 应得 n_rows_written 0 且 n_rows_already_present == n_rows_recoverable。
LIVE_MODE=LIVE /usr/bin/python3 ops/backfill_fills.py --day 20260912 \
  > ~/backfill_reports_20260913/recheck_20260912.json
```

**每份报告要读的字段**: `n_gaps`; 每个 result 的 `warning`(拒写原因)、`n_legs_rebuilt_from_venue`、`n_trades_seen`、
`n_trades_unattributed`、`n_rows_recoverable`、`symbols_unreached`、`read_failures`。

**需要 lead 另行裁定的三件事**:
1. **`--day 20260802 --apply` 会连带写普通调仓批 `A1785657675` 的补回 fills 行**(不是平仓) —— 是否要它, 单独裁。
2. **8 批补不回的平仓要不要改工具**: `state/live/watchdog/events.jsonl` 保留了每个跳闸日的平仓下单回包。按平仓形状
   (`submit` 动作 ∧ `reduce_only` ∧ `tif=IOC`)逐日数「带回包 orderId 的动作」: 08-01 **105** · 08-02 **83** · 08-05 **210** ·
   08-21 **210** · 08-26 **334** · 09-06 **268** · 09-09 **243** —— **与当日平仓订单行数逐日完全相等**(另各有 1–2 条无 orderId 的动作,
   即下单失败那几条); 09-12 为 256 对 255 行。`userTrades` 本身按 orderId 归属, 所以按 events 里的 orderId 联接**在原则上能覆盖
   全部历史平仓行**。但那是**工具改动**(新联接源 + 测试 + 旧码红), 不是命令; 且场所对只带 `startTime` 的查询能回溯到 08-01 与否未知。
   不改的话, 这 1,210 行的费用只能标成「未测」或用 5 bps 这类**标明为估计**的数, 不能写成测得。
3. **09-09 那批的 fills 行在账本里写了两遍**(6,190 = 2 × 3,095; 一遍 `rebuilt_from_venue`, 一遍 `backfilled_utc`, 无 `supersedes`)。
   `collapse_supersedes` 读出 3,095; 任何不经它直接求和的费用读者会**翻倍**。佣金币种 BNB + USDT 混合, 换算要走现有 `fee_conversion`。

**即使三步都做完**: 订单层 `fee_paid` 为 None 的计数仍是 **1,704**(append-only), 尺子 `[E]` 费用格照报未测;
研究员另指出的两处继承边界仍在 —— `find_gaps` 按 (批, 名) 有任一 fill 即不算缺口(部分成功后的重跑看不出缺),
`existing_trade_ids` 只按裸 trade_id 去重(跨 symbol 撞号会误删新行)。第一次完整拉取不受前者影响(09-12 当前 0 行 fills)。

### 6.8 收据(本节终态; 部署动词用这里的 sha)

| 件 | 值 |
|---|---|
| (a)(b) 头 | **`5feea3e9d1350d68700c329ccf16c703c338ed58`** = `bea37cf`(C4–C8, §6.1–6.5)+ `[G7]`#2 合同(§6.6, 测试文件 only)。两个都是新提交, 未 amend 任何已报告的头 |
| 分支尖端 | **`595de41168d0eb44766bf319966e4946c274f39f`** = 原 (c) cherry-pick 到 `5feea3e` 上; `git diff 8e8510c 595de41` 只有 (a)(b) 那三个文件 ⇒ (c) 自身内容逐字未变 |
| `w6_reduce_only_clamp_ab.diff` | `git diff 918559f 5feea3e`; **26 文件 / +9,033 −46**; sha256 **`b1be2bdda51c01828cff5ace88832566744de02800d93f081d88560c74b61e9f`**(上一版 `fd9ac31a…`) |
| `w6_proportional_response_c.diff` | `git diff 5feea3e 595de41`; 7 文件 / +859 −6; sha256 **`15d29d99faad2f1ad5597a89da1c1686ca94d2d94adc24c6ab1a4e4327912d5c`** —— 与 `bea37cf` 那一版**逐字节相同**(本轮只动尺子文件, (c) 不碰它, 上下文行没动) |
| 套件 @ `5feea3e` | `tests_reduce_only_clamp` **87/87**(T9a / T9b 看门狗 §4-5b CLEAN, §4-7 CLEAN)· `tests_disposition_matrix` **60/60**(`[G7]`#2 extra: 账本 441 行 2 终局 / 0 开着; 夹具 2 终局 / 1 开着; 全一致)。`w8_g72_tests_reduce_only_clamp_5feea3e.log` · `w8_g72_tests_disposition_matrix_5feea3e.log` |
| `[G7]`#2 红能力 | A / B 红、C 绿, 全在预期格: `w8_g72_contract_mutants.log`(含促成本次改动的双运行时演示) |
| 电池 (a)(b) 头 | @ `5feea3e`, stamp `20260913T024857Z`: **134 套 / 133 绿 / 1 红** = `tests_env_loading`(克隆无 `.env`)。`w8_g72_battery_5feea3e_ledger.log` |
| 电池 分支尖端 | @ `595de41`, stamp `20260913T030452Z`: **135 套 / 134 绿 / 1 红** = `tests_env_loading`; (c) 的 `tests_unknown_size_local_response` 与 `tests_position_break_blindspot` rc 0。`w8_g72_battery_595de41_ledger.log` |
| 快照与运行时 | 同 §5 只读快照 `2026-09-13T00:04:34Z`; 运行树 `~/dl_quant_live` HEAD 仍 `918559f`、全程只读; 回填命令**未以任何模式执行**; 无网络、无场所/Telegram 调用; 未提交研究仓 |
