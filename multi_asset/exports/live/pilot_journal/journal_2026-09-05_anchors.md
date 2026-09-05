> **创建:** 2026-09-05 01:5xZ | **Session:** b9646a9e | **状态:** 只追加(每锚深查收据) | **作废条件:** 无(日记)

# 2026-09-05 逐锚深查日记(实盘书零接触, 只读)

## 00Z 锚(1788566400)深查(01:39–01:55Z, 全深度模板)
- ① 守护: shadow_loop_v3 PID 58281 = shadow.lock 58281(自 09-04 11:46Z kickstart, 13h53m); combo_live_daemon.sh 30944 = combo_live_daemon.pid 30944; sidecar_daemon.sh 30943 在。heartbeat OK 00:20:28Z。
- ② 信号: status OK, coverage 1.0, members 400, sel 234, w3 [0.1758,0.1177,0.7065] → 掩码 king 0.1993(target_combo w3_masked 0.19925 算术一致), turnover 0.916%, forced_exit 0, fund_updates 457(00Z 结算锚, 稳态 ~453), fetched 450 missing 0, booster 8d79186b, runtime 264s; combo_live_status anchor 匹配/ok/reader_ok, n 232, gross 0.7962; kc/fc=own, f10 打分 400; FTRIM 8/8 名(含 ONG), check_ftrim_anchor PASS; sidecar 干跑 PASS(king 自平价 4e-10); 反事实改写 20.3%(16Z 20.1 / 20Z 20.5 / 00Z 20.3, 台阶不变)。
- ③ 漏斗(A1788567839): 466 单 = skipped_min_notional 228 / partial_expired 161 / venue_reject 50 / filled 20 / no_chase_arm 7; maker 294 / topup_taker 172; behind 占比 0.44; from_reject 11; fills 去重 201; maker 成交额占比 **0.848(<0.90, 与拒单高相关; 12Z 0.803 亦)**; 成交额 4,582 USDT = 换手 2.8%; 费 1.01 USDT = 2.21 bps(带内上沿)。**拒单率(告警口径 X/Y)近 7 锚: 23.8/20.3/31.4/42.0/47.2/17.1/37.6%**, 账本 L351 跟踪规则"持续 >40% ⇒ 升级": 未满足(两锚 >40% 后回落), 继续跟踪。
- ④ 记账: venue_gross 163,522 = 1.963×NAV 83,314(target_gross 163,433, 差 0.05%); **net/gross +1.52%(第 6 锚 >1%; 序列 +0.92/1.10/1.14/1.45/1.34/1.58/1.52, 未升档、非连升)**; 未成交残差按边: 买未成 789 / 卖未成 610(净 +1,400, 方向与 venue 正净额相反 ⇒ 正净额非来自未成交空头); 被扣留名(add_blocked 4)venue 净 +24 可忽略; 00Z 结算 FUNDING_FEE n=255 合计 **−16.47 USDT**(收 3.28 / 付 19.75; 20Z −11.35); daily_nav 20260905 首行 NAV 83,314.51(较 09-04 −204.0, 09-04 全日 −438.7); phase_C anchors_row/readback 255/daily_nav 齐, per_name_stop stopped 4(CYS/MAGMA/RIVER/TRIA) cooldown 6; anchor_runs.log 末行 anchor done rc=0 00:53:56Z; guard twin AGREE(ledger-only; nav row stale) eq 83,343.28 day_twin −0.177。
- ⑤ 执行质量: 本锚 fills 尚无 +60s 标记(markout 回填 pending 17,158, 本锚写 5, request_budget 停; 累计 3,045/20,195 = 15%)⇒ 尺寸梯度本锚待回填; attempt_idx>1 的名 172(maker→taker 补单常规), 单名最多 3 单; venue_rate 峰值 938/2400, 限流计数差值告警(+798/分, CloudFront 边缘 IP)为已知信息项。
- ⑥ 告警核对: "撤名残差 −9,777 = −5.87% 由 BTCUSDT/ZORAUSDT" 每锚复发(48h 12 次), 文案与算术不符已在账本 L351 记录(实为 untradable 通道整体); position reconcile 6 名(前两锚 20/9)采用场所真相; 34 名 maxNotionalValue=0 reduce-only(退出通道, alarm_text≠source)。**无需处置; 回滚缺省 king 形态未触发。**
- ⑦ regime 仪表盘 00Z: 旗标无; σ_fund 7.3, fund 席位 0.80, IC_fund 0.007, FTRIM 反事实 +0.207 bps; 30 锚 sleeve: L|pos +1,951 / S|pos −1,037 / S|deepneg −658 USDT; 规则 R1–R4 无触发。
- 勘误(05:0xZ, 成本标定): 09-03 16Z 日记行的"−5022 拒单 76%"定义不明, 按单腿 36.2%(79/218)/按额 36.6%(health_check/calib/REPORT.md); 该行不作为引用来源。

