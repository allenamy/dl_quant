> **创建:** 2026-07-26 | **Session:** ma-v2 0C 独立审计 | **状态:** in-progress (执行轴待 08:00Z 首考后填) | **作废条件:** `anchor_timeline.py` 重新生成后步骤清单变化 ⇒ 本表须随之重生成并 diff

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

**★ 数据轴的两处缺口 (已知, 已入队列):**
1. **`funding` 台账写入器在 shadow 的 8 天里只写 00/08/16Z** ⇒ 41 个 4h symbol 的结算一行未写 ⇒ **8 天覆盖了写入器, 未覆盖结算区间归一化那条路径**。新 `binance_funding:write_funding_rows` 尚未产出可验证据 ⇒ 该能力当前 **C**。
2. **`check_funding_span:compare`** (span 表 vs `fundingInfo` 一致性) —— 新落地, **C**: 断言存在, 未见其在真实数据上执行过。**它当场应报出我实测的 15 个不一致名字 (11 个是成员)。**

---

## 两轴皆需 (看门狗 / 日志 / 断言层) (本轮填)

| 函数 | 步 | 态 | data_tier | exec_tier | 证据 / 缺口 |
|---|---|---|---|---|---|
| `watchdog:evaluate` | 18 | **E** | shadow | **testnet** | **2026-07-26T00:17:11Z 真实触发**: §4-5b 47 name-anchors + §4-7 drift, 判定为真阳性 (场所/目标 = 2.00) |
| `watchdog:run` | 4 | **E** | shadow | **testnet** | 同上; 梯子实跑 `halt_opening` → `flatten`(重试 2 次, 重读持仓) → `alert`(msg 14) |
| `watchdog` 跨锚点持久化 | (在 `anchor_loop:run_anchor` 内) | **E** | — | **DRY_RUN** | 我本次实测 5 用例: 无文件/tripped/reduce_only/**文件损坏 fail-closed**/已清除 —— 四条性质全成立 |
| `watchdog_inputs:collect` / `derive_ops_stats` / `derive_venue_events` | 5 | **E** | shadow | **DRY_RUN** | 每锚点执行; `per_day_fail_rate` 实测有值。**缺口: `derive_ops_stats` 未跟上 4-5c 的 `submit_ts` 分母修正** |
| `pilot_metrics:m1_effective_cost` | 2 | **C** | 单测 | **单测** | **★ 循环体从未执行过** (所有行 `filled_notional=0`); 且一旦有成交将 `TypeError` (我实测复现) ⇒ **§4-1 的 `c` 门至今未在有成交数据上求值过** |
| `pilot_metrics:m2_markout` | 1 | **C** | 单测 | **单测** | `fills` 表刚有生产者, 尚无成交行 |
| `pilot_log:order` / `_w` | 2 | **E** | — | **testnet** | 4,935 行 orders 落盘 (DRY_RUN) + testnet 锚点 165 行 `rows_persisted == rows_emitted` |
| `pilot_log:fill` | 1 | **C** | — | 单测 | 生产者刚接线 (`anchor_loop:700`, 此前零调用者); 尚未见成交行 |
| `pilot_log:read_day` | 1 | **E** | — | **testnet** | 被 watchdog/断言层每锚点调用; 我多次直接读取 |
| `assert_anchor_artifacts:check_artifacts` | 25 | **E** | — | **testnet** | 生产路径执行, 并在 trip 锚点发出 REGRESSION 告警 (msg 15)。**缺口 (我审出): 断言 6 三处 fail-open; 断言 7 会凭空消失; selftest 只证 8 条里的 1 条** |
| `assert_anchor_artifacts:run_and_report` | 1 | **E** | — | **testnet** | 同上 |
| `dryrun_ledger:reconcile` | 4 | **C** | — | DRY_RUN | 每锚点执行并打印, **但从未在一次真实 MISSED 锚点上被检验** ⇒ 它的 `MISSED` 分支无证据 |
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
| `anchor_loop:_universe_gate` | 8 | **C** | DRY_RUN 下整体短路; testnet 下应执行, **本次未见其输出** |
| `anchor_loop:stage_alarm` | 1 | **C** | staleness 阶梯未触发过 |
| `book_config:*` | 6 | **N** | **我未检视** (新模块) |
| `check_nosleep:*` | 13 | **N** | **我未检视** (新模块; 其 docstring 称以*观测*而非 `pmset` 设置回答) |

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
