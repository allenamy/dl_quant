> **创建:** 2026-09-23 | **Session:** session_01MCyx6gj5EdbghE9bwjBjJv(Stage 2 执行代理, lead 派出) | **状态:** 已出数, 六个判词齐; 只报告, 不下"应否换装"的结论 | **作废条件:** 预注册 `docs/PREREG_old_vs_new_models_same_engine_2026-09-23.md`(8530d2b7f, sha 1217d786)、认证引擎(exec_sim 29679672 / bt_hist_sim31 8ae6e2a4 / 标定 fda34243 / 执行器树 409ea16)、OLD 或 NEW 目标文件、或本文装置 sha 任一改变

# RESULT: Stage 2 M2(BTC-beta 叠加对冲)在 OLD / NEW_s42 / NEW_s2027 上的读数

装置与收据: `multi_asset/exports/research/m2_btc_overlay_2026-09-23/{devices,receipts}/`; 逐字复跑命令 `devices/run_m2.sh`。背景: `docs/ANALYSIS_independent_researcher_takeover_2026-09-23.md` §4(实盘书对 BTC 日 β −0.354)。

## §0 一页结论(白话)

| 底座 | 路线 L: 把对冲写进目标文件(预注册字面; 配置 diff 只有目标路径与标签) | 路线 H: 公式不变, 对冲加在执行器 reshape 之后(**具名偏离**) |
|---|---|---|
| **OLD** | **DRIFT-DEPENDENT**(另 H2.3 FAIL) | **FAIL**(H2.2) |
| **NEW_s42** | **UNDECIDED**(只跑主设置; 见 §5.3) | **FAIL**(H2.2, H2.3) |
| **NEW_s2027** | **UNDECIDED**(只跑主设置; 见 §5.3) | **FAIL**(H2.2, H2.3) |

1. **按预注册的字面做法, 认证引擎和实盘执行器都交付不了这个对冲。** 执行器(409ea16 原码)对每个已发布目标做 re-demean(w − mean(w))再 rescale(w / Σ|w|)。所以文件里的 BTC 净多头被摊回成每名 −h/N, 执行书始终美元中性。执行层实际做的是"多 BTC、空整篮山寨"的价差, 执行书 β 反而朝负方向移动, 移动量是意图的 −13%…−47%(2022–2025)。在 OLD 上它的 Sharpe +0.167 全部来自 BTC 相对山寨的漂移: 漂移项 +1.39 ≥ Δμ +1.25 bps/日, 日收益标准差反升 14%, 回撤和最差日都变差。判词是 DRIFT-DEPENDENT。
2. **按公式本意把对冲加到执行书上(路线 H), β 确实被中和了**: H2.1 三个底座全过, 已实现日 β 为 +0.031…+0.056, 反而略微过冲。**但三个底座的 Sharpe 都下降**: ΔS −0.160 / −0.109 / −0.155, 三个成本格下符号不变。2023H2 和 2024 都变好, 2025 大幅变差(−0.69 / −0.86 / −0.83)。NEW 两颗种子的 PRE2026 回撤从 −18% 左右恶化到 −23%~−24%(即 2025 年的回撤)。OLD 的回撤由 −38.4% 缩到 −33.1%。
3. **关键背景是判据窗里本来就几乎没有可对冲的负 β。** 2023H2–2025 底座的已实现日 β: OLD +0.003, NEW_s42 −0.048, NEW_s2027 −0.029。负 β 到 2026(只报告, 选型重合年)才明显: −0.165 / −0.180 / −0.176。
4. **公式的 β_book 在执行书上系统性过冲。** β_book 按"已发布目标"计算, 但执行器会抹掉已发布目标的净空头(OLD 2025 平均净额 −3.3% gross, NEW 2026 −8%)。结果执行书的事前 β 只有文件级的一半左右: OLD 2025 文件级 −0.088、执行书 −0.038; NEW_s42 2026 文件级 −0.191、执行书 −0.100。路线 H 的已实现 β 被推成正值, 2025 年 OLD +0.148, 2026 年三个底座 +0.08 / +0.17 / +0.18。
5. **路线 H 的 Δμ 为负, 而漂移项为正 +1.4 到 +2.4 bps/日。** 按 4h 窗口 g 拆分(bps/锚/单位目标 gross), 差额分三块: ① 对冲是多 BTC, 在 2023–2025 要额外付资金费(+0.013 到 +0.017); ② BTC 换手带来额外手续费(+0.012 到 +0.019); ③ 价格项没有吃到 BTC 漂移(OLD −0.050、s42 +0.003、s2027 −0.025), 即对冲在择时上是亏的。这三块都是事后的描述, 不是判据。
6. NEW 上的路线 L: 已实现 β 几乎不动(−0.046 vs −0.048; −0.031 vs −0.029), 三段全部变差(ΔS −0.275 / −0.167), 成本格未跑 ⇒ UNDECIDED(已跑的 H2.2 / H2.3 均 FAIL)。同一条 L 通道在 OLD 上靠 BTC 相对山寨漂移赚、在 NEW 上亏 —— 它不是对冲, 是一个随底座而变号的价差暴露。
7. 2026 年(只报告)底座的负 β 与实盘 −0.354 同向。路线 H 把 β 翻成正值, 回撤降 4–5pp, Sharpe 降 0.34 到 1.2。**这一年是选型重合年, 不作判据。**

我不替 lead 选路线, 也不下换装结论。判词只由预注册 H2.1–H2.4 加我运行前冻结的操作化规则得出(§1.4)。

## §1 做了什么

### 1.1 公式(一个字没改)
在锚 A、对已发布目标 w(gross 单位):
- β_i 的样本是截至 A 已完成的最近 180 根 4h bar(以 A 为终点的那根也算已完成)。取该名 4h 对数收益对 BTCUSDT 4h 对数收益的 OLS 斜率, 带截距。有效观测 ≥120, 否则取 1.0; 截断到 [−1, 4]; BTC 自身取 1。
- β_book = Σ w_i β_i; BTCUSDT += −β_book; 其余名字不动; HOLD 锚不加。
- 价格源是认证 `price_full_raw_x0918r`(23af32bd)。
- 缺测一律不计入、不填零: 首个有限 bar 之前、末个有限 bar 之后、以及 UA bar 落在 [T_{k−1}, T_k] 闭区间。第三条与认证 UA-FREEZE-EXCLUDE 是同一条规则: 起点落在 UA bar 上时起点价是陈旧价。

输入核对(建 β 之前): OLD 表在生命期内的缺测格 24,397 个, 与原价表的补缺格 21,313 加 UA 格 3,084 **集合相等**, 两者无交集。所以排除 UA 就等于排除了全部缺测; 补缺格是官方 kline 复原出的真收益, 按有效观测计入。

### 1.2 机制发现(在任何 NAV 之前, 收据 `M2_EXEC_PATH_{OLD,NEW_s42,NEW_s2027}.json`)
认证运行器调用的是实盘执行器 409ea16 的原码 `anchor_loop.apply_withhold_and_reshape`, 顺序是 POP → RESHAPE(`RESHAPE_REDEMEAN = RESHAPE_RESCALE = True`)→ CLAMP, 每锚都做。下表是平书近似(无持仓, 不可交易名全部 POP), 用执行器原函数逐锚推一遍的结果:

