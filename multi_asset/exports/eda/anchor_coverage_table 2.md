> **创建:** 2026-07-26 | **更新:** 2026-07-26 02:45Z (C 行全部对 run log 重核) | **Session:** ma-v2 0C 独立审计 | **状态:** in-progress (执行轴待 08:00Z 首考后填) | **作废条件:** `anchor_timeline.py` 重新生成后步骤清单变化 ⇒ 本表须随之重生成并 diff

# 锚点时序覆盖表 — 逐函数三态 + 两轴档位

## 生成基线

```
基线产物   anchor_timeline.json (2026-07-26 重生成)
步数       308  (其中 33 步在异常分支内)      ← 上一版 265
与上一版   新增 37, 消失 1
未解析     本地未跟进 422 / 外部内建 518      ← 本表唯一的已知盲区
```

**★ 上一版 diff 的处置 (预注册预期已被证否, 记录在案):**
- **预期**: "应出现 `venue_fills:*` 相关新步骤; 不应有任何步骤消失。" **两条都错。**
- **实况**: 新增的是 `binance_funding:write_funding_rows`/`positions_at` · `check_funding_span:run/compare` · `pilot_log:fill` · 及 `run_anchor:main` 对它们的接线;
- **消失 1 步** `binance_executor:round_px::self._floor_to()` —— 按局部化判据排查: 该函数**未**新增未解析条目 ⇒ 非解析器致盲; 代码确认为**真改写** (`round_px` 改为按边取整: buy→floor / sell→ceil)。
- **教训入表**: **预期应按*能力*命名, 不按*模块名*命名** —— fills 的能力确实落地了 (`pilot_log.fill()`, 由 `anchor_loop.py:700` 接线, 该函数在此之前零调用者), 只是不在我预测的模块里。按模块名写的预期会被无关的实现自由度证伪。

## 判据

**三态** (对"这一步被谁验过"):

| 态 | 定义 |
|---|---|
| **E 有证据** | 能指到**一次实测输出** —— 生产日志行 / 验收套件输出 / 本次审计跑过的探针 |
| **C 有检查无证据** | 存在断言或守卫, 但**从未见它在真实数据上执行过** |
| **N 无人碰过** | 前两者皆无 |

**两轴档位** (正交, 不可合并为一条阶梯 —— shadow 在数据轴强于 DRY_RUN, 在执行轴弱于它):

```
data_tier :  单测 < DRY_RUN < shadow < testnet < 实盘
exec_tier :  单测 < shadow(=零) < DRY_RUN < testnet < 实盘
```
**归轴按目标模块判定** (可判定, 不需人逐步判断): `binance_broker`/`binance_executor`/`venue_fills`/`binance_funding` ⇒ 执行轴; `panel_build`/`inference`/`legs`/`compute_preds`/`live_panel`/`funding_panel`/`fapi_source`/`funding_derive`/`build_tail`/`regime_classifier` ⇒ 数据轴; `watchdog`/`watchdog_inputs`/`pilot_log`/`pilot_metrics`/`assert_anchor_artifacts`/`dryrun_ledger`/`check_factor_health`/`state_root`/`universe` ⇒ 两轴皆需。

---

## 数据轴 (本轮填)

| 函数 | 步 | 态 | data_tier | 证据 / 缺口 |
|---|---|---|---|---|
| `compute_preds:compute` | 8 | **E** | **shadow** | shadow 8 天 (2026-07-15→22) 真信号真面板; 132 锚点被 `monitor` 打分; 我独立复算三条 IC 序列一致 |
| `compute_preds:refresh_preds` | 2 | **E** | **shadow** | 同上; 每日 cron 日志 `[preds] king: 529 anchors inferred` |
| `legs:compose_book` | 8 | **E** | **shadow** | 132 锚点的 `positions_*.json` 由它产出; 我核过目标权重 Σ\|w\|=1.0000 / Σw=−0.0000 |
| `live_panel:build_live_panel` | 3 | **E** | **shadow** | 同上链路; `overlap_validation.json` 697 公共小时 `median_rel 2e-08` `match: true` |
| `live_panel:panel_symbols` | 1 | **E** | **shadow** | 我实测 140 symbol, 并据此查出 12 个已失效名字 |
| `panel_build:*` (间接) | — | **E** | **shadow** | `tests_panel_build` 43 断言 + fixture 缺失即 `sys.exit(1)`; warmup 887h 门实测 |
| `inference:load` | 2 | **E** | **shadow** | `tests_inference_parity` 对 server 参考逐值比对; fixture 缺失硬失败 |
| `funding_panel:build_funding_grid` | 4 | **E** | **shadow** | 8 天 funding 通道; **但见下方缺口** |
| `fapi_source:_get` / `book_mids` | 2 | **E** | **testnet** | 公开端点, 本次 testnet 锚点实际取回 110 个 mid (`mid_at_anchor` 基数 1577) |

