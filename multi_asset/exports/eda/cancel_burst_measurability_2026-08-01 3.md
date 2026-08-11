> **创建:** 2026-08-01 09:0x UTC | **Session:** 0C (审计角色, 只读) | **状态:** final | **作废条件:** (a) `cancel_resting` / `RateBudget.spend_request` / `binance_broker._request` 三处任一被改动 —— 本文件的定性与"缺什么字段"的结论须重核; (b) 场所开始返回 raw-request 计数头(见 §4) —— 则 §4 的"该维度不可观测"作废; (c) `cancel_ts` 的继承缺陷被修 —— §1 的 174 之谜不再存在, 本文件降级为事故留痕。

# k-cancel burst 的可测性 —— `cancel_ts` 是什么、能不能重建发出速率、最小改法、以及 DELETE 记在哪本账

**范围:** 只读审计, **未改任何代码, 未重跑回测**。所有引用给 `文件::符号`, 不给行号(`scheduler/anchor_loop.py` 等文件在审计期间正被并发编辑, 行号是移动靶)。

**背景(来自 `PREREG_DEVIATION_weight_switch_2026-08-01.md` §4.7):** 四次 -1003 全落在 k-cancel burst, 而该 burst 的瞬时速率是账本里唯一测不到的量。本文件把这个盲点定性、定位、并给出最小修法。

---

## 1. `cancel_ts` 到底是什么时刻

### 1.1 定性: 它是**单次撤单成功返回后的本地完成时刻**, 且**只在成功时写**

证据 (`live/binance_executor.py::BinanceExecutor.cancel_resting`):

```
for p in live:
    _pacer.pace()                                            # ← 节流睡在调用之前
    cid = f"{rebalance_id}-{p['symbol']}-1"[:36]
    try:
        resp = self.broker.cancel_order(...)                 # ← DELETE 在这里发出并等回包
        p["cancel_ts"] = time.time()                         # ← 赋值在**返回之后**
        ...
    except Exception as e:
        out["errors"].append(...)                            # ← 失败路径**根本不赋值**
```

⇒ `cancel_ts` 与"DELETE 调用发出"之间隔着: **请求构造 + HMAC 签名 + `_rl_wait_if_near_limit()` 的场所背压等待(每次 5.0 s) + `RateBudget.spend_weight/spend_order/spend_request` 三个整形器的等待(可达数十秒) + 网络往返 + 场所处理 + 回包解析**。这些量**没有任何一个被记录**, 因此 `cancel_ts` 减不回发出时刻。

**⇒ 它是完成时刻(completion), 不是发出时刻(emission)。**

### 1.2 与之对照: maker 侧的 `submit_ts` **是**发出侧的时刻

`live/binance_executor.py::BinanceExecutor.submit_maker` 里 `p["submit_ts"] = time.time()` 位于 `self.broker.submit(order, ...)` **之前**。⇒ 两条腿的同名语义相反: **maker 记发出意图, cancel 记完成**。

**自查(对我上一份交付的确认, 不是更正):** 上一份文件 §4.1 用 `submit_ts` 逐分钟坐实"峰值那一分钟是 maker burst" —— 该结论成立, 因为 `submit_ts` 确实在发送侧。**但需补一句精度: 它落在该次调用**自身**的整形器等待之前, 因此它是"取得配额前的意图时刻"; 由于循环是串行的, 上一次调用的等待已计入下一次的 `submit_ts`, 所以逐分钟计数最多在分钟边界上错一格, 不影响"97 那一分钟是 maker burst"。

### 1.3 §4.7 那个 174 之谜: 是**共享 plan dict 的继承**, 已实测坐实

对 `rebalance_id A1785571266` 的 198 行逐行统计:

| | 有 `cancel_ts` | 无 |
|---|---|---|
| `maker` | **87** | 22 |
| `topup_taker` | **87** | 2 |

**87 个 topup 行的 `cancel_ts` 与同 symbol 的 maker 行 `cancel_ts` 逐位相同(87/87 完全相等, 0 个不同)。** ⇒ 174 = **87 真值 + 87 继承副本**。top-up 行与 maker 行共用同一个 `p` dict(`binance_executor` 已在别处登记过同族缺陷: `filled_notional` / `fee_paid` 的继承), `_order_row` 里 `"cancel_ts": p.get("cancel_ts")` 于是把 maker 的撤单时刻原样刻到一条**从未被撤销过的 IOC 行**上。