| 底座 / 年 | 文件级 β_book/Σ\|w\| | 执行书 β(底座) | 执行书 β(路线 L) | 意图对冲 | 执行 β 变化 / 意图(中位) |
|---|---|---|---|---|---|
| OLD 2023 | −0.049 | −0.046 | −0.053 | +0.049 | −0.13 |
| OLD 2024 | −0.003 | +0.008 | +0.008 | +0.003 | −0.15 |
| OLD 2025 | −0.088 | −0.038 | −0.074 | +0.088 | −0.43 |
| OLD 2026 | −0.140 | −0.096 | −0.084 | +0.140 | +0.13 |
| NEW_s42 2025 | −0.094 | −0.051 | −0.087 | +0.094 | −0.45 |
| NEW_s2027 2025 | −0.114 | −0.058 | −0.102 | +0.114 | −0.45 |

执行书净额两臂都恰为 0: 路线 L 的 BTC 多头被 −h/N 摊回了。"执行 β 变化 / 意图"为负, 说明 L 反向加深了负 β。原因是整篮的平均 β̄ > 1, 空整篮对冲不了多 BTC。

### 1.3 两条路线
- **路线 L(字面, 合规)**: 用 M2 目标文件跑认证运行器 `devices_v3/bt_launch.py`, 未改动。设置为认证主设置、同 32 路径(种子 0..31)、三成本格。与底座配置的 diff 只有目标路径/sha、run 标签/arm 标签、输出根。`M2_CONFIG_DIFF_{OLD,NEW_s42,NEW_s2027}.json` 全部 PASS; 被丢弃的只有 lit run, Stage 2 用不到。它测的是"把 M2 写进目标文件会怎样", **不是公式本身**。
- **路线 H(具名偏离预注册: 交付通道不同, 公式不变)**: 目标文件就是底座原文件。在执行器 POP→RESHAPE→CLAMP 之后、plan() 之前, 给 BTC 目标加 h(A)·Gs。
  - h = −β_book/Σ|w|。β_book 取已发布目标, 即公式第 2 步; Σ|w| 等于执行器的 gross_in(OLD 全部权重都在宇宙内, 最大差 3.9e−16)。Gs 是执行器自己的 sizing gross(equity × 2.0)。
  - 其余名字的执行目标与底座**逐位相同**, 总 gross 增加 |h|·Gs。这正是公式里"其余名字不变、总 gross 相应变化"两句的执行层含义。
  - HOLD / HALT / 目标无效的锚不会进入 reshape, 所以不改对冲, 持仓保留上一锚的对冲, 与生产 HOLD 语义一致。
  - BTC 在该锚不可交易时不加对冲并计数。BTC 在调用的 untradable 或 force_flat 集合里就算不可交易: 认证引擎的逐名止损(未实现深度 ≤ −30% 连续 2 锚)及其 7 天冷却同样作用在对冲腿上。32 路径全量统计, 被跳过的锚数与占比: OLD 550–603(6.0–6.6%), NEW_s42 254–257(3.9%), NEW_s2027 122–125(2.0%)。每个已加对冲的锚上, |h| 均值分别为 0.083 / 0.114 / 0.117(gross 单位)。
  - 实现在 `m2_hook.py`: 进程内包住认证的 `bt_hist_sim31.make_sim_class`, 认证文件一字未动。配置里钉了 hook 装置 sha 和对冲表 sha; 每个路径 json 的 `diag.m2h_*` 记计数。
  - **零对冲对照**: 用同一 hook、对冲表全 0, OLD 全窗 seed 0 和 31 的路径文件与认证底座**逐位相等**(每个数组键)。红能力对照(seed 0 对 seed 1)确实不等。
  - **正控**: seed 0–3 的 PRE2026 窗口起点执行 gross/(gm·NAV), 底座 0.996, H 为 1.072–1.074。同期 |h| 均值 0.082, 说明对冲确实进了执行书。
- **NEW 的 L 只跑主设置(具名偏离, 资源原因, 在任何 NEW 数字之前已声明并提交 846be156e)**: pod2 容器 CPU 配额 13.6 核(`cpu.max 1360000/100000`), 与 Stage 1 的 20 个工作进程共享; 机制诊断已经表明 L 交付不了对冲。所以 NEW 的 L 不跑成本格, H2.4 不可算, 按判词规则记 UNDECIDED。

### 1.4 判读的操作化(冻结于 `m2_readout.py` 文档串, 提交 d9aad42fd, 先于任何 M2 NAV)
- 判据对象是 32 路径均值路径(认证主表对象), 同时报路径分布。
- 只用完整 UTC 日, 即当日 6 个锚都在窗内。与预注册 Stage 1 的"完整 UTC 日"一致; 判据窗首日 2023-06-30 只有 5 个锚, 被剔除。
  - 对账: 认证 `cell_metrics` 含该残日时, OLD PRE2026 为 +1.75% / Sharpe 0.142; 剔除后为 +0.29% / 0.116; maxDD 5m 两者都是 −38.375%。差异全部来自那一天(+1.46%)。
- **H2.1**: 均值路径日收益对 BTC 日收益做 OLS(带截距)。BTC 日收益取认证价表 [d 00Z, d+1 00Z]。
- **H2.2**: ΔS = Sharpe(M2) − Sharpe(底座); 要求 PRE2026 合并 > 0, 且 2023H2 / 2024 / 2025 中至少 2 段 > 0。
- **H2.3**: 不变差 = M2 ≥ 底座, 无容差。PRE2026 maxDD(5m)和最差日两项, 均值路径与 32 路径平均各算一次, 四项全过才过。
- **H2.4**: 三个成本格各自比 ΔS_c 与主设置 ΔS 的符号, 任一为 0 算不同号。
- **漂移项** = −gm·β̄_book·μ_BTC, 其中 β̄_book 取窗内已发布锚的 β_book/Σ|w| 平均值。
- **DRIFT-DEPENDENT** 当且仅当: H2.2 过, 且 σ_M2 ≥ σ_底座, 且 Δμ > 0, 且漂移项 ≥ Δμ。
- **判词规则**: 四条全过且非 DRIFT-DEPENDENT 为 PASS; 触发漂移规则为 DRIFT-DEPENDENT; 有判据不可算为 UNDECIDED; 其余为 FAIL, 并列出失败项。

## §2 测试判词原文

pod2(`receipts/pod2/m2_tests_real.log`, m2_tests.py 2544fd03 / m2_lib.py 93f8e760, β 文件 b66afc83):
```
GREEN T1.future_invariance_synthetic.baseline_bitwise_equal
GREEN T1.future_invariance_synthetic.control_bar_ending_at_A_changes_beta
GREEN T2.beta2_clean.baseline
GREEN T2.beta2_with_UA_garbage_excluded.baseline
GREEN T2.control_same_garbage_unmarked_misses_2
GREEN T3.nobs_119_falls_back_to_1.0
GREEN T3.nobs_120_estimated
GREEN T4.clip_slope_+5_to_+4
GREEN T4.clip_slope_-3_to_-1
GREEN T4.btc_own_beta_is_exactly_1
GREEN T5.round_trip_zero_hedge_bitwise.baseline
GREEN T5.control_tiny_hedge_detected
GREEN T6.hold_row_unchanged
GREEN T7.only_btc_changes_insert_sorted
GREEN T8.beta_book_equals_dense_dot
GREEN T9.empty_or_uncomputable_raises
GREEN T1R.2023-09-14T08:00:00Z.future_invariance_real.baseline_bitwise_equal
GREEN T1R.2023-09-14T08:00:00Z.control_bar_ending_at_A_changes_beta
GREEN T1R.2023-09-14T08:00:00Z.subset_equals_full_build_bitwise
GREEN T1R.2024-03-12T16:00:00Z.future_invariance_real.baseline_bitwise_equal
GREEN T1R.2024-03-12T16:00:00Z.control_bar_ending_at_A_changes_beta
GREEN T1R.2024-03-12T16:00:00Z.subset_equals_full_build_bitwise
GREEN T1R.2025-04-07T00:00:00Z.future_invariance_real.baseline_bitwise_equal
GREEN T1R.2025-04-07T00:00:00Z.control_bar_ending_at_A_changes_beta
GREEN T1R.2025-04-07T00:00:00Z.subset_equals_full_build_bitwise
GREEN T1R.2025-10-10T20:00:00Z.future_invariance_real.baseline_bitwise_equal
GREEN T1R.2025-10-10T20:00:00Z.control_bar_ending_at_A_changes_beta
GREEN T1R.2025-10-10T20:00:00Z.subset_equals_full_build_bitwise
M2_TESTS VERDICT=ALL GREEN tests=28 red=0 out_sha256=94e7119d16542c3494bfc2af49057baac6510881386e331d158c7504550cdd45
```
Mac(`receipts/M2_TESTS_mac.json`): `M2_TESTS VERDICT=ALL GREEN tests=16 red=0`(合成部分)。

