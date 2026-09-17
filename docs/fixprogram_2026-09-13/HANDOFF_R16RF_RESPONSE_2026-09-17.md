# 第四次交付复审: R16RF(独立复审第三轮)四条边界 + 公证归因 + B14 合同 —— 逐条修复与证据

> **创建:** 2026-09-17 | **Session:** 0134cBjSFjjurUhAz95RNuWk | **状态:** 交付复审(§3.2 电池待回填) | **作废条件:** 下一轮复审响应文档取代本文; 任一提交被改写则本文 sha 作废

## 0. 一句话

R16RF 的四条 P2 边界(E1 第二条减仓入口 / E2a ±inf / E2b 检查-写入字节 / T1 空前月路径)**全部在原码上逐行核实成立并修复**, 每条带真实入口测试与**钉死提交**的修前对照; 公证套件红的**归因更正**为夹具与 LED-01 写入合同失配(修夹具 + 孤儿负控, 合同未动); B14 按失败格逐字段 dump 定出**状态-动作合同**后改断言(生产者未动); 四条测试的修前源改为钉死提交, King 测试对照缺席一律 exit 3。本轮**零部署**, 生产仍 ef60f85。收益无新测量; 「0.8–1.3」按复审意见**降级为人工保守情景**, 不是验证出的线上预期区间。

## 1. 提交链

**执行器叠加树**: `… → facdf24 → 183915f → `**`cdfc06b`**(`live/binance_broker.py` `scheduler/anchor_loop.py` + 四份测试 + `ops/gate_coverage.py`; `state/` 零入库)
**研究仓**: `… → 758c6e4c → `**`49d7c214`**(applier + 月份门 + 三份测试 + `receipts/R16RF_tests_20260917/` 六份日志)
收据 diff: `receipts/STACKED_R16RF_183915f_to_cdfc06b.diff`(493 行, sha8 1e6dc91f, 只触及上列 7 文件) · `receipts/STACKED_ef60f85_to_cdfc06b.diff`(24,947 行, sha8 c85b5edd, 生产→叠加树全量)。

## 2. 逐条

### 2.1 R16RF-E1 NaN 经陈旧信号 DERISK 进入 submit(P2, 执行器)
- **核实**: `scheduler/anchor_loop.py _scale_to` L3197–3211 —— broker 现在保留 NaN, 旧码 `state["stale_ref_contracts"]=dict(cur_c)` 把它存为参考, `cut_c=NaN`, `abs(NaN)<1e-9` 为假 ⇒ `submit({"quantity": NaN, reduce_only})`; `submit` L1573–1578 无有限性门。**第二轮修复暴露的下游回归**, 复审说对了。
- **修复**(两层, 已知有限路径不变): `_scale_to` 非有限数量具名列入 `derisk_unknown` / `state["stale_ref_unknown"]`, 不作参考、不定量、不当零, HIGH 告警; `submit()` 在每张单必经处、**DRY_RUN 分支之前**加最终有限性门, 记 `submit_refused_nonfinite_quantity`, 抛 `QuantityNotFinite(OpeningHalted)`(同一类进程内拒绝, 每个调用方的处理已在生产跑过; `binance_executor:1309` 只捕 `OpeningHalted`/`VenueTransportError`, 子类不会逃逸)。
- **证据** `tests_broker_nonfinite_positions.py` **15/15**(重写): `_request` 改为线端记录器, 探针 armed 且未 halt —— **数 POST**, 不再把任意异常当「已提交」(复审指出的弱点); 真实 `_scale_to` 按 AST 从源码提取; 三源钉死: **facdf24**(丢 NaN: DERISK 静默 0 单, 未知名被当作不存在) / **183915f**(留 NaN: DERISK `POST quantity=nan reduceOnly=true` —— 复审反例逐字复现) / **修后**(0 单, `derisk_unknown=[NANUSDT]`, 参考不含 NaN, HIGH 告警; 混合账户 10+NaN 只 POST `TENUSDT SELL 5.0 reduceOnly`); `submit(NaN)` LIVE 与 DRY_RUN 都拒(183915f: 1 POST)。

### 2.2 R16RF-E2a 写入端接受 ±inf(P2, 研究仓 applier)
- **核实**: C2b `(_row_ts == _rec_ts) and (_row_ts == _row_ts)` —— `inf==inf` 为真; 消费者 `_finite()` 拒 ±inf。成立。
- **修复**: `math.isfinite(_row_ts) and math.isfinite(_rec_ts) and _row_ts == _rec_ts`, 与消费者同一合同。
- **证据** `tests_led04_apply_identity.py` E1(+inf/−inf): `--apply` REFUSE 2, 不落盘; **D2(fda1d3ef 源)**: +inf 被准入并写入 exit 0 PASS(复现)。

