> **创建:** 2026-08-01 08:38 UTC | **Session:** 0C (审计角色) | **状态:** final | **作废条件:** (a) 实盘首锚未按 challenger 权重执行, 或执行后又改回 champion —— 则本记录描述的偏离未发生, 应作废重写; (b) §56-3(3) 四条判据被 team-lead 正式修订 —— 则本记录比对的是旧判据, 须与新判据并列保留而非替换; (c) n≥250 达成后出具正式判定 —— 本记录降级为过程留痕, 不再是"当前状态"。

# 预注册偏离记录 —— 权重切换 (champion → challenger) 提前执行

**性质:** 这是一份**偏离记录**, 不是判定。§56-3(3) 的四条判据**没有全部达标**; 切换是**用户下达的裁定**(第二次重申), 在 n=174/250 时**提前执行**, **非判据触发**。本文件不评判该不该切, 只做三件事: 照抄判据并逐条给读数、核验判据不会被自己的执行掏空、量化耦合风险。

**本文件不重跑回测、不重估 Sharpe、不改任何冻结判据。** 唯一的新计算是 t_eff 的只读重算(见 §1.1)与订单数的产物差分(见 §3), 两者都从**已持久化的产物**读, 不重跑信号链。

---

## 0. 事实基线

| 项 | 值 | 来源 |
|---|---|---|
| champion 权重 | king .30 / s2 .10 / funding .30 / size .30 | `engine/live/challenger.py:38` |
| challenger 权重 | king .50 / s2 .17 / funding .17 / size .16 | `engine/live/challenger.py:39` |
| 影子切片 | n=174 锚 / 29 天 / 2026-07-01T00:00Z → 2026-07-29T20:00Z | `exports/live/challenger/compare.json` (jpline, 写于 2026-07-31T09:09Z) |
| 上一次冻结读数 | n=156, t_eff 5.657 | `exports/eda/challenger_gate_readings_2026-07-29.json` |
| 管线状态 | run_daily 2026-07-31 status=ok, 9/9 验收套件绿 | `exports/live/monitor/last_run.json` |

**读数新鲜度警示:** compare.json 由 2026-07-31T09:09Z 那次 run_daily 写出, 覆盖到 2026-07-29T20:00Z 的成熟锚点。2026-08-01 的 run_daily 在本文件写就时尚未运行(它跑在 09:00Z 之后)。⇒ 下面所有影子读数的**新鲜度是 2 天**, 不是当天。

---

## 1. 判据原文与逐条读数

### 判据原文(照抄 `multi_asset/exports/eda/audit_2026-07-25.md` §56-3(3), 一字未改)

> **(3) 换权重四条同时满足**: ΔIC>0 且 t_eff≥3 且样本≥250锚 / 日胜率≥0.60 / 至少一个 n≥10 stress 分层 challenger 不劣 / 换手≤1.5 且用实测成本重做净成本检验。**当前胜率 0.77✓ 换手 1.39✓ 样本不足✗ stress=0 结构上无法评估✗ ⇒ 换权重被 stress 与样本量阻断, 不被 IC 证据阻断; §2.4 保持 champion 不是惰性而是这两条缺口。**

> **(4)** `infl = 1+2Σ_{k=1..12} max(ρ_k,0)`, `t_eff = t/√infl`, 必须同报原始 t 与 t_eff, 判定用 t_eff; 该估计量正偏、保守是刻意的, **禁止末尾改用更宽松估计量。**

> **(5)** stress 仍为 0: 不阻塞启动, **阻塞加规模与换权重**; 强制登记"窗口内无事故"永不得读作"已通过逆境检验"。

**另有一条独立的、写在生成器里的样本门(不在 §56-3(3) 内, 但同属预注册, 一并照抄):**

> `challenger.py:246` 每日报告固定输出: **"29 shadow days so far; the pre-registered rule needs >=60 before a switch may be proposed."**
> `track_matrix.py:55/62/70` 三条比较各自 `"min_days": 60`; 且 `track_matrix.py:86-87` `GENERALISATION.not_a_substitute`: **"generalisation is a SEPARATE observation. It cannot rescue a comparison that failed its own criteria, and it cannot be used to shorten min_days."**

### 逐条读数 (n=174)

