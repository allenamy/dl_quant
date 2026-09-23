> **创建:** 2026-09-23 09:29Z | **Session:** session_01MCyx6gj5EdbghE9bwjBjJv(Stage 1 执行代理,受 lead 派) | **状态:** 按预注册 8530d2b7f + 修订 1(70adc6cac)执行完毕;判词 **UNDECIDED**;不含任何换装建议 | **作废条件:** OLD / OLD_HOLD / NEW 目标文件、认证引擎(exec_sim 29679672 / bt_hist_sim31 8ae6e2a4 / 标定 fda34243)、`ovn_stats.py`(1c35efb5)或预注册 / 修订 1 改动

# 结果:在役模型(OLD)vs 修复输入重训模型(NEW)—— 同引擎整书对照(Stage 1)

预注册 `docs/PREREG_old_vs_new_models_same_engine_2026-09-23.md`(8530d2b7f,sha 1217d786);修订 1 `docs/AMENDMENT_1_old_vs_new_models_same_engine_2026-09-23.md`(70adc6cac,sha 73336df6)。判据一个字没改。装置与收据在 `multi_asset/exports/research/old_vs_new_2026-09-23/`。

## §0 结论(白话)

**判词:UNDECIDED。** 两个 NEW 种子对两个旧对照(OLD、OLD_HOLD)都没有同时满足 G1–G5,所以不是 PASS;两个种子对 OLD_HOLD 的 G1 区间上界都远大于 0,所以也不是 REVERSE。

| 种子 | 对 OLD | 对 OLD_HOLD |
|---|---|---|
| NEW_s42 | G1 **不过**(+8.51 bps/日,97.5% 区间 [−0.37, +21.19]);G2–G5 全过 | G1 **不过**(+5.98,[−1.35, +15.48]);G3 **不过**(最差段 Sharpe −0.783,门 ≥ −0.769);G2 / G4 / G5 过 |
| NEW_s2027 | G1 **不过**(+7.14,[−0.84, +18.27]);G2–G5 全过 | G1 **不过**(+4.62,[−1.91, +12.93]);G3 **不过**(最差段 Sharpe −0.888,门 ≥ −0.769);G2 / G4 / G5 过 |

读法(只陈述测到的,不替 lead 判):

1. **方向**:pre-2026 判据窗里,两个 NEW 种子的点估计都高于两个旧对照,但幅度不同:对 OLD 高 7–8.5 bps/日,对 OLD_HOLD 高 4.6–6.0 bps/日。**卡住 G1 的是 Bonferroni 97.5% 区间的下界**,四个比较的下界都略低于 0。
2. **逐段**:NEW 对 OLD 三段全赢。对 OLD_HOLD,2024 和 2025 赢,**2023H2 两个种子都略输**(−0.26 / −0.47 bps/日)。G3 对 OLD_HOLD 失败也出在 2023H2:OLD_HOLD 在这一段的 Sharpe(−0.67)高于 NEW(−0.78 / −0.89)。
3. **C1(发布语义)是真实的、可量化的**:同一个旧模型,只把「门失败时交易 King 回退书」改成「持有」,pre-2026 的日差是 +2.53 bps/日(三段全正,区间跨 0)。NEW−OLD 的 8.5 里,约 2.5 来自这个语义差,约 6.0 来自模型或输入差(这是线性恒等式 NEW−OLD = (NEW−OLD_HOLD) + (OLD_HOLD−OLD),按所示三位小数成立:8.506 = 5.979 + 2.527;以 s42 为例)。
4. **成本不是解释**:三个认证成本格下,四个比较的点估计符号都不变,量级几乎不动(G4 全过)。pre-2026 NEW 的换手是 OLD 的 52–59%(0.050 / 0.057 对 0.096),手续费低 41–47%(0.128 / 0.144 对 0.243 bps/锚/gross)(见现金分解)。
5. **2026(只报告)四臂几乎一样**:Sharpe 4.15–4.25,NEW 对 OLD 仅 +0.8 到 +1.4 bps/日。**2026-08-31→09-18(只描述,18 天)NEW 略差于 OLD**(−3.6 / −2.1 bps/日)。
6. **R-P(只报告)**:以 2023-06-30T04Z 为起点、−25% 永久停机时,OLD 32/32 条路径在 2024-03-18 附近触线,OLD_HOLD 10/32 触线,NEW 两个种子都是 0/32。窗口一直到 2026-08-31,包含 2026。

**不在本文结论范围内**:是否换装、是否放宽判据、是否再做别的检验。这些都由 lead 与用户裁定。


## §1 时间线(修订 1 与我第一次读到 NAV 的先后)

| 时刻(UTC) | 事件 | 收据 |
|---|---|---|
| 05:49 | 开始:读预注册(8530d2b7f,sha 1217d786)、认证引擎、NEW 目标 | — |
| 06:00 | 执行口径落盘(先于任何数字) | `receipts/OVN_OPERATIONALISATION.json` |
| 06:03–06:05 | **事故**:我的适配器测试临时副本把 `/workspace` 配额用尽(EDQUOT),卷上所有写入失败约 2 分钟;删掉自己的临时文件后恢复。收集器输出自 09-11 16:24 起就没写过,未受影响。此后运行输出一律放 `/dev/shm/ovn_2026-09-23` | `logs/OVN_INCIDENTS.log` |
| 06:16 | 身份披露写成(`written_before_any_nav: true`) | `receipts/IDENTITY_DISCLOSURE.json` |
| 06:17 | 提交 e6d8f6680:口径、适配器、红绿测试、身份披露、配置、diff | git |
| 06:19 | 启动 OLD / NEW_s42 / NEW_s2027 主运行与两条延伸运行 | `logs/launch_*.log` |
| ~06:25 | 统计装置空跑,用的是**已发布**的认证 A0 与 V4 运行(不是本对照):读到 A0 2024 段 +18.3% / Sharpe 0.96 / 回撤 −26.9%(A0 = OLD 的已发布认证数字,预注册写明 lead 早已看过),以及 V4−A0 的空跑差值(V4 ≠ NEW) | `logs/stats_dryrun.log` |
| **08:00:19** | **lead 提交修订 1(70adc6cac)** | git |
| 08:10 | 我读到修订 1;OLD_HOLD 目标构建并验过(`OVN_OLD_HOLD VERDICT=PASS`),启动 OLD_HOLD 运行 | `targets/TARGETS_OLD_HOLD.json` |
| 08:15:31 | 提交 87603a450:OLD_HOLD 装置与配置、双对照统计装置。**截至此时我没有读过任何 OVN 的 NAV 或由 NAV 导出的数字**;对 OVN 运行只核过路径文件的 sha 是否与认证运行一致 | git |
| 08:25:55–08:26 | **事故**:我的 4 个启动器进程组(父进程 + bash 包装)被外部结束,没有写出 EXIT 行;每组只剩刚派生的一个工作进程(成为孤儿,正常跑完)。`oom_kill` 计数没有变化,3 MB 的 bash 包装也一起消失,不像 OOM;来源不明,不是我做的。路径文件全部原子写入,用 `--resume` 按 sha 复核后续跑(标签 `*_r2`)| `logs/OVN_INCIDENTS.log` |
| 08:40 | 描述性延伸段(08-31→09-18)的装置输出:**这是我第一次读到 OVN 的 NAV 导出数字**(晚于修订 1 的 08:00:19) | `receipts/OVN_EXT.json` |
| 09:22:32–09:23:27 | 判据统计与判词(`OVN_STATS VERDICT=UNDECIDED`,后处理链 `EXIT 0`) | `receipts/pod2/OVN_STATS.json` |

