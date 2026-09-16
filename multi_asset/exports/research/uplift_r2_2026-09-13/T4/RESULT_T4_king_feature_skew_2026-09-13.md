> **创建:** 2026-09-13 ~07:4xZ | **Session:** https://claude.ai/code/session_01BzpuBRGZh8oPvpD8NgqsME (teammate T4) | **状态:** 已判(判据冻结于 `PREREG_T4_king_feature_skew_2026-09-13.md` sha256 `0f94b754…b4dd`, 2026-09-13T06:52:11Z, 先于任何结果数字; 每个装置运行前断言该 sha); 数字后未改阈/窗/读法; 未经 lead 复跑 | **作废条件:** 生产者 `shadow_loop_v3.py`(e9c98374…)或在役 booster(8d79186b)换代; 研究 king 源 `SLOW_v3_on_v4axis.npy`(64767318…)或 r18 装置(9b8a6323…)被替换; 冻结快照 `private/snapshot_1789272000/` 被改(SHA256SUMS 会红)
> **口径:** v4 钉; g = net_ex/gross_total, bps/4h 锚/单位 gross; king rank-IC 对记账 y4s = Π(1+r)−1 RAW(`meta_newprod_v4.npz`); 未从 5m 缓存重算任何收益。表格由 `devices/t4_tables.py` 从收据渲染到 `receipts/TABLES_T4.md`。
> **零接触(VERIFIED):** `~/wide_shadow` 与 `~/dl_quant_live` 只读(生产者 venv 只当解释器; combo 子进程 `PYTHONDONTWRITEBYTECODE=1`); 平价目录 `parity_replay_2026-09-12/` 未写(git status 空); 无 API 调用; pod2 只用 CPU, 每次运行前后 `nvidia-smi` 0 % / 2 MiB, PID 333197/339489 全程 `Tl`; Mac 回放 07:36:11Z 结束, 早于生产者 08:16Z 运行窗(另设 08:08Z 按 PID 停机守卫, 未触发); 未提交。

# RESULT · T4 · king 第 80 列训练/服务口径错配的影响

## §0 一页

**判决(§5 冻结规则): NOT MATERIAL(在本分辨率下)。** 条件 (A) 与 (B) 都不成立, 无附加标签(NW 基线结论相同; 量化零对照未触发)。

> ⚠ **更正 KB-48 · P2 · AUD-KB K4 2026-09-16**(原句字节保留, 不改写): **判决(§5 冻结规则): NOT MATERIAL(在本分辨率下)** ⇒ **FX-EVAL K2 重标: INCONCLUSIVE**(RELABEL_TABLE_K2, δ D1 = 0.05 / D4 = 0.003): 书层 Δg +0.0181 [−0.0299, +0.0625](s42)/ +0.0161 [−0.0332, +0.0645](s2027) 越出 ±0.05, 未排除经济意义差异; IC 轴 ΔIC −0.000101 [−0.000272, +0.000070] ⊂ ±0.003 = EQUIVALENT。不构成「不重要」证明


| 读数(KING_LIVE = 2024-01-01 起 5838 锚 / 973 UTC 日) | 值 [CI95] |
|---|---|
| 书层 Δg(按服务 v1 − 训练一致 v0), C0 基线, 种子 42 | **+0.0181 [−0.0299, +0.0625]** |
| 同上, 种子 2027 | **+0.0161 [−0.0332, +0.0645]** |
| king rank-IC 差 ΔIC(v1 − v0) | **−0.000101 [−0.000272, +0.000070]**(IC 水平 0.0622) |
| 分辨率(CI95 半宽) | 书层 ±0.046 / ±0.049 bps/锚; ΔIC ±0.00017 |

**分数确实变了, 但 IC 与书净额的变化分不出零**: 逐锚 Spearman(v0 分数, v1 分数)均值 0.9944(最小 0.9685); 4h 结算名 12.9% 的格换了 king 十分位, 1h 名 26.8%, 8h 名 3.7%(8h 名自身输入只差在 float 舍入量级或记忆窗内换过间隔的名上, 主要是被 4h/1h 名挤动了秩位)。点估计略偏向「按服务的 v1」(四个基线×种子格 +0.005…+0.021), 2026 年内两种子反号(+0.026 / −0.025)。