**★ 数据轴的两处缺口 (已按 run log 重核):**
1. **`binance_funding:write_funding_rows` — 维持 C**, 但换成日志证据: 16 次执行 (02:22:08Z→02:43Z), **16/16 `income=0 rows=0 skipped_no_position=0`**, 15 次 `gap=COLD_START` + 1 次 `gap=None`。⇒ 外壳每锚点跑, **写行循环 0 次迭代**; 且 16 次全在 DRY_RUN ⇒ 从未对一个有持仓的账户跑过。`positions_at` 的 3 个 `_ts()` 步同样无证据。(shadow 8 天只写 00/08/16Z 那条旧缺口不变。)
2. **`check_funding_span:compare` — 降为 E** (我自查出的第四行, 上一版的 C 已过时): 19 次执行 (01:39:30Z→02:43Z), **19/19 `funding_span: STALE ours=140 venue=736 stale=15 absent_from_venue=12`** —— 断言不仅执行了, **还当场复现了我独立实测的那 15 个过期名字**。这是本表证据最强的一格。残余 C: 19/19 全 STALE ⇒ 它的"一致"分支无证据。

---

## 两轴皆需 (看门狗 / 日志 / 断言层) (本轮填)

| 函数 | 步 | 态 | data_tier | exec_tier | 证据 / 缺口 |
|---|---|---|---|---|---|
| `watchdog:evaluate` | 18 | **E** | shadow | **testnet** | **2026-07-26T00:17:11Z 真实触发**: §4-5b 47 name-anchors + §4-7 drift, 判定为真阳性 (场所/目标 = 2.00) |
| `watchdog:run` | 4 | **E** | shadow | **testnet** | 同上; 梯子实跑 `halt_opening` → `flatten`(重试 2 次, 重读持仓) → `alert`(msg 14) |
| `watchdog` 跨锚点持久化 | (在 `anchor_loop:run_anchor` 内) | **E** | — | **DRY_RUN** | 我本次实测 5 用例: 无文件/tripped/reduce_only/**文件损坏 fail-closed**/已清除 —— 四条性质全成立 |
| `watchdog_inputs:collect` / `derive_ops_stats` / `derive_venue_events` | 5 | **E** | shadow | **DRY_RUN** | 每锚点执行; `per_day_fail_rate` 实测有值。**缺口: `derive_ops_stats` 未跟上 4-5c 的 `submit_ts` 分母修正** |
| `pilot_metrics:m1_effective_cost` | 2 | **E**→见重核 | 单测 | **testnet** | **上一版的 C 已过时** (lead 指出): 00:17:11Z eval `per_day_c=[null, 20.1633]`, 我在 HEAD 上复算逐位复现。`TypeError` 已于 `4eb55b9` 修。**但门仍未在*可测*数据上求值过** —— 见重核 ① |
| `pilot_metrics:m2_markout` | 1 | **C** | 单测 | **单测** | 18 个锚点 `fill_rows_built: 0`; 全仓 0 个 fills 文件; `cond3.n_fill_rows=0` |
| `pilot_log:order` / `_w` | 2 | **E** | — | **testnet** | 4,935 行 orders 落盘 (DRY_RUN) + testnet 锚点 165 行 `rows_persisted == rows_emitted` |
| `pilot_log:fill` | 1 | **C** | — | 单测 | 生产者已接线 (`anchor_loop:700`) 且**每锚点执行**, 但 18/18 次 `fill_rows_built: 0` (DRY_RUN 无成交可归属); 接线时刻 (`6594b77` 02:15Z) **晚于唯一一次 TESTNET 锚点** (00:00Z) ⇒ 从未在能产出成交的模式下跑过 |
| `pilot_log:read_day` | 1 | **E** | — | **testnet** | 被 watchdog/断言层每锚点调用; 我多次直接读取 |
| `assert_anchor_artifacts:check_artifacts` | 25 | **E** | — | **testnet** | 生产路径执行, 并在 trip 锚点发出 REGRESSION 告警 (msg 15)。**缺口 (我审出): 断言 6 三处 fail-open; 断言 7 会凭空消失; selftest 只证 8 条里的 1 条** |
| `assert_anchor_artifacts:run_and_report` | 1 | **E** | — | **testnet** | 同上 |
| `dryrun_ledger:reconcile` | 4 | **C** | — | DRY_RUN | 比上一版更弱: 183/183 锚点 `expected = 0` ⇒ **逐锚点 `for e in exp` 循环体一次都没进过**, `OK`/`STARTED_NOT_FINISHED`/`MISSED` **三个状态全部无证据** (不止 MISSED)。129 次走 `NOT_STARTED` 早退, 54 次走真 reconcile 但期望集为空 |
| `check_factor_health:run` | 2 | **E** | shadow | — | 我本次端到端跑过: `{"ok": true, "rolling_rank_ic": 0.0487, "caliber": "champion_fixfunding", "decay_judged": true}`。**缺口: `MAX_STALE_H=8` vs 每日 cron ⇒ 每天 16/24 小时会误报 STALE** |
| `state_root:bind` / `paths_for` / `assert_single_delta` | 5 | **E** | — | **testnet** | `tests_state_root` 9 断言; **且我本次实证了它的价值 —— 我一度读错树 (DRY_RUN vs testnet), 而正是它把两棵树分开的** |