## §2 做了什么(装置与数据身份)

| 环节 | 做法 | 收据 |
|---|---|---|
| NEW 目标搬到持久存储 | pod2 `/tmp/codex_combo_20260923/combo_s{42,2027}` 的 6 个文件与本地备份 `artifacts/combo_targets` 的 sha256 逐一相等;复制到 `/workspace/old_vs_new_2026-09-23/new_targets` 后再核一遍 | `receipts/NEW_TARGETS_COPY_SHA256SUMS.txt` |
| 执行口径(先于任何数字) | 预注册没写明的做法先落盘:日序列只用完整 UTC 日;「路径均值」= 32 条路径各自指标的算术均值;97.5% 双侧区间 = 自举分位 1.25 / 98.75;NEW 轴开始之前的 1,110 个锚写成 HOLD,等等 | `receipts/OVN_OPERATIONALISATION.json`(提交 e6d8f6680,早于任何 NAV) |
| 适配器 | NEW `trade_mask` 为真 ⇒ kind 2,CSR 行 = `weights[i]` 的非零项;为假 ⇒ kind 0(HOLD,不写文件,执行器保持上一锚的持仓)。用**认证加载器** `bt_objb_targets.py`(05cc5dc2)读回后,scaled 6,723 / 6,308 个发布锚、lit 3,072 / 3,042 个发布锚**逐位相等**(uint64 视图);NEW 权重落在 PIT 宇宙外的名数 = 0 | `targets/TARGETS_NEW_s{42,2027}.json` |
| 适配器红绿测试 | 先断言基线为绿,再做 5 个变异,每个都必须因**指定的原因**变红:索引 +1、发布行改为持有、权重值 +1 ulp、交换两个符号、在持有行塞入权重。原文 `OVN_ADAPTER_TEST VERDICT=PASS baseline=GREEN mutations_red_as_named=5/5`,`EXIT 0` | `receipts/OVN_ADAPTER_TEST_s42.json`、`logs/ovn_adapter_test_s42.log` |
| 引擎 | 认证装置原样复制并逐一核 sha:`bt_launch.py` 393a8dc8、`bt_driver_lib.py` ba3bc261、`bt_hist_sim31.py` 8ae6e2a4、`exec_sim.py` 29679672,合池标定 fda34243;32 条成交路径(种子 0..31)。成交随机数按 (seed, rid, symbol, leg) 逐单哈希生成,**不带状态**,两臂在同一笔请求上用的是同一个随机数 | 各路径 `PATH_*.json` 里的 `device_sha256` |
| 配置 | OLD = 认证 `RUN_CONFIG_main_A0_2026-09-19.json`(7b6dca2c)原样,只改标签和输出根目录(run tag 不变,便于逐字节比对);NEW = OLD 配置只换目标来源、arm/tag/role 与血统块。叶级 diff 已断言:**所有设置逐字节相同** | `receipts/OVN_CONFIG_DIFF.json`、`configs/` |
| OLD 复现对照 | OLD 在新根目录里把 5 格 × 32 条路径全部重跑一遍;每个路径 npz 的 sha256 必须与认证运行一致,否则停机。**结果:160 / 160 逐字节相同**(base / fee / slip / fill / lit 各 32 / 32),今天跑的引擎就是认证引擎 | `receipts/pod2/OVN_STATS.json` → `preconditions.P1_old_reproduction` |
| 统计装置自检 | 先在**已发布**的 A0 / V4 运行上空跑(不是本对照的数字):2024 段均值路径总收益 +18.3%、Sharpe 0.96、5 分钟回撤 −26.9%,与认证 A0 表逐项一致 | 空跑日志 `logs/stats_dryrun.log`、`logs/stats_dryrun2.log`(第二次含恒等对照:同一臂自比得 0.000,区间 [0, 0]) |

## §3 身份披露摘要(预注册 §1.7;全文在 `receipts/IDENTITY_DISCLOSURE.json`,在任何 NAV 之前写成)

| # | 项目 | 实测 |
|---|---|---|
| 1 | OLD 每年由哪一折服务;是否样本内 | King:2023H2 全部由 fold 2023 服务;2024 / 2025 / 2026 的头 181 个锚沿用上一年的折(30 天规则),其余由当年折服务。F10:每年由当年折服务。**在五个段内逐锚检查,被训练标签覆盖的锚(label_end > A)King 0、F10 0;违反服务规则的锚也是 0。** 需要注意:OLD 的 F10 在每年第一锚与训练标签末只隔 1 个锚,没有 NEW 那样的 60 锚隔离 |
| 2 | NEW 每折标签截止 vs 首服务锚(须 ≥ 60 锚隔离) | King 五折(含只影响席位历史的 2022H2 预热折)的间隔**都正好是 60 锚** ✅;在 combo 轴上逐锚检查,King 最小间隔 60。F10 两个种子各 23 折,最小间隔 **217 锚** ✅(训练器只取合格训练锚的前 85%,所以实际间隔远大于 60:2023 折 217,2024 折 546,202501 折 875) |
| 3 | 两边 scaled 发布门的规则原文与逐段可发布锚数 | 原文(带文件 sha 与行号)在收据 `item3_gates`。OLD(`b_driver.py` aaf82ba6):okf ≥ ⌈380n/400⌉、0.4 ≤ gross ≤ 1.2、names ≥ ⌈150n/400⌉、全部权重在宇宙内、宇宙内名数 ≥ ⌈150n/400⌉、宇宙内 gross > 0.4、King 文件存在;**失败 ⇒ 交易 King 文件**。NEW(`combo_target.py` d7577e82):okf ≥ int(ceil(.95n))、0.4 ≤ gross ≤ 1.2、names ≥ int(ceil(.375n));**失败 ⇒ HOLD**。两套下限公式在 n = 1..829 上整数完全相同(0 处不符)。**规则不同,记为具名混淆 C1–C3**(见下) |
| 4 | NEW → 认证 CSR 适配器往返逐位相等 | 通过:scaled 6,723(s42)/ 6,308(s2027)个发布锚、lit 3,072 / 3,042 个发布锚,经认证加载器读回后逐位相等;红绿测试 5/5 变异按指定原因变红。OLD_HOLD 改写同样有往返测试(3,337 个改写锚写回后与 OLD 逐位相等) |
| 5 | 两臂配置 diff | NEW 对 OLD:只有标签、arm / tag / role、目标来源(npz 与收据的路径和 sha)、血统块不同;OLD_HOLD 对「去掉 lit 运行的 OLD」同样如此。全部由装置断言 |

