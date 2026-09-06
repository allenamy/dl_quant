> **创建:** 2026-09-06 01:5xZ | **Session:** b9646a9e | **状态:** 只追加(每锚深查收据) | **作废条件:** 无(日记)

# 2026-09-06 逐锚深查日记(实盘书零接触, 只读)

## 00Z 锚(1788652800)深查(01:41–01:5xZ; 定时 01:09Z 未触发 —— 会话当时非空闲, 手动补做一次, 不复核; 巡检脚本 tools/inspect_anchor.py)
- ① 守护: 生产者 10900 = shadow.lock = launchd com.hsy.shadowloop(播种后 kickstart 的 PID, 已跑 12h53m); combo 30944 = com.hsy.combolive; sidecar 30943 = com.hsy.sidecar; launchd 其余项(markout_backfill/regime_weekly/c2shadow/stopoverlay/regime_dash/anchor_report)在。
- ② 信号: OK, coverage 1.0, members 400, sel 242, **fund_updates 457(00Z 8h 结算锚 ✓)**, forced_exit 1, fetched 450/缺 0, runtime 262.5 s; w3 [0.2773, 0.1163, 0.6063] ⇒ 掩码 king **0.3138**(播种后第三锚, 验收带 [0.28, 0.32] 内 ✓); 上锚(20Z→00Z)score gross −11.96 / net −13.79 bps(carry +1.70, cost 0.13; 单位书); combo rc=0 **00:21:03Z**, n 241, gross 0.8057, kc/fc own, w3m [0.3139, 0, 0.6861] 算术 ✓, ρ(kc,fc) 0.970, book_form combo_v2main_norev24, φ 0.45; 反事实改写 20.6%(12Z 18.9 / 16Z 19.3 / 20Z 20.5 / 00Z 20.6: 连续 >+0.2pp 仅 16Z→20Z 一次, 台阶 19–20% 上沿, 不升级)。
- ③ 漏斗(A1788654240; 执行器 wake N+24, readback 00:24:02Z): 486 行 = min_notional 201 / partial_expired 156 / venue_reject 64 / filled 51 / no_chase_arm 14; **首次 −5022 58 / 首次落单 135 ⇒ 真实率 30.1%**(升级线 40%; 旧口径 46.7%; 日志新口径行 ✓); **重挂随机实验第四锚: 候选 27 全部重挂(落单 21, 再拒 6), direct 31(累计 direct 104/1500), 行标记 requote 52 / direct 31 / exempt 2 ✓**; behind 占比 0.49 ✓; chase 87 / no_chase 69 / forced 0(中性带内, C 层 fill 空); fills 264 笔 7,289 USDT = **换手 4.35%**(÷ venue gross 167,708; 16Z/20Z 的 6.27/5.51 系席位重排, 已回稳态带内 ✓); **maker 占比 0.714 —— 播种后三锚 0.64 / 0.61 / 0.71 连续 <0.85, 按 20Z 登记规则记为结构性观察项(非事故)**: 分解 = "37 个 maker 被 −5022 拒→taker 补单" = direct 臂 31 + 再拒 6(重挂随机实验的设计成本, p .5, 读数点 14 天前不评臂间差; 实验前基线 0.79–0.85)+ partial_expired 补单; 处置 = 无(进实验读数与 30 锚 maker 占比对照)。
- 费: fills 佣金 264 笔全部 commission_asset=BNB(08-05 用户配置 BNB 抵扣; 执行器 fee_asset_baseline assets=[BNB], 逐腿换算在 venue_fills c05f1f5); **巡检脚本旧版把 BNB 数量当 USDT 求和 ⇒ "fee 0.00 USDT" 假读数 = 脚本盲区, 本次已改为按资产分列(不换算)**; 本锚费 bps 不报(此前各锚"费 x bps"来源非本脚本, 不追溯)。
- ④ 记账: readback 每名 held+targeted(末行 ZROUSDT 00:24:02Z); position reconcile 5 名 adopting venue truth(例行 5–15); **venue gross 167,708 = 1.971×NAV 85,087; net/gross +1.25%(第 14 锚 >1%, 机制同前: 止损 5 + 冷却 7 名的目标仓不能开)**; NAV 路径 20Z 85,911 → 00Z 85,087(−0.96%); 00Z 结算 funding −10.34 USDT; 日内(00Z 起)已实现 −24.1 / 未实现 +311; wallet 84,776; anchor done rc=0 **00:53:39Z**; rate_timeline 3,234 行; 限流计数差值 +780 权重/分钟(峰值 843/2400, 同族)。daily_nav realised_by_type 的 COMMISSION 行为资产混合求和(BNB 数量), 数值 −0.001 不是 USDT 费 —— 既有已知盲区(pilot_metrics L163 注释), 只记不改。
- ⑤ 止损: **HEMIUSDT 00:24:09Z per_name_stop 触发(深度 −33.7%, 连续 2 个终锚读回 ≤ −30%)⇒ flatten_only(maker 出场, 不追), 出场后 7 天禁入, 条款 cf40ea21, 30 天反事实对照待回填**; per_name_stop stopped 5 / cooldown 7(20Z: 4 / 7); 撤名 3: BTC / DASH / ZORA(撤名残差 −11,900 = −6.98%, 文案≠算术, E-0903-D 已登记)。
- ⑥ 告警核对: 重整后 5 名跨 min_notional 门槛(CYS/MAGMA/ONG/RIVER/TRIA, 只报); 39 名 reduce-only(add_blocked 含 HYPE/TRIA); "37 个 maker 被 −5022 拒" = direct 31 + 再拒 6 ✓(实验预期); REGIME 周报 00:33Z(sig_fund 近 7 天均 12.4 ≥p75, 2026 均 16.7 —— 仍在宽档有利区); 执行器 external_book producer=combo_stage ✓(前缀门 0ae54cc 未启用, 无 fallback 键)。**无需处置; 回滚未触发。**
- exec_n6 §2 P4 时序参考(实盘 N+16 形态, 本锚): 生产者 runtime 262 s ⇒ target ≈ N+20:22; combo rc=0 N+21:03; 执行器 wake N+24:00。沙箱(offset 1, 预算 480, PID 69679)与探针(PID 69646)均在等 04Z(loop.out `next 04:01:00`); 实盘生产者 10900 未动。
- 未算项: markout60 分桶(脚本不含; 累计见 09-05 20Z 行); 08-26 以来数列下锚补。
- 待 04Z: 探针 P1(04:00:10Z klines / 04:00:20–04:04:00 fundingRate 27 名)+ 沙箱 P2(04:01Z 起, 与实盘 target 逐名比对)读数 04:25Z(cron 0075725c)。
- **[01:5xZ 增量, 同锚重复触发(定时延后), 只报增量]** ① 守护句柄: shadow.lock 10900 = 进程 ✓, fea171/combo_live_daemon.pid 30944 = 进程 ✓, sidecar 30943 ✓。② `state/anchor_runs.log` 末行 anchor done rc=0 00:53:39Z ✓; venue_rate 峰值窗权重 843, 订单峰值 220/分钟。③ 尺寸梯度 markout60(本锚 maker 成交 178/183 已回填; 桶 = 本锚成交额三分位, 界 12/30 USDT, 成交额加权): 小 +0.88 / 中 +1.97 / 大 +9.94 bps, 三桶非负 ✓(桶界按本锚分位, 与 09-05 各锚桶界未必同; 单锚观察)。④ **guard_twin(launchd com.hsy.guardtwin, 每 20 min; 此前日记从未读过它, 本锚起纳入)**: 01:01:00Z **DISAGREE** 「DAY twin −0.426% vs daily_nav-arith −0.959%」(差 0.53pp, 容差 0.5pp), 01:21/01:41Z 回 AGREE(ledger-only; nav row stale)。溯源(读码 `~/guard_twin/guard_twin.py` L288–325): arith = 00Z 锚 NAV(00:45Z 评估)对 09-05 最后一行 20Z 锚 NAV 85,911, 窗 ≈20:45→00:45Z; twin = 当前权益对自家 23:40:52Z 快照, 窗 23:40→01:01Z; **两窗不同, 差额 = 20:45→23:40Z 的书变动**(00:00:56Z 权益 85,328 已较 20Z NAV −0.68%)。账本恒等按资产 gap: USDT −5e-10 / BNB −9e-15(wallet = Σincome 精确), closed_account_gap 0 ⇒ **记账无缺陷, 属窗口口径贴容差线**(历史每日约 1 次同类, 09-05 04Z 「INPUT equity vs daily_nav −0.63pp」同族)。只记不改, 不页报。⑤ 沙箱 69679 / 探针 69646 仍在等 04Z; 实盘生产者未动。**无需处置。**