## 04Z 锚(1788580800)深查(05:39–05:45Z, 全深度模板)
- ① 守护: shadow_loop_v3 58281 = shadow.lock; combo_live_daemon 30944 = pid; sidecar 30943 在; heartbeat OK 04:20:31Z。
- ② 信号: OK, coverage 1.0, members 400, sel 233, w3 [0.1696,0.1247,0.7057] → 掩码 king 0.1938(算术一致), turnover 2.0%, **forced_exit 2 名**, fund_updates 357(4h 锚稳态 ~353), fetched 450/缺 0, booster 8d79186b, runtime 267s; 上锚(00Z)score gross +56.8 / net +55.1 bps(单位书, 强正锚); combo 锚匹配/ok/读者验收, n 231, gross 0.7939, kc/fc own, f10 400, FTRIM 10/10 验收 PASS, sidecar 干跑 PASS; 反事实改写 20.5%(20.5/20.3/20.5 台阶不变)。
- ③ 漏斗(A1788582240): 497 单 = min_notional 226 / 部分过期 180 / 场所拒 61 / 成交 23 / 无臂 7; maker 306 / taker 补单 191; behind 0.42; **拒单 61/306 maker 单 = 19.9%(告警口径 61/126 = 48%; 近 5 锚 42/47/17/38/48%)**; **maker 成交额占比 0.830(<0.90, 12Z 0.80 / 00Z 0.85 / 04Z 0.83 三次)**; 成交额 11,915 USDT = **换手 7.1%(高于 2–5.5% 稳态, 本锚重平衡量大)**; 费 2.69 USDT = 2.26 bps(带内上沿); 未成交 买 1,865 / 卖 1,472。
- ④ 记账: venue_gross 167,983 = 1.961×NAV 85,641(target 167,940, 差 0.03%); **net/gross +1.65%(第 9 锚 >1%; 序列 …1.58/1.52/1.65, 未达 2%, 未连升三锚)**; 04Z 结算 FUNDING_FEE n=189 合计 −4.76 USDT; **daily_nav 20260905 NAV 85,640.7, 较 09-04 +2,122(+2.5%; 已实现 +1,008 / 未实现 +1,541)**; phase_C 三件齐; anchor done rc=0 04:54:32Z; guard twin AGREE(eq 85,720.8); per_name_stop 停 4 冷却 6 不变。
- ⑤ 执行质量: 本锚 fills 无 +60s 标记; markout 回填仍被 request_budget 截停(本锚写 4, pending 17,432, 累计覆盖 ≈15%)⇒ 尺寸梯度不可评; 单名最多 3 单。
- ⑥ 告警核对: position reconcile 15 名(前三锚 20/9/6)采用场所真相; 撤名残差 −11,926 = −6.96%(文案与算术不符, 账本 L351 已记); 36 名 reduce-only(退出通道); −5022 拒单 48% HIGH(见 ③, 跟踪项)。**无需处置; 回滚缺省 king 形态未触发。**
- ⑦ regime 仪表盘 04Z: 旗标无; σ_fund 9.7, fund 席位 0.81, IC_fund +0.081, FTRIM 反事实 −0.50 bps; R1–R4 无触发。
- 关注项汇总: (a) −5022 拒单率近 5 锚 3 次 >40%(告警口径), 账本 L351 升级条件"持续 >40%"接近; (b) maker 占比三次 <0.90; (c) net/gross 第 9 锚 >1%; (d) markout 回填覆盖停在 15%, 逆向选择成本(体检最大未知)因此定不下来 —— 提高回填 request budget 属执行器改动, 待用户字。