逐段可发布锚数(scaled 读法;OLD 的「回退」= 门失败后交易 King 文件,NEW 与 OLD_HOLD 的「持有」= 不写文件、维持上一锚的合约数量):

| 段 | OLD:combo / King 回退 | OLD_HOLD:combo / 持有 | NEW_s42:发布 / 持有 | NEW_s2027:发布 / 持有 |
|---|---|---|---|---|
| 2023H2(1,109 锚) | 886 / 223 | 886 / 223 | 753 / 356 | 757 / 352 |
| 2024(2,196) | 1,902 / 294 | 1,902 / 294 | 1,931 / 265 | 1,576 / 620 |
| 2025(2,190) | 1,384 / 806 | 1,384 / 806 | 1,668 / 522 | 1,508 / 682 |
| 2026 至 08-31(1,453) | 1,453 / 0 | 1,453 / 0 | 1,453 / 0 | 1,453 / 0 |

NEW 的持有原因全部是 gross 超出 [0.4, 1.2]。

**具名混淆**(NEW 与 OLD 的差不只是「模型不同」):

- **C1 失败动作不同**:OLD 交易 King 回退书,NEW 持有。修订 1 为此加了 OLD_HOLD 臂,C1 的量化见 §5。
- **C2 门的条件不同**:OLD 还要求权重全在宇宙内、宇宙内名数与宇宙内 gross 过线、King 文件存在;NEW 没有这些条件(它的链本身掩码到合法集)。
- **C3 n 不同**:同一个公式,OLD 用生产者当锚的成员数,NEW 用修正后的成员列表。各段平均 n:OLD 196 / 262 / 378 / 395,NEW 207 / 273 / 388 / 400。
- **C4 模型新鲜度不同,两个方向都有(运行前补记,早于 NAV)**:每年年初 OLD 的 F10 比 NEW 新鲜(间隔 1 锚对 ≥ 217 锚);从 2025 年起 NEW 的 F10 每月重训,OLD 每年一次;King 方面,OLD 在每年头 30 天沿用上一年的折,NEW 从 1 月 1 日起就用新折(间隔 60)。
- **C5 状态起点**:NEW 的组合状态从 2023-01-01 以零起步(之前 1,110 个锚写成持有,即空仓);OLD 的链从 2022-01-31 冷启动。到判据窗(2023-06-30T04Z)两边都已热身。

## §4–§9 数表(逐字来自 `receipts/OVN_TABLES_rendered.md`, sha256 c02dbbf46d3f1a9a;每个数都读自带 sha 的收据)

顺序:§4 判词行与 G1–G5 实测 vs 门(每个种子对两个对照)→ §5 C1 量化(OLD_HOLD − OLD,非判据)→ §6 逐段表(R-main,含 §4-2 日止损事件数与逐名止损数)→ §7 现金分解 → §8 认证均值路径(描述)→ §9 成本格与 literal 读数、2026-08-31→09-18 延伸段(只描述)、R-P / R-P2(只报告)。单位:d̄ 为 bps/日(完整 UTC 日);g 与现金分解为 bps/锚/单位目标 gross;收益与回撤为 %。

<!-- rendered by ovn_render.py from OVN_STATS.json sha256 660ea5584fee439d4189b0de221da79614e4a50b3d82c136eb5b08eaa773c81a; OVN_EXT.json sha256 2384e4799ff8cd6b7ea68c7b5d5bdb4ff5b176738695fda4bd629db24e787775 -->

### Verdict lines (AMENDMENT 1: each NEW seed must pass G1–G5 against BOTH OLD and OLD_HOLD)

- NEW_s42 vs OLD: G1=FAIL (+8.506 bps/day, 97.5% CI 30d [-0.370, +21.191]) · G2=PASS (3/3) · G3=PASS · G4=PASS · G5=PASS · all=FAIL
- NEW_s42 vs OLD_HOLD: G1=FAIL (+5.979 bps/day, 97.5% CI 30d [-1.354, +15.482]) · G2=PASS (2/3) · G3=FAIL · G4=PASS · G5=PASS · all=FAIL
- NEW_s2027 vs OLD: G1=FAIL (+7.142 bps/day, 97.5% CI 30d [-0.836, +18.266]) · G2=PASS (3/3) · G3=PASS · G4=PASS · G5=PASS · all=FAIL
- NEW_s2027 vs OLD_HOLD: G1=FAIL (+4.615 bps/day, 97.5% CI 30d [-1.909, +12.928]) · G2=PASS (2/3) · G3=FAIL · G4=PASS · G5=PASS · all=FAIL
- **VERDICT = UNDECIDED** — AMENDMENT 1: PASS iff both NEW seeds pass G1..G5 against OLD AND against OLD_HOLD; REVERSE iff both seeds' G1 97.5% interval (30-day blocks) upper bound vs OLD_HOLD < 0; else UNDECIDED (which control each seed passed is listed)
- which control each seed passed: {"NEW_s42": {"OLD": false, "OLD_HOLD": false}, "NEW_s2027": {"OLD": false, "OLD_HOLD": false}}; original prereg verdict vs OLD only (superseded, transparency): UNDECIDED

### G1–G5 for NEW_s42: measured vs gate, against each control