## exec_n6 读数 #1: 04Z 锚(1788667200; 04:25–04:3xZ; cron b323c726; 只读)
- **P1 数据到位 GREEN(VERIFIED probe_log.jsonl)**: klines 收盘于 N 的 bar 在 N+10.5 s 时 10/10 在; fundingRate 27 名中应结算 15 名(4h 名 12 + 1h 名 3)**全部在各自第一次查询时已在**(4h 名 N+22–35 s, 1h 名 N+51–53 s = 探针轮内逐名 1 s 顺序延迟, 非到位延迟), 后四轮无一消失(无抖动), 无错误; 12 名 8h 结算名无 N 行 = 预期(04Z 非 8h 结算点)。100% 到位上界 = N+0:53(首次查询时刻)。读数脚本首版按 t_after 分桶把不同名混桶, 打出假 RED; 已改为逐名首见逻辑(本次提交), 08Z/12Z 读数用新版。
- **P2 沙箱 vs 实盘: 恒等 GREEN / 运行时间 RED**: members 400 / sel 242 / coverage 1.0 / fund_updates 354(base 64)/ forced_exit 0 / fetched 450 / missing 0 全同; w3 [0.2860, 0.1167, 0.5973] 相同; king 形态 target 238 名 max|Δw| 0, Σ|Δw|/gross 0, universe_sha 同; 沙箱 anchor_error/anchor_skip 无; 探针无 429/−1003, 探针权重最大 73; 沙箱 weight_used 865。**沙箱 runtime 243.5 s > 门 210 s**: 预算 240→480 没有缩短运行(实盘同锚 235.5 s @240 vs 沙箱 243.5 s @480), 瓶颈是逐请求延迟(≈804 次请求 × ≈0.3 s), 不是限速器(865 权重 / 243 s ≈ 214/分钟 ≪ 480)。
- **P4 时序 RED(冻结补救 = 执行器 offset 7)**: 沙箱 target 04:05:03Z = N+5.05 min(data_max_ts = N ✓, 最新数据 ✓); 实盘 target N+19.92, combo rc=0 N+20.55(延迟 38 s); 投影 offset 1 下 combo 落盘 N+5.68 min > N+5:30。
- **判定: P1 GREEN / P2 恒等 GREEN + 运行时间 RED / P4 RED。不做任何换装动作。** 沙箱 69679 / 探针 69646 / 实盘生产者 10900 未动; 实盘链路未变(生产者 N+16, 执行器 N+24)。
- 前瞻(INFERRED): 08Z 为 8h 结算锚(457 次资金费请求, 实盘 16Z 同形态 runtime 316 s), 若延迟主导, 沙箱落盘约 N+6:20, combo 约 N+7:00 ⇒ offset 7 也不够。⇒ 修正提案两条(写入 PREREG §2 末, **待用户字, 未生效**): (a) 运行时间门 ≤ 270 s 改为「投影 combo 落盘 ≤ N+(offset − 0.5) min」并取 offset 7; (b) Phase 2 = 生产者拉取并行化(4 线程, 权重仍 ≤ 480/分钟), 另立预注册 + 三锚沙箱验证, 目标落盘 ≤ N+2:30。
- **[04:4xZ exec_n6 Phase 2 启动(用户字「按最佳路径执行, 确保效果最优」)]** 根因 = 生产者顺序拉取 ≈800 次请求 × ≈0.23–0.30 s, 不是数据不到位, 也不是限速预算。取数层 v2(并行 K 线 6 线程 + 无 symbol 的批量资金费分页 + 预算 720 + 超时 10 s; 旋钮缺省 = 逐字现行为, diff 133 行)独立收据(`exec_n6_2026-09-06/v2/fetch_layer_test.json`, VERIFIED): 450 名 K 线顺序 104.5 s(232 ms/次)vs 6 线程 22.6 s, 行数据 sha 相等, 0 错误; 批量资金费 8h 窗 2 页 1241 行 767 名, 与逐名 60 名逐行相等。附带事实: fundingRate 接口与 fundingInfo 共用独立 500 次/5 分钟配额, 现行逐名 354–457 次/锚贴线; 在役 urlopen 无超时。**沙箱已换 v2**(旧 PID 69679 按 PID 终止, 新 PID 93793, 旋钮 6/720/1/10, offset 1, 08:01Z 首跑); 探针 #2(PID 93815)覆盖 16Z; 实盘生产者 10900 未动。预注册 `PREREG_deploy_exec_n6_phase2_2026-09-06.md`(48535bc, sha 225af161): 三锚 08/12/16Z 门 = 恒等 + runtime ≤ 90 s + 投影落盘 ≤ N+2:30 + 探针; 执行器 N+3 + 前缀门宽限 4(硬截止 N+7); 换装窗 17:05Z, 首锚 20Z 验收。Phase 1 的 offset 7 提案作废(被 Phase 2 取代)。

