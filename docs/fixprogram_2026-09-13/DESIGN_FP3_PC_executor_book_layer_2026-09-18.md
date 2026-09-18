# FP3 P-C 设计 v3: 执行器书层作为纯函数(决策前可见状态 → 逐请求下单意图)— 2026-09-18

> **创建:** 2026-09-18 06:0xZ; v2 06:4xZ; **v3 07:1xZ**(按独立复审第九轮 b3f7130a 三处问题重写; v1/v2 原字节在 git 517b7a5d / 92663c06) | **Session:** b9646a9e(主研究员) | **状态:** 设计(全部输入来源已在生产记录里逐项核到; 装置未写) | **作废条件:** 执行器记录格式变更; 复审否决 §3
> **v2 的三处错误(第九轮复审, 已用原函数核实)**: ① `target_gross ÷ gross_mult` 在限仓时还原不出交易前权益(反例: 权益 100、2×、限仓后目标毛额 149 ⇒ 反推 74.5); ② `known_gaps` 是下单**后**的缺口清单, 当交易前禁止名单会把结果喂回输入; ③ 持仓张数 × 下单中价 ≠ 生产用的账户估值, 「允许差一手」会放过不同订单——必须逐请求核数量、方向、阶段、身份。

## 1. 决策前状态的**真实记录点**(执行器树 409ea16; 04Z 锚逐项核过)
| 量 | 来源(每锚一条, 决策时写) | 04Z 实测 |
|---|---|---|
| 交易前权益 eq_pre | `state/anchor_runs.log` 的 **phase_A 行** `sizing.nav`(= `_size_book` 用的 `_snap0.equity`, L1325/L1978) | 115,439.26(≠ target_gross/2 = 115,220; ≠ 交易后 NAV 行 115,606) |
| 目标毛额 | phase_A `sizing.gross / gross_wanted / resized / target_leverage` | 230,878.51, resized True, 2.0 |
| 目标权重 | target_live/<A>.json(P-B 可重现)→ `EXT.target_vector`, `gross_norm` 在 anchors 行 `external_book.gross_norm` | 242 名, 0.8145 |
| 扣留集(决策时) | phase_A `untradable_names` + `untradable_reason` + `untradable_held`; anchors 行 `external_book.held_exit / meta_excluded / below_min_notional{names}`; `n_untradable_withheld` | 14 名: popped 6 / flatten_only 7 / add_blocked 1; held_exit 7; 小额 1(LTCUSDT) |
| 止损集 | phase_A `untradable_reason` 里 source = per_name_stop 的名(即 `_untradable_sources["per_name_stop"]`); phase_C `per_name_stop{stopped, counters, cooldown_n}` | stopped 0, counters NEAR/ARB 1, cooldown 6 |
| 场所过滤器 | phase_A `external_filters` + `universe.tradable`; floors/step/tick = `exchange_info_cache.json`(**当前**文件; 历史锚要当时快照, 无则标缺证) | tradable 列表; 658 名过滤器 |
| 决策价 | orders 行 `mid_at_anchor`(逐名, 决策时; 与 `price_submit` 分开) | — |
| 决策前持仓 | 上一锚 `position_readback`(张数)按期间 fills 推进; 推不出 ⇒ `UNAVAILABLE_STATE`; loop_state.positions 只作核对 | 243 行 |
| 场所上限钳 | phase_A `venue_cap_clamp` | — |
| **验收对象** | `orders.jsonl` 每单 `request_ledger[*]`: `client_id = <rid>-<SYMBOL>-<attempt>`, `qty`, `notional_est`, `state`, `confirmed_qty/notional`, `trade_qty/trade_quote`(逐 trade id) + 订单行 `side / attempt_idx / order_type / placement_arm / terminal_reason` | 504 单 |
**不用**: `known_gaps`(下单后)、`daily_nav`(交易后)、`target_gross ÷ gross_mult`(限仓失真)、当前 `per_name_stop.json`(倒推历史)。

## 2. 纯函数合同(v3)
`intent(A) → {requests: [{client_id, symbol, side, qty, notional_est, attempt_idx, reason}], skipped: {name → reason}, popped/flatten_only/add_blocked: sets, reshape_report, gross_intent}`
- 输入全部来自 §1 的决策时记录; 顺序与生产一致(anchor_loop): `_size_book`(eq_pre × gross_mult, 死区/下限规则同码)→ `EXT.target_vector` → 扣留集(untradable ∪ held_exit ∪ per_name_stop)→ `EXT.below_min_notional`(小额)→ `apply_withhold_and_reshape(target, held, untradable, sizing_gross, floors, force_flat=stop)`(POP → RESHAPE → CLAMP, 同码 import)→ 张数按 step 取整 → 逐请求意图。
- **验收 P-C1 = 逐请求精确匹配**: 对每个 `client_id`(rid-SYMBOL-attempt): 数量(step 取整后**相等**)、方向、阶段(attempt_idx)、订单类型; 多出/缺少的请求逐条归因(拒单重试、追单臂、场所上限钳、小额跳过)或标缺证。不设「一手」容差; 名义额只作对照, 不作判据。
- 锚后回读、fills、known_gaps 只用于**验证输出**与执行层归因, 不进入输入。

## 3. 判据与顺序
- **P-C1**: 先在**输入齐全的新锚**(09-18 04Z 起, phase_A/phase_C/orders/readback 齐)上 1–2 锚做到逐请求零不可归因差异; 达不到就逐条列差异, 不放宽。
- **P-C2**: 三个止损日(09-06/09-09/09-12)与 09-16/17 的层分解(生产者目标 → 意图 → 实际), 缺状态的锚标缺证。
- **P-C3**(只读反事实): 止损分母改「相对开仓价」、「两锚确认 → 一锚」; 完整组合对照; 部署另立提案 + 用户字。
- 顺序与复审一致: **先修合同(本件)→ 新锚验证 → 再补历史**; 不再在本历史上追加规则规格。

## 4. 工作量
纯函数 + 逐请求比较器 0.5 d(同码 import: `scheduler.anchor_loop.apply_withhold_and_reshape`, `live.external_book`, `live.per_name_stop`, `signal.legs`); 04Z/08Z 两锚 P-C1 0.25 d; 历史回补 + P-C2 0.5 d; P-C3 0.5 d; 独立复审。装置只读, 与生产树零接触(import 冻结副本 409ea16)。