| # | gate | vs OLD | vs OLD_HOLD |
|---|---|---|---|
| G1 | pre-2026 d̄ mean > 0 and 97.5% two-sided lower bound (30-day blocks) > 0 | +8.506 bps/day; 97.5% [-0.370, +21.191] (30d); 95% [+0.564, +19.190]; 5d-block 97.5% [+0.610, +18.363]; 915 d × 32 paths → **FAIL** | +5.979 bps/day; 97.5% [-1.354, +15.482] (30d); 95% [-0.482, +14.239]; 5d-block 97.5% [-0.784, +13.756]; 915 d × 32 paths → **FAIL** |
| G2 | ≥ 2 of 3 segments with mean d̄ > 0 | 2023H2 +6.098 / 2024 +4.804 / 2025 +13.431 → 3/3 → **PASS** | 2023H2 -0.259 / 2024 +3.052 / 2025 +12.059 → 2/3 → **PASS** |
| G3 | NEW worst-segment Sharpe ≥ control worst − 0.10; pre-2026 maxDD (path mean) not worse than control by > 2 pp | worst-seg Sharpe NEW -0.783 vs ctrl -1.817 (need ≥ -1.917) ok; maxDD5m NEW -18.1% vs ctrl -38.4% (need ≥ -40.4%) ok → **PASS** | worst-seg Sharpe NEW -0.783 vs ctrl -0.669 (need ≥ -0.769) FAIL; maxDD5m NEW -18.1% vs ctrl -29.0% (need ≥ -31.0%) ok → **FAIL** |
| G4 | G1 point estimate keeps sign under fee×1.25 / slip×1.5 / fill×0.9 | fee_x1.25 +8.763; slip_x1.5 +8.944; fill_x0.9 +8.377 (base +8.506) → **PASS** | fee_x1.25 +6.034; slip_x1.5 +6.061; fill_x0.9 +5.988 (base +5.979) → **PASS** |
| G5 | pre-2026 §4-2 day-stop events (path mean) NEW ≤ 1.25 × control | NEW 3.94 vs limit 8.05 (ctrl 6.44) → **PASS** | NEW 3.94 vs limit 7.15 (ctrl 5.72) → **PASS** |

G1 with the partial first day included (sensitivity): vs OLD: +8.572 bps/day, changes G1: False; vs OLD_HOLD: +6.048 bps/day, changes G1: False. 2026 segment mean d̄ (report only): vs OLD +1.429 bps/day; vs OLD_HOLD +1.483 bps/day

### G1–G5 for NEW_s2027: measured vs gate, against each control

| # | gate | vs OLD | vs OLD_HOLD |
|---|---|---|---|
| G1 | pre-2026 d̄ mean > 0 and 97.5% two-sided lower bound (30-day blocks) > 0 | +7.142 bps/day; 97.5% [-0.836, +18.266] (30d); 95% [+0.042, +16.751]; 5d-block 97.5% [-0.912, +16.774]; 915 d × 32 paths → **FAIL** | +4.615 bps/day; 97.5% [-1.909, +12.928] (30d); 95% [-1.198, +11.815]; 5d-block 97.5% [-1.835, +12.051]; 915 d × 32 paths → **FAIL** |
| G2 | ≥ 2 of 3 segments with mean d̄ > 0 | 2023H2 +5.892 / 2024 +4.077 / 2025 +10.844 → 3/3 → **PASS** | 2023H2 -0.465 / 2024 +2.325 / 2025 +9.472 → 2/3 → **PASS** |
| G3 | NEW worst-segment Sharpe ≥ control worst − 0.10; pre-2026 maxDD (path mean) not worse than control by > 2 pp | worst-seg Sharpe NEW -0.888 vs ctrl -1.817 (need ≥ -1.917) ok; maxDD5m NEW -17.6% vs ctrl -38.4% (need ≥ -40.4%) ok → **PASS** | worst-seg Sharpe NEW -0.888 vs ctrl -0.669 (need ≥ -0.769) FAIL; maxDD5m NEW -17.6% vs ctrl -29.0% (need ≥ -31.0%) ok → **FAIL** |
| G4 | G1 point estimate keeps sign under fee×1.25 / slip×1.5 / fill×0.9 | fee_x1.25 +7.484; slip_x1.5 +7.689; fill_x0.9 +7.122 (base +7.142) → **PASS** | fee_x1.25 +4.755; slip_x1.5 +4.805; fill_x0.9 +4.733 (base +4.615) → **PASS** |
| G5 | pre-2026 §4-2 day-stop events (path mean) NEW ≤ 1.25 × control | NEW 4.62 vs limit 8.05 (ctrl 6.44) → **PASS** | NEW 4.62 vs limit 7.15 (ctrl 5.72) → **PASS** |

G1 with the partial first day included (sensitivity): vs OLD: +7.306 bps/day, changes G1: False; vs OLD_HOLD: +4.782 bps/day, changes G1: False. 2026 segment mean d̄ (report only): vs OLD +0.766 bps/day; vs OLD_HOLD +0.821 bps/day

### C1 quantified: OLD_HOLD − OLD (same model, only the failure action differs; NOT a criterion)

| quantity | value |
|---|---|
| G1-form | +2.527 bps/day; 97.5% [-2.639, +8.605] (30d); 95% [-2.010, +7.709]; 5d-block 97.5% [-2.699, +8.099]; 915 d × 32 paths → FAIL |
| G2-form | 2023H2 +6.357 / 2024 +1.752 / 2025 +1.372 → 3/3 → PASS |
| G3-form | worst-seg Sharpe NEW -0.669 vs ctrl -1.817 (need ≥ -1.917) ok; maxDD5m NEW -29.0% vs ctrl -38.4% (need ≥ -40.4%) ok → PASS |
| G5-form | NEW 5.72 vs limit 8.05 (ctrl 6.44) → PASS |

### Per segment, R-main (base cost cell, scaled reading): 32-path mean [2.5%, 97.5%]

