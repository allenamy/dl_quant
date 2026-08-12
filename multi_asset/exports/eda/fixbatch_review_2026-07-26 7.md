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

---

# 终审 (0C, 2026-07-26 17:2x–17:3xZ)

## ★ 先撤回我自己的一条: **阻塞 B 作废**

**我此前测的是**顶层** `run_acceptance.sh` (19 套)。本仓有**两个同名 runner**, 0B 用的是 `live/run_acceptance.sh` (26 套) —— **9 个新套件全部在其中**。⇒ 阻塞 B 是我看错了文件, **撤回**。**

## ★★ 但由此撞出一条更要紧的: **两个 runner 都自称"唯一"**

| | 顶层 `run_acceptance.sh` (19) | `live/run_acceptance.sh` (26) |
|---|---|---|
| 自称 | "**the single** machine-checkable green/red statement for this repo" | "**Single** machine-checkable acceptance statement for the pilot prerequisite stack" |
| 独有 | **`drift_gate` · `gate_coverage` · `metrics_freeze`** | 9 个新套件 + `tests_production_signature` |

**⇒ 两者**都能跑、都出判决、都自称唯一**, 而检查项是**互有独占**的 ⇒ **谁都不是"那一句"**, 且**各自的绿对另一方的红完全沉默**。**

> **⇒ 最具体的后果: `metrics_freeze` **只存在于顶层 runner**。⇒ 0B 用 26 套 runner 验证一个**修改了被冻结文件**的批次, 而那个 runner **根本看不见冻结**。⇒ "26/26 全绿"与"冻结已漂"可以同时为真 —— 今天正是如此。**

## ★★ 26 套的 "ALL GREEN" 里, **三条 known-fail 有两条是假的**

```
ACCEPTANCE: ALL GREEN (23/23 suites exit 0, plus 3 KNOWN-FAIL, each listed with its reason)
  known-fail tests_inference_parity      — ModuleNotFoundError torch — not installed (pre-existing)
  known-fail tests_panel_build           — local-vs-server xsr rank-channel parity drift (pre-existing)
  known-fail tests_production_signature  — ModuleNotFoundError pilot_daily (pre-existing)
```

**解释器没有钉:**
```
顶层    . ops/pyenv.sh ;  PY="${ACCEPT_PY:-/usr/bin/python3}"     ← 钉死, 且注释写明本机三个 python 的理由
live/   PY="${ACCEPT_PY:-python3}"                                ← 裸 python3
裸 python3 = /usr/local/opt/python@3.14/bin/python3.14 (3.14.4), **无 torch**
```

**我用钉死的解释器直接跑这两套:**

| 套件 | `live/` runner 判定 | `/usr/bin/python3` 实测 |
|---|---|---|
| `tests_inference_parity` | KNOWN-FAIL "torch not installed (**pre-existing**)" | **exit 0** |
| `tests_panel_build` | KNOWN-FAIL "xsr parity drift (**pre-existing**)" | **exit 0** |

**⇒ torch **是**装了的 —— 只是没装在这个 runner 挑中的解释器里。⇒ 两条 "pre-existing" 都**不是**事实, 是**这个 runner 自己的环境缺陷**。⇒ `tests_panel_build` 的 `max|Δ| 7e-2` 也同源 (不同 numpy ⇒ 不同 rank/统计), 却被写成"本地-服务器 parity 漂移"。**

> **★ 这正是 lead 头条描述的那个形态 —— "恒红, 人人替它补理由" —— **在修复它的那一批里又发生了一次, 只是低一层**: 豁免清单把一个**可修的 runner 缺陷**吸收进了一个**听起来像事实的理由**。⇒ 与"容差带吞掉同量级的非良性原因"同族: **一个听起来是事实的理由, 恰恰是最不会被追问的那种。****

**⇒ 判定: 项 ① **不通过**。**

## ② e 受控材料: **通过**, 但缺一个对照

**已有 (我用钉死解释器复跑, ALL PASS):**
```
正对照  "the fixture really tripped (otherwise the ladder never runs and this proves nothing)"
        一次 scoped run 生产 orders.jsonl 逐字节不变   f29939950275 -> f29939950275
        两次 scoped run 仍逐字节不变 (2026-07-26 复现)  行数 2 -> 2
        行**没有被丢弃**: 写在 state_dir 底下 (两个 tmp 路径实证)
        显式 rows_root 仍落在给定树 ⇒ 生产路径未被默认值废掉
```

**⇒ 这组对照是好的: 它同时证明了"写被隔离了"、"隔离没把行悄悄丢掉"、"生产路径仍然通" —— 三件都要, 缺一件就能被绕过。**

**★ 缺的那一个: `digest()` 自己的红能力。** 套件里**没有**"追加一字节 ⇒ digest 改变"的对照。若 `digest()` 哪天退化 (读空、返回常量), **所有 byte-identical 断言都会空过**。

**⇒ 我在外部补测了: `e346432021b0` → 追加一字节 → `8d329ac99ccf` ⇒ 敏感 ✓。⇒ 所以今天的结论成立; 但这条对照**不在套件里**, 未来无人守。(未经裁定: 建议并入该套件。)**

## ③ 协议侧: **已完成 —— 但派工给我的 sha 是错的**

| | |
|---|---|
| 派工要求 pin | `e9d531f1083ef…55d27` |
| **实际冻结** | **`9a033684be07bcd8d27a3ea1b7624467e15f29f42c4ffd88f0e618f19ebac99c`** (冻结于 **17:21:24Z**) |
| 现在的检查 | `check_metrics_freeze.py` ⇒ **`FROZEN_MATCH`, exit 0** ⇒ **阻塞 A 已解除** |

**⇒ 为什么会差: `e9d531f1` 是**我 17:0xZ 测到的中途字节**; 之后 0B 按**我提的精度修正** (m4 的崩溃红 vs 稀释红分开写 + 记入 `m1:93` 的同族守卫) 又改了注释 ⇒ 文件再次变哈希 ⇒ 最终是 `9a033684…`。**

> **★ 我按指示直接写 `e9d531f1` 就会把协议钉在一个**已被取代的中间态**上 —— 正是我当初提出"协议与代码必须一起落地"时要防的那件事, 差点由我自己犯下。⇒ 教训: **pin 一个哈希之前, 去读它此刻的真值** —— 不要用转述值, 哪怕转述者是几分钟前的权威。⇒ 而它之所以会动, 恰恰是因为我自己的意见被采纳了。**

**`004f0f7`**: 本仓唯一一处在 `anchor_coverage_table.md`, 是一句**关于 02:59/03:05Z 那两次提交的、正确的历史陈述**。**⇒ 我没有"刷掉"它 —— 改写一条准确的历史记录违反"never rewrite historical labels"。** lead 所指的陈引在 `dl_quant_live/docs/OPEN_ITEMS.md`, 0B 已自行更新为 `9a033684…`。

---

## 终审结论

| 项 | 判定 |
|---|---|
| ① 电池修复 | **不通过** —— 解释器未钉 ⇒ 3 条 known-fail 里 2 条为假; 且两个同名 runner 各自独占检查项, `metrics_freeze` 对 0B 用的那个不可见 |
| ② e 隔离 | **通过** (缺 `digest` 自身红能力对照, 我外部补测通过, 建议并入) |
| ③ 协议 pin | **完成** —— 已按实测真值 `9a033684…` 更新, 并记录了差点钉错 |
| 阻塞 A (冻结漂移) | **已解除** (`FROZEN_MATCH`) |
| 阻塞 B (9 套件不在电池) | **由我撤回** (我看错了 runner) |