## 04Z 锚(1788667200)深查(05:39–05:4xZ; 定时 05:09Z 未触发(会话忙), 手动补做; 脚本 tools/inspect_anchor.py)
- ① 守护: 生产者 10900 = shadow.lock = launchd(16h52m); combo 30944 = pidfile; sidecar 30943; 三项在。
- ② 信号: OK, coverage 1.0, members 400, sel 242, fund_updates 354(4h 整点 ✓), forced_exit 0, fetched 450/缺 0, runtime 235.5 s; w3 [0.2860, 0.1167, 0.5973] ⇒ 掩码 king **0.3238**(播种后第四锚, 略超验收带上沿 0.32 —— 验收只对首锚, 后续按 msharpe 自然漂移, 只记); 上锚(00Z→04Z)score gross −67.5 / net **−69.2 bps**(单位书; 实盘 −88 bps/gross, 见 RESULT_giveback_attribution_live); combo rc=0 04:20:33Z, n 241, gross 0.8103, kc/fc own, w3m [0.3238, 0, 0.6762] 算术 ✓, ρ(kc,fc) 0.967; 反事实改写 20.8%(00Z 20.6 → 04Z 20.8, +0.2pp; 台阶 19–21% 内, 未连续三锚 >+0.2pp, 不升级)。
- ③ 漏斗(A1788668640): 486 行 = min_notional 200 / partial_expired 147 / venue_reject 73 / filled 53 / no_chase_arm 13; **首次 −5022 65/186 = 34.9%**(升级线 40%, 今日最高; 旧口径 47.7%); **重挂随机实验第五锚: 候选 34 全重挂(落单 26, 再拒 8), direct 31(累计 direct 135/1500)**, 行标记 requote 66 / direct 31 / exempt 2 ✓; behind 占比 0.477 ✓; chase 84 / no_chase 63; fills 269 笔 8,870 USDT = 换手 5.30%(稳态上沿); **maker 占比 0.693(播种后 0.64/0.61/0.71/0.69, 第四锚 <0.85, 结构性观察项延续: direct 臂 31 + 再拒 8 进 taker 补单)**; 佣金 0.003057 BNB(按资产分列)。
- ④ 记账: readback ZROUSDT 末行 04:24:02Z; position reconcile 13 名 adopting venue truth(例行带 5–15 上沿); venue gross 165,181 = **1.977×NAV 83,568**; net/gross +1.26%(第 15 锚 >1%, 机制同前); NAV 00Z 85,087 → 04Z 83,568(**−1.8%; 09-05 20Z 峰 85,911 起 −2.7%**); 日内已实现 −456(REALIZED −434, funding −22), 未实现 −774; anchor done rc=0 04:52:48Z; 限流差值 +1,203 权重/分钟(峰值窗 1,298/2,400, 高于前几锚的 780–988, 同族: 差值归属 CloudFront 边缘, 未定); 停止 5 / 冷却 7。
- ⑤ 执行质量: markout60 maker(154 笔)小 +1.72 / 中 +0.41 / **大 −9.87 bps**, 全部 −7.22(大桶拖深: 崩跌锚里大额单被逆向选择; 08-26 以来累计大桶 −4.7 同向); 桶界 13/33 USDT。
- ⑥ 告警核对: **cond2 调查档首次触发 04:45Z(日权益 −2.73% ≤ −2.68%; ALERT ONLY 不停机; 历史 1.8/年, 实盘预期 3–4/年)—— 归因见 `docs/RESULT_giveback_attribution_live_2026-09-06.md`(73b2038): 多头极端正费率名单锚崩跌(4USDT −22.8% / CLO −14.3% / APR −12.9%), 非 BTC 非普跌**; guard_twin 05:01Z AGREE(twin −2.365% vs arith −2.727%, 差 0.36pp < 0.5 容差); 撤名残差 −12,341(文案≠算术, 已登记); 38 名 reduce-only(HEMI 在减); "39 个 maker 被 −5022 拒" = direct 31 + 再拒 8 ✓; 重整后 7 名跨 min_notional(只报)。**无需处置; 回滚未触发。**
- 待 08Z: 8h 结算锚 fund_updates ~457; Phase 2 沙箱 v2 首跑(08:01Z)与 08:25Z 读数; maker 占比是否随 direct 臂比例波动。