三项指定测试的实测值:
- ① 未来扰动不变性: 扰动 A 之后的全部价格行, 并追加 A 之后的 UA 格, β **逐位不变**, 合成与认证价表 4 个锚都如此; 对照改动以 A 为终点的那根 bar, β 变化 0.013–0.149。
- ② β=2 合成序列: 误差 0; 窗内 30 根 bar 带跳变或零填平的"垃圾"并标记为 UA 时, 误差 8.9e−16(有效 150); 不标记的对照偏差 0.061。
- ③ 119 个有效观测回落 1.0; 120 个有效观测估计值为 2.0, 误差 7e−16。

目标变换器的往返测试: hedge 全为 0 时, kind/off/idx/val 连同 dtype 逐位相等。真实文件上, 认证适配器加载 M2 文件后, 非 BTC 列与底座逐位相等, BTC 列等于底座加 hedge 逐位相等, HOLD 行不加(`BUILD_*_M2.json`)。

## §3 β_book(gross 单位 = β_book/Σ|w|, 已发布锚)

| 底座 / 窗 | n | 均值 | p5 | p25 | p50 | p75 | p95 | <0 占比 |
|---|---|---|---|---|---|---|---|---|
| OLD PRE2026 | 5495 | −0.0483 | −0.2309 | −0.0965 | −0.0489 | +0.0097 | +0.0992 | 71.3% |
| OLD 2023H2 / 2024 / 2025 | 1109 / 2196 / 2190 | −0.0601 / −0.0027 / −0.0880 | | | −0.0618 / −0.0035 / −0.0813 | | | 95.2% / 51.9% / 78.5% |
| OLD 2026(只报告) | 1453 | −0.1396 | −0.2417 | −0.1904 | −0.1416 | −0.1046 | −0.0040 | 95.5% |
| NEW_s42 PRE2026 | 4352 | −0.0721 | −0.2975 | −0.1178 | −0.0470 | −0.0030 | +0.0885 | 76.2% |
| NEW_s42 2023H2 / 2024 / 2025 | 753 / 1931 / 1668 | −0.0760 / −0.0514 / −0.0944 | | | −0.0610 / −0.0378 / −0.0471 | | | 92.3% / 74.4% / 71.1% |
| NEW_s42 2026(只报告) | 1453 | −0.1915 | −0.3945 | −0.2659 | −0.1899 | −0.1189 | +0.0546 | 90.2% |
| NEW_s2027 PRE2026 | 3841 | −0.0832 | −0.3177 | −0.1308 | −0.0600 | −0.0108 | +0.0676 | 79.8% |
| NEW_s2027 2023H2 / 2024 / 2025 | 757 / 1576 / 1508 | −0.0934 / −0.0488 / −0.1140 | | | −0.0826 / −0.0356 / −0.0716 | | | 95.1% / 72.8% / 79.4% |
| NEW_s2027 2026(只报告) | 1453 | −0.1924 | −0.3961 | −0.2655 | −0.1895 | −0.1184 | +0.0474 | 90.3% |

- 回落名占已发布 |w| 的份额: 2023 年起三个底座都是 0.0000; 只有 OLD 2022(非判据窗)为 0.50, 原因是价表 2022-06-29T20Z 才开始。
- 数据局限: 死合约冻结行(如 SCUSDT、FTTUSDT)在认证价表里是有限的常数价, 不是 NaN。它们被估成 β=0, 但已发布权重在其上的份额为 0; "≥50% bar 零收益"的名合计 ≤0.04%|w|, 对 β_book 可忽略。
- 路线 L 文件级 gross 变化 Σ|w_M2|/Σ|w|: OLD 2025 1.11、2026 1.14; NEW 2026 1.19。执行器再缩回 2.0。

## §4 OLD(底座 = 认证 A0 路径; 与 Stage 1 的 OLD 逐位相同, §6)

#### OLD_L_literal — VERDICT **DRIFT-DEPENDENT** (failing: H2.3)

receipt `M2_READOUT_OLD_L.json` · device m2_readout.py 66cbfe80f573 · UTC 2026-09-23T08:48:49Z

| criterion | measured | gate | result |
|---|---|---|---|
| H2.1 realised daily beta vs BTC, PRE2026 (M2 arm) | -0.017 (base +0.003) | [−0.10, +0.10] | PASS |
| H2.2 ΔSharpe PRE2026; segments | +0.167; 2023H2 +0.022, 2024 +0.073, 2025 +0.224 (3/3 > 0) | > 0 and ≥ 2/3 | PASS |
| H2.3 maxDD 5m and worst day not worse (mean path and path average) | maxdd_mean_path -39.06% vs -38.38%; worst_day_mean_path -6.06% vs -4.62%; maxdd_path_average -39.10% vs -38.40%; worst_day_path_average -6.11% vs -4.62% | M2 ≥ base, all four | FAIL |
| H2.4 cost cells: sign of ΔSharpe unchanged | fee_x1.25 ΔS +0.175; slip_x1.5 ΔS +0.179; fill_x0.9 ΔS +0.160 | same sign as +0.167 | PASS |

**Drift / variance decomposition (PRE2026, mean paths, complete UTC days, n = 915)**

| quantity | value |
|---|---|
| μ base (daily) | +0.70 bps |
| μ M2 (daily) | +1.96 bps |
| Δμ | +1.25 bps |
| σ base (daily) | +116.03 bps |
| σ M2 (daily) | +132.43 bps |
| Δσ | +16.40 bps |
| μ BTC (daily) | +14.43 bps |
| mean β_book / Σ|w| (published anchors) | -0.0483 |
| drift term −gm·β̄_book·μ_BTC (daily) | +1.39 bps |
| drift / Δμ | +1.1100 |
| Sharpe change from the mean only | +0.2066 |
| Sharpe change from the variance only | -0.0144 |
| DRIFT-DEPENDENT rule fires | True (h22_pass=True, sd_m2_ge_sd_base=True, d_mu_pos=True, drift_ge_d_mu=True) |

**Per segment, two arms (mean path; per-path [2.5 %, 97.5 %] in brackets)**

