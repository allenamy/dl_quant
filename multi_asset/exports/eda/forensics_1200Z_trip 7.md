> **创建:** 2026-07-26 13:0xZ | **Session:** ma-v2 0C 独立取证 | **状态:** final | **作废条件:** 若 0B 的 E1-E6 判分器给出与本文分解矛盾的数字, 以两边交叉后 team-lead 的裁定为准

# 12:00Z 大考锚点 trip 的独立取证 (0C)

## ★★★ 一 (最紧急, 与派工无关但压过它): **两个仓位此刻仍是活的**

`state.json`: **`flatten_ok: False`**; ALARM 12:18:42Z: **`FLATTEN FAILED — positions may be stuck`**。

```
flatten_all 尝试 1: n_orders=103  失败 103/103   [-1111] Precision is over the maximum defined for this asset
flatten_all 尝试 2: n_orders=103  失败   2/103   [-4005] Quantity greater than max quantity
flatten_all 尝试 3: n_orders=  2  失败   2/2     [-4005] 同上
```

**⇒ 卡住的两个名字 (逐字来自 `events.jsonl` 的 `flatten_all.failed`):**

| symbol | side | quantity | 错误 |
|---|---|---|---|
| **MEMEUSDT** | buy | 271229.0 | `[-4005] Quantity greater than max quantity` |
| **1000BONKUSDT** | buy | 165709.0 | `[-4005] Quantity greater than max quantity` |

**⇒ 这两个仓位无法由现行梯子平掉 —— `flatten_all` 每个 symbol 只下**一张**单, 不按场所的 `maxQty` 切块。⇒ 系统已 halt(不再开仓)、reduce-only 已启用, 但**这两个头寸是活的、有方向的敞口**, 且梯子每次重试都会以同样的方式失败。**

### 顺带查出: 尝试 1 之所以 103/103 全败, 是一个**单位错误**

`watchdog.run()` 构造 `pos = {sym: float(r["venue_position_notional"]) ...}` —— **名义 USD**;
`flatten_all(positions, ...)` 用 `"quantity": abs(v)` —— **把名义当成了数量**。

⇒ 尝试 1 提交的是 `1000BONKUSDT buy 515.97971293` (名义), 被拒 `[-1111] Precision`;
⇒ 重试前"重读持仓"改用合约张数 (`165709.0`), 于是尝试 2 有 101 个成功。

**⇒ 即: 每一次 trip 的**第一次**平仓尝试都结构性必败, 只有"重读后的重试"真正平仓。** 00:17Z 那次的 `53/54` 是同一形态 (那次只有 1 个名字的名义数恰好是合法数量)。

---

## 二 (派工 ①): **B19 归档在这次 trip 上并未被检验** —— 它走的是"无可归档"分支

`state/testnet/watchdog/` 下**没有 `archive/` 目录**; `ALARM.log` 里**没有** `trip-state archive FAILED`。

**读码: B19 归档的是*即将被覆盖的那一份* (`if os.path.exists(state_p)`)。而 08:20Z 清除时 `state.json` 已被移除 ⇒ 12:00Z 这次 trip 写 state 时, 没有前一份可归档 ⇒ 归档块空转。**

**⇒ 结论: 归档**没有失败**, 但它**也没有被证明**。这次 trip 恰好是"清除后的第一次", 是唯一一种走不到归档路径的情形。⇒ B19 的红能力仍未在真 trip 上见过 —— 要见到它, 需要**同一棵树上的第二次 trip**(即下一次覆盖发生时)。**

**事发 state 当前完好** (`tripped_at 2026-07-26T12:17:31Z`, 三条 flatten 错误俱在)。**我已按 sha256 快照留存五件** (`_post1200_{state,ALARM,events,last_eval,trip_receipt}` + `_post1200_hashes.txt`) —— **这次不是靠侥幸, 是因为上一轮的教训让它成了流程**; 但请注意**这仍是审计侧的旁证**, 不能替代 B19 自己被证明。

---