**去重后的真实完成节奏:** 08:16 分 **36** 个, 08:17 分 **51** 个, 合计 **87** —— 全部 ≤ 进程自计 peak orders/min = 97。**§4.7 里"102 > 97 所以 `cancel_ts` 不是逐次时刻"的推理方向正确, 但真正的原因是记录重复, 不只是时刻语义。两者都成立: 语义是完成时刻, 且计数被重复了一倍。**

### 1.4 缺口的锐利处: **失败的那两笔没有任何时间戳**

`DOGEUSDT` / `TIAUSDT`(今天被 -1003 打掉的两笔撤单)实测: `terminal_reason = partial_expired`, `submit_ts` 有, **`cancel_ts = None`**。

而 `binance_executor.py::sweep_stale_orders` 的注释已经把这件事写死过:

> **Different causes, identical signature: `partial_expired` with `cancel_ts=null`, and nothing that ever looked again.**

⇒ **撤单失败与"这单本来就没在挂"在行里是同一个签名。** 今天 109 个 maker 行里 22 行 `cancel_ts=None`, 其成分是 11 `skipped_min_notional` + 8 `venue_reject` + 1 `skipped_no_mid` + **2 `partial_expired`(= 真正的撤单失败)**。**要把那 2 笔从 22 笔里分出来, 只能靠 `phase_B` 日志里的 `k_cancel.errors` 字符串, 行本身分不出来。**

---

## 2. 现有记录能否重建**发出**速率

## 答: 不能。

| 想要的量 | 现有记录 | 判定 |
|---|---|---|
| DELETE 的**发出**时刻 | 无任何字段 | ❌ 不存在 |
| DELETE 的**完成**时刻(仅成功者) | `cancel_ts`(需先去掉 87 个继承副本) | ⚠️ 可得, 但不是发出时刻, 且**漏掉全部失败者** |
| 每次调用的等待时长 | `RateBudget.stats` 只有**全锚点累计** `wait_seconds` 与 `waits` 次数, 不分维度到调用 | ❌ 减不回去 |
| 场所背压等待 | `VENUE_RL["waits"] / ["wait_s"]` 同样只有累计 | ❌ |
| 逐请求时间线 | `RateBudget._requests` **确实是逐请求时间戳列表**, 但 `spend_request` 每次进来先执行 `self._requests = [t for t in self._requests if now - t < 60]` —— **60 秒以外的全部丢弃**; `snapshot()` 也只返回计数不返回时间戳 | ❌ **数据在内存里存在过, 被主动丢弃了** |

**⇒ 缺的字段有且只有一个: DELETE 请求在取得配额之后、写 socket 之前的那个时刻。** 其余一切(完成时刻、累计等待、峰值)都无法反推它。

### 2.1 能重建的那一半(明标口径), 以及它已经说明的事

用去重后的 87 个**完成**时刻, 今天 08:00Z 那一锚的 k-cancel:

```
n = 87 (成功者; 另 2 笔失败无时刻)
跨度 85.7 s        平均间隔 1.00 s   中位 0.97 s   最小 0.11 s   最大 2.06 s
隐含完成速率 = 60.9 /min
逐分钟: 08:16 → 36    08:17 → 51
```

中位间隔 0.97 s 紧贴 `rate_budget.BURST_MIN_INTERVAL_S = 0.9` ⇒ **`BurstPacer` 在生效, 是它决定节奏。**

**★ 这半个重建已经足以推翻一个直觉: k-cancel burst 在我们自己的账本里根本不密集 —— 约 61 次/min, 对 300 orders/min(20%)与 600 requests/min(10%)。四次封禁落在这里, 不是因为这个 burst 快。** (最小间隔 0.11 s 出现过一次, 短于 pacer 下限, 说明存在 pace 未生效的路径或时钟抖动 —— 值得 0B 看一眼, 但单次 0.11 s 不足以造成任何限流。)

**这一半的三个不可修补的洞, 明说:** (a) 完成 ≠ 发出, 二者差一个不被记录的可变等待; (b) 失败者完全缺席, 而失败者正是我们要研究的对象; (c) 该重建**依赖去重**, 而去重靠的是"topup 与 maker 的值逐位相等"这一观察 —— 一旦某天 topup 真的产生了自己的撤单, 这个去重规则会**静默地把真值当副本删掉**。

