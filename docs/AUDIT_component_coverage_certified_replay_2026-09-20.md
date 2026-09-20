> **创建:** 2026-09-20 | **Session:** session_01KW6frfphbFmFzx7wUtGhLb(独立组件覆盖审计, 只读) | **状态:** 出数 —— 63 行覆盖矩阵(IMPLEMENTED 26 / APPROXIMATED 22 / MISSING 7 / NOT-APPLICABLE-IN-HISTORY 6 / NOT-EXERCISED 2), 机读件 `multi_asset/exports/research/coverage_audit_2026-09-20/receipts/COVERAGE_MATRIX.json`(sha e19b7f01) | **作废条件:** 执行器树离开 409ea16, 或生产者 `shadow_loop_v3.py` 离开 e9c98374 / `combo_stage.py` 离开 3520d363; 或 `TARGETS_A0_main.npz` b9f0dc9f / 模拟器 v3.1 29679672 / 合池标定 fda34243 / 冻结配置 `RUN_CONFIG_main_A0_2026-09-19.json` 7b6dca2c 任一被撤回或改判; 或本文任一行被具名收据推翻

# 审计: 认证历史回放到底实现了在役系统的哪些部件(A0 臂, 只读)

**被审对象(三段链):**
- **目标侧(书该持什么)** = 对象 B, `multi_asset/exports/research/object_b_2026-09-19/`, `targets/TARGETS_A0_main.npz` b9f0dc9f(10,039 锚, 2022-01-31 → 2026-08-31)与 `TARGETS_A0_ext.npz` 085d8858(10,152 锚, 到 2026-09-18T20Z)。
- **执行侧(实际成交什么)** = 模拟器 v3.1, `multi_asset/exports/research/replay_exec_2026-09-19/exec_sim.py` 29679672 + 合池标定 `CALIBRATION_v3_POOLED_20260826_20260910.json` fda34243。
- **表** = `multi_asset/exports/research/baseline_tables_2026-09-19/`, 冻结配置 `RUN_CONFIG_main_A0_2026-09-19.json` 7b6dca2c; 主运行 `OBJB_A0|scaled|rule|raw|UAFE`, 9,139 锚(2022-06-30 → 2026-08-31)× 32 条成交路径, NAV0 = 100,000 USDT, gross_mult 2.0。

**地面真值:** 执行器 `~/dl_quant_live` @ **409ea162746d0ba459db33c3f5c07865c24a7514**; 生产者 `~/wide_shadow`(`shadow_loop_v3.py` **e9c98374**, `fea171/combo_stage.py` **3520d363**)。两处全程只读: 未写入、未运行、未调用交易所、未碰 launchd。

**盲态(CFG-04 / CFG-06):** 追单 / 重挂 / 挂单深度三个实验保持盲态。本文只报**臂名、分臂机制与分配计数/平衡**, 不计算也不引用任何分臂结果量。

**方法纪律:** 每行必须带(一)在役树 file:line、(二)回放链 file:line、(三)从运行收据或逐锚记录里**读出来的数**。装置副本与在役树按 sha256 逐件核对。未能核实的写 UNVERIFIED 并说明需要什么。

---

## §0 一页结论(白话)

1. **代码同一性这一层是干净的。** 执行器侧 8 个承重模块(`binance_executor` / `external_book` / `per_name_stop` / `chase_policy` / `requote_experiment` / `anchor_loop` / `legs` / `book.json`)在 pod2 镜像里与在役树 **8/8 sha256 逐位相同**; 模拟器按 `__file__` 断言它们确实从镜像导入(`exec_sim.py:131-132`)。生产者侧 `shadow_loop_v3_replay.py` 与在役 `e9c98374` 的差异**恰好 2 处**(TAIL_SCORE、取 K 线), `combo_stage_replay_3520d363.py` 与在役 `3520d363` 的差异**恰好 3 处**(家目录、缓存截断、页报抑制) —— 都是逐字 diff 核过的, 不是自述。
2. **最大的缺口不在目标侧也不在成交侧, 在风控侧。** 回放只实现了看门狗的 **§4-2 日止损(−4%)** 一条; **§4-1 / §4-3 / §4-4 / §4-4b / §4-5 / §4-6 / §4-7 全部没有实现**。其中 **§4-4 =「自起始本金累计 −25% ⇒ 撤单 + 全书平仓 + 账户 reduce-only, 且只能人工恢复」**(`live/watchdog.py:109-131`、`:1940`、`:2012-2014`、`ops/resume_from_trip.sh:232-249`)。**实测: 32 条路径全部在完整配方窗内跌破 −25%**(最早 2024-03-11, 中位 2024-03-18, 最晚 2024-06-13), 且**平均 77.0% 的完整配方锚落在首次跌破之后**。也就是说 **+134.6% / 年化 +30.8% 这条路径, 在役规则下需要一次人工放行才走得下去**; 表里没有这个门。
3. **COMBO_LIVE 飞前断言的地板被改写过, 并且改写是**实质的**。** 按在役字面规则(F10 覆盖 ≥380/400、名数 ≥150), 10,039 个锚里只有 **2,356 个(23.5%)**会交易 combo 书, 其余交易 king 书; 主表用的是按 `n_members/400` 缩放后的地板, 于是 **6,702 个(66.8%)**交易 combo。两个读数都跑了(`OBJB_A0|scaled|*` 与 `OBJB_A0|lit|*`), 所以这个选择的代价是**可测的**, 但本文没有测它。
4. **执行层的全部经验依据是 16 天。** 合池标定取自 2026-08-26 → 09-10 的实盘执行记录, 被套到 4.2 年历史上; 而这套参数自己的验收门在样本内 **CAL = FAIL(11/12, 败在价格与成交项)**, 只有被看过的那一周 HIST_DIAG 通过(12/12), 文档自己声明那**不是独立验证**。真前瞻验证已预注册, 尚无数据。
5. **在役里根本不存在的东西, 回放也正确地没有**: 没有任何止盈规则(执行器树与生产者树两轮 grep 各 0 命中); 外部书模式下执行器侧的**中性带与换手 EMA 是死的**(`anchor_loop.py:1872-1874`、`:2064-2071`), 逐名权重上限与风险预算也是死的 —— 回放同样不施加, 这是对的。换手整形真正活着的那一份在生产者侧(EMA α=0.1 + 带 0.00025), 回放逐位复现。
6. **被刻意丢掉的**: 实盘的保护性平仓(off-schedule 跑、看门狗梯队、人工平仓)与追单/挂单实验的**分臂效果**。对「这套配方在当前规则下历史上会怎样」是**合理的**; 对「这个账户历史上会赚多少」是**不合理的** —— 实盘已因 launchd 补跑导致三次全书平仓, 任何配方回放都装不下这件事。

