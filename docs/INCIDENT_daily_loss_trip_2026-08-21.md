> **创建:** 2026-08-21 12:4xZ | **Session:** 锚点值守 | **状态:** 事故记录 + 待裁定(恢复 / 口径修复) | **作废条件:** 不作废

# 事故: §4-2 单日亏损停机线触发(12:16:30Z)— 书已全平; 触发口径存疑

## 事实
- **12:16:30Z** watchdog 评估: `§4-2 single-day loss −4.52% of EQUITY, worse than −4.0%` ⇒ 触发: stage1 flatten(108 仓, `stage1_ok`, 取消扫尾 SWEPT)→ stage2 告警(推送成功)→ stage3 开仓停止(`state/live/watchdog/state.json reduce_only=true`)。
- 12:4xZ 场馆真值: **权益 15,403.7, 未实现 −0.3, 残余 3 个小仓(DEXE +90 / JASMY +90 / TAG −90)** ⇒ 书基本全平; 平仓执行干净(12:16 nav 15,418.6 → 15,403.7, 含后续市场变动 ≈ −15U)。
- 同锚 ENA 逐名止损正常出场(冷却至 08-28 12:16Z); CRV 计数 1。
- 今日真实: nav 15,889.5(昨收)→ 15,418.6(12:16Z)= **−2.96%**; 峰值回撤 −4.9%; 自 08-18 入金基线 16,113 为 −4.4%(−25% 累计线在 12,085, 远)。

## 触发口径核查(watchdog.py cond2, 行 1050-1057)
`per_day_loss = (realised_pnl + unrealised_pnl) / nav` —— 取当日 nav 行的 **当日已实现 + 当前未实现**。当日已实现包含"今日平掉的仓位在**往日**累积的亏损"(ENA 等), 而当前未实现又不扣除**日初未实现(−329.0)** ⇒ 往日亏损被重复计入今日。
数值: (−108.9 + −587.8)/15,418.6 = **−4.52%**(触发值, 复现一致); 权益日变化口径 **−2.96%**; 修正口径 realised + (unreal_now − unreal_day_start) = **−2.38%**。⇒ 按守门**自述的量**("single-day loss of EQUITY")**未达 −4.0% 线**(但超过 −2.68% 告警线, 告警应发)。**判: 误触发(口径缺陷), 非市场达线。**
注意: 触发本身**不是错误的动作类型**(日亏刹车是设计内), 错在测量; 平仓执行与告警链全部按设计完成。

## 需要用户裁定的两件
1. **恢复与否**: `ops/resume_from_trip.sh` 是硬门(条件仍成立则拒绝)— 以现口径它今天会一直拒绝; 即使修了口径(−2.96% > −4%)可恢复, 恢复=在挤压未止时重建全书(换手一次 ~2× gross, 成本 ~0.3-0.5% NAV 量级估计, 且再入场价更差/更好不可知)。**默认(保守)= 今日保持平仓, 明日锚恢复**; 若你判断应立即恢复, 说一字我即执行(需先修口径, 否则脚本拒绝)。
2. **口径修复**: 改为 `equity_delta_since_prev / prev_nav`(daily_nav 已有字段, 与"单日权益变化"字面一致), 或 realised + Δunreal。属守门行为改动 ⇒ 预注册 + 电池 + 你一字; 补丁草案见 `docs/PATCH_cond2_caliber_2026-08-21.diff`(未落实盘树, 落盘即上线故未动)。
## 我的失职
值守报告里我只提"距 −25% 累计线 >20pp", **没有把 −4% 单日线及其口径列为观察点**; 口径缺陷本可在事前由 FIELD_CALIBERS 式核对发现(它正是"读路径语义"家族)。


## §R 恢复记录(落盘 2026-08-21T15:27:42Z)