**历史(§1)**: 第 80 列从影子首锚 **2026-08-16 12Z** 起就按 v1 服务, 生产者全部版本同一写法; 两代在役 booster(08-16 的 29ffaf58、09-01 的 8d79186b)**都是 v0 训练**(数据级识别)。错配在**同一个 bundle 导出器里分叉**: 它在 v0 特征文件上训练 booster, 却给生产者导出 v1 EMA 状态。真钱自 2026-08-22 12Z 带着这个错配交易。研究回放的 king 腿(r18/A0 用的 `SLOW_v3_on_v4axis.npy`)本轮逐位复现为 v0 打分 —— **回放 king 与实盘 king 在 4h/1h 名上确实不是同一个分数**, 这是回放-实盘差的一个真实来源, 但按上表它在书层的量级在 ±0.05 bps/锚分辨率之下。07-27 的 as_trained/corrected 裁定管的是执行器的 DL 头, 不是这个 king; **不是回退, 是同类错配在一条没有逐件口径门的新管线里重现**。

**实盘窗(§6, 41 链式锚 09-05 16Z → 09-12 08Z, 描述)**: served 臂仍逐位复现线上(king L∞ ≤ 9.3e-10, 41/41); 只改第 80 列的 v0 臂相对 served: king 分数 Spearman 中位 0.9950(最小 0.9864), 9.7% 成员格换十分位(4h 名 11.4%); **combo target_live 归一 L1 中位 0.0081(最大 0.0134), L∞ 中位 2.7e-4, 权重相关 ≥ 0.99980**; 描述性价格 Δg(v0 − served, 32 锚 / 6 日)+0.097 bps/锚 —— 只 6 个日块、只价格、链式持仓分叉, 与 973 日历史读数的符号相反, 不作结论。

**修复形态(只陈述, 不提议)**: 给 king 第 80 列服务 v0, 或用 v1 重训 king; 两者都是生产者/bundle 改动, 需用户字。本轮证据不支持「修了就会变好」。