---

## 编排层 (本轮部分填)

| 函数 | 步 | 态 | 说明 |
|---|---|---|---|
| `run_anchor:main` | 51 | **E** | 每锚点执行; 14 步在异常分支内 —— **异常分支本身多为 C** (从未见触发) |
| `anchor_loop:run_anchor` | 25 | **E** | 同上 |
| `anchor_loop:_trade` | 13 | **E** | testnet 锚点实跑 |
| `anchor_loop:complete_anchor` | 13 | **E** | testnet phase_B 实跑 (`rows_emitted 165 / persisted 165 / n_topped_up 55 / k_cancel 9`) |
| `anchor_loop:_universe_gate` | **9** (上一版误记 8) | **E** (函数) / **C** (9 步中 6 步) | **上一版的 C 已过时** (lead 指出): 两个 TESTNET 锚点 (log:1433 / log:2970) 都带完整 `universe{...}` 输出; 其余 176 次是 `{"skipped":"DRY_RUN"}` 短路。**但 6/9 步仍无证据, 且最新那步是构造性 C** —— 见重核 ② |
| `anchor_loop:stage_alarm` | 1 | **E** | **上一版的 C 是错的** (我自查出的第三行): 2/183 锚点 `action=FLATTEN`, 两条不同分支各走一次 —— 见重核 ③ |
| `book_config:*` | 6 | **N** | **我未检视** (新模块) |
| `check_nosleep:*` | 13 | **N** | **我未检视** (新模块; 其 docstring 称以*观测*而非 `pmset` 设置回答) |

---

---

## ★★ C 行 run-log 重核 (2026-07-26T02:44:54Z 冻结)

**为什么必须重核 (team-lead 裁定):** 每个 C 行断言的都是"它要判定的情形**从未发生**" —— 那是三层阶梯第 3 层("这段代码**做过** X 吗")的主张, **只有日志能答, 代码读不出来**。上一版有几行是从代码状态的记忆里填的, 不是从 run log 里查的。⇒ 每行现附 **检索范围 + 检索式 + 命中数**; "会崩"类断言另附**现行 HEAD 的代码指针**。

**检索基底 (冻结, 供复核)**

| 项 | 值 |
|---|---|
| run log | `~/dl_quant_live/state/anchor_runs.log`, 3872 行, **2026-07-25T15:06:56Z → 2026-07-26T02:43:11Z** |
| 锚点 | **183** 次 `anchor start` = 181 DRY_RUN + **2 TESTNET** (21:51:45Z, 00:00:00Z) |
| 其他证据源 | `state/testnet/watchdog/last_eval.json` · `state/testnet/pilot_log/2026072{5,6}/orders.jsonl` · `state/notify_audit.jsonl` · `state/{,testnet/}watchdog/ALARM.log` · `config/book.json` |
| 代码指针基线 | HEAD **`eb918fa`** (重核这半小时里 HEAD 从 `2a16818` 走到 `eb918fa` —— 代码仍在动) |

**八格结果 (不是七格 —— 表里 `**C**` 计 8 处): 4 格降为 E, 4 格维持 C 但证据从"记忆"换成"日志"。**

