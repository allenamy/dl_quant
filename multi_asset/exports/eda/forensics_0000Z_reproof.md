> **创建:** 2026-07-27 00:3xZ | **Session:** ma-v2 0C 独立取证 | **状态:** final (Phase 1 根因定位完成; 修复不由我提) | **作废条件:** 0B 的独立分解给出与本文矛盾的边界证据

# 00:00Z 重证明 FAIL — 独立分解 (0C)

**方法: 按 systematic-debugging 的 Phase 1 —— 先在**每个组件边界**取证, 再定位断点。不提修法。**

## 项 1 — 92 个异常的逐名分解: **签名极干净**

```
n_latest = 92     n_historical = 372
frac 分布 = {1.0: 92}          ← 全部 1.0, 无一例外
最新 readback 非零名字 = 92
92 异常 ∩ 92 非零名字 = 92     ← 完全同一集合
```

**⇒ 回答 lead 的问题: **"全 1.0 = 无 fills 可消费的签名"—— 确认**。`frac = 1.0` 意味 `expected = 0`, 即 `prev = 0` 且 `consumed = 0`。⇒ 书从平仓建到 92 个名字, 而台账里**一条成交都没有**可以解释它们。**

> **★ 与 12:00Z 那次是**同类不同因**: 那次 `frac ≈ 0.5` (台账**双计**); 这次 `frac = 1.0` (台账**零计**)。⇒ **方向仍然是判据**: 0.5 = 台账多算一倍; 1.0 = 台账什么都没算。**
> **⇒ 且这次 5b **不是假阳性**: 92 个仓位确实"未被台账解释"。缺陷在上游 —— 台账不知道成交发生过。**

## 项 2 — fills 断在哪一环: **断在 venue → orders 的**覆盖**上**

**逐边界取证:**

| 边界 | 证据 | 判定 |
|---|---|---|
| 场所侧成交是否发生 | `orders_spent=304` · 92 个名字真的建了仓 | **发生了** |
| 场所 → 台账 (`fill_details_for`) | **101/109 个 symbol 未进 `queried_ok`** | **★ 断在这里** |
| 台账 `filled_notional` | 101 行 `terminal_reason=skipped_unknown_fill`, `filled_notional=None` | 是上一环的**后果** |
| fill 行构建 | `fill_rows_built=0` | 是上上环的**后果** (没有 `filled_notional` 就无行可建) |

**机制 (逐行追到源头):**
```
anchor_loop.py:643-646   unknown = {s for s in live_syms if s not in _reached}
venue_fills.fill_details_for:  for sym in symbols: try: allOrders(sym); queried_ok.add(sym)
                               except Exception: continue        ← 吞掉, 不记原因
binance_executor.py:421  if p["symbol"] in unknown_fills:  → 行标 skipped_unknown_fill, 跳过补单
```

**⇒ 101 个 symbol 的 `allOrders` 调用**抛了异常**⇒ 未进覆盖集 ⇒ 全部按 UNKNOWN 跳过。**

### ★ 三处怀疑逐一排除

| lead 的怀疑 | 判定 |
|---|---|
| **e** `rows_root` 默认反转吞了写入者 | **排除** —— `rows_emitted 109 / rows_persisted 109`, 行**写下来了**; 断的是行**里的值**, 不是行的去处 |
| **a2** 终态条件 | **排除** —— 95 个 `protective_flatten` 行拿到了 `filled` 与非零 `filled_notional`, 说明终态读取本身能工作 |
| **b** 三类行改造 | **排除** —— 三类行都正确落盘且可区分 (`maker` 8 / `topup_taker` 101 / `protective_flatten` 95) |

### ★★ 但**为什么**那 101 个调用失败 —— **无法归因, 且这是本次最该修的**

**我先排除了自己的第一个假设**: 我一度读 `weight_spent=1560 > 自设上限 1000` 认定是限速。**错 —— 这是把总量当成了速率**: `spend_weight` 是**每分钟滚动窗**(`now - _w_start >= 60` 即重置), 而 1560 是**整个 ~20 分钟锚点的累计**。`waits=0` 与之一致。⇒ **预算守卫不背这个锅。**

**⇒ 真实原因**取不到**: `except Exception: continue` **不记录任何东西** —— 没有日志、没有按异常类型的计数、没有样本。⇒ 事后**无法**知道那 101 次是 429 / 超时 / 签名 / 别的。**

> **★ 这个吞异常是**故意**的, 而且它的目的正当 (让"没问到"不被当成"没成交" —— 覆盖集单独报出)。⇒ **但"不把缺席当成零"与"不记录缺席的原因"是两件事, 它只需要前者。** ⇒ 结果: 守卫做对了**判定**, 却让**诊断**无法进行。⇒ 一个按异常类型计数的计数器就能回答今天这个问题。**

## 项 3 — E 考卷可判性

| 科目 | 依赖 fills? | 本锚点可判? |
|---|---|---|
| M1 有效成本 | **是** (`filled_notional` + `avg_fill_px`) | **否** —— 101 行 None; 仅剩 95 个 `protective_flatten`(**平仓腿, 非再平衡腿**), 用它算 c 是**换了量** |
| M2 markout | **是** (fills 表) | **否** —— 本锚点 fill 行 0 |
| M3 成交率 | **是** (maker filled/intended) | **部分** —— 只有 8 个 maker 行 |
| M5 权重保真 | **否** (readback vs target) | **可判** |
| §4-5b / 4-7 | 否 | **可判**(且已触发) |

**⇒ 建议判词 (未经裁定): **考卷不作废, 但"成交口径"那几科作废** —— M1/M2 判 UNKNOWN 而非判差; M5 与止损侧照判。⇒ 理由与 §2.5.7 的合格日判据同源: **一个量没被测出来, 与这个量很差, 是两件事。****

## 项 4 — `factor_health STALE 28.2h`: 另一条线, 与本缺陷独立

告警原文: *"the shadow's own report is 28.2h old (limit 26.0h). A daily cron that logs `done` …"*
**⇒ 它量的是 shadow 日报的**新鲜度**, 与本仓的成交路径无因果关系 (成交缺陷不会让 shadow 报告变旧)。⇒ 归因需要 shadow cron 侧的日志, **在研究仓/服务器侧, 不在本仓** ⇒ 我此处只确认**独立**, 不做归因。**

---

## 未经单独检验

1. **"101 次调用抛异常"是由"未进 `queried_ok`"反推的** —— 该集合只在 `try` 成功时添加, 所以未进 = 抛了; 但我**没有**独立复现那 101 次调用;
2. **8 个成功的名字在字母序上偏后** (`ICP/NOT/ONE/OP/RENDER/SOL/ZIL/ZK`), 而失败的从 `1000BONK` 开始 ⇒ 形态像"前段失败、后段成功"。**我没有确认迭代顺序就是字母序** —— 若是, 这个"后缀"形态本身是线索 (例如某种在循环中途恢复的限制); 若不是, 该观察无效;
3. **项 3 的科目依赖是我读 `pilot_metrics` 得出的**, 未与 E 考卷的正式定义逐条对照;
4. **我没有查 92 之外那 17 个 live 名字** (109 − 92) 的去向。