| # | 判据(原文分句) | 当前读数 | 达标 |
|---|---|---|---|
| 1a | ΔIC>0 | **+0.03886** (champion 0.05742 → challenger 0.09628) | ✅ |
| 1b | t_eff≥3 | **t_raw 7.813 → t_eff 6.278** (infl 1.5492) | ✅ |
| 1c | 样本≥250 锚 | **174** | ❌ (缺 76 锚) |
| 2 | 日胜率≥0.60 | **0.7931** (23/29 天) | ✅ |
| 3 | 至少一个 n≥10 stress 分层 challenger 不劣 | **n_stress = 0** (btc_rvol>18.0 bps/min 的锚点一个都没出现) | ❌ **结构性不可评** |
| 4a | 换手≤1.5 | **1.402** (每锚 0.6336 → 0.8886) | ✅ |
| 4b | 用**实测成本**重做净成本检验 | **无实测成本** —— 管线出具的 `c_bps_overall = 3.6135` 其 caliber 逐字为 `"SHADOW/MOCK — simulated fills, no account, no venue contact"` | ❌ **不可评** |
| — | (生成器内) 影子天数≥60 | **29** | ❌ |

**四条中: 达标 4 个分句(1a/1b/2/4a), 未达标 4 个分句(1c/3/4b/60天)。判据是"四条同时满足", 现状是四条各有一半。**

### 1.1 t_eff 在 n=174 的重算 (§56-3(4) 定义, 未换估计量)

重算方式: **只读**。从**已持久化的持仓产物**(`exports/live/positions/*.json` 与 `exports/live/challenger/positions/*.json`, 各 174 个文件, curve `B_backfilled_4leg`)配合面板 `Y4` 逐锚点算 `xsec_rank_ic`, 再作差。**没有重跑信号链, 没有重跑回测。** 探针: `/tmp/teff_probe_174.py` (jpline)。

保真校验(重算 vs `compare.json` 持久值):

| 量 | 重算 | 持久值 | 一致 |
|---|---|---|---|
| mean_d_ic | 0.03885 | 0.03886 | ✅ (末位舍入) |
| mean_ic_champion | 0.05742 | 0.05742 | ✅ |
| mean_ic_challenger | 0.09628 | 0.09628 | ✅ |
| t_raw | 7.813 | 7.81 | ✅ |

⇒ 逐锚点序列与 `challenger.py` 的 IC 循环等价, 重算可用。

```
n        = 174
sd       = 0.06560  (ddof=1, 与 challenger.py 的 pandas .std() 同口径)
t_raw    = 7.813
ρ_1..12  = -0.0680 -0.0621 +0.0717 -0.0217 -0.0322 -0.1438
           -0.1428 +0.0110 +0.1369 -0.1223 +0.0211 +0.0339
infl     = 1 + 2·Σ max(ρ_k,0) = 1 + 2·(0.0717+0.0110+0.1369+0.0211+0.0339) = 1.5492
t_eff    = 7.813 / √1.5492 = 6.278
```

与 07-29 冻结文件对照: n 156→174, t_raw 7.193→7.813, infl 1.6166→1.5492, **t_eff 5.657→6.278**。判据线 3 未被逼近, **IC 证据这一条比 3 天前更强而非更弱**。

### 1.2 判据 4b 的净成本算术 (在**建模**成本下重做, 因为实测成本不存在)

从 `pnl_daily.csv` 与 `compare.json` 的持久值直接解, 不重估:

```
d_net_sum   = 0.072639 − 0.046176 = 0.026463
d_turn      = 174 × (0.8886 − 0.6336) = 44.37
FILL = 0.51, cost = 1.9 bps (n_stress=0 ⇒ 全部走 calm 支)
d_net = FILL·(d_gross − d_turn·cost·1e-4)
  ⇒ d_gross = 0.026463/0.51 + 44.37×1.9e-4 = 0.051888 + 0.008430 = 0.060318
  ⇒ 盈亏平衡成本 = d_gross/d_turn ×1e4 = 13.59 bps
```

n=156 时该值为 13.31 bps, 现为 **13.59 bps**。**但这不满足判据 4b** —— 判据要的是"用实测成本重做", 上式用的仍是 1.9 bps 建模成本。**把 3.6135 代进去也不满足**, 因为那个数自己的 caliber 字段写的是模拟成交。