| window | arm | days | Sharpe | total ret | CAGR | maxDD 5m | worst day | β daily vs BTC | g bps/anchor | fee bps | day stops | name stops |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| PRE2026 | base | 915 | 0.12 [-0.04, 0.24] | +0.3% | +0.1% | -38.4% [-39.8, -36.8] | -4.62% | +0.003 | +0.073 | 0.243 | 6.4 | 793 |
| PRE2026 | m2 | 915 | 0.28 [0.18, 0.40] | +10.4% | +4.0% | -39.1% [-40.6, -37.7] | -6.06% | -0.017 | +0.175 | 0.248 | 9.8 | 782 |
| 2023H2 | base | 184 | -1.82 [-2.00, -1.59] | -17.1% | -31.0% | -22.0% [-23.2, -20.8] | -3.03% | -0.093 | -0.738 | 0.288 | 0.0 | 55 |
| 2023H2 | m2 | 184 | -1.80 [-1.95, -1.63] | -16.8% | -30.5% | -21.3% [-22.5, -20.1] | -3.10% | -0.087 | -0.724 | 0.282 | 0.0 | 59 |
| 2024 | base | 366 | 0.96 [0.77, 1.06] | +18.3% | +18.2% | -26.9% [-28.3, -25.7] | -4.31% | +0.029 | +0.425 | 0.217 | 1.0 | 258 |
| 2024 | m2 | 366 | 1.03 [0.82, 1.20] | +21.4% | +21.4% | -28.9% [-30.2, -27.5] | -5.65% | +0.035 | +0.497 | 0.219 | 1.4 | 266 |
| 2025 | base | 365 | 0.21 [-0.06, 0.43] | +2.2% | +2.2% | -27.6% [-30.0, -26.3] | -4.62% | +0.001 | +0.130 | 0.246 | 5.4 | 480 |
| 2025 | m2 | 365 | 0.44 [0.32, 0.57] | +9.2% | +9.2% | -31.6% [-33.8, -30.2] | -6.06% | -0.074 | +0.307 | 0.259 | 8.3 | 458 |
| 2026_report_only | base | 242 | 4.18 [3.87, 4.45] | +129.1% | +249.1% | -18.1% [-19.9, -16.6] | -4.61% | -0.165 | +2.988 | 0.123 | 1.6 | 329 |
| 2026_report_only | m2 | 242 | 3.67 [3.41, 3.94] | +95.3% | +174.5% | -15.1% [-16.4, -13.9] | -4.11% | -0.130 | +2.408 | 0.115 | 1.6 | 312 |

**β_book in gross units (β_book / Σ|w|, published anchors)**

| window | n | mean | p5 | p25 | p50 | p75 | p95 | share < 0 |
|---|---|---|---|---|---|---|---|---|
| PRE2026 | 5495 | -0.0483 | -0.2309 | -0.0965 | -0.0489 | +0.0097 | +0.0992 | 71.3% |
| 2023H2 | 1109 | -0.0601 | -0.1162 | -0.0885 | -0.0618 | -0.0329 | -0.0010 | 95.2% |
| 2024 | 2196 | -0.0027 | -0.1229 | -0.0606 | -0.0035 | +0.0525 | +0.1241 | 51.9% |
| 2025 | 2190 | -0.0880 | -0.2819 | -0.1525 | -0.0813 | -0.0128 | +0.0899 | 78.5% |
| 2026_report_only | 1453 | -0.1396 | -0.2417 | -0.1904 | -0.1416 | -0.1046 | -0.0040 | 95.5% |

#### OLD_H_hook — VERDICT **FAIL** (failing: H2.2)

receipt `M2_READOUT_OLD_H.json` · device m2_readout.py 66cbfe80f573 · UTC 2026-09-23T08:37:20Z

| criterion | measured | gate | result |
|---|---|---|---|
| H2.1 realised daily beta vs BTC, PRE2026 (M2 arm) | +0.056 (base +0.003) | [−0.10, +0.10] | PASS |
| H2.2 ΔSharpe PRE2026; segments | -0.160; 2023H2 +0.326, 2024 +0.308, 2025 -0.688 (2/3 > 0) | > 0 and ≥ 2/3 | FAIL |
| H2.3 maxDD 5m and worst day not worse (mean path and path average) | maxdd_mean_path -33.05% vs -38.38%; worst_day_mean_path -4.18% vs -4.62%; maxdd_path_average -33.08% vs -38.40%; worst_day_path_average -4.18% vs -4.62% | M2 ≥ base, all four | PASS |
| H2.4 cost cells: sign of ΔSharpe unchanged | fee_x1.25 ΔS -0.186; slip_x1.5 ΔS -0.197; fill_x0.9 ΔS -0.163 | same sign as -0.160 | PASS |

**Drift / variance decomposition (PRE2026, mean paths, complete UTC days, n = 915)**

| quantity | value |
|---|---|
| μ base (daily) | +0.70 bps |
| μ M2 (daily) | -0.26 bps |
| Δμ | -0.97 bps |
| σ base (daily) | +116.03 bps |
| σ M2 (daily) | +114.44 bps |
| Δσ | -1.59 bps |
| μ BTC (daily) | +14.43 bps |
| mean β_book / Σ|w| (published anchors) | -0.0483 |
| drift term −gm·β̄_book·μ_BTC (daily) | +1.39 bps |
| drift / Δμ | -1.4412 |
| Sharpe change from the mean only | -0.1591 |
| Sharpe change from the variance only | +0.0016 |
| DRIFT-DEPENDENT rule fires | False (h22_pass=False, sd_m2_ge_sd_base=False, d_mu_pos=False, drift_ge_d_mu=True) |

**Per segment, two arms (mean path; per-path [2.5 %, 97.5 %] in brackets)**

| window | arm | days | Sharpe | total ret | CAGR | maxDD 5m | worst day | β daily vs BTC | g bps/anchor | fee bps | day stops | name stops |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| PRE2026 | base | 915 | 0.12 [-0.04, 0.24] | +0.3% | +0.1% | -38.4% [-39.8, -36.8] | -4.62% | +0.003 | +0.073 | 0.243 | 6.4 | 793 |
| PRE2026 | m2 | 915 | -0.04 [-0.15, 0.11] | -8.0% | -3.3% | -33.1% [-34.6, -31.4] | -4.18% | +0.056 | -0.009 | 0.262 | 3.8 | 851 |
| 2023H2 | base | 184 | -1.82 [-2.00, -1.59] | -17.1% | -31.0% | -22.0% [-23.2, -20.8] | -3.03% | -0.093 | -0.738 | 0.288 | 0.0 | 55 |
| 2023H2 | m2 | 184 | -1.50 [-1.69, -1.28] | -14.1% | -26.0% | -19.3% [-20.6, -17.7] | -2.74% | +0.039 | -0.582 | 0.300 | 0.0 | 54 |
| 2024 | base | 366 | 0.96 [0.77, 1.06] | +18.3% | +18.2% | -26.9% [-28.3, -25.7] | -4.31% | +0.029 | +0.425 | 0.217 | 1.0 | 258 |
| 2024 | m2 | 366 | 1.27 [1.00, 1.45] | +24.9% | +24.8% | -23.5% [-24.8, -22.1] | -2.96% | +0.002 | +0.547 | 0.231 | 0.0 | 308 |
| 2025 | base | 365 | 0.21 [-0.06, 0.43] | +2.2% | +2.2% | -27.6% [-30.0, -26.3] | -4.62% | +0.001 | +0.130 | 0.246 | 5.4 | 480 |
| 2025 | m2 | 365 | -0.47 [-0.64, -0.27] | -14.3% | -14.3% | -28.6% [-30.8, -26.4] | -4.18% | +0.148 | -0.277 | 0.273 | 3.8 | 488 |
| 2026_report_only | base | 242 | 4.18 [3.87, 4.45] | +129.1% | +249.1% | -18.1% [-19.9, -16.6] | -4.61% | -0.165 | +2.988 | 0.123 | 1.6 | 329 |
| 2026_report_only | m2 | 242 | 3.84 [3.51, 4.17] | +112.9% | +212.6% | -13.5% [-15.1, -11.9] | -4.90% | +0.084 | +2.731 | 0.141 | 2.9 | 335 |

