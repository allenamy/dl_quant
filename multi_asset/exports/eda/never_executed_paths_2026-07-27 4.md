# TESTNET never-executed path inventory + funding-crossing pre-registration

> **创建:** 2026-07-27 06:20 UTC | **Session:** 0C | **状态:** final (pre-registration — written BEFORE the paths run) | **作废条件:** 每条路径首次执行并被判读后, 该条转为"已执行, 见判读"

**只读产出**: 三天日志 + 代码反推, 未改动任何树。

---

## ★ 头号更正: 08:00Z **不是** funding 首考 —— 书在跨越那一刻是平的

lead 的派工说"16:00 重证明锚点若持仓跨过结算, 这条路径首考"。**前提不成立**, 实测:

```
最新 position_readback : 2026-07-27T04:15:48Z   109 行   Σ|notional| = 0.00   非零仓位 0
今日已跑锚点            : 00:18Z(trip) · 04:15Z            ← 注意都在整点后 15–18 分
```

结算在 **08:00:00.000Z 这一瞬**发生, 而 08:00Z 锚点的下单发生在它**之后**(锚点约 08:15Z 才跑)。⇒ **08:00:00 那一刻账户是平的, 该结算不会产生任何 income**。

> **⇒ funding 首次真跨越是 12:00Z 锚点**(为 12:00:00Z 结算定价, 用 08:00Z 锚点写下的 readback —— 那是重证明开出的第一本书)。
> **⇒ 08:00Z 锚点仍然值得看**, 但它的预期读数是"再一次 income=0", 而**那不是首考通过, 是首考没发生**。把它当首考通过, 就是把"条件没出现"读成"条件通过了" —— 本项目今晚已经记过这个形态三次。

### 结构事实: 每一个锚点小时都撞在结算瞬间上

```
anchor_hours = (0, 4, 8, 12, 16, 20) UTC      anchor_interval_s = 14400 (4h)
4h 结算: 00 04 08 12 16 20      8h 结算: 00 08 16
⇒ 六个锚点全部与 4h 结算重合; 其中三个同时与 8h 结算重合。
```
这不是巧合而是设计, 但它有一个后果值得写下来: **每一次结算都恰好落在"本锚点的 readback 还没写"与"上一锚点的 readback 已 4h 老"之间**, 也就是 `positions_at` 两侧断言的正中间。

### 预注册: funding 首次真跨越 (12:00Z 锚点) 的预期读数

`positions_at` 的两侧断言会这样读 (`live/binance_funding.py:208`):

| 断言 | 12:00Z 结算的实际取值 | 判读 |
|---|---|---|
| (i) readback 必须**严格早于**结算瞬间 | 本锚点 readback ≈ 12:15Z ⇒ **排除**; 采用 08:00Z 锚点的 ≈ 08:15Z | 按设计 |
| (ii) 年龄 ≤ 一个锚点间隔 (14400s) | age = 12:00:00 − 08:15 ≈ **13500s < 14400s** | **通过, 余量约 15 分** |

**⇒ 余量来自锚点滞后 15 分钟这一事实。** 注意方向: readback **越晚**, age **越小** ⇒ 锚点迟到反而更安全; 真正致命的是**上一个锚点缺席** —— 那时最近的 readback 变成 4h 前的那个, age ≈ 8h > 14400s ⇒ (ii) 拒绝 ⇒ **该结算不写行, 计入 `skipped_no_position` 并告警**。这是正确行为, 但它意味着 **一次缺席锚点会让那一轮 funding 永久无法入账**(venue income 仍在, 但我们无法为它定价)。

**预期读数, 逐项**:

```
income 行数量级 : 每个持仓 symbol 一行。109 名 × 若干非零仓 ⇒ 量级 O(10)–O(100), 不是 0 也不是数千。
                  若 income 行数 >> 非零仓位数 ⇒ 拉取窗口回溯过远(start=retention_floor), 需查。
sign 约定       : 代码 `long pays when rate>0 => income 的符号 = sign(-(pos*rate))`。
                  ⇒ 多头 + 正费率 ⇒ funding_paid < 0 (我们付); 空头 + 正费率 ⇒ funding_paid > 0 (我们收)。
                  期望 `sign=OK`; 出现 `sign=WIRING_ERROR` 即 §3f 抓到接线错误。
position_notional_at_settlement : **必须来自我们自己的 readback**, 绝不能由 paid/rate 反推
                  (反推会让 §3f 变成恒真式)。它是 schema v2 的 not_null ⇒ 定不了价的结算**不写行**,
                  而缺席被 `skipped_no_position` 计数 —— 覆盖率不会被"只统计活下来的行"粉饰。
gap 状态        : 首次写入后应从 COLD_START 转 **CONTINUOUS**。
                  (我第一版扫描找的是 `gap=OK` —— 一个代码永远不会输出的字符串; 真实取值只有
                   COLD_START / PERMANENT_GAP / CONTINUOUS。**用自己臆想的标记去证明"从未发生", 证不出任何东西。**)
sign_consistency: 仓位为 0 的行走 `abs(pos)<1e-9 -> continue` ⇒ 计入 `unverifiable`, **不计入 pass**。
                  ⇒ 若 08:00Z 真出现 income 行而书是平的, 期望 checked=0 / unverifiable=N, verdict 非 OK。
```