| # | C 格 | 判定 | 检索式 → 命中 | 层级 |
|---|---|---|---|---|
| ① | `pilot_metrics:m1_effective_cost` | **C → E** (lead 对) | `last_eval.json` `per_day_c=[null,20.1633]`; 我在 HEAD 上对 `20260726/orders.jsonl` 复算 → `c_bps_overall 20.1633 / n_filled_orders 38 / filled_notional_total 8757.41` **逐位复现** | 3 |
| ② | `anchor_loop:_universe_gate` | **C → E** (lead 对) | `grep -c n_gone` → **2** (= 两个 TESTNET 锚点); `grep -c 'universe": {"skipped"'` → **176** | 3 |
| ③ | `anchor_loop:stage_alarm` | **C → E** (我自查) | `grep -o '"action": "[A-Z]*"'` → FLATTEN **2** / TRADE 181 | 3 |
| ④ | `check_funding_span:compare` | **C → E** (我自查) | `grep -c funding_span:` → **19**, 其中非 `stale=15` 者 **0** | 3 |
| ⑤ | `pilot_metrics:m2_markout` | **C 维持** | `grep -o '"fill_rows_built": [0-9]*' \| grep -vc '": 0'` → **0** (18 次全 0); `find state -name '*fills*.jsonl'` → **0 个文件**; `cond3.n_fill_rows` → 0 | 3 |
| ⑥ | `pilot_log:fill` | **C 维持** | 同上 + 接线 commit `6594b77` @02:15Z **晚于**唯一 TESTNET 锚点 @00:00Z | 3 |
| ⑦ | `dryrun_ledger:reconcile` | **C 维持 (且更弱)** | `grep -c MISSED` → **0**; 但 `ledger:` 183 行**全部 `0/0 completed, day 0`** ⇒ 期望集恒空 | 3 |
| ⑧ | `binance_funding:write_funding_rows` | **C 维持** | `grep 'funding: income=... rows=' \| grep -vc 'rows=0'` → **0** (16 次全 0) | 3 |

### ① m1 —— 门确实求值过了, 但**从未在可测数据上**求值过

`TypeError` 那句**我撤回**: 现行代码 `live/pilot_metrics.py:78-80` 是 `if o.get("avg_fill_px") is None: n_unmeasured_slippage += 1; continue` (`4eb55b9` 修的), 描述的是已不存在的代码。**但把 C 换成 E 之后, 那 38 行本身暴露了三件新的事:**

- **(a) 38/38 行 `fee_paid = None`** ⇒ `n_unmeasured_fee = 38`, `measurement_complete: false`。**20.1633 是纯滑点数**, 分子的手续费一半结构性缺席。⇒ §4-1 的 `c` 门**已在有成交的数据上求值过, 但一次也没在*完整*数据上求值过** —— 这两句不是同一句。
- **(b) ★ 16 笔已成交的 SELL 带负 `filled_notional` (合计 −4596.09), 被 `if f <= 0: continue` 整体丢弃。** 当日成交名义 13353.50, m1 只看见 8757.41 = **65.6%, 且全是买单**。`filled_notional` 是**签名量** —— `live/binance_broker.py:414` `out["filled_notional"] = sign * cq if cq > 0 else None` —— 而 m1 那道守卫把"已成交的卖单"和"没成交的单"判成同一件事。docstring 里的 "ONE-SIDED" 指每边只计一次, 不是"只计买边"。
- **(c) 同一签名量在同一文件里被三种读法消费**: `m4_turnover:192` 取 `abs()` ✅ · `m1:68` 丢负数 ❌ · `m3_fill_rate:162` **直接求和 ⇒ 买卖相消** ❌ (而它下一行的分母写的是 `abs(intended_notional)` —— 作者在相邻两行里对符号的态度不一致, 与 m1 自己注释里记的 `fee_paid`/`avg_fill_px` "孪生漏检"是同一形态)。

### ② universe_gate —— 函数 E, 但**它的身份在唯一一次执行之后变了**

9 步里: `venue_status` / `broker.positions` / `classify` **执行过** (2 次); `venue_status_unknown` 告警、`exit_orders` 提交循环、循环内 except 告警、`exit_only_held` 告警、`gone_from_venue_held` 告警 **均无证据** (输出里 `n_exit_only=0 / n_gone=0`)。

**第 9 步 (`if:cfgmap/if:blocked/...::self.alarm()`, maxNotionalValue=0 扣除) 是构造性 C**: 它随 `bcfa1b5` 落地于 **2026-07-26T00:56Z**, 比 `_universe_gate` 最后一次执行 (00:01:22Z) **晚 55 分钟**。**正面佐证: 00:00Z 那行日志的 `universe{...}` 里没有 `n_zero_cap_withheld` 键, 而现行 return 字典恒含该键。** ⇒ 这一格记录的是一个**已经不存在的函数**的执行证据。

### ③ stage_alarm —— 上一版是错的, 两条分支各走过一次