## §1 事实表(按日期; 全部来自代码与产物)
| 日期 UTC | 事实 | 收据 | 标签 |
|---|---|---|---|
| 07-11 → 07-25..29 | 执行器 140 名 DL 书的 as_trained/corrected 裁定: 对象 = `wide_dl_full.npz`(07-11 建)与 `checkpoints/king_fold4.pt`、`s2_fold4.pt`(「frozen king/s2 heads」); 机制 = 逐件口径门 `signal/assert_funding_dim.py` + 内容 sha 登记 | `dl_quant_live/live/factor_version_registry.py` L48–98 | VERIFIED(代码) |
| 08-15/16 | 宽书 slow-LGBM king 出现。特征构建器第 80 列 = 面板 `f_fund_ema`(v0)、第 81 列 = `f_fund_now`(原始费率): `pod_fea_wide.py` L64、`pod_fea_ext.py` L61(文件头「fund 列语义不变(v0+now)」)。面板定义 `pod_panel_ext.py` L124–143 | 代码 | VERIFIED |
| 08-16 13:03Z | 八月 bundle(`pod_export_shadow_bundle.py`): **L17/L42 在该特征文件上训练并保存 booster 29ffaf58; L69 用 `f_fund_ema_v1` 建 fund 腿; L196/L207 导出 v1 EMA 状态 `fund_ema_v1_state.json` 给生产者** | 代码 | VERIFIED(代码) |
| 08-16 | 29ffaf58 训练第 80 列 = v0: 其 `feature_infos` 第 76/77 项与「正典八月面板 v0 重铸」的建箱抽样逐字相同, 换成 v1 则第 76 项不同(八月特征文件已于 09-01 覆盖, 成员集为近似, kline 列 75/76 相同) | `receipts/RECEIPT_T4_facts_booster_sample.json` | VERIFIED(数据级识别) |
| 08-16 12Z | 影子首锚(booster 29ffaf58)。EMA 由上面的 v1 状态起步 ⇒ 第 80 列自首锚即 v1 | `shadow_log.jsonl` 首个 signal 事件 | 首锚代码版本未存档(最早存档 `shadow_loop.py` mtime 08-17 04:19Z)⇒ INFERRED |
| 08-17 → 09-04 | 生产者全部存档版本: `shadow_loop.py` L234/L302、`shadow_loop_v2.py` L278/L346、`v3.bak_predemeanfix` L315/L383、`v3.pre_m1_20260904_backup` L321/L389、现役 v3(e9c98374)L344/L418, 以及研究仓 `wide_live_staging_2026-08-22/shadow/shadow_loop.orig.py` L234/L302 —— 全是 `rn = rate×8/iv` 与 `FE_ANCH[:, 80] = fe_v` | 文件 + grep | VERIFIED |
| 未测时刻(结果文件 09-01 06:04Z) | 影子验收 A2 PASS(权重相关中位 0.9999): 比对的是 α = 0.1 平滑后的权重, 且每锚把 H 重置为参考轨迹(L165), 被比较的两个向量共享 0.9×H | `~/wide_shadow/acceptance.py` L38–168, `acceptance_results.json` | VERIFIED(代码读法; 该门对列错配的灵敏度未测) |
| 08-22 04Z | 首个 king `target_live`(`shadow_loop_v2`, booster 29ffaf58) | `state/target_live/1787371200.json` | VERIFIED |
| 08-22 12Z | 首个真钱宽书锚 | `docs/ERROR_LEDGER_2026-08-20.md` L83 E-0822-A | 转引 |
| 08-26 04Z | combo 覆写 `target_live`; king 腿 = 同一 booster 的 `legz["king"]`(v1 输入); V2MAIN 的 `fund_ema` 输入同样是 v1(`combo_stage.py` L141/L146) | MILESTONE_2026-08-26 §0; 代码 | VERIFIED |
| 09-01 06:00Z 建 / 08Z 服务 | bundle v3(`pod_export_bundle_v3.py`)同样分叉: L26/L52 训练 8d79186b, L87 v1 fund 腿, L214/L231 v1 状态。训练文件第 80 列 v0(T1 逐位 100%); 8d79186b 的 78 项 `feature_infos` 与 v0 重建 **78/78 逐字相同**, v1 重建第 76 项不同 | `shadow_log.jsonl` booster 切换锚; T4/T1 收据 | VERIFIED |
| 09-05 12:47Z | 在役席位的 king 腿收益历史 917 行由 v3 样本外(v0 打分)行播种, 此后追加行是 v1 打分 | STATE.md L146 | 转引(未测) |
| 08-21 | 08-21 仪器 `slow_pred_hist_oos.npy`(`pod_slow_hist_folds.py`)同为 v0: `pod_panel_wide_hist.py` L91–100 原始费率 EMA, `pod_fea_wide_hist.py` L66 | 代码 | VERIFIED(代码) |
| 09-09 03:29Z | 研究 king `SLOW_v3_on_v4axis.npy` = bundle v3 `slow_pred_pinned.npy` 按 E_ts 对齐(`build_dev_v4.py` L40–41)。本轮用导出器配方重建: 2026 行逐位复现(580,800 格), 2024/2025 两折重训逐位复现(601,406 / 849,811 格), 对齐文件与原件**字节相同**(sha 64767318…) ⇒ **研究 king 在全部 2024–2026 格上是 v0 打分** | `receipts/RECEIPT_T4_kings.json` | VERIFIED |
| 09-12 | r18/A0 书的 king 输入 = 上一行文件(`r18_drive.py` L48、L53–55) | 代码 + r18 收据 | VERIFIED |

