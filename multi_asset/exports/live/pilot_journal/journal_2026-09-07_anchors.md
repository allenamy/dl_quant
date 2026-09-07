> **创建:** 2026-09-07 01:1xZ | **Session:** b9646a9e | **状态:** LIVING(逐锚追加) | **上一日:** `journal_2026-09-06_anchors.md`(§4-2 单日止损事件档) | **作废条件:** 不作废 — 只追加

# 实盘日记 2026-09-07 —— 止损后复场日

## ★ 01:11:03Z 止损恢复执行成功(唯一一次写操作)
> 用户字 09-06「按第一条修, 修完后 09-07 04Z 恢复建仓, 2x 杠杆」; 判据 `PREREG_watchdog_cond2_resume_semantics_2026-09-06` §3 + §8。

### 五项前置(全过, 逐条 VERIFIED)
| 项 | 读数 | 判 |
|---|---|---|
| (a) 代码 + 电池 | 实盘仓含 **`c800690`**(watchdog §4-2 恢复语义)与 `9ae2e39`(dedup 指纹); `_safe_commit_acc.log` 末段 **`ACCEPTANCE: ALL GREEN (128/128 suites exit 0)`** | ✓ |
| (b) 09-07 NAV 行 | `20260907/daily_nav.jsonl` 存在(00:39Z 由 00Z 锚 phase C 写出, 713 B) | ✓ |
| (c) 时刻 < 04:00Z | 01:10:15Z | ✓ |
| (d) 仍处停机态 | `reduce_only true`, `open_orders_halted true`, `tripped_at 2026-09-06T08:46:08Z` | ✓ |
| **(e) 当日无划转(§8.2 新增)** | `external_flow_usdt [0.0]`, `realised_truncated [False]` | ✓ |
- 09-07 当日变化 **−0.0021%**(nav 82,236.03 vs prev_nav 82,237.77)= 空仓下的权益摆动, 距 −4.0% 线极远 ⇒ `recent` 取的是 09-07 而非回退到 09-06。**§8.2 的活风险本日未兑现。**

### 只读核查(步骤 ②)
`LIVE_MODE=LIVE bash ops/resume_from_trip.sh --check` ⇒ **`CHECK: RESUMABLE — the gate passes and no condition is blind.`** exit 0, 未触碰任何状态。

### ★ 一次被工具挡下的操作失误(如实记录)
**第一次执行真实恢复时我漏了 `LIVE_MODE=LIVE`**(只读核查那条带了, 写操作那条没带)。脚本按设计拒绝:
> `mode = DRY_RUN … ✗ DRY_RUN is NOT tripped, but ['LIVE'] IS. Refusing: you almost certainly meant one of those. Re-run with LIVE_MODE=LIVE.` → `── ABORTED: wrong mode. State untouched.`

**未触碰任何状态**, 重跑时补齐环境变量并**用 `out=$(...); rc=$?` 取退出码而非经管道读**(项目已登记的管道退出码陷阱)。
- **登记为错题形态**: 这正是 E-0826-C/D 家族(**复跑/执行命令漏 env**)。防线起作用的原因是脚本做了「哪个 mode 在停机」的交叉检查, 而不是盲接受当前 mode —— **一个在错误场景下会红的守卫**。

### 执行与验证(步骤 ③④)
`RC=0`, 逐步收据:
- **1/4 硬门**: `✓ no condition currently fires, and none was blind`
- **2/4 证据隔离(从不删除)**: `state_20260907T011103Z_resumed.json`(2,048 B; 内含 `reduce_only true` / `open_orders_halted true` / `tripped_at 2026-09-06T08:46:08Z`, `grep -c reduce_only` = 1)
- **3/4 清除**: `removed state/live/watchdog/state.json`; `no harvest_ema.json (EMA memory already clean)` —— 该脚本按 PREREG_harvest_speed 的重置规则本会一并隔离 harvest EMA, 本次因文件本就不存在而无操作(**记下来, 因为"没做"和"做了"在日志里长得像**)
- **4/4**: `✓ no halt/reduce-only state remains`
- **独立复验(不信脚本自述)**: `state/live/watchdog/state.json` **不存在 ✓** · `halt.json` 不存在 ✓ · `reduce_only.flag` 不存在 ✓ · **`trip_receipt.json` 仍在(1,296 B)** ✓ · 隔离目录另存 08-26 与 08-22 两次历史恢复, 未被覆盖 ✓