- 15:06:56Z: `note: "book flattened by staleness ladder"` ⇒ `has_positions` 真 ⇒ `stage_alarm("FLATTEN","CRITICAL")`;
- 另一次: `note: "cold start: no signal, empty book, nothing to do"` ⇒ `stage_alarm("FLATTEN_COLD","INFO")`。
- 佐证: `state/notify_audit.jsonl` 首行 `ts 1784992016.485644 severity CRITICAL` vs 该锚点 `anchor_wall_ts 1784992016.485567` —— **相差 77 µs**。
- **HOLD / DERISK 两级仍无证据** (`grep -c 'action": "HOLD\|DERISK'` → 0)。
- **★ 顺带查出的量测缺口: 告警的正文全仓无落盘处。** `notify_audit.jsonl` 只记投递回执 (severity/status/message_id, **无 message 字段**), `grep -rl 'flattening book\|de-risking\|signal stale' state/` → **0 个文件**。⇒ 上面那条只能靠"严重度 + 时间戳吻合"坐实, 不能靠正文。**一条正文只存在于 Telegram 会话里的告警, 在本机上是不可审计的** —— 而本表恰恰是靠日志判 C 的。

### ⑦ ledger —— 比上一版说的更弱

183 行 `ledger:` **全部 `0/0 completed (0.0%), day 0`**: 129 次 `gate=NOT_STARTED` (走 `if not clock_start` 早退), 54 次 `gate=NOT_YET` (17:10:13Z→20:15:43Z 那段, 配置里一度有 clock date, 现已回到 `config/book.json: "dryrun_clock_start": null`)。**两种情形下 `expected` 都是 0** ⇒ `for e in exp:` 循环体一次未进 ⇒ **`OK` / `STARTED_NOT_FINISHED` / `MISSED` 三个状态全部无证据**, 不止 MISSED。**⇒ §2.5 的时钟至今未起算, 这张对账器从未有过一个非空的期望集去对。**

---

## ★★ 重核过程中查出的新问题 (不属于本表原设计, 但 08:00Z 之前必须知道)

**同一个符号混淆的第四个现场, 而且它就是 trip 那份证据的来源。**

`live/watchdog.py:471-474` (§4-5b, 判"仓位动了但没有我们的单能解释"):
```python
f = float(o["filled_notional"] or 0.0)
if f > 0:                                     # ← 已成交的卖单在这里被丢掉
    filled_by_anchor[ats][sym] += (1 if o["side"] == "buy" else -1) * f
```
`filled_notional` 已经带符号, 这里**既丢负数、又再乘一次符号** —— 双重错。

**我用 trip 当天的真实台账把 5b 原样跑了一遍, 又把符号改对跑了一遍 (`n=47` 两边完全一致, 即我复现了看门狗那 47 条):**

| | `unexplained_frac` 分布 |
|---|---|
| **现行代码** | 31 条 ≈ 0.5 + **16 条 = 1.0** |
| **符号改对** | **47 条全部 ≈ 0.5** |

那 16 条 `1.0` **恰好就是那 16 笔卖单**。例: `AVAXUSDT` 现行报 `expected 0.0 / observed −770.98 / frac 1.0`; 符号改对后是 `expected −385.66 / observed −770.98 / frac 0.4998`。

**⇒ 三条结论, 分开写:**

1. **trip 仍是真阳性** —— 改对之后 47 条**全部**落在 0.5, 即"仓位是我们下单量的 2 倍"这**一个**原因, 干净利落。
2. **但证据的形状被这个 bug 改了**: 现行输出看上去是**两个族群** (31 条"一半没解释" + 16 条"全部没解释"), 会诱导读者去找第二个失效原因; 实际只有一个。
3. **★ 这是一个被另一个缺陷掩盖着的缺陷**: 只要 `filled_notional < 0` 的卖单一直被丢, **任何一笔正常成交的卖单都会让 5b 报 `frac ≈ 1.0`** —— 即 5b 在空头方向上是个**常驻假阳性发生器**。现在看不出来, 是因为 2× 敞口那个真缺陷让它们**恰好也是真阳性**。**⇒ 0B 修完 2× 之后, 5b 会继续在每个卖单名字上触发, 而现场会读作"2× 没修好"。**

**同族的第四处**: `pilot_metrics.py:212` (`m5_weight_fidelity`) 同样是 `if f > 0:` + 显式乘符号 ⇒ `venue_vs_inferred_drift` 的推算持仓里**没有任何卖单**。而 §4-7 `unrecovered_position_drift` 正是这次 trip 的第二个触发条件。

> **未经裁定 (按边界, 我不派任务): 这四处 (`m1:68` · `m3:162` · `watchdog:471` · `m5:212`) 是否为同一处修复, 由 team-lead 裁定后交 0B。我只读、只报。**

---

## ★ 陈旧性检测已上线 (第十形态, team-lead 批准 2026-07-26)