**任务书 (iii) 的回答**: 07-27 裁定不是为这个 king 设的(对象是执行器 DL 头与 `wide_dl_full.npz`), 宽书 king 晚三周才出现, `~/wide_shadow` 与 `fea171` 的 .py 对 `as_trained / funding_panel / assert_funding_dim` 零引用 ⇒ 没有「路由到 v0 后又被回退」这回事。

## §2 门(`receipts/TABLES_T4.md` T4、各收据)
| 门 | 读数 | 判 |
|---|---|---|
| 列 81 口径(预注册前) | 训练第 81 列在 1,195,841 个「原始 ≠ 归一化」格上 100% = 原始; 服务侧 C81 实测 10,786 格相对差 0 | 两侧同为原始 ⇒ 不设第 81 列臂 |
| K26 | 8d79186b 在存储 v0 输入上对 2026 全部 580,800 格的预测与归档逐位相等 | PASS |
| KF | 重训 2024/2025 折预测与归档逐位相等 ⇒ K0 = 归档研究 king | PASS(逐位) |
| AL | 对齐后与 `SLOW_v3_on_v4axis.npy` 字节相同 | PASS |
| S0 | 第 76 列逐位相同的行上分数差恰为 0(三段各 36/143/203 行) | PASS |
| PB | T4 开发树 + K0 文件跑 C0_s42, `rec`(10039×23)与 `W`(10039×829)与 r18 归档逐位相等 | PASS |
| PC1 | served 臂 king L∞ 最大 9.31e-10(41/41); combo `target_live` L∞ 最大 1.125e-4(41/41 ≤ 2e-4, 与 Phase 1 包络同); 席位腿收益条目差 0 | PASS |
| PC-INJ | 注入路径喂装置自己的 EMA: X、pred、king npz、king 目标文件 41 锚逐位同 served | PASS |
| ONE-PLACE | diff 恰一行; 成员集全同; 第 76 列之外 X 逐位同; 第 76 列相同的 386 行 pred 逐位同 | PASS |
| V0P | v0 馈入对 x0910 面板 `f_fund_ema`(27 锚, 10,799 格): 相对差中位 2.2e-7, 99.66% ≤ 1e-3; 例外 DEXE 26 / GWEI 9 / EPIC 2 | PASS |
| V1R | 同一重建乘 8/iv 对服务值(41 锚, 16,399 格): 中位 1.9e-7, 99.37% ≤ 1e-3; 例外 ERA 41 / DEXE 32 / GWEI 25 / EPIC 4 / IOST 1 | PASS |

V1R 例外名与 T1 记录的「07-09..08-14 生产者把 1h 行记成 4.0」的名单重合(ERA、DEXE), 这些行留在生产者自己的 v1 状态里, 重建看不到; v0 不依赖间隔, 所以 V0P 不受影响。实盘窗首锚(09-05 16Z)抽查: 8h 名第 76 列 served/v0 中位 1.000000(p10–p90 0.999999–1.000001, 87 名中 5 名逐位相同), 4h 名 2.000000(p10–p90 1.999995–2.000005) —— 实质差异只在非 8h 名上。

## §3 分数层(`TABLES_T4.md` T1)
| 窗 | 逐锚 Spearman(v0, v1) 均值 / p1 / 最小 | 十分位变动 全部 / 4h / 1h / 8h | IC v0 | IC v1 | ΔIC [CI95] |
|---|---|---|---|---|---|
| KING_LIVE(= W_ALPHA 上有 king 分数的锚, 装置核实相同, 5838) | 0.9944 / 0.9824 / 0.9685 | 9.18% / 12.87% / 26.82% / 3.73% | 0.06219 | 0.06209 | −0.000101 [−0.000272, +0.000070] |
| Y2026(1452) | 0.9942 / 0.9847 / 0.9799 | 10.76% / 13.12% / 9.17% / 4.57% | 0.06356 | 0.06370 | +0.000140 [−0.000179, +0.000462] |

ΔIC 逐年(描述): 2024 −0.000385, 2025 +0.000025, 2026 +0.000140。量化零对照 K0f: 十分位变动 0 格, ΔIC −1.1e-8。

