# pilot journal · 2026-09-12(UTC 日)· 只追加

> 00:00Z 锚的全深度条目写在 `journal_2026-09-11_anchors.md` L150–240(当时按会话续写); 本文件从 04Z 锚起。

## 2026-09-12 04:00Z 锚 · 全深度深查(只读, 实盘零接触)

**锚**: canonical 1789185600(04:00Z, **非结算锚**)/ 执行器 anchor_ts 1789187043.614(04:24:03Z)/ rid A1789187040。**结论: 无异常处置需求; 一项恶化(net/gross 连续第二锚越 ±1% 观察带且加深到 −1.12%), 一项极端读数(neutrality 同侧 taker 98.7 bps, 33 笔基数), 尺寸梯度非负性连续第三锚不成立; 其余全在带。**

### ① 三守护 — 全绿(句柄为准)
| 守护 | 句柄 | PID | launchd | 运行时长 |
|---|---|---|---|---|
| shadow_loop_v3 | `shadow.lock` = 10900 | 10900 ✓ | shadowloop | 6d 17:00 |
| sidecar_daemon.sh | — | 30943 | sidecar 30943 ✓ | 13d 00:43 |
| combo_live_daemon.sh | `fea171/combo_live_daemon.pid` = 30944 | 30944 ✓ | combolive 30944 ✓ | 13d 00:43 |