**如何在排练锚里主动触发**: 08:00Z 锚点正常开仓 → 不必等 12:00Z, 可在 **08:30Z 后手动跑一个排练锚**(见 §2.5.9), 它会为 08:00Z 结算重新尝试定价 —— 但仍会因"书在 08:00:00 是平的"而无 income。**真正的加速办法只有一个: 让 08:00Z 锚点开出仓位, 然后在 12:00Z 之前不要平仓。** funding 无法被排练伪造, 因为它是场所侧的现金流。

---

## 其余从未执行路径 (标记取自代码, 且在正确的语料里搜)

> ⚠ **方法学警告, 先说**: 我的第一版扫描把订单级事实(`blocked_by_halt` 等)拿去 `anchor_runs.log` 里找, 于是把一条**跑了 642 次**的路径报成"从未执行"。订单级事实住在 `pilot_log/*/orders.jsonl`。**"零命中"永远先证明标记本身能命中。**

| 路径 | 状态 | 主动触发方案 (排练锚) |
|---|---|---|
| funding 带真实仓位定价 | ★ 从未 | 见上; 只能靠真持仓跨结算 |
| funding `gap=CONTINUOUS` | ★ 从未 | 随首次写行自动达成 |
| funding `gap=PERMANENT_GAP` | ★ 从未 | 不可安全触发(需 >90 天空档); **保留为不可测路径, 明写** |
| funding sign 判决 (`OK`/`WIRING_ERROR`) | ★ 从未 | 随首次写行达成; WIRING_ERROR 只能靠故障注入 |
| `skipped_no_position` > 0 | ★ 从未 | 排练锚: 临时把 `max_age_s` 传 1s ⇒ 强制 (ii) 拒绝, 验证它**计数并告警**而不是静默 |
| preds/推理失败阶梯 | ★ 从未 | 排练锚: 指向一个不存在的 preds 路径 ⇒ 验证阶梯降级而非崩溃 |
| DERISK / 陈旧阶梯 | ★ 从未 | 排练锚: 喂一个人工陈旧的 preds 时间戳 |
| kill switch | ★ 从未 | 排练锚: touch kill 文件, 验证当锚立即停手且可清除 |
| 时钟偏移超限 | ★ 从未 | 排练锚: 注入偏移(仅 arm 检查读它) |
| 场所 -4164 (min_notional 拒单) | ★ 从未 | **我们自己的 `skipped_min_notional` 跑了 62 次, 但那是我们先拦下来**; 场所侧拒单需刻意下一笔低于 BTCUSDT 50 USDT 门槛的单 —— 与下一批"逐币 min_notional"同车验证 |
| maxQty 分块 | ★ 从未 | 需要一笔超过 `mkt_max_qty` 的市价单; 排练锚可对一个小 maxQty 币种构造 |
| 跨日 NAV 首滚(带仓位) | ★ 从未(三天 NAV 行均在平仓/停机态) | 只需 08:00Z 开仓后跨过 00:00Z |
| 进程重启恢复 | **已跑 36 次** | — |
| 离表锚点(off-schedule) | **已跑 189 次** | — |
| halt/reduce-only 拦下开仓 | **已跑 642 次** | — |
| 场所拒单 / 我方 min-notional 跳过 | **已跑 272 / 62 次** | — |

**不可安全触发者必须留名**: `PERMANENT_GAP` 与 `WIRING_ERROR` 两条**无法在排练里诚实制造**(一个要 90 天空档, 一个要真接线错误)。它们只能靠**故障注入套件**覆盖, 或者永远停留在"未演示"。**登记为不可测, 好过让它们混在"待触发"里显得迟早会被覆盖。**