---

## §1 覆盖矩阵(63 行)

判词图例: **IMPL** = 跑的是在役代码或逐位等价实现且被实际触发; **APPROX** = 在, 但有具名差异; **MISS** = 在役有、回放没有; **N/A-HIST** = 回放里不可能存在或在役本身是死的, 缺席正确; **NOT-EXER** = 实现了但本次运行没触发。

完整字段(在役 file:line / 回放 file:line / 触发计数 / 方向与量级)在机读件 `receipts/COVERAGE_MATRIX.json`; 下表是同一批行的摘要。

### §1.1 生产者侧(目标)

| # | 部件 | 在役 | 回放 | 触发计数 | 判词 |
|---|---|---|---|---|---|
| P-01 | 生产者装置谱系 | `shadow_loop_v3.py` e9c98374 | `shadow_loop_v3_replay.py` 4d3bc157, 与在役 diff **恰好 2 处**; pin 断言 `b_driver.py:153` | — | **IMPL** |
| P-02 | combo 装置谱系 | `fea171/combo_stage.py` 3520d363, 399 行 | `combo_stage_replay_3520d363.py` 92c49fa8, 387 行; diff **恰好 3 处**(L10 家目录 / L23-24 缓存截断 / L299 页报抑制) | — | **IMPL** |
| P-03 | 超参 bundle | `shadow_bundle/config.json` **3a8422f3**(NTOP 400 / cov_min .95 / qv4h_min 250k / cap_mult 2.5 / α .1 / band 2.5e-4 / msharpe_look 900 / sel_min 80) | 同一文件同一 sha(`RUN_CONFIG_A0_main.json` inputs_sha256.bundle_config) | — | **IMPL** |
| P-04 | 席位权重 w3(msharpe 900) | `:456-462` | 逐位同 | 10,039 锚; w3[king] 均 0.4266(0.0000–1.0000) | **IMPL** |
| P-05 | 席位暖机 | 在役**从不冷启**: bundle `leg_returns.npz` 6061af10 接力(`:223-226`) | `b_driver.py:280` LR 置空, 自己挣 900 个腿收益 | lr_len 第 900 条到位; 1,191 锚跑在 1/3 权重上 | **APPROX**(对头条**零影响**: 完整配方窗按 B_CORE_start 起算) |
| P-06 | king 腿 | 单一在役 booster `slow2026.txt` **8d79186b**(= `book.json` booster_sha_pin) | `b_lib.FoldBooster('folds')` 作同一个 `booster` 实参, 逐锚取 label_end < A−30d 的最新年折(`b_lib.py:110`); 2026 折**就是**在役文件 | 折覆盖: None 2,191 / 2023 2,190 / 2024 2,196 / 2025 2,190 / 2026 1,272 | **APPROX**(折外, 方向 = 比在役 booster 更不利) |
| P-07 | F10/DL 腿 | 单一在役导出 `f10_live_s42_np.npz` **351ae26b**(= f10_sha_pin) | P2 用生产 171 管线逐名打分 + 年折; P3 以 rank/128 + 恒等模型注入, 使 `zf` 与生产逐位同(`b_lib.py:133-147`, 断言 `:141`) | 折覆盖 None 2,010 / 2023 2,190 / 2024 2,196 / 2025 2,190 / 2026 1,453; n_f10_scored 均 235.8 | **APPROX**(同上) |
| P-08 | 去 rev24 腿 | `combo_stage.py:229-232` | 逐位同 | 10,038 锚记录 `w3_masked` | **IMPL** |
| P-09 | φ=0.45 混合 + 执行器口径 reshape | `:271-272` / `:200-208` | 逐位同 | kind==2 于 6,702 锚 | **IMPL** |
| P-10 | FTRIM(负费率空头 z 层排除) | `:236-254`, rn8 ≤ −0.0010 且 z<0 | 逐位同; iv 由在役 `run_anchor:341-343` 自己算, 非默认 8h | **52,496** kc 名-锚 / **45,483** fc 名-锚, 覆盖 **8,075 / 10,038** 锚; rn8_coverage 恒 1.0000 | **IMPL**(口径注: 在役覆盖 <1) |
| P-11 | 流动性门 `sel`(qv4h ≥ 250k)+ sel_min | `:473-477` | 逐位同 | sel 均 239.8 vs members 均 263.6; **239,280** 名-锚被门掉, 6,815 锚 sel<members; sel_min 从未咬合(min 133 > 80) | **IMPL** |
| P-12 | 成员筛(covr/vol/NTOP) | `:365-380` | 逐位同 | members 均 263.6(133–400); members<50 跳锚 0 次 | **IMPL** |
| P-13 | COMBO_LIVE 飞前断言 + 回落 king | `:330-336` 断言 + `:313-318` `_bail` ⇒ 本锚交易 king(fail-open) | 装置逐位同; `b_driver.combo_outcome:229-270` 同时记录**字面**结果与把 380/150 地板按 `n_members/400` **缩放**后的结果(`:258-262`) | 飞前失败 **7,682 / 10,039**(7,482 因 F10 覆盖 <380, 200 因 gross 出界); 字面: king 7,683 / combo 2,356; 缩放: king 3,337 / combo **6,702** | **APPROX**(实质: 字面规则下只有 23.5% 的锚交易 combo) |
| P-14 | 硬截止 N+22:40 | `:322-324`, 写者会**输掉**这场与读取窗的赛跑 | 回放写到 `target_live_combo/` ⇒ `_rehearsal=True` ⇒ 该分支被跳过 | 0 锚因截止 bail(7,682 个失败全在 preflight) | **N/A-HIST** |
| P-15 | 用实盘读者自验收 | `:369-381` 导入 `external_book` 跑 verify_file+parse_target, 不过即回滚 king | 同路径; 读者是 sha 核过的暂存副本(`b_driver.py:57,67-71,293-294`) | STAGE_MANIFEST 每次运行前逐件核 sha | **IMPL** |
| P-16 | 宇宙 / PIT 成员 | bundle 里冻结的 450 名 `symbols_live` | 逐锚取 P2 `universe.npz` 6322b573 的 PIT 行(`b_driver.py:306-307`) | n_live 均 275.0(136–449) | **APPROX**(D4: PIT 是历史上唯一因果的宇宙) |
| P-17 | 秩基名单(exchangeInfo 代理) | `:311-318` 场所 TRADING∪live, ≥300 才接受 | `b_driver.py:126-130,308` 代理 = trading24 ∩ COIN ∪ live | n_base 均 321.2(138–614); exinfo_ok True 4,343 / False 5,696; fund_base_n 均 319.5 | **APPROX**(历史 exchangeInfo 不可得, D3) |
| P-18 | 出宇宙即平 / 非成员即平 | `:174-175`, `:496-511` | 逐位同 | 强制出场 **2,138** 锚 / **3,675** 名-锚 / Σ|w| 8.76 | **IMPL** |
| P-19 | 逐名权重上限 | `:487-490` capw = 2.5/n_sel | 逐位同 | n_sel=240 时上限 = gross 的 1.04% | **IMPL** |
| P-20 | gross 归一 | `:484-490` 两次 L1 归一 | 逐位同 | signal.gross_pos 均 0.6962 | **IMPL** |
| P-21 | 生产者换手 EMA(α=0.1)+ 中性带(2.5e-4) | `:492-494` | 逐位同; kc/fc 各自锚寻址状态 | 状态源 ('own','own') 于 **10,037 / 10,039** 锚; 逐锚换手均 0.05135 | **IMPL** |
| P-22 | fund 腿秩基(M1) | `:100-111`, `:413-417` | 逐位同 | fund_base_n 均 319.5 > members 均 263.6 ⇒ 基确实更宽 | **IMPL** |
| P-23 | 覆盖门 / anchor_skip | `:301-310` coverage<0.80 ⇒ 跳锚 | 门在跑, 但输入是合成的(`REPLAY_KLINES` 报 missing=0) | status 全 OK; coverage min 0.9574; **跳锚 0 次** | **NOT-EXER** |
| P-24 | 增量 K 线 + ret5 ±0.30 裁剪 | `:276-300`, CHN_CLIPS `:150` | 替换 #1: 换成 holefix2 面板(1d7f459d), **裁剪在两边都在** | diff hunk 2; RUN_CONFIG data_version | **APPROX**(丢的是填充次序与 f16 抖动, 非裁剪) |
| P-25 | TAIL_SCORE | `:151` True, `:445-453` 只加字段不改书 | 替换 #2: False | diff hunk 1; 喂 w3 的腿收益在 `:433-439`, 与此旗标无关 | **N/A-HIST**(零影响) |
| P-26 | 实时等价缓存规则 | 无在役对应物 | 预注册规则 S4 **门 FAIL ⇒ 未施加**(R0, `b_driver.py:105-107`) | `LIVE_EQUIV.json`: LE_A′ FAIL, 12,952 格「此处 NaN 而生产有限」(全来自 SCRTUSDT/STORJUSDT), 反向 0 格, 负控 41,837 格红 | **MISS**(按死名敞口界: 逐年写入份额 0.0069%–0.045%) |