### 2.3 R16RF-E2b 检查通过的字节 ≠ 写出的字节(P2, 同文件)
- **核实**: C1 `gsha(a.records)` 一次、`checks()` `open(a.records)` 二次、`apply()` `open(a.records).read()` 三次; 成功条件不核落盘 sha。成立(遗留缺口, 非 C2b 新造)。
- **修复**: 记录字节进程内**只捕获一次**(`RAW`, 同 dataless/short-read 守卫), C1/解析/写出/最终核对全对这一份; 最终成功条件 = 落盘 sha == 授权 sha(两种模式), 不等则挪走 `.REJECTED_SHA_MISMATCH_<ts>` 并 FAIL; 收据加 `records_bytes_captured_sha256` / `persisted_sha256`。
- **证据** F1/F2: 用复审同样的 `tempfile.mkstemp` 审计钩子在检查后换成对调文件 —— 落盘 == 授权 sha, 记录未被对调, PASS; **D3(fda1d3ef 源)**: 写出的是被换的字节且 PASS(复现)。**11/11**。

### 2.4 R16RF-T1 空前月路径缩小应检查集合(P2, 月份门)
- **核实**: P0 只查键在不在(L107–114); P4 `_need` 过滤空串(L209)。`CACHE=` ⇒ 7/8 PASS; 8 空 ⇒ `n_required=0`, 对一份无关文件的记录 PASS。成立。
- **修复**: 新增 **P0b** 任一合同中空的 ROLLED 值**具名**拒绝(先于覆盖构造); P4 覆盖**按键**计(`n_required_keys=8`, 空/缺键列入 `previous_rolled_keys_not_in_record`), 不再被过滤或去重缩小; P1/P2/P3 对空值不出噪声。
- **证据** `tests_pipeline_gates.py` Q8(CACHE 空 + 7 件记录 ⇒ rc3, P0b=[CACHE], P4 8 键缺 CACHE) / Q8b(8 空 + 无关记录 ⇒ rc3, P0b 8 名, P4 8 键全缺 —— 不是 0) / Q8c(本月合同空值)。**478/478 ALL PASS**。

### 2.5 公证套件红的归因更正(复审 §2)
- **核实**: 我 17:05Z 电池的逐格日志 —— W1(TCC 形态)OK、R2(断链)OK, 红的是 **W9/V1**; 夹具 L424–426/L500–502 写 `trade_id=100+i, supersedes_trade_id=100+i`, 文件里无此原始成交, `PilotLogger.fill`(L488–528)按 LED-01 判 `orphan_supersede` 返回 False 并隔离, 夹具不看返回值。**我上一轮把它归为「公证 16 日断链」是错的**, 复审对。
- **修复**(只改夹具): 修订行 supersede 文件里真实存在的原始行(Sandbox.day 写的 trade_id 1..3, 同 symbol), 逐行断言 `fill` 返回 True 且字节增长(W9-pre/V1-pre); 新增 **W9n** 孤儿负控(返回 False、字节不变、隔离为 orphan_supersede)。写入合同一字未动。套件 **ALL PASS** ⇒ 上次电池 5 红中此红关闭。

### 2.6 B14 状态-动作合同(复审 §3)
- **失败格逐字段实值**(183915f dump): `latest.anchor_kind=halted_book_held`, `portfolio_dev_frac=0.01 < portfolio_limit_frac=0.25`(held-book 意图生效, 不是无标记邻近的 99% 意图零破位), `trip_gate=split_unauth`, `split.unauth_frac=0.013`(夹具故意留在其它名字上的 R1 残差), `latest.triggered=True`, `state=BREAK`, `cond5.triggered=True`; 随后 `ev3.tripped=False`, `triggers=[]`, `local_responses=[{names:[S007USDT], kind:proportional_local}]`, 无新增 flatten 调用(唯一一次是 ev1 局部响应自己的, 只覆盖 S007USDT)。
- **消费者图谱**(`position_break.py` / `watchdog.py`): 动作路径只消费 `triggered` + §4 比例门 ⇒ {书级 trip | 局部响应 | 无}; `state` 由最新已判锚的 `triggered` 派生(BREAK iff triggered, UNOBSERVED 只压非 BREAK), 只被 conditions 展示块与 split 告警侧读, **没有任何动作读 state**。
- **合同**: `state=BREAK` = 「判官在该锚量到了一个具名的、超线的未授权偏差」这一**测量标签**; 对具名比例破位的动作是局部响应(记录在 `local_responses`), 不是 trip。旧断言 `state != BREAK` 断的是合同没承诺的东西; FIXPROGRAM 旧文「断言 == BREAK 而实际 LOCAL」**方向反了**(复审指出)。
- **处置**: 生产者不动; B14 改断动作合同(不 trip、无书级触发、dev<limit、无新增 flatten、历史平过集合 == [S007USDT]); 新增 **B14c** 把「BREAK 是测量标签、动作是比例门的」钉死; 无标记邻近正控原样保留。**60/60**。这不是「预先批准只改断言」—— 是先取实值、画消费者图、再按合同改。

