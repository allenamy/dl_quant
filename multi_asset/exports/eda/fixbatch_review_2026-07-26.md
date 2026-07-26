> **创建:** 2026-07-26 17:1xZ | **Session:** ma-v2 0C 独立复核 | **状态:** final | **结论: 不通过 —— 两条独立的阻塞项**

# 修复批 a–j 独立复核 (0C) — **不予放行**

**0B 自报 10/10 红→绿。逐项验后: 代码改动本身多数是对的且有实质, 但**批次在树上不绿**, 且**它自己的新套件没有一条进入权威判据**。**

---

## ★★ 阻塞 A — 电池在树上 **NOT GREEN**, 且失败是**本批引入的**

我在树上重跑 `bash run_acceptance.sh` (17:03:40Z):

```
19 套: 18 过 / metrics_freeze **EXIT 1**
ACCEPTANCE: NOT GREEN — at least one suite failed
```

**`metrics_freeze` 的读数:**
```
state          DRIFT
current_sha256 e9d531f1083ef0287685ee6d713af35055dbad2046d934b1150bf99d9c155d27
frozen_sha256  df7f93104039f392deb56732ea29e6fa268956b3bf6ce4bb2a206b3cbde368ae
frozen_utc     2026-07-26T04:57:46Z
```

**★ 归因 (这一步决定它是不是"先前失败"):**

| | sha256 |
|---|---|
| 冻结记录 | `df7f9310…368ae` |
| **HEAD (本批之前)** | **`df7f9310…368ae` —— 与冻结逐位相同** |
| 工作树 (含本批) | `e9d531f1…55d27` |

**⇒ 本批之前 `metrics_freeze` 是**绿**的。⇒ 它**不属于** 0B 所说的"4 个先前失败"。⇒ **是本批把一条绿的门变红了。****

**⇒ 但这不是缺陷 —— 是冻结机制在正常工作。** 改动本身 ([h]) 是实质且正确的:
- `M1_COMPLETENESS_COMPONENTS = ("n_unmeasured_slippage", "n_unmeasured_fee")` —— 正是 §2.5.7 需要的机器可判 pin, 且注释写明了别名陷阱;
- `m4_turnover` 加行型守卫 —— 排除 `protective_flatten`, 同时修掉 `float(None)` 崩溃**与** `n_anchors` 分母稀释 (梯子行给分子加 0、给年化分母各加 1 ⇒ §3d 门读得比现实好)。

**⇒ 处置: 需要**有意的重新冻结并记录理由**, 而不是让它带红提交。`pilot_metrics.py` 自己的文件头写着"editing this script after signing = editing the protocol"。**

## ★★ 阻塞 B — 本批**自己的 9 个新套件, 一条都不在电池里**

`run_acceptance.sh` 的 `SUITES=(...)` 是**硬编码的 19 条数组**。磁盘上存在但**不在数组里**的:

```
tests_flatten_ladder   tests_flatten_rows    tests_ghost_rows
tests_m4_rowtype       tests_market_maxqty   tests_readback_universe
tests_scoped_writes    tests_topup_leg_fill  tests_trip_page
```

**⇒ 这 9 条正是 a–j 批次自己的红→绿证据所在。⇒ 于是"10/10 红→绿"是一句**由部件手工拼装的、关于整体的主张**。**

> **⇒ 而 `run_acceptance.sh` 的文件头自己就禁止这件事:**
> **"any claim 'the suites are green' must cite THIS script's output; never assemble the claim by hand from parts — a claim about the whole, assembled by hand, drifts."**
> **⇒ 权威判据覆盖不到本批的任何新工作。⇒ 与今晚反复出现的同一形态: **新能力做好了, 但没接进那个替整体说话的东西**。**

---

## 已通过的部分 (逐项)

### ③ `tests_watchdog` 三处改动: **全部是契约变更, 无一是放宽**

| 改动 | 判定 | 理由 |
|---|---|---|
| `MockBroker()` → `MockBroker(positions={...})` (2 处) | **契约变更, 合法** | [c] 之后梯子从 `broker.positions()`(张数) 取尺寸而非台账 readback(USD 名义) ⇒ 期待平仓的场景必须声明场所持有什么。**三条断言原文未动**, 只补了新契约要求的输入 |
| `_ReadbackDown` 断言替换 | **契约变更 + 加强** | 旧: "读回失败仍平仓, 但声明重发了未确认数量"; 新: "读不到持仓就**什么都不发**"。**并新增一条断言旧行为**不再发生** (`not stage1_resent_stale_quantities`) ⇒ 断言数 1→2, 是反向加固不是放宽 |
| `venue_reject` → `_NOT_FILLED = (submitted_rejected, never_submitted)` | **契约变更 (词汇拆分) + 加强** | 单一标签拆成两个, 表面是放宽; 但**新增的双条件** `(submit_ts is None) ⟺ (reason == never_submitted)` 把该放宽重新钉死。**且该断言对我实测到的真缺陷有红能力**: 旧代码所有 `protective_flatten` 行 `submit_ts=null` + `reason=venue_reject` ⇒ `True == False` ⇒ 断言失败 |

### ④ 三个规格决定

| 决定 | 判定 |
|---|---|
| `rows_root` 默认反转 | **安全方向, 且生产已显式接线** —— `_rows_root = rows_root or os.path.join(sdir, "pilot_log")`, 忘记传 ⇒ 写进自己的 state_dir 而非污染生产; 而 `run_anchor.py:263` **显式传了 `rows_root=log_root`** ⇒ 生产的梯子行仍落在真台账 (我核过, 这是"修复反被默认值废掉"的那个风险点) |
| `TERMINAL_REASONS` +2 | 与 ③ 第三条同一改动, **由双条件钉死** ⇒ 合法 |
| `attempt_idx` / 行型守卫普查 | m4 已按 `order_type` 白名单 (`maker`, `topup_taker`) 排除, **按类型而非按空值** ⇒ 同时修掉崩溃与分母稀释, 是正确的那一版 |