### §1.2 执行器侧(成交)

| # | 部件 | 在役 | 回放 | 触发计数 | 判词 |
|---|---|---|---|---|---|
| E-01 | 执行器装置谱系 | 8 个承重文件 sha256 | pod2 镜像 **8/8 逐位相同**; `exec_sim.py:131-132` 按 `__file__` 断言 | 复用函数: `apply_withhold_and_reshape` / `RebalanceExecutor.plan` / `round_qty` / `parse_target`·`target_vector`·`held_not_in_target`·`below_min_notional` / `to_notional` / `per_name_stop.evaluate`·`active_sets` / `chase_policy.plan_experiment` / `requote_experiment.assign` | **IMPL** |
| E-02 | `verify_file` / `parse_target` + 三个 sha 钉 | `external_book.py:275-294`(4 项)`:305-413`(21 项, 含 booster/f10 钉 `:393-400`) | 在役函数逐锚调用(`exec_sim.py:511`), 但**三个钉强制置 None**(`:136`) | 9,139 锚里 hold_why_invalid = 0、hold_why_missing = 0 | **APPROX**(钉失效 ⇒ 不演练「模型 sha 不匹配 ⇒ HOLD」这条在役失败模式) |
| E-03 | 决策时刻 N+24:00 与无前视 | `book.json` anchor_offset_min 24, poll_grace 5 | `exec_sim.py:508-511` t_dec = A+1440s, 只读 ≤t_dec 的最后一根完整 5m bar(N+20); 电池用**未来扰动**测试钉住 | RUN_CONFIG decision 字段; 电池 `BATTERY_tests_exec_sim_v31` | **IMPL**(轮询重试未建模) |
| E-04 | gross = NAV × 2.0 | `anchor_loop.py:1553`, gross_mult 2.0 | `exec_sim.py:531-533`; `bt_driver_lib.py:135` 对在役 ext_cfg 断言 | 9,122 个交易锚全有 rec_sizing_gross | **IMPL** |
| E-05 | 杠杆死区 ±10% | `book.json:68` + `anchor_loop.py:1555-1558` | 未建模, 每锚无条件重算 | 受据: 死区在实盘 272/272 锚**从未生效** | **APPROX**(≈0, 且方向与实盘一致) |
| E-06 | 最小敞口停机门 4,000 USDT | `book.json:70` + `anchor_loop.py:1980-1994` | 未建模 | NAV0 10 万 ×2 ⇒ gross 20 万; 需 −98% 回撤才咬合(最差路径 −36%) | **MISS**(本次 ≈0) |
| E-07 | 执行器 reshape(非零去均值 + L1) | `legs.py:194-199` ← `anchor_loop.py:414-416`; 顺序 POP→RESHAPE→CLAMP | 原样调用(`exec_sim.py:537-538`) | rec_n_untradable 合计 **92,915** 名-锚 / 8,504 锚 | **IMPL** |
| E-08 | withhold pop 与持有不可交易 clamp | `anchor_loop.py:315-333`, `:462-486` | 同函数; clamp 输出喂 `reduce_only_syms`(`exec_sim.py:540,547`) | rec_n_held_exit 合计 22,449 名-锚 | **IMPL** |
| E-09 | 场所名义上限 `maxNotionalValue` clamp | `anchor_loop.py:824-908`, margin 2% | **未建模**(`exec_sim.py:43` 明写); 镜像 `exchange_info_cache.json` **根本没有该字段** | 镜像 sha 5b437600, 660 名, 键只有 tick/step/min_qty/max_qty/mkt_max_qty/mkt_step/min_notional | **MISS**(本 NAV 下 ≈0: 均仓 ~800 USDT, 名上限 ~2,000 USDT, 远低于任何档位; 随 NAV 放大) |
| E-10 | 场所元数据排除(非 COIN/杠杆代币/非永续) | `external_book.py:533-558` ← `anchor_loop.py:1849-1859` | 执行器侧缺席(`meta` 恒空, `bt_hist_sim31.py:190`); 等价过滤上移到生产者基名单(`b_lib.py:46` noncoin) | `LIVE_EQUIV.json` n_noncoin_names = 76 | **APPROX**(非 COIN 已覆盖; 杠杆代币/状态名未覆盖) |
| E-11 | 目标外持仓出场 | `external_book.py:508-513` | 原样调用(`exec_sim.py:522`) | 22,449 名-锚 / 3,314 锚 | **IMPL** |
| E-12 | 2× 最小名义额尘埃过滤 | `external_book.py:515-531`, mult 2.0 | 原样调用(`exec_sim.py:534-536`) | rec_n_dust_target 合计 **18,596** 名-锚 / 7,261 锚 | **IMPL** |
| E-13 | 计划器前置门(最小名义/取整/无中价) | `binance_executor.py:769-874`; 带 `band_bps` 因 `DEFAULT_BAND_BPS=0.0` 恒等 | 原样调用(`exec_sim.py:547`), stub 同样带 0.0(`:141`) | 下单计划 **1,865,462**; skipped_min_notional **380,197** / 9,070 锚; skipped_no_mid **0** | **IMPL** |
| E-14 | 交易所过滤器(tick/step/minQty/minNotional) | `binance_executor.py:496-554`, 逐模式缓存 | **单张 2026-09-19 快照**套全史(`exec_sim.py:139-140`) | sha 5b437600, 660 名 | **APPROX**(移动最小名义额跳过人口 380,197 与取整; 主项 5 USDT 长期稳定 ⇒ 预期小) |
| E-15 | 逐锚可交易掩码 | exchangeInfo status == TRADING | `tradability_v1` **state_W24H == 2**(近 24h 有成交)(`bt_hist_sim31.py:190`) | rec_n_untradable 92,915 名-锚; tradability sha bebf69ab | **APPROX**(「近 24h 成交」≠「在列且 TRADING」; 方向 = 回放在清淡期比在役少交易) |
| E-16 | 逐名止损 d30_n2(cf40ea21)触发 | `per_name_stop.py:117-142`, wide 档 depth ≤ −0.30 × 连续 2 锚, min_notional 5 USDT | **调用同一纯函数** `PNS.evaluate`(`exec_sim.py:475`), 并断言 profile=wide 且 depth_pct=−0.30(`:137-138`) | 32 路径 **38,644** 次 STOP; seed 0: 1,208 次, 停名 1,601 名-锚 / 952 锚 | **IMPL**(输入近似: 在役读场所 `unrealizedProfit`, 模拟用自己的入场价) |
| E-17 | 止损评估时刻 | 终锚回读一次(`anchor_loop.py:2823-2835`), 下一锚消费 | 历史无回读帧 ⇒ 恒在 **A+2700s(N+45)**(`exec_sim.py:462-465`) | RUN_CONFIG stop_eval 字段 | **APPROX**(差以分钟计, 非以锚计) |
| E-18 | 止损: 只平不加 / maker 优先 / 部分成交残差 / 7 天冷却 | flatten_only `anchor_loop.py:2041-2045`; MARKET 转换只对**被拒**的 maker 且过 25bps 价差门(`binance_executor.py:308,1850-1856`); **部分成交**残差无人追(`:1882-1893`, 裁定 R2′); 冷却自**出场**起算 7 天(`per_name_stop.py:102-109`) | force_flat 进在役 reshape(`exec_sim.py:538`); `e4_block`(`:595`)= 「停名且首腿未被拒 ⇒ 不补腿」, 正是 from_partial/from_reject 的那条分界; 冷却用同一 `active_sets`(`:524`) | seed 0: residual_e4_not_chased **216**; rec_n_cooldown **50,498** 名-锚 / 6,839 锚。E4 起点在历史里设为 0(2026-09-13 才部署) | **APPROX**(25bps 价差门未建模; 「当前配置贯穿全史」) |
| E-19 | **止盈规则** | **在役不存在**。`~/dl_quant_live` grep `take_profit`/`TAKE_PROFIT`/`takeProfit`/`profit_target`/`TRAILING_STOP`/`STOP_MARKET`/`stopPrice`/`callbackRate` **0 命中**; `per_name_stop.py:130` 只测单边 `depth <= depth_pct`; 下单只构造 LIMIT/MARKET。`~/wide_shadow` 同类 grep 亦 0 命中 | 正确地缺席 | 两轮独立 grep 各 0 命中 | **N/A-HIST** |
| E-20 | 书层日止损 −4% 与恢复规则 | `watchdog.py:109` **−4.0(百分数, 不是 −0.04)**; 口径 = 当日末 NAV vs 前日末 NAV(`:1378`); 有划转的日 = UNKNOWN(`:1374-1376`); 触发 ⇒ 梯队 halt→**撤单**→reduce-only 全平→告警(`:3096-3113`)+ 账户 reduce-only; **恢复只能人工**(`ops/resume_from_trip.sh`, 三道硬拒 `:232-249`) | `exec_sim.py:480-490`: 同 UNKNOWN 划转规则; loss < −0.04 ⇒ 在 max(A+2760s, t+1) 平仓; `halt_until` = **次日 UTC 00Z 自动恢复** | 32 路径 **262** 次 FLATTEN, **16** 个不同日期(其中 6 个日期 32/32 路径全中); seed 0: 8 次平仓 / 17 个 HALT 锚; 渲染表 FULL_RECIPE「日止损/停机/持有 = 8.06 / 16.44 / 0」 | **APPROX**(三处具名差异, 见下) |
| E-21 | **看门狗其余条款 §4-1/§4-3/§4-4/§4-4b/§4-5/§4-6/§4-7** | 全部走同一梯队 + 账户 reduce-only + **只能人工恢复**。**§4-4 = 自起始本金累计 −25%**(`:131`, 判 `:1940`, 触发串 `:2012-2014`) | **一条都没有**。RUN_CONFIG `events.rule` 明写「只 §4-2」 | **本次运行实测**: 自完整配方起点(2023-06-30T04Z)算, **32/32 路径**跌破 −25%(最早 2024-03-11T16Z, 中位 2024-03-18T16Z, 最晚 2024-06-13T12Z); 平均 **77.0%** 的完整配方锚在首次跌破之后; 累计最低均 −34.6%(最差 −36.3%)。头条口径 maxDD 4h −38.2% / 5m −38.4% | **MISS**(本审计最大缺口) |
| E-22 | 外部书不可得阶梯(HOLD/DERISK/FLATTEN) | `book.json:167` hold + `anchor_loop.py:253-256` 6 锚 DERISK / 12 锚 FLATTEN | 只有第一级: 无目标文件 ⇒ HOLD 持仓(`exec_sim.py:505-506`) | hold_why_missing = 0 且 hold_why_invalid = 0 ⇒ 阶梯**从未起步**(因 P-23 生产者零跳锚) | **NOT-EXER** |
| E-23 | `open_orders_halted` 与平仓后行为 | `binance_broker.py:1564-1567` **只挡开仓方向**, reduce-only 恒通过; 平仓后按 `BOOK_HELD_HALT_KINDS`(`position_break.py:182`)决定意图是否读作 FLAT | `exec_sim.py:499-504`: HALT ⇒ **整锚空转**(不读目标、任何方向都不下单); 无开仓/减仓之分, 无 position_break | seed 0: TRADE 9,122 / HALT 17; 均 16.44 停机锚/路径 | **APPROX**(回放在停机期把在役会减掉的仓位一起冻住; 量级 0.18% 的锚) |
| E-24 | maker / 重挂 / 追单 三腿结构 | 三腿三个 client-id 后缀(`binance_executor.py:3-10`): ① GTX post-only @ round_px(锚时中价), 驻留 k=900s; ② **恰好一次**重挂被 −5022 拒的计划 @ **新拉的** bookTicker 中价(`:1216-1351`); ③ MARKET 追单(无 price ⇒ 不发 timeInForce), 按 `mkt_max_qty` 切块, 过 25bps 价差门 | 塌缩为**两腿合池结果模型**(`exec_sim.py:556-617`): 首腿抽 拒/全成/零成/部分(p_rej .29064, p_full .79437, p_zero .16011, p_part .04552, fbar .54238); 单一残差腿 π=.60361 成交, maker 占比 .46460; 滑点 首腿 −2.66e-4 / 后腿 −8.69e-5 / 平仓 +4.29e-4; 时间偏移 5 个分位各 1/5 量 | seed 0: first_full 1,050,166 / first_zero 212,465 / first_partial 60,685 / first_refused 542,146; completed_maker 225,966 / completed_taker 261,526 / not_completed 320,174 / below_floor 7,414。换手: 首腿 1.160 亿 / 后腿 0.506 亿 / 平仓 0.020 亿 USDT | **APPROX**(两层: 结构塌缩 + 16 天参数外推) |
| E-25 | 追单实验 —— **只报分配** | `chase_policy.py:98-100` 臂 chase/no_chase/chase_forced, 权重 .5/.5(`:144`), 键 `sha256('{rid}|chase_arm_v2|{symbol}')`(`:166-173`) | 在役 `plan_experiment` 逐锚调用**只取分配**(`exec_sim.py:632-633`); 结果参数跨臂合池, 无任何结果量以臂为条件(`:35-38`) | seed 0 分配计数: chase **136,644** / no_chase **135,773** / chase_forced **517**; 随机臂平衡 **50.16% / 49.84%** | **APPROX** |
| E-26 | 重挂实验 —— **只报分配** | `requote_experiment.py:37-44`, p_requote 0.5 | `exec_sim.py:635-637` 对每个被拒名调在役 `RQ.assign`; 历史里起点设为 0(2026-09-05 才部署) | 被分配人口 = 首腿被拒数 **542,146**(seed 0)。**注: 逐锚 requote 分配计数只在模拟器日志记录里, 未进路径 npz 列 ⇒ 此数为按代码推导, 非从计数列读出** | **APPROX** |
| E-27 | 挂单深度实验(placement bandit) | `placement_bandit.py:33-38` join/behind, ε=0.5(`book.json:129`), 作用于 attempt-1 maker 价(`binance_executor.py:1076-1085`) | **完全未建模**(`exec_sim.py:43` 明写) | — | **MISS**(标定窗内 ε 已是 0.5 ⇒ **均值**已被合池参数吸收; 丢的是离散度与价格路径交互; 量级 ≈ 一半 maker 腿各一个 tick) |
| E-28 | 手续费 | 逐名从 `/fapi/v1/userTrades` 取 commission, BNB 按**永续 bookTicker 中价**折算(`venue_fills.py:708-715`); 被裁定的口径(BNB 现货 1m 收盘)`bnb_conversion.py` **无生产调用方** | 每个时代一套合池 maker/taker; 历史**全程 USDT 时代**(`bt_hist_sim31.py:236`): maker 2.0 bps / taker 5.0 bps | seed 0 手续费 42,458.8 USDT / 换手 1.686 亿 = **2.52 bps**。对实盘校核: HIST_DIAG T_fee sim 308.3610 vs live 332.1617 **比 0.9283**; CAL 比 0.9963 | **APPROX**(诊断周低报 7.2%; 按预注册 fee×1.25 格 = −3.03 pp CAGR 折算, 7% 缺口 ≈ −0.8 pp CAGR) |
| E-29 | 资金费记账 | `/fapi/v1/income` FUNDING_FEE 逐结算按自己的回读仓位计价 | `exec_sim.py:421-433`: f = −q·P·r, q = **结算时刻**持仓, 带恒等式与重复行审计(`bt_hist_sim31.py:75-83`); 费率来自 P2 账本 bea6f575 | seed 0 合计 **−116,799.7 USDT**; HIST_DIAG T_funding 比 1.0319, CAL 比 1.0394; 渲染表 g 分解资金费 +0.57 bps/锚 | **IMPL** |
| E-30 | 执行器侧中性带 + 换手 EMA | **外部书模式下两者皆死**: `anchor_loop.py:1866-1873`「生产者的权重就是目标: 无 compose_book, 无风险预算, 无 harvest EMA, 无中性带」; 跳过点 `:1872-1874` 与 `:2064-2071`; 第三条带 `DEFAULT_BAND_BPS=0.0` 恒等 | 两者皆不施加; stub 同样 0.0(`exec_sim.py:141`) | 活着的那一份在生产者侧(P-21) | **N/A-HIST**(零影响) |
| E-31 | 执行器侧逐名权重/波动上限 | **不存在**: `pos_cap_pct` 99.0 在 `compose_book` 内(`legs.py:249`), 外部书模式不调用; 风险预算同理; `book.json:2` 自列为「内部书专用、外部书下惰性」 | 正确地缺席 | `book_config.py:126` 记录这些是零读者键 | **N/A-HIST** |
| E-32 | 限速 / 传输失败 / 开跑时的在飞订单 | `rate_budget.py`; `SUBMIT_TRANSPORT_ABORT_N=5`; `VENUE_LOCK_CODE=-4400`; 90s 撤单预算; 跨锚在飞单 | **未建模**(`exec_sim.py:43-44`); 历史还从**空书 + 空止损态**冷启(`bt_hist_sim31.py:241-247`, 封存并盖 sha) | — | **MISS**(p_rej=0.2906 已吸收标定窗的**平均**传输损耗; 缺的是它的时变与应力相关性) |
| E-33 | reduce-only 拒单(−2022)处理 | `reduce_only_reject.py` 三分类(benign/disagreement/unresolved), 无书层动作; 它喂的连败计数器**零读者** | 未建模 | `spec_book_reshape.py:342-356` 记录该缺席 | **MISS**(对收益 0) |
| E-34 | 计划外运行全书平仓 / KILL / 人工保护性平仓 | `anchor_loop.py:1290-1301`(实测已发生 3 次全书平仓, dev_frac 0.9639/105 单); `:1102-1113` KILL; `watchdog.py:3117-3135` protective_flatten 行 | **刻意丢掉**: 历史跑 `events='rule'` 只实现 §4-2。`exec_sim` 的 'live' 事件模式会回放真实停机/平仓, 但只覆盖 2026-08-26..09-18 重叠窗, 历史不用 | RUN_CONFIG `events.rule` 文本; `exec_sim.py:492-497` | **N/A-HIST**(对「配方在当前规则下」**合理**; 对「账户会赚多少」**不合理**) |
| E-35 | UNAVAILABLE bar 政策(回放专属) | 无在役对应物 | UA-FREEZE-EXCLUDE(`bt_hist_sim31.py:26-42,275-295`) | seed 0: 冻结 **69** 名-锚 / 66 锚; 持有 UNKNOWN 0、丢弃计划名义 0、缺口内取消成交 0、剔除损益 0.00 USDT | **IMPL**(本窗**零咬合**) |
| E-36 | 生产路径**平价认证的覆盖面** | — | 门 F 把回放目标文件与**归档的实盘目标文件**逐名逐位比 | `GATE_F.json`: PASS, **n_anchors_tested = 12**, 对象 A 共 144 锚, **135 锚因无归档输入不可测**; 12 锚全在 2026-09-17..09-19; 字面差异只有 `f10_sha`(生产者版本差)与 `gross_norm`(CPython Neumaier 求和, `b_lib.py:248-253`)。门史: 第 1 次 FAIL、第 2 次 FAIL、第 3 次 PASS(两次控制修订**写在看到失败之后**, 收据自陈) | **APPROX**(端到端输出平价只覆盖 **12 / 10,039 锚 = 0.12%**, 且集中在 3 天内) |
| E-37 | 执行层**经验验证的覆盖面** | — | v1b 门 v2 用 32 条路径的逐窗条件均值对唯一一条实盘路径 | CAL(93 窗, 样本内)**FAIL 11/12**(败在 price_and_trading: |e| 均 0.214·scale, p90 e/tol 1.005, 11 窗出界); HIST_DIAG(48 窗)PASS 12/12, 但文档自陈**不是独立验证**; 真前瞻验证已预注册、无数据 | **APPROX** |