| segment | arm | Sharpe (full UTC days) | total return | CAGR | maxDD 5m | worst day | §4-2 day stops | per-name stops | turnover/gross per anchor | n windows / full days |
|---|---|---|---|---|---|---|---|---|---|---|
| 2023H2 | OLD | -1.82 [-2.00, -1.59] | -15.8% [-17.2%, -14.1%] | -28.9% [-31.2%, -26.0%] | -22.0% [-23.2%, -20.8%] | -3.04% [-3.17%, -2.92%] | +0.0 [+0.0, +0.0] | +55 [+52, +59] | 0.1158 | 1109 / 184 |
| 2023H2 | OLD_HOLD | -0.67 [-0.90, -0.48] | -5.3% [-7.2%, -3.7%] | -10.1% [-13.7%, -7.1%] | -12.8% [-13.9%, -11.6%] | -2.85% [-2.97%, -2.78%] | +0.0 [+0.0, +0.0] | +57 [+54, +61] | 0.0878 | 1109 / 184 |
| 2023H2 | NEW_s42 | -0.78 [-0.99, -0.49] | -5.0% [-6.6%, -2.6%] | -9.5% [-12.6%, -5.2%] | -14.8% [-16.1%, -13.1%] | -3.08% [-3.64%, -2.65%] | +0.3 [+0.0, +1.0] | +75 [+69, +79] | 0.0538 | 1109 / 184 |
| 2023H2 | NEW_s2027 | -0.89 [-1.12, -0.59] | -4.4% [-6.4%, -2.2%] | -8.5% [-12.2%, -4.2%] | -15.0% [-16.0%, -14.0%] | -4.09% [-4.90%, -3.68%] | +1.0 [+0.8, +1.0] | +87 [+83, +91] | 0.0545 | 1109 / 184 |
| 2024 | OLD | +0.95 [+0.77, +1.06] | +18.3% [+14.1%, +20.8%] | +18.2% [+14.1%, +20.8%] | -26.9% [-28.3%, -25.7%] | -4.31% [-4.47%, -4.20%] | +1.0 [+1.0, +1.0] | +258 [+251, +268] | 0.0867 | 2196 / 366 |
| 2024 | OLD_HOLD | +1.21 [+1.06, +1.36] | +25.8% [+22.0%, +29.7%] | +25.8% [+22.0%, +29.6%] | -24.6% [-26.2%, -23.4%] | -4.30% [-4.49%, -4.01%] | +1.0 [+0.8, +1.0] | +307 [+295, +323] | 0.0655 | 2196 / 366 |
| 2024 | NEW_s42 | +1.85 [+1.67, +2.00] | +41.0% [+36.1%, +44.8%] | +40.9% [+36.0%, +44.6%] | -13.7% [-14.9%, -12.4%] | -3.75% [-4.38%, -3.42%] | +0.2 [+0.0, +1.0] | +357 [+317, +376] | 0.0649 | 2196 / 366 |
| 2024 | NEW_s2027 | +1.73 [+1.57, +1.91] | +37.4% [+33.3%, +42.0%] | +37.2% [+33.2%, +41.9%] | -12.9% [-14.2%, -11.7%] | -3.71% [-4.39%, -3.15%] | +0.4 [+0.0, +1.0] | +471 [+438, +500] | 0.0537 | 2196 / 366 |
| 2025 | OLD | +0.21 [-0.06, +0.43] | +2.2% [-4.9%, +7.9%] | +2.2% [-4.9%, +7.9%] | -27.7% [-30.0%, -26.3%] | -4.62% [-5.04%, -4.28%] | +5.4 [+4.0, +7.0] | +480 [+469, +490] | 0.0963 | 2190 / 365 |
| 2025 | OLD_HOLD | +0.42 [+0.28, +0.58] | +7.6% [+3.8%, +12.1%] | +7.6% [+3.8%, +12.1%] | -19.6% [-22.8%, -18.5%] | -6.90% [-7.20%, -6.68%] | +4.8 [+4.0, +6.0] | +668 [+576, +691] | 0.0559 | 2190 / 365 |
| 2025 | NEW_s42 | +1.89 [+1.69, +2.05] | +65.6% [+56.0%, +73.4%] | +65.6% [+56.0%, +73.4%] | -12.4% [-13.2%, -11.8%] | -4.78% [-4.96%, -4.42%] | +3.3 [+2.0, +4.0] | +644 [+567, +661] | 0.0512 | 2190 / 365 |
| 2025 | NEW_s2027 | +1.65 [+1.47, +1.86] | +51.3% [+43.6%, +61.6%] | +51.3% [+43.6%, +61.6%] | -12.1% [-12.9%, -11.5%] | -4.46% [-4.80%, -4.32%] | +3.2 [+3.0, +4.0] | +525 [+514, +532] | 0.0451 | 2190 / 365 |
| pre2026 | OLD | +0.12 [-0.04, +0.24] | +1.8% [-6.7%, +9.4%] | +0.7% [-2.7%, +3.6%] | -38.4% [-39.8%, -36.8%] | -4.62% [-5.04%, -4.36%] | +6.4 [+5.0, +8.0] | +793 [+782, +806] | 0.0964 | 5495 / 915 |
| pre2026 | OLD_HOLD | +0.53 [+0.45, +0.63] | +28.3% [+22.3%, +35.7%] | +10.4% [+8.4%, +12.9%] | -29.0% [-30.6%, -27.5%] | -6.90% [-7.20%, -6.68%] | +5.7 [+5.0, +7.0] | +1031 [+932, +1071] | 0.0661 | 5495 / 915 |
| pre2026 | NEW_s42 | +1.44 [+1.35, +1.55] | +121.9% [+110.3%, +135.3%] | +37.4% [+34.5%, +40.6%] | -18.1% [-20.3%, -15.8%] | -4.78% [-4.96%, -4.42%] | +3.9 [+3.0, +5.2] | +1075 [+958, +1109] | 0.0572 | 5495 / 915 |
| pre2026 | NEW_s2027 | +1.28 [+1.21, +1.39] | +98.6% [+89.6%, +110.5%] | +31.4% [+29.0%, +34.5%] | -17.6% [-19.5%, -15.8%] | -4.49% [-4.90%, -4.32%] | +4.6 [+4.0, +6.0] | +1083 [+1047, +1113] | 0.0504 | 5495 / 915 |
| 2026 | OLD | +4.15 [+3.87, +4.45] | +130.6% [+117.2%, +142.7%] | +252.4% [+221.9%, +280.5%] | -18.2% [-19.9%, -16.6%] | -4.61% [-4.73%, -4.49%] | +1.6 [+1.0, +3.4] | +329 [+318, +339] | 0.0482 | 1453 / 242 |
| 2026 | OLD_HOLD | +4.15 [+3.82, +4.43] | +130.3% [+114.6%, +142.7%] | +251.7% [+216.2%, +280.6%] | -18.1% [-19.8%, -16.5%] | -4.61% [-4.73%, -4.48%] | +1.6 [+1.0, +3.4] | +326 [+315, +335] | 0.0484 | 1453 / 242 |
| 2026 | NEW_s42 | +4.25 [+4.00, +4.54] | +138.3% [+124.2%, +151.2%] | +270.3% [+237.6%, +300.9%] | -19.7% [-20.9%, -18.2%] | -4.81% [-5.05%, -4.40%] | +2.6 [+2.0, +3.2] | +320 [+312, +329] | 0.0485 | 1453 / 242 |
| 2026 | NEW_s2027 | +4.25 [+3.95, +4.60] | +134.7% [+121.9%, +150.1%] | +261.8% [+232.5%, +298.2%] | -19.4% [-20.4%, -18.2%] | -4.58% [-4.92%, -4.19%] | +2.1 [+1.0, +3.0] | +322 [+313, +331] | 0.0479 | 1453 / 242 |

### Cash decomposition, R-main: bps per anchor per unit target gross, 32-path mean (identity g = price − funding paid − fee − unknown, max err printed)