---

## 未决 / 我没能判的

**② e (隔离) —— 我的方法**不成立**, 判 UNKNOWN。** 我在电池前后各取一次生产台账全量哈希:
```
电池前 90cf5b54…   电池后 7f601725…   (17 个文件, 数量未变)
```
**但同一窗口内有一次锚点运行 (17:03:55Z 起, 17:04:31Z 完), ⇒ 变化不可归因于电池。⇒ 要判隔离, 需要 lead 指定的那个受控实验 (树副本 + 无并发锚点), 我未做。**

**② g / b / f 三项抽验未做** —— 因为阻塞 B 意味着这些套件**当前不在权威判据内**, 先解决"它们算不算数"比先验它们的数值更要紧。

## ★ 一条连带: §2.5.7 引用的正是这次被作废的冻结

**我写的 §2.5.7 把组件集 pin 成 "as of freeze `df7f9310`" —— 而本批正是把 `pilot_metrics.py` 从该冻结改走的那一批。⇒ 重新冻结时必须一并更新 §2.5.7 的引用, 否则协议引用了一个**已不描述当前代码**的冻结 id。⇒ 反过来说: 本批的 `M1_COMPLETENESS_COMPONENTS` 恰恰是让那条 pin 机器可判的东西 —— **修复与协议文本必须一起落地**, 不能只落一半。**

## 顺带观察 (非阻塞)

`state/testnet/pilot_log/20260726/fills.jsonl` **首次出现** ⇒ M2 的输入第一次存在。我未审其内容。

---

# ② 抽验 (补做, 无 deadline 之后)

## 九个新套件: **全绿** (逐个单跑)

```
tests_flatten_ladder ✓  tests_flatten_rows ✓  tests_ghost_rows ✓  tests_m4_rowtype ✓
tests_market_maxqty ✓   tests_readback_universe ✓  tests_scoped_writes ✓
tests_topup_leg_fill ✓  tests_trip_page ✓
```
**⇒ 套件本身是好的。阻塞 B 说的是它们**不在权威判据里**, 不是它们不通过。**

## ★ g 红能力: **确认存在, 但失效形态与 0B 所述不同**

**摘掉 `m4_turnover` 的行型守卫 ⇒ `tests_ghost_rows` exit=1** ✓ 红能力成立。**但它是这样红的:**

```
TypeError: float() argument must be a string or a number, not 'NoneType'
  pilot_metrics.py:330  tgt += sum(abs(float(r["target_w"]) - float(r["prev_w"])) ...)
```

**⇒ 它**崩**在 `prev_w=None` 上, 根本走不到比较那一步。⇒ 0B 引的 `328.5→219.0, n_anchors 2→3` **不会出现**。**

**⇒ 而那组数字正是本批注释里自己写下的**反事实**: "(b) would, **once the None was made 'safe'**, have opened one extra anchor bucket per trip"。⇒ 即它描述的是**另一个(把 None 变安全的)修法**下的稀释, 不是摘掉守卫所观测到的红。**

> **⇒ 判定: 红能力**成立**; 但把"崩溃红"与"稀释红"当成同一件事引用是不准确的 —— **两者都是真问题, 只有一个是这个测试所演示的**。**

**顺带查出**: `m1_effective_cost` **也**有同一条行型守卫 (行 93), 且它**在 HEAD 就存在** (HEAD 出现 1 次 / 工作树 2 次 ⇒ 本批加的是 m4 那条)。摘掉 m1 那条会让 ghost 行把 `measurement_complete` 从 True 翻成 False —— **它同样是承重的**。

## b / f: 已知答案编在 fixture 里, 与真实序列一致

- **b** `tests_flatten_rows` 回放 12:17:31Z 真实序列: **"103 refused / 101 filled + 2 refused / 2 refused"**, 并明写 "101 real protective flattens left NO order row" —— **与我 12:1xZ 独立实测的 208 行 / 只记失败 完全一致**;
- **f** `tests_topup_leg_fill` 的已知答案: **"77 top-up rows reported filled_notional BIT-IDENTICAL to their maker sibling"** + **"all 77 had submit_ts = None"** —— **与我预注册并实测的 77 / 双腿 / 继承值 逐项吻合**。

---

# ★★ 我自己在这次复核里犯的两个错 (记录在案)

| # | 错 | 怎么抓到的 |
|---|---|---|
| 1 | 把 [g] 当成 `tests_m4_rowtype` 去跑红能力 (它其实是 `tests_ghost_rows`) | 摘掉守卫后 `tests_m4_rowtype` 仍 ALL PASS —— 与"必须 FAIL"矛盾 |
| 2 | **`replace(old, '', 1)` 删掉的是 m1 的守卫, 不是 m4 的** (该行在文件里出现**两次**) | 结果显示"删 m4 的一行改变了 m1 的输出" —— **因果上不可能**, 由此回查才发现删错了行 |

> **★ 第 2 个尤其值得记: 它**产出了一个红**, 而红正是我要找的东西 ⇒ **它会以错误的理由确认这条主张**。抓到它的不是结果好看不好看, 是"这个因果链根本不成立"。⇒ 与今晚多次出现的同一条: **一个可信的结果, 其可信恰恰来自它符合预期。**
