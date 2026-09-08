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
3. [B_EXPECTED] 重整后 **5 名**跨过 min_notional(1000FLOKI/1000LUNC/1000SHIB/AIXBT/ASTER)。
4. [B_EXPECTED] **6 名**场所扣留 reduce-only(其中 1000LUNC/ASTER 进入 reducing)。
5. [B_EXPECTED] **16 个** maker 被 −5022 拒(20Z 18)。
6. [C_MEASURE] 限流计数差 **755 权重/分钟**, 归属仍未定(封禁 IP 是 CloudFront 边缘节点), 不喂任何决策。

**未 PushNotification**: 无回滚级异常; 日内 +0.215%; guard_twin ledger 恒等式闭合; 杠杆/中性/守护全部带内。