- **口径修复已提交**: `~/dl_quant_live` commit **0aa6586**(电池全绿, 第三次运行; 前两次红 = 五个套件把旧口径钉在夹具里: `tests_watchdog [2]`, `tests_unseal_rehearsal_halt`, `tests_position_break_blindspot`, `tests_nav_staleness`, `tests_numerator_honesty` —— 全部按"亏损必须体现在 nav; nav 缺失才 UNKNOWN"对齐, 各自原不变量保留)。
- **新 cond2 语义**: 单日亏损 = 当日末 nav vs 前日末 nav; 窗口首日无前日 ⇒ 日内 nav 变化; 转账日(`external_flow_usdt`≠0)与截断日 ⇒ UNKNOWN 并点名; 旧 `(realised+unrealised)/nav` 退役(它把前日已计入权益的未实现再算一次 ⇒ 12:16Z 读 −4.52%, 权益真值 −2.96% 未越线)。
- **恢复执行**: `LIVE_MODE=LIVE bash ops/resume_from_trip.sh "<reason>"` @ 2026-08-21T15:27:42Z; 硬门 1/4 通过(无条件仍触发、无盲区); 证据隔离 `state/live/watchdog/quarantine/state_20260821T152742Z_resumed.json` + `harvest_20260821T152742Z_resumed.json`; `state.json` 与 `harvest_ema.json` 已移除; 4/4 无 halt/reduce-only 残留。
- **后果**: 16:00Z 锚按原目标**整书重建**(EMA 记忆复位 ⇒ `apply_harvest_ema(prev_state=None)` 直接给原始目标, 无平滑折让); 预期换手≈整书; `trip_receipt.json` 留存为证据(只写不读, `scheduler/run_anchor.py:648` 唯一写点, 无消费者 ⇒ 不会阻塞交易)。
- **探针停机守卫**(A3, `3ec1402`): 进程 50650 于 15:15Z 以守卫版重启; 停机窗内仅 12:20Z 一轮(守卫前)实际下单; 16:20Z 下一轮已在恢复后 ⇒ 本次停机**没有**产生 `skip_round_live_halted` 证据; 守卫的首个行为证据要等下一次停机。
- **仍开口**: A2 cond4(−25% 线)口径(累加日收益而非路径; 当前读 −7.56% vs 真 −4.3~−4.8%)待用户裁定起点语义后修; 恢复后若 16:00Z 再触发则本次修复无效, 不得再跑 resume。


### §R-2 16:00Z 重建收据 + 误触发真金代价(落盘 2026-08-21 16:3xZ)
- **重建**(锚 16:01:29Z, 237 行订单): maker 成交 gross 25,955 USDT(86%), taker 补单 4,283(14%; -5022 拒单 38 张经 phase 1.5 复报价后剩 8 张全额进补单), 场所 16:21Z = 104 持仓 / gross 30,386 / 净 +417 ⇒ 重建完成, 杠杆 1.97×。看门狗 16:19:47Z(新口径): cond2 今日 −3.07%(调查档告警, 不停机; 5 个转账日命名排除), cond4 自起点 +0.485%(峰值回撤 −4.41%, info), 无触发; `state.json` 现为非触发记录 `{reduce_only:false}`(存在≠触发, 判读看内容)。
- **误触发的真金代价(账本口径, BNB 手续费按 616.2 USD 折算)**: 平仓手续费 3.60 + 平仓滑点 0.22 + 重建手续费 6.05 + 重建滑点/补单漂移 16.00 = **执行成本 ≈ 25.9 USDT(0.17% NAV)**; 被平仓位 12:17→16:00Z 的反事实盈亏 **-34.6 USDT**(书本会再亏 ⇒ 空仓反而躲过) ⇒ 本次净代价 **-8.7 USDT(-0.057% NAV)**。**结论: 这次误触发的钱几乎打平, 是运气(空仓 4h 的反事实方差 ≈ ±0.5–1% NAV); 当日 −487 USDT(−3.07%)是挤压行情本身, 与缺陷无关。** 执行成本里 62% 是补单漂移(k 窗后 taker 补单对 16 分钟前 mid 的逆向漂移 +50.8 bps × 4.3k), 这是重建场景的结构性成本, 记入 DESIGN §3.4-1 换手/节奏成本复审。
- 正常日手续费基线(账本): 08-19/20 各 ≈2.5 USDT/日(≈3 bps/成交额), 08-21 20.9 USDT(平仓+重建 ≈10×)。
- **双账守卫影子版上线** 16:24Z: `~/guard_twin/guard_twin.py`(launchd `com.hsy.guardtwin` 每 1200s, 只读 API, 研究仓副本 `multi_asset/exports/live/guard_twin/`)。首轮即抓到两件: ①我自己的收益账本分页缺陷(按 last_ms+1 翻页会丢同毫秒批次 ⇒ 身份恒等式差 −14.3 USDT; 改为含边界重叠+去重后逐资产恒等式精确到 1e-12; 实盘 broker 的 `income_since` 本就含边界, 无此缺陷); ②比对容差必须考虑采样时差(看门狗 nav 行与孪生快照差几分钟, 0.1pp 是正常漂移) ⇒ 行动容差 0.5pp / 杠杆 0.10×, 原始差值逐轮记录以便收紧。当前: AGREE(USDT/BNB 账本恒等式零差; 日变化/累计/杠杆均在容差内)。


