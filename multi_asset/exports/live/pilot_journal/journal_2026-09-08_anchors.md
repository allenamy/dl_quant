> **创建:** 2026-09-08 | **Session:** b9646a9e | **状态:** 只追加 | **口径:** 每锚一次深查, 同锚重触发只报增量; 实盘零接触

# 2026-09-08 逐锚深查

## 00Z 锚(00:24Z 执行, 00:51:48Z `anchor done rc=0`; 01:4xZ 记; 全深度)

**一句话**: 全项通过。**执行质量连续第三锚改善**(maker 57→79→**89%** 名义, markout −3.98→−1.31→**−0.62** bps, −5022 33→25→**20.5%**)。新 UTC 日首锚, 日内 **+0.215%**。

### ① 三守护(按句柄验) — 全绿
`shadow_loop_v3` PID **10900** ≡ `shadow.lock` ✓ · `combo_live_daemon` PID **30944** ≡ `combo_live_daemon.pid` ✓ · `sidecar_daemon` PID 30943(无 pid 文件系设计)· exec_n6 沙盒 50689(预期)。

### ② 信号六项 — 全绿
| 项 | 读数 | |
|---|---|---|
| `fund_updates` | **451** | ✓ 00Z 是 8h 结算锚, 稳态 ~453 |
| `forced_exit_n` | 1 (gross 0.0021) | 20Z 为 2 |
| sel / members / coverage | 247 / 400 / 1.0 | ✓ |
| fetched / missing / future_dropped | 450 / 0 / 0 | ✓ |
| **掩码算术** | `0.302/(0.302+0.6265) = 0.32526` ≡ 落盘 `0.3252` | ✓ **逐位** |
| combo | anchor 1788825600 匹配 · ok/reader_ok · age **0.3s** · n 246 gross 0.8390 · 32.4s rc=0 | ✓ |
| kc/fc · FTRIM | `own`/`own` · 排除 **8** 名 rn8 覆盖 1.000 | ✓ |
| **反事实改写幅度** | **20.86%**(20Z 21.44%, 16Z 21.24%; 增量 **−0.58pp**) | **回落**, 升级判据更远 |

### ③ 执行漏斗(按 `anchor_ts`)— **连续第三锚改善**
| 项 | **00Z** | 20Z | 16Z | 模板带 |
|---|---|---|---|---|
| 唯一成交 / 名义 | 199 / 5,980 | 228 / 6,198 | 276 / 7,596 | — |
| **maker 笔 / 名义** | **83% / 89%** | 79% / 83% | 57% / 56% | ≥90%(**逼近**) |
| fee | **2.33 bps** | 2.50 | 3.32 | 1.80-2.3(**已无 BNB 折扣**; ×0.9 = 2.10 深入带内) |
| 换手/gross | **3.60%** | 3.75% | 4.6% | ✓ 2-5.5% |
| **+60s markout** | **−0.62 bps @99%** | −1.31 @97% | −3.98 @75% | 持续改善 |
| `rate_5022` | **20.5%**(34/166) | 24.7% | 33.1% | 持续改善 |
| placement behind | **44%** | 51% | 52% | ≈50%(近 7 锚 43-53%, 均 48%) |
| requote 分臂 | requote 36 / direct 15 / exempt 2 | 44/16/2 | 48/32/1 | — |
| 终态 | skipped_min_notional 208 · partial_expired 150 · venue_reject 35 · filled 19 · skipped_no_chase_arm 7 | | | |

### ④ 记账 — 全绿
`NAV 82,782.42` · `venue_gross 166,133` ⇒ **杠杆 2.0069×** ✓ · `venue_net −522` / **net/gross −0.0031** ✓ · `opening_halted False` · regime **calm** · `rows_persisted 419`
**当日 1 行 NAV**(新 UTC 日首锚), `external_flow=0` / `realised_truncated=False` ⇒ 守卫可判, **日内 +0.215%**。
**FUNDING_FEE**(00Z = 8h 结算锚): **234 名 −10.76 USDT**, 读龄中位 11,796 s(**结构性**: 00Z 结算前最新仓位读是 20:24Z 那次)。
`phase_C`: `anchors_row true` / `readback 234` / `daily_nav_row true` / `cooldown_n 12` / `net_over_gross −0.003143` ✓
`state/anchor_runs.log` 末行 **`2026-09-08T00:51:48Z anchor done rc=0`** ✓

