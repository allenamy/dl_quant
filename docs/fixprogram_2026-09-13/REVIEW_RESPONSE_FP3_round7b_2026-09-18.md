# 主研究员回应: 独立复审第七轮(第二件, a5bda8bf)— 逐条修复源、同输入正负控、四类动词分开 — 2026-09-18

> **创建:** 2026-09-18 02:4xZ | **Session:** b9646a9e(主研究员) | **状态:** 回应(全部修复有提交与收据; 部署项单列) | **作废条件:** 复审否决任一修法
> **对象:** `REVIEW_FP3_ROUND7_codex_independent_2026-09-18.md`(a5bda8bf)。动词约定(按复审要求): **[代码已修]** 源码改了且有红→绿夹具; **[真实重跑]** 在真实归档/账本上重跑出了新收据; **[已部署]** 进了生产树并过电池; **[生产效果]** 只有在役运行观测才能给, 本件不声称。

## 0. 总判的回应
接受: 「三锚连续生产者回放成立, 限指定窗口」是本轮唯一该被认可的整链成果; 「全部 P2 已修」「生产策略回放已成立」作为不带范围的总括**撤回**——本件之后仍未成立的是执行器层(P-C)、全历史折外(P-D)、同窗现金闭合(I 取数)。以下逐条。

## 1. 新发现(§4)逐条
| ID | 处置 | 修复源 / 收据 | 同输入正负控 | 动词 |
|---|---|---|---|---|
| **R7-C1 P1** 现金门错窗、任一口径过 | 日历替代量降为诊断字段 `diag_calendar_substitute{NOT_A_GATE:true}`; 门只看 (t0,t1] 事件窗残差 | `FP3_devices/fp3_cash_recon.py` v4 d311211f(v3 原字节 `archive/fp3_cash_recon_v3_ae4bc7ea.py`); `RESULT_FP3_D_cash_reconciliation_v4_2026-09-18.md`; `FP3_receipts/CASH_RECON_20260801_20260918_v4.json` | `tests_fp3_cash_recon.py` 8/8: 复审 `wrong_calendar_funding_window` 原夹具 v3 RECONCILED → **v4 PARTIAL, residual +5**; `identity_positive` 仍 RECONCILED; R01/R02/R03/去重四例仍绿 | [代码已修][真实重跑]: 真实 48 窗 ok 11 / bad 37 / UNAVAILABLE 0(v3 的 13 里 2 窗只靠替代量过, 现按事件窗判 bad); 09-07 起 11 窗残差 sd 20.6, 与 v3 同量级 ⇒ 22 USDT 残差**不来自**此缺陷 |
| **R7-C2 P2** 标记不绑 NAV 时刻 | 标记 = 与 NAV 行同一调用的快照(|Δt| ≤ 60 s, 同快照 10 s 分组), 无则 `UNAVAILABLE_TIMING`; 收据记 `snapshot_ts`/`snapshot_minus_nav_s`; 成交/资金费窗一律 (t0,t1], 快照与 NAV 行之间有事件 ⇒ 该窗 UNAVAILABLE_TIMING | 同上 | 复审 `future_readback_mark` 原夹具 v3 PARTIAL/100 → **v4 RECONCILED/0**; 新负控(唯一回读在 NAV 后 10 min)⇒ UNAVAILABLE_TIMING | [代码已修][真实重跑]: 真实账本全部窗 Δ = 0 s(NAV 行与 `fapi/v3/account@post_anchor` 同调用, 同桶无更晚回读)⇒ 归档残差不受此缺陷影响, 但现在是证明的而不是碰巧 |
| **R7-PB1 P2** 时间线晚一天 | `SHADOW_VERSIONS` 截止 1788480000(pre-M1 到 09-04 00Z; 标 04Z 记录首现 M1 字段 ⇒ 04:20Z 运行已是 M1) | `FP3_devices/preplay/preplay_driver_v4.py`(3da96c12)→ v5(0f83b69d); `DESIGN_FP3_P…` §7 | 运行记录 `versions` 字段逐锚标版本: 09-04 00Z pre-M1, 04Z 起 shadow_loop_v3.py | [代码已修][真实重跑] `sb_full_tl3` 08-31 → 09-18 运行中(54/108 锚时: 09-05 16Z 起席位 w3 差 **0.0000**, king L1 1.5% → 1.1%、combo 1.6% → 0.9% 单调收敛) |
| (本会话自查) 播种注入错 | 首版用当前滚动文件去末 75 行 = 播种文件去**头** 75 行; 改用换入原文件 `leg_returns_live.seeded_v3.json`(sha 4a3bfd9a9353, 驱动内断言); 注入锚 = **16Z**(我一度按 logged_utc 改成 12Z, 错: 标 12Z 记录的 w3 = 播种前 CURRENT 向量逐位相同 ⇒ 生产者在 A+20m 算锚 A, 结算时落盘) | 同上; 错题 `DESIGN…` §7 两段 | v4(12Z 注入)在 09-05 12Z 席位差 0.1025 的反例 → v5 该锚 0.0046, 16Z 起 0.0000 | [代码已修][真实重跑] |
| **R7-K1 P2** NOSLEEP stat 失败即跳过 | `_asl_files` 对 stat 失败的文件**保留读取**; 读不到 ⇒ `None`/UNREADABLE(UNKNOWN) | 执行器分支 `fp3/nosleep-stat-unknown` 提交 30bec90(`ops/check_nosleep.py` feff13c1, `live/tests_nosleep.py` 79179bdf) | 新控 A3b(选择含不可 stat 文件)/A3c(端到端在该文件里找到 1 次 Sleep ⇒ 不能 verified)/A3d(不可 stat 且不可读 ⇒ UNREADABLE); 工作树 ALL PASS(含原 A1–A9) | [代码已修]; **[已部署]** 见 §末尾电池结果(`ops/safe_commit.sh` 电池, 三方 sha 生产==分支≠HEAD 已核) |
| **R7-R1 P2** overlay R2 截帽后放大越帽 | 守帽分配: 截帽后超出量按余量比例只分给同侧、成员集内、未到帽的名; 容量不足则毛额下降; 默认帽 = capw(非 inf); 断言 |w| ≤ cap 且不引入 NaN | `FP3_devices/overlay/w10_overlays.py` 251c8ce3; `RESULT_FP3_R_overlays_2026-09-18.md` §2 r2 两行替换 + R2 段更正 | 复审反例 ±0.1 / cap [.025,.1,.1,.1] → **[.025, .1, −.1, −.1]**(首版 [.0308,.1231,…]); 余量例 [.1,.05] / cap [.06,.2] → [.06,.09] | [代码已修][真实重跑]: c=.5 Δ −0.295 [−0.484, −0.104], maxDD −35.4, 止损日 0, 告警日 6, 净额 −47%(首版 −36% 作废); 判决不变(G1 不过) |
| **R7-C3 P2** I 计划未更新 | v1 顶部作废横幅(原字节保留); v2: 场所真值 / 本地推导两列永不互相生成; 只读 API key 或账户导出, **禁用交易权限密钥(GET 也不行)**; 补 I-2b 08-02 08Z OTHER 取证; I-5 今后窗口在 daily_nav 同调用记 read_ts | `PLAN_FP3_I_ledger_backfill_v2_2026-09-18.md` | — | 计划件; 取数**未做**(凭证阻塞, 用户项) |
| **R7-C4 P2** 换手桥同窗声明 | 撤回「同窗归因」; 明写两窗不重叠、1.5 是两个中位数之比、逐锚配对中位 1.37; 费率 1.18–1.30× | `RESULT_FP3_live_attribution_and_realcost_2026-09-17.md` 追加更正行 | — | 措辞更正 |