## §4 书层(`TABLES_T4.md` T2; Δg = 按服务 v1 − 训练一致 v0)
| 基线 | 种子 | W_ALPHA | **KING_LIVE** | Y2026 | KING_LIVE Sharpe v0 → v1 |
|---|---|---|---|---|---|
| C0 | 42 | +0.0116 [−0.0156, +0.0396] | **+0.0181 [−0.0299, +0.0625]** | +0.0264 [−0.0457, +0.0982] | 2.151 → 2.182 |
| C0 | 2027 | +0.0103 [−0.0224, +0.0422] | **+0.0161 [−0.0332, +0.0645]** | −0.0251 [−0.1607, +0.0907] | 2.175 → 2.197 |
| NW | 42 | +0.0137 [−0.0126, +0.0416] | +0.0215 [−0.0225, +0.0631] | +0.0260 [−0.0459, +0.0982] | 2.155 → 2.192 |
| NW | 2027 | +0.0033 [−0.0318, +0.0380] | +0.0052 [−0.0482, +0.0547] | −0.0254 [−0.1619, +0.0901] | 2.205 → 2.210 |

C0 s42 KING_LIVE 分解: Δpnl +0.0233 / Δcarry +0.0065 / Δcost −0.0013; 换手 −0.63%; 席位 king 均权 0.6241 → 0.6190。2024 年前 Δg 恒为 0(首个差异锚 2024-01-01 00Z)。K0f 零对照 Δg ≈ −1e-7。

## §5 判决
- (A) C0、KING_LIVE、两种子 CI95 都不含 0 且同号: **不成立**(两种子 CI 都含 0)。
- (B) KING_LIVE ΔIC CI95 不含 0: **不成立**。
- NW 基线 (A) 同样不成立 ⇒ 无 BASE-DEPENDENT; K0f 零对照 (A)(B) 均不成立 ⇒ 无 INSTRUMENT-FLAG。
- **⇒ NOT MATERIAL(在本分辨率下)**: 书层 ±0.046 / ±0.049 bps/锚/单位 gross, ΔIC ±0.00017。
- 读法边界: 这是研究回放口径的判决。它说「把研究 king 从 v0 输入换成 v1 输入, 2024 年以来书净额与 IC 的变化分不出零」; 它不说在役 king 在实盘里没有吃亏, 实盘窗的差值见 §6。

## §6 实盘窗(`TABLES_T4.md` T4–T6; v0 臂 − served 臂; 只描述)
| 量(41 锚) | 中位 | 最大 / 最小 |
|---|---|---|
| king 原始分数 Spearman | 0.9950 | 最小 0.9864 |
| king 十分位变动(全部 1,593/16,400; 4h 1,452/12,698; 1h 1/88; 8h 140/3,613) | 9.7% / 11.4% / 1.1% / 3.9% | — |
| king 段目标(生产者 king 文件)L∞ | 4.17e-4 | 7.09e-4 |
| king 段目标 归一化 L1 | 0.0116 | 0.0196(首锚 0.0010, 随 EMA 状态累积) |
| **combo `target_live` L∞** | **2.69e-4** | **4.78e-4** |
| **combo `target_live` 归一化 L1** | **0.0081** | **0.0134**(首锚 0.0013) |
| combo 权重相关 | 0.99991 | 最小 0.99980 |
| combo gross 比 v0/served | 1.0008 | 0.9993–1.0019 |
| 掩码席位 king 权重差 | +0.00025 | −0.00035…+0.00059 |

**描述性价格 Δg**(combo `target_live`, 对记账 y4s, 32 锚 / 6 个 UTC 日): 均值 +0.097 bps/锚/单位 gross, 日块 CI95 [+0.035, +0.140]; 单锚最大 +1.087(09-08 12Z)、最小 −1.160(09-08 00Z)。**不作结论**: 6 个日块的分位区间不可靠; 只含价格(无 carry、成本、执行钟); 链式两臂持仓会分叉; 与 973 日历史书层读数符号相反。作为量纲: 它比 R22 测得的回放-线上基线残差 U = 0.0017 bps 大约 58 倍, 即差值是装置分辨得出来的真实目标差, 但方向在一周内不可判。