| segment | arm | g | price & trading | funding paid | fee | unknown excluded | identity max err |
|---|---|---|---|---|---|---|---|
| 2023H2 | OLD | -0.738 | -0.172 | +0.278 | +0.288 | +0.000 | 6.3e-11 |
| 2023H2 | OLD_HOLD | -0.208 | +0.146 | +0.136 | +0.218 | +0.000 | 7.9e-11 |
| 2023H2 | NEW_s42 | -0.202 | -0.053 | +0.014 | +0.135 | +0.000 | 6.6e-11 |
| 2023H2 | NEW_s2027 | -0.179 | +0.017 | +0.059 | +0.138 | +0.000 | 4.9e-11 |
| 2024 | OLD | +0.425 | +0.869 | +0.227 | +0.217 | +0.000 | 8.5e-11 |
| 2024 | OLD_HOLD | +0.567 | +0.925 | +0.194 | +0.164 | +0.000 | 9.2e-11 |
| 2024 | NEW_s42 | +0.829 | +1.146 | +0.155 | +0.162 | +0.000 | 1.1e-10 |
| 2024 | NEW_s2027 | +0.768 | +1.059 | +0.158 | +0.134 | +0.000 | 1.1e-10 |
| 2025 | OLD | +0.130 | +1.110 | +0.735 | +0.246 | +0.000 | 1.1e-10 |
| 2025 | OLD_HOLD | +0.236 | +0.816 | +0.436 | +0.144 | +0.000 | 1.0e-10 |
| 2025 | NEW_s42 | +1.232 | +1.784 | +0.420 | +0.131 | +0.000 | 1.2e-10 |
| 2025 | NEW_s2027 | +1.022 | +1.531 | +0.393 | +0.116 | -0.000 | 1.2e-10 |
| pre2026 | OLD | +0.073 | +0.755 | +0.440 | +0.243 | +0.000 | 1.1e-10 |
| pre2026 | OLD_HOLD | +0.279 | +0.724 | +0.278 | +0.167 | +0.000 | 1.0e-10 |
| pre2026 | NEW_s42 | +0.782 | +1.158 | +0.232 | +0.144 | +0.000 | 1.2e-10 |
| pre2026 | NEW_s2027 | +0.678 | +1.037 | +0.232 | +0.128 | -0.000 | 1.2e-10 |
| 2026 | OLD | +2.988 | +4.179 | +1.069 | +0.123 | +0.000 | 1.2e-10 |
| 2026 | OLD_HOLD | +2.983 | +4.174 | +1.068 | +0.123 | +0.000 | 1.1e-10 |
| 2026 | NEW_s42 | +3.101 | +4.326 | +1.099 | +0.125 | +0.000 | 1.3e-10 |
| 2026 | NEW_s2027 | +3.047 | +4.269 | +1.099 | +0.123 | +0.000 | 1.3e-10 |

### Certified MEAN PATH (descriptive; the published headline convention)

| segment | arm | Sharpe | total return | maxDD 5m |
|---|---|---|---|---|
| 2023H2 | OLD | -1.82 | -15.8% | -22.0% |
| 2023H2 | OLD_HOLD | -0.67 | -5.3% | -12.6% |
| 2023H2 | NEW_s42 | -0.79 | -5.0% | -14.8% |
| 2023H2 | NEW_s2027 | -0.90 | -4.4% | -15.0% |
| 2024 | OLD | +0.96 | +18.3% | -26.9% |
| 2024 | OLD_HOLD | +1.21 | +25.8% | -24.6% |
| 2024 | NEW_s42 | +1.86 | +41.0% | -13.7% |
| 2024 | NEW_s2027 | +1.74 | +37.4% | -12.9% |
| 2025 | OLD | +0.21 | +2.2% | -27.6% |
| 2025 | OLD_HOLD | +0.42 | +7.6% | -19.5% |
| 2025 | NEW_s42 | +1.90 | +65.6% | -11.9% |
| 2025 | NEW_s2027 | +1.66 | +51.3% | -11.8% |
| pre2026 | OLD | +0.12 | +1.7% | -38.4% |
| pre2026 | OLD_HOLD | +0.54 | +28.3% | -28.9% |
| pre2026 | NEW_s42 | +1.45 | +121.9% | -18.1% |
| pre2026 | NEW_s2027 | +1.29 | +98.7% | -17.5% |
| 2026 | OLD | +4.18 | +130.6% | -18.1% |
| 2026 | OLD_HOLD | +4.18 | +130.3% | -18.1% |
| 2026 | NEW_s42 | +4.28 | +138.3% | -19.7% |
| 2026 | NEW_s2027 | +4.28 | +134.7% | -19.4% |

### Cost cells and the literal (fixed-380) reading: path-mean Sharpe / total return (report only)

| cell | segment | OLD | OLD_HOLD | NEW_s42 | NEW_s2027 |
|---|---|---|---|---|---|
| fee_x1.25 | pre2026 | S +0.00 / -4.6% | S +0.45 / +22.6% | S +1.37 / +113.0% | S +1.23 / +92.2% |
| fee_x1.25 | 2026 | S +4.10 / +128.2% | S +4.11 / +128.3% | S +4.21 / +136.5% | S +4.21 / +133.2% |
| slip_x1.5 | pre2026 | S -0.08 / -8.8% | S +0.39 / +18.8% | S +1.32 / +107.0% | S +1.18 / +87.2% |
| slip_x1.5 | 2026 | S +4.07 / +126.8% | S +4.08 / +126.9% | S +4.17 / +134.5% | S +4.19 / +131.9% |
| fill_x0.9 | pre2026 | S +0.12 / +2.2% | S +0.51 / +27.1% | S +1.43 / +120.0% | S +1.28 / +98.9% |
| fill_x0.9 | 2026 | S +4.13 / +129.8% | S +4.13 / +129.6% | S +4.28 / +139.7% | S +4.26 / +135.3% |
| lit | pre2026 | S -0.34 / -23.5% | not run (by design) | S +0.89 / +40.6% | S +0.83 / +34.6% |
| lit | 2026 | S +4.01 / +123.7% | not run (by design) | S +4.27 / +139.6% | S +4.27 / +136.0% |

### 2026-08-31T04Z → 2026-09-18T20Z (DESCRIBE ONLY; OLD = certified OBJB_A0X run)

| arm | total return | Sharpe (full days) | maxDD 5m | worst day | g | day stops | d̄ vs OLD (point, bps/day) |
|---|---|---|---|---|---|---|---|
| OLD | -5.4% | -2.43 | -10.8% | -3.75% | -2.295 | 1.00 | — |
| NEW_s42 | -5.9% | -2.89 | -11.2% | -3.73% | -2.554 | 1.00 | -3.63 (18 d) |
| NEW_s2027 | -5.6% | -2.66 | -10.9% | -3.73% | -2.413 | 1.00 | -2.06 (18 d) |

Control, NEW X run vs NEW main run on shared anchors ≤ 2026-08-30T20Z: {"NEW_s42": {"shared_anchors": 9138, "max_abs_diff_window_return": 0.0, "bitwise_equal": true}, "NEW_s2027": {"shared_anchors": 9138, "max_abs_diff_window_return": 0.0, "bitwise_equal": true}}