## 三 (派工 ②): 77 个异常的独立分解 —— **是对账口径缺口, 不是缺陷复发**

**方向就是判据**: 原事故是**场所**持有台账的 2 倍; 这次是**台账**声称场所的 2 倍。

```
last_reconciled_ats = 1785067248.199   latest = 77   historical = 178
消费窗 (1785053771.3, 1785068250.9]  含 181 条 in-ledger 成交: maker 78 + topup_taker 103
77 异常名 ∩ 有 topup 成交 = 77/77      77 异常名 ∩ 有 maker 成交 = 77/77
77 异常名中窗内完全没有被消费成交的 = 0
```

| 分组 | 计数 | 其中异常 |
|---|---|---|
| **两腿都"成交"** | 78 | **77** |
| 仅 topup 成交 | 25 | **0** |
| 仅 maker 成交 | 0 | 0 |
| 异常但不属以上任何组 | — | **0** |

**⇒ 异常集合 = "maker 腿成交且 topup 行也带成交额"的名字集合 (78 中的 77)。**

### 逐行看, 结论是自明的

| symbol | maker attempt1 | topup attempt2 |
|---|---|---|
| LISTAUSDT | intended 645.11 → **filled 644.4325** | intended **0.68** → **filled 644.4325** |
| ZILUSDT | intended 645.11 → **filled 644.978358** | intended **0.13** → **filled 644.978358** |
| DOGEUSDT | intended −553.05 → **filled −553.026** | intended **−0.03** → filled **−553.026**, `terminal_reason = skipped_min_notional` |

**⇒ topup 行的 `filled_notional` 是 maker 腿成交额的**继承值**, 不是它自己的成交。它自己的 `intended` 只有 0.68 / 0.13 / −0.03。**

**⇒ 决定性一行: DOGEUSDT 的 topup `terminal_reason = skipped_min_notional` —— 这张单**从未提交**, 却带着一个非空的 `filled_notional`。一张没发出去的单不可能有成交。**

**⇒ 机制: 共享 plan dict 的继承** —— 正是 `binance_executor.py:349` 注释里点名的那一族 ("shared-plan-dict inheritance in this function (filled_notional, fee_paid, now this)")。**该注释警告的第三个字段就是它自己, 而防线没有覆盖到 `filled_notional` 在 topup 腿上的这条路径。**

### ⇒ 由此, §4-5b 这次是**假阳性**

- 台账 `Σfills` 把每个双腿名字**数了两遍** ⇒ `expected ≈ 2 × 真实`;
- 场所 readback 是**对的** (`observed` = 真实);
- ⇒ `unexplained_frac ≈ 0.500` 均匀出现在 77 个名字上 —— **一个原因, 一个族群**;
- ⇒ **书的规模是对的; 错的是记录。** 与 00:17Z 那次(场所真的 2 倍)方向相反。

**⇒ 但 §4-7 与 5b 同源, 所以它也是同一个假阳性 —— 两个触发仍然只是同一个探测器数了两遍。**

---

## 未经单独检验的步骤清单

1. **我未独立向场所确认 MEMEUSDT / 1000BONKUSDT 此刻的真实持仓** —— 上面的"活的"是从 `flatten_all.failed` + `flatten_ok: False` 推出的, 不是直读。**这条应由能读场所的一侧立刻证实。**
2. **78 个双腿名字里那 1 个不异常的, 我没有查是哪个、为什么** —— 它可能是分解的反例, 也可能只是 maker 成交额小到 frac ≤ 0.10。
3. **"尝试 1 传的是名义"我读的是 `watchdog.run` 的构造点与 `flatten_all` 的签名**, 未在运行时打印证实; 但两次尝试的量级差 (515.98 vs 165709.0) 与错误码 (`-1111` → `-4005`) 与该读法一致。
4. **`n_historical = 178` 我没有分解** —— 其中含 00:17Z 的 47 + 04:15Z 的 54 + 本次 77 = 178, 数目吻合, 但我未逐条核。