**β_book in gross units (β_book / Σ|w|, published anchors)**

| window | n | mean | p5 | p25 | p50 | p75 | p95 | share < 0 |
|---|---|---|---|---|---|---|---|---|
| PRE2026 | 5495 | -0.0483 | -0.2309 | -0.0965 | -0.0489 | +0.0097 | +0.0992 | 71.3% |
| 2023H2 | 1109 | -0.0601 | -0.1162 | -0.0885 | -0.0618 | -0.0329 | -0.0010 | 95.2% |
| 2024 | 2196 | -0.0027 | -0.1229 | -0.0606 | -0.0035 | +0.0525 | +0.1241 | 51.9% |
| 2025 | 2190 | -0.0880 | -0.2819 | -0.1525 | -0.0813 | -0.0128 | +0.0899 | 78.5% |
| 2026_report_only | 1453 | -0.1396 | -0.2417 | -0.1904 | -0.1416 | -0.1046 | -0.0040 | 95.5% |

## §5 NEW(底座 = Stage 1 的 NEW 路径 `/dev/shm/ovn_2026-09-23/runs/OVN_NEW_*`)

### 5.1 / 5.2 路线 H

#### NEW_s42_H_hook — VERDICT **FAIL** (failing: H2.2, H2.3)

receipt `M2_READOUT_NEW_s42_H.json` · device m2_readout.py 66cbfe80f573 · UTC 2026-09-23T08:39:49Z

| criterion | measured | gate | result |
|---|---|---|---|
| H2.1 realised daily beta vs BTC, PRE2026 (M2 arm) | +0.031 (base -0.048) | [−0.10, +0.10] | PASS |
| H2.2 ΔSharpe PRE2026; segments | -0.109; 2023H2 +0.522, 2024 +0.855, 2025 -0.863 (2/3 > 0) | > 0 and ≥ 2/3 | FAIL |
| H2.3 maxDD 5m and worst day not worse (mean path and path average) | maxdd_mean_path -23.77% vs -18.09%; worst_day_mean_path -6.33% vs -4.73%; maxdd_path_average -24.09% vs -18.11%; worst_day_path_average -6.33% vs -4.78% | M2 ≥ base, all four | FAIL |
| H2.4 cost cells: sign of ΔSharpe unchanged | fee_x1.25 ΔS -0.114; slip_x1.5 ΔS -0.112; fill_x0.9 ΔS -0.115 | same sign as -0.109 | PASS |

**Drift / variance decomposition (PRE2026, mean paths, complete UTC days, n = 915)**

| quantity | value |
|---|---|
| μ base (daily) | +9.21 bps |
| μ M2 (daily) | +8.91 bps |
| Δμ | -0.30 bps |
| σ base (daily) | +121.31 bps |
| σ M2 (daily) | +126.84 bps |
| Δσ | +5.53 bps |
| μ BTC (daily) | +14.43 bps |
| mean β_book / Σ|w| (published anchors) | -0.0721 |
| drift term −gm·β̄_book·μ_BTC (daily) | +2.08 bps |
| drift / Δμ | -6.8581 |
| Sharpe change from the mean only | -0.0478 |
| Sharpe change from the variance only | -0.0632 |
| DRIFT-DEPENDENT rule fires | False (h22_pass=False, sd_m2_ge_sd_base=True, d_mu_pos=False, drift_ge_d_mu=True) |

**Per segment, two arms (mean path; per-path [2.5 %, 97.5 %] in brackets)**

| window | arm | days | Sharpe | total ret | CAGR | maxDD 5m | worst day | β daily vs BTC | g bps/anchor | fee bps | day stops | name stops |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| PRE2026 | base | 915 | 1.45 [1.35, 1.55] | +117.2% | +36.3% | -18.1% [-20.3, -15.8] | -4.73% | -0.048 | +0.782 | 0.144 | 3.9 | 1075 |
| PRE2026 | m2 | 915 | 1.34 [1.25, 1.43] | +109.9% | +34.4% | -23.8% [-26.0, -22.8] | -6.33% | +0.031 | +0.755 | 0.159 | 5.8 | 996 |
| 2023H2 | base | 184 | -0.79 [-0.99, -0.49] | -7.0% | -13.3% | -14.8% [-16.1, -13.1] | -3.08% | -0.059 | -0.202 | 0.135 | 0.3 | 75 |
| 2023H2 | m2 | 184 | -0.27 [-0.47, -0.09] | -2.9% | -5.7% | -12.9% [-14.0, -12.1] | -2.61% | +0.083 | -0.010 | 0.139 | 0.0 | 77 |
| 2024 | base | 366 | 1.86 [1.67, 2.00] | +41.0% | +40.9% | -13.7% [-14.9, -12.4] | -3.54% | -0.045 | +0.829 | 0.162 | 0.2 | 357 |
| 2024 | m2 | 366 | 2.71 [2.56, 2.88] | +64.6% | +64.4% | -13.1% [-14.0, -12.1] | -3.08% | +0.029 | +1.184 | 0.171 | 0.0 | 366 |
| 2025 | base | 365 | 1.90 [1.69, 2.05] | +65.6% | +65.6% | -11.9% [-13.2, -11.8] | -4.73% | -0.046 | +1.232 | 0.131 | 3.3 | 644 |
| 2025 | m2 | 365 | 1.03 [0.84, 1.18] | +31.4% | +31.4% | -23.8% [-26.0, -22.8] | -6.33% | +0.012 | +0.712 | 0.156 | 5.8 | 552 |
| 2026_report_only | base | 242 | 4.28 [4.00, 4.54] | +136.9% | +267.2% | -19.7% [-20.9, -18.2] | -4.54% | -0.180 | +3.101 | 0.125 | 2.6 | 320 |
| 2026_report_only | m2 | 242 | 3.19 [2.89, 3.46] | +93.2% | +170.1% | -15.6% [-17.2, -14.3] | -4.96% | +0.173 | +2.403 | 0.141 | 2.9 | 329 |

**β_book in gross units (β_book / Σ|w|, published anchors)**

| window | n | mean | p5 | p25 | p50 | p75 | p95 | share < 0 |
|---|---|---|---|---|---|---|---|---|
| PRE2026 | 4352 | -0.0721 | -0.2975 | -0.1178 | -0.0470 | -0.0030 | +0.0885 | 76.2% |
| 2023H2 | 753 | -0.0760 | -0.1950 | -0.1161 | -0.0610 | -0.0301 | +0.0148 | 92.3% |
| 2024 | 1931 | -0.0514 | -0.1935 | -0.0970 | -0.0378 | +0.0014 | +0.0524 | 74.4% |
| 2025 | 1668 | -0.0944 | -0.4760 | -0.2058 | -0.0471 | +0.0134 | +0.1222 | 71.1% |
| 2026_report_only | 1453 | -0.1915 | -0.3945 | -0.2659 | -0.1899 | -0.1189 | +0.0546 | 90.2% |

#### NEW_s2027_H_hook — VERDICT **FAIL** (failing: H2.2, H2.3)

receipt `M2_READOUT_NEW_s2027_H.json` · device m2_readout.py 66cbfe80f573 · UTC 2026-09-23T08:33:05Z