## exec_n6 Phase 2 读数 #1: 08Z 锚(1788681600, 8h 结算锚; 08:25Z; 只读)
- **P1 数据到位 GREEN**: klines 收盘于 N 的 bar 在 N+10.4 s 时 10/10 在; fundingRate **27/27 名全部在各自第一次查询时已在**(N+24 s ~ N+56 s = 探针轮内逐名 1 s 顺序延迟), 后四轮无一消失, 无错误。8h 结算锚上所有名(4h/8h/1h 三类)都到位。
- **P2 恒等 GREEN(本次验证的核心)**: 沙箱 v2(并行 K 线 6 线程 + 批量资金费 + 预算 720 + 超时 10 s)与实盘顺序取数逐位相同 —— members 400 / sel 243 / coverage 1.0 / **fund_updates 454(结算锚)/ fund_updates_base 75** / forced_exit 0 / fetched 450 / missing 0 全同; w3 [0.2922, 0.1158, 0.5921] 相同; king 形态 target 240 名 **max|Δw| 0.00e+00**, Σ|Δw|/gross 0, gross_norm 0.855604 相同, universe_sha 相同; 沙箱无 anchor_error/anchor_skip; 探针无 429/−1003。
- **P2 时序: runtime GREEN, 三个子指标 RED**: **runtime 43.5 s**(门 ≤ 90 ✓; 实盘同锚 **290.1 s** ⇒ **6.7×**), `t_klines_s` 24.1(门 ≤ 45 ✓), 但 **`t_fund_s` 16.8 > 门 5 RED**、**`n_err` 5 > 门 0 RED**、**`fund_fallback_n` 8 > 门 5 RED**; 批量本身正常(bulk_ok true, 2 页 1240 行), weight_used 461(实盘 976)。
- **P4 落盘 GREEN**: 沙箱 target 08:01:43Z = **N+1.72 min**(data_max_ts = N ✓); 实盘 target N+20.83, combo rc=0 N+21.52(延迟 41 s); 投影 offset 1 下 combo 落盘 **N+2.40 min ≤ 门 N+2:30 ✓**。
- **判定: P1 GREEN / P2 恒等 GREEN / P2 时序 RED(三项)/ P4 GREEN ⇒ 按冻结判据本锚不合格, 不做任何换装动作。**
- **红项溯源(诊断, 不改判据)**: (a) `n_err` 5 = 461 次请求里 5 次三试全败, 均为资金费逐名回退请求; 它们**未造成任何差异**(fetched 450/缺 0, fund_updates 与实盘逐位同) —— 因为回退名都是"上次结算早于 8h 批量窗"的陈旧名, 本锚无结算。根因 = **我在 v2 里新加的 10 s HTTP 超时**在 6 路并行下过紧(在役生产者根本没有超时, 只会一直等)。(b) `t_fund_s` 16.8 的大部分是这 5 次失败的重试等待(1 s + 2 s × 5 ≈ 9 s)。(c) `fund_fallback_n` 8 是**结构量**: 批量窗设为锚前 8h, 上次结算早于该窗的名必须逐名回退; 我把门写成 ≤5 是拍脑袋。
- **处置(装置修, 判据不动)**: 把 HTTP 超时 10 s → 25 s、批量窗 8h → 26h(逐名筛选仍按 `fundingTime ≥ (last_ts+1)`, 语义不变, 页数上限 6 足够), 重启沙箱, **用同一套冻结门在新的锚(12Z/16Z/20Z)重新验证**; 08Z 这一锚的红读数按原样保留在案, 不追溯改判。**换装决策相应从 16:25Z 推迟到 20Z 锚之后。**

## ★★ 止损触发与全书平仓(08:46:08Z; 事件档, 只读排查)
- **性质: 不是交易所强平, 是执行器自带风控层 §4-2 远端底线**(`live/watchdog.py` `DAY_LOSS_LIMIT_PCT = -4.0`, 口径 [B32] = 当日最后 NAV vs 前一日最后 NAV)。触发值 **−4.12%**(85,910.9 → 82,373.0), 门 −4.0%。收据 `state/live/watchdog/trip_receipt.json`(tripped_at 08:46:08Z, message_sha 0b64d447, 已投递 message_id 1120)。
- **执行与验证(VERIFIED `watchdog/state.json` degradation)**: 顺序 halt_opening → flatten → alert; `stage1_flatten_attempts 1`, `stage1_ok true`, 平仓单 = **IOC reduce-only**(样本 BABYUSDT/ETH…), `stage1b_cancel_state SWEPT`(挂单 0), `stage1_residual {}`(无残留), `stage1_verified_by_reread true`, 读回口径 = 场所账户快照。**post_flatten 读回 268 行全为 0, gross 0**(平仓前 08:24Z 批次: 238 个非零名, gross 162,742)。`reduce_only true`, `stage3_open_halted true` ⇒ **下一锚(12Z)起不开新仓**。
- **日内路径**: 09-05 末 85,910.9 → 00Z 85,087.2(−0.96%)→ 04Z 83,568.4(−1.79%)→ 08Z 82,373.0(−1.43%), 合计 −4.12%; 三个连续亏损锚。
- **归因(实盘账本, 持仓×价差)**: 00Z→04Z **−88.1 bps/gross**(多头侧 −93.2, 空头 +5.1; 4USDT −22.8% = −443 USDT, CLO −14.3% = −274, APR −12.9% = −175); 04Z→08Z **−74.3 bps/gross**(多头 −60.1, 空头 −14.2; BULLA −17.3% = −281, COLLECT −14.5% = −247, EPIC 空头 +9.8% = −129)。**机制与 `RESULT_giveback_attribution_live_2026-09-06`(73b2038)同一条**: 多头极端正费率名连续崩跌, 且第三锚起空头侧也开始被挤; 市场因子仍近零(BTC ±0.12%, 山寨等权 −0.14~−0.50%)。
- **基率对照(`RESULT_giveback_baserate_2026-09-06`, 1c45ef8)**: 在役形态回放 2024→26 的 973 个 UTC 日里 ≤ −4.0% 只有 **2(s42)/ 5(s2027)** 天, 全部在 2025-04/05 ⇒ 约 **1–2 天/年**; watchdog 自述该档 4.5 年 3 次且全在 2024, "长期沉默不代表它坏了"。**本次是设计包络内的罕见事件, 不是新缺陷**; 但回放是结构口径(无 maker 成交滑点/逆向选择), 真实频率只会更高。
- **恢复条件(只读核查, `LIVE_MODE=LIVE bash ops/resume_from_trip.sh --check`, 未触碰任何状态)**: **NOT RESUMABLE —— 触发条件仍成立**(硬门 1/4 拒绝)。该脚本设计为条件仍真时拒绝清除, 无覆盖旗标。日口径按 UTC 日切, **00:00Z 起新的一天, 届时"当日损失"重置**, 条件自然不再成立。
- **当前状态**: 账户全现金(gross 0), 挂单 0, 开仓已停; 生产者/combo/sidecar 照常产出目标文件(只是执行器不开仓); NAV 82,373(日 −4.12%, 09-05 峰 86,489 起 −4.76%)。
- **待用户裁定(不自作主张)**: ① 何时恢复(最早 00:00Z 后, 且需 `resume_from_trip.sh "理由"` 显式执行); ② 恢复后是否维持 2.0× gross; ③ 重建全书的一次性成本(≈163k 名义 × 换手成本, maker 约 2.8 bps ≈ 46 USDT, 若走 taker 约 4.5 bps ≈ 73 USDT, 另加滑点); ④ N+6 Phase 2 换装是否顺延(书已平, 换装本身与书行为无关, 但停机期间换装会让首锚验收失去"正常交易"的对照)。