## §7 修复会是什么(事实陈述, 不是提议)
1. **服务 v0 给 king 第 80 列**: 生产者在第 4 步并行维护一份原始费率 EMA 状态(同半衰期), 持久化并播种(本轮 `devices/t4_v0_feed.py` 的重建法, 或导出器加一份 v0 状态), 只把 king 列换成它; fund 腿、carry、FTRIM 仍用 v1。另需平价测试(对研究 K0 的重叠锚)与生产者换装流程。
2. **用 v1 重训 king**: 把特征构建器 FUND 列换成 `f_fund_ema_v1`, 重建特征文件、重训三折与 slow2026、重过 IC 门与书层回放, 并按 09-05 先例重新播种席位历史。
3. 两者都是生产者/bundle 行为改动, 需要用户字。本轮读数不显示任何一种能提升书: 历史点估计略偏向现状(v1), 实盘一周描述值偏向 v0, 均不可判。V2MAIN 的同形错配(§1 08-26 行)不因只修 king 而消失。

## §8 偏离预注册与事后处理
1. 预注册在任何结果数字之前冻结两次, 唯一改动是头部创建时刻标签(~07:1xZ → 06:5xZ); 两个 sha 都在 `receipts/PREREG_FREEZE_sha.txt`。
2. 两个口径识别装置(`t4_facts_caliber.py`、`t4_facts_booster_sample.py`)在预注册之前运行, 只读口径与血统, 结果写进预注册 P4/P5。
3. 快照: 第一条 shell 命令里 BSD `seq` 输出科学计数法, 逐锚文件拷贝全部报错(未拷任何逐锚文件); 四个核心文件在同一命令里一次拷完, 前后 mtime 与 `last_anchor` 相同; 逐锚文件随后用 Python 拷贝(247 个), SHA256SUMS 254 行。
4. `t4_v0_feed.py` 审计计数条件写错(把种子区间之前的行算作区间内), 修后重跑; 馈入输出 sha 不变(e3eb4dde…)。
5. `v1inj` 首次启动在参数解析就失败(zsh 不对 `$ANCH` 分词), 未做任何计算; 用 `${=ANCH}` 重跑。
6. 驱动 `t4_replay_driver.py` 在任何运行前两处小改: chain-only 断言挪到 `main_snapshot` 之前; 收据的 `device_sha256` 改为按臂取文件。完整差异 `devices/t4_replay_driver.diff`(194 行, 全部标 `# T4`)。
7. 书层 K0 基线: C0_s42 用本轮 PB 运行; C0_s2027、NW_s42、NW_s2027 用 r18 归档臂(它们的 king 文件与 K0 字节相同, r18 GATE P 已逐位覆盖)。
8. 实盘窗 8h 名的第 76 列差在 float32 舍入量级(§2 末段为首锚抽查, 事后描述, 不入任何门), 这使 ONE-PLACE 统计里「第 76 列不同」的行数(16,014/16,400)包含大量浮点级差; 不影响任何门的判定。

## §9 核实不了 / 边界
1. 08-16 booster 的训练口径靠 LightGBM 建箱抽样范围识别, 八月特征文件本身已不存在; 成员集为近似。
2. 影子首锚(08-16 12Z)跑的代码版本没有存档, 「首锚即 v1」由导出的 v1 EMA 状态推出。
3. 判决是研究回放口径(v4 钉、`costb_PWR_G230k` 成本模型), 不是实盘盈亏; 实盘窗只有目标文件差与描述性价格 Δg。
4. V2MAIN 的同形错配未测; 在役席位的 king 历史(v0 打分行播种)未测。
5. 执行器是否按写出的每个 `target_live` 交易未在本轮核对(文件同一性见 R22 materiality)。
6. 回放与线上 combo 段仍有 ≤1.13e-4 的历史残差(机理未闭合, Phase 1 已记); 两臂共享该残差源, v0−served 差值不受其影响, 但 served 臂对线上的 combo 复现是「包络内」而非逐位。