| criterion | measured | gate | result |
|---|---|---|---|
| H2.1 realised daily beta vs BTC, PRE2026 (M2 arm) | +0.051 (base -0.029) | [−0.10, +0.10] | PASS |
| H2.2 ΔSharpe PRE2026; segments | -0.155; 2023H2 +0.421, 2024 +0.680, 2025 -0.829 (2/3 > 0) | > 0 and ≥ 2/3 | FAIL |
| H2.3 maxDD 5m and worst day not worse (mean path and path average) | maxdd_mean_path -22.90% vs -17.48%; worst_day_mean_path -6.11% vs -4.43%; maxdd_path_average -23.47% vs -17.61%; worst_day_path_average -6.11% vs -4.49% | M2 ≥ base, all four | FAIL |
| H2.4 cost cells: sign of ΔSharpe unchanged | fee_x1.25 ΔS -0.163; slip_x1.5 ΔS -0.163; fill_x0.9 ΔS -0.156 | same sign as -0.155 | PASS |

**Drift / variance decomposition (PRE2026, mean paths, complete UTC days, n = 915)**

| quantity | value |
|---|---|
| μ base (daily) | +7.85 bps |
| μ M2 (daily) | +7.21 bps |
| Δμ | -0.64 bps |
| σ base (daily) | +115.99 bps |
| σ M2 (daily) | +121.00 bps |
| Δσ | +5.01 bps |
| μ BTC (daily) | +14.43 bps |
| mean β_book / Σ|w| (published anchors) | -0.0832 |
| drift term −gm·β̄_book·μ_BTC (daily) | +2.40 bps |
| drift / Δμ | -3.7432 |
| Sharpe change from the mean only | -0.1056 |
| Sharpe change from the variance only | -0.0535 |
| DRIFT-DEPENDENT rule fires | False (h22_pass=False, sd_m2_ge_sd_base=True, d_mu_pos=False, drift_ge_d_mu=True) |

**Per segment, two arms (mean path; per-path [2.5 %, 97.5 %] in brackets)**

| window | arm | days | Sharpe | total ret | CAGR | maxDD 5m | worst day | β daily vs BTC | g bps/anchor | fee bps | day stops | name stops |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| PRE2026 | base | 915 | 1.29 [1.21, 1.39] | +92.8% | +29.9% | -17.5% [-19.5, -15.8] | -4.43% | -0.029 | +0.678 | 0.128 | 4.6 | 1083 |
| PRE2026 | m2 | 915 | 1.14 [1.03, 1.26] | +80.9% | +26.7% | -22.9% [-25.8, -22.2] | -6.11% | +0.051 | +0.623 | 0.140 | 6.1 | 1046 |
| 2023H2 | base | 184 | -0.90 [-1.12, -0.59] | -7.2% | -13.8% | -15.0% [-16.0, -14.0] | -4.05% | -0.043 | -0.179 | 0.138 | 1.0 | 87 |
| 2023H2 | m2 | 184 | -0.48 [-0.81, -0.20] | -4.5% | -8.7% | -14.3% [-16.6, -13.2] | -3.58% | +0.108 | -0.046 | 0.144 | 0.8 | 89 |
| 2024 | base | 366 | 1.74 [1.57, 1.91] | +37.4% | +37.3% | -12.9% [-14.2, -11.7] | -3.68% | -0.043 | +0.768 | 0.134 | 0.4 | 471 |
| 2024 | m2 | 366 | 2.42 [2.28, 2.54] | +55.1% | +54.9% | -11.2% [-12.1, -10.5] | -3.06% | +0.023 | +1.046 | 0.141 | 0.0 | 490 |
| 2025 | base | 365 | 1.66 [1.47, 1.86] | +51.3% | +51.3% | -11.8% [-12.9, -11.5] | -4.43% | -0.000 | +1.022 | 0.116 | 3.2 | 525 |
| 2025 | m2 | 365 | 0.83 [0.62, 1.05] | +22.1% | +22.1% | -22.9% [-25.8, -22.2] | -6.11% | +0.071 | +0.537 | 0.138 | 5.3 | 467 |
| 2026_report_only | base | 242 | 4.28 [3.95, 4.60] | +133.4% | +259.1% | -19.4% [-20.4, -18.2] | -4.52% | -0.176 | +3.047 | 0.123 | 2.1 | 322 |
| 2026_report_only | m2 | 242 | 3.08 [2.80, 3.34] | +87.3% | +157.6% | -15.2% [-16.5, -14.0] | -4.85% | +0.182 | +2.292 | 0.141 | 2.8 | 331 |

**β_book in gross units (β_book / Σ|w|, published anchors)**

| window | n | mean | p5 | p25 | p50 | p75 | p95 | share < 0 |
|---|---|---|---|---|---|---|---|---|
| PRE2026 | 3841 | -0.0832 | -0.3177 | -0.1308 | -0.0600 | -0.0108 | +0.0676 | 79.8% |
| 2023H2 | 757 | -0.0934 | -0.2117 | -0.1362 | -0.0826 | -0.0457 | -0.0011 | 95.1% |
| 2024 | 1576 | -0.0488 | -0.1957 | -0.0879 | -0.0356 | +0.0030 | +0.0532 | 72.8% |
| 2025 | 1508 | -0.1140 | -0.4602 | -0.2030 | -0.0716 | -0.0141 | +0.1092 | 79.4% |
| 2026_report_only | 1453 | -0.1924 | -0.3961 | -0.2655 | -0.1895 | -0.1184 | +0.0474 | 90.3% |

### 5.3 路线 L(只跑主设置, 成本格未跑 ⇒ UNDECIDED)

NEW 上路线 L 的已实现 β 几乎不动(s42 −0.046 vs 底座 −0.048; s2027 −0.031 vs −0.029): 执行器把文件里的 BTC 净多摊回整篮, 但与 OLD 不同, 这条「多 BTC 空整篮」价差在 NEW 上三段全部亏(ΔS −0.275 / −0.167, 0/3 段 > 0), 方差上升(σ +5~+8 bps/日)。H2.4 未跑, 按规则判 UNDECIDED; 已跑的 H2.2 / H2.3 均 FAIL。

#### NEW_s42_L_literal_main_only — VERDICT **UNDECIDED** (failing: H2.2, H2.3, H2.4)

receipt `M2_READOUT_NEW_s42_L.json` · device m2_readout.py 66cbfe80f573 · UTC 2026-09-23T09:02:48Z

| criterion | measured | gate | result |
|---|---|---|---|
| H2.1 realised daily beta vs BTC, PRE2026 (M2 arm) | -0.046 (base -0.048) | [−0.10, +0.10] | PASS |
| H2.2 ΔSharpe PRE2026; segments | -0.275; 2023H2 -0.347, 2024 -0.326, 2025 -0.233 (0/3 > 0) | > 0 and ≥ 2/3 | FAIL |
| H2.3 maxDD 5m and worst day not worse (mean path and path average) | maxdd_mean_path -20.78% vs -18.09%; worst_day_mean_path -6.38% vs -4.73%; maxdd_path_average -20.80% vs -18.11%; worst_day_path_average -6.38% vs -4.78% | M2 ≥ base, all four | FAIL |
| H2.4 cost cells: sign of ΔSharpe unchanged |  | same sign as -0.275 | FAIL |

**Drift / variance decomposition (PRE2026, mean paths, complete UTC days, n = 915)**

| quantity | value |
|---|---|
| μ base (daily) | +9.21 bps |
| μ M2 (daily) | +7.92 bps |
| Δμ | -1.30 bps |
| σ base (daily) | +121.31 bps |
| σ M2 (daily) | +128.65 bps |
| Δσ | +7.34 bps |
| μ BTC (daily) | +14.43 bps |
| mean β_book / Σ|w| (published anchors) | -0.0721 |
| drift term −gm·β̄_book·μ_BTC (daily) | +2.08 bps |
| drift / Δμ | -1.6042 |
| Sharpe change from the mean only | -0.2044 |
| Sharpe change from the variance only | -0.0827 |
| DRIFT-DEPENDENT rule fires | False (h22_pass=False, sd_m2_ge_sd_base=True, d_mu_pos=False, drift_ge_d_mu=True) |