---

## 3. 最小可测方案 —— 目标是 **DELETE 的发出时刻**

### 方案 A (**推荐**): 给 `RateBudget` 的请求时间线加标签并留档 —— 不碰执行路径

**依据: 想要的时刻在代码里已经被计算出来了, 只是被丢弃。** `binance_broker::_request` 的顺序是

```
_rl_wait_if_near_limit()      # 场所背压等待
BUDGET.spend_request()        # ← 取得配额的瞬间; 此后才构造/签名/写 socket
BUDGET.spend_weight(...)
if path in ("/fapi/v1/order","/fapi/v1/batchOrders") and method in ("POST","DELETE"):
    BUDGET.spend_order()
```

`spend_request()` 内部 `self._requests.append(now)` 的那个 `now`, **就是"配额到手、即将发出"的时刻, 且它对成功与失败一视同仁**(记账在发送之前, 见 `_request` 的 `★ SPEND BEFORE SENDING` 注释)。

最小改动三处, 全在**记账层**, 执行路径一行不动:

1. `rate_budget.RateBudget.spend_request(tag: str = "")` —— 多一个参数; 在现有 `self._requests.append(now)` 旁边多一句 `self._req_log.append((now, tag))`(**append-only, 不参与那句 60 s 裁剪**)。
2. `binance_broker::_request` —— 把 `BUDGET.spend_request()` 改成 `BUDGET.spend_request(f"{method} {path}")`。**一个实参。**
3. 锚点收尾处把 `BUDGET` 的 `_req_log` 落盘(与现有 `rate_budget:` 那行日志同一个位置)。

代价: 每锚 ~757 条 `(float, str)` ≈ 25 KB; 与现有 `orders.jsonl`(今日 391 KB)同数量级以下。
收益: **逐请求、带端点标签、含失败者的发出时间线** ⇒ k-cancel burst 的每秒/每分发出速率可直接画出, 且顺带把 maker burst、fills 回读、top-up 三段都分开了(目前 `requests_peak_per_min = 270` **归属不明**, 记录里查不出它属于哪一段)。
**不需要 schema 变更**(不新增 `orders.jsonl` 列 ⇒ 不触发 `log_schema_falsify_v2` 的口径面)。

### 方案 B (备选, 若 `rate_budget` 不可动): 镜像 maker 侧, 在 `cancel_resting` 里加一个前置时戳

在 `try` **之外、之前**写 `p["cancel_req_ts"] = time.time()`(放在 try 外, 失败者才拿得到), 并在 `live/pilot_log.py` 的行 schema 里加 `cancel_req_ts` 一列。

**比 A 差在三点, 必须一并交代:** (a) 它记的是"进入调用前"而不是"取得配额后", 中间隔着该次调用自身的两层等待(场所背压 5 s + 整形器), 因此在被限流的那一刻误差最大 —— **恰恰是我们最想测准的时刻**; (b) 需要新增一列 ⇒ 触发 schema 面; (c) 它写在 `p` 上, 会**继承同一个共享 dict 缺陷**, 于是新列上市第一天就带着 §1.3 那个 87 副本的问题, 除非同时修 `_order_row`。

### 方案 C (不推荐, 记录以免被当成免费选项): 用 `broker.actions`

`binance_broker::cancel_order` 对成功写 `{"action":"cancel", ..., "ts":...}`, 对异常写 `{"action":"cancel_noop", ..., "ts":...}`(**在 `-2011` 判定之前, 因此失败者也有记录**)。⇒ 覆盖面比 `cancel_ts` 好。但 (a) 两个 `ts` 都在 `_request` **返回之后**取, 仍是完成时刻; (b) `self.actions` 是纯内存 list, **grep 全仓无任何落盘点** ⇒ 现在等于不存在。要用它得先加持久化, 那不比 A 小。

**结论: 选 A。它是唯一一个既覆盖失败者、又真的落在发出侧、又不需要动执行路径与行 schema 的方案。**

---

## 4. DELETE 记在哪本账 —— 我方与场所

### 4.1 我方: **三个维度全都记**

`binance_broker::_request`(逐字):

```
BUDGET.spend_request()                                       # 请求数: 记
BUDGET.spend_weight(self._WEIGHTS.get(path, 1))              # 权重: /fapi/v1/order = 1, 记
if path in ("/fapi/v1/order","/fapi/v1/batchOrders") and method in ("POST","DELETE"):
    BUDGET.spend_order()                                     # 订单配额: DELETE 明确在内, 记
```