**一个已变的事实, 记录但不推断:** 自 2026-07-29 起测试网有真实成交(2026-08-01 单锚 `fills.jsonl` 286 行, 前一锚 318 行)。⇒ 一个**测试网口径**的实测 c 现在**在数据上可构造**, 但 (a) 没有任何管线出具它; (b) 测试网深度不是主网深度, 它也不是判据 4b 想要的那个"实测"。**本文件不代为构造。**

---

## 2. 明写: 这次偏离放弃了什么

### 2.1 这是裁定, 不是触发

**实盘首锚使用 challenger 权重, 是用户在 2026-08-01 下达并第二次重申的裁定, 在 n=174 时执行, 距 §56-3(3) 的 250 锚门槛还差 76 锚(按 6.04 锚/天约 12.6 天, 约 2026-08-13)。判据没有触发。** §56-3(3) 末句"§2.4 保持 champion 不是惰性而是这两条缺口"所指的两条缺口(样本量、stress), **在执行时仍然存在**。

### 2.2 放弃的第一件事: n≥250 的稳定性检验

250 锚这条门不是为了把 t 推得更高 —— t_eff 早在 n=156 就是 5.657。它买的是**跨时间的稳定性**: 174 锚只覆盖 **29 天、单个日历月(2026-07)**, ΔIC 在一个 regime 内为正, 与它在多个 regime 内为正, 是两个不同的命题。放弃 76 锚 = 放弃"这个权重优势能不能活过换月"的那次检验。

**该检验此后仍可做, 但代价变了:** 影子双轨会继续跑到 250 锚(见 §3 前的核验结论: 双轨在切换后仍独立), 所以证据会照常累积。**变化的是它的角色** —— 250 锚到达时, 它不再是"要不要切"的前置判据, 而是"切了之后要不要退回"的事后检验。**这两者的举证责任方向相反**, 记录在此, 免得届时把一个"退回门"当成"准入门"来读。

### 2.3 放弃的第二件事: 压力层从未被测 —— **但这是两条腿共有的空白**

`n_stress_anchors = 0`: 定义为 `btc_rvol > 18.0 bps/min` 的锚点在 174 个锚里**一个都没有出现**。这不是 challenger 表现差, 是**测量从未发生**。

**★ 必须点明的对称性: 这个空白不是 challenger 独有的缺陷。** champion 在同一 174 个锚上**同样**从未经历过一个压力锚。⇒ "继续用 champion" 并不因此获得任何逆境证据。§56-3(5) 已预先写死: **"窗口内无事故"永不得读作"已通过逆境检验"** —— 这条对两条腿一视同仁。

**因此本次偏离在压力维度上放弃的, 严格说是: 一个 challenger 相对 champion 在高波动下不劣的*比较*。它不是"用未经压力测试的东西替换了经过压力测试的东西"** —— 两者都没被测过。这是一次**在未知逆境行为上从一个未测配置换到另一个未测配置**。

唯一相邻的证据(**明标为不满足判据**): funding 腿最差 5% 尾部, n=**9** < 10, champion 净 −0.002362 vs challenger 净 −0.000023, 方向对 challenger 有利。**它按原文不合格**(n<10), 且"funding 腿尾部算不算 stress 分层"本身是一个定义问题, 不是读数。该尾部的 n 随样本机械增长, n=10 大约在 ~200 锚到达。

### 2.4 放弃的第三件事: 判据 4b 从未被满足过

"用实测成本重做净成本检验"这一句, **从预注册写下到今天, 一次都没有被评估过** —— 因为不存在实测成本。切换发生时, 该条既非通过也非失败, 而是**始终未评估**。盈亏平衡余量 13.59 bps vs 建模 1.9 bps(7.2×)、vs 模拟 3.61 bps(3.8×)看着宽, **但两个分母都不是判据要的那个量。**

---

## 3. 【交付 2】核验: 判据会不会被自己的执行掏空

**是非题: 线上把部署权重换成 challenger 之后, 影子双轨是否仍然独立跑两套权重?**

## 答: 是, 仍然独立。ΔIC 不会结构性归零。

### 3.1 代码证据