**判定部分已从本表**散文**移进机器可读的 `anchor_coverage_evidence.json`** (本文件仍是叙述与缺口的所在, 但**判定以那份 JSON 为准**)。`anchor_timeline.py` 每次生成时自动比对**每格的 `evidence_utc`** 与**该函数最后改动的 commit 时刻** (`git log -L <该函数行域>:<文件>`, 逐**函数**而非逐文件 —— 文件级时刻会让每次提交作废全表, 而每天喊狼的检查等于没有检查)。**后者晚 ⇒ 该格自动降 UNKNOWN。**

**六种结局都已实测走通 (红/绿俱全):** `FRESH` 25 · `RE-PINNED` 7 · **`STALE` 7** · `UNDETERMINED` (实测过 11, 现为 0) · `ORPHAN` 1 · `NO_EVIDENCE` 30。缺席不产生绿灯: 证据文件不存在 ⇒ 全部 UNKNOWN; `git log -L` 失败 ⇒ UNKNOWN; **文件有未提交改动 ⇒ 该文件所有函数 UNKNOWN** (git 历史看不见工作区, 否则会给一份"和磁盘上的代码不是同一份代码"的绿灯)。

### ★ 证据链是三环, 不是两环 (team-lead 精化 + 我补上中间那环)

lead 指出数据轴的证据不是 shadow 直接背书, 而是经 parity 套件传递 —— **对**。但链是三环, 中间那环**冻结**:

```
pilot 实现 ──[parity 套件, 每次验收在 HEAD 重跑]──▶ fixture (冻结: 2026-07-25T14:52〜15:15Z 采集)
           ──[fixture 由 engine 某版本产出]──▶ engine ──[shadow 07-15→07-22]──▶ 真实数据
```

**我核了中间那环 (它才是链的年龄上限)**: engine 的 `signal_chain`/`panel_source`/`ic_monitor`/`netting` 最后改动 = `f6740f9` @ **2026-07-19T12:04Z**, 早于 fixture 采集、也在 shadow 窗内 ⇒ **V_fixture == V_shadow, 本环成立**。
> **一个差点踩上的陷阱**: `f6740f9` 是这些文件**首次入 git** (全栈收仓, +101 行 0 删除), **不是**一次行为改动 —— 代码此前已在 server 上运行。若当成"引擎在 shadow 窗中途变过", 会把 shadow 证据从 8 天错砍到 3 天。**"文件在 git 里出现" ≠ "代码变过"。**

**⇒ 由此定的规则 (已写进工具): 合取链的陈旧度 = 最*陈旧*那一环, 不是最*新鲜*那一环。所以 `pinned_by` 只中和 head 环的改动, **绝不把 `evidence_utc` 往前推** —— 否则 fixture 这种冻结环会从视野里消失。** 且 `pinned_by` 必须同时写 `pins`(它到底钉住了什么), 缺 `pins` 一律判 STALE: "有套件覆盖"在写清覆盖了什么之前不是一个事实。

### 证据源是三类, 不是两类 (team-lead 第三次精化 —— shadow 轴真陈旧已归零)

```
① 套件 @HEAD          每次验收重跑 —— 钉 head 环, 讲**正确性**
② 生产日志 @HEAD      每锚点真实数据 —— 第 3 层执行证据, 讲**执行**, 不讲正确性
③ shadow / server 记录 链尾, 冻结
```

**② 的边界必须随它一起走**: 一条生产日志行证明"它跑了并返回了", **不证明"它返回的对"**。把两者并成一个绿灯, 等于把"跑过"悄悄升格成"没问题"。⇒ 工具里 `proves` 必填, 另设 `residual` 让正确性缺口在格子转绿之后**仍然可见**。

**③ 两个通道是相加的, 不是二选一**: `refresh_preds` 逼出这条 —— 套件钉住它的**三条拒写路径**, 生产日志钉住它的**成功路径**, 是同一函数的**互补两半**。只报第一个通道会把另一半悄悄丢掉。现在显示为 `RE-PINNED[suit+prod]`。

**验过的证据行 (机械链, 非我的印象):** `refresh_preds` 的 `ok:true` 分支**只能**由 `compute(...)` 正常返回后到达 (`payload = compute(...)` → `_save_atomic` → `return ok:true`) ⇒ 那 185 行是 `compute` 跑完的**机械证明**; 远端产物 `state/preds_latest.json` 的 mtime (03:09:31Z) 与最新一行**逐秒吻合** ⇒ "did N / landed M" 成立。

**⇒ `compute_preds:compute` 由 STALE 升为 `RE-PINNED[prod]` —— shadow 轴的真陈旧归零。** 残余已记在格子里: **全仓仍无任何套件调用 `CP.compute`, 正确性证据仍停在 shadow 期。**