**★ guard_twin: `AGREE(ledger-only; nav row stale)`, 且这是仪器的正确行为。** `day_pct_twin −0.040` 与 `day_pct_arith_on_daily_nav +0.215` 相差 0.26pp, 但孪生**自己置 `comparable = false`** —— 因为 NAV 行已陈旧 43.4 分钟, 且孪生的 `prev_close_src = twin:2026-09-07T23:46:48Z`(自身快照)与 daily_nav 的日界不同。它据此退回 **ledger-only** 判据, 而账本恒等式闭合到 **3.49e-10 USDT**(USDT wallet 82,417.18966885 vs sum_income 82,417.18966884965), `disagreements = []`, `transfers_today = 0`, `lev_twin 2.018`。
⇒ **这是「仪器声明自己的盲区而不是产出一个假比较」的正面案例**, 与「我的仪器在极端处失效」相反。

### ⑤ 执行质量
- **尺寸梯度三桶: 仍无法评估** —— `exec_probe/v2/KILL` 在盘(08-22 起, **第 17 天**)。
- markout 回填: 09-08 `pending=199 written=183 requests=167`(近乎追平); 09-07 补尾 `pending=112 written=19`。
- **placement 单名连抽: 无异常。** 近 7 锚(跨日)全程在场 218 名: 最长连抽分布 {1:2, 2:76, 3:70, 4:42, 5:17, 6:8, 7:3}; **7/7 全同实测 3, 公平硬币期望 3.4** ⇒ 带内。每锚 behind 43/48/51/46/53/53/45%。

### ⑥ 告警 6 条 —— 两条结构性项**连续第三锚**出现
1. **[HIGH / A_DECIDE] 仓位对账 5 名超出重估范围 —— 已采纳场所真值。**(20Z 为 12 名, **改善**)本锚唯一最高层级告警。
2. **[C_MEASURE] 撤名残差 −9,030.14 USDT = 目标 gross 的 −5.44%(阈值 >2%)**, 仍由 **14 个 `maxNotionalValue=0` 扣留名**造成(20Z −5.91%)。**连续第三锚超阈**, 是冻结宇宙 + 场所扣留叠加的结构性缺口。
> **★ 更正 2026-09-08 06:0xZ(E-0902-A 复发, 我的错)**: 上一条把「撤名残差」当成**书想要却拿不到的单边敞口**报出, **是错的**。读码(`anchor_loop.py` L1562 `apply_withhold_and_reshape`)确认: `net_before` 是 **pop 之后、reshape 之前**的失衡量, 而 reshape **当场把它修回中性** —— 告警原文即写「已重整回中性」, 账本 `net_after ≈ 3.6e-12`, `venue_net/gross` 逐锚在 ±0.3% 内。该告警分层是 **C_MEASURE / INFO / recorded-only**, 策略注释为 "informational unless it grows"。**它从来不是一个待处置的敞口, 我把告警文案当风险读了四次。**
> **真正留在书上的是 `clamped_after_reshape`**(held untradable 被场所钉住、**故意不吸收**的残余), 而该字段自 **2026-09-05 12Z 起因变量名碰撞已停止落盘**(见 `ERROR_LEDGER` **E-0908-A**)。
3. [B_EXPECTED] 重整后 **5 名**跨过 min_notional(1000FLOKI/1000LUNC/1000SHIB/AIXBT/ASTER)。
4. [B_EXPECTED] **6 名**场所扣留 reduce-only(其中 1000LUNC/ASTER 进入 reducing)。
5. [B_EXPECTED] **16 个** maker 被 −5022 拒(20Z 18)。
6. [C_MEASURE] 限流计数差 **755 权重/分钟**, 归属仍未定(封禁 IP 是 CloudFront 边缘节点), 不喂任何决策。

**未 PushNotification**: 无回滚级异常; 日内 +0.215%; guard_twin ledger 恒等式闭合; 杠杆/中性/守护全部带内。

---
## 04Z 锚深查(04:24Z 执行, 04:51:05Z `anchor done rc=0`; 05:3xZ 记; 全深度)
> 说明: 04:48Z 曾为用户盘面问题做过归因与崩跌暴露(见下 §归因), **未做模板 ②③④⑤** —— 本条为该锚的首次全深度深查。