| 文件:行 (jpline `.../quant_research_multi_asset/multi_asset/`) | 内容 | 含义 |
|---|---|---|
| `engine/live/challenger.py:38` | `CHAMPION = {"king": 0.30, "s2": 0.10, "funding": 0.30, "size": 0.30}` | champion 臂的权重是**模块内字面量** |
| `engine/live/challenger.py:39` | `CHALLENGER = {"king": 0.50, "s2": 0.17, "funding": 0.17, "size": 0.16}` | challenger 臂同样 |
| `engine/live/challenger.py:73-74` | `champ4 = _positions_w(src, anchors, CHAMPION)` / `chall4 = _positions_w(src, anchors, CHALLENGER)` | **两臂各自现算**, 都不读任何持仓产物 |
| `engine/live/challenger.py:46` | `chain = SignalChain(src, weights=weights, ...)` | 权重**显式传入** |
| `engine/signal_chain.py:44` | `self.w = dict(weights or DEFAULT_WEIGHTS)` | 显式传入 ⇒ `DEFAULT_WEIGHTS` **不参与**。改 `DEFAULT_WEIGHTS` 影响不到 challenger.py 的任何一臂 |
| `engine/live/challenger.py:33` | `CHAMP_POS = MA + "/exports/live/positions"` | **定义后全文再无引用**(`grep -n CHAMP_POS` 只命中第 33 行) ⇒ 影子的 champion 臂**不从部署产物读** |
| `engine/live/track_matrix.py:36-37` | `W_CHAMP = {...0.30...}` / `W_CHALL = {...0.50...}` | 四轨矩阵同样硬编码, 同样免疫 |
| `engine/live/fixfunding_track.py:38` | `WEIGHTS = {"king": 0.30, ...}` | 第三轨权重**冻结在 champion**(见 §3.3, 这条会产生一个副作用) |

**⇒ 影子里没有任何一条腿是从"当前部署配置"读权重的。判据不会被自己的执行掏空。**

### 3.2 ★ 但发现一个**方向相反**的执行保真隐患: 按 `config/book.json` 切换是**空转**

判据不会被掏空, 但**切换动作本身有一个会静默失效的路径**, 属于"裁定给出的是性质而不是动作"那一族:

| 文件:行 (`~/dl_quant_live/`) | 内容 |
|---|---|
| `config/book.json:3` | `"weights": {"king": 0.3, "s2": 0.1, "funding": 0.3, "size": 0.3}` |
| `scheduler/anchor_loop.py:932` | `book = LG.compose_book(king, s2, fund, dvol)` ← **没有传 weights 参数** |
| `signal/legs.py:122` | `w = dict(weights or WEIGHTS)` ← 因此回落到模块字面量 |
| `signal/legs.py:33` | `WEIGHTS = {"king": 0.30, "s2": 0.10, "funding": 0.30, "size": 0.30}` ← **这才是实际下单用的权重** |
| — | `grep -rn '"weights"' live/ signal/ scheduler/ ops/`(去掉 tests_) ⇒ **零命中**。`config/book.json` 的 `weights` 键**没有任何读者**。`live/book_config.py` 只读 `anchors_utc` / `anchor_late_tolerance_min` / `panel.*` / `target_leverage` / `gross_usdt_pilot_p0` / `expected_leverage_bracket`。 |
| `live/frozen_inputs.py:106` | 却把 `config/book.json` 描述为 `"the OPERATING config: weights, caps, schedule, gross"` —— **文档声称它带权重, 代码不读它。** |
| `live/frozen_inputs.py:81-83` | `"The rest of book.json is deliberately NOT pinned: weights, caps and schedule are operating decisions"` ⇒ **权重变更不受任何 pin 保护, 也没有任何测试断言 `legs.WEIGHTS` 与 `book.json["weights"]` 一致。** |

**⇒ 若切换以"改 `config/book.json`"的方式执行, 书照旧按 champion 权重下单, 而配置文件、以及任何引用该配置的记录, 都会声称是 challenger。没有守卫会发现。**
**⇒ 切换必须改 `signal/legs.py:33 WEIGHTS`(或给 `anchor_loop.py` 的 `compose_book` 调用显式传参)。改完必须验证**下单**权重, 不是验证配置文件。**

**★ 行号是移动靶, 以不变量为准:** `scheduler/anchor_loop.py` 在本次审计期间正被并发修改(`git status` 显示 `M`, mtime 2026-08-01 08:37Z; 同一处调用在我相隔约 12 分钟的两次 grep 中从第 926 行移到第 932 行)。上表行号是 08:37Z 的读数。**不随行号变动的那件事是: 该调用不传 `weights` 参数, 因此实际下单权重来自 `signal/legs.py:33`。核验时请按符号找, 不按行号找。**