## 08Z 锚(1788681600)深查(09:5xZ 补做; 该锚即止损事件前的最后一个正常交易锚, 事件本身见上方 ★★ 小节, 此处只报锚级增量)
- ① 守护: 生产者 10900 = shadow.lock; combo 30944 = pidfile; sidecar 30943(三项在)。
- ② 信号: OK, coverage 1.0, members 400, sel 243, **fund_updates 454(8h 结算锚 ✓)**, forced_exit 0, fetched 450/缺 0, runtime **290.1 s**(结算锚拉取多, 与 09-05 16Z 的 316 s 同量级); w3 [0.2922, 0.1158, 0.5921] ⇒ 掩码 king **0.3304**(播种后逐锚 0.3045→0.3086→0.3139→0.3238→0.3304, 单调上行, 已超验收带上沿 0.32 —— 验收只约束首锚, 此后按 msharpe 自然漂移; **登记观察: 席位五锚连升, 若继续升过 0.40 需复看动态席位规则的分母窗**); 上锚(04Z→08Z)score gross −75.1 / net **−77.1 bps**(单位书); combo rc=0 08:21:31Z, n 243, gross 0.8124, kc/fc own, w3m [0.3304, 0, 0.6696] 算术 ✓, ρ 0.966; 反事实改写 **21.1%**(00Z 20.6 → 04Z 20.8 → 08Z 21.1, 连续两锚 +0.2~0.3pp; **未满三锚,不升级, 下锚必看**)。
- ③ 漏斗(A1788683040): 764 行 = filled 314 / min_notional 207 / partial_expired 155 / venue_reject 73 / no_chase_arm 15(行数显著高于常锚 ~486, 因 per_name_stop 两名 flatten_only + 大量重整); 首次 −5022 66/191 = **34.6%**(升级线 40%); 重挂实验第六锚: 候选 37 全重挂(落单 30, 再拒 7), direct 29(**累计 direct 164/1500**); behind 占比 0.562(0.50 ± 抽样); chase 75 / no_chase 80; fills 267 笔 6,923 USDT = **换手 4.20%**(稳态带内); **maker 占比 0.731**(播种后第五锚 <0.85, 结构性观察项延续)。
- ④ 记账(**09:5xZ 更正: 本行三个数字初稿是在计算打印前写下的, 与实测不符, 现按脚本输出改正, 原值 164,349 / +1.27% / 「结算 funding 行 267 合计 −10.98」作废**): venue gross **162,742** = 1.976×NAV 82,373; net **+2,366**, net/gross **+1.454%**(第 16 锚 >1%); n_names_skipped 119; 当日 funding 累计见 daily_nav 的 realised_by_type **FUNDING_FEE −33.05 USDT**(按 anchor_ts ±2h 过滤 funding.jsonl 得 0 行 —— 结算行的时间字段不落在该窗内, 口径不匹配, 只报当日累计); 日内已实现 −477.3(REALIZED −444.2, COMMISSION −0.003, funding −33.0)/ 未实现 −1,945.0; phase C 三件齐 08:44:28Z(anchors_row / readback 268 行 / per_name_stop); anchor done rc=0 09:46:34Z(止损后的收尾运行, 权重峰值 170)。
- ⑤ 执行质量(**同上更正**): markout60 maker(179 笔有 +60 s 中价)小 **+0.14** / 中 **−3.01** / 大 **−6.55** bps, 全部 **−5.29**(桶界 10/29 USDT; 原稿 +0.71/+2.06/−7.53/−4.26 作废); 大桶连续第三个锚为负(08Z −6.55, 04Z −9.87, 00Z −9.94), **崩跌锚里大额单被逆向选择**, 与归因一致。
- ⑥ 告警: position reconcile 12 名 adopting venue truth; 重整后 8 名跨 min_notional; 撤名残差 −11,880(文案≠算术, 已登记); 39 名 reduce-only; "36 个 maker 被 −5022 拒" = direct 29 + 再拒 7 ✓; **per_name_stop 两名触发: FLOCKUSDT 深度 −42.3%、COLLECTUSDT 深度 −51.3%, 连续 2 个终锚 ≤ −30% ⇒ flatten_only + 7 天禁入(条款 cf40ea21)**。**该锚无需处置; 其后 08:46Z 的 §4-2 止损与全书平仓见上方事件档。**

## exec_n6 Phase 2 重验读数 #1: 12Z 锚(1788696000; 12:25Z; 只读; **装置修后第一锚 —— 我的修改让情况更糟, 如实记录**)
- **P2 恒等 GREEN(唯一稳定成立的那一项)**: 沙箱 v2 与实盘逐位相同 —— members 400 / sel 245 / coverage 1.0 / fund_updates 354 / fund_updates_base 64 / forced_exit 0 / fetched 450 / missing 0 全同; w3 [0.2913, 0.1068, 0.6018] 同; king 形态 target 241 名 **max|Δw| 0.00e+00**, gross_norm 0.860604 同, universe_sha 同。**取数层的正确性从未出过问题, 两个锚都是逐位相同。**
- **P2 时序 RED, 且比 08Z 更差**: runtime **141.3 s**(08Z 43.5 s; 门 ≤90)⇒ RED; `t_fund_s` **116.4**(08Z 16.8; 门 ≤5)⇒ RED; `n_err` 5(门 0)⇒ RED; `t_klines_s` 21.9 ✓。
- **根因(我的装置修反噬, VERIFIED fetch_v2 字段)**: 把批量窗从 8h 放宽到 **26h** 后 —— `bulk_ok=false`, `bulk_pages=6`(撞到我自己设的 6 页上限), `bulk_rows=3953` 仍未穷尽。分页以「末行 fundingTime」续页, 而同一结算时刻约有 460 行, 页边界落在时刻中间会重复读, **每页有效推进远小于 1000 行**; 26h 窗的应有行数约 2,900–4,000, 6 页去重后 3,953 仍判未尽 ⇒ 代码按设计**整锚回退逐名**(354 次)⇒ t_fund 116 s。`fund_fallback_n=0` 是计数器语义所致(该计数只在 bulk_ok 为真时累加), **不代表没有回退**, 这一点也要记: 我给的字段在 bulk 失败时会误导。
- **`n_err` 5 与超时无关**: 08Z(超时 10 s)与 12Z(超时 25 s)都恰好 5 次三试全败 ⇒ 我此前把它归因于「10 s 超时过紧」**是错的**, 需另查(候选: 特定符号在 fundingRate 上恒返错误; 待下锚用逐名日志定位)。
- **P1 RED(按冻结措辞), 但属仪器假象**: 27/27 名在各自**第一次查询时**已在, 无抖动; 但最后一名的首次查询落在 **N+60.x s**, 越过「N+1:00 前 100%」这条线。探针按 1 req/s 顺序扫 27 名, 轮次起点 N+45 ⇒ 末名必然 ≈N+60 —— **这条门量的是探针自己的扫描速度, 不是数据到位时刻**(08Z 同样是「全部首查即在」, 只因末名落在 N+56 而判绿)。按纪律**不在看过数字后改门**, 故记 RED。
- **P4 RED**: 沙箱 target 12:03:21Z = N+3.35 min, 投影 combo 落盘 **N+4.00 min > 门 N+2:30**。
- **判定: P2 恒等 GREEN; P1 / P2 时序 / P4 全 RED ⇒ 不换装, 不改门。** 沙箱(PID 15515)/探针/实盘生产者未动。
- **处置选项(呈用户, 我不自行决定)**: (a) **装置继续修**: 批量窗回 8h(实测 2 页即穷尽、bulk_ok 真、t_fund 16.8), 并把分页改为「按 fundingTime 严格递增 + 同刻整批」以消除重复读; 另查 n_err 5 的真实来源。此路仍要面对 `t_fund ≤5` / `fund_fallback ≤5` / `n_err 0` 三条门 —— **它们是我在看任何数字之前拍脑袋写的, 8h 窗下 fallback 恒为 8(结构量)⇒ 该门在当前设计下不可达。** (b) **承认门设得过紧, 另立预注册**把 P2 时序门重写为**结果门**(「投影 combo 落盘 ≤ N+(执行器 offset −0.5) min」+「恒等逐位相同」+「无 429/−1003」), 不再对中间量设阈值; 旧门作废需在新预注册里写明理由与作废时点。(c) **放弃 Phase 2**, 维持在役 N+24。