### 状态
**默认已从「不交易」翻回「交易」。下一个锚(04Z)按 `constant_leverage_2.00` 一次性重建全书。**
脚本自带的警告照录: *"If the guard fires again on the next anchor, the cause was NOT fixed — do not re-run this."* ⇒ **若 04Z 或其后再触发, 不得重跑本脚本, 必须先查因并报用户。**

### ⚠ 今日纪律(§8.2, 到首锚验收 PASS 为止)
**09-07 全天(UTC)不得向合约钱包转入或转出任何资金**(含 BFUSD/理财互转)。机制: 划转会使当日变成"未定价日", `recent` 回退到 09-06 的 −4.27% ⇒ **cond2 再次触发, 把刚建好的书再平一次**。隔离复现装置 `pilot_journal/tools/resume_gate_flowday_probe.py`。暴露窗只有今天。

## 00Z 锚(1788739200, 8h 结算锚)深查(01:39Z; **第五个也是最后一个停机锚** —— 恢复发生在其后的 01:11Z)
> 生产者侧五门读数见 09-06 日记的 exec_n6 结果门重验 #3 段, 不重复。本节的价值 = **两条新 HIGH 告警的根因**, 两条都查到实测机制, 两条都无需处置。

### ① 三守护
`shadow.lock` = **10900**(uptime 1d 12:51)· `combo_live_daemon.pid` = **30944** · `sidecar_daemon.sh` = **30943**(uptime 7d 20:35)。句柄一致。

### ② 信号六项
`members 400 · sel 245 · coverage 1.0 · fund_updates 454`(8h 结算带 ~453 ✓)· `forced_exit_n 1` · `w3 [0.2869, 0.0908, 0.6223]`; combo rc=0 00:21:07Z, n 245, gross 0.8287, kc/fc 均 own, f10 打分 400, ρ(kc,fc) **0.9626**(20Z 0.9612, 微升)。
**掩码算术逐位核**: 0.2869/(0.2869+0.6223) = **0.315584** = target_combo 的 `w3_masked[0]` ✓。
**反事实改写 21.0%**(16Z 21.36 / 20Z 21.36 / 00Z 21.0), 落在 16Z 重设的 **20.5–21.5%** 新带内, 两条判据分支均未触发。

### ③ ★ 新 HIGH 告警之一: 锚点产物断言 REGRESSION —— **UTC 日切效应, 04Z 自愈**
- **告警原文**: `no orders column is constant for want of a producer [NO_PRODUCER=['fee_all_usdt','fee_assets','requote_arm','requote_p','spread_at_submit_bps']; …] — 系统跑完了, 但该留下的痕迹没有留下。`
- **不是去重吞掉**(先排除已登记的 dedup 缺陷): 该断言**逐锚都跑**, `anchor_runs.log` 显示 09-06 12Z/16Z/20Z 三锚均 **`artifacts: OK (10/10 hold)`**, 只有 09-07 00Z 变 **`REGRESSION (8/9 hold)`**。
- **根因(VERIFIED 实测, 非推断)**: 该断言**按 UTC 日**取 orders 文件。逐日统计 —— **09-06: 2,425 行 / 7 个锚 / 其中 876 行有 `submit_ts`**(日内前几锚在止损前有真实成交)⇒ 费用/重挂/spread 列有产生者 ⇒ 通过; **09-07: 230 行 / 仅 00Z 一个锚 / `submit_ts` 行数 = 0**(229 `blocked_by_halt` + 1 最小名义)⇒ 这些列全部无产生者 ⇒ 判 REGRESSION。
- **⇒ 09-07 是第一个"整日只含停机锚"的 UTC 日**, 这条断言按设计报出"该留下的痕迹没有留下"—— **它是对的, 只是原因是停机不是缺陷**。**04Z 有真实下单后自愈**, 不处置。
- 附: 08-24→08-30 的同名告警是**另一回事**(`NO_PRODUCER='placement_eps'` 单列), 与本次列集完全不同, 不要混读。