### R-P (§4-4 −25 % from the base's starting equity, permanent halt) and R-P2 (day stop + named resume delay), FULL_RECIPE base 2023-06-30T04Z — report only

| arm | R-P halted paths | R-P median halt anchor | R-P end return (P-halt / no-halt) | R-P2 H=12h W_ENTRY: paths hit −25 % | median −25 % anchor | end return P2 / no halt |
|---|---|---|---|---|---|---|
| OLD | 32/32 | 2024-03-18T16:00:00Z | -25.3% / +134.6% | 32/32 | 2024-03-18T16:00:00Z | -25.3% / +134.6% (n_eff 32) |
| OLD_HOLD | 10/32 | 2024-08-05T08:00:00Z | +128.9% / +195.4% | 19/32 | 2024-07-21T20:00:00Z | +65.7% / +195.4% (n_eff 32) |
| NEW_s42 | 0/32 | none | +428.8% / +428.8% | 0/32 | None | +425.0% / +428.8% (n_eff 32) |
| NEW_s2027 | 0/32 | none | +366.1% / +366.1% | 0/32 | None | +367.7% / +366.1% (n_eff 32) |


## §10 偏离预注册、执行口径、缺测(UNAVAILABLE)与事故

**判据:零改动。** 窗口、读数、路径、块长、B、随机数种子都与预注册 / 修订 1 一致。没有去掉任何路径,也没有换任何读数。

执行口径:预注册没写明的地方,在任何数字之前落盘为 `receipts/OVN_OPERATIONALISATION.json`,不算偏离,逐条列出:
- 日序列只用**完整 UTC 日**(一天 6 个锚都在段内)。判据窗首日 2023-06-30 只有 5 个锚,不计入日序列,但它的 5 个窗计入总收益、回撤和事件数。把这一天也算进去重算 G1,四个比较的结论都不变(见 G1 表下方的敏感性)。
- 「32 路径均值」= 32 条路径各自指标的算术均值;「[2.5%, 97.5%]」= 这 32 个值的分位数。G3 用的就是这个路径均值。认证的「均值路径」口径作为描述另列,两种口径相差最多 0.033 Sharpe(NEW_s42 的 2026 段)、0.48 pp 回撤。
- 97.5% 双侧区间 = 自举分布的 1.25 / 98.75 分位;块长 30 日与 5 日各自用一个新的 `default_rng([20260923, 1])` 生成器;非循环移动块,做法与 `bt_tables.mbb_indices` 相同。
- G4 = 在同一成本格下 NEW_c 对 OLD_c(或 OLD_HOLD_c)的 G1 点估计,与基准格同号且严格非零。

与预注册文字的出入(具名):
1. **输出位置**:运行输出放在 `/dev/shm/ovn_2026-09-23`,不在 `/workspace`。原因是 `/workspace` 卷已到配额(下面事故 1)。这是位置,不是设置;四个臂的 `pod_root` 相同。
2. **NEW 轴之前的 1,110 个锚**(2022-06-30T00Z → 2022-12-31T20Z)写成持有、空行,即空仓。这与 NEW 构建器自己「从现金起步」的定义一致;这些锚都在判据窗之前。
3. **延伸段的 OLD** 用的是认证的 `OBJB_A0X_scaled` 运行(A0_ext 目标 085d8858),而不是 A0_main,因为 A0_main 目标只到 2026-08-31T00Z。NEW 的延伸运行在共享锚上与 NEW 主运行逐位相等(9,138 锚,最大差 0.0)。**OLD_HOLD 没有延伸段**,因为修订 1 没有要求改写 A0_ext 目标 —— 具名缺测。
4. **OLD_HOLD 没跑 lit 读数**:修订 1 只改 scaled 读法,lit 本来就不作判据 —— 具名缺测。
5. **R-P / R-P2** 用的是仓库里的第 7 轮认证版本(`bt_p_reading.py` a7cb9c4d、`bt_p2_reading.py` fa67ae29、`bt_agg.py` 43fe1092),不是 pod2 `devices_v3` 里更早的版本。配置由认证的 `bt_p_config_for.py` 从冻结的 A0 P / P2 配置逐字节复制,只改读哪些运行目录。它们的窗口到 2026-08-31,**包含 2026**,只作报告。
6. **统计装置在修订 1 之后改过一次**(08:1xZ,早于任何 OVN 数字),改动是加 OLD_HOLD 对照和修订后的判词规则。改前改后都先在已发布的 A0 / V4 运行上空跑,并包含恒等对照:同一臂自比得到 0.000,区间 [0, 0]。

**UNAVAILABLE**:无。统计收据 `unavailable = []`;每个比较 915 个完整日 × 32 条路径,自举 10,000 / 10,000 次抽样都有定义;g 恒等式最大误差 1.3e−10。

**事故**(全文 `logs/OVN_INCIDENTS.log`):
1. **06:03–06:05Z `/workspace` 配额用尽(EDQUOT),由我造成**:适配器测试把一个 192 MiB 的变异输入副本写到 `/workspace`,把卷的剩余配额用完,卷上所有写入失败约 2 分钟。我删掉自己的临时文件后恢复;恢复后卷上只剩约 200 MB 余量。我核过收集器(`strategy_rebuild_20260911/leverage_data`)的输出,它自 09-11 16:24 起就没再写过,所以不受影响;其他会话在这 2 分钟里有没有写入,我无法核实。**卷只剩约 200 MB 余量,这本身就是任何会话都会撞上的风险。**
2. **08:25:55–08:26Z 我的 4 个启动器进程组被外部结束**:父进程与 bash 包装一起消失,没有写出 EXIT 行;每组刚派生的那个工作进程成了孤儿,正常跑完。`memory.events` 的 `oom_kill` 没有变化,3 MB 的 bash 包装也一起消失,不符合 OOM 的特征。来源不明,不是我做的(我唯一一次 kill 是 08:26 按 OLD_HOLD 自己记录的 PGID 发出,当时该组已不存在)。当时同一 cgroup 里有 M2 代理的多个启动器,两边共享 61 GB 上限和 22 GiB 的启动门,我的 4 个启动器在事故前都停在这个门上。处理:等孤儿跑完,再用 `--resume`(按 sha 复核已有路径)以 `*_r2` 标签续跑。**OLD 的 160 个路径文件与认证运行逐字节相同**,说明续跑没有改变任何确定性结果。
3. 适配器测试第一次被 ssh 超时截断,身份披露第一次因读错 `scores.npz` 的轴(IndexError)失败。两份日志原样保留(`*_try1_*.log`)。

## §11 复跑命令