**一句话**: 全项通过, **日内 +1.502%**(00Z→04Z 大涨)。执行较 00Z 略回落但仍在带内; **两条结构性告警连续第四锚**。

### ① 三守护(按句柄验) — 全绿
`shadow_loop_v3` PID **10900** ≡ `shadow.lock` ✓ · `combo_live_daemon` PID **30944** ≡ `combo_live_daemon.pid` ✓ · `sidecar_daemon` PID 30943(无 pid 文件系设计)· exec_n6 沙盒 50689。

### ② 信号六项 — 全绿
| 项 | 读数 | |
|---|---|---|
| `fund_updates` | **351** | ✓ 04Z 非结算锚, 稳态 ~353 |
| `forced_exit_n` | **0** | 20Z 曾 2, 00Z 曾 1 |
| sel / members / coverage | 249 / 400 / 1.0 | ✓ |
| fetched / missing / future_dropped | 450 / 0 / 0 | ✓ |
| **掩码算术** | `0.3015/(0.3015+0.6302) = 0.32360` ≡ 落盘 `0.3236` | ✓ **逐位** |
| combo | anchor 1788840000 匹配 · ok/reader_ok · age **0.6s** · n 247 gross 0.8418 · 30.6s rc=0 | ✓ |
| kc/fc · FTRIM | `own`/`own` · 排除 **8** 名 rn8 覆盖 1.000 · carry_bps 1.761 | ✓ |
| **反事实改写幅度** | **20.86%**(与 00Z **完全持平**, 增量 **0.00pp**; 20Z 21.44%) | 平台化确认 |

### ③ 执行漏斗(按 `anchor_ts`)
| 项 | **04Z** | 00Z | 20Z | 模板带 |
|---|---|---|---|---|
| 唯一成交 / 名义 | 215 / 5,430 | 199 / 5,980 | 228 / 6,198 | — |
| **maker 笔 / 名义** | **76% / 78%** | 83% / 89% | 79% / 83% | ≥90%(**回落**) |
| fee | **2.65 bps** | 2.33 | 2.50 | 1.80-2.3(无 BNB 折扣口径; ×0.9 = 2.39 仍略超) |
| 换手/gross | **3.24%** | 3.60% | 3.75% | ✓ 2-5.5% |
| **+60s markout** | **−1.52 bps @95%** | −0.62 @99% | −1.31 @97% | 回落 |
| `rate_5022` | **22.5%**(34/151) | 20.5% | 24.7% | 带内波动 |
| placement behind | **45%**(182/404) | 44% | 51% | 近 8 锚 43-53% 均 48% |
| requote 分臂 | requote 34 / direct 16 / exempt 2 | 36/15/2 | 44/16/2 | — |
| 终态 | skipped_min_notional 203 · partial_expired 131 · venue_reject 38 · filled 26 · skipped_no_chase_arm 6 | | | |

### ④ 记账 — 全绿
`NAV 83,845.50` · `venue_gross 167,490` ⇒ **杠杆 1.9976×** ✓ · `venue_net +487` / **net/gross +0.0029**(00Z 为 −0.0031, 本锚偏多)✓ · `net/equity +0.0058` · `opening_halted False` · regime **calm** · `rows_persisted 404`
**当日 2 行 NAV 82,782 → 83,845, 日内 +1.502%**, `external_flow=0` / `realised_truncated=False` ⇒ 守卫可判。
**FUNDING**: 04:00Z 结算 **169 名 −11.26 USDT**(4h 间隔名在每个 4h 锚结算); 当日累计 **−22.07 USDT**。
`phase_C`: `anchors_row true` / `readback 235` / `daily_nav_row true` / `cooldown_n 12` / `net_over_gross +0.002905` ✓
**guard_twin AGREE**(05:07:19Z): `eq=83,669.65 nav=83,845.50 day_twin=1.057 arith=1.502 anchor_rc=0 lev=2.005 gap=+0.00 deep=[]` —— day_twin 与 arith 差 0.44pp 系**日界口径不同**(孪生日起点 ≈00:00Z 自身快照, daily_nav 日起点 = 09-07 末行), 孪生自身判据 `gap=+0.00` 通过。
`known_gaps`: 6 名 gross **195.4** net **−98.8**(00Z 为 7 名 406.8/394.9, **大幅收窄**)。