### 3.3 ★ 切换后会出现的两个口径分裂(不掏空判据, 但会掏空**监控**)

**(a) 部署持仓产物不盖权重章 —— 切换后无法从文件回答"这一锚是哪套权重产的"。**
实测两臂产物的键:

```
exports/live/positions/positions_20260729_20.json           键: anchor_ts_ms anchor_utc horizon_h schema track factor_version panel      ← 无 weights
exports/live/challenger/positions/positions_20260729_20.json 键: anchor_ts_ms anchor_utc horizon_h track weights schema                  ← 有 weights
```

champion 侧由 `signal_loop._positions` 用 `DEFAULT_WEIGHTS` 生成(`signal_loop.py:154-156`)。切换后若同步改了 `DEFAULT_WEIGHTS`, `exports/live/positions/` 会**静默变成 challenger 权重的书, 文件里没有任何一处记录这件事**, 而 `track` 字段仍写着 `"champion"`。这正是 §57-S5 已登记、至今未修的缺陷, 切换会把它从"读不出旧文件的版本"升级为"**新旧文件同名同 track 但是两本不同的书**"。

**(b) 因子健康/衰减判定会落到一条不是我们在交易的曲线上 —— 又一次。**
`state/factor_health_last.json` 实测 `"caliber": "champion_fixfunding"`, 而 `fixfunding_track.py:38` 的 `WEIGHTS` 冻结在 champion。⇒ **切换后, 衰减告警测的是 champion 权重的书, 交易的是 challenger 权重的书。** 这与 §56-1(3) 记录过的那次(告警读 `A_provisional_3leg`, 一条不含 funding 腿的曲线)是**同一族缺陷的第二次发生**。§2.5.4 的窗口末尾复核序列(决策序列 = fixfunding 修正四腿)同理: **切换后, 那条预注册的决策序列不再是部署口径。**

**注: (b) 不是切换制造的新错, 而是切换使一个已存在的口径分裂重新变得 load-bearing。修法便宜(给 fixfunding_track 增开一条 challenger 权重的曲线, 或明写它测的是因子不是权重), 但必须在切换生效前决定, 否则窗口末尾会拿一条错口径的曲线做决策。**

---

## 4. 【交付 3】耦合风险定量: 换手 1.402× 对下单/撤单与限流预算的影响

### 4.1 观测基线 —— 2026-08-01T08:00Z 那一锚 (`rebalance_id A1785571266`, 测试网, champion 权重)

来源: `~/dl_quant_live/state/testnet/pilot_log/20260801/{anchors,orders}.jsonl` 与 `state/anchor_runs.log:12106,12162,12163`。

| 量 | 值 |
|---|---|
| target_gross / realized_gross | 8,737.45 / 8,356.8 USDT |
| 目标名字数 | 110 (maker 行 109, 另 1 未成行) |
| maker: 提交 | **97** = 89 `partial_expired` + 8 `venue_reject` |
| maker: 未提交 | 12 = 11 `skipped_min_notional` + 1 `skipped_no_mid` |
| k-cancel DELETE | **89** = 22 `cancelled` + 65 `already_terminal` + 2 `errors`(-1003) |
| top-up: 提交 | **37** = 23 `filled` + 14 `abandoned_max_attempts` |
| top-up: 未提交 | 52 `skipped_min_notional` |
| `orders_spent` | **223** —— 恒等式 **97 + 89 + 37 = 223 精确成立** |
| `requests_spent` | **757** ⇒ 非订单读请求 = 757 − 223 = **534** |
| `weight_spent` / waits | 5,745 / 4 次, 累计 **202.38 s** |
| **peak/min: weight / orders / requests** | **1000(自设上限, 已顶格) / 97 / 270** |
| 场所侧(仅记录) | `peak_window_weight = 6152` vs testnet 公布 6000/1m; `gap_vs_this_process = 6127`, 归因 **UNVERIFIED**(被封 IP 130.176.187.110 是 CloudFront 边缘, 非我方出口 103.252.201.68) |

**峰值由哪个 burst 决定 —— 用时间戳坐实, 不靠数字巧合:** `submit_ts` 逐分钟统计 = **08:01 分 89 个 maker**(另 8 个 `venue_reject` 无 `submit_ts`, 同分钟)⇒ **97 = maker 提交 burst, 就是 peak orders/min 那一分钟。** top-up 23 个落在 08:18 分, 与峰值不同分钟。

