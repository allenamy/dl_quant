> **创建:** 2026-09-18 | **Session:** b9646a9e | **状态:** 已完成 | **作废条件:** P-C1 装置换代, 或区间外重跑改变了任一聚合数字

# P-C1 R15-P1/P2 — 检测不是会计(detection-not-accounting)收据

## 一句话
R15-P1/P2 的修复**只买检测能力, 不改任何账面数字**。P-C1 是回放装置(仪器); 修的是「装置抓不住一条违反生产规则的记录」这个**测量缺陷**, 不是交易缺陷。任何把它读成「书此前算错了」的措辞都是错的。

## 检测 vs 会计 —— 逐项证据
1. **不变量**: 区间内全 **46,363** 条订单行, 处处 `filled_known_notional == filled_notional`(两者皆非 None), **0 行分歧**。修法把残差的总额列从 `filled_known_notional`(只是已知部分)改读 `filled_notional`(闭合总额, 生产 `ledger_row_columns` L266 = `known_n if closed else None`), 在这 46,363 行上二者相等 ⇒ 对已闭合行是逐位 no-op。
2. **唯一分歧 2 行** = 真实 `filled_amount_unknown`(MEMEUSDT / POPCATUSDT), 同属 rid `A1789215839` = **09-12 12Z**; 该锚在装置里因 `TREE_LACKS_FORCE_FLAT_WITH_STOPS` **被拒(REFUSED)**, 装置从不到达该锚的残差逻辑 ⇒ 已量测聚合不受影响。
3. **51 锚历史重跑聚合逐位不变**(prior v13 收据 vs v14 / 结构版): 34 可跑 / 30 可测 / 4 空测 / **6,599 数量相等** / complete_parity **0/34** / plan_population 全同。
4. **逐锚量测指标**(09-15 00Z 抽样): pre-fix 设备 == v14 == 结构版, 逐位相同(R1_exact/comparisons/complete_parity/n_unmeasurable/plan/request population)。

## 生产是拒绝的 —— 为什么这不是交易缺陷
生产执行器 409ea16 `live/binance_executor.py` L1735-1742 读不到成交时写 `skipped_unknown_fill`, `submitted=False`, 把 `intended_notional` 与 `filled_notional` **两者声明未知**, 附注「从假定为零去补单会把已有仓位翻倍」。**生产从不从假定零补单。** 本修复只让回放装置也不再捏造那个零 —— 若某天真有一条从假定零补出的记录, v13 的装置会把它读成 CLEAN, v14 会拒绝。

## 唯一的逐锚字节差(非会计、非本修复)
v13→v14 收据里 7 个近锚 `reshape_bitwise` 漂移(如 16/17→17/17), within-1e-9 稳定在 34。对照证实为**时间漂移**: pre-fix 设备现在同样给 17/17, 且与 fixed 设备逐锚量测指标逐位相同, 上游于 R3-only 改动 ⇒ 非本修复所致。(观察到的是 `reshape_bitwise` 漂移, 非 `filters_assumed_current` —— 本次重跑该标记稳定。)

## 收据指针
- 聚合: `PC1_HISTORY_v14_0910_0918.json`(51 锚, 09-10 00Z→09-18 08Z)。
- commits: `66c23d3e`(R15-P1/P2 修复 + `_sent` 措辞)/ `934a8cb3`(R15-P1 结构收口: 唯一拒绝式访问器 + UNKNOWN 毒化哨兵)。
- 电池: `pc1_intent_replay.py` 结构版 sha `923d6b84`, `tests_pc1_v13.py` **49/49 ALL PASS**; [11.1]-[11.4]/[11.6] 及结构对照 [11.7]/[11.8] 在 pre-fix(sha `f74732b6`)RED。