## 12Z 锚(1788696000)深查(13:39Z; **第一个完全停机的锚 —— 本条同时是"停机锚基线", 供明日复场锚对照**)
- ① 守护: 生产者 10900 = shadow.lock = launchd(24h); combo 30944 = pidfile; sidecar 30943。三项在, 句柄一致。
- ② 信号(**停机不影响信号侧, 生产者照常产出**): OK, coverage 1.0, members 400, sel 245, fund_updates 354(4h 整点 ✓), forced_exit 0, fetched 450/缺 0, runtime 251.4 s; w3 [0.2913, 0.1068, 0.6018] ⇒ 掩码 king **0.3262**(08Z 0.3304 后回落, 五连升中止); 上锚(08Z→12Z)score gross −22.0 / net **−23.6 bps**(单位书 —— **注意: 这是"书若在场"的假想值, 实盘该窗空仓, 不是实际盈亏**); combo rc=0 12:20:50Z, n 244, gross 0.8177, kc/fc own, w3m [0.3262, 0, 0.6738] 算术 ✓, ρ 0.964; 反事实改写 **21.0%**(08Z 21.1 → 12Z 21.0, 回落, 三锚连升门未触发)。
- ③ 执行漏斗(**这是停机的证据**): orders 228 行 = **`blocked_by_halt` 227 + `skipped_min_notional` 1**; **fills 0 笔, 换手 0, 拒单 0, 无重挂/chase 记录**(requote report 与拒单率行均 NOT FOUND ⇒ 根本没有下单路径被走到)。placement 臂仍被记(behind 107 / join 121, 占比 0.469)—— 那是**计划阶段**的随机分臂, 在被 halt 挡下之前就已写入, 属预期; **重挂实验累计 direct 停在 164/1500, 停机期不累积**。
- ④ 记账: readback 末行 ZROUSDT 0.0(全零); venue gross **0**; NAV **82,241.4**(08Z 82,373.0 → −132 = 平仓净成本, 约 16.3 万名义的费用+滑点合计 ≈8 bps); 日内已实现 **−2,479.4**(REALIZED −2,446.3 + funding −33.0 + 佣金 −0.003)= 平仓把未实现兑现; 未实现 0; target_gross 164,481.69(**目标仍在算, 只是不执行**); phase C 三件齐; anchor done rc=0 12:40:49Z; 限流峰值窗 361(远低于交易日的 843–1,298)。
- ⑤ 执行质量: 无成交 ⇒ 尺寸梯度与 markout 本锚无数据(不是异常)。
- ⑥ 告警核对: **position reconcile 233 名 "adopting venue truth"** —— 这是**平仓后的必然**(书以为持有 233 名, 场所全为 0), 非事故, 但严重度写成 INFO 而文案是 HIGH, 属既登记的"文案≠来源"家族; 撤名残差 −9,756(16 个撤下名, 含全部冷却名); **per_name_stop: COLLECTUSDT / CYSUSDT 出场并进入 7 天冷却(至 09-13 12:39Z)** ⇒ **停止名 0, 冷却名 14**(平仓把"停止"状态转成了"冷却"); guard_twin 12:42/13:02 **DISAGREE**(day_twin −3.73% vs arith −4.27%, 差 0.54pp 略超 0.5 容差), 13:22 回 AGREE —— 根因与 09-06 01:01Z 那次同族: 两把尺子的窗口不同(twin 用自家快照起点, arith 用日切 NAV), 平仓日两者必然分叉; 账本恒等 gap 仍为 0, **只记不处置**。
- **判定: 停机链路按设计工作 —— 信号照常、执行全挡、账目干净、NAV 行可用。无需处置。**
- **对明日复场的三条基线**: (a) 停机锚的 orders 全部 `blocked_by_halt`, 复场锚应变为正常终态分布; (b) 冷却名 14 个在 09-13 前不会建仓, 复场锚的 gross 因此略低于 2.0×(体检 §4 已把验收带放到 [1.85, 2.05]); (c) guard_twin 在平仓/复场这两天会持续 DISAGREE, 属窗口口径而非缺陷。

## exec_n6 结果门重验 #1: 16Z 锚(anchor 1788710400, 8h 结算锚)
> 读数时刻 16:25–16:3xZ; 判据 = `docs/PREREG_exec_n6_phase2_gates_v2_2026-09-06.md` §3, **一字未改**; 只读, 实盘书零接触(书自 08:46Z 止损后仍平仓, 本锚无成交, 不影响本组门 —— 五门判的都是**生产者取数与落盘时序**, 与是否交易无关)。