`docs/API_SEMANTICS.md` 的端点表与代码一致: **`/fapi/v1/order` | 权重 `1 (+订单配额)` | 消费者列出 `submit / cancel_order / last_fill_details`。**

⇒ **不存在"我们把撤单记漏了"这回事。** 并且 `cancel_order` 走的是**按 client id 的单笔 DELETE**, 不是 `allOpenOrders`(执行器注释明确禁止在交易路径用后者)。

**唯一的记账不对称(与今天无关, 但登记):** `/fapi/v1/allOpenOrders`(DELETE, 由 `cancel_all_open_orders` = flatten/watchdog 路径使用)**不在**上面那个 path 元组里 ⇒ 它花请求与权重, **但不花订单配额**。它不在锚点交易路径上(`API_SEMANTICS` 也标注"运维工具, 非锚点路径"), 所以今天的封禁与它无关; 但**熔断 flatten 时它会在最紧张的时刻少记一个维度**。

### 4.2 场所: 三个维度里**只有两个可观测**, 而封我们的正是那个不可观测的

`binance_broker::_rl_observe` 解析回包头:

| 维度 | 场所返回的头 | 我们能不能看见 |
|---|---|---|
| 权重 | `X-MBX-USED-WEIGHT-1M` | ✅ |
| 订单数 | `X-MBX-ORDER-COUNT-1M` | ✅ (仅订单类端点回包带) |
| **原始请求数** | **没有对应的头** | ❌ **完全不可观测** |

而 -1003 的报文原话是 **"current limit of IP(...) is 6000 **requests**"** —— **场所据以封禁的那个维度, 没有任何可读的计数器。** 我方 `REQUESTS_PER_MIN = 600` 这个上限, 其注释已自认是从报文文本**推断**的窗口("the request cap is INFERRED from the -1003 text ... which named 6000 requests without a window")。

### 4.3 "自己没打满却被封"的真实解释: **不是维度错配, 是口径人口错配**

今天 08:00Z 那一锚三个维度的实测:

| 维度 | 我方进程自计峰值 | 我方上限 | 场所计数器 | 场所公布(testnet) |
|---|---|---|---|---|
| orders/min | 97 | 300 (32%) | **97** (`peak_order_count_1m`) | 1200 |
| requests/min | 270 | 600 (45%) | **不可观测** | 6000(仅见于报文) |
| weight/min | **1000(顶格)** | 1000 (100%) | **6152** (`peak_window_weight`) | 6000 → **已越线** |

**⇒ 越线的是 weight, 越的是场所那本账: 6152 > 6000。而我方同一分钟自计不超过 1000。差额 `gap_vs_this_process = 6127`。**

`_rl_observe` 的注释已经把机制写死了, 与你的猜想同形但更具体:

> `BUDGET` 是 per-process singleton, 所以这个 IP 上的**其他每一个进程** —— 健康检查、安装脚本、运维探针 —— 各自带着一个从零开始的钱包, 谁也看不见谁。**场所的头一次看见全部。**

再叠加一层已登记的不确定: 被封的 IP `130.176.187.110` 是 **CloudFront 边缘**, 不是我方出口 `103.252.201.68` ⇒ 那 6152 里有多少是我们的, **归因 UNVERIFIED**。

**⇒ 对你的判断的直接回答: 「两套账各自都没超, 合起来超了」——方向对, 但拆法不是"我们记 A 场所记 B"。三个维度上我们和场所记的是同一件事(撤单在两边都算订单、都算权重、都算请求)。分裂在于**统计人口**: 我们的账本是"本进程", 场所的账本是"整个 IP(且可能是一个共享边缘)"。同一维度, 不同人口, 差 6127。**

### 4.4 一个**记录不足以判定**的问题, 明说

"场所的 `X-MBX-ORDER-COUNT-1M` 到底算不算 DELETE" —— **从今天的记录判不了。** 我方逐分钟订单数是 maker 分钟 97 / 撤单分钟 36 与 51, 峰值 97; 场所报的峰值也是 97。**若场所算撤单, 峰值仍是 97(来自 maker 分钟); 若不算, 峰值还是 97。两个假设给出同一个观测值。** 要判定必须留**逐次**的头读数, 而 `_rl_observe` 只保留 `max`。⇒ 方案 A 若顺带把每次读到的头值也追加进同一条时间线(`spend_request` 的 tag 之外再存一个观测值), **同一次改动即可把这个问题变成可判定的** —— 建议一并做, 但它是加分项, 不是本次要求。