**⇒ 而它不是万能通行证 (已实测): 给 `m1_effective_cost` 挂一条真实存在的生产证据 (`per_day_c`, 00:17:32Z), 机制照样判 STALE —— 因为那行早于该函数 02:59:13Z 的改动。**

### residual 的两条出路 (team-lead 裁定 2026-07-26)

**"residual 不降级判定"批准 —— 理由是陈旧与不完整是两个维度, 折进一个状态正是我们拆了一晚上的那类合并。但 display-only 不够:**

1. **汇总行带 residual 计数** —— 现在是 `RE-PINNED 8 (4 带 residual)`。**汇总行是这张表的嘴; 缺口在格子里可见、在头条里不可见 = 正门挂牌侧门没挂。**
2. **每条 residual 落成 OPEN ITEM, 带 owner + 可判定的闭合条件**, 且**闭合条件凡机械可判的都由工具每次现场探一次** ⇒ **条目会自己宣布"我可以关了"**, 不必靠谁记得它存在。缺 `closes_when` 的 residual 单独计数并标 `★不可跟踪, 只能被重读`。

**当前 4 条 OPEN ITEM (owner 一律"未经裁定 —— 0C 记录, 分派由 team-lead", 按 §83 边界):**

| 函数 | 缺口 | 闭合条件 | 探针 |
|---|---|---|---|
| `compute_preds:compute` | 执行证据不含正确性; 全仓无套件调用 `CP.compute` | 某受验收覆盖的套件直接调用 `compute_preds.compute` 且 ALL PASS | 未匹配 |
| `compute_preds:refresh_preds` | 两半分属两个通道, **没有任何一处同时验两侧** | `tests_signal_and_loop` 出现对成功路径的断言 | 未匹配 |
| `live_panel:panel_symbols` | 钉住的是"返回了可哈希名单"不是"名单正确"; 且我未排除指纹由缓存路径产出 | 某套件对 `panel_symbols()` 返回值本身做断言 | 未匹配 |
| `assert_anchor_artifacts:run_and_report` | selftest 只证 8 条断言里的 1 条 | 8 条逐条注入各转红一次 | (非机械判据, 无探针) |

**探针两侧都验过**: 拿 `INF\.load\(` 探 ⇒ `satisfied: True` (命中 `tests_inference_parity.py:76`); 拿 `CP\.compute\(` 探 ⇒ `False`; 探针缺字段 ⇒ `unknown`, 不是 `satisfied: False`。

**两个监督者互证 (lead 裁定)**: 四条 owner = **0B / 窗口内 (B 组)**, 并进 `dl_quant_live/docs/OPEN_ITEMS.md` (那边每锚点自动报**龄期**), 我的探针留作独立**闭合**检测器。⇒ 同一条待办两个监督者, **两边不一致本身就是信号**。⇒ 于是我又加了第三项检查: **条目是否真的落到了那份 OPEN_ITEMS 里** —— 只活在我这边 = **派工在途中丢了**, 而这件事从两个监督者各自看都是不可见的。当前 4/4 标 `⚠尚未出现`, 待 lead 派工后自行转绿。

### ★ 这轮里工具自己犯了三次它要抓的错

| # | 症状 | 形态 |
|---|---|---|
| 1 | `residual` 变对象后, 单行 `why` 打印**整个 dict** —— 那句话被埋进它自己的元数据 | **为"看见"而做的改动, 第一版让东西更看不见** |
| 2 | 探针 glob 匹配 0 个文件时返回 `satisfied: False` (文件被改名/不存在 ⇒ 报"条件未满足") | **缺席折进确定的否定** —— 方向保守, **状态错误**, 而这工具的全部存在理由就是拒绝这笔交易 |
| 3 | 读到**正在写入**的验收日志 (无终止标记) ⇒ 判 `NOT ALL PASS` | **在途 ≠ 失败**。这批日志没有独立的失败标记 ⇒ "未完成"与"失败"内容上不可分 ⇒ 只能回溯到最近一次**完成**的运行, **并把跳过了几次未完成的运行一并报出** (否则会掩盖一个每次都中途死掉的套件) |

**#3 差点让我向 lead 报一句假话** ("parity 套件转红")。实际那次运行随后完成且 ALL PASS —— **`n_newer_without_terminal_marker` 现在 0**。⇒ **写检测器的人和被检测的代码, 犯的是同一批错误; 唯一的区别是检测器会当场把自己抓出来。**

**结果 (上一版口径): 7 个 shadow 轴格里 6 个 RE-PINNED, 精确剩下一格是真陈旧。**