### ④ ★ 新 HIGH 告警之二: ic_monitor #55 ALERT —— **崩跌两锚的回声, 且序列已冻结**
- **告警原文**: `r24=-0.02372 (ALERT<-0.02277, DECIDE<-0.04425), r48=-0.00964, β-resid r24=-0.03051, n=151`
- **复算逐位吻合**(不信装置自述): 我独立重算 `n=151` ✓、`r24=-0.02372` ✓。
- **★ 序列停在 09-06 04Z**: ic_monitor 从 `position_readback`(场所回读)算逐锚 rank-IC; **停机后仓位全零 ⇒ 不产行**。因此 `ics[-24:]` 是**最后 24 个"有仓位"的锚**, 窗 = **09-02 08Z → 09-06 04Z**, 完全落在停机之前。
- **★ 拆分(决定性)**: 窗内 **09-06 00Z(−0.14469)与 04Z(−0.16332)两个崩跌锚均值 −0.15401, 单独贡献 r24 的 54%**; **剔除这两锚, 其余 22 锚均值 −0.01188, 不越 ALERT 线(−0.02277)**。⇒ **这条 ALERT 完全由触发止损的那次崩跌造成, 不含任何新信息。**
- **判读依据(读码, 非记忆)**: `ic_monitor.py` 头部预注册 —— **ALERT = 历史上 5% 的日子会处于的状态; DECIDE = 1%**; 本次距 DECIDE(−0.04425)**很远**; 投递规则"同级 24h 内不重发"。⇒ **ALERT 档的处置就是记录与观察, 不是动作。不处置。**
- **前向提示(登记, 防止将来误读)**: 04Z 复场后新行才会重新累积, 而**两个崩跌锚会留在 24 锚窗内约 23 个锚(≈3.8 天, 到 ≈09-11)**。这期间该 ALERT 可能每日复现, **不得据此推断"书坏了"**。它离清除只差 0.001 —— 只要非崩跌锚均值好于 **−0.0108**(当前 −0.0119)即自动消除。

### ⑤ 执行漏斗与记账(停机第五锚)
orders **230 = `blocked_by_halt` 229 + `skipped_min_notional` 1**; fills 0; 拒单真实率 0.0%; requote/chase 臂空。
placement `behind` 占比 **0.43**(前三锚 0.469 / 0.515 / 0.539)—— **回落**, 印证 20Z 判读"在噪声内, 不作判断"是对的。
NAV **82,236.03** · target_gross 164,473.73 vs NAV×2.0 = 164,472.05, 差 **+1.68** ✓ · venue_gross 0 · 已实现 **0.00**(新的一天) · flow **0.0** · truncated False · readback 全零 · `anchor done rc=0` 00:40:07Z · 权重峰值 **292**。
`per_name_stop`: **冷却 13 / 停止 0**(SKRUSDT 冷却期满恢复可入, 14→13)。撤名残差 −8,202.79(−4.99%)/ 15 名。

### ⑥ ★ guard_twin 的第三次预言兑现: DISAGREE 已消失
09-06 我判 DISAGREE 是"平仓日两把尺子窗口不同"的口径现象、不是缺陷, 并预期新的一天会消失。**实测 00:44Z 与 01:04Z 两次 nav 行新鲜时均 `AGREE`**(day_twin −0.009 vs arith −0.002, 相差 0.007pp, 远在 0.5pp 容差内), `gap=-0.00`, `lev=0.0`。⇒ 该判读成立, **09-06 那串 DISAGREE 就此结案**。

### ⑦ 停机的机会成本 —— 三窗齐了, **结论翻转为"省钱"**
| 窗 | 纸面书净额(单位书) |
|---|---|
| 12Z→16Z | **+14.00** |
| 16Z→20Z | **−4.70** |
| 20Z→00Z | **−21.39** |
| **合计** | **−12.09 bps** |