---

## 5. 顺带一条(超出所问, 但便宜且与 burst 规模直接相关)

今天 89 次 DELETE 里 **65 次(73%)的回包是 `-2011 already_terminal`** —— 即**七成的撤单请求花在"发现这单本来就不在挂"上**。`cancel_order` 的注释已写明 `-2011` 同时覆盖"已成交/已过期"与"从未存在", 不可用于推断成交。

⇒ burst 的规模(89)里有 65 是**可事先知道**的信息。**不评估修法**(读取顺序涉及"撤单必须先于读成交"这条已用事故换来的不变量, 不是我这次的范围), 只登记: **若要压 burst 规模, 这 73% 是最大的一块, 而不是换权重带来的那 +3~5%。**

---

## 6. 未核实(明标)

1. `requests_peak_per_min = 270` 属于哪一段(maker / k-cancel / fills 回读 / top-up)—— **记录里查不出**, 只保留了峰值不保留时间线。按端点权重表估算, fills 回读(`allOrders`×110 + `userTrades`×110)是候选大头, 但**这是估算不是观测**。
2. 场所 `X-MBX-ORDER-COUNT-1M` 是否计入 DELETE(§4.4)。
3. 最小间隔 0.11 s 那一次为何短于 `BurstPacer` 的 0.9 s 下限。
4. 测试网与主网的限流数值不同(`venue_limits` 实测 testnet REQUEST_WEIGHT 6000/1m vs mainnet 2400/1m), 本文件所有场所侧读数均为 **testnet** 口径。
5. `RateBudget` 是 per-process 单例, 因此本文件所有"我方"读数都只是**锚点进程这一个钱包**; 同一 IP 上其他进程的支出不在其中(这正是 §4.3 的机制)。

---

# 附录 (2026-08-01 09:3x UTC 追加) — 6.15× 的判别: H1 邻居 vs H2 我方权重表

**问题:** `gap_vs_this_process = 6127`, 6152/1000 ≈ 6.15×。H1(共享边缘的邻居流量)预测比值随机漂; H2(我方 `_WEIGHTS` 系统性低估)预测比值稳定且随我方用量同向。

**方法:** 把 `state/anchor_runs.log` 全部 `rate_budget:` 与紧随其后的 `venue_rate:` 行逐锚配对。**未发任何新请求。** 场所侧头读数自 2026-07-31T04:36Z 才开始记录(此前 `_rl_observe` 尚未上线)⇒ **07-29 与 07-30 两次封禁没有场所侧数据, 本判别只覆盖后两次。**

## A1 配对结果 (n=23 锚, 其中我方峰值顶格 1000 的 6 锚)

| ts (UTC) | 我方 weight_spent | 我方 requests | 我方 w/req | 场所 peak_window_weight | 比值 vs 1000 |
|---|---|---|---|---|---|
| 07-31T08:21 | 4734 | 685 | 6.91 | 6767 | 6.77 |
| 07-31T16:23 | 5207 | 719 | 7.24 | 6709 | 6.71 |
| 07-31T20:24 | 6381 | 1011 | 6.31 | 4130 | 4.13 |
| 08-01T00:20 | 5241 | 253 | **20.72** | 1747 | **1.75** |
| 08-01T04:23 | 6398 | 727 | 8.80 | 4458 | 4.46 |
| 08-01T08:23 | 5745 | 757 | 7.59 | 6152 | 6.15 |

全部 23 锚的比值(场所峰值 / 我方峰值): min 0.08, max 6.77, median 0.71, **CV 1.28**。

## A2 判词: **两个假设都被证伪, 存活的是第三个 —— 而它仍然在我们这边**

**H1(邻居)被证伪 —— 两条独立证据:**
1. **我方空闲时场所计数器接近零.** 16 次只发 2–3 个请求的运行, 场所 peak 全部落在 **5 / 33 / 34**, 从无一次上千。邻居流量不会只在我们跑锚点时出现。
2. **corr(场所峰值, 我方 requests_spent) = +0.933**(与 weight_spent 亦 +0.899)。**场所那本账随我们自己的用量走。**