### ④b 归因(00Z→04Z, 04:48Z 已算, 覆盖 100%)
价格 P&L **+1,105.9** / NAV 实变 **+1,063.1**。**多头腿 +784(71%) / 空头腿 +322(29%) —— 两条腿都赚 ⇒ 离散度而非 beta**(ETH −0.38% / SOL −0.57%, 均做空小仓)。
最赚: **SOPH +45.04% · IOST +26.48% · FORM +24.82%**(单锚), 前 5 名占总盈利 42%; 盈 127 / 亏 107。
**★ 与 09-07 16Z 亏损名高度重合**: SOPH 当时 −10.49%、XAN −7.35%、BULLA −2.61%, 今日全在赚 ⇒ **同一暴露, 反向。**
**崩跌形态暴露**(readback 隐含价 24h 窗, 覆盖多头 gross 67%): 24h 涨 ≥20% 的 **2 名 gross 1,536 = 全书 0.9%**(SOPH +115.4%, IOST +48.1%)。⚠ 本地 kline 缓存仅覆盖多头 gross 的 **11%**, 不可用于此判断; 窗口只有 24h 而受据形态是 3 日, **上述为下界**。

### ⑤ 执行质量
- **尺寸梯度三桶: 仍无法评估** —— `exec_probe/v2/KILL` 在盘, **第 17 天**。
- markout 回填: 09-08 `pending=221 written=192 requests=172`; 09-07 补尾 `pending=76 written=11`。
- **placement 单名连抽: 无异常。** 近 8 锚全程在场 **217 名**: 最长连抽分布 {1:2, 2:64, 3:71, 4:44, 5:21, 6:10, 7:4, 8:1}; **8/8 全同实测 1, 公平硬币期望 1.7, 95% [0, 5] ⇒ 带内**。每锚 behind 43/47/51/46/53/53/45/45%。

### ⑥ 告警 6 条 —— 两条结构性项**连续第四锚**
1. **[HIGH / A_DECIDE] 仓位对账 7 名超出重估范围 —— 已采纳场所真值。**(00Z 5 名, 20Z 12 名)本锚唯一最高层级。
2. **[C_MEASURE] 撤名残差 −9,001.59 USDT = 目标 gross 的 −5.39%(阈值 >2%)**, 仍由 **14 个 `maxNotionalValue=0` 扣留名**造成(00Z −5.44%, 20Z −5.91%)。**连续第四锚超阈, 数值稳定在 −5.4% 附近。**
> **★ 更正 2026-09-08 06:0xZ(E-0902-A 复发, 我的错)**: 上一条把「撤名残差」当成**书想要却拿不到的单边敞口**报出, **是错的**。读码(`anchor_loop.py` L1562 `apply_withhold_and_reshape`)确认: `net_before` 是 **pop 之后、reshape 之前**的失衡量, 而 reshape **当场把它修回中性** —— 告警原文即写「已重整回中性」, 账本 `net_after ≈ 3.6e-12`, `venue_net/gross` 逐锚在 ±0.3% 内。该告警分层是 **C_MEASURE / INFO / recorded-only**, 策略注释为 "informational unless it grows"。**它从来不是一个待处置的敞口, 我把告警文案当风险读了四次。**
> **真正留在书上的是 `clamped_after_reshape`**(held untradable 被场所钉住、**故意不吸收**的残余), 而该字段自 **2026-09-05 12Z 起因变量名碰撞已停止落盘**(见 `ERROR_LEDGER` **E-0908-A**)。
3. [B_EXPECTED] 重整后 5 名跨 min_notional(1000LUNC/1000SHIB/AIXBT/ASTER/TURBO)。
4. [B_EXPECTED] **7 名**场所扣留(ASTER/1000LUNC 进入 reducing)。
5. [B_EXPECTED] **20 个** maker 被 −5022 拒(00Z 16, 20Z 18)。
6. [C_MEASURE] 限流计数差 **656 权重/分钟**, 归属未定, 不喂决策。

**未 PushNotification**: 无回滚级异常; 日内 **+1.502%** 距 −2.68% 告警线 4.2pp、距 −4.0% 停机线 5.5pp; guard_twin AGREE; 杠杆/中性/守护全部带内。