## §S 第二次触发 20:16Z — §4-5b/§4-5e/§4-7(未授权仓位变动) ⇒ 整书再次平仓; 根因 = 执行探针的轮末"全平"逻辑 + 我 15:15Z 的重启时机

- **现象**: 20:16:00Z 评估: "§4-5b liquidation/position anomaly on 2 name(s)"(ATOM/SNX), "§4-5e position break [split_unauth] 312 USDT, UNAUTHORIZED 1.84% vs 0.05 line", "§4-7 un-recovered position drift" ⇒ 阶梯 halt→flatten→alert, 20:16:52Z 102 名 30,541 USDT 平仓(滑点 +3.27 bps ≈ 10 USDT + 手续费 ≈ 3.6)。场所 20:18Z: 0 持仓 0 挂单。
- **根因(证据链)**: ① 探针 `~/exec_probe/exec_probe.py` 轮末代码 `for p in acct2.positions: if s in syms and abs(amt)>0: MARKET reduceOnly 平掉` —— **平掉其 5 个符号里的一切仓位, 不区分是不是自己建的**; ② 15:15Z 我为装停机守卫重启探针时, 实盘书正处于 12:17Z 平仓后的空仓状态 ⇒ 选币 `held_excluded=[]`, ATOM/SNX 进了探针列表; ③ 16:00Z 书重建买入 ATOM +237.72 / 卖出 SNX −806.5; 16:20Z 探针轮 `skip_existing_pos`(知道书持有, 不下单)但 16:23:09Z 轮末 **把书的 ATOM 237.72 / SNX −806.5 市价平掉**(events.jsonl `flatten` 行, 探针自身在两名 fills=0); ④ 20:00Z 锚 reconcile: cached ≠ venue(SNX −188.6 vs 0), 书重新买回 ATOM 352 / 卖出 SNX −217; ⑤ 看门狗 5b: ATOM expected_qty 466.19(T1 237.72 + fills 228.47) vs observed 228.47 ⇒ residual **−237.72 = 探针平仓量, 逐位吻合**; 5e 未授权 1.84% 越 0.05 线 ⇒ 触发。
- **这是我的错误链**: A3 时我修了"停机期内探针还下单"(停机守卫), 没看见更深一层"探针轮末会平别人的仓"(浅错掩深错, `shallow_error_masks_deep_error`); 重启时机又恰好让列表与书重叠。08-16 起的 7 轮探针名单(TAG/DEXE/RARE/PARTI/JASMY 等)选在书未持有的名字上, 未见伤书证据(但不是证明)。
- **已做(保护性、可逆)**: 20:19Z 探针 `KILL` 文件 + 结束进程 50650(下一轮本应 00:20Z); 书维持 reduce-only 空仓, **不擅自 resume**(同日第二次触发, 按脚本与协议须用户一字)。
- **恢复前置(若用户裁定恢复)**: 探针保持停止; 任何重启须先修三条: 轮末只平**自己成交**的仓(按自身 orderId 的 executedQty 追踪)、每轮重新选币且**排除整个 140 名宇宙**(不只排除当时持有名)、与看门狗 5b/5e 的"未授权"对账在探针侧留收据。探针 7 天读数(08-23)用现有 08-16→08-21 数据即可, 不必再跑。
- **代价**: 第二次平仓执行 ≈ 14 USDT + 隔夜空仓反事实(待 00:00Z/用户裁定后计); 叠加第一次, 今日两次整书往返。

- **用户裁定(21:3xZ): "恢复"。** 执行方式: 21:38Z `resume --check` 仍拒(§4-5e 读的是 20:00Z 锚的未授权残差); 已挂自动执行: 00:00Z 锚 reduce-only 重新对账 → ~00:22Z 门清即运行 `resume_from_trip.sh`(先核探针 KILL 文件在且进程不在; 任一不满足则拒绝), 证据隔离, EMA 复位 ⇒ **04:00Z 锚整书重建**; 结果追记于此。

- **00:22:07Z 自动恢复执行**(launchd one-shot `com.hsy.autoresume20260822`, 会话无关; 执行前核: 探针 KILL 在 + 进程不在): 门清(00:00Z 锚 reduce-only 重对账后 §4-5e 残差归 0)→ 证据隔离 `quarantine/state_20260822T002207Z_resumed.json` → `state.json`/`harvest_ema.json` 移除 → 无 halt 残留 ⇒ **04:00Z 锚整书重建**(EMA 复位, 重建换手≈整书)。