逐字抄录在 `multi_asset/exports/research/old_vs_new_2026-09-23/devices/RUN_OVN.sh`,包括两次失败尝试与续跑。Mac 端渲染:`/usr/bin/python3 devices/ovn_render.py receipts/pod2/OVN_STATS.json receipts/pod2/OVN_EXT.json receipts/pod2 receipts/OVN_TABLES_rendered.md`。

## §12 收据

| 内容 | 路径(相对 `multi_asset/exports/research/old_vs_new_2026-09-23/`) |
|---|---|
| 判据统计与判词 | `receipts/pod2/OVN_STATS.json`(sha 660ea558) |
| 渲染表(本文 §4–§9 逐字来自这里) | `receipts/OVN_TABLES_rendered.md` |
| 延伸段 | `receipts/pod2/OVN_EXT.json` |
| R-P / R-P2 | `receipts/pod2/BT_P_READING_OVN_{OLD,OLD_HOLD,NEW_s42,NEW_s2027}.json`、`BT_P2_READING_OVN_*.json`;配置在 `configs/RUN_CONFIG_P*reading_OVN_*.json` |
| 启动器收据 | `receipts/pod2/BT_LAUNCH_full_ovn_*.json`(`*_r2` 为续跑) |
| 执行口径 / 身份披露 / 配置 diff | `receipts/OVN_OPERATIONALISATION.json`、`receipts/IDENTITY_DISCLOSURE.json`(Mac 版含一段运行前补记,pod2 原件 sha aca27f0c)、`receipts/OVN_CONFIG_DIFF*.json` |
| 适配器与 OLD_HOLD | `targets/TARGETS_NEW_s{42,2027}.{npz,json}`、`targets/TARGETS_OLD_HOLD.json`(npz 1091922e 不入库,可由 TARGETS_A0_main.npz 与 `devices/ovn_old_hold.py` 逐位重建)、`receipts/OVN_ADAPTER_TEST_s42.json` |
| 装置 | `devices/`(ovn_adapter / ovn_adapter_test / ovn_make_configs / ovn_identity / ovn_old_hold / ovn_make_config_old_hold / ovn_stats / ovn_ext / ovn_render / ovn_post.sh / ovn_detach.sh / RUN_OVN.sh) |
| 路径文件 | pod2 `/dev/shm/ovn_2026-09-23/runs/`(RAM 盘,**pod 重启即丢**;可按 RUN_OVN.sh 逐位重跑,OLD 部分与 `/workspace/baseline_tables_2026-09-19/runs/OBJB_A0_*` 逐字节相同) |

## §13 追加(lead 09-23 要求):2026 与线上重叠期,只描述、不判

32 条路径均值 [2.5%, 97.5%];R-main 认证主设置;数字来自两份收据,sha 写在表头注释。

<!-- from OVN_STATS.json sha 660ea5584fee439d and OVN_EXT.json sha 2384e4799ff8cd6b -->
| 段 | 臂 | 累计收益 | Sharpe(完整 UTC 日) | 最大回撤 5m | 最差日 | 完整日数 |
|---|---|---|---|---|---|---|
| 2026-01-01→08-31(1,453 锚) | OLD | +130.6% [+117.2%, +142.7%] | +4.15 [+3.87, +4.45] | -18.2% [-19.9%, -16.6%] | -4.61% [-4.73%, -4.49%] | 242 |
| 2026-01-01→08-31(1,453 锚) | OLD_HOLD | +130.3% [+114.6%, +142.7%] | +4.15 [+3.82, +4.43] | -18.1% [-19.8%, -16.5%] | -4.61% [-4.73%, -4.48%] | 242 |
| 2026-01-01→08-31(1,453 锚) | NEW_s42 | +138.3% [+124.2%, +151.2%] | +4.25 [+4.00, +4.54] | -19.7% [-20.9%, -18.2%] | -4.81% [-5.05%, -4.40%] | 242 |
| 2026-01-01→08-31(1,453 锚) | NEW_s2027 | +134.7% [+121.9%, +150.1%] | +4.25 [+3.95, +4.60] | -19.4% [-20.4%, -18.2%] | -4.58% [-4.92%, -4.19%] | 242 |
| 2026-08-31T04Z→09-18T20Z(113 锚) | OLD | -5.4% [-6.5%, -4.3%] | -2.43 [-3.16, -1.65] | -10.8% [-12.3%, -9.8%] | -3.75% [-4.08%, -3.56%] | 18 |
| 2026-08-31T04Z→09-18T20Z(113 锚) | OLD_HOLD | **未跑(UNAVAILABLE)** | — | — | — | — |
| 2026-08-31T04Z→09-18T20Z(113 锚) | NEW_s42 | -5.9% [-7.1%, -5.2%] | -2.89 [-3.61, -2.38] | -11.2% [-12.8%, -10.2%] | -3.73% [-4.09%, -3.52%] | 18 |
| 2026-08-31T04Z→09-18T20Z(113 锚) | NEW_s2027 | -5.6% [-6.8%, -4.6%] | -2.66 [-3.49, -1.95] | -10.9% [-12.5%, -9.8%] | -3.73% [-4.09%, -3.51%] | 18 |

d̄ 点估计(NEW − 对照,bps/日,只描述):2026 段 NEW_s42 对 OLD +1.43; 2026 段 NEW_s42 对 OLD_HOLD +1.48; 2026 段 NEW_s2027 对 OLD +0.77; 2026 段 NEW_s2027 对 OLD_HOLD +0.82; 延伸段 NEW_s42 对 OLD -3.63(18 天); 延伸段 NEW_s2027 对 OLD -2.06(18 天)

须知:
- **OLD_HOLD 在延伸段没跑**,标为 UNAVAILABLE,没有用 OLD 的数字代替。OLD 的目标在两段里都没有 King 回退锚(A0_ext scaled:2026 段 1,453/1,453 是 combo,延伸段 113/113 是 combo),所以 OLD_HOLD 在这两段的目标与 OLD 完全相同,差别只可能来自 2026 之前积累下来的持仓与止损状态。2026 段实测 OLD 与 OLD_HOLD 几乎一样(+130.6% 对 +130.3%)。要补跑,需要把 A0_ext 目标同样改写,再跑 32 条路径,约 30–40 分钟。
- **延伸段只到 2026-09-18T20Z**,因为认证价格表 x0918r 只到 09-19T00Z。线上亏损窗(分析文档说的 09-16→09-22)只覆盖了一部分,**09-19→09-22 在本引擎里没有测**。
- 延伸段的 OLD 是认证 `OBJB_A0X_scaled` 运行,目标来自 A0_ext 链。NEW 的延伸运行在共享锚上与 NEW 主运行逐位相等。
- 18 个完整日的样本,只作描述。