---
## 08Z 锚深查(08:24Z 执行, 08:54:14Z `anchor done rc=0`; 09:4xZ 记; 全深度)

**一句话**: **单锚 −1.34%**(04Z 83,845 → 08Z 82,720), 把日内 +1.502% 吐回到 **+0.140%**; **XANUSDT 一名 −665 = 总亏的 59%, 单锚 −39.76%**。执行面 maker 继续下滑但 markout 反而翻正。**★ 补丁 `64c4a16` 验收通过。**

### ★★ 补丁验收(本锚首要任务) — **通过**
08Z 行的 `reshape` 字段**恢复为撤名重整报告**:
`net_before −7,353.13` · `net_after **−1.15e-12**` · `gross_before 153,547 → gross_after 165,729` · `n_popped 14` · `names_crossed_floor 6 名`
**`clamped_after_reshape`(三天来首次读到)**: `names [1000SHIB, ERA, TNSR, TREE, TURBO]` · `pinned_net_usdt +12.24` · **`net_shift_usdt −49.99`** · **`book_net_usdt −49.99`**
⇒ **场所强制、故意不吸收的残余 = −49.99 USDT**(占 gross 166,999 的 **−0.030 bps**)—— 这就是"书的净额为什么不是精确零"的账本解释。
**切换点精确**: 09-08 三锚中 00Z/04Z 仍是拒单率报告(补丁前), **08Z 起是撤名报告**(补丁后)。09-05 3/6 · 09-06 0/6 · 09-07 0/6 · 09-08 1/3。
⚠ **我方一处自我更正**: 此前称「`post_only_refusals` 字段为空」—— **找错地方了**。该字段本就落在 **phase_A 日志**(本锚内容完整: `n_reached 204 rate_5022 0.299`), 从来不在 anchors 行。

### ① 三守护 — 全绿
`shadow.lock` 10900 ≡ PID · `combo_live_daemon.pid` 30944 ≡ PID · sidecar 30943 · exec_n6 沙盒 50689。

### ② 信号六项 — 全绿
`fund_updates` **451** ✓(08Z 8h 结算锚, 稳态 ~453)· `forced_exit_n` **1**(gross 0.0041)· sel **251** / members 400 / coverage **1.0** · fetched 450 missing 0 future_dropped 0 · runtime 285.9s
**掩码算术 `0.306/(0.306+0.6239) = 0.32907` ≡ 落盘 `0.3291`** ✓ **逐位**
combo anchor 匹配 · ok/reader_ok · age **1.0s** · n 250 gross 0.8428 · 45.2s rc=0 · kc/fc `own` · FTRIM **7** 名
**`carry_bps` 0.899**(04Z 1.761, **腰斩**)· 生产者 `turnover 0.0213`(04Z 0.01156, **近乎翻倍**)
**反事实改写幅度 20.72%**(04Z 20.86 / 00Z 20.86)—— **连续三锚 20.7–20.9%, 平台化确认**

### ③ 执行漏斗 — **maker 继续下滑, 但 markout 翻正**
| 项 | **08Z** | 04Z | 00Z |
|---|---|---|---|
| 成交 / 名义 | 275 / 7,557 | 215 / 5,430 | 199 / 5,980 |
| **maker 笔 / 名义** | **69% / 71%** | 76% / 78% | 83% / 89% |
| fee | **2.88 bps** | 2.65 | 2.33 |
| 换手/gross | **4.53%** | 3.24% | 3.60% |
| **+60s markout** | **+4.54 bps @88%** | −1.52 @95% | −0.62 @99% |
| `rate_5022` | **29.9%** | 22.5% | 20.5% |
| `venue_reject` 终态 | **66** | 38 | 35 |
| placement behind | **54%** | 45% | 44% |
| requote 分臂 | requote 62 / direct 30 | 34/16 | 36/15 |

**markout 翻正 +4.54 是本锚特有**: 成交后 60 秒 mid 普遍朝我方有利方向移动 —— 与"锚内发生了方向性大幅移动"一致, **不是执行变好**。