### 4.2 关键机制: **订单数由广度决定, 不由换手量决定**

`binance_executor.py:52` `DEFAULT_BAND_BPS = 0.0` ⇒ **无免交易带**。唯一的过滤是 min-notional 与 lot 取整(`binance_executor.py:498-517`)。⇒ 每锚的订单数 = **|Δnotional| 越过各自 min_notional 的名字个数**, 而不是 Σ|Δw|。

在 gross ≈ 8,737 USDT / 110 名字下, 单名中位敞口约 $79, 而典型 |Δw|×G 远高于 5 USDT 的地板 ⇒ **两套权重都近乎每锚全书重挂**。换手涨 1.402×, 涨的是**单笔大小**, 不是**笔数**。

### 4.3 增量 —— 两种独立算法

**算法 A (主, 用 challenger 自己的书):** 从 174 个锚的**已持久化持仓产物**逐锚差分(curve B 四腿), 按 G = 8,737.45 与 `exchange_info_cache.json` 的逐币 min_notional 数越界名字数。

```
                     每锚越界名字数            L1 换手(校验用)
champion             mean 100.10  median 101  max 109      0.6302
challenger           mean 102.83  median 104  max 110      0.8850
比值                 1.0273                                 1.4043
绝对增量             +2.73 名/锚
```

**校验: L1 比值 1.4043 复现 compare.json 的 1.402(差 0.2%)** ⇒ 该产物差分与影子自身的换手口径一致, 因此同一差分得出的名字数可信。

**算法 B (旁证, 用今天的真实订单向量):** 取今天 08:00Z 那 109 个 maker 行的 `|intended_notional|`, 整体乘 1.402, 数越界:

```
scale 1.000 -> 99 / 109 越界   (实测未提交 11 个 min_notional ⇒ 98, 差 1, 属 lot 取整边界, 可接受)
scale 1.402 -> 104 / 109 越界   ⇒ +5, 比值 1.051
```

**两法给出的 maker 增量: +2.7 (A) 到 +5.0 (B) 笔/锚。**

### 4.4 逐分项增量

| 分项 | champion 实测 | challenger 估计 | 绝对增量 | 倍数 |
|---|---|---|---|---|
| maker 提交 | 97 | 99.7 – 102.0 | **+2.7 – +5.0** | 1.027 – 1.051 |
| k-cancel DELETE | 89 | 91.5 – 93.6 | **+2.5 – +4.6** | 同上(挂单数随 maker 提交数走) |
| top-up 提交 | 37 | **不可从产物推定** —— 点估 +1, 上界 +52 | **+1 – +52** | 1.03 – 3.4 |
| **每锚订单总数** | **223** | **229 (点估) – 285 (上界)** | **+6 – +62** | **1.028 – 1.276** |
| 每锚请求总数 | 757 | 763 – 819 | +6 – +62 | 1.008 – 1.082 |

**top-up 那一格为什么给区间而不给点估(不足之处, 明说):** top-up 的下单量是 maker 部分成交后的**残差**, 它取决于成交动态, 不在任何影子产物里。把今天的 top-up `intended_notional` 向量乘 1.402 只让越界数从 23 变到 24(+1), **但当天实际提交了 37 笔而我按同一地板只数出 23 笔 ⇒ 该向量与"是否提交"的对应关系我没有核实, 因此这个 +1 的点估未经验证。** 上界取"当前被 min_notional 挡下的 52 笔全部越界"=+52。**这一格数据不足以给出可信点估。**

### 4.5 推到限流预算的峰值

峰值由 maker burst 决定(§4.1 时间戳已坐实), 该 burst 的规模 = maker 提交数:

| 预算维度 | 自设上限 | 今日峰值 | challenger 峰值 | 占用率 |
|---|---|---|---|---|
| orders/min | 300 | 97 (32.3%) | **99.7 – 102.0** | **33.2% – 34.0%** |
| requests/min | 600 | 270 (45.0%) | **272.7 – 275.0** | **45.5% – 45.8%** |
| requests/min (top-up 上界情形, 若 +52 落在同一分钟) | 600 | 270 | ≤ **331.6** | ≤ **55.3%** |
| weight/min | 1000 | **1000 (已顶格)** | **仍是 1000** | 100% (不变) |