---

## §2 MISSING 与 APPROXIMATED 的方向与量级(只列非零的)

| 行 | 缺口 | 方向 | 量级 |
|---|---|---|---|
| **E-21** | 看门狗 §4-4「自起始本金 −25% ⇒ 全平 + 停机 + 只能人工恢复」未建模(§4-1/4-3/4-4b/4-5/4-6/4-7 同缺) | **回放高估在役系统会拿到的收益** | **不是小修正而是换了一段历史**: 32/32 路径在 2024 上半年跌破 −25%, 平均 **77.0%** 的完整配方锚落在触发之后, 而 2026 的全部收益都在触发之后。头条 +134.6% / +30.8% 在役规则下需一次人工放行 |
| **P-13** | COMBO_LIVE 飞前地板被按 n_members/400 缩放 | 改变**交易哪本书** | 字面规则 combo 只占 23.5% 的锚, 主表占 66.8%; 代价可由已出数的 `lit` 臂测(本文未测) |
| **E-24** | 三腿塌缩为两腿 + 16 天合池参数套全史 | 未知 | 参数外推那一半有预注册界: 滑点 +50% = **−5.07 pp CAGR**, 手续费 ×1.25 = **−3.03 pp**, 成交率 ×0.9 = **+0.02 pp**; 结构塌缩那一半**无界** |
| **E-28** | 手续费低报 | **回放高估收益** | 诊断周 sim/live 比 **0.9283**; 按 fee×1.25 格线性折算 ≈ **−0.8 pp CAGR** |
| **E-20** | 日止损后**自动**次日恢复 vs 在役**人工**恢复 | 未知 | 受据 `halt_after_every_flatten_19_anchors_never_traded_2026-09-18`: 实盘每次平仓后 8–20 小时不再平衡 ≈ 2–5 锚; 8 次平仓/路径 ⇒ 约 16–40 个多交易的锚 / 9,139(**<0.5%**) |
| **E-23** | 停机时回放冻结**一切**方向, 在役只挡开仓 | 回放在停机期多持了在役会减掉的仓 | 16.44 停机锚/路径 / 9,139 = **0.18%** |
| **E-15** | 可交易掩码用「近 24h 有成交」代替「在列且 TRADING」 | 回放在清淡期少交易 | 未测 |
| **E-14** | 2026-09 的交易所过滤器套全史 | 未知 | 影响 380,197 次最小名义额跳过与取整; 主项(5 USDT)长期稳定 ⇒ 预期小 |
| **E-09** | 场所名义上限 clamp 未建模 | 回放在最大仓位上略高 | 本 NAV 下 ≈0(均仓 ~800 USDT ≪ 任何档位); 随 NAV 放大 |
| **E-27** | 挂单深度实验未建模 | 未知 | 均值已被合池参数吸收(标定窗 ε 已是 0.5); 剩一半 maker 腿各一个 tick 的离散度 |
| **E-32** | 限速/传输/在飞单未建模 | 回放比实盘平滑 | 平均损耗已进 p_rej=0.2906; 时变与应力相关性未知 |
| **P-26** | 实时等价缓存规则 FAIL 后未施加(R0) | 未知 | 死名敞口逐年 **0.0069%–0.045%** 的写入 gross(33–289 名-锚格/年) |
| **P-06 / P-07** | king / F10 用年度折外模型而非在役单一模型 | **刻意**, 方向 = 比在役模型更不利 | 未单独定量(v4 臂与配对表是设计中的对照, 尚未跑) |
| **P-16 / P-17** | PIT 宇宙 + trading24∩COIN 秩基代理 | 秩基是 fund 腿的分母 ⇒ fund z 与在役不同 | 未测; 历史 exchangeInfo 不可得(D3) |
| **E-36** | 端到端输出平价只有 12 锚 | 对数字无方向 | **0.12%** 的锚, 集中在 3 天; 其余靠代码同一性 |
| **E-37** | 执行层标定自己的门在样本内 FAIL | 未知 | CAL 11/12, 唯一通过的是被看过的那一周 |