### 五条结果门: **全绿(5/5)**
| # | 门 | 读数 | 判 |
|---|---|---|---|
| 1 | **恒等** | members 400=400, sel 246=246, coverage 1.0=1.0, fund_updates 454=454, **fund_updates_base 76=76**, forced_exit 1=1, fetched 450/missing 0 两侧同; w3 [0.2935, 0.1046, 0.6020] 两侧逐位同; target n 241=241, **max\|Δw\| 0.00e+00, Σ\|Δw\|/gross 0.00e+00**, universe_sha 同, **weights_sha 两侧同 `160eb7060deb`**; 无 anchor_error/skip(`sandbox anomaly rows: none`) | **GREEN** |
| 2 | **投影 combo 落盘 ≤ N+2:30** | 沙箱 target 落盘 **N+1.78min**(16:01:47Z)+ 实盘 combo 时延 **41s** ⇒ 投影 **N+2.47min** | **GREEN, 但只富余 1.8 秒**(见下) |
| 3 | **应结算名首查即在 + klines** | 应结算 **27/27 全部首查即在, 无抖动**(末名首查 N+64s = 探针 1 req/s 扫描速度, 非数据到位时间); klines 收盘于 N 的 bar **10/10 @N+10.9s** | **GREEN** |
| 4 | **无 429/−1003 且权重峰值 ≤1200** | 两侧日志本锚行 429/−1003/banned 命中 **0**; 权重峰值 沙箱 **465** / 实盘 **976** | **GREEN** |
| 5 | **沙箱 runtime ≤210s 且 bulk_ok** | runtime **46.9s**(实盘 271.5s), `bulk_ok=True`, bulk_pages 7, bulk_rows 4496 | **GREEN** |

### 只报不判(诊断项)
`t_klines_s 22.6` · `t_fund_s 21.6` · `fund_per_symbol_n 7` · `fund_fallback_n 7` · `bulk_pages 7`(cap 12)· `n_req 465` · `n_err 5` · `weight_used 465`(沙箱)/ `976`(实盘)· `bulk_hours 26`。

### ★ `fund_err_syms` 结案: n_err=5 的真根因不是超时, 是 5 个非 ASCII 名的新上市合约
- **失败名单(原样记录)**: `['哈基米USDT', '币安人生USDT', '我踏马来了USDT', '牛来USDT', '龙虾USDT']`。
- **此前的误判已更正**: 08Z 我把 `n_err=5` 归因于 10s 超时; 12Z 把超时放到 25s **仍然恰好是 5**, 当时只记了"归因错误"。现在有了名单, 根因确定: **失败的永远是这同 5 个名**, 与超时无关。
- **它们为什么会被查(VERIFIED 读码)**: M1 秩基 = 场所 `exchangeInfo` 里 `PERPETUAL ∧ USDT ∧ TRADING` 的**全部名** ∪ `symbols_live`(v2 L329–335, 实盘 v1 L317 同式)。新上市名因此进入 fund 遍历基。它们**没有 ledger** ⇒ `last_ts = anchor − 40 天` ⇒ 落在 26 小时批量窗之外 ⇒ 走逐名回退(这就是 `fund_per_symbol_n 7` 的来源)。
- **为什么失败(INFERRED, 高置信, 未发请求验证)**: 7 个回退名里失败的恰好是**全部 5 个非 ASCII 名**, 成功的 2 个是 ASCII 新上市名 ⇒ 指向逐名 `fundingRate` 查询对非 ASCII symbol 的处理。**未做 API 复现**(实盘 API 无谓请求一律不发), 故标 INFERRED。
- **对书的影响: 零到可忽略, 且非 v2 引入**。① 这 5 个名**既不在 `symbols_live`(450) 也不在 `symbols_panel`(829)**(逐一核对, 两个集合里非 ASCII 名各为 0 个)⇒ **永远不可交易, 不会进书**; ② 它们只会影响 M1 的 fund 秩归一基 —— 取数失败 ⇒ 无 EMA ⇒ 本就被排除在秩基外, 基大小少 5(约 460 名里的 1%); ③ **沙箱与实盘 `fund_updates_base` 同为 76、目标权重逐位相同** ⇒ 实盘 v1 生产者有完全相同的行为, **不是 Phase 2 的回归**。
- **登记为观察项, 不提改动**: 若将来要修, 属生产者取数层改动, 需预注册; 当前无净影响, 优先级低。

### ⚠ 必须说清的一点: 第 2 门是**擦线过**
投影 N+2.47min vs 门线 N+2:30 ⇒ **富余仅 1.8 秒**。构成 = 沙箱落盘 N+1.78min(107s)+ 实盘 combo 时延 41s。**若 combo 时延到 43s 该门即红**。combo 时延本身不受 offset 改变影响(它是守护轮询 + 重写的固有耗时, 历史区间 30–50s), 因此这条门在后续两锚有真实的翻红概率。**本次不改门、不换装**; 三锚汇总时若出现红项, 按预注册处理, 不得因"只差 2 秒"而放行。

### 判定
**五门全绿, 但第 2 门擦线。** 按既定条件, 换装仍顺延至: 复场后连续 ≥6 个正常交易锚 + 04Z 首锚验收 PASS + 用户字。本次不起换装定时。下一次读数 = 20:25Z(`fac9976b`, anchor 1788724800)。