**weight 维度是特殊的, 单独说: 它今天已经顶在自设上限 1000, 由整形器压住(4 次等待, 累计 202.38 s)。⇒ challenger 的增量不会抬高 weight 峰值, 它转化为更长的等待。** 按今日均值 5,745 weight / 757 requests = **7.59 weight/request**, 增量 +6 – +62 requests ⇒ **+46 – +470 weight** ⇒ 在 1000/min 的整形器下 **额外等待 +2.7 s – +28.2 s**。今日该锚全长约 330 s(08:18:04→08:23:34), 加上上界增量约 358 s, 距 `anchor_max_seconds = 1500` 仍远。

**场所侧, 只给可核的数, 不给概率:** 今天场所在对齐 1 分钟窗口上读到 6,152 weight(testnet 公布 6000/1m), 而我方同分钟自设不超过 1000, `gap_vs_this_process = 6127` 且归因写明 **UNVERIFIED**(被封的是共享 CloudFront 边缘 IP)。⇒ challenger 的 +46 – +470 weight 相当于场所所计 6,152 的 **0.7% – 7.6%**。**由于该计数器的归因未定, 不能由这个百分比推出任何封禁概率, 本文件也不推。**

### 4.6 挂单遗留(今天的具体故障)的增量

今天 2 笔撤单因 -1003 失败, 留下挂单; 挂单母体 = 89 笔 k-cancel, 失败率 2/89 = **2.25%**。**在失败率不变的假设下**, challenger 的挂单母体 91.5 – 93.6 ⇒ 预期失败 **2.06 – 2.10 笔**, 增量 **+0.06 – +0.10 笔/锚**, 可忽略。

**★ 但这个假设正是最值得怀疑的一条(不足之处, 明说): 07-29 / 07-30 / 07-31 / 08-01 四次 -1003 全部落在 k-cancel burst 上。⇒ 失败率与请求数并不独立。四个事件不足以估计这个依赖关系, 因此上面那个"+0.06 – +0.10"只在"失败率与规模无关"这个已被四次事件质疑的前提下成立。**

### 4.7 ★ 一个测不出来的量(必须记, 因为它正是最关键的那个)

**k-cancel burst 的每分钟速率, 从我们自己的订单账本读不出来。** `cancel_ts` 逐分钟统计给出 08:16 分 72 个 + 08:17 分 **102** 个 = 174 个; 但 (a) k_cancel 报告的 DELETE 调用只有 89 个, (b) 进程自计的 peak orders/min 是 97 < 102。⇒ **`cancel_ts` 不是逐次调用的发出时刻**(更像批量落账时刻)。

**这意味着: 四次封禁全部发生在 k-cancel burst, 而这个 burst 的瞬时速率恰恰是我们的记录唯一无法测量的那一个。** 上面 §4.5 关于峰值的所有结论都建立在 maker burst 上(那个有 `submit_ts` 可坐实); **k-cancel 那一侧我只能给规模(89→91.5–93.6), 给不了速率。** 这不是本次切换造成的, 但换权重会把这个母体推大 3–5%, 而我们没有尺子看它推到了多快。

---

## 5. 未单独核实(明标)

1. 影子 compare.json 的新鲜度为 2 天(覆盖到 07-29T20:00Z); 08-01 的 run_daily 尚未运行。
2. §56-3(3) "样本≥250锚"我按 challenger 影子切片(现 174)读; 协议未在别处给出第二种样本定义, 但我也未穷举核对。
3. `challenger.py:18` 的 docstring 指向 `exports/live/challenger/README.md` 作为预注册判据所在 —— **该文件在 jpline 上不存在**(该目录只有 compare.json / daily_report.md / pnl_daily.csv / positions/)。因此本文件照抄的是 `audit_2026-07-25.md` §56-3(3) 与生成器内联的 60 天门。**指针悬空, 但被指向的判据本身在别处有据。**
4. funding 腿 p05 尾部是否构成"stress 分层", 是定义问题, 不是读数, 本文件不裁。
5. top-up 提交数的模型未经验证(§4.4)。
6. k-cancel 的每分钟速率不可测(§4.7)。
7. 测试网 min_notional 地板与主网可能不同; §4.2–4.4 的越界计数用的是测试网 `exchange_info_cache.json`。