### 2.7 测试装置(复审 §3.1–3.2)
- 四条测试修前源改为**钉死提交**(facdf24 / ba247021 / fda1d3ef), 形态核验后再用, 移动窗只作退路; King 测试对照缺席一律 **exit 3**, 不再落到 ALL PASS。
- broker 测试改为数 POST(见 2.1)。

## 3. 套件与电池
### 3.1 受影响既有套件(叠加树 cdfc06b)
tests_binance_broker / flatten_ladder / signal_and_loop / watchdog / offschedule_held_book / flatten_rows / reduce_only_clamp / imports / flatten_batch_identity / stale_order_sweep / topup_leg_fill / reject_topup / binance_executor 全绿; tests_ledger_notary ALL PASS; tests_proportional_response 60/60。日志 `receipts/R16RF_tests_20260917/`。
### 3.2 全量叠加电池(20Z 窗口内, 22:42:35Z→22:58:21Z, head cdfc06b, `/usr/bin/python3` 3.9.6)
收据 `receipts/STACKED_BATTERY_20260916T224235Z.log`(sha8 cffdf2de)。**157 绿 / 3 红 / 1 UNAVAILABLE, RC=1(既有红仍在)。**
相对 17:05Z 基线(155/5/1, head 183915f): **转绿 = `tests_ledger_notary`、`tests_proportional_response`**(正是本轮修的两套); **新红 = 0**; 共同 **161** 套里只有这两套退出码变化, 其余逐套件一致(初稿误写 159 —— 那是 facdf24 基线的规模, 独立研究员指出, 已更正)。
剩余非零: `drift_gate` / `tests_drift_gate`(真漂移×2, pilot_metrics 研究副本与上游不一致, 应按方向审阅后同步, 不能改门求绿) · `tests_entrypoint_wiring`(本机 nosleep/电源, `log_verified=False` = 未取得睡眠日志, 不证明睡过) · `tests_env_loading` 3 = UNAVAILABLE(叠加树按规矩无 .env, 不折算 PASS)。
ENVRED-2(开跑现算): env 缺失 · notify_audit 1986 行 · pilot_log 47 天 · watchdog_events 15 —— 与两次基线**逐项相同**(未重拷账本), 仅 audit 最新行年龄随钟 17.94h。按复审 §1 的读法: 这证明的是**已执行验收集合的退出状态无退化**, 不是穷尽输入的无回归 —— 本轮 DERISK 反例正是电池断言之外的回归, 它由 `tests_broker_nonfinite_positions` A5/C3 覆盖。

## 4. 接受的复审意见(不再争)
- 「现有电池无新增失败套件」≠「无任何回归」—— 接受; 本轮 DERISK 反例正是电池断言之外的回归。§3.2 的「157/3/1」按此读法陈述。
- 「0.8–1.3」= 人工保守情景锚点, 不是验证出的线上预期区间; 2.523 的条件限制保持; 本轮无新收益实验。`HONEST_EXPECTATION` **已改 v4**: 六处就地划去+附注(§0「波动没有问题」过强 · LED-10 下界 · CI「必然偏窄」· 源码不在 Git/清树即失 · 结论框标「人工保守情景锚点」· §5 加「不主张验证出的线上区间」), 原句字节保留。
- 驱动的旧来源闭包(月 driver 不核前月合同/PREV 记录/旧工件)限制成立, 本轮未扩张。