## 07:0xZ 执行器改动上线: markout 回填(用户字 09-05 "提高回填预算"; 非书行为)
- 实盘仓 `bc099d7`(safe_commit, 电池 125/125 全绿, 已推送): `ops/backfill_markout.py` 三处 —— 标记窗口 5s → 60s(`mark_lag_s`/`mark_window_s` 逐行落盘, 严格口径可按 lag ≤5s 筛); 窗口内确无成交的行写入终止行(`mark_status=no_trade_within_window`, mid 保持 None = 未测, 退出待办集, 不再每轮重查); 锚间 launchd 任务预算 240 请求/300s → 900/1800s(PACE 2s 不变 ⇒ 600 权重/分; 锚内路径仍受其自身 deadline 约束)。新增 `live/tests_markout_window.py`(SUITES + gate_coverage 边界自述); `tests_guard_coverage` f3 期望改为终止语义(17 → 0 请求)。
- 根因收据: 覆盖停在 15% 不是预算不足, 是稀薄名 5s 窗内无成交且"未落盘"导致每轮重查同一批(240 请求换 4–5 个标记)。生效: 下一锚(08Z)锚内路径 + 下一次锚间任务(17:05 本地 = 09:05Z)。
- 未动: E-0905-F(COMMISSION 分项 tranId 去重碰撞)待用户字。

## 09:1xZ 执行器第二次改动上线: markout 回填的 2 天窗口规则(E-0905-G; 非书行为)
- 根因(08:54Z 探针, VERIFIED): 交易所 `aggTrades` 按时间检索只开放最近 2 天(HTTP 400 −4166 "Search window is restricted to recent 2 days only"); 更早的窗每请求必败, 被吞成"截断"再逐名重试再败, 不落盘 ⇒ 每轮预算全部花在永远答不了的日子(待办 17,660 笔, 2 天窗内仅 1,856)。08Z 锚在第一次改动(bc099d7)下的实测: 每日 25 请求, written=0, terminal=0 —— 证明第一次改动不触及真因。
- 实盘仓 `6a01b5a`(safe_commit, 电池 125/125): 回填前按 `now − (fill_ts+60s) > 47h` 切分, 超窗成交写终止行 `aggtrades_window_expired`(不发请求); `marks_for_group` 识别 −4166 ⇒ 整组终止, 不逐名重试; 汇总计 `n_expired`; 测试 (e)(f) 新增。生效: 下一锚(12Z)与下一次锚间任务(13:05Z)。预期: 2 天窗内的新成交在下一轮几乎全部获得标记, 覆盖从此按锚增长。
- 历史 17.6k 笔: pod2 从交易所公开每日 aggTrades 档案(CDN, 免限速)按同一定义计算 +60s 标记(含 5s 严格变体与延迟), 产物 marks.json → 导入脚本以 supersede 行写回账本(待写, 经 safe_commit)。

## 09:37Z 账本回写: 历史 +60s 标记导入(实盘仓 `74aca9b` 导入脚本, 电池 126/126; marks.json sha 12c5a099…)
- 干跑与实跑一致: 写入 15,802 个标记(supersede 行, 来源 data.binance.vision 每日 aggTrades, 逐行带档案 sha 与延迟)、73 个"窗内无成交"终止行; 1,102 笔已由执行器自身路径标记(2 天窗口修复已见效); 681 笔 09-05 等档案发布(`--resume`)。单一写者: 锚间回填任务退出后执行。
- **覆盖(去重 20,712 笔): 已标 19,956 = 96.3%(档案 15,802 + 场所 4,154), 终止 75, 待办 681**(导入前 ≈15%)。
- 成交额加权 maker markout60 −2.22 bps [−3.47, −0.87](买 −1.40 / 卖 −3.04), taker 补单 +1.11(不显著); 全成本 3.92 bps/单位换手(费 2.25 + 逆向 1.66)⇒ 每锚 −0.12 bps of gross ≈ 2× 下 −5%/年; "砍六成"情景作废(体检 §7 已改)。