零影响的具名缺口(记录在案, 不进上表): E-05 杠杆死区(实盘 272/272 从未生效)、E-06 最小敞口门(需 −98% 回撤)、E-33 −2022 处理(观测性)、P-25 TAIL_SCORE(只加日志字段)。

---

## §3 未能核实 / UNVERIFIED

1. **E-26 重挂分配计数**: 逐锚 `requote_assignment_counts` 只存在于模拟器的日志记录里, 没有进路径 npz 的计数列(npz 只有 `armcount_chase/no_chase/chase_forced`)。本文报的「被分配人口 = 542,146」是**按代码推导**(`exec_sim.py:635-637` 对每个 `refused_names` 调用一次)乘以读到的 `out_first_refused`, 不是从计数列读出的。要核实需要重跑 `--keep-decisions` 或读 `AGG_*.npz` 里未导出的日志段。
2. **P-13 缩放读数的代价**: `OBJB_A0|lit|*` 臂已经跑完(32 路径, `BT_RUN_SUMMARY_A0.json` 有它的 events/UA 计数), 但**本文没有计算两个读数的水平差**。要核实只需对两个 run 目录跑一次 `bt_tables main_a0` 的对比, 属于表代理的职责。
3. **P-14 硬截止在实盘的触发频率**: 需要 `~/wide_shadow/state/combo_live_status.json` 的历史(每锚整份重写, 无追加账本) ⇒ 不可回溯。
4. **E-21 的其余条款**: §4-1(成本 >9bps 连 5 日)、§4-6(权重保真 corr<0.85 连 3 日)、§4-7(再平衡失败率 >5% 连 3 日)**可以从本次运行的输出直接评估**, 本文只评估了 §4-4。§4-3(崩跌日 markout 尾部)与 §4-5(场所/账户/仓位断裂)在回放里没有可用输入。
5. **A0_ext(延长段 2026-08-31T04Z → 09-18T20Z)**: 目标已出齐(`TARGETS_A0_ext.npz` 085d8858, EXT_REPRO 共同 10,039 锚**逐位全同**, 收据 PASS), 表侧的 `OBJB_A0X_*` 运行目录已存在但**尚无 `BT_RUN_SUMMARY_A0X.json`**, 所以本文的全部触发计数取自 A0 主运行。