## 5. 未做 / 待裁定(逐条, 不作完成声明)
- R16R §5 六项(v2 后视中位数 / 面板装置三处 / NOSLEEP-1 / finalize 三态后继(冻结装置需裁定) / CLOSE 终止瞬间 / 月度重训配对); 月 driver 前月来源闭包; drift 红的 pilot_metrics 同步方向; 复审 PENDING_DECISIONS 的各项建议 —— 需用户裁定的已列, 不需裁定的下一轮按第一优先推进。
- 部署批准(零部署)。

## 6. 复跑命令(逐字)
```
cd <scratchpad>/stack
/usr/bin/python3 live/tests_broker_nonfinite_positions.py
/usr/bin/python3 live/tests_ledger_notary.py
/usr/bin/python3 live/tests_proportional_response.py
cd ~/Desktop/quant_research/docs/fixprogram_2026-09-13
/usr/bin/python3 FX_EXEC2/devices/tests_led04_apply_identity.py
/usr/bin/python3 FX_MODEL/devices/tests_fm_gate_b_repro_king_exit.py
cd ~/Desktop/quant_research/multi_asset/exports/research/retrain_2026-09/v4_chain_2026-09-09
/usr/bin/python3 tests_pipeline_gates.py
```

---
## 7. 补充(独立复审第四轮 7a05b4f4, 2026-09-17): RFR-RECOVERY + B14 真实 run + 两处文字收窄

### 7.1 RFR-RECOVERY(P2, 执行器)—— 未知仓位恢复可读后被留在减仓参考之外
- **核实**: 我在 cdfc06b 上按复审序列实跑 NaN→10→10→5: 锚 2 起 0 单、0 告警、`derisk_unknown=[]`、参考仍 `{}`、`stale_ref_unknown` 只写不读 —— 复审表格逐字复现。该静默在 facdf24 就存在(丢 NaN 后同样不在参考里), 第三轮修复没把恢复路径想完。
- **恢复规则(事先写进 `_scale_to` docstring, 按复审边界: 不把缺参考当 0, 不臆造陈旧期起点数量, 采用时点/比例预先写清防重试缩基)**:
  | 情形 | 规则 | 可见性 |
  |---|---|---|
  | 未知→有限 | 本次陈旧期内**第一次有限读数**作「迟到参考」, **只设一次、永不降低**; 从该锚起按 frac 减仓 | `derisk_recovered`, `state.stale_ref_late[sym]{value, frac_at_adoption, reason}`, HIGH 告警明说「不是陈旧期起点的真实数量」 |
  | 未知→缺席(=0) | 解决为平, 不下单 | `derisk_resolved_flat`, HIGH 告警 |
  | 已知→未知→恢复 | 沿用**原**参考, 减仓恢复 | 未知期间每锚具名 `derisk_unknown` + HIGH |
  | 快照时缺席→之后出现 | 同迟到参考(reason `absent_at_snapshot`) | 同上 |
  | 仍未知 | 不采用、不减、每锚持续具名告警 | `derisk_unknown` + HIGH |
  为什么采用迟到参考而不是只告警不减: 陈旧期把一个名字留在全敞口直到阶段结束, 违背梯子的目的。~~开仓已停, 迟到读数只可能 ≤ 真实陈旧期起点数量, 因此只会多减不会少减~~ **更正(第五轮复审 1004d6d6)**: 开仓虽停, 陈旧期**之前**挂出的旧单仍可能迟到成交, 迟到读数可高可低于从未读到的起点数量, 减仓量可能大于或小于比例量 —— 这是**恢复政策选择**, 不是推导出的保证。固定迟到参考(只设一次)保留; 若你裁定改为「只告警不减」, 是一处开关, 属你的裁定。