## 08Z 锚(1788595200)深查(09:39–09:45Z, 全深度模板)
- ① 守护: 生产者 58281 = shadow.lock; combo 30944 = pid; sidecar 30943; heartbeat OK 08:20:44Z。
- ② 信号: OK, coverage 1.0, members 400, sel 237, w3 [0.1677,0.1283,0.7040] → 掩码 king 0.1924(算术一致), turnover 1.3%, forced_exit 0, fund_updates 457(8h 结算锚 ~453 ✓), fetched 450/缺 0, booster 8d79186b, runtime 279s; 上锚(04Z→08Z)score **gross −20.0 / net −21.9 bps**(单位书, 亏损锚); combo 锚匹配/ok/读者验收 n 234 gross 0.8015; kc/fc own, f10 400; FTRIM 8/8 PASS; sidecar 干跑 PASS; 反事实改写 20.3%(台阶不变)。
- ③ 漏斗(A1788596640): 483 单 = min_notional 225 / 部分过期 138 / 场所拒 **87** / 成交 31; maker 325 / taker 补单 158; behind 0.41; **拒单 87/325 = 26.8%(告警口径 87/187 = 46.5%; 近 6 锚 42/47/17/38/48/47%, 4/6 ≥40% ⇒ 账本 L351 "持续 >40%" 升级条件已触及)**; **maker 成交额占比 0.791(第 4 次 <0.90, 新低)**; 成交额 5,781 = 换手 3.4%; **费 2.37 bps(超 1.80–2.3 带上沿, 系 taker 补单占比升)**; 未成交 买 1,489 / 卖 1,095。
- ④ 记账: venue_gross 168,221 = 1.961×NAV 85,768(target 168,141 ✓); **net/gross +1.79%(第 10 锚 >1%; 序列 …1.52/1.65/1.79 连升两锚)**; 逐名分解(readback 258 名 vs target 文件×gross): venue 多 85,614 / 空 82,607; 偏离集中在止损/冷却名: 目标做空但不能开的 EGLD −900 / ZORA −850 / ARB −681 / USELESS −816 / BTR −685(冷却 6 名)⇒ 缺空 ≈ +3.9k; 目标做多但已停的 MAGMA +1,774 / RIVER +1,635 / TRIA +1,235 ⇒ 缺多 ≈ −4.6k; 正偏离合计 +16.6k / 负 −6.2k ⇒ **正净额主要来自止损/冷却层禁止再入的名(信号要的仓不能开), 不是成交缺口**; 08Z 结算 FUNDING_FEE n=256 合计 −12.36 USDT; daily_nav 09-05 NAV 85,767.7(+2,249, +2.7% 日内; 已实现 +1,211 / 未实现 +1,474); phase_C 三件齐(08:44Z), anchor done rc=0 09:01:02Z; guard twin AGREE(eq 85,730.7); 09:21Z 另有一条 phase_C SKIPPED_NON_LIVE = 电池干跑锚, 非实盘路径。
- **止损触发: DASHUSDT 08:43Z, 深度 −31.8% 连续 2 终锚(04Z 计数 1 → 08Z 触发)⇒ flatten_only(maker 出场不追), 7 天禁入; 持仓 −489 USDT(目标 −506); 停止名 5(CYS/DASH/MAGMA/RIVER/TRIA), 冷却 6。**
- ⑤ 执行质量(账本 96% 覆盖后首次可评): **maker 尺寸梯度三桶(成交额加权 markout60): 小 −1.16 / 中 −1.52 / 大 −3.44 bps, 全负且随尺寸变差**(模板"三桶非负"不成立, 与全量逆向选择读数一致); taker 补单 +0.24; 08-26 以来 −3.31。本锚 fills 标记 9/235(锚内回填在 6a01b5a 前运行), 下一锚起应接近全量。
- ⑥ 告警核对: 撤名残差 −11,841(文案与算术不符, 已记); 36 名 reduce-only(CAKE 减仓中); 限流计数差值 +625(已知); −5022 拒单 46.5% HIGH(见 ③)。**无需处置; 回滚缺省 king 形态未触发。**
- ⑦ regime 仪表盘 08Z: 旗标无; σ_fund 6.0, fund 席位 0.81, IC_fund +0.009; R1–R4 无触发。
- **升级项(给用户):** −5022 拒单率 6 锚中 4 锚 ≥40%, 账本 L351 的候选处置(提交前重取盘口/按批次刷新 mid)属执行器改动, 需用户字; 关联 maker 占比降至 0.79、费 2.37 bps。
