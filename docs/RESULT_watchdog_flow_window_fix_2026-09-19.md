> **创建:** 2026-09-19 | **Session:** session_01KW6frfphbFmFzx7wUtGhLb(子代理: 裁定 #5 看门狗划转窗修复) | **状态:** 隔离克隆内实现 + 测试 + 全电池; **未部署**(生产执行器仍是 `409ea16`, 本文件不授权部署) | **作废条件:** 部署前生产执行器 HEAD 不再是 `409ea16`(需在新基线上重做 §4 红/绿与 §6 电池); 或复审推翻 §1 合同的任一条; 或场所改变 `/fapi/v1/assetIndex` / `multiAssetsMargin` / `income` 的语义

# 看门狗 §4-2 / §4-4 外部资金流: 按事件时间、按资产、以 NAV 自身单位归窗(裁定 #5)

**⛔ 未部署。** 生产执行器 `~/dl_quant_live` 运行树 `409ea16`(本会话只读核对), 本工作全部在隔离克隆
`scratchpad/exec_clone_watchdog5`(分支 `fix/watchdog-flow-window-2026-09-19`)里完成; 未对生产仓写入、未推送、未碰 launchd、
未调用交易所(克隆无 `.env`、无任何密钥)。部署由 lead 按 §8 清单执行。

## §0 结论(白话)

1. **修了什么**: 看门狗判「单日亏损」(§4-2)和「自起始权益累计收益」(§4-4)时, 以前靠 `daily_nav.external_flow_usdt` 这一个数判断
   有没有出入金。它有三处毛病: 把不同币按数量相加(08-05 的 −200 USDT 和 +0.33275 BNB 记成 −199.667)、按自然日累计而不是按被比较的
   两行 NAV 之间、以及**前一日最后一行(~20:4xZ)到 00:00Z 之间的划转谁都不记** —— 次日会把出金读成亏损。另外账户是多资产保证金,
   NAV 是 USD, USDT 脱锚会被读成亏损。
2. **现在**: 每行 NAV 旁边记一份 `flow_window` 记录(每笔非盈亏收入的**自己的时间**、币种、金额、场所 id; 覆盖到前一日最后一行的
   「缺口段」拉取; 场所的保证金模式与抵押计价率)。§4-2 用 **(V(t1) − F − V(t0)) / V(t0)**, V = NAV 的 USDT 等值, F = 窗内流量逐币按
   场所计价率折算; 任何一项证不出来 ⇒ **UNKNOWN 并写明原因**(沿用既有 blind 动作: 页报、恢复门拒绝, 不触发)。§4-4 的「这天有没有划转」
   改为按同一窗判断(缺口段也算; 证不出没有 ⇒ 当作可能有, 走既有的划转日规则, 流量金额仍不进入)。
3. **没改什么**: 阈值(−4% / −2.68% / −25%)、杠杆、动作合同、`external_flow_usdt` 本身(`ops/daily_summary` 仍读它)。
   **无记录的旧行逐字节按旧口径判**(控制格 0a/0b 在两棵树上都绿)。
4. **证据**: 新套件 `tests_flow_window` 在修复提交上 **34/34**; 同一套件在 `409ea16` 上 **6/22**(15 个缺陷格 + 变异段红; 其中
   14 格为 RED0: 409ea16 把流量/单位读成亏损并**触发** 11 格、该定价却盲 2 格、在证不出的输入上照常定价 1 格)。13 个变异检查每个都把对应格打红。**真实账本影子回放**(50 天 291 行,
   只读): 旧口径 42 天定价、8 个划转日盲; 新口径 50/50 定价、0 个 UNKNOWN; 两者都定价的 42 天差值中位 0.012 pp、最大 0.053 pp
   (= USDT 指数的单位效应); §4-4 在真实账本上**逐位不变**(−2.4864% 对 −2.4864%)。
5. **全电池**: 见 §6(判词行原文 + 退出码 + 解释器); 克隆与生产的树外状态不同, 6 个套件在**基线 409ea16 就红**, 原因逐条列出, 改后同样
   6 个、同样的失败格, 其余全绿, 新套件绿。

## §1 合同(一处声明: `live/flow_window.py`, 写者与两个读者共用)

| 维度 | 规则 | 不可证时 |
|---|---|---|
| **事件时间** | 窗 = (t0, t1], t0/t1 = 被比较两行的 `nav_ts`(权益快照时刻, 不是拉取时刻、不是自然日)。半开区间 ⇒ 相邻窗划分时间, 每个事件恰落一窗。§4-2: t0 = 前一日最后一行(无可用前收盘 ⇒ 当日第一行, 与旧分支同选); §4-4: t0 = 前一个按日折叠行 | 行无有限 `nav_ts` ⇒ UNKNOWN |
| **覆盖** | 窗内各行记录里 **complete** 的拉取段之并集必须覆盖 (t0, t1] 每一毫秒。写者每行两段: `gap` = [floor(前一日最后一行 nav_ts), 00:00Z − 1](新增拉取, 覆盖 20:4xZ→00:00Z 缺口), `day` = [00:00Z, 拉取前时钟](原有 since-00Z 拉取, 同一次调用)。complete ⇔ 未抛出、`truncated is False`、带原始行、回答的起止与所问一致 | 缺口段/日段失败、截断、起止不符 ⇒ UNKNOWN「coverage」, 列出每个不完整段及原因 |
| **人口/分类** | 非 P&L 类型的每条收入行都记(时间/币种/金额/tranId/symbol)。`PNL_INCOME_TYPES` = {REALIZED_PNL, COMMISSION, FUNDING_FEE, DELIVERED_SETTELMENT}(已在 NAV 内), `FLOW_INCOME_TYPES` = {TRANSFER}(相减)。依据: LIVE 账户 07-31..09-19 全部 134,755 行收入只出现这 5 种 | 窗内出现任何未分类类型 ⇒ UNKNOWN 并点名类型(新类型出现当天就被抓住, 不默认成盈亏) |
| **身份** | 事件键 (tranId, type, symbol, asset) —— 与 `income_since` 的去重键同(E-0909-H); 多行记录重叠的事件取并集、只计一次。另: 每行 `day` 段的 TRANSFER 数量和必须等于该行自己的旧载体 `external_flow_usdt`(同一次拉取; `ops/reprice_day` 追加的行按设计换过窗口, 不比) | 不等 ⇒ UNKNOWN「record identity」; 记录版本不符/畸形 ⇒ UNKNOWN |
| **单位** | V(row) = nav / USDTUSD `bidRate`(该行 `multiAssetsMargin = true`, NAV 是 USD)或 nav(false, NAV 是 USDT)。流量逐币按**收盘行**的场所 `bidRate`(= NAV 自己用的计价: USDT ×(1−1e-4)、BNB ×0.95)折 USD 再除以收盘 USDT 率; USDT 按面值。**新路径中不存在跨币数量相加** | 流量币种无计价率 / 计价率非正或非有限 / 计价时间距快照 > 600 s / 保证金模式读不到 ⇒ UNKNOWN 并点名 |
| **指标** | §4-2: r = (V(t1) − F − V(t0)) / V(t0) × 100(basis `USDT_EQ`, 两端都有计价率时 USDT 脱锚被精确分离)。开盘行无计价率(本版之前写的行, 或其读取失败)⇒ 单位不可分离: 仅当收盘 USDTUSD 指数偏离 1 ≤ ±50 bps 时按行自身单位判(basis `ROW_UNIT …`, 数值与旧口径同式) | 偏离 > ±50 bps ⇒ UNKNOWN「unit not separable … off peg」 |
| **未知行为** | 从不当「亏损」也从不当「没事」。§4-2: 该日 `per_day_loss = None`, 状态串 `flow window UNKNOWN: <原因>` ⇒ 最新权益日不可定价 ⇒ `blind` ⇒ 进 `conditions_blind` ⇒ run_anchor 页报、`resume_from_trip.sh` 拒绝(**409ea16 既有动作, 未改**)。§4-4: `flow_possible` ⇒ 走既有划转日规则(realised + Δunrealised, 流量金额不进入); 该规则也定不了价 ⇒ 既有 `chain_broken` 盲规则 | — |
| **旧行** | 收盘行无 `flow_window` 记录(本版之前写的行、或任何夹具)⇒ **不走新路径**, B32 口径逐字节不变 | — |

**声明的、本修复不证明的**(可证伪, 不冒充覆盖): ① 流量按收盘行计价率而非事件时刻计价 —— 非 USDT 资产在划转后到收盘快照之间的价格变动
算进流量(0.33 BNB ≈ 190 USD, BNB 动 5% ≈ 10 USD ≈ 10 万 NAV 的 0.01%); ② **入账延迟**: 快照前几秒发生、拉取时场所尚未入账的划转对
该锚不可见(409ea16 同样暴露), 当日后续每一行都重拉全日与缺口段, 当日最终读数能看到; ③ 只用正余额的 `bidRate`, 负抵押余额(askRate)
与两行之间切换保证金模式未建模; ④ DEPEG_TOL = 50 bps: 研究缓存 876 个 NAV 附近分钟的 USDTUSD 指数在 [0.99840, 1.00022], 最坏 16 bps;
⑤ §4-4 仍按 USD 的 nav 比值复利(单位未分离), USDT 脱锚会动它 —— 其阈值 −25%, 不在本修复范围, 需另立。

## §2 改动(克隆提交 `1c888279e00949ff8af3c8b5438d9688e44b5953`, 父 `409ea162746d0ba459db33c3f5c07865c24a7514`)

10 文件, +1157 / −9(其中新模块 394 行、新套件 610 行)。行号为提交 `1c88827` 内的行号。

| 文件 | 行 | 改动 |
|---|---|---|
| `live/flow_window.py`(新) | L64–83 声明; L115–188 写者(`_segment` / `build_record` / `collect`); L191–394 读者(`_covers` / `_rate` / `_unit` / `_value` / `window`) | 合同本体, 见 §1 |
| `live/watchdog.py` | L71 | `import flow_window as FW` |
| | L1257–1264 | §4-2 新状态: `_prev_day_row`、`_loss_flow_unknown_days`、`_flow_window_days` |
| | L1379–1387, L1392–1402 | 收盘行有记录 ⇒ `FW.window(开盘行, 收盘行, 当日各行)`; PRICED ⇒ 用 pct; 否则 None + 具名原因(`_safe` 包裹: 求值抛出 ⇒ UNKNOWN 且进 metric_errors) |
| | L1419–1427 | 每日状态串加 `flow window UNKNOWN: …`; `_prev_day_row = n0` |
| | L1647–1656 | cond2 明细: 旧 `caliber` 串注明只管无记录的行; 新键 `flow_window_caliber` / `n_days_flow_window_unknown` / `flow_window_unknown_days` / `flow_window_days` |
| | L1913, L1929–1942 | §4-4: 有记录的行 ⇒ `_is_flow = FW.window(前一折叠行, 本行, 全部 NAV 行)["flow_possible"]`(求值失败 ⇒ True) |
| | L2018–2022, L2028–2029 | §4-4 口径串补一句「划转判定」; 新键 `flow_window_days` |
| `scheduler/anchor_loop.py` | L3112–3113 | 日段拉取前记时钟 `_fw_day_req_ms` |
| | L3122–3134 | `_FW.collect(broker, day_start, prev_row=prev, day_pull=inc, …)`; 永不抛出(失败 ⇒ 版本为 None 的记录 ⇒ 读者 UNKNOWN) |
| | L3179–3180 | `daily_nav(..., **{RECORD_KEY: 记录})` |
| `live/binance_broker.py` | L866–869 | 权重表: `/fapi/v1/assetIndex` 10、`/fapi/v1/multiAssetsMargin` 30 |
| | L2202–2205 | `income_since` 返回值**加** `rows`(去重后的原始行; 加性) |
| | L2222–2268 | 新 `nav_valuation()`: DRY_RUN ⇒ None; 否则两次读取各自记错、从不抛出; 只收 `*USD` 行 |
| `docs/API_SEMANTICS.md` | L35, L48–49 | 两个新端点的语义与调用方; `income` 行补 `rows` 与缺口段 |
| `live/tests_imports.py` | L99–101 | `flow_window` 进生产模块清单(导入图漂移检查要求) |
| `ops/income_callers.py` | L43–46 | `binance_broker` 声明补: 返回 `rows`、缺口段经同一函数 |
| `ops/gate_coverage.py` | L270, L272 | `tests_cond2_stale_day` 自述注明「旧口径只管无记录的行」; 新 `tests_flow_window` 的边界自述 |
| `run_acceptance.sh` | L363–364 | 注册 `tests_flow_window` |
| `live/tests_flow_window.py`(新) | 全文件 | §4 |

## §3 消费者普查(改了返回合同或新增字段的每一处)

| 被改对象 | 改动 | 消费者(全仓 grep, 非测试 + 测试) | 结论 |
|---|---|---|---|
| `BinanceBroker.income_since` 返回 dict | **加** 键 `rows` | `scheduler/anchor_loop.py` L3116(读具名键 realised_pnl / by_type / by_type_asset / non_usdt_assets / truncated / external_flow / realised_components); `ops/reprice_day.py` L146(同, 具名键); `live/flow_window.collect`(新, 读 rows / truncated / start_ms / end_ms); 测试 `tests_income_twin_rows` / `tests_numerator_honesty` / `tests_reprice_day`(具名键) | 无人整体序列化或枚举键 ⇒ 加性安全; 三套件改后均绿(§6) |
| `daily_nav` 行 | **加** 字段 `flow_window` | 读行的: watchdog §4-2/§4-4(新读者)、`pilot_metrics.stoploss_inputs`(具名列)、`ops/daily_summary`(具名列)、`ops/reprice_day`(`dict(last)` 整行复制 ⇒ 记录随行保留, nav_ts 不变 ⇒ 记录仍对; 其重拉的 `external_flow_usdt` 换过窗口, 身份检查对 `repriced_at` 行跳过并注明)、`ops/first_real_anchor`(具名列)、`pilot_log.validate`(只查必填/非空, 允许新增) | 安全 |
| `external_flow_usdt` | **不变**(仍是自然日 TRANSFER 数量和) | `ops/daily_summary`(自然日差分, 已知其为累计)、watchdog 旧路径(仅无记录行) | 未动; 新路径不读它(身份检查除外) |
| watchdog `evaluate()` 输出 | cond2/cond4 明细**加**键; 每日状态串对新行可为 `flow window UNKNOWN: …`; cond2 `caliber` 串末尾加一句 | `scheduler/run_anchor.py` L628(读 `recent_day_pct`)、L662(`conditions_blind` 页报)、`ops/resume_from_trip.sh`(`conditions_blind` / `tripped`)、`ops/first_anchor_review` / `ops/rejudge_ledger_rows` / `ops/unseed_rehearsal_halt`(读 blind / tripped / triggers)、`tests_threshold_roles`(源码子串 `"recent_day_pct": recent`, 未动)、`tests_guard_calibers`(`"STARTING" in drawdown_caliber`, 保留) | 语义键不变; 新行的 `recent_day_pct` 变为流量调整后的数(即本修复的目的) |
| `BinanceBroker.nav_valuation`(新) | — | 仅 `flow_window.collect` | 新 |
| `_WEIGHTS` | 加两项 | `_request_once` 限流计费; `tests_guard_coverage` 查 aggTrades 等既有项 | 加性 |

**请求成本**(部署时要知道): 每个锚的 daily_nav 块多 3 次请求 —— 缺口段 income(通常 1 页, 权重 30)、`multiAssetsMargin`(30)、
`assetIndex`(10), 合计 **+70 权重/锚**, 落在锚末尾; 09-19 08Z 锚全锚峰值窗权重 1316/2400(anchor_runs.log 该行)。

## §4 红(409ea16)/ 绿(1c88827)证据

同一个套件 `live/tests_flow_window.py` 跑两棵树: **绿** = 提交 `1c88827`; **红** = `409ea16` 原样检出 + 只拷入 `live/flow_window.py`
与套件本身(夹具要用 `build_record` 构造记录; 看门狗、写者、broker 都是旧的)。409ea16 上 **6/22 通过, 退出码 1**; 1c88827 上 **34/34, 退出码 0**。

| 格 | 场景(账户真值) | 409ea16 读数 | 1c88827 读数 |
|---|---|---|---|
| 0a | 旧行(无记录), −0.50% | −0.50% 不触发 | 同 ✓(两树同) |
| 0b | 旧行, 划转日 | blind「transfer day」 | 同 ✓ |
| 0c | 新行无流量 −0.50% | −0.50% | −0.50% ✓ |
| 0d | 新行普通 −4.50% | **触发** §4-2 | **仍触发** ✓(不削弱) |
| **1** (i) | D1 22:00 缺口出金 −10,000, 当日真实 P&L −300 | **−10.30% 触发 §4-2**; §4-4 −10.3 | −0.30% 不触发; 两个 D2 行都携带该事件只计一次; §4-4 −0.3001(划转日规则) |
| **1b** (i) | 缺口出金 −30,000 | **触发 §4-2 与 §4-4**(−30.3% < −25%) | 均不触发, −0.30% |
| **2a** (ii) | 08-05 形态: −200 USDT + 0.33275025 BNB, P&L −500 | blind(「transfer day」) | **−0.50%**, F = −200 + 0.33275025×551/0.99970002 = −16.5996(不是 −199.667) |
| **2b** (ii) | 同窗 −10 BNB / +10 USDT(数量和 0), P&L −200 | **−5.73% 触发** | −0.20% 不触发 |
| **3a** (iii) | D1 最后快照后 1 s、该行拉取前 1 s 出金 −6,000 | D1 blind; **D2 −6.10% 触发** | D1 定价 0.00%(无流量), D2 −0.10%(事件按自身时间归 D2 窗) |
| **3b** (iii) | 首日, 划转都在首行之前(08-01 形态) | blind | 定价 +0.366% |
| **4a** (iv) | 缺口 BNB 出金, 收盘行无 BNB 计价率 | **−5.74% 触发** | UNKNOWN「flow n1 is −10.0 BNB: no valuation — no BNB rate on the row」, blind, 不触发 |
| **4b** (iv) | 收盘行计价读取失败(503)+ 缺口出金 | **−10.30% 触发** | UNKNOWN「closing row: no valuation on the row (… 503 …)」 |
| **4c** (iv) | 缺口拉取抛出 + 缺口出金 | **−10.30% 触发**; §4-4 −10.3 | UNKNOWN「coverage … pull raised」; §4-4 视作可能划转 −0.3001 |
| **4d** (iv) | 缺口内 INTERNAL_TRANSFER −10,000 | **−10.30% 触发** | UNKNOWN「unclassified income type(s) … INTERNAL_TRANSFER」 |
| **4e** (iv) | 保证金模式读不到 | 定价 −0.50% | UNKNOWN「margin mode unknown」 |
| **5a** (v) | USDTUSD 0.9998 → 0.9598, 真实 P&L −0.5% | **−4.48% 触发** | −0.50%(USDT_EQ) |
| **5b** (v) | 同上, 开盘行为本版前的旧行 | **−4.48% 触发** | UNKNOWN「unit not separable … 4.0200% off peg > ±0.50%」 |
| 5c (v) | 开盘旧行, 指数 0.9997 | −0.5100% | −0.5100%(ROW_UNIT, 与旧口径同数)✓ 两树同 |
| 6 | 行载体 −5,000 而记录日段无划转 | blind(「transfer day」) | UNKNOWN「record identity」(能力格, 两树都盲, 只有原因不同) |
| **7** | **真实** `anchor_loop.finalize_anchor` 写 4 行(假场所, 缺口出金) | 无记录; **−10.30% 触发** | 每行有记录; 缺口拉取请求为 [floor(D1 末行 nav_ts), D2 00:00Z − 1]; −0.30% |

**变异(vi)**: 13 个内存变异检查, 每个都先确认该格绿、装上变异后该格变红, 全部成立 —— 缺口事件丢弃(1 → −10.30% 触发)· 逐币改面值
(2a → F = −199.667; 2b → −5.73% 触发)· 去掉上界(3a → D1 读 +6.00%)· 无计价流量静默跳过(4a → −5.74% 触发)· 不查覆盖(4c → 触发)·
未分类并入盈亏(4d → 触发)· 不分离单位(5a → −4.48% 触发)· 容差放开(5b → 触发)· 未知模式当 USD(4e → 定价)· 去掉身份检查(6 → 定价)·
去掉去重(1 → +9.70%)· 写者去掉缺口拉取(7 → UNKNOWN coverage)。**[Z]** 四个源文件前后 sha256 相同(变异只在内存)。

## §5 真实账本影子回放(只读, 离线)

装置 `receipts/watchdog_flow_window_2026-09-19/replay_real_ledger.py` 读生产 `state/live/pilot_log` 的真实 daily_nav 行(只读), 用研究
只读收入全量 `FP3_receipts/venue_readonly_2026-09-19/INCOME_ALL_20260731_now.json`(COMPLETE)与 1m 指数 K 线缓存, 为每行合成新写者
**会写**的记录(日段 = [00:00Z, nav_ts + 3 s]、缺口段、multiAssetsMargin = true), 写进临时副本, 跑修复后的看门狗; 第二个装置
`replay_old_watchdog.py` 用 **409ea16 自己的看门狗**逐日截断复算旧读数, 与第一个装置的旧口径列逐日对照 —— **0 处不一致**。

| 量 | 409ea16 | 1c88827 |
|---|---|---|
| 天数 / 行数 | 50 / 291(08-01 .. 09-19 00:44Z) | 同 |
| §4-2 定价天数 | 42(8 个划转日 blind) | **50**, UNKNOWN **0** |
| 两者都定价的 42 天差值 | — | 中位 0.012 pp, 最大 0.053 pp(09-18: −1.7522% → −1.8048%, USDTUSD 指数当日变动) |
| 原 8 个盲日的新读数 | blind | 08-01 +0.482(流量窗内 0)· 08-02 +1.074(+36.82)· **08-05 −0.009(F = −10.61 USDT 等值, 不是 −199.667)**· 08-10 +1.262 · 08-18 +0.729 · 08-27 −0.446 · 09-03 −0.633(+62,997.81)· 09-08 −0.725(+35,007.38) |
| 身份检查(日段 TRANSFER 和 = 真实 `external_flow_usdt`) | — | 291/291 行成立 |
| §4-4 全树累计 | −2.4864% | **−2.4864%**(逐位同; 真实史上无缺口划转, 划转日集合相同) |
| 触发 | 无 | 无 |

限定: 真实拉取时刻未记录, 以 nav_ts + 3 s 代替; 保证金模式按 09-19 实测 true 外推全期; 计价率由 1m K 线插值(研究测得与账户实际率差
中位 0.1 ppm、sd 23.7 ppm)。这是**影子回放**, 不是生产行为的收据 —— 部署后的第一锚才是(§8)。

## §6 全电池(判词原文 + 退出码 + 解释器)

两次全电池都在隔离克隆里、用 `run_acceptance.sh` 原样(仓库根; L28 `PY="${ACCEPT_PY:-/usr/bin/python3}"`, **ACCEPT_PY 未设**)跑,
退出码直接取自 runner(不经管道, 写进 `.out` 末行)。**解释器**(runner 自报): `resolved=/usr/bin/python3  sys.executable=/Applications/Xcode.app/Contents/Developer/usr/bin/python3  version=3.9.6  torch=2.2.2  ACCEPT_PY=UNSET`。
**树外状态**(runner 自报): `.env=false  notify_audit_lines=1047  notify_audit_newest_age_hours=582.6 / 583.0` —— 与生产不同, 计数不可与生产计数比较。

| 运行 | 树 | 起止 UTC | 判词行(原文) | 退出码 | 套件 |
|---|---|---|---|---|---|
| 基线 | `409ea162…`(干净克隆) | 09:00:14 → ≈09:13:36 | `ACCEPTANCE: NOT GREEN — at least one suite failed (see table above)` | **1** | 161 个, 155 个 0 / 6 个非 0 |
| 改后 | `1c888279…`(已提交, 跑前 `git status` 0 行) | 09:25:52 → 09:39:26 | `ACCEPTANCE: NOT GREEN — at least one suite failed (see table above)` | **1** | 162 个, 156 个 0 / 同样 6 个非 0 |

**判读**: 逐套件退出码表两次运行**只差一行** —— 新增 `tests_flow_window 0`(日志末行 `34/34 checks passed` / `ALL PASS`)。
6 个红套件两次相同, 且每个套件的失败行逐行相同(去掉耗时后 md5 一致); 全部是**克隆的树外状态**所致, 与本改动无关:

| 套件 | 退出码 | 失败原因(日志原句摘) | 为何是树外状态 |
|---|---|---|---|
| `tests_env_loading` | 3 | `UNAVAILABLE (not a pass, not a failure of the code): … populates TELEGRAM_* on import` | 克隆没有 `.env`(记忆 KB-73 同型: 克隆 133/135 vs 生产 135/135) |
| `tests_alarm_digest` | 1 | `last-24h push discipline — only 0 readable alarms in 24h — NOT OBSERVABLE, not a pass` | 克隆的 `notify_audit.jsonl` 是 583 h 前的提交快照 |
| `tests_reject_topup` | 1 | `...and they account for ~93% of the 1131 USDT break…` / `no post-fix anchor in the tree yet — NOT OBSERVABLE` | 读真实 LIVE 账本日; 克隆的 `state/live/pilot_log` 只有提交进仓的 20260801 |
| `tests_disposition_matrix` | 1 | `NOT_OBSERVABLE: {'FLATTEN-20260801T201827Z': ['no watchdog event log']}` 等 | 需要 `state/live/watchdog/events.jsonl` 与真实平仓批次, 克隆没有 |
| `tests_break_split_wiring` | 1 | `the anchor that flattened 83 positions is CLEARED …` / SymbolFilters parsed cache | 需要真实 83 名平仓锚与过滤器缓存, 克隆没有 |
| `tests_unseal_rehearsal_halt` | 1 | `FIDELITY: … live=['cond2_day_loss'] fixture=['cond1_c_persist', 'cond7_ops']` | 该格拿**真实 LIVE 树**的 blind 集与夹具比; 克隆的 LIVE 树只有 20260801(一个旧行划转日 ⇒ 旧口径 cond2 blind), 两棵树上一样 |

⚠ `tests_unseal_rehearsal_halt` 的 FIDELITY 格**在生产上读的是运行时的真实 LIVE 树**: 部署后若某锚新口径判 UNKNOWN(例如计价端点失败),
该锚 cond2 blind, 这一格会随之变红 —— 与今天「划转日 cond2 blind 时它也会红」同一机制, 不是回归; 部署清单第 4 步读到它红时先看
`flow_window_unknown_days`。

**两次运行都会改写克隆里被跟踪的 state 文件**(DRY_RUN 入口格写 `state/watchdog/last_eval.json`、面板缓存等; 基线后 9 个被跟踪文件
改动 + 5 个未跟踪, 改后 14 行 `git status`)。每次跑完都已 `git checkout -- state/` + `git clean` 复原; 被测代码 = 提交本身
(`tree_head` 由 runner 写进 `*_interpreter.json`: 基线 `409ea162…`, 改后 `1c888279…`)。

**网络**: 协调者 2026-09-19 的规则(全电池只在静默窗、各一次、记起止与核对的 anchor_runs.log 行)见 `battery_windows.txt`。
**如实说明**: 基线是在规则到达之前启动的(09:00:14Z), 事后于 09:05:57Z 才读 `anchor_runs.log`, 其末行 `2026-09-19T08:55:09Z anchor done rc=0`
早于启动, 所以基线落在静默窗内, 但「启动前核对」这一步当时没有做; 改后那次是启动前核对的(09:25:47Z)。
两次全电池之间, 我在**网络被硬断**的条件下(`http(s)_proxy`/`ALL_PROXY` → `http://127.0.0.1:9`, 任何 urllib 请求在本机即被拒)单独跑过
被改动的套件(`tests_flow_window` / `tests_imports` / `income_callers` / `gate_coverage` / `tests_static_names`)以及与改动代码相关的
23 个套件(另在改口径串后复跑了其中 5 个与 `tests_threshold_roles`; `tests_watchdog`、`tests_cond2_stale_day`、`tests_guard_calibers`、`tests_numerator_honesty`、`tests_cond4_amended_transfer_day`、
`tests_income_twin_rows`、`tests_reprice_day`、`tests_binance_broker`、`tests_daily_summary` 等, 日志在 `preverify_netblocked_logs.tar.gz`; 其中 `tests_position_break_blindspot` 按其设计**只读**生产的 `state/testnet/pilot_log`)。
后者严格说不是「我改过的套件」; 我这样做是为了不浪费唯一一次改后全电池, 并以硬断网保证零请求到达交易所 —— 其中 `tests_signal_and_loop`
在 DRY_RUN 下会真去取 `bookTicker`, 于是在断网下崩溃(`URLError: [Errno 61] Connection refused`, 证明断网生效、请求未出本机), 它的
判词以改后全电池为准(退出码 0)。若协调者认为这超出了规则的字面, 以此处记录为准。

## §7 行为变化与残余(不静默)

**对新写的行(部署之后)行为有变的地方, 全部列出**:
1. §4-2 在有流量的日子**定价**(以前一律 blind)。真实史上这会让 8 个 blind 日变为有读数; 恢复门在这些日子不再因 cond2 blind 拒绝 ——
   这是 M2-33 的既有逻辑, 不是新放宽。
2. §4-2 普通日读数变为 USDT 等值(真实史上与旧读数差 ≤ 0.053 pp)。阈值未改, 所以相当于把判据从「USD 权益变化」校正为「USDT 盈亏」。
3. §4-2 **新增的 UNKNOWN 来源**: 缺口段/日段拉取失败或截断、计价读取失败、未分类收入类型、保证金模式读不到、记录与载体不符。
   以前这些情形(除截断外)会**假定流量为 0 照常定价**(`float(None or 0.0)`)。代价: 例如计价端点一次失败会让该锚 §4-2 blind(下一行即恢复);
   新收入类型会让 §4-2 blind 直到在 `flow_window.PNL_INCOME_TYPES / FLOW_INCOME_TYPES` 里分类。**这是「未知不是零」的刻意取舍。**
4. §4-4 在「证不出窗内无划转」时走划转日规则(以前按 nav 比值); 若该日 realised 也不可用则按既有规则 `chain_broken` ⇒ blind。
   真实史 0 个这样的日子(291 行 0 行拉取失败、0 行截断)。
5. 部署当天第一扇窗的开盘行是旧行(无计价率) ⇒ basis `ROW_UNIT`, 数与旧口径同式(控制格 5c); 下一天起 `USDT_EQ`。

**残余 / 未验证**:
- 入账延迟(§1 声明②)在生产上未测; 若场所对 TRANSFER 入账有秒级以上延迟, 快照前数秒的划转对该锚不可见(与 409ea16 同)。
- `assetIndex` 的 `bidRate` 是读取时刻的率, 比快照晚数秒至数十秒(允许 ≤ 600 s); 未在生产上与账户实际率逐行对比。
- §4-4 单位未分离(§1 声明⑤)。
- 新套件所有格都是合成树或进程内假场所; 真实数据上的证据只有 §5 的影子回放。
- 本电池在克隆里跑: 克隆无 `.env`、状态树是提交时快照(pilot_log 只有 20260801), 与生产树外状态不同, 计数不可与生产的计数直接比较(§6)。
- 执行器仓 `docs/API_SEMANTICS.md` §3 表(L81)仍写 `multiAssetsMargin`「还没用」、§5 写「尚未接线」—— 对 `arm()` 断言仍然成立, 但它现在已被每行读取(§1b 表 L49 已写明)。为不在电池之后改树, 本提交未改这两处旧句; 部署时可顺手更正(纯文档, 不影响任何套件判词以外的东西 —— `tests_imports` 只要求端点出现在文档里)。

## §8 部署清单(给 lead; 本文件不执行任何一步)

0. **前置**: `git -C ~/dl_quant_live rev-parse HEAD` 仍为 `409ea16…`(否则在新 HEAD 上重做 §4 与 §6)。本会话 09:3xZ 只读核对(`git --no-optional-locks status`, 不写索引): 生产工作树 638 行改动/未跟踪, 除 `state/` 外只有 `.rollback_latest`、两个 `rollback_*` 目录、`staging_batch1/`、`staging_s2gen/`; 对本补丁 10 个文件的 `status -- <10 个路径>` 为空 —— 部署前再核一次。
1. **静默窗**: 与本次电池同规则 —— 某锚 `anchor done` 行出现之后、N+3:40 之前, 且剩余 ≥ 20 分钟才开始; 记下核对的 anchor_runs.log 行与 UTC。**不要在 N+0:00..N+0:55 之间动**(执行器 N+24:00 起读书交易, 末尾写 daily_nav)。
2. **搬入**: 只经 `ops/safe_commit.sh`(CLAUDE.md: 执行器改动只经 safe_commit + 电池全绿)。补丁 `receipts/watchdog_flow_window_2026-09-19/0001-watchdog-flow-window-1c88827.patch` 用来还原出与 1c88827 **同一棵树**: 已在 409ea16 的干净检出上 `git am` 验证, 应用后树 sha = `e03bebbb6935b2aeb7818ef30da14d97274ef33b` = 提交 1c88827 的树; 共 10 个文件, 2 个新建。
3. **三方 sha 核对**(E-0917-E 教训): 对 10 个文件逐个打印 生产盘上 / 补丁来源(1c88827 的 blob)/ 部署前 HEAD, 断言 生产 == 来源 ≠ 旧 HEAD(`live/flow_window.py`、`live/tests_flow_window.py` 为新文件)。`safe_commit.sh` 步骤 2 的 diff 必须非空且只含这 10 个文件。
4. **全电池**: `~/dl_quant_live/run_acceptance.sh`(仓库根; 解释器缺省 `/usr/bin/python3`, 引用计数时同时写明解释器与 `.env` 状态), 读判词行整行 + 退出码(不经管道)。期望: 生产树外状态下 `ACCEPTANCE: ALL GREEN (162/162 suites exit 0)` —— 409ea16 注册 161 个套件(本克隆基线逐行计数 161; 记忆索引记 409ea16 电池 161/161), 本补丁加 1 个。任何红 ⇒ 不部署。
5. **首锚验收**(部署后第一个锚, 写 journal):
   - 该锚每一行新 daily_nav 都有 `flow_window` 字段; `segments` 里 `gap` 段起点 = 前一日最后一行 `nav_ts` 的毫秒下取整、终点 = 当日 00:00Z − 1, `day` 段 complete; `valuation.multi_assets_margin` 为 true、`rates.USDT.bid_rate` = `rates.USDT.index` ×(1 − 1e-4)(8–9 月观测指数 0.9984–1.0002)、`rates.BNB` 存在且 bid/index = 0.95、各 `time_ms` 距 `nav_ts` 不超过数十秒;
   - `state/live/watchdog/last_eval.json` 的 `conditions.cond2_day_loss.flow_window_days` 末项: `state = PRICED`, `basis` 以 `ROW_UNIT` 开头(开盘行是旧行), 窗内无划转时 `pct` 与旧式 (nav_last − nav_prev)/nav_prev 同数; `flow_window_unknown_days` 为空; `cond4_drawdown.flow_window_days` 末项 `transfer_possible` 与旧载体判断一致(无划转 ⇒ False), `cum_return_from_start_pct` 按旧式延续;
   - 锚末尾请求数多 3 次(anchor_runs.log 的 rate_timeline 行), 峰值窗权重不越 80% 等待线;
   - 次日第一锚起 `basis = USDT_EQ`。
6. **回滚**: 正向提交还原这 10 个文件到 409ea16 的 blob(`git revert <部署提交>`), 不 force push、不 amend; 已写入的 `flow_window` 字段是加性的, 旧看门狗忽略它, 不需要清理账本。回滚后同样全电池 + 首锚核对。
7. STATE 一行 + 交独立研究员复审(裁定 #5 实施顺序的最后两步)。

## §9 收据与复跑

目录 `docs/fixprogram_2026-09-13/receipts/watchdog_flow_window_2026-09-19/`(`MANIFEST.sha256` 逐文件):
- `0001-watchdog-flow-window-1c88827.patch` —— `git format-patch 409ea16..1c88827`; 在 409ea16 干净检出上 `git am` 后树 sha `e03bebbb…` = 1c88827 的树。
- `red_on_409ea16_tests_flow_window.log` —— 新套件在 409ea16(+ 仅 flow_window.py)上: `6/22 checks passed`, EXIT=1。
- `green_1c88827_tests_flow_window.log` —— 新套件在 1c88827 上 34/34。
- `battery_baseline_409ea16.out` + `battery_baseline_409ea16_suite_logs.tar.gz`; `battery_after_1c88827.out` + `battery_after_1c88827_suite_logs.tar.gz`; `battery_windows.txt`(两次全电池的起止 UTC 与核对的 anchor_runs.log 行)。
- `preverify_netblocked_logs.tar.gz` —— 全电池之前, 在**网络被硬断**(http(s)_proxy → 127.0.0.1:9)下单独跑的相关套件日志(见 §6 说明)。
- `replay_real_ledger.py`、`replay_old_watchdog.py`(装置, 与结论同寿命)+ `REPLAY_real_ledger_flow_window.json`、`REPLAY_real_ledger_old_watchdog.json`。

复跑(逐字; 克隆路径为本会话 scratchpad, 复跑者用自己的克隆):
```
git clone ~/dl_quant_live <clone> && cd <clone> && git checkout -b fix/watchdog-flow-window-2026-09-19 409ea16
git am <receipts>/0001-watchdog-flow-window-1c88827.patch
cd live && /usr/bin/python3 tests_flow_window.py            # 期望 34/34, ALL PASS
# 红: 在 409ea16 干净检出里只拷入 live/flow_window.py 与 live/tests_flow_window.py 再跑同一命令 ⇒ 6/22, 退出码 1
/usr/bin/python3 <receipts>/replay_real_ledger.py <修复后仓库根> ~/dl_quant_live/state/live/pilot_log \
  docs/fixprogram_2026-09-13/FP3_receipts/venue_readonly_2026-09-19/INCOME_ALL_20260731_now.json \
  docs/fixprogram_2026-09-13/FP3_receipts/venue_readonly_2026-09-19/INDEX_KLINES_1m_OHLC_cache.json <out.json>
/usr/bin/python3 <receipts>/replay_old_watchdog.py <409ea16 检出根> ~/dl_quant_live/state/live/pilot_log 1789778699.5690491 <上一步 out.json> <out2.json>
```
(`INCOME_ALL_20260731_now.json` 以 `.gz` 入库, 复跑前 `gunzip -k`; 真实账本会继续增长, 装置按 09-19 00:44Z 与收入全量终点截断。)