- **证据** `tests_broker_nonfinite_positions.py` **23/23**: B1 未知→有限(锚 2 采用 10, 一单 sell 5.0, 锚 3 读 5 静默) · B1b 读 12 再读 10 参考仍 12(sell 6.0 / 4.0, 不重采用) · B2 未知→缺席 · B3 已知→未知→恢复(原参考) · B4 跨进程(state 经 JSON 往返) · B5 有限对照不变 · B6 持续未知每锚告警; **C7(cdfc06b 对照)**: 锚 2/3 读 10 却 0 单、无未知、无告警、参考空 —— 复审发现复现。
### 7.2 B14 下一锚改为真实 run(复审 §3)
`evaluate` 不带 broker、不执行, 旧「flatten 计数不变」断言无鉴别力 —— 复审对。ev3 改为 `WD.run(broker=vb, state_dir=sd)`: 有标记 ⇒ 无新增 flatten、**其余 99 仓保留**; 无标记正控 ⇒ 新增一次 flatten、**99→0**。`tests_proportional_response` **60/60**。生产者未动。
### 7.3 文字更正
- 本文 §3.2「共同 159 套」→ **161**(159 是 facdf24 基线规模; 复审指出)。
- `HONEST_EXPECTATION` §3.6「只活在未跟踪文件/不可复现」→ 收窄为「尚未全部入库、未按 sha 逐条固化」(C6 已证可恢复, 且复审证据已归档独立分支); §5「从 126 格里挑出来的一格」→「126 格预注册网格中唯一交付的一格」(未完成不证明择优过程发生过)。原句划去保留。
### 7.4 提交与电池
叠加树 `cdfc06b → d580eb5`(`scheduler/anchor_loop.py` + 两份测试; 收据 `receipts/STACKED_RFR_cdfc06b_to_d580eb5.diff` 227 行 sha8 c1d98f62); 研究仓 `41ee91c3 → (本节)`。电池(01:05:00Z→01:23:27Z, head `d580eb5`, `/usr/bin/python3` 3.9.6): 收据 `receipts/STACKED_BATTERY_20260917T010500Z.log`(sha8 dd38c901)。**157 绿 / 3 红 / 1 UNAVAILABLE, RC=1(既有红仍在)。** 相对 22:42Z(157/3/1, cdfc06b): **161 套退出码逐套件零差异**, 新红 0; 本轮改过的 `tests_broker_nonfinite_positions`、`tests_proportional_response`、`tests_signal_and_loop` 均 0。余红同前: 真漂移×2 · 本机 nosleep · 无 .env(UNAVAILABLE)。ENVRED-2 计数与前两次逐项相同(1986 / 47 / 15 / 无 env), audit 年龄随钟 20.32h。同样按复审读法: 证明已执行验收集合无退化, 恢复路径反例由 B1–B6/C7 覆盖, 不在电池断言里。零部署, 生产仍 ef60f85。

### 7.5 第五轮复审(1004d6d6, 2026-09-17)收口与两处更正
- 复审接受恢复修复与 B14 验收, 独立验证 27 条断言(恢复 / 重试 / 空头对称 / 状态保存恢复)通过, broker 23/23、proportional 60/60 复跑一致, 两次电池 161 套退出码完全一致(157/3/1)。**未发现新的阻断性执行器问题, 可以收口。**
- 更正 1(已改 `_scale_to` docstring + 本文 §7.1): 「开仓已停 ⇒ 迟到读数必 ≤ 起点」不成立(旧单可迟到成交); 迟到参考是**恢复政策选择**, 保留固定规则, 写明可选替代。
- 更正 2(已改测试): C7 的 cdfc06b 对照缺席时原脚本仍落到 ALL PASS —— 与 King 测试同一形态; 现改为 `CONTROL UNAVAILABLE` exit 3(对照缺席演练实测 rc=3)。本次对照在场, 23/23 有效。
- 提交: 叠加树 `d580eb5 → 6661ea3`(docstring + 测试出口; 收据 `receipts/STACKED_RFR5_d580eb5_to_6661ea3.diff`), 研究仓 `c66c2146 → 47576786 → (回填)`; 电池 05:05Z 窗待回填。
- **代码收口 ≠ 部署条件满足**(复审明言, 接受): 真漂移(`drift_gate`/`tests_drift_gate`, pilot_metrics 研究副本 vs 上游, 按方向审后同步、不削弱门)、防休眠证据(`tests_entrypoint_wiring`, NOSLEEP-1 有界查询)、运行环境凭据加载(`tests_env_loading`, 生产 .env 在生产树验收, 不向研究员提供凭据)三项**仍需验收**, 之后由你按原协议决定合并与部署。零部署, 生产仍 ef60f85, 无新收益结论。

### 7.6 部署(2026-09-17 02:06Z, 用户裁定)
运行树 `~/dl_quant_live`: ef60f85 → **6661ea3** = origin/main(push + pull --ff-only; runbook `docs/RUNBOOK_deploy_executor_6661ea3_2026-09-17.md`)。本文此前所有「零部署 / 生产仍 ef60f85」表述自此作废。生产电池 158/3/0(`receipts/PROD_BATTERY_20260917T020706Z_6661ea3.log`; alarm_digest/env_loading 转绿, 新红 0); 漂移 re-vendor 完成, 漂移门 exit 0; 余红 nosleep(NOSLEEP-1)。首锚 04:00Z(04:24Z 交易)验收随后回填。