---

## §4 本审计不主张

- 不主张任何历史水平、夏普或期望; 本文没有算一个新的书层收益数, 引用的都是已入库收据里的数。
- 不主张模拟器是对的或是错的; 只主张它验证过什么、没验证过什么(E-36 / E-37)。
- 不修任何缺口。E-21 是一个真缺口, 按任务书**只报不修**。
- 不改他人文件: 未改 `STATE.md`、错题集、记忆、对象 B / 基线表 / 模拟器的任何收据与装置。
- 不建议任何实盘改动。

---

## §5 收据与复跑

| 件 | 值 |
|---|---|
| 机读矩阵 | `multi_asset/exports/research/coverage_audit_2026-09-20/receipts/COVERAGE_MATRIX.json` sha256 `e19b7f01e0f6e50c25f002290b47144c6305509d96450d3cac26f9427ee4e613` |
| 在役执行器 | `git -C ~/dl_quant_live rev-parse HEAD` = `409ea162746d0ba459db33c3f5c07865c24a7514` |
| 在役生产者 | `shasum -a 256 ~/wide_shadow/shadow_loop_v3.py` = `e9c98374…`; `~/wide_shadow/fea171/combo_stage.py` = `3520d363…`; `~/wide_shadow/shadow_bundle/config.json` = `3a8422f3…` |
| 8/8 模块 sha 核对 | Mac `shasum -a 256 live/{binance_executor,external_book,per_name_stop,chase_policy,requote_experiment}.py scheduler/anchor_loop.py signal/legs.py config/book.json` vs pod2 `sha256sum /workspace/replay_r_2026-09-19/work/exec_mirror/exec_tree_409ea16/<同名>` |
| 生产者装置 diff | `diff ~/wide_shadow/shadow_loop_v3.py <pod2 devices/shadow_loop_v3_replay.py>`(3 hunks, 2 行为性); `diff <(sed -n '2,$p' devices/combo_stage_replay_3520d363.py) ~/wide_shadow/fea171/combo_stage.py`(3 hunks) |
| 生产者侧计数 | pod2 `/workspace/object_b_2026-09-19/work/A0_main/P3.json`(10,039 条逐锚记录) |
| 执行侧计数 | pod2 `/workspace/baseline_tables_2026-09-19/runs/OBJB_A0_scaled_rule_raw_UAFE/PATH_*_seed_*.npz`(32 × 9,139) |
| §4-4 跌破测算 | 对 32 条路径取 `navm1 / navm0[k(2023-06-30T04Z)] − 1`, 求首个 < −0.25 的锚(逐字命令在 COVERAGE_MATRIX.json 的 E-21 行 evidence 字段) |
| 表侧汇总 | `.../baseline_tables_2026-09-19/receipts/pod2/receipts/BT_RUN_SUMMARY_A0.json`、`receipts/A0_TABLES_rendered.md` |
| 门收据 | `.../object_b_2026-09-19/receipts/{GATE_F.json, LIVE_EQUIV.json, TARGETS_A0_main.json, RUN_CONFIG_A0_main.json}`; `.../replay_exec_2026-09-19/V1B2_GATE_v31_{CAL,HIST_DIAG}_*.json` |

资源: 本次审计只读, 未跑任何训练或回放; pod2 上只做了 npz/json 读取(单进程 < 1 GB, 各 < 10 s), 未杀任何进程, 未写 pod2 任何目录。