PID 50689 = `cc_tmp/exec_n6_sandbox` 研究沙箱, 非在役。**★ 固定新增项(RUNBOOK_b681ca5 §3#6)**: 执行器运行树 `HEAD d040c74` ≠ `origin/main b681ca5` ⇒ 运行树落后 = 有未部署改动(b681ca5 部署验收进行中, 窗 05:00–08:15Z), 照常报, 本锚不动作。

### ② 信号六项 — 全部在带
status OK / coverage 1.0 / members 400 / sel 266 / **fund_updates 355**(4h 非结算锚稳态 ~353 ✓)/ forced_exit_n **0** / turnover 0.0264 / gross_pos 0.8975 / carry 1.125 bps / cost 0.088 bps / runtime 260.9s / fetched 450 missing 0 / future_dropped 0 / data_max_ts = 锚 ✓。
w3 = [0.3250, 0.0998, 0.5751] ⇒ **w3_masked king = 0.3611**, 与 target_combo 自报 [0.361061, 0.0, 0.638939] 一致 ✓(上锚 0.3557)。
combo_live_status: anchor 匹配 ✓ / ok / done / **reader_ok true** / n 263 / gross 0.8650 / age_s 0.4 / 04:21:12Z rc=0。
target_combo: phi 0.45 / combo_v2main_norev24 / **kc·fc 均 own** ✓ / **n_f10_scored 400** ✓ / net_after_reshape 0.0 / rho_kc_fc 0.9374(上锚 0.9369)。
**反事实改写 = 24.4%**。序列 24.53(16Z)→ 24.50(20Z)→ 24.52(00Z)→ **24.4**(本锚), 增量 **−0.1pp**, **未触发升级**。
生产者 paper 计分(对上锚 00Z 书): gross −0.424 / net −1.568 bps(该计分器在给已退役 king 书计分, STATE 已记, 不喂决策)。

### ③ 执行漏斗(按执行器 anchor_ts 归属; fills 去重=**后写胜出**)
orders **489**(= rows_persisted 489 ✓)/ fills 去重 **287**
终态: skipped_min_notional 190(maker 47 + topup 143)· partial_expired 179 · **venue_reject 54** · filled 47 · skipped_no_chase_arm 19
order_type: maker 280(attempt 1 = 276, 重挂 attempt 2 = 4)/ topup_taker 209
**venue_reject 54** = **−5022 首发 49** + 重挂再拒 4 + **−2027 一单**(PIEVERSEUSDT); 首发 post-only 穿价率 **49/210 = 23.3%**(升级线 40%)
分臂拒单率(maker 行, terminal_reason=venue_reject): **join 0.2520**(31/123)/ **behind 0.1467**(22/150)/ exempt 0.1429(1/7)
**behind 占比 = 0.554**(149/269, 排除 exempt)— 设计点 0.50, 上锚 0.5037
requote 44 / direct 26 / exempt 2; requote report: candidates 23 → 落单 19, 再拒 4 转 taker; chase 87 / no_chase 92
换手三口径: anchor_report **7.5%**(上锚 6.7%)/ 成交 Σ 9,268U ÷ venue gross = 3.98% / maker attempt-1 意图 Σ 13,257U = 5.65% target gross; 生产者 turnover 2.64% ⇒ 口径差 **2.84×**(上锚 2.79×, r11 已登记未闭合)

### ④ 记账
| 项 | 值 | 判 |
|---|---|---|
| venue_gross_usdt | 232,973.99 | target 234,516.13 ⇒ **0.9934** ✓ |
| NAV | 117,452.35 | gross/NAV = **1.9836** ≈ 2.0 ✓ |
| **net_over_gross** | **−1.1219%** | **★ 越 ±1% 观察带, 连续第二锚, 加深**(−0.7169 → −1.0192 → −1.1219); = 执行器 1.5% 中性带的 74.8%, 未动作 |
| neutrality_price | deficient=buy, 需 taker 2,613.70U, **同侧实测 taker 98.67 bps**(33 笔 / 1,422U 基数), 价 25.79U(下界) | ★ 极端读数(上锚 +17.38, 20Z −7.76), 只测不补 |
| net_over_equity | −2.2253% | — |
| opening_halted | False | ✓ |
| 04Z 结算 | 非结算锚, funding.jsonl 窗内 0 行 | ✓(当日 income 累计 FUNDING_FEE −24.11) |
| phase_C readback | 257 行 ✓ | — |
| per_name_stop | stopped 1 = IOSTUSDT(自 09-10 08:43Z, 非本锚)/ cooldown 9 | **本锚无新命中** ✓ |
| `state/anchor_runs.log` 末行 | `2026-09-12T04:57:28Z anchor done rc=0` | ✓ |
| watchdog | tripped=False, triggers [], metric_errors [] | ✓ |
| **guard_twin** | **AGREE**(ledger-only; nav 行 stale)eq=117,459.74 | ✓ |
| n_names_skipped | 65(上锚 91) | ↓ |
| known_gaps | **20 名**(上锚 9), gross 3,094U / net 2,774U, venue_cap = PIEVERSEUSDT 2,102U | ★ 上升 |
| reshape | net_before **−11,024.37**(−4.70% target gross; 上锚 −4.82%)→ net_after −8e-12 ✓; gross 220,719 → 234,587; floor_set_changed true(IOST/MANA 跨门, 只报不迭代) | ✓ |
| 限流 | peak_window_weight 760(上锚 731); rate_budget peak/min weight 810 / orders 233(自限 1000 / 300), waits 0 | ✓ |

**当日 NAV**: 前日收 117,515.79 → 00Z 118,120.06 → **04Z 117,452.35**: 本锚 **−667.71(−0.565%)**, 当日累计 **−63.44(−0.054%)**; external_flow 0。已实现 +132.59(REALIZED_PNL +158.85 / FUNDING_FEE −24.11 / COMMISSION −2.15); 未实现 2,065.34 → 1,322.37(−742.96)。连续四正日后本日目前小负。

### ⑤ 执行质量
- **maker 占比 行 0.6690 / 名义 0.7621** — 带 ≥0.90, **带外**(上锚 0.7579 / 0.7738), 名义略降; taker 占比 24%(上锚 23%)
- **费 2.7138 bps** — maker 恰 **2.0000** / taker 恰 **5.0000**, 287 笔 commission_asset **全 USDT**
- **markout 回填 262/287 = 91.3%** ✓(字段 `mid_at_fill_plus_60s`)
- **尺寸梯度三桶**(自建口径: maker attempt-1, intended_notional 三分位, Σ|filled|/Σintended): small **0.4579** / mid **0.6042** / large **0.5265**(上锚 0.62 / 0.78 / 0.57)⇒ **非负性仍不成立(mid > large), 连续第三锚同形状; 且三桶齐降**
- **chase 单名连抽**: 无名字 ≥2 次(最大 1)✓(上锚 23 名 2 次)

### ⑥ 异常处置 — **无需处置**; 本锚告警 6 条(上锚 7), 无新类型, 两条量变
1. `position reconcile: 10 名与场所差异超出重估范围 — 采用场所真值`(**上锚 5 → 10 ★ 加倍**, 第二次出现)
2. `撤名残差 −11,024.37 USDT = 目标 gross 的 −4.70%(>2% 门), 由 10 个撤下的名字造成`(含 BTCUSDT; 上锚 −4.82%, **连续第二锚**)
3. 重整后 2 名跨过 min_notional 门槛(IOST / MANA), `floor_set_changed: true`, 只报告不迭代
4. 8 个持仓名被场所扣住(maxNotionalValue=0), reduce-only(上锚 7): reducing ETC, add_blocked IOST / MANA
5. **−2027** PIEVERSEUSDT +2,102U(上锚 +2,124U), 每锚重现直到目标回落; 候选修复需用户字
6. 30 个 maker 被 −5022 拒, 残差按全额进 taker 补单(上锚 32)

上锚的「限流计数差值」告警本锚未出现。回滚缺省 / 生产者重启 / 整体回滚: **均未触发, 不动**。

### ⑦ 与上一锚(00Z)对比
| 指标 | 00Z | **04Z** | 向 |
|---|---|---|---|
| venue_reject(−5022 首发) | 56 (55) | **54 (49)** | ↓ 略改善 |
| 首发 post-only 穿价率 | — | **23.3%** | 升级线 40% 内 |
| join 臂拒单率 | 0.2148 | **0.2520** | ↑ 恶化 |
| behind 臂拒单率 | 0.1825 | **0.1467** | ↓ 改善 |
| maker 占比(名义) | 0.7738 | **0.7621** | → 带外持平 |
| 费 bps | 2.6786 | **2.7138** | ↑ |
| taker 占比 | 23% | **24%** | → |
| **net_over_gross** | −1.0192% | **−1.1219%** | **↑ 越带加深** |
| behind 占比 | 0.5037 | **0.554** | ↑ 离设计点 |
| 生产者 turnover | 2.404% | **2.64%** | ↑ |
| 执行器换手(anchor_report) | 6.7% | **7.5%** | ↑ |
| markout 回填 | 91.6% | 91.3% | → |
| **neutrality 同侧 taker bps** | +17.38 | **+98.67** | ★ 极端 |
| position reconcile 超范围名 | 5 | **10** | ↑ |
| known_gaps 名数 | 9 | **20** | ↑ |
| 尺寸梯度 s/m/l | .62/.78/.57 | **.46/.60/.53** | ↓ 齐降 |
| 反事实改写 | 24.52% | 24.4% | → |

### 待验证 / 推断分栏
**已验证(本机第一手)**: ①②③④⑤ 全部读数; 分臂拒单率; NAV 与损益分解; guard_twin AGREE; anchor done rc=0; 六条告警原文; 运行树 HEAD vs origin/main。
**待验证**: (a) **尺寸梯度非负性连续三锚不成立且本锚三桶齐降** —— 分桶仍为自建口径, 需与既有仪器对齐后再判; (b) 撤名残差 −4.7% / −4.8% 连续两锚, 20 锚基率回溯未做; (c) position reconcile 5 → 10 名: 是否与「撤下的 10 名」同一集合未逐名核; (d) neutrality 同侧 taker 98.67 bps 是 33 笔基数上的实测, 看 08Z 是否回落; (e) net/gross 三锚 −0.72 / −1.02 / −1.12 单调加深, 08Z 若越 1.5% 执行器中性带会自行动作(只报, 不干预)。
**推断**: (c) 大概率同集合(撤下名字场所有仓而目标为 0 ⇒ 差异 >5% 触发 reconcile 告警); taker 占比与费的上升同源于 −5022 拒单残差进 taker(与上锚同), 外因未测, 不下因果结论。

### 与研究线的交叉(只记, 不动)
- maker 费恰 2.0000 / taker 恰 5.0000 / 全 USDT ⇒ **BNB 折扣自 09-07 断, 至本锚第 6 日**, VIP0 底档; r11 定价 ≈ +1.5% NAV/年; 运维裁定域。
- 运行树落后 origin/main(b681ca5)⇒ 部署验收(E1)进行中; 本锚是 d040c74 上的倒数第二个锚(若 08Z 前部署)。

## 2026-09-12 06:05:30Z · 执行器部署 d040c74 → b681ca5(用户字 09-12; 非锚事件)

- **动作**(RUNBOOK §0 五前提在同一脚本内复核 5/5 真后执行): `git -C ~/dl_quant_live fetch origin main && git -C ~/dl_quant_live merge --ff-only b681ca5285e9620cb6d9158d72dc2d50b2d21109`; HEAD 现 = origin/main = b681ca5。无进程重启(执行器由 launchd 每锚新起)。
- **§2 核**: HEAD ✓ · 27 文件 +5098/−280 ✓ · state/ 外干净 ✓ · `ops/check_upstream_drift.py` rc=0 ✓ · compileall rc=0 ✓ · 烟测 identity_unknown / static_names / transport_resilience(92)ALL PASS ✓ · `com.dlquant.live.anchor` 在册 ✓。
- **部署前验收**(`docs/ACCEPTANCE_b681ca5_2026-09-12.md`, 隔离克隆, 05:43Z 快照): 神经价读者 19/19 锚逐位相等; 看门狗 43 日 0 差; 回滚排演 diff=0; 克隆电池 130/132 绿。**两红树无关**: 旧树 d040c74 克隆同快照直接跑同两套 ⇒ rc=1, FAIL 3+4 条, 三条 disposition payload sha 前 12 位 d19da6693f71 / bea0dd249993 / 78a55480d2cc 两树一致。归因: `.env` gitignored(克隆无); 账本事实 — A1789115039(09-11 08:23Z, E-0910-A 锁复发)involuntary 4,504U; PIEVERSE −2027 残差 ≈2.2kU 超自身 gross 1%(A1788999840 09-10 00:24Z 重建锚 gross 154,910 等)。
- **待办**: 08Z 首锚 §3 六条验收; 06:36Z 后运行目录电池作收据(预期 tests_disposition_matrix 红, 账本事实); tests_disposition_matrix 分类更新需裁定(否则挡 safe_commit); 52 行写回另裁。回滚 = §5 revert 链。

### 06:36:30–06:50:53Z · 运行目录全电池(RUNBOOK §2-6 部署收据, HEAD b681ca5)
- **132 套件 / 131 绿 / 1 红 = `tests_disposition_matrix`**(3 条真账本断言; payload sha 前 12 位 d19da6693f71 / bea0dd249993 / 78a55480d2cc 与克隆、旧树 d040c74 **三处逐字节同** ⇒ 账本事实: E-0910-A 锁复发锚 A1789115039 involuntary 4,504U; PIEVERSE −2027 残差超自身 gross 1% 于 A1788999840(09-10 00:24Z 重建锚)等)。`tests_env_loading` 运行目录 **14/14**(克隆红仅因 gitignored `.env`)。收据 `docs/receipts/rundir_battery_b681ca5_20260912T063630Z.log`; 逐套件日志 `~/dl_quant_live/state/acceptance/20260912T063630Z_*.log`。
- ⚠ 电池的 DRY_RUN 锚写进了共享的 `state/anchor_runs.log`: `06:37:05Z anchor start mode=DRY_RUN … 06:38:40Z anchor done rc=0`(arm: no venue contacted; orders/fills/anchors.jsonl 在该窗 0 行)。**08Z 深查读 log 尾时以 `mode=LIVE` 的锚为准**(`start_dryrun_clock.sh` L156 已注明该共享性质)。
- 运维后果(登记, 待裁定): 下一次 `safe_commit` 会被该套件挡住, 直到其分类按 E-0910-A / −2027 上限更新。

### 07:35:01–07:49:52Z · `tests_disposition_matrix` 重标定经 safe_commit 落地(非锚事件; 用户字「确保无误可以更新」)
- 运行目录 `ops/safe_commit.sh live/tests_disposition_matrix.py`: fetch 已最新 → **电池 132/132 ALL GREEN**(07:34:58–07:49:49Z)→ commit → push `b681ca5..77d9baf main`。运行树 HEAD = origin/main = **77d9baf**; 仅测试文件, 零运行时改动。
- ⚠ 电池再次在共享 `state/anchor_runs.log` 留下 DRY_RUN 锚行(07:3x–07:4xZ `mode=DRY_RUN`); 08Z 深查以 `mode=LIVE` 为准。
- 内容与收据: `docs/DESIGN_disposition_matrix_recalibration6_2026-09-12.md` §1–§4; 突变红日志 `docs/receipts/tests_disposition_matrix_recal6_mut_*.log`; safe_commit 日志 `docs/receipts/safe_commit_tests_disposition_matrix_20260912T073501Z.log`。

## 2026-09-12 08:00Z 锚 · 全深度深查 + **b681ca5 首锚验收(RUNBOOK §3)**(只读, 实盘零接触)

**锚**: canonical 1789200000(08:00Z, **8h 结算锚**)/ 执行器 anchor_ts 1789201442.562(08:24:02Z)/ rid A1789201439 / **运行树 77d9baf(= b681ca5 运行时 + 测试文件)—— 新执行器代码的第一个实盘锚**。**结论: §3 六条全过, 首锚验收 PASS; E-0909-E 有限上限截断生效(−2027 残差 2,102U → 0); 无异常处置; 一项新事件(per_name_stop 触发 LSKUSDT)。**

### §3 首锚验收
| # | 条目 | 读数 | 判 |
|---|---|---|---|
| 1 | `anchor_runs.log` 末行 / 看门狗 | `08:56:06Z anchor done rc=0`; tripped=False, triggers [], metric_errors [] | ✓ |
| 2 | 带 `request_ledger` 的 maker 行 >0; inconsistent / venue_inconsistent / filled_amount_unknown / ledger_label_mismatch 行数; 补单行子成交 | maker 283 行中 **159 带 request_ledger**(= 全部 159 条 partial_expired 即有场所事实的行; 63 min_notional 与 61 venue_reject 无账本, 合乎设计); 四类标记行 **0 / 0 / 0 / 0**; 48 条 filled 补单**全部**带 request_ledger(逐请求 confirmed_qty/notional, settled_by=identity)+ fee_source「userTrades, N child fill(s)」(RUNBOOK 写的键名 `avg_fill_px_children` 不存在, 子成交信息在 request_ledger/fee_source 里) | ✓ |
| 3 | `neutrality_price` 新键 | 有 `n_fills_measured` 20 / `coverage_measured_notional` 1.0 / `measured_over`(已测口径说明); deficient=sell, 需 taker 416.8U, **同侧实测 0.88 bps**(04Z 的 98.67 极端读数回落), 价 0.0365U 下界 | ✓ |
| 4 | `verify_reshape_anchor` 引已测口径 | 中性段:「该侧实测 taker 0.88bps(已测 20 笔 / $1220.06; 未定价 $0, 费未知 $0; 覆盖 1.0/1.0)」✓。判据 1 \|INTENT net\| 7,441U FAIL、判据 2 FAIL = 外部书锚的既有性质(E1 验收: 旧树 d040c74 同 rc=1 同判据段), 非读者变化 | ✓(既有) |
| 5 | guard_twin / anchor_report | **twin AGREE**(ledger-only; nav 行 stale)eq=118,184.00; anchor_report 照常出报 | ✓ |
| 6 | HEAD = origin/main | **77d9baf = 77d9baf** | ✓ |
| + | **E-0909-E 有限上限截断** | known_gaps `venue_cap_usdt` **0**, `venue_cap_names` **[]**(04Z: 2,102U PIEVERSEUSDT); 新告警「场所上限截断 1 名 Σ\|Δ\| 157U = gross 0.07%: PIEVERSEUSDT +2,117→+1,960(cap 2,000)」; PIEVERSE maker 行 partial_expired 1,960(无 −2027) | ✓ **首次归零** |

### ① 三守护 全绿: shadow.lock=10900 ✓ / sidecar 30943 ✓ / combo_live_daemon.pid=30944 ✓。
### ② 信号六项 全在带
status OK / coverage 1.0 / members 400 / sel 267 / **fund_updates 454**(8h 结算锚 ~453 ✓)/ forced_exit_n 0 / runtime 312.3s / fetched 450 missing 0。w3 [0.3271, 0.1092, 0.5636] ⇒ 掩码 king **0.3672** = target_combo 0.367264 ✓。combo_live_status 匹配 / ok / done / reader_ok / n 265 / gross 0.8648 / 08:21:57Z rc=0; kc·fc own ✓, rho 0.9349, phi 0.45。**反事实改写 24.9%**(序列 24.52 → 24.4 → **24.9**, 本锚 +0.5pp; 判据 = 台阶再升一档或连续 3 锚 >+0.2pp, 未触发, 12Z 再看)。生产者 paper 计分(对 04Z 书): gross +1.233 / net +0.02。
### ③ 执行漏斗(anchor_ts 归属; fills 后写胜出)
orders **477** = rows_persisted ✓ / fills 332。终态 min_notional 198 · partial_expired 159 · **venue_reject 61**(−5022 首发 54 + 重挂再拒 7; **−2027 0**)· filled 48 · no_chase 11。首发穿价率 **54/194 = 27.8%**(04Z 23.3%, 线 40%)。分臂拒单率 join **0.253** / behind **0.177**; behind 占比 **0.464**(04Z 0.554; 设计 0.50)。requote 52 / direct 28。换手三口径: anchor_report ? / 成交 Σ 11,883U ÷ gross 236,243 = 5.03%; 生产者 turnover(signal 行)未取, 12Z 补。
### ④ 记账
venue_gross 236,243 / target 235,972 ⇒ **1.0012** ✓; NAV **118,243.44** ⇒ gross/NAV 1.998 ✓; **net/gross +0.1764%**(04Z −1.12%; 三锚单调加深被本锚打断, 回到带内); net/equity +0.35%; opening_halted False; **08Z 结算 FUNDING**: funding.jsonl 255 行 settlement_ts 08:00Z, anchor_report 「funding 255 名 −8.11U」; 当日 income FUNDING_FEE 累计 −32.19(00Z −14.80 ⇒ 08Z 结算 ≈ −17.39); readback 照常; per_name_stop **新触发 LSKUSDT**(深度 −32.3% 连续 2 终锚 ≤ −30% ⇒ flatten_only, 7 天禁入; 条款 cf40ea21)⇒ stopped 2(IOST 自 09-10, LSK 本锚)/ cooldown 9; known_gaps **11 名 / 820U**(04Z 20 / 3,094U —— −2027 归零所致); reshape net_before **−11,212(−4.75%, 连续第三锚 >2%)** → 0 ✓, floor 跨门 IOST; n_names_skipped 80; 限流 peak_window_weight 725(04Z 760)。
**当日 NAV**: 117,515.79(前日收)→ 118,120.06(00Z)→ 117,452.35(04Z)→ **118,243.44(08Z)**: 本锚 +791.09, 当日累计 **+727.65 = +0.62%**; external_flow 0; 已实现 +218.44(REALIZED +258.69 / FUNDING −32.19 / COMMISSION −8.06); 未实现 2,030.20。
### ⑤ 执行质量
maker 占比 行 0.581 / **名义 0.771**(04Z 0.762, 带 ≥0.90 仍带外); 费 **2.687 bps**(maker 恰 2.0000 / taker 恰 5.0000, 332 笔全 USDT ⇒ **BNB 折扣断第 6 日**); markout 回填 224/332 = 67.5%(锚后 30 分钟, 回填 cron 仍在跑: pending 385 written 247, 12Z 复读); **尺寸梯度 s/m/l 0.517 / 0.575 / 0.655 ⇒ 非负性成立**(前三锚不成立后首次成立); chase 单名连抽 最大 1 ✓。
### ⑥ 异常处置 — **无需处置**; 告警 7 条(04Z 6), 两条新类型(一条是修复生效的正常信息, 一条是止损事件)
1. position reconcile 超范围 **8 名**(04Z 10) 2. 1 名跨 min_notional(IOST) 3. 撤名残差 −11,212U = −4.75%(第三锚) 4. 6 名被场所扣住 reduce-only(04Z 8) 5. **★新(正常)**: 场所上限截断 1 名 157U(E-0909-E 生效) 6. 35 个 maker −5022 转 taker(04Z 30) 7. **★新事件**: per_name_stop 触发 LSKUSDT。**−2027 告警自 09-08 起首次消失。** 回滚/重启/整体回滚均未触发。
### ⑦ 与 04Z 对比
| 指标 | 04Z | **08Z** | 向 |
|---|---|---|---|
| −2027 残差 | 2,102U | **0** | ★ 修复生效 |
| venue_reject(−5022 首发) | 54 (49) | 61 (54) | ↑ |
| 首发穿价率 | 23.3% | **27.8%** | ↑(线 40%) |
| join / behind 拒单率 | .252 / .147 | .253 / **.177** | → / ↑ |
| maker 占比(名义) | 0.762 | 0.771 | → 带外 |
| 费 bps | 2.714 | 2.687 | → |
| **net/gross** | −1.12% | **+0.18%** | ★ 回带 |
| neutrality 同侧 taker bps | 98.67 | **0.88** | ★ 回落 |
| known_gaps | 20 名 3,094U | **11 名 820U** | ↓ |
| 尺寸梯度 s/m/l | .46/.60/.53 | **.52/.57/.65** | ★ 非负成立 |
| reconcile 超范围名 | 10 | 8 | ↓ |
| 反事实改写 | 24.4% | **24.9%** | ↑ +0.5pp |
| NAV 当日 | −0.05% | **+0.62%** | ↑ |
### 待验证 / 推断
**已验证**: §3 六条 + 截断归零; ①–⑥ 全部读数。**待验证**: (a) 反事实改写 +0.5pp 单锚跳变, 12Z 看是否连升; (b) 撤名残差连续第三锚 >2%(−4.7~−4.8% 稳定), 基率回溯仍未做; (c) LSKUSDT 止损 30 天反事实对照待回填(条款自带); (d) 测试 `_CAP_CLAMP_DEPLOYED_TS` 应按套件自身设计设为本锚(首个受截断治理的锚, anchor_ts 1789201439), 使 −2027 类「上线后必为零」断言开始生效 —— 测试文件小改, 走 safe_commit(下一窗 09:36Z 后)。**推断**: net/gross 回带与 −2027 归零同锚发生, 但 net 由多因素决定, 不归因。
### 与研究线的交叉(只记)
BNB 折扣断第 6 日(运维裁定域); 新读者的「已测口径」数字(0.88 bps)将进入 r21/r14 同族的下一次成本对账。

## 11:4xZ(非锚)研究仓入库: 十月链驱动 + 判官底 28 + F9
- 研究仓 `15941da7`(实盘运行树 918559f 未动, 生产者未动): W3 `chain_v4_monthly.sh` + 月合同 + 负控; W4 判官底 28; lead 第七轮 F9 判官自绑合同(前身 `judge_v4.r4_7f1aa5d6.py`)。链自检本人复跑: 合并 222 ALL PASS → 加 [Q] 首跑 227/228([O] 一格语义反转, 改标)→ 228 ALL PASS(收据 `v4_chain_2026-09-09/receipts/monthly_chain_2026-09-12/tests_pipeline_gates_lead_*.log`)。`receipts/v4_scripts_sha_full.json` 重生成(94 文件)。
- W1/W2 执行器改动仍在克隆(452bcfbd 收据), 落地窗 13:00Z / 13:36Z。
- 待 12Z 锚(12:23Z 起): 快照 1789214400 + backfill_probe(08Z vs 12Z)+ 快照种子平价; 每锚深查模板。

## 2026-09-12 12:00Z 锚 · 🔴 E-0912-A 看门狗假阳性平仓(12:47:37Z)—— 事故头(深查 ①–⑦ 由 insp-12z 代理补在后)
- 12:59:19Z 我在锚 done 后 50 s 启动 W2 safe_commit(计划窗 13:00Z), **13:04Z 得知看门狗已于 12:47Z 触发, 立即 pkill safe_commit + 电池, `git checkout` 六文件 + 删两新文件, 运行树回 918559f 逐字节一致**(日志 `docs/receipts/safe_commit_w2_readers_three_bucket_20260912T125919Z.log` 尾行)。事故期间不落任何执行器改动。
- 根因链与代价见 ERROR_LEDGER E-0912-A; 12Z 快照 / 回填探针 0 / 快照种子平价精确 照做(db99c169)。13:00:20Z 执行器再跑一次 = off_schedule 只报告(orders=0, DRY_RUN N/A)。
- 恢复需用户字; 修复设计 W6 开工; 16Z 起书空仓、开仓停, 锚照跑但不下单。



<!-- 12Z 深查 ①–⑦ 由 insp-12z 代理产出(只读), lead 未改一字; 事故头见上节 -->
## 2026-09-12 12:00Z 锚 · 全深度深查(只读, 实盘零接触)

**锚**: canonical 1789214400(12:00Z; 188 个 4h 间隔名在此结算, 8h 名不结算)/ 执行器 anchor_ts 1789215841.923763(12:24:01Z)/ rid A1789215839 / **运行树 918559f = origin/main 918559f**(`.git/logs/HEAD`: 77d9baf → 918559f 于 09:51:55Z, 仅测试文件 `_CAP_CLAMP_DEPLOYED_TS=1789201439`; 运行时仍 = b681ca5, **新运行时的第二个实盘锚**)。`anchor_runs.log`: `12:00:00Z anchor start mode=LIVE` … `12:58:29Z anchor done rc=0`(其后 12:59:53Z 的 `mode=DRY_RUN` 是 safe_commit 电池, 不算)。

**★★ 结论: 看门狗于 12:47:37Z 触发(§4-5b + §4-7), 阶梯执行 halt → 255 张 IOC reduce-only 全书平仓(Σ 235,382.55 U, 全 FILLED, 0 错)→ reduce-only 已启用, 下一锚起停止开仓; 锚仍 rc=0 收尾。触发源 = 两张全退出 maker 单(MEMEUSDT / POPCATUSDT)被新运行时的请求账本「identity: 场所应答 origQty 与我方不等」标成 `filled_amount_unknown`(差额 294 张 ≈ 0.15 U / 1 张 ≈ 0.05 U, 均 < 5 U 尘埃底), §4-5b 把「大小未知的执行」计为仓位异常。该标签为 pilot_log 全史首次出现(此前每日 0 行)。本锚需要用户裁定(书已平), 我方零动作。**

### ★ 触发事实链(全部第一手, 句柄为准)
| 时刻(Z) | 事件 | 句柄 |
|---|---|---|
| 12:24:01 | 锚执行 rid A1789215839, phase_A reconcile 4 名超重估范围(MINA/MET/STAR/LSK) | `launchd_out.log` phase_A |
| 12:24:57 | MEMEUSDT sell 1,933,986 张 / POPCATUSDT sell 10,435 张 两张全退出 maker(target_w 0, placement_arm exempt, 属 external_book `held_exit` 7 名)下达; 场所应答 origQty **1,933,692 / 10,434** | orders.jsonl 两行 `request_ledger[0].inconsistent` |
| 12:24–12:40 | 两单子成交: MEME 3 笔 Σ 1,015.19 U(= 场所接受量全成)/ POPCAT 2 笔 Σ 509.07 U(全成); 均 maker, 费 0.203 / 0.102 U | fills.jsonl trade_id 376472584-6 / 278395713-4 |
| 12:45:47 | phase_B: rows_emitted 496, `book_cache_unknown_legs` 4 腿(MEME/POPCAT × maker/topup)保留缓存旧值; 两 maker 行 terminal **filled_amount_unknown**, 两 topup 行 **skipped_unknown_fill**; 告警×3(阶段 B 歧义 UNKNOWN 2 / 有数量无金额 2 / 不补单 2) | `launchd_out.log` phase_B; notify_audit 12:44:02–12:44:04 |
| 12:45:47 | per_name_stop: **LSKUSDT 已出场 → 7 天禁入冷却至 09-19 12:45Z** | notify_audit; `per_name_stop.json` cooldown LSKUSDT=1789821947.8 |
| 12:45:49 | phase_C: anchors 行 / readback 258 / daily_nav 行(NAV 117,976.93)/ venue net/gross −0.3778% | `launchd_out.log` phase_C |
| 12:46:57 | funding 拉取 income 194 行 CONTINUOUS sign OK | `live/funding_last_pull.json` |
| **12:47:37** | **看门狗评估 tripped=True**: triggers `§4-5b liquidation/position anomaly on 2 name(s) at the latest reconciled anchor (17 in this window's history)` + `§4-7 un-recovered position drift`; metric_errors []; partial [cond2, cond4]; cond5b examples = MEMEUSDT / POPCATUSDT `kind=execution_of_unknown_size, why="request ledger inconsistent"`, observed_qty 0.0, residual 不可定价; cond7 `drift_state=DRIFT` | `live/watchdog/last_eval.json` |
| 12:47:38.6 | `halt_opening_orders` submitted_ok | `live/watchdog/events.jsonl` 末行 |
| 12:47:39.2 → 12:50:00.9 | `flatten_all` **255 张 IOC reduce_only**(buy 144 / sell 111), 应答 **255/255 FILLED, executedQty==origQty 255/255, error 0**; Σ 235,382.55 U; rid `FLATTEN-20260912T124737Z` 255 行 orders(order_type protective_flatten, fee_paid None) | events.jsonl; orders.jsonl |
| 12:50:01 | `set_reduce_only` true(enforced local); **平仓后 readback 255 行 Σ\|notional\| = 0.00, 非零 0**(source `ladder_flatten@post_flatten`) | position_readback.jsonl anchor_ts 1789217401.30 |
| 12:50:01–04 | ALARM.log 第 4 条 `STOP-LOSS TRIPPED`; trip_receipt HIGH **PUSH DELIVERED** message_id 1403 sha 07da268f7808d427 | `live/watchdog/ALARM.log` / `trip_receipt.json` |
| 12:58:29 | anchor done rc=0 | `anchor_runs.log` |

**平仓成本(可读部分)**: 255 张 vs `mid_at_submit` 名义加权滑点 **+5.39 bps = 126.90 U**(中位 2.8 bps; >10 bps 55 张, <−10 bps 21 张; 最差 STARUSDT +82.5 bps on 2,219 U, 最好 UAIUSDT −120.8 bps on 2,339 U)。**taker 费未入账本**(平仓行 fee_paid None; fills.jsonl 无 FLATTEN 行; income 未再拉)— 按 5.0 bps 推断 ≈ 117.7 U。合计推断 ≈ 245 U ≈ 0.21% NAV。**平仓后 NAV 无任何账本读数**(daily_nav 行写于 12:45:47Z 平仓前), 待 16Z 锚 income/账户读回。

**标签机制(已验证部分)**: 两行 `request_ledger[0]`: state confirmed, confirmed_qty = 场所 origQty, `confirmed_qty_final=false`, `inconsistent="…identity: submit response origQty 1933692.0 differs from ours 1933986.0"`(POPCAT 10434 vs 10435); 行 note「phase B could not settle this maker request … UNKNOWN, bounded」; `filled_known_notional` 0.0 但 `avg_fill_px_children` 已算(0.000525 / 0.04879)。**校验**: fills 去重 Σ 12,831.97 − orders Σ\|filled_notional\| 11,307.71 = 1,524.26 = MEME 1,015.19 + POPCAT 509.07 逐分相等 ⇒ 「未知」的量恰是账本里全部可见的子成交。全史: `grep filled_amount_unknown` 与 `origQty .* differs` 在 08-01..09-11 各日 orders.jsonl 均 0 行, 本日 2 / 2。**推断(未验)**: 两名均为全退出且在 `clamped_after_reshape` 9 名内, 场所把平仓量截到实际持仓量 ⇒ origQty 与我方按权重×价算出的量差一个尘埃; identity 门把任何 origQty 不等都判 inconsistent。需开 b681ca5 请求账本代码与场所 positionAmt 才能定论, 本轮未开。

### ① 三守护 — 全绿(句柄为准)
| 守护 | 句柄 | PID | launchd | 运行时长 |
|---|---|---|---|---|
| shadow_loop_v3 | `~/wide_shadow/shadow.lock` = 10900 | 10900 ✓ | com.hsy.shadowloop 10900 | 7d 00:19 |
| sidecar_daemon.sh | — | 30943 ✓ | com.hsy.sidecar 30943 | 13d 08:03 |
| combo_live_daemon.sh | `fea171/combo_live_daemon.pid` = 30944 | 30944 ✓ | com.hsy.combolive 30944 | 13d 08:03 |

PID 50689 = `cc_tmp/exec_n6_sandbox` 研究沙箱, 非在役。`com.dlquant.live.anchor` 在册。运行树 HEAD 918559f = origin/main ✓(safe_commit 电池 12:59Z 起在跑, 未动)。

### ② 信号六项 — 全部在带; forced_exit 重新出现
status OK / coverage 1.0 / members 400 / sel 263 / **fund_updates 355**(4h 非 8h 结算锚稳态 ~353 ✓)/ **forced_exit_n 4, forced_exit_gross 0.0112**(≈1.1%; 08Z 0 / 04Z 0, 自 09-11 16Z 归零后首次再现, 名不在日志字段)/ turnover 0.0387 / gross_pos 0.8831 / carry 1.104 bps / cost 0.142 bps / runtime 283.4s / fetched 450 missing 0 / future_dropped 0 / data_max_ts = 锚 ✓ / exinfo_ok / logged 12:20:43Z(`shadow_log.jsonl` 末 signal 行; heartbeat 12:20:48Z OK)。
w3 = [0.3277, 0.1091, 0.5632] ⇒ **w3_masked king = 0.3277/(0.3277+0.5632) = 0.3678** = target_combo 自报 [0.367819, 0.0, 0.632181] ✓(08Z 0.3672)。
combo_live_status: anchor 1789214400 ✓ / ok / done / reader_ok true / n 261 / gross 0.85228 / age_s 0.4 / 12:21:29Z rc=0(`combo_live.log` ⑤ 读者验收 ok)。sidecar: blend n 263 gross 0.8475 ρ(f10,king) −0.085 SIDECAR_DRYRUN PASS 12:23:16Z。
target_combo: phi 0.45 / combo_v2main_norev24 / **kc·fc 均 own** ✓ / **n_f10_scored 400** ✓ / net_after_reshape 0.0 / rho_kc_fc **0.9336**(08Z 0.9349, 缓降延续)/ kc_gross 0.8857 fc_gross 0.8422。FTRIM kc 7 / fc 7(ACE/IOST/LSK/ONG/RVN/SOPH/TREE), rn8 覆盖 1.0。
**反事实改写 = 25.36%**(L1(w_live−w_king)/L1(w_king), `target_live/1789214400.json` vs `target_live_king/1789214400.json`, n 261 vs 263; 同法复算 08Z = 24.88% 与日志 24.9 ✓)。序列 24.52(00Z)→ 24.4(04Z, −0.1)→ 24.9(08Z, +0.5)→ **25.36(本锚, +0.46pp)**: **连续第二锚 >+0.2pp(不是第三), 「连续 3 锚」判据未满足**; 水平首次过 25%(历史最高此前 24.6), 是否算「升一档」按判据原文裁。
生产者 paper 计分(对 08Z 书): gross −11.529 / net −12.483 bps(给已退役 king 书计分, 不喂决策)。
regime 仪表盘(`~/regime_dash/REGIME_DASH.md` 12:50:01Z): σ_fund 8.51 bp(<p75)/ 短周期名占比 0.777(≥p95)/ 深负占比 0.018 / 书深负空头 0.003 / 席位 king 0.368 fund 0.632 / IC_fund −0.061 / IC_瞬时 +0.088 / FTRIM 7 / FTRIM 反事实 0.045 bps; **旗标无, R1–R4 无触发**; 上锚→本锚 sleeve: S|pos −214.6 U(116 名), L|pos +131.4 U, S|shallowneg −76.6 U。

### ③ 执行漏斗(按执行器 anchor_ts 归属; fills 去重=后写胜出)
orders **496**(= rows_persisted 496 ✓; 另 255 行 FLATTEN 见上)/ fills 567 行 → 去重 **336**(phase_B fill_rows_built 336 ✓, n_trades_unattributed 0)
order_type: maker 277(attempt 1 = 275, 重挂 attempt 2 = 2)/ topup_taker 219
终态: skipped_min_notional 198(maker 39 + topup 159)· partial_expired 192 · **venue_reject 44**(**−5022 首发 42 + 重挂再拒 2; −2027 = 0** ✓)· filled 40(topup)· skipped_no_chase_arm 18 · **filled_amount_unknown 2(maker, 新)** · **skipped_unknown_fill 2(topup, 新)**
首发 post-only 穿价率(执行器自报 `[A1789215839]` 行): **42/219 = 19.2%**(分母 = 场所应答的首次 maker 单 = 首拒 42 + 首落单 177; 升级线 40%; 08Z 27.8%); 我方按全部 attempt-1 maker 行算 42/275 = 15.3%
分臂拒单率(maker 行 venue_reject): **join 0.1745**(26/149)/ **behind 0.1513**(18/119)/ exempt 0(0/9); **behind 占比 0.444**(119/268; 设计 0.50; 08Z 0.464)
requote(phase_B): candidates 19 → requoted 19 → 落单 17 / 再拒 2 转 taker; direct 23; p 0.5。chase 实验: population 192 全随机化; topup 实发 40(全成)/ no_chase 18。k_cancel: cancelled 33 / already_terminal 161 / errors 0
换手四口径: anchor_report **7.9%**(08Z 8.3%)/ 成交 Σ 11,307.71 U(orders)÷ venue gross 235,398 = 4.80%(fills 去重 Σ 12,831.97 含 MEME/POPCAT 子成交 = 5.45%)/ maker attempt-1 意图 Σ 14,661.88 = 6.23% target gross / 生产者 turnover 3.87% ⇒ 口径差 7.9/3.87 = **2.04×**(04Z 2.84×)

### ④ 记账(anchors 行 = 12:45:49Z 平仓前快照)
| 项 | 值 | 判 |
|---|---|---|
| venue_gross_usdt | 235,397.72 | target 235,497.44 ⇒ **0.99958** ✓ |
| NAV | 117,976.93(nav_ts 12:45:47Z, 平仓前) | gross/NAV = **1.9953** ≈ 2.0 ✓ |
| net_over_gross | **−0.3778%** | 带内(08Z +0.18%; 04Z −1.12%) |
| neutrality_price | deficient=buy, 需 taker 889.24 U, 同侧实测 **43.91 bps**(28 笔 / 1,378.62 U, coverage 1.0/1.0, n_fills_measured 28), 价 3.90 U(下界) | 08Z 0.88 → 43.9, 只测不补 |
| net_over_equity | −0.7537% | — |
| opening_halted(anchors 行) | False(写于触发前)| **现 `watchdog/state.json` open_orders_halted=true, reduce_only=true** |
| 12Z 结算 | funding.jsonl **188 行 settlement_ts 12:00Z Σ −9.25 U**(4h 间隔名; funding_last_pull 12:46:57Z income 194 行 CONTINUOUS sign OK) | 与 income FUNDING_FEE 日累 −32.19(08Z)→ −41.33 相符 |
| income 当日(至 12:45Z) | REALIZED +261.63 / FUNDING −41.33 / COMMISSION −11.16 = **+209.14**; 未实现 1,769.92 | 平仓后未再拉 |
| readback | 258 行 post_anchor(Σ 235,397.72, 非零 255)+ **255 行 post_flatten(Σ 0.00, 非零 0)** | 平仓后书为空 ✓ |
| per_name_stop | stopped 1 = IOSTUSDT(09-10 起)/ **LSKUSDT 出场 → cooldown 至 09-19 12:45Z** / cooldown 10(XANUSDT →09-16 20:39Z; DASHUSDT →09-12 17:24Z; COLLECT/CYS/FLOCK/HEMI/MAGMA/RIVER/TRIA →09-13 13:19Z) | 08Z stopped 2 / cooldown 9 |
| `anchor_runs.log` 末 LIVE 行 | `2026-09-12T12:58:29Z anchor done rc=0` | ✓ |
| **watchdog** | **tripped=True 12:47:37Z**, triggers §4-5b(2 名)+ §4-7, metric_errors [] | ★★ 见事实链 |
| guard_twin | **AGREE**(ledger-only; nav 行 stale)eq=117,874.46(引用 nav 118,243.44 = 08Z 行) | ✓(对触发盲, 见 ⑥) |
| n_names_skipped | 59(08Z 80) | ↓ |
| known_gaps | **20 名 + 2 unsized(MEME/POPCAT topup)**, gross 2,555.90 / net −879.76; **venue_cap_usdt 0 / venue_cap_names []** ✓ | E-0909-E 第二锚归零; 截断 PIEVERSE +2,161→+1,960(201 U = 0.09%) |
| reshape | net_before **−13,684.25(−5.80% target gross; 连续第四锚 >2%: −4.70/−4.75/−5.80)** → −3e-12 ✓; gross 221,607 → 235,777; popped 10(BTC/COLLECT/CYS/DASH/FLOCK/HEMI/MAGMA/RIVER/TRIA/XAN); floor 跨门 IOST/LSK/ZK; clamped_after_reshape 9 名 net_shift −79.06 U | ★ 加深 |
| 限流 | **peak_window_weight 915**(08Z 725; 含平仓突发); rate_budget peak/min weight **981**(自限 1000)/ orders 238 / requests 244; waits 0 | ★ 贴近自限 |

**当日 NAV**: 前日收 117,515.79 → 00Z 118,120.06 → 04Z 117,452.35 → 08Z 118,243.44 → **12Z(平仓前 12:45:47Z)117,976.93**: 本锚 −266.51, 当日累计 **+461.14 = +0.392%**; external_flow 0。**平仓后权益 = 117,976.93 − 未实现回吐/兑现差 − 平仓滑点 126.90 − taker 费(≈117.7 推断)—— 无读数, 不填数。**

### ⑤ 执行质量(A1789215839 本身, 不含平仓)
- **maker 占比 行 0.738 / 名义 0.862**(fills 去重 venue_maker_flag; 剔除 MEME/POPCAT 子成交 = 9,541/11,308 = 0.844; anchor_report taker 16%)— 带 ≥0.90 仍带外, 但为当日最好(08Z 0.771)
- **费 2.4130 bps**(fills 基, Σ 3.0964 / 12,831.97; anchor_report 2.74 bps = 同费 / orders 基 11,307.7)— maker 恰 **2.0000** / taker 恰 **5.0000**, 336 笔 commission_asset **全 USDT**, `fee_asset_baseline` assets [] ⇒ **BNB 折扣断第 6 日**
- **markout 回填 228/336 = 67.9%**(12:58Z 读; cron CAPPED(deadline) pending 171; 08Z 复读已达 273/332 = 82.2%)
- **尺寸梯度三桶**(maker attempt-1, intended 三分位 15.6 / 49.4 U, Σ\|filled\|/Σintended): small **0.609** / mid **0.661** / large **0.651** ⇒ 非负性**微弱不成立**(m > l 0.01), 三桶齐升(08Z .52/.57/.65)
- **chase 单名连抽**: 最大 1 ✓
- **平仓腿**(独立列): 255 张 IOC 全 taker, 滑点 +5.39 bps / 126.90 U, 费未记账

### ⑥ 异常处置 — **★★ 需用户裁定(书已平, 开仓已停); 我方零动作**。本锚告警 11 条(08Z 7): 推送 7 / 仅记 4 / 未送达 0; **四条新类型**
1. position reconcile **4 名**超重估范围(MINA/MET/STAR/LSK; 08Z 8)— PUSH
2. 重整后 **3 名**跨 min_notional(IOST/LSK/ZK), 只报不迭代 — 记
3. 撤名残差 **−13,684.25 U = −5.80%**(>2%, 第四锚), 10 名撤下 — 记
4. **10** 个持仓名被场所扣住 reduce-only(08Z 6): reducing ZRO / add_blocked IOST / flatten_only ACU·OPEN·MEME·LSK — 记
5. 场所上限截断 1 名 201 U(PIEVERSE +2,161→+1,960, cap 2,000; E-0909-E 第二锚) — PUSH(正常)
6. **★新**: 阶段 B 歧义 maker 结算: 查到 0 / 确认未下达 0 / **仍 UNKNOWN 2**(MEMEUSDT, POPCATUSDT; 文案「满页或查询失败」, 但行内 inconsistent 字段写的是 identity/origQty 不等)— PUSH
7. **★新**: 2 名有成交数量无可读金额 → UNKNOWN 不补单(「读成 0.0 是产生 2.00x 加倍的输入」)— PUSH
8. **★新**: 2 名 unreadable fills → skipped_unknown_fill, failure classes=UNRECORDED — PUSH
9. 25 个 maker −5022 转 taker(08Z 35)— 记
10. per_name_stop: **LSKUSDT 已出场 → 7 天冷却至 09-19 12:45Z** — PUSH
11. **★新(事件)**: **止损触发 §4-5b + §4-7 — 书已平仓, reduce-only 已启用** — PUSH DELIVERED(id 1403)

其他常驻读数: factor_health VERDICT UNKNOWN(shadow monitor 报告不可读; episode 68f039b2 已告警不重复, 既有)/ funding_span STALE(既有)/ metrics_freeze FROZEN_MATCH / nosleep ok / artifacts 11/11 / open_items 30。
**E-0909-E −2027 残差 = 0** ✓(venue_reject 44 张全为 −5022)。**request_ledger**: maker 277 行中 **194 带 request_ledger**(= 192 partial_expired + 2 filled_amount_unknown; 39 min_notional 与 44 venue_reject 无账本, 合乎设计); topup filled 40 行全带 request_ledger; **四类标记: inconsistent 2 / venue_inconsistent 0 / filled_amount_unknown 2 / ledger_label_mismatch 0 ⇒ 预期 0/0/0/0 未达成**, 且这 2 正是触发源。`neutrality_price` 已测口径键全在(n_fills_measured 28, coverage_measured_notional 1.0)。
**回滚 / 重启 / 整体回滚判据**: 生产者三守护绿、信号全在带、combo 读者 ok ⇒ 生产者侧无触发; 执行器 rc=0、传输 0 错、账本 496 行齐 ⇒ 无崩溃形态; **触发的是执行器自己的 §4-5b 状态门对两笔尘埃级 origQty 不等的分类**。恢复动词 = `ops/resume_from_trip.sh`(收据原文: 「条件仍成立时它会拒绝」; cond5b 以「最近已对账锚」为状态, 16Z 前不会自清)。这属书行为 = 用户字域, 本条只记事实。

### ⑦ 与上一锚(08Z)对比
| 指标 | 08Z | **12Z** | 向 |
|---|---|---|---|
| −2027 残差 | 0 | **0** | ✓ 持续 |
| venue_reject(−5022 首发) | 61 (54) | **44 (42)** | ↓ 改善 |
| 首发穿价率 | 27.8% | **19.2%**(42/219) | ↓ 改善(线 40%) |
| join / behind 拒单率 | .253 / .177 | **.175 / .151** | ↓ / ↓ |
| behind 占比 | 0.464 | 0.444 | → 离设计点 |
| maker 占比(名义) | 0.771 | **0.862**(剔未知 0.844) | ↑ 仍带外 |
| 费 bps | 2.687 | **2.413**(fills 基; 报告口径 2.74) | ↓ |
| taker 占比(anchor_report) | 23% | **16%** | ↓ |
| **net/gross** | +0.18% | **−0.38%** | 带内 |
| neutrality 同侧 taker bps | 0.88 | **43.91** | ↑(04Z 98.67) |
| known_gaps | 11 名 820 U | **20 名 + 2 unsized, 2,556 U** | ↑ |
| 撤名残差 | −4.75% | **−5.80%** | ↑ 第四锚 |
| 尺寸梯度 s/m/l | .52/.57/.65 | **.61/.66/.65** | 齐升; 非负性微弱失 |
| reconcile 超范围名 | 8 | **4** | ↓ |
| 反事实改写 | 24.9% | **25.36%** | ↑ +0.46pp(连续第二) |
| forced_exit_n / gross | 0 / 0 | **4 / 0.0112** | ★ 再现 |
| 生产者 turnover | 3.12% | **3.87%** | ↑ |
| 执行器换手(anchor_report) | 8.3% | 7.9% | → |
| markout 回填 | 67.5%→82.2%(复读) | 67.9%(12:58Z) | → |
| peak_window_weight | 725 | **915** | ↑(含平仓) |
| 告警数 / 新类型 | 7 / 2 | **11 / 4** | ↑ |
| per_name_stop | stopped 2 / cd 9 | stopped 1 / **cd 10(LSK 出场)** | — |
| NAV 当日(平仓前) | +0.62% | **+0.39%** | ↓ |
| **watchdog** | tripped=False | **tripped=True 12:47:37Z, 全书已平** | ★★ |
| guard_twin | AGREE eq 118,184.00 | AGREE eq 117,874.46 | ✓ |
| 运行树 HEAD | 77d9baf | **918559f**(= origin/main) | 仅测试文件 |

### 待验证 / 推断分栏
**已验证(本机第一手)**: ①②③④⑤ 全部读数; 触发事实链每一行的句柄; 平仓 255/255 FILLED 与 post_flatten readback Σ 0; 两行 request_ledger 的 origQty 不等原文; 标签全史 0 → 2; 11 条告警原文; HEAD reflog 时刻; 反事实改写自算并对 08Z 复现。
**待验证**: (a) **反事实改写 25.36%: 连续第二锚 >+0.2pp(不是第三), 判据未满足; 首次过 25% 是否算「升一档」按原文裁**; (b) **撤名残差 −5.80% 连续第四锚 >2% 且为四锚最深**, 基率回溯仍未做; (c) **LSKUSDT: 已出场并进 7 天冷却(至 09-19 12:45Z), stopped 表只剩 IOSTUSDT**; 30 天反事实对照待回填; (d) **§4-5b 把「identity origQty 不等」计为 execution_of_unknown_size 的语义, 与 5 U 尘埃底为何不适用(`mark_source: not applicable`)—— 需开 b681ca5 请求账本 / 看门狗代码逐位核, 本轮未开**; (e) **平仓后 NAV / 权益 / 手续费无账本读数**, 16Z 锚 income 拉取或人工读账后补; (f) §4-7 「un-recovered position drift」在 last_eval 只暴露 drift_state=DRIFT, 具体名/量未见; (g) W2: `ops/first_anchor_review.py` 运行树上为落地中的新版, **未运行**, 全部读原始文件。
**推断(标明)**: 两名全退出单被场所截到实际持仓量 ⇒ origQty 少一个尘埃(MEME 294 张 ≈ 0.15 U, POPCAT 1 张 ≈ 0.05 U); 子成交合计恰等于场所接受量, 即两仓**实际已平干净**, 「未知」是标签而非执行事实; 08Z 同运行时无此形态, 因 08Z 无被截量的全退出单(未逐名核)。**不据此下结论, 交裁定。**

### 与研究线的交叉(只记, 不动)
- 新运行时 b681ca5 的请求账本 identity 门在第二个实盘锚把两笔尘埃级 origQty 差升级为「大小未知的执行」, 经 §4-5b 触发全书平仓 —— 与 E-0909-G(账本缺口触发)同族: **看门狗读的是账本标签而非场所仓位**(`ledger-not-book` 家族); 平仓成本 ≈ 245 U(滑点实测 126.90 + 费推断 117.7)。
- anchor_report 常驻器 12:55Z 输出 `status=warn ["taker 占比 16%"]`, **对 12:47Z 的触发/平仓不着一字**(twin 也 AGREE)—— 该仪器对看门狗状态盲, 与 08Z 验收 §3#5 「anchor_report 照常出报」同源。
- BNB 折扣断第 6 日(运维裁定域); 12Z 4h 名结算 188 行 −9.25 U 说明「非结算锚」只对 8h 名成立, 深查模板的 funding 预期需按间隔分列。

## 2026-09-12 16:00Z 锚 · 停开仓状态下的锚(只读, 实盘零接触; 每锚深查增量)
- **执行器**: phase_A 16:24:02Z, rid A1789230240, phase_B 16:39:03Z(k_cancel 0), phase_C 16:39:07Z(readback 245 行, nav 行, per_name_stop 无触发, cooldown 11), `anchor done rc=0` 16:41:50Z。**订单行 245 = 243 `blocked_by_halt` + 2 `skipped_min_notional`, submit_ts 全空, fills 0** ⇒ 开仓停按设计生效, 零下单; 目标 gross 235,335U 全部被挡。看门狗 16:39:53Z 评估 tripped=False(最新对账锚无异常), 但 state 仍 reduce_only/halted(设计: 需人工恢复)。告警 raised 5 / delivered 2(factor_health、funding_span 已抑制重复)。
- **首次平仓后 NAV 账本读数**: 16Z daily_nav **117,787.02**(12Z 平仓前 117,976.93 ⇒ **−189.91U = −0.16%**, 含平仓滑点/费与空仓期间的标记差; 当日 realised +1,781.69 = 平仓把未实现 P&L 变现); 读回 Σ|名义| **0.0**(245 行)。
- **三守护** 10900 / 30943 / 30944 全在; 生产者 combo_live_status ok/done/reader_ok n 260 gross 0.845(16:22:31Z), last_anchor 1789228800。
- **平价前向**: 16Z 生产者快照 1789228800(16:42:17Z, 4 文件); 回填探针 12Z→16Z **0/0/0**(11,472 行 × 829 名)⇒ 快照对 **2/3**; 快照种子平价(12Z 种子 → 16Z)运行中。
- **处置**: 无。恢复交易 = W6 复审 → 用户字部署 → 用户手动 `resume_from_trip.sh`。

## 2026-09-12 20:00Z 锚 · 全深度深查(停开仓第二锚; 只读, 实盘零接触)
**锚**: canonical 1789243200 / 执行器 anchor_ts 1789244641.115767(20:24Z)/ rid **A1789244640** / 运行树 918559f(代码与 918559f 逐字节相同)。**结论: 无处置; 开仓停按设计生效(零下单); 平价前向序列 3/3 完成。**
### ① 三守护 全绿(句柄为准): shadow.lock **10900** ✓ / sidecar **30943** ✓ / combo_live_daemon.pid **30944** ✓。
### ② 信号六项 全在带
status **OK** / coverage **1.0** / members **400** / sel **259** / **fund_updates 355**(4h 整点稳态 ~353 ✓)/ forced_exit_n **4**(gross 0.0065)/ runtime **243.5 s** / fetched 450 missing 0 / future_dropped 0 / exinfo_ok true / data_max_ts == 锚。w3 **[0.3254, 0.1130, 0.5616]** ⇒ 掩码算术 0.3254/(0.3254+0.5616) = **0.366855** vs target_combo `w3_masked[0]` **0.366832** ✓(1e-5 内)。combo_live_status: anchor 匹配 / ok / done / reader_ok / n **257** / gross **0.8390** / 20:20:50Z。kc_state_source **own** / fc_state_source **own** ✓; n_f10_scored **400** ✓; rho_kc_fc **0.9271**; phi **0.45**; book_form combo_v2main_norev24; net_after_reshape −0.0; kc_gross 0.8748 / fc_gross 0.8264。生产者 turnover **3.119%**(稳态 2–5.5% ✓), carry 1.176 bps, cost 0.117 bps。**反事实改写 26.58%**(序列 24.52 → 24.4 → 24.9 → 25.36 → **26.58**; 连续第三锚增量 >+0.2pp ⇒ **按判据达到升级条件**, 但书处于空仓/停开仓态, 该量只描述生产者目标书与 king 形态的差, 与实际持仓无关 ⇒ 记为**待验证**, 恢复交易后首两锚复判)。
### ③ 执行漏斗(按 anchor_ts 归属)
orders **245** = **243 `blocked_by_halt` + 2 `skipped_min_notional`**; **submit_ts 行 0, fills 0** ⇒ 零下单; Σ|intended| **235,286.5U**(= 目标 gross, 全被挡)。maker 占比/换手/费 bps/分臂/behind 占比: **本锚不适用**(无成交)。
### ④ 记账
anchors 行 6(00/04/08/12/16/20Z), phase_C anchors_row ✓ / readback **245 行 Σ|名义| 0.00** ✓ / per_name_stop 无触发(cooldown 11); `opening_halted` **true**; target_gross 235,286U, venue_gross —(空仓), net/gross —; **NAV 117,779.56**(16Z 117,787.02, **−7.47U**; 空仓期唯一变动项, 待验证来源); 当日 realised **+1,781.69**(12Z 平仓把未实现变现后不变); **20Z 非 8h 结算锚 ⇒ funding 行 0** ✓; `anchor done rc=0` **20:41:09Z**; 看门狗 20:39:49Z 评估 **tripped=False**(最新对账锚无异常)但 state 仍 reduce_only/halted(设计: 需人工恢复); 告警 raised 4 / delivered 2。
### ⑤ 执行质量 — 无成交, 三项(尺寸梯度/markout/chase)本锚不适用。
### ⑥ 异常处置 — **无**。回滚/重启/整体回滚均未触发; 生产者未触。
### ⑦ 与 16Z 对比(增量)
| 指标 | 16Z | **20Z** | 向 |
|---|---|---|---|
| 订单行 | 245(243 挡 + 2 小额) | 245(同) | → |
| fills | 0 | 0 | → |
| NAV | 117,787.02 | **117,779.56** | −7.47U |
| sel / n | 260 | 259 / 257 | → |
| fund_updates | (16Z 结算锚) | 355(4h 稳态) | ✓ |
| 反事实改写 | 25.36% | **26.58%** | ↑ +1.22pp(连续第三锚 >+0.2pp) |
| 看门狗评估 | tripped=False | tripped=False | → |
### 待验证 / 推断
**已验证**: ①–④ 全部读数; 平价 3/3。**待验证**: (a) 空仓期 NAV −7.47U 的来源(无持仓、无成交、非结算锚; 可能为标记/权益读数口径, 需 API 才能确证); (b) 反事实改写达到升级判据但书空仓 —— 恢复后首两锚复判; (c) 撤名残差/尺寸梯度等成交类指标自 12Z 起无观测。**推断**: 零下单与 `opening_halted` 一致, 与看门狗 state 一致。
### 平价前向序列完成(研究线, 不影响实盘)
回填探针三对 08Z→12Z / 12Z→16Z / 16Z→20Z **全部 0/0/0**; 快照种子平价 12Z / 16Z / 20Z **全部逐位精确**(king L∞ 0.0, combo target_live L∞ 0.0)⇒ AMENDMENT 3 裁定: 支持「起点状态差」候选, 未排除历史缓存/辅助文件/左边界三因子(见 PREREG)。