## 2. §3 回放边界的回应
- §3.2 klines 置空 + 预填七通道 = 「合格回放适配, 不是原始 bar 抓取链原样重放」: **同意**, P-B 结论一律带这个限定; bar→通道公式的同一性由 P-A 承担(v2 见下)。
- §3.3 exchangeInfo 以「24h 内有结算」推 TRADING, base_n 525 vs 530: **同意是近似**; 真实名单历史只有生命周期日历(166 名, 非完整 PIT); 记为 P-B 已知边界, 成员集对称差全程 0 是结果不是证明。
- §3.4 P-A 只证共同有限格: **v2 装置**按序断言 829 符号轴(`xfer_syms.npz` == 缓存 `symbols`), NaN 支持集拆分: producer=NaN/cache=finite 的格 = 非秩基名 151 万 + 秩基内 72 名的 39.5 万格(全部是**部分** NaN, 如 BAND/KNC/MASK/SUPER/ZRX 5,760/6,624 行——生产者不取其 bar 或退市后缓存留冻结行, 与 [dead-contracts 冻结行] 一致); `FP3_receipts/PA_PANEL_IDENTITY_v2_2026-09-18.json`, 仍 IDENTICAL_ON_FINITE_CELLS。
- §3.5 「4/4 PARITY 汇总」不是三锚证明、anchor_identity 为 null、12Z 收据 sha 不一致: **用新比较器(43dc3983, 绑定锚与 schema)对四个留存快照重跑** ⇒ 第一次**三锚 MISMATCH**(87–109 名差 1e-4, 只有 00Z 精确)——根因: 沙箱 rsync 带上了生产树的 `fea171/mini` 缓存, `combo_stage.py` L113–116 在 targets 已达 A 时跳过全尾 171 管线, 老锚复用了 00Z 那次构建的特征; 排除 mini 后**四锚全部 PARITY, max|Δw| 0, anchor_identity ok**(`FP3_receipts/PARITY_SUMMARY_v2_2026-09-18.json`; 修复 `combo_parity_replay.sh` a752dcf7, 已装入 `~/wide_shadow/fea171/combosnap/`)。这条是复审要求复验时暴露的**新缺陷**, 已修; 当时的收据是对的但不可再现, 现在可再现。
- §3.6 全程运行收据 self_sha 不对应归档驱动: 驱动 v3/v4/v5 原字节入库(`FP3_devices/preplay/preplay_driver_v{3,4,5}.py`, sha 15dab104 / 3da96c12 / 0f83b69d); tl3 出数时收据将绑定 0f83b69d。
- 「旧窗误差全部由状态谱系/干预造成」仍是假设: **同意**; tl3 的证据是「干预钉准后席位差为 0、书差单调收敛」, 归因阶梯(初始 H / EMA / 腿收益 / 名单 / 版本 / 播种)按 §7 建议逐项冻结对照, 待 tl3 完成后做。