| 格 | 结局 | 钉住它的套件 / 缺口 |
|---|---|---|
| `inference:load` | RE-PINNED | `tests_inference_parity`: `INF.load()` 实调 + 与 server 逐值比对 |
| `live_panel:build_live_panel` · `funding_panel:build_funding_grid` | RE-PINNED | `tests_panel_build`: LIVE 路径 max\|Δ\| 3.31e-05; funding 两种口径都走到 |
| `legs:compose_book` | RE-PINNED | `tests_signal_and_loop`: 三处调用 |
| `compute_preds:refresh_preds` | RE-PINNED **(部分)** | **仅三条拒写路径**; 成功路径未覆盖 |
| `live_panel:panel_symbols` | RE-PINNED **(部分)** | 仅作 `columns_fingerprint` 的输入; 钉住的不是名单正确性 |
| **`compute_preds:compute`** | **STALE** | **全仓无任何套件调用 `CP.compute`** ⇒ lead 说的"换不到指针的才是真陈旧", 精确剩这一格 |

> **★ 口径必须说死: 这**不**表示 shadow 那 8 天的 IC 结论作废 —— shadow 跑的是**当时**的代码, 结论对**当时**的代码成立。作废的是**覆盖率主张**。alpha 证据与覆盖证据是两件事。

### 检测器已在做实事

**02:59Z / 03:05Z 0B 两次提交 (`9e5480f` R19 schema / `004f0f7` 断言层), 当场把 4 格自动降为 UNKNOWN** —— `anchor_loop:_trade` · `complete_anchor` · `pilot_metrics:m1_effective_cost` · `m2_markout` · `assert_anchor_artifacts:check_artifacts`。**没有人需要记得去问。** 其中 `m2_markout` 是一个 **C** 格被降级 —— 正确: 代码变了, "从未触发"这句话的主语也变了。

---

## 执行轴 (**待 08:00Z 首考后填** — team-lead 建议, 避免填两遍)

**23 步 (上限集), 涉及 `binance_broker` 的 `submit`/`positions`/`positions_notional`/`arm`/`cancel_order`/`account_snapshot`/`income_since`/`__init__` · `venue_fills` 的 `fills_for`/`fill_details_for` · `binance_funding` 的 `fetch_rates`/`fetch_income` · `anchor_loop:_universe_gate`。**

**当前状态: 全部 exec_tier = `testnet (带已知缺陷)`** —— 2026-07-26T00:17Z 那一轮确实执行了它们, 但那一轮暴露了两个根因 (`fills_for` 读回为 0 ⇒ 补单按全额下 ⇒ 2× 敞口; `round_px` 未按边取整 ⇒ 39 sell / 13 buy 被拒)。**⇒ 08:00Z 修复后首考跑完, 这 23 步应升至 `testnet (修复后实证)`, 届时填。**

---

## 未经单独检验的步骤清单 (本表)

1. **`panel_build:*` 一行是聚合的** —— 时序表里 `panel_build` 的步骤分散在 `build_live_panel` 等函数内, 我按模块归并填了一行, **未逐函数核**;
2. **`book_config` / `check_nosleep` 标 N 是因为我未检视, 不是因为我确认无人碰过** —— 0B 可能有证据, 我没问;
3. **"异常分支多为 C"是按类推断**, 未逐条核对 33 个异常分支步骤各自是否被触发过;
4. **数据轴 tier 标 `shadow` 依据的是 8 天 shadow 运行**, 而我已查明其 funding 台账为 8h-only ⇒ **funding 相关的 shadow 档位应视为部分覆盖**, 我未进一步细分。

**重核这一轮新增的未检验项:**

5. **E 行未做同等重核** —— 本轮只把 8 个 C 格对了日志。**E 格的证据我没有逐条重放**, 其中至少 `watchdog_inputs` / `assert_anchor_artifacts` 两行的证据是几小时前记的, 而这期间 HEAD 走了 6 个 commit。⇒ **本表现在是"C 格已达第 3 层, E 格仍是第 2 层记忆"的混合体。**
6. **`stage_alarm` 的 E 建立在"严重度+时间戳吻合"上**, 不是正文 —— 因为正文全仓不落盘 (见重核 ③)。这是一条**用推断补上的证据**, 与其他 E 格不同级。
7. **5b 那份复算用的是 trip 当天的台账**, 我**没有**验证 `position_readback` 本身是否也受同一符号问题影响 (它来自 `/fapi/v3/positionRisk`, 与订单表不同源, 但我没查其写入路径)。
8. **`m3_fill_rate` 的买卖相消是我读代码判的, 不是实测** —— 当日 0 笔 maker 成交, 该路径无法在现有数据上验证。⇒ 它是一条**预测**, 不是一次观测。