⇒ **停机三窗净"省"了 12.1 bps, 不是花掉。** 我在 20Z 只有两窗时报的是"放弃约 9.3 bps"(成本), 第三窗到齐后**符号翻转**。这正好是"单窗读数是噪声"的现成例子 —— **两个数据点的方向不可外推**。markout 回填 00:40Z written 2 / pending 18, `expired=0 terminal=0`。

### 判定
**五个停机锚全部按设计工作, 无一需要处置。** 两条新 HIGH 告警均查到实测机制, 均为停机的必然产物(一条日切、一条回声), 04Z 后一条自愈、一条需约 3.8 天滚出窗口。**下一锚 04Z = 复场首锚, 一次性重建 @2.0×, 05:10Z 验收(定时 39722150)。今日禁划转纪律仍在。**

## 04Z 复场首锚(1788753600)—— 建成 62%, 主因 = 场所 −4400 限制(用户裁定: 照常, 不干预)
> 04:45Z 只读排查, 无任何写操作。完整验收由 05:10Z 定时 `39722150` 按冻结门判, **本节不代替它, 也不改门**。

### 链路时序(VERIFIED `anchor_runs.log`)
生产者 04:20:06Z 落盘(sel 246, members 400, cov 1.0, fund_updates 354, forced_exit 1, w3 [0.2941, 0.0884, 0.6176], runtime 245.9s)→ combo n=245, gross_norm 0.8277 → phase_A **04:24:59Z**(book_source external, nominal_anchor 1788753600)→ k 窗 900s → phase_B 04:45:11Z(`k_cancel: cancelled 60, already_terminal 142`)→ phase_C 04:45:12Z(anchors_row ✓, readback 227 行, daily_nav ✓)。

### 245 个目标名的去向(按唯一符号归类, VERIFIED)
| 归类 | 名数 |
|---|---|
| ① **成交, 有仓位** | **145** |
| ② **场所 `[-4400]` 只允许减仓** | **67** |
| ④ 已挂单但 k 窗内未成交(被撤) | 13 |
| ⑤ 未提交(其它) | 2 |
| 未进订单(最小名义 / 14 个冷却名等) | 18 |

- **venue gross 102,218 USDT / 目标 164,470 = 62%; 实际杠杆 1.24× 而非 2.0×; net/gross **+7.58%**(净多 7,749 USDT ≈ 9.4% NAV)。**
- 已提交 202 行中成交 145 = **72%**; post-only `-5022` 45 行 + requote 1 行(重建锚的正常量级, 参照 E-0903-D 入金重建 76%)。

### ★ 主因: 场所量化交易规则限制(不是书、不是信号、不是执行缺陷)
报错逐字: `[-4400] Futures Trading Quantitative Rules violated, only reduceOnly order is allowed` —— 账户在这些标的上**只被允许减仓**。
**历史(全部日文件扫描, VERIFIED)**: 08-26 **75 行** · 08-27 **24 行** · 08-28→09-06 **0 行(十天)** · 09-07 **68 行**。累计受影响 **136 个不同符号**。
⇒ **它只在大规模一次性重建当天出现**(08-26 = 1.5×→2.0× 一步建仓 = E-0826-F 当天; 09-07 = 空仓→2.0× 重建), 且**两次都在一天内自行消退**; 按标的触发并轮换, 非账户整体封禁。

### 处置: **照常, 不干预(用户 09-07 裁定)**
- 下一锚(08Z)继续对这 67 个名下单, EMA 目标持续, gross 自然向 2.0× 收敛; 不做任何加急建仓、不改 k 窗、不改书。
- 依据: −4400 是场所侧状态, 我方任何动作都不影响它消退; 干预只会引入新的不确定性。
- **方向敞口登记**: 建成期间书带 +7.58% net/gross 的非计划净多(被挡的 67 名不是随机分布在多空两侧)。量级检验: 市场跌 5% ⇒ 约 −387 USDT, 远离 cond2 的 −3,289 线, **不构成风控事件, 但要在 08Z 复看是否收敛**。
- **05:10Z 验收预期为红**: 冻结门写的是 `gross → 1.9-2.05×NAV`, 现 1.24×。**门不改**(看过数字后改判据是禁止的), 到时如实记红并注明根因为场所限制。