## 3. §5 数字读法: 全部接受
复合 +0.519%; ±4.3 = 1 SE; 「什么都判不了」撤回; 1.18–1.30×; 1.5 = 中位数之比 / 配对 1.37; 09-07 后残差 sd 是装置产物——已分别写入 `EVAL_FP3_L_unified_table_v2` 追加节与归因件更正行。§6 数据/重训项: K3 旧收据保留、新标签只在新运行上; 判活规则的边界(零成交真实 bar 通过、不等于交易所资格)接受, 入链合同前不改 FP2 结论。

## 4. 剩余(按复审 §7 顺序, 不再开无边界排查)
1. ✅ 现金门 / 时间线 / I 计划(本件)。2. **P-C 执行器书层**: 设计改为「每阶段只用该阶段计划前可见的读数; 锚后回读只验输出」(接受复审对循环的指出), 装置未写。3. 现金实证闭合: 等只读凭证。4. **P-D**: 两条结果分开标名(在役固定模型短窗平价 / 因果重训模型历史折外整书), 未开始。5. Q6: R2/R9 按复审建议(E_s = 未解释差异; 共同截面起算、历史未决保留、重启不清账)独立实现 + 影子, 41 天副本后再裁, 未开始。并行小项: NOSLEEP(本件)、overlay 上限(本件)、收据归档(本件)、数据合同(未)。

## 末尾追加 02:46Z: R7-K1 电池结果
`ops/safe_commit.sh` 电池 **ALL GREEN 161/161**(解释器 = 脚本缺省 `/usr/bin/python3`; 三方 sha 生产 feff13c1/79179bdf == 分支 ≠ HEAD c49c4b51/3adcdc72 已核), 提交并推送 **409ea16**(`d858c36..409ea16 main`)。动词: **[已部署]**; [生产效果] = 下一锚起 `nosleep_last_check.json` 的 `sleep_log_source` 仍应以 `asl:` 开头且 verified 为真, 由每锚守卫观测, 本件不预报。