**H2(单一稳定倍数)也被证伪:** 6 个顶格锚的隐含倍数 **1.75 – 6.77, CV 0.39**。不是一个常数。

**存活的 H3 = 端点相关的低估, 且有正向指纹:**
> **corr(比值, 我方平均 weight/request) = −0.818** (n=6)。
> 即: **我们自己给某锚的流量记的单价越低, 场所超出我们越多。** 那个唯一的低比值锚(1.75)恰是单价最高的(20.72), 而 4.1–6.8 的高比值锚单价都在 6.3–8.8。

## A3 代码里找到的机制 —— 比"表里某个数字写小了"更根本: **两本账数的不是同一群请求**

`signal/fapi_source.py::FapiSource`(preds 生产者的行情读取路径, 每锚 140 symbol 的 klines + funding)有三处与 `binance_broker::_request` 不对称:

1. **`_throttle` 只调 `BUDGET.spend_weight(weight)`, 没有 `spend_request()`** ⇒ **整条读取路径完全不在请求预算里。** `requests_spent=757` 只是 broker 的请求数; 场所计的是全部。**而 -1003 封的正是请求维度。**
2. **该路径从不调 `_rl_observe`** ⇒ 我们读到的 `X-MBX-USED-WEIGHT-1M` **只采样自 broker 调用**, 读取路径的流量既不计请求也不被观测。
3. **`_get` 的 `_throttle` 在重试循环之外** ⇒ `RETRIES = 3`, **重试在我们账上免费, 在场所账上每次都是真请求。**

**★ 而且两条路径打的不是同一个场所:** `fapi_source.BASE = "https://fapi.binance.com"`(**主网**), broker 在 `BASE_TESTNET = "https://testnet.binancefuture.com"`(`state/testnet/.mode` = TESTNET)。**同一个 `BUDGET` 单例把主网行情权重与测试网订单权重加在一起整形, 而我们拿来对比的 `peak_window_weight` 是测试网那个 IP 的计数器。**

⇒ **`6152 vs 1000` 这个比值本身不是任何一个量的干净测量: 分母混了两个场所的支出, 分子只来自其中一个。** 6.15× 既不能读成"邻居占了 5152", 也不能读成"我们的表低估 6.15 倍"。

## A4 对修法的直接影响

**你的操作性结论成立: 整形器确实没在整形, 且原因在我们这边, 不在邻居。** 但修法不是(只是)改权重表里的数字:

1. **`fapi_source._throttle` 必须同时 `spend_request()`** —— 这是三个维度里唯一一个整条路径缺席的; 也是唯一一个把我们封掉的维度。
2. **`_throttle` 必须移进重试循环**(或重试单独计费)。
3. **两个 host 应各有各的预算**(场所按 IP×host 分别限流; 一个混合钱包对哪一边都不准), 或至少在日志里分开报。
4. **权重表的逐端点核对目前做不了 —— 明说.** `_rl_observe` 只保留 `max` 与 `last`, **逐次的 `X-MBX-USED-WEIGHT-1M` 增量没有留存**; 而读取路径**根本不读头**。⇒ **从现有记录无法算出任何单个端点的真实权重**, 我也不会去发请求测它。**唯一的仪器就是 §3 方案 A 那一条: 给逐请求时间线加 `tag`, 并把每次读到的头值一起存下来 —— 单个端点的真实权重就是这条序列的一阶差分。一次改动同时关掉 §2(撤单发出速率)与本节(逐端点权重)两个盲点。**

## A5 顺带一条(小, 但会让背压门槛在不同进程里不一样)

23 锚里 `published REQUEST_WEIGHT` 出现两个值: **6000**(跑过 exchangeInfo 的锚点进程)与 **2400**(短运行, 未读取 ⇒ 用了默认值)。`_rl_wait_if_near_limit` 按 80% 触发 ⇒ **同一台机器上, 背压门槛在 1920 与 4800 之间取决于该进程有没有读过 exchangeInfo。**

## A6 本节未核实

1. 07-29 / 07-30 两次封禁**无场所侧数据**, 结论不覆盖它们。
2. 逐端点真实权重(见 A4-4)。
3. 空闲分钟的场所读数在 5 与 33/34 之间跳动(我方支出完全相同), 差 ~29 —— 这确实是一部分带外流量, **但量级是几十, 不是几千。**
4. 6 个顶格锚的样本量小; −0.818 的相关是指纹不是证明。