**Per segment, two arms (mean path; per-path [2.5 %, 97.5 %] in brackets)**

| window | arm | days | Sharpe | total ret | CAGR | maxDD 5m | worst day | β daily vs BTC | g bps/anchor | fee bps | day stops | name stops |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| PRE2026 | base | 915 | 1.45 [1.35, 1.55] | +117.2% | +36.3% | -18.1% [-20.3, -15.8] | -4.73% | -0.048 | +0.782 | 0.144 | 3.9 | 1075 |
| PRE2026 | m2 | 915 | 1.18 [1.09, 1.27] | +91.3% | +29.5% | -20.8% [-22.4, -18.9] | -6.38% | -0.046 | +0.676 | 0.147 | 6.1 | 1046 |
| 2023H2 | base | 184 | -0.79 [-0.99, -0.49] | -7.0% | -13.3% | -14.8% [-16.1, -13.1] | -3.08% | -0.059 | -0.202 | 0.135 | 0.3 | 75 |
| 2023H2 | m2 | 184 | -1.14 [-1.27, -0.92] | -10.2% | -19.3% | -17.9% [-18.9, -17.0] | -3.05% | -0.058 | -0.362 | 0.132 | 0.0 | 78 |
| 2024 | base | 366 | 1.86 [1.67, 2.00] | +41.0% | +40.9% | -13.7% [-14.9, -12.4] | -3.54% | -0.045 | +0.829 | 0.162 | 0.2 | 357 |
| 2024 | m2 | 366 | 1.53 [1.41, 1.69] | +34.4% | +34.3% | -14.6% [-15.3, -13.9] | -4.69% | -0.037 | +0.729 | 0.163 | 1.0 | 335 |
| 2025 | base | 365 | 1.90 [1.69, 2.05] | +65.6% | +65.6% | -11.9% [-13.2, -11.8] | -4.73% | -0.046 | +1.232 | 0.131 | 3.3 | 644 |
| 2025 | m2 | 365 | 1.66 [1.47, 1.78] | +58.6% | +58.6% | -14.5% [-15.8, -13.8] | -6.38% | -0.055 | +1.148 | 0.139 | 5.0 | 632 |
| 2026_report_only | base | 242 | 4.28 [4.00, 4.54] | +136.9% | +267.2% | -19.7% [-20.9, -18.2] | -4.54% | -0.180 | +3.101 | 0.125 | 2.6 | 320 |
| 2026_report_only | m2 | 242 | 3.70 [3.41, 4.02] | +95.5% | +174.8% | -15.4% [-16.9, -13.8] | -4.09% | -0.133 | +2.403 | 0.110 | 1.7 | 300 |

**β_book in gross units (β_book / Σ|w|, published anchors)**

| window | n | mean | p5 | p25 | p50 | p75 | p95 | share < 0 |
|---|---|---|---|---|---|---|---|---|
| PRE2026 | 4352 | -0.0721 | -0.2975 | -0.1178 | -0.0470 | -0.0030 | +0.0885 | 76.2% |
| 2023H2 | 753 | -0.0760 | -0.1950 | -0.1161 | -0.0610 | -0.0301 | +0.0148 | 92.3% |
| 2024 | 1931 | -0.0514 | -0.1935 | -0.0970 | -0.0378 | +0.0014 | +0.0524 | 74.4% |
| 2025 | 1668 | -0.0944 | -0.4760 | -0.2058 | -0.0471 | +0.0134 | +0.1222 | 71.1% |
| 2026_report_only | 1453 | -0.1915 | -0.3945 | -0.2659 | -0.1899 | -0.1189 | +0.0546 | 90.2% |

#### NEW_s2027_L_literal_main_only — VERDICT **UNDECIDED** (failing: H2.2, H2.3, H2.4)

receipt `M2_READOUT_NEW_s2027_L.json` · device m2_readout.py 66cbfe80f573 · UTC 2026-09-23T09:02:56Z

| criterion | measured | gate | result |
|---|---|---|---|
| H2.1 realised daily beta vs BTC, PRE2026 (M2 arm) | -0.031 (base -0.029) | [−0.10, +0.10] | PASS |
| H2.2 ΔSharpe PRE2026; segments | -0.167; 2023H2 -0.274, 2024 -0.208, 2025 -0.106 (0/3 > 0) | > 0 and ≥ 2/3 | FAIL |
| H2.3 maxDD 5m and worst day not worse (mean path and path average) | maxdd_mean_path -19.65% vs -17.48%; worst_day_mean_path -6.24% vs -4.43%; maxdd_path_average -19.69% vs -17.61%; worst_day_path_average -6.24% vs -4.49% | M2 ≥ base, all four | FAIL |
| H2.4 cost cells: sign of ΔSharpe unchanged |  | same sign as -0.167 | FAIL |

**Drift / variance decomposition (PRE2026, mean paths, complete UTC days, n = 915)**

| quantity | value |
|---|---|
| μ base (daily) | +7.85 bps |
| μ M2 (daily) | +7.33 bps |
| Δμ | -0.52 bps |
| σ base (daily) | +115.99 bps |
| σ M2 (daily) | +124.35 bps |
| Δσ | +8.36 bps |
| μ BTC (daily) | +14.43 bps |
| mean β_book / Σ|w| (published anchors) | -0.0832 |
| drift term −gm·β̄_book·μ_BTC (daily) | +2.40 bps |
| drift / Δμ | -4.6296 |
| Sharpe change from the mean only | -0.0854 |
| Sharpe change from the variance only | -0.0869 |
| DRIFT-DEPENDENT rule fires | False (h22_pass=False, sd_m2_ge_sd_base=True, d_mu_pos=False, drift_ge_d_mu=True) |

**Per segment, two arms (mean path; per-path [2.5 %, 97.5 %] in brackets)**

| window | arm | days | Sharpe | total ret | CAGR | maxDD 5m | worst day | β daily vs BTC | g bps/anchor | fee bps | day stops | name stops |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| PRE2026 | base | 915 | 1.29 [1.21, 1.39] | +92.8% | +29.9% | -17.5% [-19.5, -15.8] | -4.43% | -0.029 | +0.678 | 0.128 | 4.6 | 1083 |
| PRE2026 | m2 | 915 | 1.13 [1.02, 1.22] | +82.2% | +27.0% | -19.7% [-21.2, -17.5] | -6.24% | -0.031 | +0.635 | 0.131 | 7.9 | 1044 |
| 2023H2 | base | 184 | -0.90 [-1.12, -0.59] | -7.2% | -13.8% | -15.0% [-16.0, -14.0] | -4.05% | -0.043 | -0.179 | 0.138 | 1.0 | 87 |
| 2023H2 | m2 | 184 | -1.17 [-1.41, -0.92] | -9.8% | -18.5% | -17.6% [-19.4, -16.1] | -3.92% | -0.049 | -0.308 | 0.134 | 0.9 | 87 |
| 2024 | base | 366 | 1.74 [1.57, 1.91] | +37.4% | +37.3% | -12.9% [-14.2, -11.7] | -3.68% | -0.043 | +0.768 | 0.134 | 0.4 | 471 |
| 2024 | m2 | 366 | 1.53 [1.40, 1.63] | +33.3% | +33.2% | -14.0% [-15.5, -13.0] | -4.73% | -0.033 | +0.706 | 0.136 | 1.0 | 457 |
| 2025 | base | 365 | 1.66 [1.47, 1.86] | +51.3% | +51.3% | -11.8% [-12.9, -11.5] | -4.43% | -0.000 | +1.022 | 0.116 | 3.2 | 525 |
| 2025 | m2 | 365 | 1.55 [1.39, 1.73] | +51.5% | +51.5% | -14.4% [-15.5, -14.0] | -6.24% | -0.019 | +1.042 | 0.124 | 6.0 | 500 |
| 2026_report_only | base | 242 | 4.28 [3.95, 4.60] | +133.4% | +259.1% | -19.4% [-20.4, -18.2] | -4.52% | -0.176 | +3.047 | 0.123 | 2.1 | 322 |
| 2026_report_only | m2 | 242 | 3.60 [3.35, 3.83] | +91.7% | +166.8% | -15.5% [-16.7, -14.1] | -4.13% | -0.129 | +2.336 | 0.110 | 1.6 | 303 |

