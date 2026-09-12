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