## 16Z 锚(1788710400, 8h 结算锚)深查(17:39Z; **第三个完全停机锚**; 本条只写与 12Z 停机基线的**增量**与**一处越线项**)
> 本锚的生产者侧五门读数已在上一节(exec_n6 结果门重验 #1)记录, 不重复; 本节补执行/记账/守卫侧, 并处理一处预注册越线。

### ① 三守护(按句柄文件验, 非按进程名)
`shadow.lock` = **10900**(生产者, uptime 1d 04:51) · `fea171/combo_live_daemon.pid` = **30944**(uptime 7d 12:35) · `sidecar_daemon.sh` = **30943**。三项在, 句柄一致。
**注**: `ps | grep sidecar` 会同时命中 macOS 自带的 `/usr/libexec/SidecarRelay`(PID 1895) —— 与本项目无关, 属 pgrep 模式匹配陷阱家族, 按句柄文件判即可。

### ② 信号六项(与停机无关, 生产者照常)
`members 400 · sel 246 · coverage 1.0 · fund_updates 454`(8h 结算整点带 ~453 ✓)· `forced_exit_n 1` · `w3 [0.2935, 0.1046, 0.6020]` ⇒ **掩码 king 0.3277**; combo rc=0 16:21:12Z, n 246, gross 0.8211, kc/fc 均 own, `w3m [0.32773, 0, 0.67227]` 掩码算术 ✓(0.2935/(0.2935+0.602) = 0.3277), ρ(kc,fc) **0.9618**, f10 打分 400 ✓; 上锚(12Z→16Z)score **gross +15.54 / net +13.996 bps**(单位书 —— **书若在场本可赚, 但实盘该窗空仓; 这是停机的机会成本, 不是盈亏**)。

### ③ ★ 反事实改写 21.36% —— 预注册台阶线**已越**, 但根因已查清, 不升级为异常
逐锚序列(现算, 装置 = king 形态 vs combo 形态逐名 Σ|Δw|/gross_king):

| 锚 | 改写% | 掩码 king | ρ(kc,fc) |
|---|---|---|---|
| 09-04 12Z | 17.91 | 0.2188 | 0.9758 |
| 09-05 08Z | 18.89 | 0.1924 | 0.9759 |
| 09-05 12Z | 18.93 | **0.1878** | 0.9765 |
| **09-05 16Z** | **19.35** | **0.3045** | 0.9752 |
| 09-05 20Z | 20.50 | 0.3086 | 0.9718 |
| 09-06 00Z | 20.65 | 0.3139 | 0.9698 |
| 09-06 04Z | 20.83 | 0.3238 | 0.9674 |
| 09-06 08Z | 21.09 | 0.3304 | 0.9656 |
| 09-06 12Z | 21.00 | 0.3262 | 0.9636 |
| **09-06 16Z** | **21.36** | 0.3277 | **0.9618** |

- **判据逐条对**: 「连续 3 锚增量 > +0.2pp」**未触发**(最长连续两锚: 04Z +0.19 / 08Z +0.26 已断; 12Z −0.10)。「level 再升一档」—— **触发**: 登记台阶是 **19–20%**, 而最近 6 锚全部落在 **20.5–21.4%**, 整体高于原带。**判据是 OR, 所以按字面已越线, 不能因为另一条没触发就略过。**
- **根因(VERIFIED, 不是异常)**: 改写幅度与掩码 king 席位的相关 **r = +0.899(n=14)**; 阶跃**恰好落在 09-05 12Z→16Z 之间**, 而 **09-05 12:47Z 正是 king 席位播种上线**(席位 0.1878 → 0.2999, 收据见 09-05 日记与 `seat_seed_v3_deployed_2026-09-05`)。机制: combo 改写的是 king 腿(55/45 混 V2MAIN), king 席位变大 ⇒ 被改写的那一部分变大。ρ(kc,fc) 同步单调下滑 0.9765 → 0.9618, 与同一机制一致。
- **处置**: **不升级为异常**(有已授权、有日期、有收据的原因), 但**显式重设基线**: 反事实改写台阶由 19–20% 迁移到 **20.5–21.5%**, 下一档判据从新带起算。**登记而非静默接受** —— 台阶迁移本身要留痕, 否则下次再涨就没有参照。

### ④ 执行漏斗(停机, 与 12Z 同形)
orders **231 行 = `blocked_by_halt` 230 + `skipped_min_notional` 1**; **fills 0**; 换手 0; 拒单真实率 **0.0%**(首拒 0 / 首落单 0); requote report 与拒单率行均 NOT FOUND; `requote_arm` 空(停机期不累积, direct 仍停在 164/1500); placement 臂 join 112 / behind 119, **behind 占比 0.515 ≈ 0.50 ✓**(计划阶段随机分臂, 在被 halt 挡下前已写, 属预期); chase 臂空。

### ⑤ 记账
NAV **82,237.30**(12Z 82,241.36)· target_gross 164,468.95 ≈ NAV×2.0 ✓ · venue_gross **0**(平仓) · 日内已实现 **−2,479.37 不变**(REALIZED −2,446.32 / FUNDING −33.05 / COMMISSION −0.003) · 未实现 0 · **16Z 是 8h 结算锚但空仓 ⇒ 无新资金费, 正确** · readback 末行 ZROUSDT 全零 · `anchor done rc=0` 16:40:21Z · 执行器窗口权重峰值 **496**。
- **NAV −4.07 的解释(VERIFIED, 非缺陷)**: guard_twin 每 20 分钟读到的权益在**空仓状态下仍在 ±5 USDT 内摆动**(15:02→17:23 实测 82,232.05 ~ 82,241.93, `lev=0.0`)⇒ 两个相隔 4 小时的 daily_nav 快照差 4 USDT 属同一摆动的采样, 不是盈亏(已实现未变、未实现为 0)。**推断来源 = 非 USDT 抵押品(BNB)按市价折算**(INFERRED, 未取逐资产快照证实)。
- **连带**: 止损告警数字由 −4.27% 变 −4.28%, 正是这 4 USDT 采样差(82,237.30/85,910.88 − 1 = −4.276%)。**明日恢复门判的也是这个单点快照量, 摆动幅度 ±0.006% 相对 −4% 线可忽略。**

### ⑥ 守卫与告警
`per_name_stop`: **停止 0 / 冷却 14**(与 12Z 同, COLLECT/CYS 冷却至 09-13)。
**guard_twin 机制已查清**: 16:43 / 17:03 **DISAGREE**(day_twin −3.741 vs arith −4.276, 差 0.53pp > 0.5pp 容差), 17:23 回 **AGREE(ledger-only; nav row stale)**。规律 = **只要当锚 nav 行是新鲜的就 DISAGREE, 行变陈旧后孪生退回 ledger-only 即 AGREE**。差值来自平仓日两把尺子的窗口不同, 账本恒等 gap 恒为 −0.00。**只记不处置**, 与 12Z 同族。
告警: 撤名残差 **−9,208 USDT(−5.60%)**, 15 个撤下名; LINKUSDT 跨过 min_notional(仅报告)。两条均为平仓后预期家族。

### ⑦ 执行质量
无成交 ⇒ 尺寸梯度三桶与 markout 本锚无数据(非异常)。markout 回填 16:40Z 两日合计 written 6 / pending 34, `expired=0 terminal=0` —— E-0905-G 修复后不再空转。

### 判定
**停机链路第三锚仍按设计工作, 无需处置。** 唯一需要留痕的是 ③ 的台阶迁移(已重设基线)。下一锚 20Z, 深查照常; 恢复动作 09-07 01:10Z。