**β_book in gross units (β_book / Σ|w|, published anchors)**

| window | n | mean | p5 | p25 | p50 | p75 | p95 | share < 0 |
|---|---|---|---|---|---|---|---|---|
| PRE2026 | 3841 | -0.0832 | -0.3177 | -0.1308 | -0.0600 | -0.0108 | +0.0676 | 79.8% |
| 2023H2 | 757 | -0.0934 | -0.2117 | -0.1362 | -0.0826 | -0.0457 | -0.0011 | 95.1% |
| 2024 | 1576 | -0.0488 | -0.1957 | -0.0879 | -0.0356 | +0.0030 | +0.0532 | 72.8% |
| 2025 | 1508 | -0.1140 | -0.4602 | -0.2030 | -0.0716 | -0.0141 | +0.1092 | 79.4% |
| 2026_report_only | 1453 | -0.1924 | -0.3961 | -0.2655 | -0.1895 | -0.1184 | +0.0474 | 90.3% |

## §6 对照与复现

| 对照 | 结果 | 收据 |
|---|---|---|
| Stage 1 的 OLD 路径 vs 认证 A0 路径(32 种子) | 逐位相等(每个数组键); 红能力对照不等 | `STAGE1_OLD_vs_certified_A0.json` |
| 我在 L 配置里原样附跑的 OLD 底座 vs 认证 A0(32 种子) | 逐位相等; 红能力对照不等 | `M2_BASE_CONTROL_vs_certified_A0.json` |
| 零对冲 hook vs 认证 OLD 底座(全窗 seed 0 / 31) | 逐位相等; hook 在全部 9,122 个交易锚上激活 | `M2H0_CONTROL_vs_certified_A0.json` |
| 零对冲 hook vs Stage 1 NEW 底座(全窗 seed 0) | 两颗种子 seed 0 均逐位相等(每个数组键); 红能力对照不等 —— hook 在带 HOLD 锚的 NEW 底座上同样透明 | `M2H0_CONTROL_NEW_{s42,s2027}_vs_stage1_base.json` |
| 各发射器判词 | `BT_LAUNCH VERDICT=PASS`: full_m2old(5 run × 32)、full_m2h(4×32)、full_m2h_new_s42(4×32)、full_m2h_new_s2027(4×32)、smoke_new_s42_lit_main 与 smoke_new_s2027_lit_main(各 1 run × 32, 全窗)、smoke_m2h0_ctrl(1×2)、smoke_m2h0_new_s42 / s2027(各 1×1); 全部 rc 0, audits_clean OK | pod2 `/dev/shm/m2_btc_overlay_2026-09-23/receipts/BT_LAUNCH_*.json` |
| 读数装置自检(底座 vs 自身) | 全部 Δ=0; H2.2 / H2.4 因 0 不 > 0 判 FAIL, 符合预期 | `M2_READOUT_SELFTEST.json` |

## §7 偏离预注册与局限(逐条具名)

1. **路线 H 是偏离。** 交付通道从目标文件改成执行器层叠加腿, 公式与判据未改。之所以需要它, 是 §1.2 的执行器 re-demean。若要在生产中交付 M2, 需要改执行器: 加一条不经 reshape 的叠加腿。这属于书行为改动, 按项目规则需要预注册加用户裁定。
2. **NEW 的路线 L 只跑主设置**(资源原因, 数字之前已声明)。因此 H2.4 不可算, 判词为 UNDECIDED。
3. **输出根改为 `/dev/shm/m2_btc_overlay_2026-09-23`。** pod2 `/workspace` 在 06:04Z 触到磁盘配额(20 MB 写入失败); Stage 1 也同样迁到了 `/dev/shm/ovn_2026-09-23`。这只是配置里的输出路径改动。另有两点影响共享机器: `/dev/shm` 计入 61 GB cgroup 内存, 我的路径文件约 7 GB 仍在那里; `/dev/shm` 是 noexec, 我的第一版链脚本因此没启动, 已改为经 bash 执行(`run_m2.sh` 有记录)。**`/workspace` 配额满是全机问题, 需要 lead 处理。**
4. **β_book 按已发布目标计算(公式原文)**, 执行书因 re-demean 与之不同, 路线 H 因此过冲(§0 第 4 点)。我没有改成"按执行书算", 那会改动公式。
5. **路线 H 的对冲腿受认证逐名止损约束**, 被跳过的锚占比 OLD 6.0–6.6%、NEW 2.0–3.9%。这是引擎行为, 不是我选的参数。
6. **漂移项只用已发布锚的 β_book。** NEW 有 HOLD 锚, 路线 H 在 HOLD 锚上持有上一锚的对冲, 漂移项对此是近似。
7. **路线 L 的漂移项描述的是公式意图的对冲**, 而执行层实际是 BTC 对整篮的价差。结论 DRIFT-DEPENDENT 仍成立: 方差上升, 且增量不超过漂移项。
8. `m2_exec_path.py` 的机制表是平书近似(无持仓、无止损), 只用于解释机制; 判据用的是模拟器的已实现 β。
9. `m2_exec_path.py` 用过两个版本: OLD 用 0c2ee943, NEW 用 896c495e。后者只改了两处, 对 OLD 的输出没有影响: 一是底座 run 可以从派生配置记录的 base_config 取; 二是没有已发布锚的年份具名列出, 不再参与聚合。
10. 2026-08-31→09-18 的扩展窗(只描述)没有做 M2: OLD 的 A0 目标只到 08-31, 我也没有为扩展目标另建 M2 文件。

## §8 收据与提交
- 装置: `m2_lib.py`(93f8e760), `m2_tests.py`(2544fd03), `m2_build_targets.py`(fcf80296), `m2_exec_path.py`(0c2ee943 → 896c495e), `m2_make_config.py`(5ac11740), `m2_make_config_hook.py`(0656adb9), `m2_hook.py`(e6e755ea), `m2_path_compare.py`(36ff925d), `m2_readout.py`(66cbfe80), `m2_render.py`, `m2_chain_new_literal{,_v2}.sh`, `m2_chain_readouts.sh`, `run_m2.sh`。
- 目标: OLD M2 为 `TARGETS_A0_main_M2.npz`(25e1c3d1, pod2 `/workspace/m2_btc_overlay_2026-09-23/work/targets/`); NEW M2 为 `TARGETS_NEW_{s42,s2027}_M2.npz`(6613efa9 / 17576061, pod2 `/dev/shm/…/work/targets/`)。
- 提交: d9aad42fd(装置与运行前声明, 先于任何 M2 NAV)、846be156e(NEW 目标/配置/诊断与 NEW 路线 L 范围声明, 先于任何 NEW M2 NAV)、本文提交(读数)。