## §10 复跑(逐字)
pod2(cwd `/workspace/uplift_r2_2026-09-13/T4`; 先 `scp -q /Users/haosiyu/wide_shadow/shadow_bundle.aug20260816_backup/slow2026.txt pod2:/workspace/uplift_r2_2026-09-13/T4/private_inputs/slow2026_aug_29ffaf58.txt`):
```
env -i PATH=/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin HOME=/root /workspace/venv/bin/python devices/t4_facts_caliber.py PATH,HOME,LC_CTYPE
env -i PATH=/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin HOME=/root /workspace/venv/bin/python devices/t4_facts_booster_sample.py PATH,HOME,LC_CTYPE
env -i PATH=/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin HOME=/root /workspace/venv/bin/python devices/t4_kings.py PATH,HOME,LC_CTYPE
env -i PATH=/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin HOME=/root /workspace/venv/bin/python devices/t4_extract_x0910.py PATH,HOME,LC_CTYPE
env -i PATH=/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin HOME=/root /workspace/venv/bin/python devices/t4_book_drive.py PATH,HOME,LC_CTYPE
env -i PATH=/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin HOME=/root /workspace/venv/bin/python devices/t4_judge.py PATH,HOME,LC_CTYPE
```
(前三个与 book_drive 实际以 `nohup … > receipts/<装置名>_stdout.log 2>&1 < /dev/null &` 启动; 日志拷在 `receipts/pod2/`。)
Mac(快照已冻结在 `private/snapshot_1789272000/`, 逐文件 SHA256SUMS; 驱动启动时校验):
```
cd …/T4/devices && env -i PATH=/usr/bin:/bin HOME=/Users/haosiyu /usr/bin/python3 -B mk_t4_v0col80_device.py
cd …/T4 && env -i PATH=/usr/bin:/bin HOME=/Users/haosiyu /usr/bin/python3 -B devices/t4_v0_feed.py PATH,HOME,LC_CTYPE,CPATH,LIBRARY_PATH,MANPATH,SDKROOT,__CF_USER_TEXT_ENCODING
cd …/T4/devices && ANCH=$(python3 -c "print(' '.join(str(a) for a in range(1788624000, 1789200000+1, 14400)))")
env -i PATH=/usr/bin:/bin HOME=/Users/haosiyu REPLAY_COMBO=0 /Users/haosiyu/wide_shadow/venv/bin/python -B t4_replay_driver.py --arm v1inj --chain ${=ANCH}
env -i PATH=/usr/bin:/bin HOME=/Users/haosiyu /Users/haosiyu/wide_shadow/venv/bin/python -B t4_replay_driver.py --arm served --chain ${=ANCH}
env -i PATH=/usr/bin:/bin HOME=/Users/haosiyu /Users/haosiyu/wide_shadow/venv/bin/python -B t4_replay_driver.py --arm v0 --chain ${=ANCH}
cd …/T4 && env -i PATH=/usr/bin:/bin HOME=/Users/haosiyu /Users/haosiyu/wide_shadow/venv/bin/python -B devices/t4_live_judge.py PATH,HOME,LC_CTYPE,__CF_USER_TEXT_ENCODING
env -i PATH=/usr/bin:/bin HOME=/Users/haosiyu /usr/bin/python3 -B devices/t4_tables.py
```
(`served` 与 `v0` 两臂并行运行; zsh 下 `${=ANCH}` 为分词写法。不要在生产者 N+15..N+23 分钟窗内跑 Mac 回放。)

## §11 数字标签与校验和
§2–§6 数字 **VERIFIED**(本轮计算, 收据可复算)。转引项: 首个真钱锚(ERROR_LEDGER)、09-05 席位播种(STATE.md)、combo 在役起点(MILESTONE)、R22 基线残差 U。装置、收据与表格的 sha256 见 `SHA256SUMS.txt`。
