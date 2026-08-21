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