### ④ 记账
`NAV 82,719.86` · `venue_gross 166,999` ⇒ **杠杆 2.0189×**(带内, 但为今日最高)· `venue_net −1,073` / **net/gross −0.0064**(今日最大倾斜; 00Z −0.0031, 04Z +0.0029)· regime **calm** · `rows_persisted 474`
**当日 NAV 82,782 → 83,845 → 82,720, 日内 +0.140%**; `flow=0` / `trunc=False` ⇒ 守卫可判。**距 −2.68% 告警线 2.8pp, 距 −4.0% 停机线 4.1pp。**
**FUNDING 08Z(8h 结算锚)**: 两组结算合计 **234 名 −5.54 USDT**(182 名 −4.88 + 52 名 −0.66); 当日累计 **−27.63**。⚠ 我初读只取了最后一组(52 名)即称"异常", **是我读法错**, 非异常。
`phase_C`: `anchors_row true` / `readback 239` / `daily_nav_row true` / `cooldown_n 12` / **`counters {"XANUSDT": 1}`** / `net_over_gross −0.006427`
**guard_twin `AGREE(ledger-only; nav row stale)`** —— NAV 行陈旧 0.7h, 退回 ledger 判据。

### ④b ★ 归因: 单锚 −1.34% 是一个名字
覆盖 100%。价格 P&L **−1,123.7** / NAV 实变 **−1,125.6**(差 −1.9 ⇒ 几乎全是价格)。
**多头腿 −976(87%) / 空头腿 −147(13%)**。亏 118 / 盈 116, **前 5 名占毛亏 49%**。

| 名 | P&L | 仓位 | 锚内 |
|---|---|---|---|
| **XANUSDT** | **−665.1** | +1,673(多) | **−39.76%** |
| IOSTUSDT | −119.9 | +691(多) | −17.35% |
| PIEVERSEUSDT | −106.5 | +1,726(多) | −6.17% |

**XANUSDT 一名 = 总亏的 59%。** 其全天轨迹(隐含价): 09-07 04Z 0.021525 → 16Z 0.018786 → 09-08 04Z 0.021220 → **08Z 0.012783**。`per_name_stop.counters` 已记 **XANUSDT: 1**(尚未 stopped)。
昨日赢家的分化: SOPH **+57(+6.75%)** · FORM **+83(+11.33%)** 仍在涨; **IOST −120(−17.35%)** 回吐。

### ④c ★★ 与我 3 小时前风险回答的对账 —— **我的前兆筛选没抓到它**
06:0xZ 我用 24h 涨幅 ≥20% 作为"已记录崩跌形态"的筛子, 报出 **2 名 = 全书 0.9%**(SOPH +115.4%, IOST +48.1%)。
**XANUSDT 不在那个名单里**(其 24h 涨幅低于展示的第 14 名 +16.4%), 却是本锚 **59% 亏损的来源**。
⇒ **「3 日涨 ≥20%」这个前兆条件, 对本次最大单名崩跌无效。** 这不推翻既有受据(那条来自 09-06 的 7/9 崩跌名), 但**证明它不是充分筛子**, 我此前给的"0.9% 暴露"是**下界且可能严重低估**。已记为限制。
(IOST 确实在名单里且确实回吐 −17.35% —— 筛子对它有效。)

### ⑤ 执行质量
- **尺寸梯度三桶: 仍无法评估**(`exec_probe/v2/KILL`, **第 17 天**)
- markout 回填: 09-08 `pending=288 written=240 requests=222`; 09-07 补尾 `pending=58 written=7`

### ⑥ 告警 6 条
1. **[A_DECIDE] 仓位对账 12 名**超出重估范围(04Z 7 名, 00Z 5 名 —— **本锚回升**)
2. **撤名残差 −7,353.13 = −4.44%**(04Z −5.39%, 00Z −5.44%, 20Z −5.91% —— **连续第五锚超阈但在收窄**)。⚠ 该数**已确认不是敞口**(reshape 当场修回中性, `net_after −1.15e-12`), 见 09-07 journal 的更正块与 **E-0908-A**。
3. 重整后 **6 名**跨 min_notional · 4. **7 名**场所扣留 · 5. **35 个** maker −5022(04Z 20, 00Z 16 —— **翻倍**)· 6. 限流差 **828 权重/分钟**(归属未定)

**未 PushNotification**: 日内仍 **+0.140%** 为正, 距停机线 4.1pp; guard_twin AGREE; 杠杆/中性带内; 无回滚级异常。**单名崩跌属已记录形态(砍尾家族六形态已判负), 不触发动作。**
