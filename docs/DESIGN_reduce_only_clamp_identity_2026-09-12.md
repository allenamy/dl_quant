> **创建:** 2026-09-12 13:2xZ | **Session:** https://claude.ai/code/session_01BzpuBRGZh8oPvpD8NgqsME | **状态:** 事实表 + 方案(W6, 克隆实现中; 部署与恢复 = 用户字) | **作废条件:** W6 落地后转收据; 或用户裁定回滚 d040c74

# DESIGN W6: E-0912-A 修复 —— reduce-only 截量不是矛盾, 全退出按持仓张数下单, 局部「未知」不平全书

**一句话**: 三处改动, 每处对应事实链的一环, 每处有会红的测试与旧码红。(a) `binance_broker.submit_identity_mismatch` 加第四态 **clamped**; (b) `binance_executor.plan` 全退出的数量 = 持仓张数; (c) 看门狗 §4-5b 对「场所记录自洽、仅我方读不出」的少数名执行**比例响应**(停开仓 + 告警 + 只处置那几名), 全书平仓保留给真实事件。(a)(b) 是点修; (c) 是书行为改动 ⇒ **需用户裁定**(本文给性质与判据, 不替选)。

## §1 事实表(收据 = ERROR_LEDGER E-0912-A 七条; 行号 = 运行树 918559f)
| # | 事实 | 位置 | 修哪一环 |
|---|---|---|---|
| F1 | 全退出(`target_w=0`, 持有)⇒ 计划 `reduce_only=True` ⇒ 回执 `"reduceOnly": true`(设计如此, 保留) | `anchor_loop.py` L1630, L1930–1932; `binance_executor.plan` L757 | — |
| F2 | 数量 = `round_qty(delta / mid)`; delta 由 `current_notional`(持仓 × mark)得 ⇒ mark ≠ mid 时数量 ≠ 持仓张数(MEME +294 张 = 0.015%; POPCAT +1) | `binance_executor.plan` L774 | (b) |
| F3 | 交易所对 reduceOnly 单 qty > 持仓: 截到持仓, 回执 origQty = 持仓(两名逐张相等), 不报错(-2022 只在无仓/方向错) | 回执 `events.jsonl` 12:47Z 行 submit/resp | (a) |
| F4 | `_ident_check(origQty)` 相对容差 1e-6 ⇒ 「differs from ours」⇒ `inconsistent = "submit identity: …"` 直接 return(不再读 executedQty) | `binance_broker.py` L343, L1487–1491 | (a) |
| F5 | `ledger_inconsistencies` 把任何 `inconsistent` 字符串收为矛盾; `reconcile` 第 5 轮「矛盾最先」⇒ `unquantifiable`; D2 ⇒ `execution_of_unknown_size` 异常 | `binance_executor.py` L163–175; `reconcile.py` L200–203, L455–473 | (a)(c) |
| F6 | §4-5b 状态门 M=1: 最新对账锚任一异常 ⇒ 触发; §4-7 漂移 = `bool(_rec["latest"])` 同一对账 ⇒ 同因两条 | `watchdog.py` L1770–1867, `watchdog_inputs.py` L115 | (c) |
| F7 | 触发 ⇒ 阶梯 halt_opening → flatten_all(255 张 IOC reduce-only, 235,383 USDT, 5.39 bps 滑点 + 5 bps 费 ≈ 245 USDT)→ alert; 异常名合计 1,524 USDT = gross 0.65% | `watchdog/state.json` degradation, `events.jsonl` | (c) |
| F8 | 历史: `differs from ours` 今天前 0 行; 08Z 四类标记 0/0/0/0 ⇒ 首次出现 = 首次「全退出 + mark≠mid」 | `pilot_log/*/orders.jsonl` 扫描 | 测试用真行 |
| F9 | 复审 15 轮 + 电池 132 套无 reduce-only 截量正控; 身份核对三态(absent/malformed/value)缺 clamped | `binance_broker.py` L300–345 docstring; `tests_*` | 新套件 |

## §2 方案
### (a) clamped 态(`binance_broker.py`)
`_ident_check(rec, "origQty", expected, what)` 前置: 若 `order.reduce_only is True` 且 `resp.reduceOnly is True` 且 `0 < origQty < expected`(同侧、更小)⇒ 返回 **None** 并在 `out["clamped"] = {"ours": expected, "venue": origQty, "why": "reduceOnly clamped to position"}` 记录; `orig_qty` 取回执值(它就是持仓); 后续 executedQty / 子成交按 origQty 为界。**不放宽**: origQty > ours、方向不符、非 reduceOnly 的 origQty 差, 仍是矛盾。容差 1e-6 不动。
### (b) 全退出数量 = 持仓张数(`binance_executor.plan`)
`target == 0 and held != 0` ⇒ `qty = -held_qty`(读回的 `venue_position_qty`, 非 notional/mid), 仍过 `round_qty`; 其余路径不变。效果: F2 差异从源头消失, (a) 成为纵深防御而非主防线。持仓张数缺失(读回无 qty 列)⇒ 退回旧路径并记 `qty_source=notional_over_mid`。
### (c) 比例响应(书行为改动, **用户裁定**)
判据(冻结先于看数): 最新对账锚的 `execution_of_unknown_size` 异常若满足 **全部**: (i) 场所记录自洽(回执 origQty == Σ 子成交, 读回该名持仓与之相容); (ii) 异常名 Σ|intended| ≤ gross 的 **2%** 且名数 ≤ **5**; ⇒ 响应 = 停开仓 + HIGH 告警 + 仅对这些名做 reduce-only 复核(不平其他名); 不满足任一 ⇒ 现行全书阶梯。§4-7 漂移与 §4-5b 共用对账 ⇒ 同一判据。选项: **A** 采用上述 2%/5 名; **B** 仅停开仓+告警, 不自动处置; **C** 维持现行(任一未知 ⇒ 全书)。我方建议 A。
### 测试(全部先红后绿; 旧码红)
`live/tests_reduce_only_clamp.py`(新): T1 真回执(MEME 12Z 行, 逐字)⇒ 新码 `clamped`、`inconsistent` 空、orig_qty 1933692; 旧码 `inconsistent` 非空。T2 origQty > ours 同 reduceOnly ⇒ 仍矛盾。T3 非 reduceOnly 的 origQty 差 ⇒ 仍矛盾。T4 方向错 ⇒ 矛盾。T5 `plan` 全退出: held_qty 1933692 / mark≠mid ⇒ qty == −1933692。T6 读回无 qty ⇒ 退回旧路径且记 `qty_source`。T7 端到端: 12Z 真账本三文件(orders/fills/position_readback)经 `reconcile` ⇒ 新码 MEME/POPCAT `known`(residual 0), `anomalies` 0; 旧码 2 异常(=E-0912-A 复现)。T8 (c) 若采用: 合成 2 名/0.65% 自洽未知 ⇒ 局部响应; 6 名或 3% ⇒ 全书。电池全绿; `gate_coverage` 条目。
### 落地
克隆 `/Users/haosiyu/cc_tmp/exec_w6`(918559f 起); 研究员复审; 用户字 ⇒ 非锚窗 `fetch + merge --ff-only <sha>` ⇒ 首锚验收(RUNBOOK §3 + 新条目: 全退出名 origQty == 持仓, `clamped` 记录数, 四类标记 0)⇒ 用户手动恢复(看门狗 resume 动词按 state.json 说明)。
## §3 不做
不改 1e-6 容差; 不删身份核对(它对「回执不是我们的单」仍是对的); 不回滚 d040c74(等用户字); 不在事故期间落 W1/W2。
